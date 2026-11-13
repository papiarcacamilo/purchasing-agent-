"""Construcción y compilación del grafo LangGraph.

Flujo completo:

    START -> interpretar_pedido -> validar_pedido
             validar_pedido  <-> pedir_aclaracion    (ciclo de aclaración)
             validar_pedido   -> preparar_busqueda -> agente_buscador
             agente_buscador <-> herramientas        (ciclo del agente)
             agente_buscador  -> recolectar_ofertas -> normalizar_ofertas
                              -> clasificar_equivalencia -> calcular_presupuesto -> END

Hay dos ciclos y los dos tienen tope: MAX_ACLARACIONES y MAX_VUELTAS.
"""
from typing import Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from cotizador.herramientas import crear_herramientas
from langgraph.checkpoint.base import BaseCheckpointSaver

from cotizador.nodos import (
    calcular_presupuesto,
    crear_nodo_agente_buscador,
    crear_nodo_clasificar,
    crear_nodo_interpretar,
    crear_nodo_preparar_busqueda,
    crear_nodo_recolectar,
    normalizar_ofertas,
    pedir_aclaracion,
    validar_pedido,
)
from cotizador.routers import enrutar_aclaracion, enrutar_busqueda, enrutar_validacion
from cotizador.schemas import EstadoCompra, Oferta


def construir_grafo(
    interprete: Optional[Runnable] = None,
    buscador: Optional[Runnable] = None,
    clasificador: Optional[Runnable] = None,
    catalogos: Optional[dict[str, list[Oferta]]] = None,
    herramientas: Optional[list[BaseTool]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
):
    """Arma y compila el grafo.

    Las dependencias externas se inyectan por parámetro: el mismo grafo corre
    con OpenAI en producción y con funciones falsas en las pruebas.
    """
    if catalogos is None:
        from cotizador.catalogos import cargar_catalogos

        catalogos = cargar_catalogos()
    if herramientas is None:
        herramientas = crear_herramientas(catalogos)
    if interprete is None or buscador is None or clasificador is None:
        # Se importa aquí para no exigir la clave cuando todo se inyecta.
        from cotizador.llm import construir_buscador, construir_clasificador, construir_interprete

        interprete = interprete or construir_interprete()
        buscador = buscador or construir_buscador(herramientas)
        clasificador = clasificador or construir_clasificador()

    g = StateGraph(EstadoCompra)

    # --- Nodos ---
    g.add_node("interpretar_pedido", crear_nodo_interpretar(interprete))
    g.add_node("validar_pedido", validar_pedido)
    g.add_node("pedir_aclaracion", pedir_aclaracion)
    g.add_node("preparar_busqueda", crear_nodo_preparar_busqueda(catalogos))
    g.add_node("agente_buscador", crear_nodo_agente_buscador(buscador, herramientas))
    # ToolNode ejecuta las llamadas que pidió el agente. messages_key: nuestro
    # campo se llama "mensajes", no "messages".
    g.add_node("herramientas", ToolNode(herramientas, messages_key="mensajes"))
    g.add_node("recolectar_ofertas", crear_nodo_recolectar(catalogos))
    g.add_node("normalizar_ofertas", normalizar_ofertas)
    g.add_node("clasificar_equivalencia", crear_nodo_clasificar(clasificador))
    g.add_node("calcular_presupuesto", calcular_presupuesto)

    # --- Aristas ---
    g.add_edge(START, "interpretar_pedido")
    g.add_edge("interpretar_pedido", "validar_pedido")
    g.add_conditional_edges(
        "validar_pedido", enrutar_validacion, ["pedir_aclaracion", "preparar_busqueda"]
    )
    # Tras la respuesta se reinterpreta la solicitud completa: el pedido nuevo
    # reemplaza al anterior y vuelve a validarse. Si no hubo respuesta se pasa
    # directo a validar, sin gastar una llamada al modelo.
    g.add_conditional_edges(
        "pedir_aclaracion", enrutar_aclaracion, ["interpretar_pedido", "validar_pedido"]
    )
    g.add_edge("preparar_busqueda", "agente_buscador")

    # Enrutamiento: el agente pide herramientas o da por terminada la búsqueda.
    g.add_conditional_edges(
        "agente_buscador", enrutar_busqueda, ["herramientas", "recolectar_ofertas"]
    )
    g.add_edge("herramientas", "agente_buscador")
    g.add_edge("recolectar_ofertas", "normalizar_ofertas")
    g.add_edge("normalizar_ofertas", "clasificar_equivalencia")
    g.add_edge("clasificar_equivalencia", "calcular_presupuesto")
    g.add_edge("calcular_presupuesto", END)

    # Sin checkpointer el grafo funciona, pero si se detiene a preguntar no
    # puede reanudarse: no hay dónde guardar el estado de la pausa.
    return g.compile(checkpointer=checkpointer)

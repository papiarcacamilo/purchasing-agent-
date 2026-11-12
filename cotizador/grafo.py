"""Construcción y compilación del grafo LangGraph.

Flujo actual (fases 1 y 2):

    START -> interpretar_pedido -> preparar_busqueda -> agente_buscador
             agente_buscador <-> herramientas        (ciclo del agente)
             agente_buscador  -> recolectar_ofertas -> END

En las siguientes fases se agregan la validación con `interrupt()`, la
normalización, el presupuesto y el informe.
"""
from typing import Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from cotizador.herramientas import crear_herramientas
from cotizador.nodos import (
    crear_nodo_agente_buscador,
    crear_nodo_interpretar,
    crear_nodo_preparar_busqueda,
    crear_nodo_recolectar,
)
from cotizador.routers import enrutar_busqueda
from cotizador.schemas import EstadoCompra, Oferta


def construir_grafo(
    interprete: Optional[Runnable] = None,
    buscador: Optional[Runnable] = None,
    catalogos: Optional[dict[str, list[Oferta]]] = None,
    herramientas: Optional[list[BaseTool]] = None,
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
    if interprete is None or buscador is None:
        # Se importa aquí para no exigir la clave cuando todo se inyecta.
        from cotizador.llm import construir_buscador, construir_interprete

        interprete = interprete or construir_interprete()
        buscador = buscador or construir_buscador(herramientas)

    g = StateGraph(EstadoCompra)

    # --- Nodos ---
    g.add_node("interpretar_pedido", crear_nodo_interpretar(interprete))
    g.add_node("preparar_busqueda", crear_nodo_preparar_busqueda(catalogos))
    g.add_node("agente_buscador", crear_nodo_agente_buscador(buscador, herramientas))
    # ToolNode ejecuta las llamadas que pidió el agente. messages_key: nuestro
    # campo se llama "mensajes", no "messages".
    g.add_node("herramientas", ToolNode(herramientas, messages_key="mensajes"))
    g.add_node("recolectar_ofertas", crear_nodo_recolectar(catalogos))

    # --- Aristas ---
    g.add_edge(START, "interpretar_pedido")
    g.add_edge("interpretar_pedido", "preparar_busqueda")
    g.add_edge("preparar_busqueda", "agente_buscador")

    # Enrutamiento: el agente pide herramientas o da por terminada la búsqueda.
    g.add_conditional_edges(
        "agente_buscador", enrutar_busqueda, ["herramientas", "recolectar_ofertas"]
    )
    g.add_edge("herramientas", "agente_buscador")
    g.add_edge("recolectar_ofertas", END)

    return g.compile()

"""Construcción y compilación del grafo LangGraph.

Por ahora el grafo tiene un solo nodo. En las siguientes fases se agregan la
validación, el agente buscador, la normalización, el presupuesto y el informe.
"""
from typing import Optional

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from cotizador.nodos import crear_nodo_interpretar
from cotizador.schemas import EstadoCompra


def construir_grafo(interprete: Optional[Runnable] = None):
    """Arma y compila el grafo.

    Las dependencias externas se inyectan por parámetro: el mismo grafo corre
    con OpenAI en producción y con funciones falsas en las pruebas.
    """
    if interprete is None:
        # Se importa aquí para no exigir la clave cuando se inyecta un intérprete.
        from cotizador.llm import construir_interprete

        interprete = construir_interprete()

    g = StateGraph(EstadoCompra)

    # --- Nodos ---
    g.add_node("interpretar_pedido", crear_nodo_interpretar(interprete))

    # --- Aristas ---
    g.add_edge(START, "interpretar_pedido")
    g.add_edge("interpretar_pedido", END)

    return g.compile()

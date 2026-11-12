"""Funciones de enrutamiento (aristas condicionales).

Reciben el estado y devuelven la CLAVE del siguiente nodo. No modifican el estado.
"""
from cotizador.nodos.buscar import MAX_VUELTAS, vueltas_usadas
from cotizador.schemas import EstadoCompra


def enrutar_busqueda(state: EstadoCompra) -> str:
    """Agente buscador -> herramientas (si pidió alguna) o fin de la búsqueda.

    El tope de vueltas corta el ciclo aunque el agente siga pidiendo búsquedas.
    """
    ultimo = state.mensajes[-1] if state.mensajes else None
    quiere_buscar = bool(getattr(ultimo, "tool_calls", None))
    if quiere_buscar and vueltas_usadas(state.mensajes) <= MAX_VUELTAS:
        return "herramientas"
    return "recolectar_ofertas"

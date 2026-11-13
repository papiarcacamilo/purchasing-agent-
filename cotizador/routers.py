"""Funciones de enrutamiento (aristas condicionales).

Reciben el estado y devuelven la CLAVE del siguiente nodo. No modifican el estado.
"""
from cotizador.nodos.buscar import MAX_VUELTAS, vueltas_usadas
from cotizador.nodos.validar import necesita_aclaracion
from cotizador.schemas import EstadoCompra


def enrutar_aclaracion(state: EstadoCompra) -> str:
    """Después de preguntar -> reinterpretar, o volver a validar.

    Si el usuario no respondió no hay texto nuevo: reinterpretar gastaría una
    llamada al modelo para obtener exactamente el mismo pedido.
    """
    if state.hubo_respuesta:
        return "interpretar_pedido"
    return "validar_pedido"


def enrutar_validacion(state: EstadoCompra) -> str:
    """Validación -> preguntar al usuario o seguir con la búsqueda.

    Usa la misma función que el nodo `validar_pedido`, para que la regla no
    pueda quedar escrita de dos formas distintas.
    """
    if necesita_aclaracion(state):
        return "pedir_aclaracion"
    return "preparar_busqueda"


def enrutar_busqueda(state: EstadoCompra) -> str:
    """Agente buscador -> herramientas (si pidió alguna) o fin de la búsqueda.

    El tope de vueltas corta el ciclo aunque el agente siga pidiendo búsquedas.
    """
    ultimo = state.mensajes[-1] if state.mensajes else None
    quiere_buscar = bool(getattr(ultimo, "tool_calls", None))
    if quiere_buscar and vueltas_usadas(state.mensajes) <= MAX_VUELTAS:
        return "herramientas"
    return "recolectar_ofertas"

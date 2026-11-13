"""Nodo 3: detiene el grafo y le pregunta al usuario lo que falta.

`interrupt()` no es un `input()`: no lee del teclado. Lo que hace es **guardar
el estado completo del grafo y salir**, entregando a quien lo invocó una
pregunta. Quien atiende esa pregunta puede ser una consola, un cuaderno, una
API o un chat, y puede responder un segundo después o al día siguiente.

El grafo se reanuda con `Command(resume=<respuesta>)`: la ejecución vuelve a
entrar en este mismo nodo, y `interrupt()` devuelve esa respuesta como si
nunca hubiera habido una pausa.

Para que el estado se pueda guardar y recuperar hace falta un *checkpointer*
al compilar. Sin él, el grafo no se rompe: se detiene e informa lo que
necesitaba, pero no puede reanudarse.
"""
from langgraph.types import interrupt

from cotizador.nodos.validar import MAX_ACLARACIONES
from cotizador.schemas import EstadoCompra

# Marca el bloque de diálogo dentro de la solicitud. El prompt del intérprete
# conoce esta misma marca y sabe que lo que viene después NO es un producto
# nuevo: completa uno que ya estaba.
MARCA_ACLARACION = "--- Aclaración posterior ---"


def componer_solicitud(state: EstadoCompra, respuesta: str) -> str:
    """Pega la respuesta a la solicitud como un diálogo, no como más texto.

    Escribir solo la respuesta suelta al final ("...y 2 litros de aceite / 2kg")
    hace que el modelo la lea como un producto más. Nombrar la pregunta la ata
    al producto al que pertenece.
    """
    pregunta = "; ".join(state.datos_faltantes) or "aclaración"
    return (
        f"{state.texto_usuario}\n"
        f"{MARCA_ACLARACION}\n"
        f"Pregunta: {pregunta}\n"
        f"Respuesta del usuario: {respuesta}"
    )


def redactar_pregunta(faltan: list[str]) -> str:
    """Convierte la lista de huecos en una sola pregunta para una persona."""
    if not faltan:
        return "¿Desea agregar algo a la solicitud?"
    if len(faltan) == 1:
        return f"Para cotizar bien falta un dato: ¿{faltan[0]}?"
    puntos = "\n".join(f"  - {f}" for f in faltan)
    return f"Para cotizar bien faltan estos datos:\n{puntos}\n¿Los puede indicar?"


def _resumen(state: EstadoCompra) -> list[str]:
    """Lo que sí se entendió, para que el usuario no repita todo."""
    if state.pedido is None:
        return []
    resumen = []
    for item in state.pedido.items:
        cantidad = (
            f"{item.cantidad:g} {item.unidad}"
            if item.cantidad is not None and item.unidad
            else "cantidad sin definir"
        )
        resumen.append(f"{item.producto}: {cantidad}")
    return resumen


def pedir_aclaracion(state: EstadoCompra) -> dict:
    """Pausa el grafo. Al reanudarse, suma la respuesta a la solicitud original."""
    respuesta = interrupt(
        {
            "tipo": "aclaracion",
            "pregunta": redactar_pregunta(state.datos_faltantes),
            "faltan": state.datos_faltantes,
            "entendido": _resumen(state),
            "intento": state.aclaraciones + 1,
        }
    )

    texto = str(respuesta or "").strip()

    if not texto:
        # El usuario no quiso o no pudo responder. No se vuelve a preguntar
        # (sería insistir) y el grafo sigue: `validar_pedido` dejará
        # constancia de lo que no se supo.
        return {
            "aclaraciones": MAX_ACLARACIONES,
            "hubo_respuesta": False,
            "historial": ["[pedir_aclaracion] el usuario no respondió; se continúa sin el dato"],
        }

    # La respuesta se suma al texto original y se vuelve a interpretar todo
    # junto. Reinterpretar cuesta una llamada al modelo, pero evita escribir
    # un segundo analizador de lenguaje solo para las respuestas.
    return {
        "texto_usuario": componer_solicitud(state, texto),
        "aclaraciones": state.aclaraciones + 1,
        "hubo_respuesta": True,
        "historial": [f"[pedir_aclaracion] respuesta recibida: {texto}"],
    }

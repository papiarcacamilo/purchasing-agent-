"""Ejecuta el grafo atendiendo las pausas de `interrupt()`.

Es el puente entre el grafo y quien responde las preguntas. El grafo no sabe
si al otro lado hay una consola, un cuaderno o una prueba automática: solo
devuelve una pregunta y espera un `Command(resume=...)`.

    ejecutar("necesito arroz", responder=lambda p: "2 kg")
"""
import uuid
from typing import Callable, Optional

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from cotizador.grafo import construir_grafo
from cotizador.schemas import EstadoCompra

# Tope de seguridad del lado de quien ejecuta. El grafo ya tiene el suyo
# (MAX_ACLARACIONES); este protege contra un grafo mal cableado.
MAX_PAUSAS = 4


def responder_por_consola(pregunta: dict) -> str:
    """Muestra la pregunta en la terminal y devuelve lo que escriba el usuario."""
    print("\n--------- EL COTIZADOR NECESITA UN DATO ---------")
    if pregunta.get("entendido"):
        print("Hasta ahora se entendió:")
        for linea in pregunta["entendido"]:
            print(f"  - {linea}")
    print(pregunta.get("pregunta", "¿Puede aclarar la solicitud?"))
    print("(Enter en blanco para continuar sin ese dato.)")
    return input("> ").strip()


def ejecutar(
    texto: str,
    responder: Callable[[dict], str] = responder_por_consola,
    grafo=None,
    thread_id: Optional[str] = None,
) -> EstadoCompra:
    """Corre el grafo de principio a fin, atendiendo las pausas que aparezcan.

    `responder` recibe el contenido de la pausa y devuelve el texto del
    usuario. Devolver una cadena vacía significa "siga sin ese dato".
    """
    if grafo is None:
        # El checkpointer guarda el estado en memoria del proceso: alcanza para
        # una conversación. Para que la pausa sobreviva a un reinicio habría
        # que usar uno con base de datos, sin cambiar nada más del grafo.
        grafo = construir_grafo(checkpointer=InMemorySaver())

    # El thread_id identifica la conversación: es la llave con la que el
    # checkpointer encuentra el estado guardado al reanudar.
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}

    entrada = EstadoCompra(texto_usuario=texto)
    for _ in range(MAX_PAUSAS + 1):
        salida = grafo.invoke(entrada, config)
        pausas = salida.get("__interrupt__")
        if not pausas:
            return EstadoCompra.model_validate(salida)
        entrada = Command(resume=responder(pausas[0].value))

    raise RuntimeError(
        f"El grafo se detuvo más de {MAX_PAUSAS} veces: revise el tope de aclaraciones."
    )

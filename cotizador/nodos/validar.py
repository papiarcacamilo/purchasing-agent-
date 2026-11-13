"""Nodo 2: revisa el pedido interpretado y decide si hay que preguntar.

La validación es determinista: no se le pregunta al modelo si el pedido está
completo, se comprueba con código. El modelo ya hizo su trabajo (convertir
texto en datos); decidir si esos datos alcanzan es una regla del negocio.

Se distinguen dos cosas:

- **Dato faltante**: sin él no se puede cotizar bien (no se sabe cuánto
  comprar). Justifica detener el grafo y preguntarle al usuario.
- **Suposición**: el cotizador puede seguir, pero debe declarar bajo qué
  supuesto trabajó. No justifica interrumpir a nadie.
"""
from typing import Optional

from cotizador.schemas import EstadoCompra, Pedido

# Tope de preguntas. Sin tope, un usuario que nunca responde lo que falta
# dejaría el grafo preguntando en círculo.
MAX_ACLARACIONES = 2


def datos_que_faltan(pedido: Optional[Pedido]) -> list[str]:
    """Lista, en lenguaje natural, lo que impide cotizar bien.

    Devuelve una lista vacía si el pedido alcanza para trabajar.
    """
    if pedido is None or not pedido.items:
        return ["qué productos hay que cotizar"]

    faltan = []
    for item in pedido.items:
        if item.cantidad is None:
            faltan.append(f"cuánto {item.producto} se necesita")
        elif item.cantidad <= 0:
            faltan.append(f"una cantidad válida de {item.producto} (se entendió {item.cantidad:g})")
        elif item.unidad is None:
            faltan.append(f"en qué unidad son {item.cantidad:g} de {item.producto}")
    return faltan


def necesita_aclaracion(state: EstadoCompra) -> bool:
    """¿Hay que detenerse a preguntar?

    Una sola función para que el nodo y la arista condicional no puedan
    discrepar: si cambia la regla, cambia en un solo lugar.
    """
    return bool(state.datos_faltantes) and state.aclaraciones < MAX_ACLARACIONES


def validar_pedido(state: EstadoCompra) -> dict:
    """Marca lo que falta y, cuando el grafo sigue adelante, deja constancia."""
    faltan = datos_que_faltan(state.pedido)
    salida = {"datos_faltantes": faltan}

    # Todavía se puede preguntar: no se declara nada aún, puede que el
    # usuario responda y el hueco desaparezca.
    if faltan and state.aclaraciones < MAX_ACLARACIONES:
        salida["historial"] = [
            f"[validar_pedido] falta por aclarar: {'; '.join(faltan)}"
        ]
        return salida

    # A partir de aquí el grafo continúa. Lo que no se sepa se declara.
    suposiciones = []
    if faltan:
        suposiciones.append(
            "No se aclaró " + "; ".join(faltan)
            + ". Se cotizó un empaque de cada producto sin cantidad."
        )
    if state.pedido is not None and not state.pedido.ciudad:
        suposiciones.append(
            "No se indicó ciudad: se usaron los precios publicados en línea, "
            "que pueden variar por ciudad y no incluyen envío."
        )

    detalle = "sin datos pendientes" if not faltan else f"se continúa sin: {'; '.join(faltan)}"
    salida["historial"] = [f"[validar_pedido] {detalle}"]
    if suposiciones:
        salida["suposiciones"] = suposiciones
    return salida

"""Nodo 4: normalización de las ofertas.

Convierte el contenido de cada oferta a su unidad base y calcula el precio por
kg, por L o por unidad, para poder comparar presentaciones distintas.

Una oferta se marca como NO comparable, con su motivo, cuando:
- la tienda no publica el contenido del empaque (por ejemplo, papel higiénico
  anunciado solo en metros), o
- mide algo distinto de lo que pidió el usuario (pidió kg y la oferta está en mL).

No se descarta: el enunciado pide informar lo no comparable, no esconderlo.
"""
from agente.schemas import EstadoCompra, ItemPedido, Oferta, OfertaNormalizada, ResultadoBusqueda
from agente.unidades import (
    NOMBRE_DIMENSION,
    a_base,
    dimension,
    precio_por_unidad,
    son_comparables,
    unidad_base,
)


def normalizar_oferta(oferta: Oferta, item: ItemPedido) -> OfertaNormalizada:
    """Calcula el precio unitario de una oferta frente a lo que pidió el usuario."""
    if oferta.contenido is None or oferta.unidad_contenido is None:
        return OfertaNormalizada(
            oferta=oferta,
            comparable=False,
            motivo="la tienda no publica el contenido del empaque",
        )

    # Si el usuario no dijo unidad, se acepta la de la oferta tal cual.
    if item.unidad is not None and not son_comparables(item.unidad, oferta.unidad_contenido):
        pedido = NOMBRE_DIMENSION[dimension(item.unidad)]
        ofrecido = NOMBRE_DIMENSION[dimension(oferta.unidad_contenido)]
        return OfertaNormalizada(
            oferta=oferta,
            comparable=False,
            motivo=f"el pedido se mide en {pedido} y la oferta en {ofrecido}",
        )

    return OfertaNormalizada(
        oferta=oferta,
        comparable=True,
        contenido_base=a_base(oferta.contenido, oferta.unidad_contenido),
        unidad_base=unidad_base(oferta.unidad_contenido),
        precio_unitario=precio_por_unidad(oferta.precio, oferta.contenido, oferta.unidad_contenido),
    )


def _orden(normalizada: OfertaNormalizada) -> tuple:
    """Primero las comparables y, entre ellas, la más barata por unidad."""
    return (not normalizada.comparable, normalizada.precio_unitario or float("inf"))


def normalizar_ofertas(state: EstadoCompra) -> dict:
    """Nodo del grafo: normaliza las ofertas de cada ítem."""
    resultados, comparables, descartadas = [], 0, 0

    for resultado in state.resultados:
        normalizadas = sorted(
            (normalizar_oferta(oferta, resultado.item) for oferta in resultado.ofertas),
            key=_orden,
        )
        comparables += sum(1 for n in normalizadas if n.comparable)
        descartadas += sum(1 for n in normalizadas if not n.comparable)
        resultados.append(
            ResultadoBusqueda(item=resultado.item, ofertas=resultado.ofertas, normalizadas=normalizadas)
        )

    historial = [
        f"[normalizar_ofertas] {comparables} ofertas comparables, "
        f"{descartadas} no comparables"
    ]
    motivos = {n.motivo for r in resultados for n in r.normalizadas if n.motivo}
    if motivos:
        historial.append(f"[normalizar_ofertas] motivos: {'; '.join(sorted(motivos))}")
    return {"resultados": resultados, "historial": historial}

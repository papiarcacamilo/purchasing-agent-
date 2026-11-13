"""Cálculo del presupuesto. Código puro, sin LLM: las cuentas deben ser reproducibles.

Tres reglas acordadas con el equipo y exigidas por el enunciado:

1. No se compra fraccionado: si hacen falta 5 kg y la bolsa es de 3 kg, se compran
   2 bolsas y se informa el sobrante.
2. Se elige el empaque que MINIMIZA EL COSTO DE LO PEDIDO, no el de mejor precio
   por kilo. Para 2 kg, dos bolsas de 1 kg a $6.790 ($13.580) salen más baratas
   que una de 5 kg a $21.950, aunque esta tenga mejor precio por kilo.
3. Un envío desconocido no es cero: queda como no verificado y entonces no hay
   total confirmado, solo subtotal de productos.
"""
from typing import Optional

from cotizador.schemas import (
    ItemPedido,
    LineaPresupuesto,
    OfertaNormalizada,
    Presupuesto,
    ResultadoBusqueda,
)
from cotizador.unidades import a_base, paquetes_necesarios, son_comparables

# Primero lo que el usuario pidió; el sustituto solo si no hay equivalente.
PREFERENCIA = {"equivalente": 0, "sustituto": 1}


def paquetes_para(item: ItemPedido, normalizada: OfertaNormalizada) -> int:
    """Cuántos empaques hacen falta para cubrir lo pedido.

    Si el usuario no dijo cantidad, se presupuesta un empaque y se registra
    como suposición en el nodo.
    """
    oferta = normalizada.oferta
    if item.cantidad is None or item.unidad is None:
        return 1
    if not son_comparables(item.unidad, oferta.unidad_contenido or ""):
        return 1
    return paquetes_necesarios(item.cantidad, item.unidad, oferta.contenido, oferta.unidad_contenido)


def costo_de(item: ItemPedido, normalizada: OfertaNormalizada) -> float:
    return paquetes_para(item, normalizada) * normalizada.oferta.precio


def elegir_mejor(
    item: ItemPedido, normalizadas: list[OfertaNormalizada], proveedor: Optional[str] = None
) -> Optional[OfertaNormalizada]:
    """La oferta que cubre lo pedido al menor costo, prefiriendo las equivalentes.

    `proveedor` limita la elección a una tienda; sin él se eligen de cualquiera
    (eso es la compra combinada).
    """
    utilizables = [
        n
        for n in normalizadas
        if n.comparable
        and n.equivalencia in PREFERENCIA
        and (proveedor is None or n.oferta.proveedor == proveedor)
    ]
    if not utilizables:
        return None
    return min(utilizables, key=lambda n: (PREFERENCIA[n.equivalencia], costo_de(item, n)))


def _linea(item: ItemPedido, elegida: Optional[OfertaNormalizada]) -> LineaPresupuesto:
    if elegida is None:
        return LineaPresupuesto(
            producto=item.producto,
            cubierto=False,
            motivo="sin oferta utilizable en esta tienda",
            cantidad_pedida=item.cantidad,
        )

    oferta = elegida.oferta
    paquetes = paquetes_para(item, elegida)
    cubierta = paquetes * (elegida.contenido_base or 0)
    pedida = (
        a_base(item.cantidad, item.unidad)
        if item.cantidad is not None and item.unidad is not None
        else None
    )
    return LineaPresupuesto(
        producto=item.producto,
        cubierto=True,
        oferta=oferta,
        equivalencia=elegida.equivalencia,
        paquetes=paquetes,
        cantidad_pedida=pedida,
        cantidad_cubierta=cubierta,
        sobrante=round(cubierta - pedida, 6) if pedida is not None else None,
        unidad_base=elegida.unidad_base,
        subtotal=paquetes * oferta.precio,
    )


def _armar(nombre: str, lineas: list[LineaPresupuesto], combinado: bool = False) -> Presupuesto:
    cubiertas = [l for l in lineas if l.cubierto]
    return Presupuesto(
        nombre=nombre,
        combinado=combinado,
        lineas=lineas,
        subtotal_productos=sum(l.subtotal or 0 for l in cubiertas),
        envio=None,                 # los catálogos no publican envío: no verificado
        total_confirmado=None,      # sin envío no hay total confirmado
        items_cubiertos=len(cubiertas),
        items_totales=len(lineas),
        completo=bool(lineas) and len(cubiertas) == len(lineas),
        sin_cotizacion=[l.producto for l in lineas if not l.cubierto],
        con_sustituto=[l.producto for l in cubiertas if l.equivalencia == "sustituto"],
        tiendas=sorted({l.oferta.proveedor for l in cubiertas if l.oferta}),
    )


def presupuesto_de_tienda(resultados: list[ResultadoBusqueda], proveedor: str) -> Presupuesto:
    """Compra completa en una sola tienda."""
    lineas = [
        _linea(r.item, elegir_mejor(r.item, r.normalizadas, proveedor=proveedor)) for r in resultados
    ]
    return _armar(proveedor, lineas)


def presupuesto_combinado(resultados: list[ResultadoBusqueda]) -> Presupuesto:
    """Cada producto donde salga más barato, sin importar la tienda."""
    lineas = [_linea(r.item, elegir_mejor(r.item, r.normalizadas)) for r in resultados]
    return _armar("Compra combinada", lineas, combinado=True)


def vale_la_pena_combinar(combinado: Presupuesto, por_tienda: list[Presupuesto]) -> bool:
    """La combinada solo se ofrece si cubre más productos o sale más barata."""
    completos = [p for p in por_tienda if p.completo]
    if len(combinado.tiendas) < 2:
        return False
    if not completos:
        return combinado.items_cubiertos > max((p.items_cubiertos for p in por_tienda), default=0)
    return combinado.subtotal_productos < min(p.subtotal_productos for p in completos)

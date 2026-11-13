"""Nodo 6: cálculo del presupuesto.

Arma un presupuesto por cada tienda consultada y, si vale la pena, una compra
combinada. Todo en código: los números deben poder comprobarse.
"""
from cotizador.presupuesto import (
    presupuesto_combinado,
    presupuesto_de_tienda,
    vale_la_pena_combinar,
)
from cotizador.schemas import EstadoCompra


def _pesos(valor: float) -> str:
    return "$ " + f"{valor:,.0f}".replace(",", ".")


def calcular_presupuesto(state: EstadoCompra) -> dict:
    """Nodo del grafo: presupuesto por tienda y alternativa combinada."""
    tiendas = state.proveedores_consultados or sorted(
        {n.oferta.proveedor for r in state.resultados for n in r.normalizadas}
    )
    por_tienda = [presupuesto_de_tienda(state.resultados, tienda) for tienda in tiendas]
    combinado = presupuesto_combinado(state.resultados)

    historial, suposiciones = [], []
    for presupuesto in por_tienda:
        estado = "completa" if presupuesto.completo else f"faltan {len(presupuesto.sin_cotizacion)}"
        historial.append(
            f"[calcular_presupuesto] {presupuesto.nombre}: "
            f"{presupuesto.items_cubiertos}/{presupuesto.items_totales} productos, "
            f"subtotal {_pesos(presupuesto.subtotal_productos)} ({estado})"
        )

    ofrecer = vale_la_pena_combinar(combinado, por_tienda)
    if ofrecer:
        historial.append(
            f"[calcular_presupuesto] compra combinada en {', '.join(combinado.tiendas)}: "
            f"{combinado.items_cubiertos}/{combinado.items_totales} productos, "
            f"subtotal {_pesos(combinado.subtotal_productos)}"
        )
    else:
        historial.append("[calcular_presupuesto] la compra combinada no aporta: no se ofrece")

    # El envío no viene en los catálogos: se dice, no se asume cero.
    historial.append(
        "[calcular_presupuesto] envío no verificado en ningún proveedor: "
        "no hay total confirmado, solo subtotal de productos"
    )

    sin_cantidad = [
        r.item.producto for r in state.resultados if r.item.cantidad is None or r.item.unidad is None
    ]
    if sin_cantidad:
        suposiciones.append(
            f"No se indicó cantidad de: {', '.join(sin_cantidad)}. Se presupuestó un empaque de cada uno."
        )

    con_sustituto = sorted({p for presupuesto in por_tienda for p in presupuesto.con_sustituto})
    if con_sustituto:
        historial.append(
            f"[calcular_presupuesto] resueltos con un sustituto: {', '.join(con_sustituto)}"
        )

    salida = {
        "presupuestos": por_tienda,
        "combinado": combinado if ofrecer else None,
        "historial": historial,
    }
    if suposiciones:
        salida["suposiciones"] = suposiciones
    return salida

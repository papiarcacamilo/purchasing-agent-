"""Pruebas del cálculo del presupuesto (código puro, sin red ni clave)."""
from datetime import date

import pytest

from agente.nodos.presupuestar import calcular_presupuesto
from agente.presupuesto import (
    costo_de,
    elegir_mejor,
    paquetes_para,
    presupuesto_combinado,
    presupuesto_de_tienda,
    vale_la_pena_combinar,
)
from agente.schemas import (
    EstadoCompra,
    ItemPedido,
    Oferta,
    OfertaNormalizada,
    ResultadoBusqueda,
)
from agente.unidades import a_base, precio_por_unidad


def _norm(nombre, precio, contenido, unidad="g", proveedor="Éxito", equivalencia="equivalente"):
    """Una oferta ya normalizada y clasificada, como llega al presupuesto."""
    oferta = Oferta(
        proveedor=proveedor, nombre=nombre, presentacion=f"{contenido} {unidad}",
        contenido=contenido, unidad_contenido=unidad, precio=precio,
        url=f"https://example.com/{nombre}", fecha_consulta=date(2026, 11, 11),
    )
    return OfertaNormalizada(
        oferta=oferta, comparable=True, contenido_base=a_base(contenido, unidad),
        unidad_base={"g": "kg", "kg": "kg", "mL": "L", "L": "L", "unidad": "unidad"}[unidad],
        precio_unitario=precio_por_unidad(precio, contenido, unidad),
        equivalencia=equivalencia, razon="prueba",
    )


def _item(producto="arroz", cantidad=2, unidad="kg"):
    return ItemPedido(
        texto_original=f"{cantidad} {unidad} de {producto}", producto=producto,
        cantidad=cantidad, unidad=unidad, marca=None, presentacion=None, observaciones=None,
    )


def test_no_se_compra_fraccionado_y_se_informa_el_sobrante():
    item = _item(cantidad=5)
    bolsa_de_3 = _norm("Arroz 3 kg", 12900, 3000)
    assert paquetes_para(item, bolsa_de_3) == 2
    assert costo_de(item, bolsa_de_3) == 25800

    presupuesto = presupuesto_de_tienda([ResultadoBusqueda(item=item, normalizadas=[bolsa_de_3])], "Éxito")
    linea = presupuesto.lineas[0]
    assert linea.paquetes == 2 and linea.subtotal == 25800
    assert linea.cantidad_cubierta == 6.0 and linea.sobrante == 1.0


def test_se_elige_lo_mas_barato_PARA_LO_PEDIDO_no_el_mejor_precio_por_kilo():
    """Caso real: para 2 kg, dos bolsas de 1 kg ganan a una de 5 kg con mejor precio/kg."""
    item = _item(cantidad=2)
    una_de_cinco = _norm("Arroz 5 kg", 21950, 5000)     # $ 4.390 por kg
    una_de_uno = _norm("Arroz 1 kg", 6790, 1000)        # $ 6.790 por kg
    assert una_de_cinco.precio_unitario < una_de_uno.precio_unitario   # gana por kilo...

    elegida = elegir_mejor(item, [una_de_cinco, una_de_uno])
    assert elegida is una_de_uno                                       # ...pero pierde por costo
    assert costo_de(item, una_de_uno) == 13580 < costo_de(item, una_de_cinco)


def test_se_prefiere_el_equivalente_aunque_el_sustituto_sea_mas_barato():
    item = _item()
    sustituto = _norm("Arroz blanco", 3000, 1000, equivalencia="sustituto")
    equivalente = _norm("Arroz integral", 4500, 1000, equivalencia="equivalente")

    elegida = elegir_mejor(item, [sustituto, equivalente])
    assert elegida is equivalente


def test_una_oferta_no_comparable_nunca_entra_al_presupuesto():
    item = _item()
    descartada = _norm("Arroz raro", 1000, 1000, equivalencia="no_comparable")
    assert elegir_mejor(item, [descartada]) is None

    presupuesto = presupuesto_de_tienda([ResultadoBusqueda(item=item, normalizadas=[descartada])], "Éxito")
    assert not presupuesto.completo
    assert presupuesto.sin_cotizacion == ["arroz"] and presupuesto.subtotal_productos == 0


def test_sin_cantidad_indicada_se_presupuesta_un_empaque():
    sin_cantidad = ItemPedido(
        texto_original="leche", producto="leche", cantidad=None, unidad=None,
        marca=None, presentacion=None, observaciones=None,
    )
    oferta = _norm("Leche 900 mL", 3090, 900, unidad="mL")
    assert paquetes_para(sin_cantidad, oferta) == 1

    salida = calcular_presupuesto(
        EstadoCompra(
            proveedores_consultados=["Éxito"],
            resultados=[ResultadoBusqueda(item=sin_cantidad, normalizadas=[oferta])],
        )
    )
    assert any("No se indicó cantidad" in s for s in salida["suposiciones"])


def test_el_envio_desconocido_no_se_toma_como_cero():
    item = _item()
    presupuesto = presupuesto_de_tienda(
        [ResultadoBusqueda(item=item, normalizadas=[_norm("Arroz 1 kg", 6790, 1000)])], "Éxito"
    )
    assert presupuesto.subtotal_productos == 13580
    assert presupuesto.envio is None            # no verificado, no cero
    assert presupuesto.total_confirmado is None  # sin envío no hay total confirmado


def test_la_compra_combinada_toma_cada_producto_donde_sale_mas_barato():
    arroz, aceite = _item("arroz"), _item("aceite", cantidad=1, unidad="L")
    resultados = [
        ResultadoBusqueda(item=arroz, normalizadas=[
            _norm("Arroz Éxito", 6790, 1000, proveedor="Éxito"),
            _norm("Arroz Carulla", 6800, 1000, proveedor="Carulla"),
        ]),
        ResultadoBusqueda(item=aceite, normalizadas=[
            _norm("Aceite Éxito", 7990, 900, unidad="mL", proveedor="Éxito"),
            _norm("Aceite Carulla", 6490, 900, unidad="mL", proveedor="Carulla"),
        ]),
    ]
    combinado = presupuesto_combinado(resultados)

    assert combinado.tiendas == ["Carulla", "Éxito"]
    assert combinado.lineas[0].oferta.proveedor == "Éxito"     # el arroz más barato
    assert combinado.lineas[1].oferta.proveedor == "Carulla"   # el aceite más barato
    # 2 arroces en Éxito + 2 aceites en Carulla (900 mL no cubren 1 L con uno solo)
    assert combinado.subtotal_productos == 2 * 6790 + 2 * 6490


def test_la_combinada_solo_se_ofrece_si_aporta_algo():
    arroz = _item()
    solo_exito = [ResultadoBusqueda(item=arroz, normalizadas=[_norm("Arroz", 6790, 1000)])]
    combinado = presupuesto_combinado(solo_exito)
    por_tienda = [presupuesto_de_tienda(solo_exito, "Éxito")]

    # Una sola tienda: combinar no aporta nada.
    assert not vale_la_pena_combinar(combinado, por_tienda)


def test_la_combinada_se_ofrece_cuando_ninguna_tienda_tiene_todo():
    arroz, aceite = _item("arroz"), _item("aceite", cantidad=1, unidad="L")
    resultados = [
        ResultadoBusqueda(item=arroz, normalizadas=[_norm("Arroz", 6790, 1000, proveedor="Éxito")]),
        ResultadoBusqueda(item=aceite, normalizadas=[
            _norm("Aceite", 6490, 1000, unidad="mL", proveedor="Carulla")
        ]),
    ]
    por_tienda = [presupuesto_de_tienda(resultados, t) for t in ("Éxito", "Carulla")]
    combinado = presupuesto_combinado(resultados)

    assert not any(p.completo for p in por_tienda)   # ninguna tienda sola alcanza
    assert combinado.completo and vale_la_pena_combinar(combinado, por_tienda)


def test_el_nodo_informa_el_estado_de_cada_tienda_y_el_envio():
    arroz = _item()
    estado = EstadoCompra(
        proveedores_consultados=["Éxito", "Carulla"],
        resultados=[ResultadoBusqueda(item=arroz, normalizadas=[
            _norm("Arroz Éxito", 6790, 1000, proveedor="Éxito")
        ])],
    )
    salida = calcular_presupuesto(estado)
    historial = " | ".join(salida["historial"])

    assert "Éxito: 1/1 productos" in historial and "completa" in historial
    assert "Carulla: 0/1 productos" in historial
    assert "envío no verificado" in historial
    assert [p.nombre for p in salida["presupuestos"]] == ["Éxito", "Carulla"]


def test_se_avisa_cuando_un_producto_se_resolvio_con_un_sustituto():
    item = _item()
    estado = EstadoCompra(
        proveedores_consultados=["Éxito"],
        resultados=[ResultadoBusqueda(item=item, normalizadas=[
            _norm("Arroz blanco", 6790, 1000, equivalencia="sustituto")
        ])],
    )
    salida = calcular_presupuesto(estado)
    assert salida["presupuestos"][0].con_sustituto == ["arroz"]
    assert any("sustituto" in linea for linea in salida["historial"])

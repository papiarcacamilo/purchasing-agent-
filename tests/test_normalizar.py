"""Pruebas del nodo de normalización (sin red ni clave)."""
from datetime import date

import pytest

from agente.nodos.normalizar import normalizar_oferta, normalizar_ofertas
from agente.schemas import EstadoCompra, ItemPedido, Oferta, ResultadoBusqueda


def _oferta(nombre="Arroz de prueba", precio=6790, contenido=1000, unidad="g", **extra) -> Oferta:
    base = dict(
        proveedor="Tienda Ficticia", nombre=nombre, presentacion=f"{contenido} {unidad}",
        contenido=contenido, unidad_contenido=unidad, precio=precio,
        url="https://example.com/p", fecha_consulta=date(2026, 11, 11),
    )
    return Oferta(**{**base, **extra})


def _item(producto="arroz", cantidad=2, unidad="kg") -> ItemPedido:
    return ItemPedido(
        texto_original=f"{cantidad} {unidad} de {producto}", producto=producto,
        cantidad=cantidad, unidad=unidad, marca=None, presentacion=None, observaciones=None,
    )


def test_una_oferta_en_gramos_se_compara_con_un_pedido_en_kilos():
    normalizada = normalizar_oferta(_oferta(contenido=5000, precio=21950), _item())
    assert normalizada.comparable and normalizada.motivo is None
    assert normalizada.contenido_base == 5.0 and normalizada.unidad_base == "kg"
    assert round(normalizada.precio_unitario) == 4390


def test_sin_contenido_publicado_la_oferta_no_es_comparable():
    sin_datos = _oferta(contenido=None, unidad=None)
    normalizada = normalizar_oferta(sin_datos, _item())
    assert not normalizada.comparable
    assert normalizada.motivo == "la tienda no publica el contenido del empaque"
    assert normalizada.precio_unitario is None


def test_una_oferta_que_mide_otra_cosa_no_es_comparable():
    aceite = _oferta(nombre="Aceite", contenido=900, unidad="mL")
    normalizada = normalizar_oferta(aceite, _item(producto="arroz", unidad="kg"))
    assert not normalizada.comparable
    assert "se mide en peso y la oferta en volumen" in normalizada.motivo


def test_si_el_usuario_no_indico_unidad_se_acepta_la_de_la_oferta():
    sin_unidad = ItemPedido(
        texto_original="leche", producto="leche", cantidad=None, unidad=None,
        marca=None, presentacion=None, observaciones=None,
    )
    normalizada = normalizar_oferta(_oferta(nombre="Leche", contenido=900, unidad="mL"), sin_unidad)
    assert normalizada.comparable and normalizada.unidad_base == "L"


def test_los_huevos_se_normalizan_por_unidad():
    cubeta = _oferta(nombre="Huevos AA (30 und)", precio=17900, contenido=30, unidad="unidad")
    normalizada = normalizar_oferta(cubeta, _item(producto="huevo", cantidad=30, unidad="unidad"))
    assert normalizada.comparable and normalizada.unidad_base == "unidad"
    assert round(normalizada.precio_unitario, 2) == pytest.approx(596.67, abs=0.01)


def test_el_nodo_ordena_las_comparables_por_precio_unitario_y_deja_las_otras_al_final():
    item = _item()
    estado = EstadoCompra(
        resultados=[
            ResultadoBusqueda(
                item=item,
                ofertas=[
                    _oferta(nombre="Arroz caro", precio=6790, contenido=1000),
                    _oferta(nombre="Arroz sin datos", contenido=None, unidad=None),
                    _oferta(nombre="Arroz barato", precio=21950, contenido=5000),
                ],
            )
        ]
    )

    salida = normalizar_ofertas(estado)
    normalizadas = salida["resultados"][0].normalizadas

    assert [n.oferta.nombre for n in normalizadas] == ["Arroz barato", "Arroz caro", "Arroz sin datos"]
    assert [n.comparable for n in normalizadas] == [True, True, False]
    # Las ofertas originales no se tocan.
    assert len(salida["resultados"][0].ofertas) == 3


def test_el_nodo_informa_cuantas_son_comparables_y_por_que_las_otras_no():
    estado = EstadoCompra(
        resultados=[
            ResultadoBusqueda(
                item=_item(),
                ofertas=[_oferta(), _oferta(nombre="Papel", contenido=None, unidad=None)],
            )
        ]
    )
    historial = normalizar_ofertas(estado)["historial"]
    assert "1 ofertas comparables, 1 no comparables" in historial[0]
    assert "no publica el contenido" in historial[1]


def test_sin_resultados_el_nodo_no_falla():
    salida = normalizar_ofertas(EstadoCompra())
    assert salida["resultados"] == []

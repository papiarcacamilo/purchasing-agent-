"""Pruebas de la conversión de unidades (código puro, sin red ni clave)."""
import pytest

from agente.unidades import (
    UnidadDesconocida,
    a_base,
    convertir,
    dimension,
    paquetes_necesarios,
    precio_por_unidad,
    son_comparables,
    unidad_base,
)


@pytest.mark.parametrize(
    "unidad, esperada", [("kg", "masa"), ("g", "masa"), ("lb", "masa"),
                         ("L", "volumen"), ("mL", "volumen"), ("unidad", "conteo")],
)
def test_cada_unidad_pertenece_a_su_dimension(unidad, esperada):
    assert dimension(unidad) == esperada


@pytest.mark.parametrize(
    "cantidad, unidad, esperado",
    [(1000, "g", 1.0), (2.5, "kg", 2.5), (1, "lb", 0.5), (900, "mL", 0.9), (30, "unidad", 30)],
)
def test_lleva_cualquier_cantidad_a_su_unidad_base(cantidad, unidad, esperado):
    # Sin error de coma flotante: 1000 g deben dar exactamente 1 kg.
    assert a_base(cantidad, unidad) == esperado


def test_la_libra_es_la_de_mercado_colombiano():
    assert convertir(1, "lb", "g") == 500
    assert convertir(0.5, "lb", "g") == 250


def test_convierte_en_los_dos_sentidos():
    assert convertir(2, "kg", "g") == 2000
    assert convertir(1500, "mL", "L") == 1.5


def test_no_se_convierte_entre_dimensiones_distintas():
    assert not son_comparables("kg", "mL")
    assert not son_comparables("unidad", "g")
    assert son_comparables("kg", "lb") and son_comparables("L", "mL")
    with pytest.raises(UnidadDesconocida):
        convertir(1, "kg", "L")


def test_una_unidad_inventada_se_rechaza():
    with pytest.raises(UnidadDesconocida):
        dimension("arroba")
    assert not son_comparables("arroba", "kg")


def test_el_precio_unitario_permite_comparar_presentaciones_distintas():
    # Caso real: arroz Diana de 5 kg frente al de 1 kg en Éxito.
    cinco_kilos = precio_por_unidad(21950, 5000, "g")
    un_kilo = precio_por_unidad(6790, 1000, "g")
    assert round(cinco_kilos) == 4390 and round(un_kilo) == 6790
    assert cinco_kilos < un_kilo        # la presentación grande sale más barata


def test_el_precio_unitario_se_expresa_en_la_unidad_base():
    assert unidad_base("g") == "kg" and unidad_base("mL") == "L"
    # 900 mL a $6.950 son $7.722 por litro.
    assert round(precio_por_unidad(6950, 900, "mL")) == 7722


def test_un_contenido_invalido_no_produce_un_precio_absurdo():
    with pytest.raises(ValueError):
        precio_por_unidad(5000, 0, "g")


@pytest.mark.parametrize(
    "pedido, unidad_pedido, contenido, unidad_contenido, paquetes",
    [
        (5, "kg", 3000, "g", 2),      # no se compra fraccionado: 2 bolsas de 3 kg
        (3, "kg", 1000, "g", 3),      # cuadra exacto
        (2, "kg", 5000, "g", 1),      # una sola bolsa alcanza
        (30, "unidad", 30, "unidad", 1),
        (30, "unidad", 12, "unidad", 3),
        (1, "L", 900, "mL", 2),
        (0.5, "lb", 500, "g", 1),
    ],
)
def test_los_paquetes_se_redondean_hacia_arriba(pedido, unidad_pedido, contenido, unidad_contenido, paquetes):
    assert paquetes_necesarios(pedido, unidad_pedido, contenido, unidad_contenido) == paquetes


def test_no_se_pide_un_paquete_de_mas_por_error_de_coma_flotante():
    # 3 bolsas de 1 kg para 3 kg: debe dar 3, no 4.
    assert paquetes_necesarios(3, "kg", 1000, "g") == 3
    assert paquetes_necesarios(0.9, "L", 900, "mL") == 1

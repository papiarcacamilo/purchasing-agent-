"""Pruebas del lector de catálogos. Usan datos FICTICIOS, no precios reales."""
from datetime import date
from pathlib import Path

import pytest

from cotizador.catalogos import (
    COLUMNAS,
    DIRECTORIO_CATALOGOS,
    ErrorCatalogo,
    _a_numero,
    cargar_catalogo,
    cargar_catalogos,
)

FICTICIO = Path(__file__).parent / "datos" / "tienda_ficticia.csv"
ENCABEZADO = ",".join(COLUMNAS)


def _csv(tmp_path, *filas, nombre="prueba.csv", separador=",", codificacion="utf-8"):
    lineas = [ENCABEZADO.replace(",", separador), *filas]
    ruta = tmp_path / nombre
    ruta.write_bytes("\n".join(lineas).encode(codificacion))
    return ruta


def test_carga_el_catalogo_ficticio_con_todos_los_campos_del_enunciado():
    arroz, aceite, huevos = cargar_catalogo(FICTICIO)
    assert (arroz.nombre, arroz.presentacion, arroz.precio, arroz.moneda) == (
        "Arroz blanco de prueba", "Bolsa x 1000 g", 4990.0, "COP",
    )
    assert arroz.proveedor == "Tienda Ficticia"
    assert arroz.url == "https://example.com/arroz-1000g"
    assert arroz.fecha_consulta == date(2026, 11, 11)
    assert arroz.disponible is True
    assert (arroz.contenido, arroz.unidad_contenido) == (1000.0, "g")
    assert aceite.precio == 12500.0 and aceite.moneda == "COP" and aceite.disponible is False
    assert huevos.fecha_consulta == date(2026, 11, 11)


def test_disponibilidad_vacia_significa_no_verificada():
    huevos = cargar_catalogo(FICTICIO)[2]
    assert huevos.disponible is None


@pytest.mark.parametrize(
    "texto, esperado",
    [("4990", 4990), ("4.990", 4990), ("$ 4.990", 4990), ("12,5", 12.5),
     ("1.234,50", 1234.5), ("1,234.50", 1234.5), ("12.500", 12500), ("1.5", 1.5)],
)
def test_interpreta_precios_con_formato_colombiano(texto, esperado):
    assert _a_numero(texto) == esperado


def test_lee_un_csv_guardado_por_excel_en_espanol(tmp_path):
    fila = "Éxito;Azúcar morena;Manuelita;Bolsa x 1 kg;1;kg;5.200;COP;Medellín;si;https://example.com/a;;2026-11-11"
    ruta = _csv(tmp_path, fila, separador=";", codificacion="cp1252")
    (oferta,) = cargar_catalogo(ruta)
    assert oferta.proveedor == "Éxito" and oferta.nombre == "Azúcar morena"
    assert oferta.precio == 5200.0 and oferta.ciudad == "Medellín"


def test_un_error_indica_archivo_y_fila(tmp_path):
    buena = "T,Arroz,,Bolsa,1,kg,4990,COP,,si,https://example.com/a,,2026-11-11"
    mala = "T,Aceite,,Botella,1,arroba,9000,COP,,si,https://example.com/b,,2026-11-11"
    with pytest.raises(ErrorCatalogo, match=r"prueba\.csv, fila 3: unidad_contenido"):
        cargar_catalogo(_csv(tmp_path, buena, mala))


def test_rechaza_filas_sin_fuente_o_sin_precio(tmp_path):
    sin_url = "T,Arroz,,Bolsa,1,kg,4990,COP,,si,,,2026-11-11"
    with pytest.raises(ErrorCatalogo, match="faltan datos obligatorios: url"):
        cargar_catalogo(_csv(tmp_path, sin_url))
    precio_cero = "T,Arroz,,Bolsa,1,kg,0,COP,,si,https://example.com/a,,2026-11-11"
    with pytest.raises(ErrorCatalogo, match="fila 2: precio"):
        cargar_catalogo(_csv(tmp_path, precio_cero))


def test_rechaza_un_archivo_sin_las_columnas_obligatorias(tmp_path):
    ruta = tmp_path / "malo.csv"
    ruta.write_text("nombre,precio\nArroz,4990\n", encoding="utf-8")
    with pytest.raises(ErrorCatalogo, match="faltan las columnas"):
        cargar_catalogo(ruta)


def test_agrupa_por_proveedor_e_ignora_filas_en_blanco(tmp_path):
    a = "Tienda A,Arroz,,Bolsa,1,kg,4990,COP,,si,https://example.com/a,,2026-11-11"
    b = "Tienda B,Arroz,,Bolsa,1,kg,5100,COP,,si,https://example.com/b,,2026-11-11"
    _csv(tmp_path, a, ",,,,,,,,,,,,", nombre="a.csv")
    _csv(tmp_path, b, nombre="b.csv")
    catalogos = cargar_catalogos(tmp_path)
    assert {p: len(o) for p, o in catalogos.items()} == {"Tienda A": 1, "Tienda B": 1}


def test_hay_variedades_que_permiten_distinguir_equivalente_de_sustituto():
    """El catálogo debe traer alguna variedad (integral, basmati) y no solo arroz blanco."""
    catalogos = cargar_catalogos(DIRECTORIO_CATALOGOS)
    nombres = " ".join(o.nombre.lower() for ofertas in catalogos.values() for o in ofertas)
    assert "integral" in nombres


def test_los_catalogos_del_proyecto_son_validos():
    # Vacíos o llenos, los CSV reales nunca deben tener filas inválidas.
    assert isinstance(cargar_catalogos(DIRECTORIO_CATALOGOS), dict)
    for nombre in ("exito.csv", "carulla.csv"):
        assert (DIRECTORIO_CATALOGOS / nombre).exists()

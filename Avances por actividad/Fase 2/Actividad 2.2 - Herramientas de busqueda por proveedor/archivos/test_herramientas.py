"""Pruebas de la búsqueda y de las herramientas (sin red, sin clave)."""
from datetime import date

import pytest

from cotizador.busqueda import buscar_ofertas, palabras_clave
from cotizador.catalogos import cargar_catalogos
from cotizador.herramientas import crear_herramienta_proveedor, crear_herramientas, nombre_herramienta
from cotizador.schemas import Oferta


def _oferta(nombre: str, precio: float, **extra) -> Oferta:
    base = dict(
        proveedor="Tienda Ficticia", nombre=nombre, presentacion="1000 gr", contenido=1000,
        unidad_contenido="g", precio=precio, url="https://example.com/p", fecha_consulta=date(2026, 11, 11),
    )
    return Oferta(**{**base, **extra})


FICTICIAS = [
    _oferta("Arroz PRUEBA blanco (1000 gr)", 5000, marca="Prueba"),
    _oferta("Arroz OTRA integral (1000 gr)", 4000, marca="Otra"),
    _oferta("Papa PRUEBA (2000 gr)", 9000, marca="Prueba"),
    _oferta("Papel higiénico PRUEBA x12 rollos", 20000, marca="Prueba", contenido=12, unidad_contenido="unidad"),
    _oferta("Huevos AA PRUEBA rojo (30 und)", 18000, contenido=30, unidad_contenido="unidad"),
    _oferta("Galletas con arroz inflado (200 gr)", 3000),
]


@pytest.mark.parametrize(
    "texto, esperado",
    [("Azúcar", ["azucar"]), ("huevos", ["huevo"]), ("papel higiénico", ["papel", "higienico"]),
     ("aceite de girasol", ["aceite", "girasol"]), ("Pastas", ["pasta"]), ("detergentes", ["detergente"])],
)
def test_palabras_clave_normaliza_tildes_plurales_y_palabras_vacias(texto, esperado):
    assert palabras_clave(texto) == esperado


def test_papa_no_coincide_con_papel():
    assert [o.nombre for o in buscar_ofertas(FICTICIAS, "papa")] == ["Papa PRUEBA (2000 gr)"]


def test_plural_y_tildes_no_impiden_encontrar():
    assert len(buscar_ofertas(FICTICIAS, "huevo")) == 1
    assert len(buscar_ofertas(FICTICIAS, "PAPEL HIGIENICO")) == 1


def test_ordena_por_relevancia_y_luego_por_precio():
    nombres = [o.nombre for o in buscar_ofertas(FICTICIAS, "arroz")]
    # Los dos arroces (más barato primero) van antes que las galletas que solo lo mencionan.
    assert nombres == [
        "Arroz OTRA integral (1000 gr)", "Arroz PRUEBA blanco (1000 gr)", "Galletas con arroz inflado (200 gr)",
    ]


def test_todas_las_palabras_deben_coincidir_incluida_la_marca():
    assert [o.marca for o in buscar_ofertas(FICTICIAS, "arroz prueba")] == ["Prueba"]
    assert buscar_ofertas(FICTICIAS, "arroz basmati") == []
    assert buscar_ofertas(FICTICIAS, "de la") == []


def test_la_herramienta_tiene_nombre_descripcion_y_esquema_para_el_modelo():
    herramienta = crear_herramienta_proveedor("Éxito", FICTICIAS)
    assert herramienta.name == "buscar_en_exito" == nombre_herramienta("Éxito")
    assert "Éxito" in herramienta.description
    assert list(herramienta.args_schema.model_json_schema()["properties"]) == ["termino"]


def test_la_herramienta_devuelve_texto_para_el_modelo_y_ofertas_para_el_codigo():
    herramienta = crear_herramienta_proveedor("Tienda Ficticia", FICTICIAS)
    # Así la llama LangGraph: con una "tool call" como las que emite el modelo.
    mensaje = herramienta.invoke(
        {"name": herramienta.name, "args": {"termino": "arroz prueba"}, "id": "llamada-1", "type": "tool_call"}
    )
    assert mensaje.tool_call_id == "llamada-1"
    assert "1 ofertas de 'arroz prueba'" in mensaje.content and "$ 5.000 COP" in mensaje.content
    assert [type(o) for o in mensaje.artifact] == [Oferta]
    assert mensaje.artifact[0].url == "https://example.com/p"


def test_sin_resultados_lo_dice_y_sugiere_reintentar():
    herramienta = crear_herramienta_proveedor("Tienda Ficticia", FICTICIAS)
    mensaje = herramienta.invoke(
        {"name": herramienta.name, "args": {"termino": "caviar"}, "id": "llamada-2", "type": "tool_call"}
    )
    assert "Sin resultados" in mensaje.content and mensaje.artifact == []


def test_hay_una_herramienta_por_proveedor_con_los_catalogos_reales():
    herramientas = crear_herramientas()
    assert [h.name for h in herramientas] == ["buscar_en_ara", "buscar_en_carulla", "buscar_en_exito"]


@pytest.mark.parametrize("termino", ["arroz", "aceite", "azúcar", "huevos", "leche", "papel higiénico"])
def test_la_canasta_basica_se_encuentra_en_exito_y_carulla(termino):
    catalogos = cargar_catalogos()
    for proveedor in ("Éxito", "Carulla"):
        assert buscar_ofertas(catalogos[proveedor], termino), f"{termino} no aparece en {proveedor}"

"""Carga de catálogos de referencia (CSV) y conversión a objetos Oferta.

Los catálogos son datos de referencia tomados de las páginas públicas de cada
tienda: cada fila conserva la URL y la fecha de consulta. Viven en
datos/catalogos/, un archivo por proveedor.

El lector tolera lo que Excel suele hacer con un CSV en español: separador
punto y coma, codificación de Windows, precios como "$ 4.990" y fechas como
"11/11/2026".

Uso:
    uv run python -m agente.catalogos        # resumen de los catálogos cargados
"""
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError

from agente.schemas import Oferta

DIRECTORIO_CATALOGOS = Path(__file__).resolve().parent.parent / "datos" / "catalogos"

COLUMNAS = [
    "proveedor", "nombre", "marca", "presentacion", "contenido", "unidad_contenido",
    "precio", "moneda", "ciudad", "disponible", "url", "id_fuente", "fecha_consulta", "nota",
]
OBLIGATORIAS = {"proveedor", "nombre", "presentacion", "precio", "url", "fecha_consulta"}

_VERDADERO = {"si", "sí", "true", "1", "disponible", "x"}
_FALSO = {"no", "false", "0", "agotado"}


class ErrorCatalogo(ValueError):
    """Una fila del catálogo no se puede interpretar. El mensaje indica archivo y fila."""


def _leer_texto(ruta: Path) -> str:
    datos = ruta.read_bytes()
    try:
        return datos.decode("utf-8-sig")  # UTF-8, con o sin marca inicial
    except UnicodeDecodeError:
        return datos.decode("cp1252")  # como guarda Excel en Windows


def _a_numero(texto: str) -> float:
    """Convierte '$ 4.990', '4,990', '1.234,50' o '12,5' a número.

    En pesos colombianos el punto separa miles: un separador seguido de
    exactamente tres cifras se toma como miles; cualquier otro, como decimal.
    """
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not re.search(r"\d", limpio):
        raise ValueError(f"'{texto}' no es un número")
    if "." in limpio and "," in limpio:
        miles, decimal = (".", ",") if limpio.rfind(",") > limpio.rfind(".") else (",", ".")
        limpio = limpio.replace(miles, "").replace(decimal, ".")
    else:
        for separador in ".,":
            partes = limpio.split(separador)
            if len(partes) > 1:
                es_miles = all(len(parte) == 3 for parte in partes[1:])
                limpio = "".join(partes) if es_miles else limpio.replace(separador, ".")
    return float(limpio)


def _a_fecha(texto: str) -> date:
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"fecha '{texto}' no válida; use AAAA-MM-DD")


def _a_disponible(texto: str):
    valor = texto.lower()
    if valor in _VERDADERO:
        return True
    if valor in _FALSO:
        return False
    if not valor:
        return None  # no verificado: no se asume que hay existencias
    raise ValueError(f"disponible '{texto}' no válido; use si, no o vacío")


def _fila_a_oferta(fila: dict) -> Oferta:
    v = {clave: (fila.get(clave) or "").strip() for clave in COLUMNAS}
    faltan = sorted(c for c in OBLIGATORIAS if not v[c])
    if faltan:
        raise ValueError(f"faltan datos obligatorios: {', '.join(faltan)}")
    return Oferta(
        proveedor=v["proveedor"],
        nombre=v["nombre"],
        marca=v["marca"] or None,
        presentacion=v["presentacion"],
        contenido=_a_numero(v["contenido"].replace(",", ".")) if v["contenido"] else None,
        unidad_contenido=v["unidad_contenido"] or None,
        precio=_a_numero(v["precio"]),
        moneda=v["moneda"] or "COP",
        ciudad=v["ciudad"] or None,
        disponible=_a_disponible(v["disponible"]),
        url=v["url"],
        id_fuente=v["id_fuente"] or None,
        fecha_consulta=_a_fecha(v["fecha_consulta"]),
        nota=v["nota"] or None,
    )


def cargar_catalogo(ruta: Path) -> list[Oferta]:
    """Lee un CSV y devuelve sus ofertas. Falla indicando archivo y fila si algo no cuadra."""
    ruta = Path(ruta)
    texto = _leer_texto(ruta)
    encabezado = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if encabezado.count(";") > encabezado.count(",") else ","

    lector = csv.DictReader(texto.splitlines(), delimiter=separador)
    columnas = {(c or "").strip() for c in (lector.fieldnames or [])}
    faltantes = sorted(OBLIGATORIAS - columnas)
    if faltantes:
        raise ErrorCatalogo(f"{ruta.name}: faltan las columnas {', '.join(faltantes)}")

    ofertas = []
    for numero, fila in enumerate(lector, start=2):  # la fila 1 es el encabezado
        fila = {(k or "").strip(): v for k, v in fila.items()}
        if not any((valor or "").strip() for valor in fila.values()):
            continue  # fila en blanco
        try:
            ofertas.append(_fila_a_oferta(fila))
        except ValidationError as error:
            detalle = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in error.errors())
            raise ErrorCatalogo(f"{ruta.name}, fila {numero}: {detalle}") from error
        except ValueError as error:
            raise ErrorCatalogo(f"{ruta.name}, fila {numero}: {error}") from error
    return ofertas


def cargar_catalogos(directorio: Path = DIRECTORIO_CATALOGOS) -> dict[str, list[Oferta]]:
    """Carga todos los CSV de un directorio y agrupa las ofertas por proveedor."""
    por_proveedor: dict[str, list[Oferta]] = {}
    for ruta in sorted(Path(directorio).glob("*.csv")):
        for oferta in cargar_catalogo(ruta):
            por_proveedor.setdefault(oferta.proveedor, []).append(oferta)
    return por_proveedor


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        catalogos = cargar_catalogos()
    except ErrorCatalogo as error:
        print(f"Catálogo con errores -> {error}")
        return 1

    archivos = sorted(DIRECTORIO_CATALOGOS.glob("*.csv"))
    print(f"Archivos CSV encontrados: {len(archivos)} ({', '.join(a.name for a in archivos) or 'ninguno'})")
    if not catalogos:
        print("Aún no hay ofertas cargadas: los catálogos están vacíos.")
        return 0
    for proveedor, ofertas in catalogos.items():
        fechas = sorted({o.fecha_consulta.isoformat() for o in ofertas})
        print(f"- {proveedor}: {len(ofertas)} ofertas | fechas de consulta: {', '.join(fechas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

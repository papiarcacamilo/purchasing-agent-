"""Búsqueda de productos en un catálogo: código puro, sin LLM.

Compara palabras normalizadas (sin tildes, en minúsculas y en singular), no
subcadenas: así "papa" no coincide con "papel" y "huevos" sí coincide con "huevo".
"""
import re
import unicodedata

from agente.schemas import Oferta

# Palabras que no ayudan a identificar un producto.
VACIAS = {"de", "del", "la", "el", "los", "las", "en", "con", "para", "por", "x", "y", "un", "una"}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Azúcar' -> 'azucar'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.lower()


def _singular(palabra: str) -> str:
    if len(palabra) > 4 and palabra.endswith("es") and not palabra.endswith(("tes", "ches")):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def palabras_clave(texto: str) -> list[str]:
    """Palabras útiles de un texto, normalizadas y en singular."""
    palabras = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [_singular(p) for p in palabras if p not in VACIAS]


def _texto_buscable(oferta: Oferta) -> list[str]:
    return palabras_clave(f"{oferta.nombre} {oferta.marca or ''}")


def coincide(oferta: Oferta, producto: str, marca: str | None = None) -> bool:
    """La oferta menciona todas las palabras del producto (y de la marca, si se exige)."""
    texto = _texto_buscable(oferta)
    exigidas = palabras_clave(producto) + (palabras_clave(marca) if marca else [])
    return bool(exigidas) and all(palabra in texto for palabra in exigidas)


def buscar_ofertas(ofertas: list[Oferta], termino: str, limite: int = 8) -> list[Oferta]:
    """Ofertas cuyo nombre o marca contienen TODAS las palabras del término.

    Se ordenan por relevancia: primero las que mencionan el término antes en el
    nombre (el producto principal) y, a igualdad, las de menor precio.
    """
    buscadas = palabras_clave(termino)
    if not buscadas:
        return []

    encontradas = []
    for oferta in ofertas:
        if coincide(oferta, termino):
            del_nombre = _texto_buscable(oferta)
            posicion = min(del_nombre.index(palabra) for palabra in buscadas)
            encontradas.append((posicion, oferta.precio, oferta))

    encontradas.sort(key=lambda fila: (fila[0], fila[1]))
    return [oferta for _, _, oferta in encontradas[:limite]]

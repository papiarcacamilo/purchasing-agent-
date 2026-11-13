"""Conversión de unidades y precio por unidad. Código puro, sin LLM.

Tres dimensiones, cada una con su unidad base:

    masa     kg, g, lb   -> base kg
    volumen  L, mL       -> base L
    conteo   unidad      -> base unidad

No se convierte entre dimensiones: 2 kg de arroz y 900 mL de aceite no son
comparables, y decirlo es parte del trabajo.

La libra se toma como 500 g, que es la libra de mercado usada en Colombia
(la libra exacta son 453,6 g; aquí se usa la comercial).
"""
from typing import Optional

from cotizador.schemas import Unidad

# unidad -> (dimensión, numerador, denominador) para llevarla a la unidad base.
# Se guarda como fracción para que 1000 g den exactamente 1 kg, sin error de coma flotante.
_A_BASE: dict[str, tuple[str, int, int]] = {
    "kg": ("masa", 1, 1),
    "g": ("masa", 1, 1000),
    "lb": ("masa", 1, 2),      # libra de mercado colombiana: 500 g
    "L": ("volumen", 1, 1),
    "mL": ("volumen", 1, 1000),
    "unidad": ("conteo", 1, 1),
}

BASE_DE_DIMENSION: dict[str, Unidad] = {"masa": "kg", "volumen": "L", "conteo": "unidad"}

NOMBRE_DIMENSION = {"masa": "peso", "volumen": "volumen", "conteo": "unidades"}


class UnidadDesconocida(ValueError):
    """La unidad no está en la tabla de conversión."""


def dimension(unidad: str) -> str:
    """'g' -> 'masa'. Falla si la unidad no se conoce."""
    if unidad not in _A_BASE:
        raise UnidadDesconocida(f"unidad '{unidad}' desconocida")
    return _A_BASE[unidad][0]


def son_comparables(una: Optional[str], otra: Optional[str]) -> bool:
    """Dos unidades son comparables si miden lo mismo (masa con masa, etc.)."""
    if una is None or otra is None:
        return False
    return una in _A_BASE and otra in _A_BASE and dimension(una) == dimension(otra)


def unidad_base(unidad: str) -> Unidad:
    """'g' -> 'kg'. La unidad en la que se expresan los precios unitarios."""
    return BASE_DE_DIMENSION[dimension(unidad)]


def a_base(cantidad: float, unidad: str) -> float:
    """Lleva una cantidad a su unidad base: 1000 g -> 1.0 (kg)."""
    _, numerador, denominador = _A_BASE[unidad] if unidad in _A_BASE else (None, 0, 0)
    if denominador == 0:
        raise UnidadDesconocida(f"unidad '{unidad}' desconocida")
    return cantidad * numerador / denominador


def convertir(cantidad: float, desde: str, hasta: str) -> float:
    """Convierte entre unidades de la MISMA dimensión: 2 kg -> 2000 g."""
    if not son_comparables(desde, hasta):
        raise UnidadDesconocida(f"no se puede convertir de '{desde}' a '{hasta}'")
    _, numerador_destino, denominador_destino = _A_BASE[hasta]
    return a_base(cantidad, desde) * denominador_destino / numerador_destino


def precio_por_unidad(precio: float, contenido: float, unidad: str) -> float:
    """Precio por kg, por L o por unidad. Falla si el contenido no es positivo."""
    en_base = a_base(contenido, unidad)
    if en_base <= 0:
        raise ValueError("el contenido debe ser mayor que cero")
    return precio / en_base


def paquetes_necesarios(cantidad_pedida: float, unidad_pedida: str, contenido: float, unidad_contenido: str) -> int:
    """Cuántos empaques enteros hacen falta. No se compra fraccionado.

    5 kg pedidos con bolsas de 3 kg -> 2 bolsas (y sobra 1 kg).
    """
    if not son_comparables(unidad_pedida, unidad_contenido):
        raise UnidadDesconocida(f"'{unidad_pedida}' y '{unidad_contenido}' no son comparables")
    pedido = a_base(cantidad_pedida, unidad_pedida)
    por_paquete = a_base(contenido, unidad_contenido)
    if por_paquete <= 0:
        raise ValueError("el contenido debe ser mayor que cero")
    faltan = pedido / por_paquete
    enteros = int(faltan)
    # Se redondea hacia arriba, con una tolerancia mínima para evitar que
    # 3 bolsas de 1 kg para 3 kg pidan una cuarta por un error de coma flotante.
    return enteros if abs(faltan - enteros) < 1e-9 else enteros + 1

"""Herramientas (tools) de búsqueda: una por proveedor, todas con la misma interfaz.

Una herramienta es una función que el LLM puede decidir llamar. Cada una tiene:
- nombre y descripción: lo que el modelo lee para decidir cuándo usarla;
- esquema de argumentos (Pydantic): lo que el modelo debe enviar;
- una función de Python que hace el trabajo real, sin LLM.

Devuelven dos cosas (response_format="content_and_artifact"):
- content : texto corto para que el modelo lea los resultados;
- artifact: la lista de objetos Oferta completos, para el resto del grafo.
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agente.busqueda import buscar_ofertas, normalizar
from agente.catalogos import cargar_catalogos
from agente.schemas import Oferta


class EntradaBusqueda(BaseModel):
    """Argumentos que el modelo debe enviar a una herramienta de búsqueda."""

    termino: str = Field(
        description=(
            "Nombre genérico del producto, sin cantidades ni unidades. "
            "Ejemplos: 'arroz', 'aceite de girasol', 'papel higiénico'. "
            "Puede incluir la marca si el usuario la exige: 'arroz diana'."
        )
    )


def _precio(valor: float) -> str:
    return "$ " + f"{valor:,.0f}".replace(",", ".")


def describir(oferta: Oferta) -> str:
    """Una oferta en una línea legible para el modelo."""
    contenido = (
        f"{oferta.contenido:g} {oferta.unidad_contenido}"
        if oferta.contenido and oferta.unidad_contenido
        else "contenido no indicado"
    )
    disponible = {True: "sí", False: "no", None: "no verificado"}[oferta.disponible]
    linea = (
        f"{oferta.nombre} | {_precio(oferta.precio)} {oferta.moneda} | {contenido} | "
        f"disponible: {disponible}"
    )
    return f"{linea} | {oferta.nota}" if oferta.nota else linea


def nombre_herramienta(proveedor: str) -> str:
    """'Éxito' -> 'buscar_en_exito'."""
    return "buscar_en_" + "_".join(normalizar(proveedor).split())


def crear_herramienta_proveedor(proveedor: str, ofertas: list[Oferta]) -> StructuredTool:
    """Fábrica: crea la herramienta de búsqueda de UN proveedor."""

    def buscar(termino: str) -> tuple[str, list[Oferta]]:
        encontradas = buscar_ofertas(ofertas, termino)
        if not encontradas:
            texto = (
                f"Sin resultados para '{termino}' en {proveedor}. "
                "Prueba con un término más general o un sinónimo."
            )
            return texto, []
        lineas = [f"{i}. {describir(o)}" for i, o in enumerate(encontradas, start=1)]
        encabezado = f"{len(encontradas)} ofertas de '{termino}' en {proveedor}:"
        return "\n".join([encabezado, *lineas]), encontradas

    return StructuredTool.from_function(
        func=buscar,
        name=nombre_herramienta(proveedor),
        description=(
            f"Busca un producto en el catálogo de referencia de {proveedor} y devuelve "
            "sus ofertas con precio, contenido y disponibilidad. Úsala una vez por producto."
        ),
        args_schema=EntradaBusqueda,
        response_format="content_and_artifact",
    )


def crear_herramientas(catalogos: dict[str, list[Oferta]] | None = None) -> list[StructuredTool]:
    """Una herramienta por cada proveedor con catálogo cargado."""
    if catalogos is None:
        catalogos = cargar_catalogos()
    return [crear_herramienta_proveedor(p, ofertas) for p, ofertas in sorted(catalogos.items())]

"""Modelos Pydantic: salida estructurada del LLM y estado compartido del grafo.

Hay dos familias de modelos y conviene no confundirlas:

- Pedido / ItemPedido: lo que DEBE devolver el LLM al interpretar la solicitud.
  Todos sus campos son obligatorios (los que pueden faltar aceptan None) y no
  admiten campos extra: así el esquema es compatible con Structured Outputs
  en modo estricto.
- EstadoCompra: la memoria compartida del grafo. Cada nodo la recibe y devuelve
  un diccionario con SOLO los campos que actualiza.
"""
import operator
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Unidades que el sistema sabe convertir. "lb" es la libra de uso comercial.
Unidad = Literal["kg", "g", "lb", "L", "mL", "unidad"]


class ItemPedido(BaseModel):
    """Un producto de la lista de compra, tal como lo pidió el usuario."""

    model_config = ConfigDict(extra="forbid")

    texto_original: str = Field(
        description="Fragmento de la solicitud que originó este ítem, sin modificar."
    )
    producto: str = Field(
        description="Nombre genérico del producto en minúsculas y singular, sin marca ni cantidad."
    )
    cantidad: Optional[float] = Field(
        description="Cantidad solicitada como número. None si el usuario no la indicó."
    )
    unidad: Optional[Unidad] = Field(
        description="Unidad de medida de la cantidad. None si el usuario no la indicó."
    )
    marca: Optional[str] = Field(
        description="Marca exigida o preferida. None si el usuario no mencionó ninguna."
    )
    presentacion: Optional[str] = Field(
        description="Presentación o empaque exigido, por ejemplo 'bolsa de 1 kg'. None si no se indicó."
    )
    observaciones: Optional[str] = Field(
        description="Otras restricciones de calidad o tipo, por ejemplo 'integral'. None si no hay."
    )


class Pedido(BaseModel):
    """Solicitud de compra completa convertida en datos estructurados."""

    model_config = ConfigDict(extra="forbid")

    items: list[ItemPedido] = Field(
        description="Productos solicitados, uno por cada artículo distinto."
    )
    ciudad: Optional[str] = Field(
        description="Ciudad o ubicación comercial de la compra. None si el usuario no la indicó."
    )
    proveedores: list[str] = Field(
        description="Proveedores que el usuario pidió consultar. Lista vacía si no nombró ninguno."
    )


class EstadoCompra(BaseModel):
    """Estado que viaja por el grafo.

    `suposiciones` e `historial` usan un reducer (operator.add): los nodos
    agregan elementos sin borrar los anteriores. El resto de campos se
    reemplaza cuando un nodo los devuelve.
    """

    texto_usuario: str = ""
    pedido: Optional[Pedido] = None
    datos_faltantes: list[str] = Field(default_factory=list)
    suposiciones: Annotated[list[str], operator.add] = Field(default_factory=list)
    historial: Annotated[list[str], operator.add] = Field(default_factory=list)

"""Modelos Pydantic: salida estructurada del LLM y estado compartido del grafo.

Hay tres familias de modelos y conviene no confundirlas:

- Pedido / ItemPedido: lo que DEBE devolver el LLM al interpretar la solicitud.
  Todos sus campos son obligatorios (los que pueden faltar aceptan None) y no
  admiten campos extra: así el esquema es compatible con Structured Outputs
  en modo estricto.
- Oferta: un precio publicado por un proveedor. No la escribe el LLM: sale de
  los catálogos, por eso sí admite valores por defecto.
- EstadoCompra: la memoria compartida del grafo. Cada nodo la recibe y devuelve
  un diccionario con SOLO los campos que actualiza.
"""
import operator
from datetime import date
from typing import Annotated, Literal, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

# Unidades que el sistema sabe convertir. "lb" es la libra de uso comercial.
Unidad = Literal["kg", "g", "lb", "L", "mL", "unidad"]

# Qué tan bien responde una oferta a lo que pidió el usuario.
Equivalencia = Literal["equivalente", "sustituto", "no_comparable"]


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


class Oferta(BaseModel):
    """Un producto publicado por un proveedor, con el origen del dato.

    Conserva todo lo que exige el enunciado: nombre, presentación, precio,
    moneda, proveedor, fuente, fecha de consulta y disponibilidad.
    """

    model_config = ConfigDict(extra="forbid")

    proveedor: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    marca: Optional[str] = None
    presentacion: str = Field(min_length=1, description="Empaque tal como lo publica la tienda.")
    contenido: Optional[float] = Field(default=None, gt=0, description="Cantidad que trae el empaque.")
    unidad_contenido: Optional[Unidad] = None
    precio: float = Field(gt=0)
    moneda: str = "COP"
    ciudad: Optional[str] = None
    disponible: Optional[bool] = Field(default=None, description="None significa no verificado.")
    url: str = Field(min_length=1, description="Página de donde se tomó el precio.")
    id_fuente: Optional[str] = Field(default=None, description="Código del producto en la tienda.")
    fecha_consulta: date
    origen: Literal["catalogo_referencia", "web"] = "catalogo_referencia"
    nota: Optional[str] = Field(default=None, description="Condición comercial, por ejemplo una oferta.")


class OfertaNormalizada(BaseModel):
    """Una oferta con su contenido llevado a la unidad base y su precio unitario.

    `comparable` dice si se puede comparar con el ítem pedido. Cuando es falso,
    `motivo` explica por qué (y así se puede informar al usuario, como pide el
    enunciado, en lugar de descartarla en silencio).
    """

    model_config = ConfigDict(extra="forbid")

    oferta: Oferta
    comparable: bool
    motivo: Optional[str] = None
    contenido_base: Optional[float] = Field(default=None, description="Contenido en kg, L o unidad.")
    unidad_base: Optional[Unidad] = None
    precio_unitario: Optional[float] = Field(default=None, description="Precio por kg, L o unidad.")
    equivalencia: Optional[Equivalencia] = None
    razon: Optional[str] = Field(default=None, description="Por qué se clasificó así.")


class ClasificacionOferta(BaseModel):
    """Cómo responde UNA oferta a lo que pidió el usuario. Lo decide el LLM."""

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(description="Número de la oferta en la lista recibida, empezando en 1.")
    equivalencia: Equivalencia = Field(
        description=(
            "equivalente: es el producto pedido y cumple todas sus restricciones. "
            "sustituto: sirve para lo mismo pero cambia una característica. "
            "no_comparable: no es el producto pedido o incumple una restricción exigida."
        )
    )
    razon: str = Field(description="Una frase breve, en español, que explique la decisión.")


class ClasificacionLote(BaseModel):
    """Salida estructurada del clasificador: una decisión por cada oferta recibida."""

    model_config = ConfigDict(extra="forbid")

    clasificaciones: list[ClasificacionOferta]


class ResultadoBusqueda(BaseModel):
    """Las ofertas encontradas para UN ítem del pedido, en todos los proveedores."""

    model_config = ConfigDict(extra="forbid")

    item: ItemPedido
    ofertas: list[Oferta] = Field(default_factory=list)
    normalizadas: list[OfertaNormalizada] = Field(default_factory=list)


class LineaPresupuesto(BaseModel):
    """Lo que hay que comprar de UN ítem en una tienda, y cuánto cuesta."""

    model_config = ConfigDict(extra="forbid")

    producto: str
    cubierto: bool
    motivo: Optional[str] = Field(default=None, description="Por qué no se pudo cubrir.")
    oferta: Optional[Oferta] = None
    equivalencia: Optional[Equivalencia] = None
    paquetes: Optional[int] = Field(default=None, description="Empaques enteros a comprar.")
    cantidad_pedida: Optional[float] = None
    cantidad_cubierta: Optional[float] = None
    sobrante: Optional[float] = Field(default=None, description="Lo que sobra por comprar empaques enteros.")
    unidad_base: Optional[Unidad] = None
    subtotal: Optional[float] = Field(default=None, description="paquetes x precio del empaque.")


class Presupuesto(BaseModel):
    """Presupuesto de una compra: en una tienda, o combinando varias.

    El envío no se conoce en los catálogos, así que `envio` queda en None y
    `total_confirmado` también: el enunciado prohíbe tratar un envío desconocido
    como cero, de modo que el único número cierto es el subtotal de productos.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(description="Nombre de la tienda, o 'Compra combinada'.")
    combinado: bool = False
    lineas: list[LineaPresupuesto] = Field(default_factory=list)
    subtotal_productos: float = 0.0
    envio: Optional[float] = Field(default=None, description="None significa no verificado.")
    total_confirmado: Optional[float] = Field(
        default=None, description="Solo se calcula si el envío está verificado."
    )
    items_cubiertos: int = 0
    items_totales: int = 0
    completo: bool = False
    sin_cotizacion: list[str] = Field(default_factory=list)
    con_sustituto: list[str] = Field(default_factory=list)
    tiendas: list[str] = Field(default_factory=list, description="Tiendas usadas (compra combinada).")


# --------------------------- El informe final ---------------------------
# Estructura del informe, independiente del formato: el mismo objeto se
# escribe en Markdown o en Word sin que puedan decir cosas distintas.

class Tabla(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encabezados: list[str]
    filas: list[list[str]] = Field(default_factory=list)


class Seccion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str
    nivel: int = 2
    parrafos: list[str] = Field(default_factory=list)
    vinetas: list[str] = Field(default_factory=list)
    tablas: list[Tabla] = Field(default_factory=list)


class Informe(BaseModel):
    """El informe como datos, antes de decidir en qué formato se escribe."""

    model_config = ConfigDict(extra="forbid")

    titulo: str
    fecha: str
    secciones: list[Seccion] = Field(default_factory=list)


class EstadoCompra(BaseModel):
    """Estado que viaja por el grafo.

    `suposiciones` e `historial` usan un reducer (operator.add): los nodos
    agregan elementos sin borrar los anteriores. El resto de campos se
    reemplaza cuando un nodo los devuelve.
    """

    texto_usuario: str = ""
    pedido: Optional[Pedido] = None
    datos_faltantes: list[str] = Field(default_factory=list)
    # Veces que el grafo ya se detuvo a preguntar. Es el tope del ciclo de
    # aclaración, igual que MAX_VUELTAS lo es del ciclo del agente buscador.
    aclaraciones: int = 0
    # ¿La última pausa trajo texto nuevo? Si no, no vale la pena volver a
    # llamar al modelo para reinterpretar lo mismo.
    hubo_respuesta: bool = False
    suposiciones: Annotated[list[str], operator.add] = Field(default_factory=list)
    historial: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Conversación del agente buscador con sus herramientas. El reducer add_messages
    # agrega los mensajes nuevos y respeta los identificadores de cada llamada.
    mensajes: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    resultados: list[ResultadoBusqueda] = Field(default_factory=list)
    proveedores_consultados: list[str] = Field(default_factory=list)
    presupuestos: list[Presupuesto] = Field(default_factory=list)
    combinado: Optional[Presupuesto] = None
    informe: Optional[Informe] = None

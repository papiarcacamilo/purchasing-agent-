"""Construcción del LLM (OpenAI) y de las cadenas con salida estructurada."""
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from langchain_core.tools import BaseTool

from cotizador.config import cargar_config
from cotizador.prompts import PROMPT_CLASIFICADOR, crear_prompt_interprete
from cotizador.schemas import ClasificacionLote, Pedido


def crear_modelo() -> ChatOpenAI:
    cfg = cargar_config()
    return ChatOpenAI(model=cfg.modelo, temperature=cfg.temperatura, api_key=cfg.api_key)


def construir_interprete(llm: Optional[BaseChatModel] = None) -> Runnable:
    """prompt | LLM con salida estructurada.

    Entrada de la cadena : {"texto_usuario": str}
    Salida de la cadena  : instancia de Pedido (validada por Pydantic)

    method="json_schema" + strict=True usa Structured Outputs de OpenAI: el
    modelo solo puede responder con un JSON que cumpla el esquema de Pedido.
    """
    llm = llm or crear_modelo()
    llm_estructurado = llm.with_structured_output(Pedido, method="json_schema", strict=True)
    return crear_prompt_interprete() | llm_estructurado


def construir_buscador(
    herramientas: list[BaseTool], llm: Optional[BaseChatModel] = None
) -> Runnable:
    """LLM con las herramientas de búsqueda enlazadas.

    Entrada : la lista de mensajes de la conversación.
    Salida  : un AIMessage que puede traer `tool_calls` (lo que el modelo quiere buscar).

    bind_tools no ejecuta nada: solo le enseña al modelo qué herramientas existen,
    con su nombre, su descripción y su esquema de argumentos.
    """
    llm = llm or crear_modelo()
    return llm.bind_tools(herramientas)


def construir_clasificador(llm: Optional[BaseChatModel] = None) -> Runnable:
    """Cadena que clasifica un lote de ofertas frente a lo que se pidió.

    Entrada : {"encargo": str} con lo pedido y la lista numerada de ofertas.
    Salida  : ClasificacionLote (una decisión por oferta, validada por Pydantic).
    """
    from langchain_core.prompts import ChatPromptTemplate

    llm = llm or crear_modelo()
    prompt = ChatPromptTemplate.from_messages(
        [("system", PROMPT_CLASIFICADOR), ("human", "{encargo}")]
    )
    return prompt | llm.with_structured_output(ClasificacionLote, method="json_schema", strict=True)

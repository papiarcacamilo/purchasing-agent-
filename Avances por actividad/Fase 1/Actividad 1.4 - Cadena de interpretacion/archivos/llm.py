"""Construcción del LLM (OpenAI) y de las cadenas con salida estructurada."""
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from cotizador.config import cargar_config
from cotizador.prompts import crear_prompt_interprete
from cotizador.schemas import Pedido


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

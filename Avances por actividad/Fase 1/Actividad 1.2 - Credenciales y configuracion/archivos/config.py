"""Carga de configuración desde variables de entorno (.env).

La clave de OpenAI nunca se escribe en el código: vive en el archivo .env,
que está excluido de git. Este módulo es el único punto que la lee.
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    # repr=False: si alguien imprime la configuración, la clave no aparece.
    api_key: str = field(repr=False)
    modelo: str
    temperatura: float


def cargar_config() -> Config:
    """Lee el .env y valida lo mínimo necesario para llamar a OpenAI."""
    # No pisa variables que ya existan en el entorno (útil en las pruebas).
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-..."):
        raise RuntimeError(
            "Falta OPENAI_API_KEY. Copia .env.example a .env y completa tu clave."
        )

    return Config(
        api_key=api_key,
        modelo=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        temperatura=float(os.getenv("OPENAI_TEMPERATURE", "0")),
    )

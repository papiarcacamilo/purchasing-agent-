"""Comprueba la configuración y la conexión con OpenAI.

Uso:
    uv run python -m cotizador.verificar

Hace una sola llamada mínima al modelo. Nunca imprime la clave.
"""
import os
import sys

import openai
from langchain_openai import ChatOpenAI

from cotizador.config import cargar_config
from cotizador.errores import explicar_error_openai


def main() -> int:
    # Git Bash en Windows no siempre usa UTF-8: lo forzamos para ver bien las tildes.
    sys.stdout.reconfigure(encoding="utf-8")

    # load_dotenv no pisa variables ya definidas: si existe una en Windows, gana esa.
    origen = (
        "variable del sistema (el .env NO se está usando)"
        if os.getenv("OPENAI_API_KEY")
        else "archivo .env"
    )

    cfg = cargar_config()
    print(f"Origen clave  : {origen}")
    print(f"Clave cargada : sí ({len(cfg.api_key)} caracteres, no se muestra)")
    print(f"Modelo        : {cfg.modelo}")
    print(f"Temperatura   : {cfg.temperatura}")

    llm = ChatOpenAI(model=cfg.modelo, temperature=cfg.temperatura, api_key=cfg.api_key)
    try:
        respuesta = llm.invoke("Responde únicamente con la palabra: OK")
    except openai.APIError as error:
        print(f"FALLO         : {explicar_error_openai(error)}")
        return 1

    uso = respuesta.usage_metadata or {}
    print(f"Respuesta     : {respuesta.content}")
    print(f"Tokens usados : {uso.get('total_tokens', 'n/d')}")
    print("Conexión con OpenAI verificada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

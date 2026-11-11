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

# Causa probable de cada error de OpenAI, en lenguaje claro.
DIAGNOSTICOS = {
    openai.AuthenticationError: (
        "OpenAI rechazo la clave (401). Esta mal copiada, fue eliminada o no es de OpenAI."
    ),
    openai.PermissionDeniedError: "La clave no tiene permiso para usar este modelo (403).",
    openai.NotFoundError: "El modelo indicado en OPENAI_MODEL no existe para esta cuenta (404).",
    openai.RateLimitError: "Sin saldo o limite de uso alcanzado en la cuenta de OpenAI (429).",
    openai.APIConnectionError: "No hay conexion con OpenAI. Revisa internet, VPN o proxy.",
}


def main() -> int:
    # load_dotenv no pisa variables ya definidas: si existe una en Windows, gana esa.
    origen = "variable del sistema (el .env NO se esta usando)" if os.getenv("OPENAI_API_KEY") else "archivo .env"

    cfg = cargar_config()
    print(f"Origen clave  : {origen}")
    print(f"Clave cargada : si ({len(cfg.api_key)} caracteres, no se muestra)")
    print(f"Modelo        : {cfg.modelo}")
    print(f"Temperatura   : {cfg.temperatura}")

    llm = ChatOpenAI(model=cfg.modelo, temperature=cfg.temperatura, api_key=cfg.api_key)
    try:
        respuesta = llm.invoke("Responde unicamente con la palabra: OK")
    except openai.APIError as error:
        causa = next(
            (texto for tipo, texto in DIAGNOSTICOS.items() if isinstance(error, tipo)),
            f"Error inesperado de OpenAI: {type(error).__name__}",
        )
        print(f"FALLO         : {causa}")
        return 1

    uso = respuesta.usage_metadata or {}
    print(f"Respuesta     : {respuesta.content}")
    print(f"Tokens usados : {uso.get('total_tokens', 'n/d')}")
    print("Conexion con OpenAI verificada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

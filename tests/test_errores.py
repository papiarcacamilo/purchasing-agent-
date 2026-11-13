"""Pruebas del traductor de errores de OpenAI (sin red)."""
import httpx
import openai
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

import main as cli
from cotizador.errores import explicar_error_openai
from cotizador.schemas import ClasificacionLote

PETICION = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _error_http(tipo, codigo: int):
    return tipo("mensaje de prueba", response=httpx.Response(codigo, request=PETICION), body=None)


def test_clave_rechazada_se_explica_como_401():
    assert "401" in explicar_error_openai(_error_http(openai.AuthenticationError, 401))


def test_sin_saldo_se_explica_como_429():
    assert "429" in explicar_error_openai(_error_http(openai.RateLimitError, 429))


def test_sin_conexion_se_explica_sin_codigo():
    assert "conexión" in explicar_error_openai(openai.APIConnectionError(request=PETICION))


def test_main_muestra_una_linea_clara_y_no_una_traza(monkeypatch, capsys):
    def falla(_):
        raise _error_http(openai.AuthenticationError, 401)

    # Se sustituye el intérprete real por uno que falla como una clave rechazada.
    # El buscador también se inyecta: así nada del grafo pide la clave.
    grafo_real = cli.construir_grafo
    sin_busqueda = RunnableLambda(lambda _: AIMessage(content="no busco nada"))
    sin_clasificar = RunnableLambda(lambda _: ClasificacionLote(clasificaciones=[]))
    monkeypatch.setattr(
        cli,
        "construir_grafo",
        lambda: grafo_real(
            interprete=RunnableLambda(falla), buscador=sin_busqueda, clasificador=sin_clasificar
        ),
    )
    monkeypatch.setattr("sys.argv", ["main.py", "--texto", "5 kg de arroz"])

    assert cli.main() == 1
    salida = capsys.readouterr().out
    assert "No se pudo consultar el modelo" in salida and "401" in salida

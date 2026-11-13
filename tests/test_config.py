"""Pruebas de la configuración: sin red y sin usar la clave real."""
import pytest

from agente.config import cargar_config


def test_falla_si_no_hay_clave(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError):
        cargar_config()


def test_falla_si_la_clave_es_la_del_ejemplo(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-...")
    with pytest.raises(RuntimeError):
        cargar_config()


def test_lee_modelo_y_temperatura_del_entorno(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-clave-falsa-de-prueba")
    monkeypatch.setenv("OPENAI_MODEL", "modelo-de-prueba")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.3")
    cfg = cargar_config()
    assert cfg.modelo == "modelo-de-prueba"
    assert cfg.temperatura == 0.3


def test_la_clave_no_aparece_al_imprimir_la_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-clave-falsa-de-prueba")
    cfg = cargar_config()
    assert "sk-clave-falsa-de-prueba" not in repr(cfg)

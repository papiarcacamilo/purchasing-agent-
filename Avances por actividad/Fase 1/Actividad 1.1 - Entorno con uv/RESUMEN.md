# Fase 1 · Actividad 1.1: Entorno del proyecto con uv

**Fecha:** 10 de noviembre de 2026 · **Estado:** completada y validada

## Objetivo
Dejar instaladas las librerías del proyecto en un entorno virtual reproducible,
en la misma generación de versiones que el repositorio de clase.

## Concepto
- `pyproject.toml` declara lo que pedimos (dependencias y versiones mínimas).
- `uv.lock` registra lo que se instaló (versión exacta de cada paquete).
- `.venv/` es el entorno virtual local; no se sube al repositorio.
- `uv run <comando>` ejecuta dentro del entorno sin tener que activarlo.

## Qué se hizo
1. Se crearon `pyproject.toml` y `.python-version` (Python 3.12).
2. En Git Bash, dentro de `Entregable 4 final`, se ejecutó `uv sync`.
3. Se validaron las importaciones con `uv run`.

## Comandos ejecutados
```bash
cd "/c/Users/JOARM/Downloads/REPO IA/Entregable 4 final"
uv sync
uv run python -c "from importlib.metadata import version as v; print('langgraph', v('langgraph')); print('langchain-openai', v('langchain-openai')); print('pydantic', v('pydantic'))"
```

## Resultado de la validación
```
langgraph 1.2.20
langchain-openai 1.7.4
pydantic 2.14.3
```

| Componente | Versión |
|---|---|
| Python | 3.12 |
| uv | 0.13.7 |
| langgraph | 1.2.20 |
| langchain-core | 1.7.7 |
| langchain-openai | 1.7.4 |
| openai | 3.49.0 |
| pydantic | 2.14.3 |
| python-dotenv | 1.2.4 |
| pytest | 9.2.0 |

## Archivos de esta actividad
- `archivos/pyproject.toml` y `archivos/.python-version`: copia de cómo quedaron al cerrar la actividad.
- `uv.lock` y `.venv/` están en la raíz del proyecto (los genera `uv`; no se copian aquí).

## Aprendizaje
Separar "lo que pido" (`pyproject.toml`) de "lo que se instaló" (`uv.lock`) permite que
cualquier persona reproduzca el mismo entorno con un solo comando: `uv sync`.

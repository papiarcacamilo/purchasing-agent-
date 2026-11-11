# Fase 1 · Actividad 1.2: Credenciales y configuración

**Fecha:** 10 de noviembre de 2026 · **Estado:** validada salvo la conexión con OpenAI (pendiente de una clave válida)

## Objetivo
Que el proyecto lea la clave de OpenAI de forma segura y comprobar la conexión con una llamada mínima.

## Concepto
Una variable de entorno es un dato que vive fuera del código. La clave se guarda en `.env`,
que git ignora, y el programa la lee al arrancar. El código puede ser público sin exponerla.

## Qué se hizo
1. `cotizador/config.py`: único punto que lee el `.env`. Falla con un mensaje claro si falta la clave
   y la oculta al imprimir la configuración (`repr=False`).
2. `cotizador/verificar.py`: llamada mínima al modelo; informa el origen de la clave y explica
   cada tipo de error en una línea. Nunca imprime la clave.
3. `tests/test_config.py`: cuatro pruebas sin red y sin clave real.
4. Se creó `.env` a partir de `.env.example` (solo en el equipo local).

## Comandos ejecutados
```bash
cp .env.example .env
notepad .env
git check-ignore -v .env
git status --short
uv run pytest -q
uv run python -m cotizador.verificar
```

## Resultado de la validación
| Comprobación | Resultado |
|---|---|
| `git check-ignore -v .env` | `.gitignore:2:.env` (git lo ignora) |
| `git status --short` | Muestra `cotizador/` y `tests/`; no muestra `.env` |
| `uv run pytest -q` | `4 passed` |
| `uv run python -m cotizador.verificar` | Error 401: OpenAI rechazó la clave suministrada |

## Pendiente para cerrar
Conseguir una clave válida (se consultó al profesor; alternativa: crédito propio de 5 USD)
y repetir `uv run python -m cotizador.verificar` hasta obtener `Conexion con OpenAI verificada.`

## Aprendizaje
- La seguridad se comprueba, no se supone: `git check-ignore` demuestra que `.env` no se subirá.
- Un error 401 es de credenciales, no de código: el programa leyó y envió la clave correctamente.
- Las pruebas con `monkeypatch` validan la configuración sin tocar la clave real.

## Archivos de esta actividad
Copia en `archivos/`: `config.py`, `verificar.py`, `test_config.py`, `.env.example`.
El archivo `.env` no se copia ni se sube.

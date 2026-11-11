# Fase 1 · Actividad 1.4: Cadena de interpretación

**Fecha:** 11 de noviembre de 2026 · **Estado:** validada sin clave (18 pruebas y prompt revisado); pendiente la prueba con el modelo real

## Objetivo
Tener la cadena que convierte una solicitud en lenguaje natural en un `Pedido` estructurado.

## Concepto
Una cadena de LangChain es una tubería: la salida de cada pieza es la entrada de la siguiente.

```
{"texto_usuario": "..."}  ->  prompt  ->  LLM con salida estructurada  ->  Pedido
```

- Prompt: plantilla con instrucciones fijas y un hueco `{texto_usuario}`.
- Salida estructurada: el modelo solo puede responder un JSON que cumpla el esquema `Pedido`.

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/prompts.py` | Instrucciones para extraer ítems, ciudad y proveedores |
| `cotizador/llm.py` | Crea el modelo y arma la cadena `prompt | llm_estructurado` |
| `cotizador/demo.py` | Muestra el prompt o ejecuta la cadena desde la terminal |
| `tests/test_interprete.py` | Seis pruebas sin red ni clave |

Decisiones del prompt:
- No inventar: lo que el usuario no dijo se responde como `null`, para que el nodo de validación sepa qué preguntar.
- El texto del usuario es dato y no instrucción: va en un mensaje aparte y delimitado (defensa contra inyección).
- Tres ejemplos de casos frontera: docenas, medias libras y productos sin cantidad.
- Un número de empaques ("2 botellas de 1 litro") se registra como cantidad en `unidad` y el tamaño va en `presentacion`.

## Comandos de validación
```bash
uv run pytest -q
uv run python -m cotizador.demo --prompt "30 huevos y 1 queso para Bogota"
```

## Resultado de la validación (11 nov 2026, Git Bash)
- `18 passed in 2.70s` (12 anteriores y 6 nuevas).
- `demo --prompt` imprimió dos mensajes: `system` (2719 caracteres, con las instrucciones y los tres ejemplos)
  y `human` (62 caracteres) con `30 huevos y 1 queso para Bogota` entre triple comilla.
- Las tildes se muestran bien en Git Bash gracias a `sys.stdout.reconfigure(encoding="utf-8")`.

## Pendiente para cerrar
Con una clave válida: `uv run python -m cotizador.demo "30 huevos y 1 queso para Bogota"`
y comprobar que el modelo devuelve huevo 30 unidad, queso 1 unidad y ciudad Bogotá.

## Aprendizaje
- El operador `|` une piezas que comparten la interfaz Runnable: la salida de una es la entrada de la otra.
- Ver el prompt formateado antes de gastar tokens permite revisar exactamente qué recibirá el modelo.
- Probar la tubería con un modelo falso separa los errores de código de los errores del LLM.

## Archivos de esta actividad
Copia en `archivos/`: `prompts.py`, `llm.py`, `demo.py`, `test_interprete.py`.

# Fase 1 · Actividad 1.3: Esquemas Pydantic

**Fecha:** 10 de noviembre de 2026 · **Estado:** completada y validada

## Objetivo
Definir la forma del pedido y del estado del grafo, y probar que rechazan datos inválidos.

## Concepto
Un esquema Pydantic es un contrato de datos: qué campos existen, de qué tipo son y qué valores
se aceptan. Con un LLM, obliga al modelo a responder con una estructura exacta.

| Modelo | Qué es | Quién lo llena |
|---|---|---|
| `Pedido` / `ItemPedido` | Lo que el LLM debe devolver | El LLM |
| `EstadoCompra` | La memoria compartida del grafo | Los nodos |

## Qué se hizo
`cotizador/schemas.py` con tres modelos:

- `ItemPedido`: `texto_original`, `producto`, `cantidad`, `unidad`, `marca`, `presentacion`, `observaciones`.
- `Pedido`: `items`, `ciudad`, `proveedores`.
- `EstadoCompra`: `texto_usuario`, `pedido`, `datos_faltantes`, `suposiciones`, `historial`.

Decisiones de diseño:
- `Unidad = Literal["kg", "g", "lb", "L", "mL", "unidad"]`: solo se aceptan unidades que el sistema sabe convertir.
- Campos opcionales sin valor por defecto: el LLM debe responder siempre, aunque sea `None`.
  Así se distingue "el usuario no lo dijo" de "el modelo lo olvidó", y el esquema es válido
  para Structured Outputs en modo estricto.
- `extra="forbid"`: no se admiten campos inventados.
- `suposiciones` e `historial` usan un reducer (`operator.add`): los nodos agregan sin borrar.

## Comandos ejecutados
```bash
uv run pytest -q
uv run python -c "from cotizador.schemas import ItemPedido; ItemPedido(texto_original='2 arrobas de papa', producto='papa', cantidad=2, unidad='arroba', marca=None, presentacion=None, observaciones=None)"
```

## Resultado de la validación
- `12 passed in 2.68s` (4 de configuración y 8 de esquemas).
- El segundo comando falló a propósito, como se esperaba:
  `Input should be 'kg', 'g', 'lb', 'L', 'mL' or 'unidad' [type=literal_error, input_value='arroba']`

## Aprendizaje
- Las descripciones de cada campo son instrucciones que el LLM lee para llenarlo.
- Un `ValidationError` es el contrato funcionando: el dato inválido no entra al sistema.
- El estado del grafo se actualiza por partes; el reducer decide si un campo se reemplaza o se acumula.

## Archivos de esta actividad
Copia en `archivos/`: `schemas.py`, `test_schemas.py`.

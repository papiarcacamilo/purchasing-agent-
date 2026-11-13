# Fase 3 · Actividad 3.1: Normalización de unidades y precio unitario

**Fecha:** 12 de noviembre de 2026 · **Estado:** completada y validada

## Objetivo
Convertir el contenido de cada oferta a una unidad común y calcular su precio por kg, por L
o por unidad, para poder comparar presentaciones distintas.

## Concepto
Dos ofertas del mismo producto no se pueden comparar si vienen en empaques distintos:
una bolsa de 1 kg a $6.790 y otra de 5 kg a $21.950 no se comparan por el precio de la
etiqueta. Hay que llevarlas a una **unidad base** y calcular el **precio unitario**.

Tres dimensiones, cada una con su unidad base:

| Dimensión | Unidades | Base |
|---|---|---|
| masa | kg, g, lb | kg |
| volumen | L, mL | L |
| conteo | unidad | unidad |

No se convierte entre dimensiones: 2 kg de arroz y 900 mL de aceite no son comparables,
y decirlo es parte del trabajo.

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/unidades.py` | Conversiones, precio unitario y cálculo de paquetes enteros |
| `cotizador/nodos/normalizar.py` | Nodo `normalizar_ofertas` del grafo |
| `cotizador/schemas.py` | Modelo `OfertaNormalizada` y campo `normalizadas` en `ResultadoBusqueda` |
| `tests/test_unidades.py` | 14 pruebas de las conversiones |
| `tests/test_normalizar.py` | 8 pruebas del nodo |

## Decisiones aplicadas (acordadas con el equipo)
1. **La libra son 500 g**: la libra de mercado colombiana, no la libra exacta de 453,6 g.
   Queda documentado en el módulo.
2. **Las conversiones se guardan como fracción** (numerador y denominador), no como decimal.
   Así 1000 g dan exactamente 1 kg, sin error de coma flotante.
3. **No se descarta lo no comparable**: se marca `comparable = False` con un motivo legible
   ("la tienda no publica el contenido del empaque"), porque el enunciado pide informarlo.
4. **Los paquetes se redondean hacia arriba**: no se compra fraccionado. Para 5 kg con bolsas
   de 3 kg hacen falta 2 bolsas. La función ya está lista para la actividad 3.3.

## Comandos de validación
```bash
uv run pytest -q
uv run python main.py --mermaid
uv run python main.py --texto "Necesito 2 kg de arroz y 30 huevos. Consulta Exito y Carulla."
```

## Resultado de la validación
- `115 passed` (93 anteriores y 22 nuevas).
- El grafo ya incluye `recolectar_ofertas --> normalizar_ofertas --> __end__`.
- Comprobación con los catálogos reales, para 2 kg de arroz:

```
Éxito    Arroz ROA blanco fortiplus (3000 gr)       $  9.650  ->  $ 3.217 por kg
Carulla  Arroz ROA blanco fortiplus (3000 gr)       $  9.650  ->  $ 3.217 por kg
Éxito    Arroz EXITO MARCA PROPIA blanco (5000 gr)  $ 16.300  ->  $ 3.260 por kg
Carulla  Arroz CARULLA blanco (2500 gr)             $  8.150  ->  $ 3.260 por kg
Éxito    Arroz DIANA blanco vitamor (3000 gr)       $ 12.900  ->  $ 4.300 por kg
```

El más barato de etiqueta (Carulla, $8.150) **no** es el más barato por kilo. Eso es
exactamente lo que el enunciado pide poder distinguir.

## Aprendizaje
- El precio de la etiqueta engaña: solo el precio por unidad permite comparar.
- Guardar las conversiones como fracción evita errores de coma flotante que, al redondear
  paquetes, harían comprar uno de más.
- Marcar lo no comparable con su motivo es más útil que descartarlo: el informe final podrá
  decir por qué una oferta no entró en la comparación.

## Archivos de esta actividad
Copia en `archivos/`: `unidades.py`, `normalizar.py`, `schemas.py`, `test_unidades.py`,
`test_normalizar.py`.

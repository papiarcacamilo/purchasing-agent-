# Fase 3 · Actividad 3.2: Clasificación de equivalencia

**Fecha:** 12 de noviembre de 2026 · **Estado:** completada, validada y probada con el modelo real

## Objetivo
Decidir si cada oferta es el producto pedido, algo que sirve para lo mismo, o algo que no
responde al pedido.

## Concepto
Es un juicio de lenguaje, no de aritmética: hay que entender qué es cada producto. Lo hace
el LLM con salida estructurada.

| Valor | Significado | Ejemplo (se pidió "arroz integral") |
|---|---|---|
| equivalente | Es el producto pedido y cumple lo exigido | Arroz DIANA integral |
| sustituto | Sirve para lo mismo, cambia una característica | Arroz DIANA blanco |
| no_comparable | No es el producto, o incumple una restricción exigida | Galletas de arroz inflado |

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/prompts.py` | `PROMPT_CLASIFICADOR` y `encargo_de_clasificacion` |
| `cotizador/llm.py` | `construir_clasificador` con salida estructurada estricta |
| `cotizador/nodos/clasificar.py` | Nodo `clasificar_equivalencia` |
| `cotizador/schemas.py` | `ClasificacionOferta`, `ClasificacionLote` y campos en `OfertaNormalizada` |
| `tests/test_clasificar.py` | 11 pruebas |

Decisiones para no gastar saldo:
- **Clasificación por lotes**: una llamada por producto con todas sus ofertas numeradas,
  no una llamada por oferta.
- **No se le pregunta lo ya decidido**: las ofertas que la normalización marcó como no
  comparables (sin contenido publicado) llevan su motivo técnico y no se envían al modelo.
- **Tope por proveedor**, con una excepción importante (ver más abajo).

## Lo que enseñó probar con el modelo real
Se probó con *"2 kg de arroz integral y 1 litro de aceite de girasol"*, un caso elegido a
propósito para forzar la diferencia entre equivalente y sustituto. Aparecieron cuatro
problemas, en cuatro ejecuciones sucesivas:

| # | Problema observado | Causa | Corrección |
|---|---|---|---|
| 1 | Las botellas de 900 mL se rechazaban por "no cumplir la exigencia" | El intérprete guardó "1 litro" como presentación EXIGIDA | Regla y ejemplo en el prompt del intérprete: la cantidad que se quiere comprar nunca es la presentación |
| 2 | Ninguna oferta de arroz quedaba como equivalente | El catálogo no tenía arroz integral: al armarlo se seleccionaron 6 de los 16 arroces de Carulla | Se agregaron 4 productos reales que faltaban, con su URL |
| 3 | Una botella de 900 mL se marcaba sustituto al pedir 1 litro | El modelo castigaba el tamaño del empaque | Regla explícita + ejemplos resueltos en el prompt del clasificador |
| 4 | Éxito quedó sin ninguna oferta de arroz | El agente buscó "arroz integral", no encontró nada y no reintentó | Se endureció la regla 3 del buscador: DEBE reintentar con el término general |

También se mejoró `seleccionar_candidatas`: una oferta que cumple una restricción exigida
(marca, presentación u observaciones) **siempre** se clasifica, aunque no esté entre las
más baratas de su tienda. Lo barato no es necesariamente lo que cumple.

### Diagnóstico equivocado, y su corrección
El problema 2 se atribuyó primero al tope por proveedor ("el integral era el quinto más
barato y quedaba fuera"). Al comprobarlo con el código, sin LLM, resultó falso: ese arroz
nunca había entrado al CSV. La mejora al tope se conservó porque es correcta por sí misma,
pero no era la causa. Queda anotado: conviene comprobar una hipótesis antes de darla por buena.

## Comandos de validación
```bash
uv run pytest -q
uv run python main.py --texto "Necesito 2 kg de arroz integral y 1 litro de aceite de girasol. Consulta Exito y Carulla."
```

## Resultado de la validación
- `129 passed`.
- Última ejecución con el modelo real: 21 ofertas, 2 vueltas del agente (reintentó en Éxito),
  5 equivalentes y 2 sustitutos. El arroz integral de Carulla sale como equivalente y las
  botellas de 900 mL también.

## Limitación conocida
Con *"aceite de girasol"* sin marca exigida, el modelo marca a veces otra marca como
sustituto en lugar de equivalente. No afecta al presupuesto (esas ofertas son más caras por
litro y el cálculo prefiere las equivalentes), y errar hacia sustituto es el error seguro:
el prompt dice que ante la duda se elija sustituto.

## Aprendizaje
- Con un LLM, **los ejemplos pesan más que las reglas**. La regla "el tamaño del empaque no
  influye" se ignoró; el ejemplo con una botella de 900 mL sí funcionó.
- Un prompt no se escribe de una vez: se corrige mirando lo que el modelo hace de verdad.
- Antes de culpar al modelo conviene revisar los datos: dos de los cuatro problemas estaban
  en el catálogo y en el intérprete, no en el clasificador.

## Archivos de esta actividad
Copia en `archivos/`: `clasificar.py`, `prompts.py`, `llm.py`, `schemas.py`, `test_clasificar.py`.

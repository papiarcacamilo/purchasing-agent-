# Fase 2 · Actividad 2.2: Herramientas de búsqueda por proveedor

**Fecha:** 12 de noviembre de 2026 · **Estado:** completada y validada

## Objetivo
Dar al agente una herramienta de búsqueda por cada proveedor, para que pueda consultar
precios por sí mismo en lugar de que el código decida qué consultar.

## Concepto
Una **herramienta** (tool) es una función que el LLM puede decidir llamar. No la ejecuta él:
devuelve una "llamada a herramienta" con los argumentos, el programa la ejecuta y le entrega
el resultado. El modelo decide *qué* buscar; el código hace la búsqueda real.

Cada herramienta tiene cuatro partes:

| Parte | Para qué | En nuestro caso |
|---|---|---|
| Nombre | El modelo lo usa para llamarla | `buscar_en_exito`, `buscar_en_carulla`, `buscar_en_ara` |
| Descripción | El modelo la lee para decidir cuándo usarla | "Busca un producto en el catálogo de X..." |
| Esquema de argumentos | Lo que el modelo debe enviar (Pydantic) | `termino: str` |
| Función | El trabajo real, sin LLM | Buscar en la lista de `Oferta` |

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/busqueda.py` | Búsqueda por palabras normalizadas (sin tildes, minúsculas, singular) |
| `cotizador/herramientas/catalogo.py` | Fábrica que crea una herramienta por proveedor |
| `cotizador/herramientas/__main__.py` | Prueba manual desde la terminal, sin clave |
| `tests/test_herramientas.py` | 20 pruebas de la búsqueda y de las herramientas |

Decisiones de diseño:
- **Se comparan palabras, no subcadenas.** Por eso "papa" no trae "papel higiénico" y
  "huevos" sí encuentra "Huevos ... (30 und)". Las tildes y los plurales se normalizan.
- **Todas las palabras del término deben aparecer**: "arroz diana" solo trae arroz de esa marca.
- **Orden por relevancia y luego por precio**: primero los productos cuyo nombre empieza por
  el término (el producto principal), y entre ellos el más barato primero.
- **Dos salidas** (`response_format="content_and_artifact"`): un texto corto que lee el modelo
  y la lista de objetos `Oferta` completos, con URL y fecha, para el resto del grafo.
- **Sin resultados no es un error**: la herramienta lo dice y sugiere reintentar con otro término,
  para que el agente pueda corregir en la actividad 2.3.

## Corrección a la actividad 2.1
Al verificar el folleto de Ara a resolución completa se encontraron errores de lectura en seis
filas (`ara.csv`): tamaño del arroz Diana, harina Haz de Oros, panela, galleta Saltín Noel,
y un aceite que en realidad eran dos productos distintos (soya x 3.000 ml y canola/oliva x 900 ml).
Se corrigieron y se añadieron los precios regulares. Ara pasó de 13 a 16 ofertas.

## Comandos de validación
```bash
uv run pytest -q
uv run python -m cotizador.herramientas "arroz"
uv run python -m cotizador.herramientas "papa"
```

## Resultado de la validación
- `64 passed` (44 anteriores y 20 nuevas).
- `herramientas "arroz"` devuelve 2 ofertas en Ara, 6 en Carulla y 6 en Éxito, ordenadas por precio.
- `herramientas "papa"` NO devuelve papel higiénico: la búsqueda por palabras funciona.

## Aprendizaje
- Una herramienta es tanto su descripción como su código: si el modelo no entiende cuándo
  usarla, no la usa. El texto de la descripción es parte del diseño.
- Comparar subcadenas es el error típico en búsquedas de catálogo ("papa" dentro de "papel").
- Separar el texto que lee el modelo del objeto que usa el código evita que el LLM tenga que
  repetir datos (y equivocarse al copiar precios o URLs).

## Archivos de esta actividad
Copia en `archivos/`: `busqueda.py`, `catalogo.py`, `__init__.py`, `__main__.py`,
`test_herramientas.py` y el `ara.csv` corregido.

# Fase 2 · Actividad 2.1: Modelo de oferta y lector de catálogos

**Fecha:** 11-12 de noviembre de 2026 · **Estado:** completada y validada

## Objetivo
Definir qué es una oferta y poder cargar catálogos CSV reales, rechazando filas mal formadas.

## Concepto
- Capa de datos: separa de dónde vienen los precios de cómo se usan. El resto del sistema
  solo conoce objetos `Oferta`; no le importa si vinieron de un CSV, una API o una página web.
- Trazabilidad: cada precio viaja con su origen (URL y fecha), lo que el enunciado llama
  "fuentes verificables".

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/schemas.py` | Nuevo modelo `Oferta` con los campos que exige el enunciado |
| `cotizador/catalogos.py` | Lee los CSV y los convierte en ofertas; tolera el formato de Excel en español |
| `datos/catalogos/exito.csv` | 52 productos reales de exito.com |
| `datos/catalogos/carulla.csv` | 50 productos reales de carulla.com |
| `datos/catalogos/ara.csv` | 13 productos del folleto público de Ara (Bogotá) |
| `datos/catalogos/README.md` | Explica columnas, fuentes y cómo comprobar los datos |
| `tests/test_catalogos.py` | 16 pruebas con una tienda ficticia |

## Recolección de precios (11 nov 2026)
- Se revisó primero el `robots.txt` de exito.com, carulla.com y aratiendas.com.
  Éxito y Carulla permiten el rastreo de categorías y productos (bloquean /api, /checkout,
  búsqueda interna y facetas). Ara bloquea /wp-admin y algunas rutas internas, no las de contenido.
- Éxito y Carulla: precios tomados de las páginas públicas de categoría y de producto, con
  `url` directa e `id_fuente` (SKU). Se usó el precio general ("Otros"), no el de tarjeta aliada.
- Ara no publica precios por producto en línea; se tomaron del folleto público "Ahorro ara"
  (Bogotá), vigente del 12 al 18 de noviembre. Dos ítems del folleto se vendían por peso, sin
  precio fijo publicado: se omitieron para no inventar un valor.
- Verificación cruzada: se comprobó una muestra contra el JSON-LD de la propia página.
  Sal Refisal Éxito $2.910 y café Sello Rojo Carulla $19.725 coincidieron exactamente.

## Decisiones de diseño
- `Oferta` guarda: proveedor, nombre, marca, presentación, contenido + unidad, precio, moneda,
  ciudad, disponibilidad, url, id_fuente, fecha_consulta, origen y nota.
- `disponible` vacío significa "no verificado", no "disponible": lo desconocido no se asume.
- El lector tolera separador `;`, codificación de Windows, precios `$ 4.990` y fechas `11/11/2026`.
- Los errores indican archivo y número de fila.

## Comandos de validación
```bash
uv run pytest -q
uv run python -m cotizador.catalogos
```

## Resultado de la validación
- `44 passed`.
- `cotizador.catalogos` carga 3 archivos: Éxito 52, Carulla 50, Ara 13 ofertas, fecha 2026-11-11.

## Aprendizaje
- Una capa de datos con una interfaz común (`Oferta`) permite mezclar fuentes muy distintas
  (dos tiendas en línea y un folleto) sin que el resto del sistema lo note.
- "Fuentes verificables" no es un adorno: guardar url + fecha permite comprobar cada precio.
- Lo que no se sabe (disponibilidad, precio por peso) se deja explícito, no se rellena.

## Archivos de esta actividad
Copia en `archivos/`: `schemas.py`, `catalogos.py`, `test_catalogos.py`, `tienda_ficticia.csv`,
los tres catálogos y el README.

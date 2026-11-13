# Fase 3 · Actividad 3.4: Cuaderno de recorrido del sistema

**Fecha:** 12 de noviembre de 2026 · **Estado:** creado y validado sin clave

## Objetivo
Tener un cuaderno Jupyter que recorra el sistema completo, pieza por pieza, para probarlo
y para entregárselo al profesor junto con el código.

## Por qué un cuaderno
El repositorio de clase trae `notebooks/quejas.ipynb`, que explica su sistema paso a paso.
Este cuaderno es el equivalente para el cotizador: permite ver y ejecutar cada pieza por
separado antes de correr el grafo entero.

## Decisión de diseño
El cuaderno **no vuelve a escribir el código**: importa el paquete `cotizador` y muestra el
fuente real con `inspect.getsource()`. Así lo que se lee en el cuaderno es exactamente lo que
corre en producción, y no se desincroniza cuando el código cambia.

## Contenido (39 celdas)
| Sección | Qué muestra | ¿Gasta clave? |
|---|---|---|
| 0 | Preparación y comprobación del `.env` | No |
| 1 | Modelos Pydantic; una unidad inválida se rechaza en vivo | No |
| 2 | Los tres catálogos y una oferta por dentro | No |
| 3 | Búsqueda por palabras ("papa" no trae "papel") y las herramientas | No |
| 4 | Conversión de unidades y precio por kg con datos reales | No |
| 5 | El prompt formateado y la cadena de interpretación | Sí |
| 6 | Nodos y estado; el nodo probado con una cadena falsa | No |
| 7 | El grafo completo y su diagrama | No |
| 8 | Ejecución de extremo a extremo, con la traza de nodos | Sí |
| 9 | Las ofertas clasificadas | — |
| 10 | El presupuesto por tienda y la compra combinada | — |
| 11 | Las pruebas automáticas | No |

Cada sección marcada *(sin clave)* funciona sin `OPENAI_API_KEY`.

## Cómo se ejecuta
```bash
uv sync                               # instala ipykernel
# En VS Code: abrir notebooks/cotizador.ipynb y elegir el kernel de .venv
# O con Jupyter, sin cambiar las dependencias:
uv run --with jupyterlab jupyter lab
```

## Validación
Se ejecutaron todas las celdas que no requieren clave: 18 de 18 corren sin error.
El dibujo del grafo usa el servicio mermaid.ink; si no hay internet, el cuaderno cae al
código Mermaid en texto, como hace el cuaderno del profesor.

## Cambio en el proyecto
Se agregó `ipykernel` al grupo `dev` de `pyproject.toml`.

## Archivos de esta actividad
Copia en `archivos/`: `cotizador.ipynb`, `pyproject.toml`.

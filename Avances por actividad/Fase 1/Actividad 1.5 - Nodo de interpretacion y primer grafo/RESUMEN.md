# Fase 1 · Actividad 1.5: Nodo de interpretación y primer grafo

**Fecha:** 11 de noviembre de 2026 · **Estado:** validada sin clave; pendiente la ejecución con el modelo real

## Objetivo
Tener el primer nodo funcionando dentro de un grafo real que se ejecuta de principio a fin.

## Concepto
Un nodo de LangGraph es una función de Python: recibe el estado y devuelve un diccionario con
solo los campos que cambia. Es el puente entre el grafo y la cadena de la actividad 1.4.

| | Cadena | Nodo |
|---|---|---|
| Qué es | Tubería de LangChain | Función de Python |
| Recibe | `{"texto_usuario": "..."}` | El `EstadoCompra` completo |
| Devuelve | Un `Pedido` | `{"pedido": ..., "historial": [...]}` |

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/nodos/interpretar.py` | Nodo `interpretar_pedido`, creado con una fábrica que recibe la cadena |
| `cotizador/grafo.py` | Grafo: inicio -> interpretar_pedido -> fin |
| `main.py` | Entrada por consola: `--texto` y `--mermaid` |
| `cotizador/errores.py` | Traduce los errores de OpenAI a una causa en una línea |
| `tests/test_grafo.py` | Seis pruebas del nodo y del grafo con un LLM falso |
| `tests/test_errores.py` | Cuatro pruebas del traductor de errores |

Decisiones:
- Inyección de dependencias: la cadena entra por parámetro, así el nodo se prueba sin clave.
- Si el texto llega vacío, el nodo no llama al modelo (no gasta tokens).
- `main.py`, `demo.py` y `verificar.py` muestran una línea clara cuando OpenAI falla, en lugar de la traza completa.

## Comandos ejecutados
```bash
uv run pytest -q
uv run python main.py --mermaid
uv run python main.py --texto "Necesito 5kg de arroz y 30 huevos"
```

## Resultado de la validación (11 nov 2026, Git Bash)
- `main.py --mermaid` imprimió el diagrama con `__start__ --> interpretar_pedido;` e `interpretar_pedido --> __end__;`.
- `main.py --texto ...` llegó hasta el nodo `interpretar_pedido` y falló con error 401 de OpenAI:
  el grafo funciona; la clave suministrada es la que se rechaza.
- Pruebas automáticas: 28 en total tras agregar el traductor de errores (24 al cerrar el nodo).

## Pendiente para cerrar
Con una clave válida: `uv run python main.py --texto "Necesito 5 kg de arroz y 30 huevos para Medellin"`.

## Aprendizaje
- El nodo no hace el trabajo de lenguaje: lo delega en la cadena y solo actualiza el estado.
- La traza del error mostró el recorrido completo: `main.py` -> grafo -> nodo -> cadena -> OpenAI.
  Leerla de abajo hacia arriba indica dónde falló realmente (la autenticación) y no en nuestro código.
- Un programa para usuarios debe explicar el fallo en una línea, no mostrar la traza.

## Archivos de esta actividad
Copia en `archivos/`: `interpretar.py`, `__init__.py`, `grafo.py`, `main.py`, `errores.py`, `test_grafo.py`, `test_errores.py`.

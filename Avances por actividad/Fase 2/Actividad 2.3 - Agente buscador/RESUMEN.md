# Fase 2 · Actividad 2.3: El agente buscador

**Fecha:** 12 de noviembre de 2026 · **Estado:** completada, validada y probada con el modelo real

## Objetivo
Que el agente consulte cada producto en cada proveedor y deje las ofertas agrupadas por ítem,
con su URL y su fecha.

## Concepto
Es el primer nodo con **ciclo**. Hasta ahora los nodos eran lineales; aquí:

1. El agente responde con *llamadas a herramientas*, no con texto. No las ejecuta él.
2. El `ToolNode` las ejecuta y devuelve las ofertas.
3. El agente vuelve a mirar: si falta algo pide más búsquedas; si no, responde sin pedir nada.
4. Una arista condicional (`enrutar_busqueda`) decide si el ciclo sigue o termina.

Esto es la *orquestación* que pide el enunciado: el LLM dirige, el código ejecuta.

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/prompts.py` | `PROMPT_BUSCADOR` y `encargo_de_busqueda` (el mensaje inicial) |
| `cotizador/llm.py` | `construir_buscador`: el LLM con las herramientas enlazadas (`bind_tools`) |
| `cotizador/nodos/buscar.py` | `preparar_busqueda`, `agente_buscador` y `recolectar_ofertas` |
| `cotizador/routers.py` | `enrutar_busqueda`: la arista condicional del ciclo |
| `cotizador/grafo.py` | Grafo completo con el ciclo y el `ToolNode` |
| `main.py` | Muestra las ofertas encontradas por producto |
| `tests/test_buscador.py` | 15 pruebas del ciclo con un modelo falso |

## Las cuatro protecciones del nodo
Por ser el nodo principal se diseñó con cuatro resguardos:

1. **El encargo lo arma el código.** La lista de productos y de herramientas se construye en
   Python, no la escribe el modelo: así no se le puede "olvidar" un producto.
2. **Tope de vueltas** (`MAX_VUELTAS = 4`). Si el agente insiste en pedir búsquedas, el router
   corta el ciclo. Sin esto, un modelo confundido gastaría saldo en bucle.
3. **Red de seguridad.** Si un ítem queda sin ofertas, el código hace la búsqueda directa.
   El enunciado exige consultar al menos dos proveedores: eso no puede depender del modelo.
   Queda anotado en el historial cuando se usa.
4. **El modelo no toca los precios.** La herramienta devuelve texto para el modelo y objetos
   `Oferta` para el código. El LLM nunca copia un precio ni una URL.

Además `preparar_busqueda` respeta los proveedores que nombre el usuario y, si pide uno sin
catálogo (por ejemplo Jumbo), lo registra como limitación en lugar de fallar.

## Cambios en el estado
`EstadoCompra` creció con tres campos:
- `mensajes`: la conversación del agente con sus herramientas (reducer `add_messages`).
- `resultados`: una lista de `ResultadoBusqueda` (ítem + sus ofertas).
- `proveedores_consultados`: en qué tiendas se buscó.

## Comandos de validación
```bash
uv run pytest -q
uv run python main.py --mermaid
uv run python main.py --texto "Necesito 2 kg de arroz, 1 litro de aceite y 30 huevos. Consulta Exito y Carulla."
```

## Resultado de la validación
- `81 passed` (64 anteriores y 17 nuevas).
- El diagrama muestra el ciclo: `agente_buscador -.-> herramientas` y `herramientas --> agente_buscador`
  (ver `grafo.mmd` en esta carpeta).

### Ejecución con el modelo real (12 nov 2026)
Solicitud: *"Necesito 2 kg de arroz, 1 litro de aceite y 30 huevos. Consulta Exito y Carulla."*

```
[interpretar_pedido]  3 items | ciudad: sin indicar | proveedores: Exito, Carulla
[preparar_busqueda]   proveedores a consultar: Éxito, Carulla
[agente_buscador]     vuelta 1: 9 búsquedas solicitadas
[agente_buscador]     el agente dio por terminada la búsqueda
[recolectar_ofertas]  40 ofertas del agente en 3 proveedores; 40 asignadas a 3 items
```

El agente resolvió todo en **una sola vuelta**, pidiendo las búsquedas en paralelo, y el ciclo
se cerró solo. Se encontraron 14 ofertas de arroz, 15 de aceite y 11 de huevos, cada una con
su precio y su enlace.

## Fallo detectado y corregido
Esa misma ejecución mostró un fallo: el usuario pidió consultar **Éxito y Carulla**,
`preparar_busqueda` lo respetó, pero el agente hizo 9 búsquedas (3 productos x 3 tiendas) e
incluyó Ara. El nodo del agente listaba *todas* las herramientas sin mirar la decisión previa.

Se corrigió en tres capas:
1. El encargo ahora lista solo las herramientas de los proveedores elegidos.
2. El prompt lo dice explícitamente (regla 1b).
3. La recolección descarta cualquier oferta de un proveedor no consultado y lo anota
   en el historial.

Dos pruebas nuevas cubren el caso, incluida una en la que el modelo desobedece la instrucción
y el código lo corrige de todos modos.

## Nota
Se actualizaron tres pruebas de la Fase 1 que asumían que el grafo terminaba en
`interpretar_pedido`; ahora continúa hasta `recolectar_ofertas`.

## Aprendizaje
- Un ciclo en un grafo necesita siempre una condición de salida y un tope: el modelo puede
  no llegar nunca a la condición por sí solo.
- Conviene separar lo que decide el LLM (qué término buscar) de lo que debe garantizarse
  siempre (que se consulten dos proveedores). Lo segundo va en código.
- Una decisión tomada en un nodo no llega sola al siguiente: hay que pasarla por el estado
  Y hacerla cumplir. El agente ignoró la elección de proveedores porque nadie se la dijo.
- Probar con el modelo real encuentra fallos que las pruebas con modelo falso no ven: el
  guion de la prueba hacía lo correcto, el modelo real no.

## Archivos de esta actividad
Copia en `archivos/`: `buscar.py`, `routers.py`, `grafo.py`, `prompts.py`, `llm.py`,
`main.py` y `test_buscador.py`. Además `grafo.mmd` con el diagrama generado.

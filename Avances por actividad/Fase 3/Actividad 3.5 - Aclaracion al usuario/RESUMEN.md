# Fase 3 · Actividad 3.5: Aclaración al usuario con `interrupt()`

**Fecha:** 13 de noviembre de 2026 · **Estado:** implementada y validada · **Decisión:** D3

## Objetivo
Que el agente se detenga a preguntar cuando le falta un dato para cotizar bien,
en vez de seguir adelante suponiendo. Es la decisión D3, aprobada el 11 de
noviembre y pendiente hasta hoy.

## Concepto: qué es `interrupt()`
No es un `input()`. `interrupt()` **guarda el estado completo del grafo y sale**,
entregando una pregunta a quien lo invocó. El grafo se reanuda con
`Command(resume=<respuesta>)`: la ejecución vuelve a entrar en el mismo nodo y
`interrupt()` devuelve esa respuesta como si nunca hubiera habido una pausa.

Quien responde puede ser una consola, un cuaderno, una API o un chat, y puede
tardar un segundo o un día. Para que el estado se pueda guardar y recuperar hace
falta un **checkpointer** al compilar el grafo.

## Dos tipos de hueco
La distinción es el centro del diseño:

| | Ejemplo | Qué se hace |
|---|---|---|
| **Dato faltante** | "necesito arroz" (¿cuánto?) | Se detiene el grafo y se pregunta |
| **Suposición** | no dijo la ciudad | Se sigue y se declara en el informe |

Sin la cantidad no se puede elegir cuántos paquetes comprar. Sin la ciudad sí se
puede cotizar: los precios de catálogo son los publicados en línea. Interrumpir a
alguien por un dato que no cambia el resultado es ruido.

## Nuevo flujo
```
START -> interpretar_pedido -> validar_pedido
         validar_pedido  <-> pedir_aclaracion    (ciclo de aclaración)
         validar_pedido   -> preparar_busqueda -> ...
```
Dos ciclos, los dos con tope: `MAX_ACLARACIONES = 2` y `MAX_VUELTAS = 4`.

## Decisiones técnicas
- **D37 — La validación es determinista.** No se le pregunta al modelo si el
  pedido está completo; se comprueba con código. El modelo ya hizo su trabajo
  (texto → datos); decidir si esos datos alcanzan es una regla del negocio.
- **D38 — Falta vs. suposición**, como arriba.
- **D39 — Tras la respuesta se reinterpreta la solicitud completa.** La respuesta
  se suma al texto original y vuelve a pasar por el intérprete. Cuesta una llamada
  al modelo, pero evita escribir un segundo analizador de lenguaje solo para las
  respuestas.
- **D40 — El checkpointer es opcional.** Se comprobó qué pasa sin él: el grafo
  **no se rompe**, devuelve `__interrupt__` con lo que necesita y se detiene; lo
  que no puede es reanudarse. Así las pruebas de cableado siguen corriendo sin
  `thread_id`.
- Una sola función, `necesita_aclaracion()`, decide la regla; la usan el nodo y
  la arista condicional, para que no puedan discrepar.

## Archivos
| Archivo | Papel |
|---|---|
| `cotizador/nodos/validar.py` | Qué falta y qué se declara |
| `cotizador/nodos/aclarar.py` | La pausa y la pregunta |
| `cotizador/ejecutar.py` | Atiende las pausas y reanuda |
| `cotizador/routers.py` | `enrutar_validacion` |
| `cotizador/schemas.py` | Campo `aclaraciones` (tope del ciclo) |
| `cotizador/grafo.py` | Cableado y `checkpointer` |
| `main.py` | Usa `ejecutar()`; imprime los supuestos |

## Validación
17 pruebas nuevas, **158 en total**, todas sin red ni clave. Cubren:
qué cuenta como faltante, el nodo, la arista, el tope, el ciclo completo con
pausa y reanudación reales, el caso del usuario que no responde, y el
comportamiento sin checkpointer.

Dos pruebas anteriores se actualizaron (no se borraron): el diagrama ahora pasa
por `validar_pedido`, y la prueba de errores intercepta el grafo donde se
construye ahora.

## Lo que esto aporta a la Fase 4
El informe debe declarar las condiciones no verificadas. Ahora el estado trae
`suposiciones` y `datos_faltantes` llenados por el propio grafo, con el texto
listo para el informe, en vez de redactarlos a mano al final.

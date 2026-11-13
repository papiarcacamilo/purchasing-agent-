# Fase 3 · Actividad 3.3: Cálculo del presupuesto

**Fecha:** 12 de noviembre de 2026 · **Estado:** completada, validada y probada con el modelo real

## Objetivo
Convertir las ofertas comparadas y clasificadas en un presupuesto: compra completa en cada
tienda, alternativa combinada, faltantes y envío declarado.

## Concepto
La decisión central no es obvia: **cuál empaque conviene comprar**. No es el de mejor precio
por kilo, sino el que minimiza el costo de lo que se pidió. Para 2 kg de arroz:

| Opción | Precio por kilo | Lo que se paga por 2 kg |
|---|---|---|
| Bolsa de 5 kg a $21.950 | $4.390 (el mejor) | 1 bolsa = $21.950 |
| Bolsa de 1 kg a $6.790 | $6.790 | 2 bolsas = $13.580 |

El de mejor precio por kilo cuesta $8.370 más, porque obliga a llevar 5 kg. El precio
unitario sirve para comparar; el costo total es el que decide.

## Qué se hizo
| Archivo | Qué hace |
|---|---|
| `cotizador/presupuesto.py` | Elección de empaque, paquetes, totales y compra combinada |
| `cotizador/nodos/presupuestar.py` | Nodo `calcular_presupuesto` |
| `cotizador/schemas.py` | `LineaPresupuesto` y `Presupuesto` |
| `main.py` | Imprime el presupuesto por tienda y la combinada |
| `tests/test_presupuesto.py` | 11 pruebas |

## Reglas aplicadas
1. **Paquetes enteros**: no se compra fraccionado; se informa el sobrante.
2. **Menor costo de lo pedido**, no mejor precio unitario (ver el ejemplo de arriba).
3. **Primero el equivalente**: un sustituto solo se usa si no hay equivalente, y queda marcado.
4. **Envío desconocido no es cero**: queda como no verificado y entonces no hay total
   confirmado, solo subtotal de productos.
5. **La combinada solo se ofrece si aporta**: si ninguna tienda sola tiene todo, o si sale
   más barata. Si no aporta, se dice.

## Comandos de validación
```bash
uv run pytest -q
uv run python main.py --texto "Necesito 2 kg de arroz, 1 litro de aceite de girasol y 30 huevos. Consulta Exito y Carulla."
```

## Resultado de la validación (12 nov 2026)
`140 passed`. Con el modelo real, 31 ofertas y 3 productos:

```
--- Éxito ---
  arroz          : 1 x Arroz ROA blanco fortiplus (3000 gr)     $  9.650  (sobran 1 kg)
  aceite girasol : 2 x Aceite FRESCAMPO botella (900 ml)        $ 15.980  (sobran 0,8 L)
  huevo          : 1 x Huevos A SMN rojo (30 und)               $ 14.490
  Subtotal productos: $ 40.120   Envío: no verificado

--- Carulla ---
  arroz          : 1 x Arroz CARULLA blanco (2500 gr)           $  8.150  (sobran 0,5 kg)
  aceite girasol : 2 x Aceite FRESCAMPO botella (900 ml)        $ 15.980  (sobran 0,8 L)
  huevo          : 1 x Huevos AA SMN rojo (30 und)              $ 17.900
  Subtotal productos: $ 42.030   Envío: no verificado

--- Compra combinada ---
  arroz  [Carulla] $ 8.150 | aceite [Carulla] $ 15.980 | huevo [Éxito] $ 14.490
  Subtotal productos: $ 38.620   Envío: no verificado
```

### Comprobación manual de las cuentas
- Arroz en Éxito: 3 kg cubren los 2 pedidos con 1 bolsa; la alternativa de 2 bolsas de 1 kg
  costaría $13.580, así que $9.650 es correcto.
- Aceite: 900 mL no cubren 1 L, por eso 2 botellas ($15.980) y sobran 0,8 L. La botella de
  2.000 mL cuesta $16.990, es decir $1.010 más: la elección es correcta.
- Sumas: 9.650 + 15.980 + 14.490 = 40.120; 8.150 + 15.980 + 17.900 = 42.030;
  8.150 + 15.980 + 14.490 = 38.620. Todas cuadran.
- La compra combinada ahorra $1.500 frente a la tienda más barata.

## Aprendizaje
- El mejor precio por unidad no es la mejor compra: depende de cuánto se necesita.
- Declarar lo que no se sabe (el envío) es parte del resultado, no una omisión.
- Tener las cuentas en código puro permite comprobarlas a mano, una por una, sin depender
  de lo que diga el modelo.

## Archivos de esta actividad
Copia en `archivos/`: `presupuesto.py`, `presupuestar.py`, `schemas.py`, `main.py`,
`test_presupuesto.py`.

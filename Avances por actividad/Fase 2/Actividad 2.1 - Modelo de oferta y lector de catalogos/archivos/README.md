# Catálogos de referencia

Cada archivo CSV contiene precios tomados de las **páginas públicas** de un proveedor.
Son **datos de referencia**: reflejan lo publicado en la fecha de consulta de cada fila
y pueden haber cambiado después. No se obtienen de APIs internas ni eludiendo protecciones.

Un archivo por proveedor: `exito.csv`, `carulla.csv`.

## Columnas

| Columna | Obligatoria | Ejemplo | Descripción |
|---|---|---|---|
| `proveedor` | Sí | Éxito | Nombre del comercio |
| `nombre` | Sí | Arroz blanco | Nombre del producto como lo publica la tienda |
| `marca` | No | Diana | Marca |
| `presentacion` | Sí | Bolsa x 1000 g | Empaque tal como aparece |
| `contenido` | No | 1000 | Cantidad que trae el empaque |
| `unidad_contenido` | No | g | Una de: kg, g, lb, L, mL, unidad |
| `precio` | Sí | 4990 | Precio publicado. Acepta `4990`, `4.990` o `$ 4.990` |
| `moneda` | No | COP | Si se deja vacía se asume COP |
| `ciudad` | No | Medellín | Ciudad para la que se consultó el precio |
| `disponible` | No | si | `si`, `no` o vacío (vacío significa no verificado) |
| `url` | Sí | https://... | Página de donde se tomó el dato |
| `id_fuente` | No | 123456 | Código del producto en la tienda (PLU o SKU) |
| `fecha_consulta` | Sí | 2026-11-11 | Día en que se consultó. Formato AAAA-MM-DD |

Sin `contenido` y `unidad_contenido` no se puede calcular el precio por unidad:
esa oferta se marcará como no comparable.

## Comprobar los catálogos

```bash
uv run python -m cotizador.catalogos
```

Si alguna fila tiene un error, el mensaje indica el archivo y el número de fila.

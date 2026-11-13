"""Nodo final: redacta la recomendación y arma el informe.

El reparto de trabajo es deliberado:

- Las tablas, los totales y los enlaces los arma el código (`informe.py`), a
  partir del estado. No pasan por el modelo.
- El modelo escribe solo el párrafo de recomendación, y recibe las cifras ya
  calculadas.
- Después, el código **comprueba** que cada cifra de dinero que aparece en ese
  párrafo exista entre las calculadas. Si alguna no cuadra, se descarta el
  párrafo y se usa uno escrito por código.

Así el informe no puede afirmar un precio que el agente no haya calculado.
"""
import re
from datetime import date
from typing import Optional

from langchain_core.runnables import Runnable

from agente.informe import construir_informe, enumerar, pesos
from agente.prompts import encargo_de_recomendacion
from agente.schemas import EstadoCompra

# Solo se verifican los números grandes: son los precios. Las cantidades
# pequeñas ("2 kg", "3 productos") no son cifras de dinero y exigirlas en la
# lista de permitidas produciría falsos positivos.
MINIMO_VERIFICABLE = 1000


def _numeros(texto: str) -> set[int]:
    """Extrae los números del texto: '$ 23.590' y '23590' dan 23590."""
    encontrados = set()
    for bruto in re.findall(r"\d[\d.,]*", texto):
        limpio = bruto.replace(".", "").replace(",", "")
        if limpio.isdigit():
            encontrados.add(int(limpio))
    return encontrados


def cifras_calculadas(state: EstadoCompra) -> set[int]:
    """Todo valor de dinero que el agente calculó y que es lícito citar."""
    permitidas: set[int] = set()
    presupuestos = list(state.presupuestos) + ([state.combinado] if state.combinado else [])

    subtotales = []
    for presupuesto in presupuestos:
        subtotales.append(presupuesto.subtotal_productos)
        permitidas.add(round(presupuesto.subtotal_productos))
        for linea in presupuesto.lineas:
            if linea.subtotal is not None:
                permitidas.add(round(linea.subtotal))
            if linea.oferta is not None:
                permitidas.add(round(linea.oferta.precio))

    # Las diferencias entre opciones: "ahorra $1.500" es una cifra legítima.
    for uno in subtotales:
        for otro in subtotales:
            permitidas.add(round(abs(uno - otro)))

    for resultado in state.resultados:
        for normalizada in resultado.normalizadas:
            permitidas.add(round(normalizada.oferta.precio))
            if normalizada.precio_unitario is not None:
                permitidas.add(round(normalizada.precio_unitario))
    return permitidas


def cifras_inventadas(texto: str, state: EstadoCompra) -> list[int]:
    """Cifras de dinero del texto que el agente nunca calculó."""
    permitidas = cifras_calculadas(state)
    return sorted(
        numero
        for numero in _numeros(texto)
        if numero >= MINIMO_VERIFICABLE and numero not in permitidas
    )


def resumen_para_el_modelo(state: EstadoCompra) -> list[str]:
    """Las cifras ya calculadas, en frases cortas que el modelo solo explica."""
    lineas = []
    for presupuesto in state.presupuestos:
        lineas.append(
            f"{presupuesto.nombre}: subtotal {pesos(presupuesto.subtotal_productos)}, "
            f"cubre {presupuesto.items_cubiertos} de {presupuesto.items_totales} productos."
        )
    if state.combinado:
        lineas.append(
            f"Compra combinada en {enumerar(state.combinado.tiendas)}: subtotal "
            f"{pesos(state.combinado.subtotal_productos)}, cubre "
            f"{state.combinado.items_cubiertos} de {state.combinado.items_totales} productos."
        )
    else:
        lineas.append("No hay compra combinada que mejore a comprar todo en una sola tienda.")

    sin_cotizacion = sorted({p for b in state.presupuestos for p in b.sin_cotizacion})
    if sin_cotizacion:
        lineas.append("Sin cotización en alguna tienda: " + ", ".join(sin_cotizacion) + ".")
    sustitutos = sorted({p for b in state.presupuestos for p in b.con_sustituto})
    if sustitutos:
        lineas.append("Resueltos con un sustituto: " + ", ".join(sustitutos) + ".")
    lineas.append("El costo de envío no está verificado en ningún proveedor.")
    return lineas


def recomendacion_por_codigo(state: EstadoCompra) -> str:
    """Recomendación sin modelo. Es el respaldo y la referencia de lo correcto."""
    completos = [p for p in state.presupuestos if p.completo]
    candidatos = completos or list(state.presupuestos)
    if not candidatos:
        return (
            "No fue posible armar un presupuesto con los proveedores consultados, "
            "de modo que no hay una compra que recomendar."
        )

    mejor = min(candidatos, key=lambda p: p.subtotal_productos)
    partes = [
        f"Con los precios consultados, la opción más económica en una sola tienda es "
        f"{mejor.nombre}, con un subtotal de {pesos(mejor.subtotal_productos)} por "
        f"{mejor.items_cubiertos} de {mejor.items_totales} productos."
    ]
    if state.combinado:
        diferencia = mejor.subtotal_productos - state.combinado.subtotal_productos
        partes.append(
            f"Repartir la compra entre {enumerar(state.combinado.tiendas)} baja el "
            f"subtotal a {pesos(state.combinado.subtotal_productos)}, es decir "
            f"{pesos(diferencia)} menos, pero obliga a comprar en más de una tienda."
        )
    partes.append(
        "El costo de envío no está verificado en ningún proveedor, así que el total "
        "definitivo debe confirmarse al momento de la compra."
    )
    return " ".join(partes)


def crear_nodo_redactar_informe(redactor: Optional[Runnable] = None, hoy: Optional[date] = None):
    """Fábrica: recibe la cadena que redacta la recomendación."""

    def redactar_informe(state: EstadoCompra) -> dict:
        respaldo = recomendacion_por_codigo(state)
        historial = []

        if redactor is None or not state.presupuestos:
            recomendacion = respaldo
            historial.append("[redactar_informe] recomendación escrita por código")
        else:
            escrito = str(
                redactor.invoke({"encargo": encargo_de_recomendacion(resumen_para_el_modelo(state))})
            ).strip()
            inventadas = cifras_inventadas(escrito, state)
            if not escrito:
                recomendacion = respaldo
                historial.append("[redactar_informe] el modelo no devolvió texto; se usó el respaldo")
            elif inventadas:
                # No se corrige el texto: se descarta. Un párrafo con una cifra
                # falsa no es recuperable editándolo.
                recomendacion = respaldo
                historial.append(
                    "[redactar_informe] descartada la redacción del modelo: cifras no "
                    f"calculadas {inventadas}; se usó el respaldo"
                )
            else:
                recomendacion = escrito
                historial.append("[redactar_informe] recomendación redactada y verificada")

        informe = construir_informe(
            state, recomendacion=recomendacion, fecha=str(hoy or date.today())
        )
        historial.append(f"[redactar_informe] informe con {len(informe.secciones)} secciones")
        return {"informe": informe, "historial": historial}

    return redactar_informe

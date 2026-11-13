"""Arma el informe final a partir del estado del grafo.

El informe se construye en dos pasos:

1. `construir_informe` convierte el estado en una estructura de secciones,
   párrafos y tablas. Es código puro: con las mismas entradas da siempre el
   mismo resultado, y no llama al modelo.
2. Un renderizador la escribe en Markdown (aquí) o en Word (`informe_word`).

Separarlo así tiene una razón: las cifras del informe no pueden depender de lo
que redacte un LLM. El modelo solo escribe el párrafo de recomendación, y lo
recibe ya calculado. Todo lo demás son datos del estado, copiados sin
reinterpretar.

Las ofertas se numeran [1], [2], ... y los enlaces van al final, en "Fuentes".
Así las tablas caben en una página y cada precio queda rastreable.
"""
from typing import Optional

from agente.schemas import EstadoCompra, Informe, Oferta, Presupuesto, Seccion, Tabla

SIN_DATO = "—"


def pesos(valor: Optional[float]) -> str:
    """Formato colombiano: 9650.0 -> '$ 9.650'."""
    if valor is None:
        return SIN_DATO
    return "$ " + f"{valor:,.0f}".replace(",", ".")


def enumerar(nombres: list[str]) -> str:
    """['Carulla', 'Éxito'] -> 'Carulla y Éxito'."""
    if not nombres:
        return SIN_DATO
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + f" y {nombres[-1]}"


def cantidad(valor: Optional[float], unidad: Optional[str]) -> str:
    if valor is None:
        return SIN_DATO
    return f"{valor:g} {unidad}" if unidad else f"{valor:g}"


class Fuentes:
    """Numera las ofertas citadas para que los enlaces vayan al final."""

    def __init__(self) -> None:
        self._por_url: dict[str, int] = {}
        self.lista: list[Oferta] = []

    def cita(self, oferta: Optional[Oferta]) -> str:
        if oferta is None or not oferta.url:
            return SIN_DATO
        if oferta.url not in self._por_url:
            self.lista.append(oferta)
            self._por_url[oferta.url] = len(self.lista)
        return f"[{self._por_url[oferta.url]}]"


# --------------------------- las seis salidas ---------------------------

def _seccion_solicitud(estado: EstadoCompra) -> Seccion:
    filas = []
    if estado.pedido:
        for item in estado.pedido.items:
            exigencias = [
                t for t in (item.marca, item.presentacion, item.observaciones) if t
            ]
            filas.append([
                item.producto,
                cantidad(item.cantidad, item.unidad),
                ", ".join(exigencias) or SIN_DATO,
            ])
    seccion = Seccion(
        titulo="1. Solicitud y productos identificados",
        parrafos=[f"Solicitud recibida: «{estado.texto_usuario.strip()}»"],
        tablas=[Tabla(encabezados=["Producto", "Cantidad pedida", "Condiciones"], filas=filas)],
    )
    ciudad = estado.pedido.ciudad if estado.pedido else None
    seccion.parrafos.append(
        f"Ciudad indicada: {ciudad or 'no indicada'}. "
        f"Proveedores consultados: {', '.join(estado.proveedores_consultados) or 'ninguno'}."
    )
    return seccion


def _seccion_ofertas(estado: EstadoCompra, fuentes: Fuentes) -> list[Seccion]:
    secciones = [
        Seccion(
            titulo="2. Ofertas encontradas",
            parrafos=[
                "Cada oferta se llevó a una unidad común para poder compararlas. "
                "La columna «Clasificación» indica si responde a lo pedido: equivalente, "
                "sustituto o no comparable."
            ],
        )
    ]
    for resultado in estado.resultados:
        filas = []
        for normalizada in resultado.normalizadas:
            oferta = normalizada.oferta
            unitario = (
                f"{pesos(normalizada.precio_unitario)} / {normalizada.unidad_base}"
                if normalizada.comparable and normalizada.precio_unitario is not None
                else normalizada.motivo or SIN_DATO
            )
            filas.append([
                oferta.proveedor,
                oferta.nombre,
                pesos(oferta.precio),
                unitario,
                normalizada.equivalencia or SIN_DATO,
                fuentes.cita(oferta),
            ])
        titulo = f"2.{len(secciones)} {resultado.item.producto} ({len(filas)} ofertas)"
        seccion = Seccion(titulo=titulo, nivel=3)
        if filas:
            seccion.tablas.append(
                Tabla(
                    # El nombre del catálogo ya trae la presentación entre
                    # paréntesis: una columna aparte repetiría el dato y haría
                    # la tabla más ancha de lo que cabe en una página.
                    encabezados=[
                        "Proveedor", "Producto", "Precio",
                        "Precio por unidad", "Clasificación", "Fuente",
                    ],
                    filas=filas,
                )
            )
        else:
            seccion.parrafos.append(
                "Sin resultados en los proveedores consultados."
            )
        secciones.append(seccion)
    return secciones


def _tabla_presupuesto(presupuesto: Presupuesto, fuentes: Fuentes) -> Tabla:
    filas = []
    for linea in presupuesto.lineas:
        if not linea.cubierto:
            filas.append([
                linea.producto, "SIN COTIZACIÓN", SIN_DATO, SIN_DATO,
                linea.motivo or SIN_DATO, SIN_DATO,
            ])
            continue
        empaque = linea.oferta.nombre
        if presupuesto.combinado:
            empaque = f"{empaque} ({linea.oferta.proveedor})"
        nota = "sustituto" if linea.equivalencia == "sustituto" else ""
        if linea.sobrante:
            sobra = f"sobran {linea.sobrante:g} {linea.unidad_base}"
            nota = f"{nota}; {sobra}" if nota else sobra
        filas.append([
            linea.producto,
            empaque,
            str(linea.paquetes),
            pesos(linea.subtotal),
            nota or SIN_DATO,
            fuentes.cita(linea.oferta),
        ])
    return Tabla(
        encabezados=["Producto", "Empaque elegido", "Paquetes", "Subtotal", "Nota", "Fuente"],
        filas=filas,
    )


def _seccion_por_proveedor(estado: EstadoCompra, fuentes: Fuentes) -> list[Seccion]:
    secciones = [
        Seccion(
            titulo="3. Compra completa por proveedor",
            parrafos=[
                "Para cada tienda se eligió el empaque que minimiza el costo de la "
                "cantidad pedida, no el de mejor precio por unidad: comprar un empaque "
                "grande con mejor precio por kilo puede costar más que cubrir lo pedido "
                "con empaques pequeños."
            ],
        )
    ]
    for presupuesto in estado.presupuestos:
        cobertura = f"{presupuesto.items_cubiertos} de {presupuesto.items_totales} productos"
        secciones.append(
            Seccion(
                titulo=f"3.{len(secciones)} {presupuesto.nombre} — {pesos(presupuesto.subtotal_productos)}",
                nivel=3,
                parrafos=[f"Cubre {cobertura}."],
                tablas=[_tabla_presupuesto(presupuesto, fuentes)],
            )
        )
    return secciones


def _seccion_combinada(estado: EstadoCompra, fuentes: Fuentes) -> Seccion:
    seccion = Seccion(titulo="4. Alternativa combinada")
    if estado.combinado is None:
        seccion.parrafos.append(
            "Comprar en varias tiendas no mejora el resultado: la mejor tienda por sí "
            "sola cubre lo mismo al mismo precio o menos, y repartir la compra añadiría "
            "un segundo envío."
        )
        return seccion
    combinado = estado.combinado
    mejor_sola = min(
        (p.subtotal_productos for p in estado.presupuestos if p.completo), default=None
    )
    seccion.parrafos.append(
        f"Repartiendo la compra entre {enumerar(combinado.tiendas)} el subtotal baja a "
        f"{pesos(combinado.subtotal_productos)}."
    )
    if mejor_sola is not None:
        diferencia = mejor_sola - combinado.subtotal_productos
        seccion.parrafos.append(
            f"Frente a la mejor tienda por separado ({pesos(mejor_sola)}), la diferencia "
            f"es de {pesos(diferencia)}. Esa diferencia no incluye el envío, que no está "
            "verificado y que aquí serían dos envíos en lugar de uno."
        )
    seccion.tablas.append(_tabla_presupuesto(combinado, fuentes))
    return seccion


def _seccion_totales(estado: EstadoCompra) -> Seccion:
    filas = []
    for presupuesto in list(estado.presupuestos) + (
        [estado.combinado] if estado.combinado else []
    ):
        filas.append([
            presupuesto.nombre,
            pesos(presupuesto.subtotal_productos),
            pesos(presupuesto.envio) if presupuesto.envio is not None else "no verificado",
            pesos(presupuesto.total_confirmado)
            if presupuesto.total_confirmado is not None
            else "no se puede calcular",
        ])
    return Seccion(
        titulo="5. Totales y costos adicionales",
        parrafos=[
            "Los catálogos consultados no publican el costo de envío. Siguiendo el "
            "enunciado, un envío desconocido no se trata como cero: el subtotal de "
            "productos es el único valor confirmado, y el total definitivo queda "
            "pendiente de verificar el envío en el momento de la compra."
        ],
        tablas=[
            Tabla(
                encabezados=["Opción", "Subtotal productos", "Envío", "Total confirmado"],
                filas=filas,
            )
        ],
    )


def _seccion_pendientes(estado: EstadoCompra) -> Seccion:
    seccion = Seccion(titulo="6. Productos sin cotización y condiciones no verificadas")

    sin_cotizacion = sorted(
        {p for presupuesto in estado.presupuestos for p in presupuesto.sin_cotizacion}
    )
    if sin_cotizacion:
        seccion.vinetas.append(
            "Sin cotización en algún proveedor: " + ", ".join(sin_cotizacion) + "."
        )
    sustitutos = sorted(
        {p for presupuesto in estado.presupuestos for p in presupuesto.con_sustituto}
    )
    if sustitutos:
        seccion.vinetas.append(
            "Resueltos con un sustituto, no con el producto exacto: "
            + ", ".join(sustitutos)
            + "."
        )
    seccion.vinetas.extend(estado.suposiciones)
    if estado.datos_faltantes:
        seccion.vinetas.append(
            "Datos que el usuario no aclaró: " + "; ".join(estado.datos_faltantes) + "."
        )
    seccion.vinetas.append(
        "El costo de envío no está verificado en ningún proveedor."
    )
    return seccion


def _seccion_recomendacion(texto: str) -> Seccion:
    return Seccion(titulo="7. Recomendación", parrafos=[texto])


def _seccion_fuentes(fuentes: Fuentes) -> Seccion:
    seccion = Seccion(
        titulo="8. Fuentes consultadas",
        parrafos=[
            "Cada precio de este informe proviene de una de estas fuentes, con la fecha "
            "en que se consultó."
        ],
    )
    filas = [
        [
            f"[{numero}]",
            oferta.proveedor,
            oferta.nombre,
            oferta.url or SIN_DATO,
            str(oferta.fecha_consulta),
        ]
        for numero, oferta in enumerate(fuentes.lista, start=1)
    ]
    seccion.tablas.append(
        Tabla(encabezados=["N.º", "Proveedor", "Producto", "Enlace", "Consultado"], filas=filas)
    )
    return seccion


def construir_informe(estado: EstadoCompra, recomendacion: str, fecha: str) -> Informe:
    """Convierte el estado final del grafo en el informe, como datos."""
    fuentes = Fuentes()
    secciones = [_seccion_solicitud(estado)]
    secciones += _seccion_ofertas(estado, fuentes)
    secciones += _seccion_por_proveedor(estado, fuentes)
    secciones.append(_seccion_combinada(estado, fuentes))
    secciones.append(_seccion_totales(estado))
    secciones.append(_seccion_pendientes(estado))
    secciones.append(_seccion_recomendacion(recomendacion))
    secciones.append(_seccion_fuentes(fuentes))
    return Informe(titulo="Informe de cotización de compra", fecha=fecha, secciones=secciones)


# --------------------------- Markdown ---------------------------

def _tabla_markdown(tabla: Tabla) -> list[str]:
    lineas = [
        "| " + " | ".join(tabla.encabezados) + " |",
        "|" + "|".join("---" for _ in tabla.encabezados) + "|",
    ]
    for fila in tabla.filas:
        lineas.append("| " + " | ".join(c.replace("|", "\\|") for c in fila) + " |")
    return lineas


def a_markdown(informe: Informe) -> str:
    lineas = [f"# {informe.titulo}", "", f"*Generado el {informe.fecha}*", ""]
    for seccion in informe.secciones:
        lineas.append("#" * seccion.nivel + f" {seccion.titulo}")
        lineas.append("")
        for parrafo in seccion.parrafos:
            lineas.extend([parrafo, ""])
        for vineta in seccion.vinetas:
            lineas.append(f"- {vineta}")
        if seccion.vinetas:
            lineas.append("")
        for tabla in seccion.tablas:
            lineas.extend(_tabla_markdown(tabla))
            lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"

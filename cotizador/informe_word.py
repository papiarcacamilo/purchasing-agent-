"""Escribe el informe en un archivo Word (.docx).

Recibe la misma estructura `Informe` que el renderizador Markdown, de modo que
los dos formatos no pueden decir cosas distintas: salen de los mismos datos.
"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from cotizador.informe import Informe, Tabla

# Estilo incluido en la plantilla por defecto de Word. Si no existiera, la
# tabla se escribe igual pero sin bordes.
ESTILO_TABLA = "Table Grid"
ANCHO_MAXIMO_CELDA = 60

# Ancho útil de la página con los márgenes por defecto.
ANCHO_UTIL_CM = 16.0
# Columnas que llevan texto largo y merecen más espacio. El resto se reparte
# el sobrante en partes iguales.
PESO_COLUMNA = {"Producto": 3.0, "Empaque elegido": 3.0, "Enlace": 4.0, "Nota": 2.0}


def _anchos(encabezados: list[str]) -> list[Cm]:
    pesos_ = [PESO_COLUMNA.get(titulo, 1.0) for titulo in encabezados]
    total = sum(pesos_)
    return [Cm(ANCHO_UTIL_CM * peso / total) for peso in pesos_]


def _escribir_tabla(documento: Document, tabla: Tabla) -> None:
    objeto = documento.add_table(rows=1, cols=len(tabla.encabezados))
    try:
        objeto.style = ESTILO_TABLA
    except KeyError:
        pass

    # Los anchos solo se respetan si la tabla se declara de ancho fijo Y se
    # fija el ancho en cada celda. `autofit = False` ya escribe el ancho fijo;
    # agregarlo otra vez a mano dejaba la etiqueta duplicada en el XML.
    objeto.autofit = False
    anchos = _anchos(tabla.encabezados)

    encabezado = objeto.rows[0].cells
    for columna, titulo in enumerate(tabla.encabezados):
        encabezado[columna].width = anchos[columna]
        parrafo = encabezado[columna].paragraphs[0]
        trozo = parrafo.add_run(titulo)
        trozo.bold = True
        trozo.font.size = Pt(9)

    for fila in tabla.filas:
        celdas = objeto.add_row().cells
        for columna, valor in enumerate(fila):
            celdas[columna].width = anchos[columna]
            texto = valor if len(valor) <= ANCHO_MAXIMO_CELDA else valor[:ANCHO_MAXIMO_CELDA] + "…"
            trozo = celdas[columna].paragraphs[0].add_run(texto)
            trozo.font.size = Pt(9)


def a_word(informe: Informe, ruta: str | Path) -> Path:
    """Escribe el informe en `ruta` y devuelve la ruta creada."""
    documento = Document()
    documento.add_heading(informe.titulo, level=0)

    fecha = documento.add_paragraph(f"Generado el {informe.fecha}")
    fecha.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fecha.runs[0].italic = True

    for seccion in informe.secciones:
        documento.add_heading(seccion.titulo, level=min(seccion.nivel, 4))
        for parrafo in seccion.parrafos:
            documento.add_paragraph(parrafo)
        for vineta in seccion.vinetas:
            documento.add_paragraph(vineta, style="List Bullet")
        for tabla in seccion.tablas:
            _escribir_tabla(documento, tabla)
            documento.add_paragraph()

    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento.save(destino)
    return destino

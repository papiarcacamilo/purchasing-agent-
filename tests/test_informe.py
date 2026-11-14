"""Pruebas del informe: estructura, Markdown, Word y verificación de cifras."""
from datetime import date
from pathlib import Path

from langchain_core.runnables import RunnableLambda

from agente.informe import a_markdown, construir_informe, pesos
from agente.informe_word import a_word
from agente.nodos.informar import (
    cifras_calculadas,
    cifras_inventadas,
    crear_nodo_redactar_informe,
    recomendacion_por_codigo,
)
from agente.schemas import (
    EstadoCompra,
    ItemPedido,
    LineaPresupuesto,
    Oferta,
    Pedido,
    Presupuesto,
)

HOY = date(2026, 11, 13)


def _oferta(proveedor, nombre, precio, contenido=1.0, unidad="kg", url="https://x.co/p"):
    return Oferta(
        proveedor=proveedor, nombre=nombre, marca=None,
        presentacion=f"{contenido:g} {unidad}",
        contenido=contenido, unidad_contenido=unidad, precio=precio, moneda="COP",
        ciudad=None, disponible=True, url=url, id_fuente="1",
        fecha_consulta=HOY, origen="catalogo_referencia", nota=None,
    )


def _linea(producto, oferta, paquetes, subtotal, equivalencia="equivalente", sobrante=None):
    return LineaPresupuesto(
        producto=producto, cubierto=True, motivo=None, oferta=oferta,
        equivalencia=equivalencia, paquetes=paquetes, cantidad_pedida=2.0,
        cantidad_cubierta=float(paquetes), sobrante=sobrante, unidad_base="kg",
        subtotal=subtotal,
    )


def _estado():
    exito = _oferta("Éxito", "Arroz ROA 3 kg", 9650.0, 3.0)
    carulla = _oferta("Carulla", "Arroz Carulla 2.5 kg", 8150.0, 2.5, url="https://y.co/p")
    return EstadoCompra(
        texto_usuario="necesito 2 kg de arroz",
        pedido=Pedido(
            items=[ItemPedido(
                texto_original="2 kg de arroz", producto="arroz", cantidad=2.0,
                unidad="kg", marca=None, presentacion=None, observaciones=None,
            )],
            ciudad=None, proveedores=[],
        ),
        proveedores_consultados=["Éxito", "Carulla"],
        presupuestos=[
            Presupuesto(
                nombre="Éxito", lineas=[_linea("arroz", exito, 1, 9650.0, sobrante=1.0)],
                subtotal_productos=9650.0, items_cubiertos=1, items_totales=1, completo=True,
            ),
            Presupuesto(
                nombre="Carulla", lineas=[_linea("arroz", carulla, 1, 8150.0, sobrante=0.5)],
                subtotal_productos=8150.0, items_cubiertos=1, items_totales=1, completo=True,
            ),
        ],
        suposiciones=["No se indicó ciudad."],
    )


# --------------------------- formato ---------------------------

def test_los_pesos_se_escriben_a_la_colombiana():
    assert pesos(9650.0) == "$ 9.650"
    assert pesos(None) == "—"


# --------------------------- estructura ---------------------------

def test_el_informe_trae_las_seis_salidas_del_enunciado():
    informe = construir_informe(_estado(), recomendacion="texto", fecha=str(HOY))
    titulos = " ".join(s.titulo for s in informe.secciones)
    for esperado in ("1. Solicitud", "2. Ofertas", "3. Compra completa por proveedor",
                     "4. Alternativa combinada", "5. Totales", "6. Productos sin cotización",
                     "7. Recomendación", "8. Fuentes"):
        assert esperado in titulos


def test_cada_precio_queda_citado_y_la_fuente_listada():
    informe = construir_informe(_estado(), recomendacion="texto", fecha=str(HOY))
    fuentes = [s for s in informe.secciones if s.titulo.startswith("8.")][0]
    enlaces = [fila[3] for fila in fuentes.tablas[0].filas]
    assert "https://x.co/p" in enlaces and "https://y.co/p" in enlaces


def test_el_envio_no_verificado_no_se_convierte_en_total():
    informe = construir_informe(_estado(), recomendacion="texto", fecha=str(HOY))
    totales = [s for s in informe.secciones if s.titulo.startswith("5.")][0]
    for fila in totales.tablas[0].filas:
        assert fila[2] == "no verificado"
        assert fila[3] == "no se puede calcular"


def test_las_suposiciones_llegan_al_informe():
    informe = construir_informe(_estado(), recomendacion="texto", fecha=str(HOY))
    pendientes = [s for s in informe.secciones if s.titulo.startswith("6.")][0]
    assert any("ciudad" in v for v in pendientes.vinetas)


# --------------------------- Markdown y Word ---------------------------

def test_markdown_escribe_tablas_y_titulos():
    texto = a_markdown(construir_informe(_estado(), recomendacion="Compre en Carulla.", fecha=str(HOY)))
    assert texto.startswith("# Informe de cotización de compra")
    assert "| Proveedor | Producto |" in texto
    assert "Compre en Carulla." in texto
    assert "$ 8.150" in texto


def test_word_se_genera_y_contiene_el_contenido(tmp_path):
    from docx import Document

    informe = construir_informe(_estado(), recomendacion="Compre en Carulla.", fecha=str(HOY))
    ruta = a_word(informe, tmp_path / "informe.docx")
    assert ruta.exists() and ruta.stat().st_size > 0

    documento = Document(str(ruta))
    textos = [p.text for p in documento.paragraphs]
    assert "Compre en Carulla." in textos
    assert any("Informe de cotización" in t for t in textos)
    celdas = [c.text for t in documento.tables for f in t.rows for c in f.cells]
    assert "$ 8.150" in celdas


# --------------------------- verificación de cifras ---------------------------

def test_las_cifras_calculadas_incluyen_subtotales_precios_y_diferencias():
    permitidas = cifras_calculadas(_estado())
    assert 9650 in permitidas and 8150 in permitidas
    assert 1500 in permitidas, "9650 - 8150: la diferencia es citable"


def test_una_cifra_que_el_agente_no_calculo_se_detecta():
    assert cifras_inventadas("Compre por $ 7.000", _estado()) == [7000]


def test_las_cantidades_pequenas_no_se_marcan_como_inventadas():
    assert cifras_inventadas("Son 2 kg en 1 paquete", _estado()) == []


def test_el_nodo_descarta_la_redaccion_con_una_cifra_falsa():
    mentiroso = RunnableLambda(lambda _: "Le recomiendo comprar en Carulla por $ 7.000.")
    salida = crear_nodo_redactar_informe(mentiroso, hoy=HOY)(_estado())

    recomendacion = [s for s in salida["informe"].secciones if s.titulo.startswith("7.")][0]
    assert "7.000" not in recomendacion.parrafos[0]
    assert recomendacion.parrafos[0] == recomendacion_por_codigo(_estado())
    assert any("descartada" in h for h in salida["historial"])


def test_el_nodo_conserva_la_redaccion_cuando_las_cifras_cuadran():
    honesto = RunnableLambda(lambda _: "Conviene Carulla: $ 8.150 frente a $ 9.650 en Éxito.")
    salida = crear_nodo_redactar_informe(honesto, hoy=HOY)(_estado())

    recomendacion = [s for s in salida["informe"].secciones if s.titulo.startswith("7.")][0]
    assert recomendacion.parrafos[0].startswith("Conviene Carulla")
    assert any("verificada" in h for h in salida["historial"])


def test_sin_modelo_la_recomendacion_la_escribe_el_codigo():
    salida = crear_nodo_redactar_informe(None, hoy=HOY)(_estado())
    recomendacion = [s for s in salida["informe"].secciones if s.titulo.startswith("7.")][0]
    assert "Carulla" in recomendacion.parrafos[0]
    assert "$ 8.150" in recomendacion.parrafos[0]


def test_sin_presupuestos_lo_dice_en_vez_de_recomendar():
    assert "no hay una compra que recomendar" in recomendacion_por_codigo(EstadoCompra())


def test_el_word_no_lleva_las_etiquetas_de_la_plantilla(tmp_path):
    from docx import Document

    informe = construir_informe(_estado(), recomendacion="r", fecha=str(HOY))
    propiedades = Document(str(a_word(informe, tmp_path / "i.docx"))).core_properties
    assert propiedades.author == "Cotizador de compras"
    assert propiedades.title == "Informe de cotización de compra"
    assert "python-docx" not in (propiedades.comments or "")


# --------------------------- dónde se guarda ---------------------------

def _estado_con_informe():
    estado = _estado()
    informe = construir_informe(estado, recomendacion="r", fecha=str(HOY))
    return estado.model_copy(update={"informe": informe})


def test_el_informe_no_puede_salir_de_su_carpeta(tmp_path, monkeypatch):
    """Un nombre como "../../fuera.md" no debe escribir fuera de informes/."""
    import main

    carpeta = tmp_path / "proyecto" / "informes"
    monkeypatch.setattr(main, "CARPETA_INFORMES", carpeta)

    ruta = main.guardar_informe(_estado_con_informe(), "../../fuera.md")

    assert Path(ruta).parent == carpeta.resolve()
    assert not (tmp_path / "fuera.md").exists()


def test_la_ruta_del_readme_sigue_funcionando(tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "CARPETA_INFORMES", tmp_path / "informes")
    ruta = main.guardar_informe(_estado_con_informe(), "informes/informe.docx")
    assert Path(ruta) == (tmp_path / "informes" / "informe.docx").resolve()
    assert Path(ruta).exists()


def test_una_extension_no_admitida_no_escribe_nada(tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "CARPETA_INFORMES", tmp_path / "informes")
    salida = main.guardar_informe(_estado_con_informe(), "informe.exe")
    assert "no admitida" in salida
    assert not (tmp_path / "informes").exists()

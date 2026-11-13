"""Pruebas del agente buscador y su ciclo con las herramientas (sin red ni clave).

El LLM se reemplaza por un modelo falso con guion: así se prueba la ORQUESTACIÓN
(quién llama a quién, cuándo se corta el ciclo, qué se recolecta) sin depender de
lo que decida un modelo real.
"""
from datetime import date

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

from agente.grafo import construir_grafo
from agente.herramientas import crear_herramientas
from agente.nodos.buscar import (
    MAX_VUELTAS,
    crear_nodo_agente_buscador,
    proveedores_a_consultar,
    vueltas_usadas,
)
from agente.routers import enrutar_busqueda
from agente.schemas import ClasificacionLote, EstadoCompra, ItemPedido, Oferta, Pedido


def _oferta(proveedor: str, nombre: str, precio: float, **extra) -> Oferta:
    base = dict(
        proveedor=proveedor, nombre=nombre, presentacion="1000 gr", contenido=1000,
        unidad_contenido="g", precio=precio, url=f"https://example.com/{precio:.0f}",
        fecha_consulta=date(2026, 11, 11),
    )
    return Oferta(**{**base, **extra})


CATALOGOS = {
    "Carulla": [
        _oferta("Carulla", "Arroz DIANA blanco (1000 gr)", 6800, marca="Diana"),
        _oferta("Carulla", "Azúcar MANUELITA blanca (1000 gr)", 4760, marca="Manuelita"),
    ],
    "Éxito": [
        _oferta("Éxito", "Arroz DIANA blanco (1000 gr)", 6790, marca="Diana"),
        _oferta("Éxito", "Arroz ROA fortiplus (3000 gr)", 9650, marca="Roa"),
        _oferta("Éxito", "Azúcar MANUELITA blanca (1000 gr)", 4408, marca="Manuelita"),
    ],
}
HERRAMIENTAS = crear_herramientas(CATALOGOS)


def _item(producto: str, **extra) -> ItemPedido:
    base = dict(
        texto_original=producto, producto=producto, cantidad=1, unidad="kg",
        marca=None, presentacion=None, observaciones=None,
    )
    return ItemPedido(**{**base, **extra})


def _pedido(*items: ItemPedido, ciudad=None, proveedores=()) -> Pedido:
    return Pedido(items=list(items), ciudad=ciudad, proveedores=list(proveedores))


def _modelo_con_guion(*respuestas: AIMessage):
    """Modelo falso: devuelve las respuestas del guion, una por llamada."""
    recibido = []
    pendientes = list(respuestas)

    def responder(mensajes):
        recibido.append(mensajes)
        return pendientes.pop(0) if pendientes else AIMessage(content="sin más búsquedas")

    return RunnableLambda(responder), recibido


def _llamada(herramienta: str, termino: str, numero: int) -> dict:
    return {"name": herramienta, "args": {"termino": termino}, "id": f"c{numero}", "type": "tool_call"}


# --- Elección de proveedores ---------------------------------------------

def test_sin_proveedores_indicados_se_consultan_todos():
    elegidos, faltan = proveedores_a_consultar(_pedido(_item("arroz")), ["Ara", "Carulla", "Éxito"])
    assert elegidos == ["Ara", "Carulla", "Éxito"] and faltan == []


def test_se_respetan_los_proveedores_que_pidio_el_usuario():
    pedido = _pedido(_item("arroz"), proveedores=["Éxito", "carulla"])
    elegidos, faltan = proveedores_a_consultar(pedido, ["Ara", "Carulla", "Éxito"])
    assert sorted(elegidos) == ["Carulla", "Éxito"] and faltan == []


def test_un_proveedor_sin_catalogo_se_reporta_y_no_deja_la_busqueda_vacia():
    pedido = _pedido(_item("arroz"), proveedores=["Jumbo"])
    elegidos, faltan = proveedores_a_consultar(pedido, ["Ara", "Carulla"])
    assert faltan == ["Jumbo"] and elegidos == ["Ara", "Carulla"]


# --- Nodo del agente ------------------------------------------------------

def test_el_prompt_obliga_a_reintentar_cuando_no_hay_resultados():
    """Si una tienda no tiene la variedad exacta, debe reintentar con el término general."""
    from agente.prompts import PROMPT_BUSCADOR

    assert "DEBES reintentarla" in PROMPT_BUSCADOR
    assert '"arroz integral" -> "arroz"' in PROMPT_BUSCADOR


def test_el_encargo_inicial_lista_productos_restricciones_y_herramientas():
    modelo, recibido = _modelo_con_guion(AIMessage(content="listo"))
    nodo = crear_nodo_agente_buscador(modelo, HERRAMIENTAS)
    pedido = _pedido(_item("arroz", marca="Diana"), _item("azúcar"), ciudad="Medellín")

    nodo(EstadoCompra(pedido=pedido))

    sistema, humano = recibido[0]
    assert isinstance(sistema, SystemMessage) and isinstance(humano, HumanMessage)
    assert "No inventes productos, precios ni tiendas" in sistema.content
    assert "1. arroz (marca exigida: Diana)" in humano.content and "2. azúcar" in humano.content
    assert "buscar_en_exito" in humano.content and "Medellín" in humano.content


def test_si_el_usuario_nombra_tiendas_solo_se_ofrecen_esas_herramientas():
    modelo, recibido = _modelo_con_guion(AIMessage(content="listo"))
    nodo = crear_nodo_agente_buscador(modelo, HERRAMIENTAS)
    estado = EstadoCompra(pedido=_pedido(_item("arroz")), proveedores_consultados=["Éxito"])

    nodo(estado)

    humano = recibido[0][1].content
    assert "buscar_en_exito" in humano
    assert "buscar_en_carulla" not in humano


def test_el_agente_continua_la_conversacion_y_registra_lo_que_pide():
    llamada = AIMessage(content="", tool_calls=[_llamada("buscar_en_exito", "arroz", 1)])
    modelo, recibido = _modelo_con_guion(llamada)
    nodo = crear_nodo_agente_buscador(modelo, HERRAMIENTAS)
    previos = [SystemMessage("s"), HumanMessage("h"), AIMessage("a")]

    salida = nodo(EstadoCompra(pedido=_pedido(_item("arroz")), mensajes=previos))

    assert recibido[0] == previos          # le llega la conversación completa
    assert salida["mensajes"] == [llamada]  # y solo agrega su respuesta
    assert "1 búsquedas solicitadas" in salida["historial"][0]


# --- Enrutamiento ---------------------------------------------------------

def test_si_el_agente_pide_herramientas_el_grafo_va_a_herramientas():
    estado = EstadoCompra(mensajes=[AIMessage(content="", tool_calls=[_llamada("buscar_en_exito", "arroz", 1)])])
    assert enrutar_busqueda(estado) == "herramientas"


def test_si_el_agente_termina_el_grafo_recolecta():
    assert enrutar_busqueda(EstadoCompra(mensajes=[AIMessage("ya busqué todo")])) == "recolectar_ofertas"


def test_el_tope_de_vueltas_corta_el_ciclo_aunque_el_agente_insista():
    insistente = [AIMessage(content="", tool_calls=[_llamada("buscar_en_exito", "arroz", i)])
                  for i in range(MAX_VUELTAS + 1)]
    assert vueltas_usadas(insistente) == MAX_VUELTAS + 1
    assert enrutar_busqueda(EstadoCompra(mensajes=insistente)) == "recolectar_ofertas"


# --- Grafo completo -------------------------------------------------------

def _grafo(*respuestas: AIMessage):
    modelo, recibido = _modelo_con_guion(*respuestas)
    interprete = RunnableLambda(lambda _: _grafo.pedido)
    sin_clasificar = RunnableLambda(lambda _: ClasificacionLote(clasificaciones=[]))
    return construir_grafo(interprete=interprete, buscador=modelo, clasificador=sin_clasificar,
                           catalogos=CATALOGOS, herramientas=HERRAMIENTAS), recibido


def test_el_ciclo_completo_busca_recolecta_y_agrupa_por_item():
    _grafo.pedido = _pedido(_item("arroz"), _item("azúcar"))
    grafo, _ = _grafo(
        AIMessage(content="", tool_calls=[
            _llamada("buscar_en_exito", "arroz", 1), _llamada("buscar_en_carulla", "arroz", 2),
            _llamada("buscar_en_exito", "azúcar", 3), _llamada("buscar_en_carulla", "azúcar", 4),
        ]),
        AIMessage(content="Busqué los dos productos en las dos tiendas."),
    )
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz y azúcar")))

    assert [r.item.producto for r in final.resultados] == ["arroz", "azúcar"]
    arroz, azucar = final.resultados
    assert {o.proveedor for o in arroz.ofertas} == {"Éxito", "Carulla"}
    assert len(arroz.ofertas) == 3 and len(azucar.ofertas) == 2
    # Ninguna oferta de azúcar se coló en el arroz.
    assert all("Arroz" in o.nombre for o in arroz.ofertas)
    assert any(isinstance(m, ToolMessage) for m in final.mensajes)


def test_se_descartan_las_ofertas_de_una_tienda_que_el_usuario_no_pidio():
    _grafo.pedido = _pedido(_item("arroz"), proveedores=["Éxito"])
    grafo, _ = _grafo(
        # El modelo se salta la instrucción y consulta también Carulla.
        AIMessage(content="", tool_calls=[
            _llamada("buscar_en_exito", "arroz", 1), _llamada("buscar_en_carulla", "arroz", 2),
        ]),
        AIMessage(content="listo"),
    )
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz en Exito")))

    assert final.proveedores_consultados == ["Éxito"]
    assert {o.proveedor for o in final.resultados[0].ofertas} == {"Éxito"}
    assert any("descartadas por ser de tiendas no pedidas" in l for l in final.historial)


def test_la_marca_exigida_filtra_las_ofertas_del_item():
    _grafo.pedido = _pedido(_item("arroz", marca="Roa"))
    grafo, _ = _grafo(
        AIMessage(content="", tool_calls=[_llamada("buscar_en_exito", "arroz", 1)]),
        AIMessage(content="listo"),
    )
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz roa")))
    assert [o.nombre for o in final.resultados[0].ofertas] == ["Arroz ROA fortiplus (3000 gr)"]


def test_si_el_agente_no_busca_nada_la_red_de_seguridad_cubre_el_item():
    _grafo.pedido = _pedido(_item("arroz"))
    grafo, _ = _grafo(AIMessage(content="No voy a buscar nada."))
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz")))

    assert {o.proveedor for o in final.resultados[0].ofertas} == {"Éxito", "Carulla"}
    assert any("búsqueda de respaldo para: arroz" in linea for linea in final.historial)


def test_un_producto_que_no_existe_queda_sin_cotizacion_y_se_registra():
    _grafo.pedido = _pedido(_item("caviar"))
    grafo, _ = _grafo(AIMessage(content="No encontré caviar."))
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="caviar")))

    assert final.resultados[0].ofertas == []
    assert any("sin cotización" in linea for linea in final.historial)


def test_las_ofertas_repetidas_no_se_duplican():
    _grafo.pedido = _pedido(_item("arroz"))
    grafo, _ = _grafo(
        AIMessage(content="", tool_calls=[
            _llamada("buscar_en_exito", "arroz", 1), _llamada("buscar_en_exito", "arroz diana", 2),
        ]),
        AIMessage(content="listo"),
    )
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz")))
    nombres = [o.nombre for o in final.resultados[0].ofertas]
    assert len(nombres) == len(set(nombres)) == 2


def test_el_grafo_no_se_queda_en_el_ciclo_si_el_agente_insiste():
    _grafo.pedido = _pedido(_item("arroz"))
    insistentes = [AIMessage(content="", tool_calls=[_llamada("buscar_en_exito", "arroz", i)])
                   for i in range(20)]
    grafo, recibido = _grafo(*insistentes)
    final = EstadoCompra.model_validate(grafo.invoke(EstadoCompra(texto_usuario="arroz")))

    assert vueltas_usadas(final.mensajes) == MAX_VUELTAS + 1
    assert len(recibido) == MAX_VUELTAS + 1   # el modelo no se llamó más veces
    assert final.resultados[0].ofertas        # y aun así se recolectó


def test_el_diagrama_muestra_el_ciclo_del_agente():
    _grafo.pedido = _pedido(_item("arroz"))
    grafo, _ = _grafo(AIMessage(content="listo"))
    mermaid = grafo.get_graph().draw_mermaid()
    assert "agente_buscador -.-> herramientas" in mermaid
    assert "herramientas --> agente_buscador" in mermaid
    assert "agente_buscador -.-> recolectar_ofertas" in mermaid

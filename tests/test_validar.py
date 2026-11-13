"""Pruebas de la validación y del ciclo de aclaración (sin red ni clave)."""
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver

from cotizador.ejecutar import ejecutar
from cotizador.grafo import construir_grafo
from cotizador.nodos.aclarar import MARCA_ACLARACION, componer_solicitud
from cotizador.nodos.validar import MAX_ACLARACIONES, datos_que_faltan, validar_pedido
from cotizador.prompts import PROMPT_SISTEMA
from cotizador.routers import enrutar_aclaracion, enrutar_validacion
from cotizador.schemas import (
    ClasificacionLote,
    EstadoCompra,
    ItemPedido,
    Pedido,
)


def _item(producto, cantidad, unidad):
    return ItemPedido(
        texto_original=producto,
        producto=producto,
        cantidad=cantidad,
        unidad=unidad,
        marca=None,
        presentacion=None,
        observaciones=None,
    )


def _pedido(items, ciudad="Medellín"):
    return Pedido(items=items, ciudad=ciudad, proveedores=["Éxito"])


# --------------------------- qué falta ---------------------------

def test_un_pedido_completo_no_tiene_nada_que_aclarar():
    assert datos_que_faltan(_pedido([_item("arroz", 2, "kg")])) == []


def test_sin_cantidad_hace_falta_preguntar():
    faltan = datos_que_faltan(_pedido([_item("arroz", None, None)]))
    assert faltan == ["cuánto arroz se necesita"]


def test_sin_unidad_hace_falta_preguntar():
    faltan = datos_que_faltan(_pedido([_item("arroz", 2, None)]))
    assert faltan == ["en qué unidad son 2 de arroz"]


def test_una_cantidad_negativa_no_se_da_por_buena():
    faltan = datos_que_faltan(_pedido([_item("arroz", -3, "kg")]))
    assert "cantidad válida" in faltan[0]


def test_un_pedido_vacio_falta_todo():
    assert datos_que_faltan(None) == ["qué productos hay que cotizar"]
    assert datos_que_faltan(_pedido([])) == ["qué productos hay que cotizar"]


def test_solo_se_pregunta_por_el_item_incompleto():
    faltan = datos_que_faltan(_pedido([_item("arroz", 2, "kg"), _item("aceite", None, None)]))
    assert faltan == ["cuánto aceite se necesita"]


# --------------------------- el nodo ---------------------------

def test_mientras_queden_intentos_no_se_declara_nada():
    estado = EstadoCompra(pedido=_pedido([_item("arroz", None, None)]))
    salida = validar_pedido(estado)
    assert salida["datos_faltantes"]
    assert "suposiciones" not in salida


def test_agotados_los_intentos_lo_que_falta_queda_declarado():
    estado = EstadoCompra(
        pedido=_pedido([_item("arroz", None, None)]), aclaraciones=MAX_ACLARACIONES
    )
    salida = validar_pedido(estado)
    assert salida["datos_faltantes"]
    assert "No se aclaró" in salida["suposiciones"][0]


def test_la_ciudad_ausente_se_declara_pero_no_detiene_el_grafo():
    estado = EstadoCompra(pedido=_pedido([_item("arroz", 2, "kg")], ciudad=None))
    salida = validar_pedido(estado)
    assert salida["datos_faltantes"] == []
    assert any("ciudad" in s for s in salida["suposiciones"])


def test_un_pedido_completo_no_agrega_suposiciones():
    estado = EstadoCompra(pedido=_pedido([_item("arroz", 2, "kg")]))
    assert "suposiciones" not in validar_pedido(estado)


# --------------------------- la arista ---------------------------

def test_la_arista_manda_a_preguntar_cuando_falta_un_dato():
    estado = EstadoCompra(datos_faltantes=["cuánto arroz se necesita"])
    assert enrutar_validacion(estado) == "pedir_aclaracion"


def test_la_arista_sigue_de_largo_si_no_falta_nada():
    assert enrutar_validacion(EstadoCompra()) == "preparar_busqueda"


def test_la_arista_deja_de_preguntar_al_llegar_al_tope():
    estado = EstadoCompra(datos_faltantes=["cuánto arroz"], aclaraciones=MAX_ACLARACIONES)
    assert enrutar_validacion(estado) == "preparar_busqueda"


# --------------------------- el ciclo completo ---------------------------

def _clasificador_vacio():
    """Clasifica todo como no comparable: aquí no se prueba la clasificación."""
    return RunnableLambda(lambda _: ClasificacionLote(clasificaciones=[]))


def _interprete(guion):
    """Devuelve un pedido distinto en cada llamada, según el guion."""
    pendientes = list(guion)

    def responder(_entrada):
        return pendientes.pop(0) if len(pendientes) > 1 else pendientes[0]

    return RunnableLambda(responder)


def _grafo_de_prueba(guion):
    # El buscador falso no pide ninguna herramienta: el ciclo del agente
    # termina de inmediato. Aquí se prueba la aclaración, no la búsqueda.
    buscador = RunnableLambda(lambda _: AIMessage(content="sin búsquedas"))
    return construir_grafo(
        interprete=_interprete(guion),
        buscador=buscador,
        clasificador=_clasificador_vacio(),
        checkpointer=InMemorySaver(),
    )


def test_el_grafo_se_detiene_pregunta_y_sigue_con_la_respuesta():
    incompleto = _pedido([_item("arroz", None, None)])
    completo = _pedido([_item("arroz", 2, "kg")])
    preguntas = []

    def responder(pausa):
        preguntas.append(pausa)
        return "2 kg"

    final = ejecutar(
        "necesito arroz", responder=responder, grafo=_grafo_de_prueba([incompleto, completo])
    )

    assert len(preguntas) == 1, "debió preguntar exactamente una vez"
    assert preguntas[0]["faltan"] == ["cuánto arroz se necesita"]
    assert "cuánto arroz" in preguntas[0]["pregunta"]
    # La respuesta se sumó al texto original, no lo reemplazó.
    assert final.texto_usuario.startswith("necesito arroz")
    assert "2 kg" in final.texto_usuario
    assert final.datos_faltantes == []
    assert final.aclaraciones == 1


def test_un_pedido_completo_nunca_interrumpe():
    preguntas = []

    def responder(pausa):
        preguntas.append(pausa)
        return ""

    ejecutar(
        "2 kg de arroz",
        responder=responder,
        grafo=_grafo_de_prueba([_pedido([_item("arroz", 2, "kg")])]),
    )
    assert preguntas == []


def test_si_el_usuario_no_responde_el_grafo_continua_y_lo_declara():
    incompleto = _pedido([_item("arroz", None, None)])

    final = ejecutar(
        "necesito arroz",
        responder=lambda _pausa: "",
        grafo=_grafo_de_prueba([incompleto]),
    )

    assert final.aclaraciones == MAX_ACLARACIONES, "debió dejar de preguntar en el tope"
    assert any("No se aclaró" in s for s in final.suposiciones)


def test_sin_checkpointer_el_grafo_se_detiene_pero_no_se_rompe():
    """Documenta el límite: sin dónde guardar el estado, no hay reanudación."""
    grafo = construir_grafo(
        interprete=_interprete([_pedido([_item("arroz", None, None)])]),
        buscador=RunnableLambda(lambda _: AIMessage(content="sin búsquedas")),
        clasificador=_clasificador_vacio(),
    )
    salida = grafo.invoke(EstadoCompra(texto_usuario="necesito arroz"))
    assert salida["__interrupt__"], "el grafo informa lo que necesita"
    assert not salida["presupuestos"], "pero no llega al presupuesto"


# --------------------- la respuesta no crea productos ---------------------

def test_la_respuesta_se_pega_como_dialogo_y_nombra_la_pregunta():
    """El fallo que esto evita: '...y 2 litros de aceite\\n2kg' hacía que el
    modelo leyera '2kg' como un tercer producto."""
    estado = EstadoCompra(
        texto_usuario="necesito arroz y 2 litros de aceite",
        datos_faltantes=["cuánto arroz se necesita"],
    )
    texto = componer_solicitud(estado, "2kg")

    assert texto.startswith("necesito arroz y 2 litros de aceite")
    assert MARCA_ACLARACION in texto
    assert "Pregunta: cuánto arroz se necesita" in texto
    assert "Respuesta del usuario: 2kg" in texto


def test_el_prompt_del_interprete_explica_esa_marca():
    """La marca no sirve de nada si el prompt no la conoce."""
    assert MARCA_ACLARACION in PROMPT_SISTEMA
    assert "NUNCA agrega un producto nuevo" in PROMPT_SISTEMA


# --------------------- no insistir ni gastar llamadas ---------------------

def test_la_arista_tras_preguntar_reinterpreta_solo_si_hubo_respuesta():
    assert enrutar_aclaracion(EstadoCompra(hubo_respuesta=True)) == "interpretar_pedido"
    assert enrutar_aclaracion(EstadoCompra(hubo_respuesta=False)) == "validar_pedido"


def test_si_no_responde_no_se_vuelve_a_llamar_al_modelo():
    """Antes se reinterpretaba el mismo texto: una llamada pagada para nada."""
    incompleto = _pedido([_item("arroz", None, None)])
    veces = []

    def contar(_entrada):
        veces.append(1)
        return incompleto

    relleno = RunnableLambda(lambda _: AIMessage(content="sin búsquedas"))
    grafo = construir_grafo(
        interprete=RunnableLambda(contar),
        buscador=relleno,
        clasificador=_clasificador_vacio(),
        checkpointer=InMemorySaver(),
    )
    final = ejecutar("necesito arroz", responder=lambda _p: "", grafo=grafo)

    assert len(veces) == 1, "solo la interpretación inicial"
    assert any("No se aclaró" in s for s in final.suposiciones)

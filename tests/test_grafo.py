"""Pruebas del nodo de interpretación y del grafo con un LLM falso (sin API ni .env)."""
from datetime import date

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from cotizador.grafo import construir_grafo
from cotizador.nodos import crear_nodo_interpretar
from cotizador.schemas import ClasificacionLote, EstadoCompra, ItemPedido, Oferta, Pedido

# Catálogo mínimo: estas pruebas miran el nodo de interpretación, no la búsqueda.
CATALOGO = {
    "Tienda Ficticia": [
        Oferta(
            proveedor="Tienda Ficticia", nombre="Arroz de prueba (1000 gr)", presentacion="1000 gr",
            contenido=1000, unidad_contenido="g", precio=5000, url="https://example.com/a",
            fecha_consulta=date(2026, 11, 11),
        )
    ]
}
SIN_BUSQUEDA = RunnableLambda(lambda _: AIMessage(content="no busco nada"))


SIN_CLASIFICAR = RunnableLambda(lambda _: ClasificacionLote(clasificaciones=[]))


def _construir(interprete):
    """Arma el grafo con el intérprete indicado y el resto de piezas falsas."""
    return construir_grafo(
        interprete=interprete, buscador=SIN_BUSQUEDA, clasificador=SIN_CLASIFICAR, catalogos=CATALOGO
    )

PEDIDO_FALSO = Pedido(
    items=[
        ItemPedido(
            texto_original="5 kg de arroz",
            producto="arroz",
            cantidad=5,
            unidad="kg",
            marca=None,
            presentacion=None,
            observaciones=None,
        ),
        ItemPedido(
            texto_original="2 litros de aceite",
            producto="aceite",
            cantidad=2,
            unidad="L",
            marca=None,
            presentacion=None,
            observaciones=None,
        ),
    ],
    ciudad="Medellín",
    proveedores=["Éxito", "Carulla"],
)


def _interprete_falso(registro: list):
    """Cadena falsa: anota lo que recibe y devuelve siempre el mismo pedido."""

    def responder(entrada: dict) -> Pedido:
        registro.append(entrada)
        return PEDIDO_FALSO

    return RunnableLambda(responder)


def test_el_nodo_entrega_el_texto_a_la_cadena_con_la_clave_del_prompt():
    llamadas = []
    nodo = crear_nodo_interpretar(_interprete_falso(llamadas))
    nodo(EstadoCompra(texto_usuario="  5 kg de arroz y 2 litros de aceite  "))
    assert llamadas == [{"texto_usuario": "5 kg de arroz y 2 litros de aceite"}]


def test_el_nodo_devuelve_solo_los_campos_que_actualiza():
    nodo = crear_nodo_interpretar(_interprete_falso([]))
    salida = nodo(EstadoCompra(texto_usuario="5 kg de arroz"))
    assert set(salida) == {"pedido", "historial"}
    assert salida["pedido"] is PEDIDO_FALSO


def test_el_historial_resume_items_ciudad_y_proveedores():
    nodo = crear_nodo_interpretar(_interprete_falso([]))
    (linea,) = nodo(EstadoCompra(texto_usuario="5 kg de arroz"))["historial"]
    assert linea.startswith("[interpretar_pedido]")
    assert "2 ítems" in linea and "Medellín" in linea and "Éxito, Carulla" in linea


def test_sin_texto_no_se_llama_al_modelo():
    llamadas = []
    nodo = crear_nodo_interpretar(_interprete_falso(llamadas))
    salida = nodo(EstadoCompra(texto_usuario="   "))
    assert llamadas == []
    assert "pedido" not in salida


def test_el_grafo_ejecuta_el_nodo_y_deja_el_pedido_en_el_estado():
    grafo = _construir(_interprete_falso([]))
    final = EstadoCompra.model_validate(
        grafo.invoke(EstadoCompra(texto_usuario="5 kg de arroz y 2 litros de aceite"))
    )
    assert [i.producto for i in final.pedido.items] == ["arroz", "aceite"]
    assert final.pedido.ciudad == "Medellín"
    assert final.historial[0].startswith("[interpretar_pedido]")


def test_el_diagrama_del_grafo_empieza_por_la_interpretacion():
    mermaid = _construir(_interprete_falso([])).get_graph().draw_mermaid()
    assert "__start__ --> interpretar_pedido" in mermaid
    assert "interpretar_pedido --> preparar_busqueda" in mermaid
    assert "recolectar_ofertas --> normalizar_ofertas" in mermaid
    assert "normalizar_ofertas --> clasificar_equivalencia" in mermaid
    assert "clasificar_equivalencia --> calcular_presupuesto" in mermaid
    assert "calcular_presupuesto --> __end__" in mermaid

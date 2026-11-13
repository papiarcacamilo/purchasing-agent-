"""Pruebas de los esquemas Pydantic (sin red y sin clave)."""
import secrets

import pytest
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from agente.schemas import EstadoCompra, ItemPedido, Pedido


def _item(**cambios) -> dict:
    """Datos de un ítem válido; cada prueba cambia solo lo que quiere examinar."""
    base = {
        "texto_original": "5 kg de arroz",
        "producto": "arroz",
        "cantidad": 5,
        "unidad": "kg",
        "marca": None,
        "presentacion": None,
        "observaciones": None,
    }
    return {**base, **cambios}


def test_pedido_valido_con_el_ejemplo_del_enunciado():
    pedido = Pedido(
        items=[
            _item(),
            _item(texto_original="2 litros de aceite", producto="aceite", cantidad=2, unidad="L"),
            _item(texto_original="3 kg de azúcar", producto="azúcar", cantidad=3, unidad="kg"),
        ],
        ciudad="Medellín",
        proveedores=[],
    )
    assert [i.producto for i in pedido.items] == ["arroz", "aceite", "azúcar"]
    assert pedido.items[0].cantidad == 5.0
    assert pedido.ciudad == "Medellín"


def test_rechaza_unidad_desconocida():
    with pytest.raises(ValidationError):
        ItemPedido(**_item(unidad="arroba"))


def test_rechaza_campos_extra():
    with pytest.raises(ValidationError):
        ItemPedido(**_item(precio=1000))


def test_los_campos_opcionales_aceptan_none_pero_deben_venir():
    assert ItemPedido(**_item(cantidad=None, unidad=None)).cantidad is None
    sin_marca = _item()
    del sin_marca["marca"]
    with pytest.raises(ValidationError):
        ItemPedido(**sin_marca)


@pytest.mark.parametrize("modelo", [Pedido, ItemPedido])
def test_esquema_compatible_con_salida_estructurada_estricta(modelo):
    esquema = modelo.model_json_schema()
    assert set(esquema["required"]) == set(esquema["properties"])
    assert esquema["additionalProperties"] is False


def test_el_llm_acepta_el_esquema_en_modo_estricto():
    # Clave falsa: construir la cadena no hace llamadas de red.
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=secrets.token_hex(12))
    assert llm.with_structured_output(Pedido, method="json_schema", strict=True) is not None


def test_el_reducer_acumula_historial_y_suposiciones():
    def nodo_a(state: EstadoCompra) -> dict:
        return {"historial": ["[a] paso uno"], "suposiciones": ["sin preferencia de marca"]}

    def nodo_b(state: EstadoCompra) -> dict:
        return {"historial": ["[b] paso dos"], "datos_faltantes": ["ciudad"]}

    g = StateGraph(EstadoCompra)
    g.add_node("a", nodo_a)
    g.add_node("b", nodo_b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)

    final = EstadoCompra.model_validate(g.compile().invoke(EstadoCompra(texto_usuario="x")))
    assert final.historial == ["[a] paso uno", "[b] paso dos"]
    assert final.suposiciones == ["sin preferencia de marca"]
    assert final.datos_faltantes == ["ciudad"]

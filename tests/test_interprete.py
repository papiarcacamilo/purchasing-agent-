"""Pruebas del prompt y de la cadena de interpretación (sin red y sin clave)."""
import secrets
from typing import get_args

from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from agente.llm import construir_interprete
from agente.prompts import PROMPT_SISTEMA, crear_prompt_interprete
from agente.schemas import ItemPedido, Pedido, Unidad


def test_el_texto_del_usuario_va_solo_en_el_mensaje_humano_y_delimitado():
    sistema, humano = crear_prompt_interprete().format_messages(texto_usuario="2 kg de papa")
    assert "2 kg de papa" not in sistema.content
    assert '"""\n2 kg de papa\n"""' in humano.content


def test_el_prompt_formatea_aunque_el_usuario_escriba_llaves():
    mensajes = crear_prompt_interprete().format_messages(texto_usuario='arroz {"kg": 5}')
    assert len(mensajes) == 2
    assert 'arroz {"kg": 5}' in mensajes[1].content


def test_el_prompt_menciona_todas_las_unidades_del_esquema():
    # Si se agrega una unidad a schemas.py, el prompt debe explicarla.
    for unidad in get_args(Unidad):
        assert unidad in PROMPT_SISTEMA


def test_el_prompt_aclara_que_la_cantidad_no_es_la_presentacion():
    """Fallo real: "1 litro de aceite" se interpretó como presentación exigida."""
    assert "La cantidad que quiere comprar NUNCA es la presentación" in PROMPT_SISTEMA
    assert "1 litro de aceite" in PROMPT_SISTEMA


def test_el_prompt_declara_el_texto_como_datos():
    assert "DATOS" in PROMPT_SISTEMA


def test_la_cadena_se_construye_con_salida_estructurada_estricta():
    # Clave falsa: construir la cadena no hace llamadas de red.
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=secrets.token_hex(12))
    assert construir_interprete(llm) is not None


def test_el_prompt_entrega_al_modelo_los_dos_mensajes():
    """Sustituye el LLM por una función: comprueba la tubería prompt -> modelo."""
    recibido = {}

    def modelo_falso(valor_prompt) -> Pedido:
        recibido["mensajes"] = valor_prompt.to_messages()
        return Pedido(
            items=[
                ItemPedido(
                    texto_original="5 kg de arroz",
                    producto="arroz",
                    cantidad=5,
                    unidad="kg",
                    marca=None,
                    presentacion=None,
                    observaciones=None,
                )
            ],
            ciudad="Medellín",
            proveedores=[],
        )

    cadena = crear_prompt_interprete() | RunnableLambda(modelo_falso)
    pedido = cadena.invoke({"texto_usuario": "5 kg de arroz para Medellín"})

    assert [m.type for m in recibido["mensajes"]] == ["system", "human"]
    assert "5 kg de arroz para Medellín" in recibido["mensajes"][1].content
    assert pedido.items[0].producto == "arroz"
    assert pedido.ciudad == "Medellín"

"""Nodo 1: interpreta la solicitud con el LLM (salida estructurada)."""
from langchain_core.runnables import Runnable

from cotizador.schemas import EstadoCompra


def crear_nodo_interpretar(cadena: Runnable):
    """Fábrica: recibe la cadena `prompt | llm.with_structured_output(Pedido)`.

    Inyectar la cadena permite usar OpenAI en producción y una función falsa
    en las pruebas, sin cambiar el nodo.
    """

    def interpretar_pedido(state: EstadoCompra) -> dict:
        texto = state.texto_usuario.strip()
        if not texto:
            # Sin texto no hay nada que interpretar: no se gasta una llamada al modelo.
            return {"historial": ["[interpretar_pedido] Solicitud vacía: no se llamó al modelo."]}

        pedido = cadena.invoke({"texto_usuario": texto})
        proveedores = ", ".join(pedido.proveedores) or "sin indicar"
        return {
            "pedido": pedido,
            "historial": [
                f"[interpretar_pedido] {len(pedido.items)} ítems | "
                f"ciudad: {pedido.ciudad or 'sin indicar'} | proveedores: {proveedores}"
            ],
        }

    return interpretar_pedido

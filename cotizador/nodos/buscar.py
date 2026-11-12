"""Nodos 3 y 3a: el agente buscador y la recolección de sus resultados.

El agente decide QUÉ buscar (y con qué término); las herramientas hacen la
búsqueda real. El ciclo agente -> herramientas -> agente se repite hasta que el
agente deja de pedir herramientas o hasta el tope de vueltas.
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from cotizador.busqueda import buscar_ofertas, coincide, normalizar
from cotizador.herramientas import nombre_herramienta
from cotizador.prompts import PROMPT_BUSCADOR, encargo_de_busqueda
from cotizador.schemas import EstadoCompra, Oferta, ResultadoBusqueda

# Tope de vueltas del ciclo: evita que una conversación se alargue sin control.
MAX_VUELTAS = 4


def vueltas_usadas(mensajes: list) -> int:
    """Cuántas veces el agente ya pidió herramientas."""
    return sum(1 for m in mensajes if isinstance(m, AIMessage) and m.tool_calls)


def proveedores_a_consultar(pedido, disponibles: list[str]) -> tuple[list[str], list[str]]:
    """Decide en qué proveedores buscar.

    Si el usuario nombró proveedores, se respetan (los que tengamos catálogo).
    Si no nombró ninguno, se consultan todos. Devuelve también los que pidió y
    no tenemos, para registrarlos como limitación.
    """
    if not pedido.proveedores:
        return disponibles, []

    elegidos, sin_catalogo = [], []
    for pedido_proveedor in pedido.proveedores:
        buscado = normalizar(pedido_proveedor)
        iguales = [p for p in disponibles if buscado in normalizar(p) or normalizar(p) in buscado]
        if iguales:
            elegidos.extend(p for p in iguales if p not in elegidos)
        else:
            sin_catalogo.append(pedido_proveedor)
    return (elegidos or disponibles), sin_catalogo


def crear_nodo_agente_buscador(modelo: Runnable, herramientas: list[BaseTool]):
    """Fábrica: recibe el LLM con herramientas enlazadas y la lista de herramientas."""
    nombres = [h.name for h in herramientas]

    def agente_buscador(state: EstadoCompra) -> dict:
        if not state.mensajes:
            # Primera vuelta: el encargo lo arma el código, no el modelo.
            encargo = encargo_de_busqueda(state.pedido, nombres)
            conversacion = [SystemMessage(PROMPT_BUSCADOR), HumanMessage(encargo)]
        else:
            conversacion = list(state.mensajes)

        respuesta = modelo.invoke(conversacion)
        pedidas = len(respuesta.tool_calls)
        nuevos = ([*conversacion, respuesta] if not state.mensajes else [respuesta])
        return {
            "mensajes": nuevos,
            "historial": [
                f"[agente_buscador] vuelta {vueltas_usadas(state.mensajes) + 1}: "
                f"{pedidas} búsquedas solicitadas"
                if pedidas
                else "[agente_buscador] el agente dio por terminada la búsqueda"
            ],
        }

    return agente_buscador


def crear_nodo_recolectar(catalogos: dict[str, list[Oferta]]):
    """Fábrica: reúne las ofertas de la conversación y garantiza la cobertura.

    1. Toma los objetos Oferta que las herramientas adjuntaron a cada respuesta.
    2. Los agrupa por ítem del pedido.
    3. Si un ítem quedó sin ofertas, hace la búsqueda directa por código
       (red de seguridad: el enunciado exige consultar al menos dos proveedores).
    """

    def recolectar_ofertas(state: EstadoCompra) -> dict:
        consultados = state.proveedores_consultados or sorted(catalogos)

        # 1. Ofertas que trajeron las herramientas, sin repetir.
        encontradas: dict[tuple, Oferta] = {}
        for mensaje in state.mensajes:
            if isinstance(mensaje, ToolMessage) and isinstance(mensaje.artifact, list):
                for oferta in mensaje.artifact:
                    encontradas.setdefault((oferta.proveedor, oferta.nombre, oferta.presentacion), oferta)
        del_agente = list(encontradas.values())

        # 2 y 3. Un resultado por ítem; si queda vacío, búsqueda de respaldo.
        resultados, con_respaldo, sin_cotizacion = [], [], []
        for item in state.pedido.items:
            suyas = [o for o in del_agente if coincide(o, item.producto, item.marca)]
            if not suyas:
                for proveedor in consultados:
                    suyas.extend(buscar_ofertas(catalogos.get(proveedor, []), item.producto, limite=4))
                suyas = [o for o in suyas if coincide(o, item.producto, item.marca)]
                (con_respaldo if suyas else sin_cotizacion).append(item.producto)
            resultados.append(ResultadoBusqueda(item=item, ofertas=suyas))

        historial = [
            f"[recolectar_ofertas] {len(del_agente)} ofertas del agente en "
            f"{len({o.proveedor for o in del_agente})} proveedores; "
            f"{sum(len(r.ofertas) for r in resultados)} asignadas a {len(resultados)} ítems"
        ]
        if con_respaldo:
            historial.append(
                f"[recolectar_ofertas] búsqueda de respaldo para: {', '.join(con_respaldo)}"
            )
        if sin_cotizacion:
            historial.append(
                f"[recolectar_ofertas] sin cotización en ningún proveedor: {', '.join(sin_cotizacion)}"
            )
        return {"resultados": resultados, "historial": historial}

    return recolectar_ofertas


def crear_nodo_preparar_busqueda(catalogos: dict[str, list[Oferta]]):
    """Nodo previo: fija en qué proveedores se va a buscar y lo deja registrado."""

    def preparar_busqueda(state: EstadoCompra) -> dict:
        elegidos, sin_catalogo = proveedores_a_consultar(state.pedido, sorted(catalogos))
        salida = {
            "proveedores_consultados": elegidos,
            "historial": [f"[preparar_busqueda] proveedores a consultar: {', '.join(elegidos)}"],
        }
        if sin_catalogo:
            salida["suposiciones"] = [
                f"No hay catálogo de {', '.join(sin_catalogo)}; se consultaron {', '.join(elegidos)}."
            ]
        return salida

    return preparar_busqueda

"""Pruebas del nodo de clasificación de equivalencia (sin red ni clave)."""
from datetime import date

from langchain_core.runnables import RunnableLambda

from agente.nodos.clasificar import (
    TOPE_POR_PROVEEDOR,
    crear_nodo_clasificar,
    seleccionar_candidatas,
)
from agente.nodos.normalizar import normalizar_ofertas
from agente.prompts import encargo_de_clasificacion
from agente.schemas import (
    ClasificacionLote,
    ClasificacionOferta,
    EstadoCompra,
    ItemPedido,
    Oferta,
    ResultadoBusqueda,
)


def _oferta(nombre, precio=6790, contenido=1000, unidad="g", proveedor="Éxito", **extra) -> Oferta:
    base = dict(
        proveedor=proveedor, nombre=nombre, presentacion=f"{contenido} {unidad}",
        contenido=contenido, unidad_contenido=unidad, precio=precio,
        url="https://example.com/p", fecha_consulta=date(2026, 11, 11),
    )
    return Oferta(**{**base, **extra})


def _item(producto="arroz", **extra) -> ItemPedido:
    base = dict(
        texto_original=f"2 kg de {producto}", producto=producto, cantidad=2, unidad="kg",
        marca=None, presentacion=None, observaciones=None,
    )
    return ItemPedido(**{**base, **extra})


def _estado(item, ofertas) -> EstadoCompra:
    """Estado con las ofertas ya normalizadas, como llegan al clasificador."""
    sin_clasificar = EstadoCompra(resultados=[ResultadoBusqueda(item=item, ofertas=ofertas)])
    return EstadoCompra(resultados=normalizar_ofertas(sin_clasificar)["resultados"])


def _clasificador(*valores):
    """Modelo falso: clasifica la oferta n con el valor n de la lista."""
    recibido = []

    def responder(entrada):
        recibido.append(entrada["encargo"])
        return ClasificacionLote(
            clasificaciones=[
                ClasificacionOferta(numero=i, equivalencia=v, razon=f"razón {i}")
                for i, v in enumerate(valores, start=1)
            ]
        )

    return RunnableLambda(responder), recibido


def test_el_prompt_prohibe_castigar_el_tamano_del_empaque():
    """Fallo real: una botella de 900 mL se marcó sustituto al pedir 1 litro."""
    from agente.prompts import PROMPT_CLASIFICADOR

    assert "El TAMAÑO DEL EMPAQUE no influye" in PROMPT_CLASIFICADOR
    assert "cuántos empaques hacen falta" in PROMPT_CLASIFICADOR
    # Las reglas solas no bastaron con el modelo real: hubo que dar ejemplos.
    assert "botella (900 mL)\" -> equivalente" in PROMPT_CLASIFICADOR
    assert "no es la marca exigida" in PROMPT_CLASIFICADOR.lower()
    # Otra variedad es sustituto, no "no comparable": así no se pierden alternativas.
    assert "es SUSTITUTO, nunca no_comparable" in PROMPT_CLASIFICADOR


def test_el_encargo_distingue_lo_exigido_de_lo_que_no_se_pidio():
    item = _item(marca="Diana", observaciones="integral")
    estado = _estado(item, [_oferta("Arroz DIANA integral", marca="Diana")])
    candidatas = estado.resultados[0].normalizadas

    encargo = encargo_de_clasificacion(item, candidatas)
    assert "Marca EXIGIDA: Diana" in encargo and "Condición EXIGIDA: integral" in encargo
    assert "1. Arroz DIANA integral" in encargo


def test_si_no_se_exige_nada_el_encargo_lo_dice():
    estado = _estado(_item(), [_oferta("Arroz DIANA")])
    encargo = encargo_de_clasificacion(_item(), estado.resultados[0].normalizadas)
    assert "no exigió marca, presentación ni condiciones" in encargo


def test_cada_oferta_queda_con_su_clasificacion_y_su_razon():
    estado = _estado(_item(), [_oferta("Arroz DIANA blanco"), _oferta("Arroz DIANA integral", precio=4500)])
    # La lista va ordenada por precio unitario: el integral (más barato) es el 1.
    cadena, _ = _clasificador("sustituto", "equivalente")

    salida = crear_nodo_clasificar(cadena)(estado)
    clasificadas = salida["resultados"][0].normalizadas

    assert [n.oferta.nombre for n in clasificadas] == ["Arroz DIANA integral", "Arroz DIANA blanco"]
    assert [n.equivalencia for n in clasificadas] == ["sustituto", "equivalente"]
    assert clasificadas[0].razon == "razón 1"
    assert "1 equivalentes, 1 sustitutos" in salida["historial"][0]


def test_lo_que_ya_era_no_comparable_no_se_le_pregunta_al_modelo():
    sin_contenido = _oferta("Papel higiénico x12", contenido=None, unidad=None)
    estado = _estado(_item(), [_oferta("Arroz DIANA"), sin_contenido])
    cadena, recibido = _clasificador("equivalente")

    clasificadas = crear_nodo_clasificar(cadena)(estado)["resultados"][0].normalizadas

    # Al modelo solo le llegó una oferta, no las dos.
    assert recibido[0].count("presentación:") == 1
    papel = next(n for n in clasificadas if "Papel" in n.oferta.nombre)
    assert papel.equivalencia == "no_comparable"
    assert papel.razon == "la tienda no publica el contenido del empaque"


def test_solo_se_clasifican_las_mas_baratas_de_cada_proveedor():
    muchas = [
        _oferta(f"Arroz {i}", precio=1000 * (i + 1), proveedor=p)
        for p in ("Éxito", "Carulla")
        for i in range(TOPE_POR_PROVEEDOR + 2)
    ]
    estado = _estado(_item(), muchas)
    candidatas = seleccionar_candidatas(estado.resultados[0].normalizadas, _item())

    assert len(candidatas) == TOPE_POR_PROVEEDOR * 2
    for proveedor in ("Éxito", "Carulla"):
        suyas = [c for c in candidatas if c.oferta.proveedor == proveedor]
        assert len(suyas) == TOPE_POR_PROVEEDOR
        # Son las más baratas por unidad de esa tienda.
        assert [c.oferta.precio for c in suyas] == sorted(c.oferta.precio for c in suyas)


def test_lo_que_cumple_una_exigencia_se_clasifica_aunque_no_sea_lo_mas_barato():
    """Fallo real: el único arroz integral era el 5.o más barato y quedaba fuera."""
    baratos = [_oferta(f"Arroz blanco {i}", precio=1000 * (i + 1)) for i in range(TOPE_POR_PROVEEDOR)]
    integral = _oferta("Arroz DIANA integral", precio=99000)       # el más caro de todos
    estado = _estado(_item(observaciones="integral"), [*baratos, integral])

    candidatas = seleccionar_candidatas(estado.resultados[0].normalizadas, _item(observaciones="integral"))

    assert "Arroz DIANA integral" in [c.oferta.nombre for c in candidatas]
    assert len(candidatas) == TOPE_POR_PROVEEDOR + 1


def test_la_marca_exigida_tambien_entra_siempre():
    baratos = [_oferta(f"Arroz {i}", precio=1000 * (i + 1), marca="Otra") for i in range(TOPE_POR_PROVEEDOR)]
    de_marca = _oferta("Arroz ROA fortiplus", precio=99000, marca="Roa")
    estado = _estado(_item(marca="Roa"), [*baratos, de_marca])

    candidatas = seleccionar_candidatas(estado.resultados[0].normalizadas, _item(marca="Roa"))
    assert "Arroz ROA fortiplus" in [c.oferta.nombre for c in candidatas]


def test_una_oferta_fuera_del_tope_queda_marcada_y_no_se_pierde():
    muchas = [_oferta(f"Arroz {i}", precio=1000 * (i + 1)) for i in range(TOPE_POR_PROVEEDOR + 1)]
    estado = _estado(_item(), muchas)
    cadena, _ = _clasificador(*["equivalente"] * TOPE_POR_PROVEEDOR)

    clasificadas = crear_nodo_clasificar(cadena)(estado)["resultados"][0].normalizadas

    assert len(clasificadas) == TOPE_POR_PROVEEDOR + 1   # no se pierde ninguna
    assert clasificadas[-1].equivalencia == "no_comparable"
    assert "más baratas" in clasificadas[-1].razon


def test_se_avisa_cuando_un_producto_no_tiene_ningun_equivalente():
    estado = _estado(_item(), [_oferta("Galletas de arroz inflado")])
    cadena, _ = _clasificador("no_comparable")

    historial = crear_nodo_clasificar(cadena)(estado)["historial"]
    assert any("sin equivalente exacto: arroz" in linea for linea in historial)


def test_un_item_sin_ofertas_no_llama_al_modelo():
    estado = EstadoCompra(resultados=[ResultadoBusqueda(item=_item(), ofertas=[])])
    cadena, recibido = _clasificador()

    salida = crear_nodo_clasificar(cadena)(estado)
    assert recibido == [] and salida["resultados"][0].normalizadas == []

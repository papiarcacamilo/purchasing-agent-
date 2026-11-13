"""Nodo 5: clasificación de equivalencia.

Decide si cada oferta es el producto pedido (equivalente), algo que sirve para
lo mismo (sustituto) o algo que no responde al pedido (no comparable).

Es un juicio de lenguaje, así que lo hace el LLM. Dos salvedades:

- Las ofertas que la normalización ya marcó como no comparables (sin contenido
  publicado, o midiendo otra cosa) no se le preguntan al modelo: ya tienen su
  motivo técnico. Así no se gastan tokens en lo que ya está decidido.
- Se clasifica por lotes, un lote por ítem, con un tope de ofertas por
  proveedor: el presupuesto solo necesita las más baratas de cada tienda.
"""
from langchain_core.runnables import Runnable

from cotizador.busqueda import palabras_clave
from cotizador.prompts import encargo_de_clasificacion
from cotizador.schemas import EstadoCompra, ItemPedido, OfertaNormalizada, ResultadoBusqueda

# Cuántas ofertas (las más baratas por unidad) se clasifican por proveedor.
TOPE_POR_PROVEEDOR = 4


def _cumple_lo_exigido(normalizada: OfertaNormalizada, exigidas: list[str]) -> bool:
    oferta = normalizada.oferta
    texto = palabras_clave(f"{oferta.nombre} {oferta.marca or ''} {oferta.presentacion}")
    return bool(exigidas) and all(palabra in texto for palabra in exigidas)


def seleccionar_candidatas(
    normalizadas: list[OfertaNormalizada], item: ItemPedido
) -> list[OfertaNormalizada]:
    """Qué ofertas se le mandan al modelo: las más baratas de cada proveedor...

    ...MÁS cualquiera que cumpla una restricción que el comprador exigió (marca,
    presentación u observaciones), aunque no esté entre las más baratas.

    Esto corrige un fallo real: al pedir "arroz integral", el único arroz integral
    del catálogo era el quinto más barato de su tienda y el tope lo dejaba fuera,
    así que ninguna oferta quedaba como equivalente. Lo barato no es lo que cumple.

    La lista ya viene ordenada por precio unitario desde la normalización.
    """
    exigidas = palabras_clave(
        " ".join(filtro for filtro in (item.marca, item.presentacion, item.observaciones) if filtro)
    )
    cuantas: dict[str, int] = {}
    elegidas = []
    for normalizada in normalizadas:
        if not normalizada.comparable:
            continue
        proveedor = normalizada.oferta.proveedor
        if _cumple_lo_exigido(normalizada, exigidas):
            elegidas.append(normalizada)          # siempre entra: es lo que se pidió
            continue
        if cuantas.get(proveedor, 0) >= TOPE_POR_PROVEEDOR:
            continue
        cuantas[proveedor] = cuantas.get(proveedor, 0) + 1
        elegidas.append(normalizada)
    return elegidas


def _copiar_con(normalizada: OfertaNormalizada, equivalencia: str, razon: str) -> OfertaNormalizada:
    return normalizada.model_copy(update={"equivalencia": equivalencia, "razon": razon})


def crear_nodo_clasificar(cadena: Runnable):
    """Fábrica: recibe la cadena `prompt | llm.with_structured_output(ClasificacionLote)`."""

    def clasificar_equivalencia(state: EstadoCompra) -> dict:
        resultados, conteo = [], {"equivalente": 0, "sustituto": 0, "no_comparable": 0}

        for resultado in state.resultados:
            candidatas = seleccionar_candidatas(resultado.normalizadas, resultado.item)
            decisiones = {}
            if candidatas:
                lote = cadena.invoke(
                    {"encargo": encargo_de_clasificacion(resultado.item, candidatas)}
                )
                decisiones = {c.numero: c for c in lote.clasificaciones}

            posicion = {id(n): i for i, n in enumerate(candidatas, start=1)}
            clasificadas = []
            for normalizada in resultado.normalizadas:
                if not normalizada.comparable:
                    # Ya tenía su motivo técnico desde la normalización.
                    clasificadas.append(_copiar_con(normalizada, "no_comparable", normalizada.motivo))
                    continue
                decision = decisiones.get(posicion.get(id(normalizada)))
                if decision is None:
                    # No se le preguntó al modelo (quedó fuera del tope) o no la respondió.
                    clasificadas.append(
                        _copiar_con(normalizada, "no_comparable", "no se clasificó: hay opciones más baratas en la misma tienda")
                    )
                    continue
                clasificadas.append(_copiar_con(normalizada, decision.equivalencia, decision.razon))

            for clasificada in clasificadas:
                conteo[clasificada.equivalencia] = conteo.get(clasificada.equivalencia, 0) + 1
            resultados.append(
                ResultadoBusqueda(
                    item=resultado.item, ofertas=resultado.ofertas, normalizadas=clasificadas
                )
            )

        historial = [
            f"[clasificar_equivalencia] {conteo['equivalente']} equivalentes, "
            f"{conteo['sustituto']} sustitutos, {conteo['no_comparable']} no comparables"
        ]
        sin_equivalente = [
            r.item.producto
            for r in resultados
            if not any(n.equivalencia == "equivalente" for n in r.normalizadas)
        ]
        if sin_equivalente:
            historial.append(
                f"[clasificar_equivalencia] sin equivalente exacto: {', '.join(sin_equivalente)}"
            )
        return {"resultados": resultados, "historial": historial}

    return clasificar_equivalencia

"""Punto de entrada por línea de comandos.

Uso:
    uv run python main.py                      # pregunta la solicitud por consola
    uv run python main.py --texto "Necesito 5 kg de arroz para Medellín"
    uv run python main.py --mermaid            # dibuja el grafo (no usa OpenAI)
"""
import argparse
import sys

import openai

from cotizador.ejecutar import ejecutar
from cotizador.errores import explicar_error_openai
from cotizador.grafo import construir_grafo


def guardar_informe(estado, ruta: str) -> str:
    """Escribe el informe del estado en `ruta`. La extensión elige el formato."""
    from pathlib import Path

    from cotizador.informe import a_markdown

    if estado.informe is None:
        return "no se generó informe (el grafo no llegó a redactarlo)"

    destino = Path(ruta)
    if destino.suffix.lower() == ".docx":
        from cotizador.informe_word import a_word

        return str(a_word(estado.informe, destino))

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(a_markdown(estado.informe), encoding="utf-8")
    return str(destino)


def main() -> int:
    # Git Bash en Windows no siempre usa UTF-8: lo forzamos para ver bien las tildes.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Cotizador de compras con LangGraph")
    parser.add_argument("--texto", default="", help="Solicitud como argumento (omite la pregunta).")
    parser.add_argument(
        "--mermaid", action="store_true", help="Imprime el diagrama Mermaid del grafo y termina."
    )
    parser.add_argument(
        "--informe",
        default="",
        help="Guarda el informe final. Con .docx escribe Word; con .md, Markdown.",
    )
    args = parser.parse_args()

    if args.mermaid:
        # Piezas de relleno: solo para dibujar, no se llama al LLM ni se exige la clave.
        from langchain_core.runnables import RunnableLambda

        relleno = RunnableLambda(lambda _: None)  # no se llama: solo se dibuja
        # Se rellenan TODAS las dependencias que usan el modelo. Si el grafo
        # crece con otra, hay que agregarla aquí: la prueba
        # `test_mermaid_funciona_sin_clave` avisa si se olvida.
        grafo = construir_grafo(
            interprete=relleno, buscador=relleno, clasificador=relleno, redactor=relleno
        )
        print(grafo.get_graph().draw_mermaid())
        return 0

    texto = args.texto.strip() or input("\n¿Qué necesita comprar? > ").strip()
    if not texto:
        print("No se recibió ninguna solicitud.")
        return 1

    try:
        # `ejecutar` atiende las pausas: si falta un dato, pregunta por consola
        # y reanuda el grafo donde se quedó.
        estado = ejecutar(texto)
    except openai.APIError as error:
        # Mensaje claro en lugar de una traza larga; nunca se imprime la clave.
        print(f"No se pudo consultar el modelo: {explicar_error_openai(error)}")
        return 1

    print("\n================ PEDIDO INTERPRETADO ================")
    print(estado.pedido.model_dump_json(indent=2) if estado.pedido else "Sin pedido.")

    print("\n================ OFERTAS ENCONTRADAS ================")
    print("Leyenda:  = equivalente   ~ sustituto   x no comparable")
    print(f"Proveedores consultados: {', '.join(estado.proveedores_consultados) or 'ninguno'}")
    for resultado in estado.resultados:
        print(f"\n--- {resultado.item.producto} ({len(resultado.ofertas)} ofertas) ---")
        for normalizada in resultado.normalizadas:
            oferta = normalizada.oferta
            precio = f"$ {oferta.precio:,.0f}".replace(",", ".")
            if normalizada.comparable:
                unitario = f"$ {normalizada.precio_unitario:,.0f}".replace(",", ".")
                detalle = f"{unitario} por {normalizada.unidad_base}"
            else:
                detalle = "no comparable"
            etiqueta = {"equivalente": "=", "sustituto": "~", "no_comparable": "x"}
            marca = etiqueta.get(normalizada.equivalencia or "", " ")
            print(f"  {marca} [{oferta.proveedor}] {oferta.nombre} | {precio} | {detalle}")
            if normalizada.razon:
                print(f"      {normalizada.equivalencia}: {normalizada.razon}")
            print(f"      {oferta.url}")
        if not resultado.ofertas:
            print("  Sin cotización en los proveedores consultados.")
    def pesos(valor):
        return "$ " + f"{valor:,.0f}".replace(",", ".")

    def mostrar(presupuesto):
        print(f"\n--- {presupuesto.nombre} ---")
        for linea in presupuesto.lineas:
            if not linea.cubierto:
                print(f"  {linea.producto}: SIN COTIZACIÓN ({linea.motivo})")
                continue
            tienda = f" [{linea.oferta.proveedor}]" if presupuesto.combinado else ""
            sustituto = "  (sustituto)" if linea.equivalencia == "sustituto" else ""
            sobra = (
                f", sobran {linea.sobrante:g} {linea.unidad_base}"
                if linea.sobrante and linea.sobrante > 0
                else ""
            )
            print(f"  {linea.producto}{tienda}: {linea.paquetes} x {linea.oferta.nombre}")
            print(f"      {pesos(linea.subtotal)}{sobra}{sustituto}")
        print(f"  Subtotal productos : {pesos(presupuesto.subtotal_productos)}")
        print("  Envío              : no verificado")
        print("  Total confirmado   : no se puede calcular sin el envío")
        if presupuesto.sin_cotizacion:
            print(f"  Sin cotización     : {', '.join(presupuesto.sin_cotizacion)}")

    print("\n================ PRESUPUESTO ================")
    for presupuesto in estado.presupuestos:
        mostrar(presupuesto)
    if estado.combinado:
        mostrar(estado.combinado)

    if estado.suposiciones:
        print("\n========= SUPUESTOS Y CONDICIONES NO VERIFICADAS =========")
        for suposicion in estado.suposiciones:
            print(f"  - {suposicion}")

    if args.informe:
        print(f"\nInforme: {guardar_informe(estado, args.informe)}")

    print("\n--- Traza de nodos ---")
    for linea in estado.historial:
        print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Punto de entrada por línea de comandos.

Uso:
    uv run python main.py                      # pregunta la solicitud por consola
    uv run python main.py --texto "Necesito 5 kg de arroz para Medellín"
    uv run python main.py --mermaid            # dibuja el grafo (no usa OpenAI)
"""
import argparse
import sys

import openai

from cotizador.errores import explicar_error_openai
from cotizador.grafo import construir_grafo
from cotizador.schemas import EstadoCompra


def main() -> int:
    # Git Bash en Windows no siempre usa UTF-8: lo forzamos para ver bien las tildes.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Cotizador de compras con LangGraph")
    parser.add_argument("--texto", default="", help="Solicitud como argumento (omite la pregunta).")
    parser.add_argument(
        "--mermaid", action="store_true", help="Imprime el diagrama Mermaid del grafo y termina."
    )
    args = parser.parse_args()

    if args.mermaid:
        # Piezas de relleno: solo para dibujar, no se llama al LLM ni se exige la clave.
        from langchain_core.runnables import RunnableLambda

        relleno = RunnableLambda(lambda _: None)
        grafo = construir_grafo(interprete=relleno, buscador=relleno)
        print(grafo.get_graph().draw_mermaid())
        return 0

    texto = args.texto.strip() or input("\n¿Qué necesita comprar? > ").strip()
    if not texto:
        print("No se recibió ninguna solicitud.")
        return 1

    grafo = construir_grafo()
    try:
        resultado = grafo.invoke(EstadoCompra(texto_usuario=texto))
    except openai.APIError as error:
        # Mensaje claro en lugar de una traza larga; nunca se imprime la clave.
        print(f"No se pudo consultar el modelo: {explicar_error_openai(error)}")
        return 1
    estado = EstadoCompra.model_validate(resultado)

    print("\n================ PEDIDO INTERPRETADO ================")
    print(estado.pedido.model_dump_json(indent=2) if estado.pedido else "Sin pedido.")

    print("\n================ OFERTAS ENCONTRADAS ================")
    print(f"Proveedores consultados: {', '.join(estado.proveedores_consultados) or 'ninguno'}")
    for resultado in estado.resultados:
        print(f"\n--- {resultado.item.producto} ({len(resultado.ofertas)} ofertas) ---")
        for oferta in resultado.ofertas:
            precio = f"$ {oferta.precio:,.0f}".replace(",", ".")
            print(f"  [{oferta.proveedor}] {oferta.nombre} | {precio} | {oferta.url}")
        if not resultado.ofertas:
            print("  Sin cotización en los proveedores consultados.")
    print("\n--- Traza de nodos ---")
    for linea in estado.historial:
        print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())

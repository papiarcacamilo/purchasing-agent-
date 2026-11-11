"""Prueba manual de la cadena de interpretación.

Uso:
    uv run python -m cotizador.demo --prompt "Necesito 5 kg de arroz para Medellín"
        Muestra los mensajes que recibiría el modelo. No usa la API ni la clave.

    uv run python -m cotizador.demo "Necesito 5 kg de arroz para Medellín"
        Llama al modelo y muestra el Pedido estructurado. Requiere una clave válida.
"""
import argparse
import sys

from cotizador.prompts import crear_prompt_interprete

EJEMPLO = (
    "Necesito 5 kg de arroz, 2 litros de aceite y 3 kg de azúcar. "
    "Consulta dos supermercados y prepara un presupuesto para Medellín."
)


def main() -> int:
    # Git Bash en Windows no siempre usa UTF-8: lo forzamos para ver bien las tildes.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Interpreta una solicitud de compra")
    parser.add_argument("texto", nargs="?", default=EJEMPLO, help="Solicitud en lenguaje natural.")
    parser.add_argument(
        "--prompt", action="store_true", help="Solo muestra el prompt; no llama al modelo."
    )
    args = parser.parse_args()

    if args.prompt:
        for mensaje in crear_prompt_interprete().format_messages(texto_usuario=args.texto):
            print(f"===== MENSAJE: {mensaje.type} ({len(mensaje.content)} caracteres) =====")
            print(mensaje.content)
            print()
        return 0

    # Se importa aquí para que --prompt funcione sin clave.
    from cotizador.llm import construir_interprete

    pedido = construir_interprete().invoke({"texto_usuario": args.texto})
    print(pedido.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

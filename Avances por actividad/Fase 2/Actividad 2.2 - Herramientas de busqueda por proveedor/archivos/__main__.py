"""Prueba manual de las herramientas, sin LLM ni clave.

Uso:
    uv run python -m cotizador.herramientas "arroz"
    uv run python -m cotizador.herramientas "papel higienico"
"""
import sys

from cotizador.herramientas import crear_herramientas


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    termino = " ".join(sys.argv[1:]).strip() or "arroz"
    herramientas = crear_herramientas()
    print(f"Herramientas disponibles: {', '.join(h.name for h in herramientas)}\n")
    for herramienta in herramientas:
        print(f"=== {herramienta.name}(termino='{termino}') ===")
        print(herramienta.invoke({"termino": termino}))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

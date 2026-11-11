"""Traduce los errores de OpenAI a una causa clara, sin trazas largas ni claves."""
import openai

# El orden importa: se revisa del error más específico al más general.
DIAGNOSTICOS = {
    openai.AuthenticationError: (
        "OpenAI rechazó la clave (401). Está mal copiada, fue eliminada o no es de OpenAI."
    ),
    openai.PermissionDeniedError: "La clave no tiene permiso para usar este modelo (403).",
    openai.NotFoundError: "El modelo indicado en OPENAI_MODEL no existe para esta cuenta (404).",
    openai.RateLimitError: "Sin saldo o límite de uso alcanzado en la cuenta de OpenAI (429).",
    openai.APIConnectionError: "No hay conexión con OpenAI. Revisa internet, VPN o proxy.",
}


def explicar_error_openai(error: Exception) -> str:
    """Devuelve la causa probable de un error de OpenAI en una sola línea."""
    for tipo, causa in DIAGNOSTICOS.items():
        if isinstance(error, tipo):
            return causa
    return f"Error inesperado de OpenAI: {type(error).__name__}"

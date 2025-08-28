from llm_guard.input_scanners import PromptInjection

print("🔄 Cargando el modelo del escáner...")
scanner = PromptInjection()
print("✅ Modelo cargado. La función está lista para usarse.")

def is_valid_prompt(user_input: str) -> bool:
    """
    Analiza el texto de un usuario con LLM Guard para detectar inyección de prompts.

    Args:
        user_input: El string de entrada proporcionado por el usuario.

    Returns:
        True si el prompt es considerado seguro (válido).
        False si se detecta un posible ataque de inyección (inválido).
    """
    _, is_valid = scanner.scan(user_input)
    return is_valid
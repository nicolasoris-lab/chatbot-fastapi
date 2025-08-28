import re

def welcome_message(user_message):
    # Convertir el mensaje a minúsculas y quitar espacios para una comparación más robusta
    normalized_message = user_message.lower().strip()

    # 1. Definir una lista de saludos y preguntas comunes
    greetings = re.compile(r"\b(hola(a|s)*|buenas|hey|que tal)\b")
    questions = re.compile(r"(qu(e|é) puedes hacer)|(ayuda)|(tus funciones)|(para qu(e|é) sirves)")

    # 2. Comprobar si el mensaje es un saludo
    if re.search(greetings, normalized_message):
        return "Hola ¿Cómo puedo ayudarte hoy?🤖"

    # 3. Comprobar si el mensaje es una pregunta sobre capacidades
    if re.search(questions, normalized_message):
        return "Soy un chatbot de IA diseñado para responder preguntas sobre la Dirección General de Rentas de la Provincia de Salta\nEstoy aquí para ayudarte\nPregúntame lo que necesites saber🤖"

    return ""
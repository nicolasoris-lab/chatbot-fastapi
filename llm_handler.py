import google.generativeai as genai
import config

# Configura la API de Google
genai.configure(api_key=config.GOOGLE_API_KEY)

# Configuración del modelo (sin cambios)
generation_config = {
    "temperature": 0.2,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

# Configuración de seguridad (sin cambios)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Inicializa el modelo de Gemini (sin cambios)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# --- ¡AQUÍ ESTÁ LA MODIFICACIÓN CLAVE! ---
def generate_answer_from_context(query: str, full_context_with_sources: str) -> str:
    """
    Usa un LLM de Google Gemini para generar una respuesta, instruyéndolo para que cite sus fuentes.
    """
    if not full_context_with_sources:
        return "No se encontró información relevante en los documentos para responder."

    # El prompt ahora incluye las instrucciones para citar las fuentes.
    # La variable 'full_context_with_sources' ya viene formateada desde chat.py
    prompt = (
        "Eres un asistente experto de la Dirección General de Rentas de Salta, Argentina. Tu tarea es responder la pregunta del usuario basándote estricta y únicamente en el contexto proporcionado.\n"
        "Si la respuesta no se encuentra en el contexto, di explícitamente: 'Basado en la información proporcionada, no puedo responder a esa pregunta.'\n"
        "Sé conciso y responde en el mismo idioma que la pregunta.\n"
        "IMPORTANTE: Al final de tu respuesta, siempre debes añadir una sección llamada 'Fuentes' donde cites de forma clara cada fuente que utilizaste, basándote en la información 'Fuente', 'Publicación' y 'Artículo' que se encuentra en el contexto.\n\n"
        f"**Contexto Proporcionado:**\n'''\n{full_context_with_sources}\n'''\n\n"
        f"**Pregunta del Usuario:**\n{query}\n\n"
        "**Respuesta:**"
    )

    try:
        # Genera el contenido usando el modelo
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error al contactar la API de Gemini: {e}")
        return "Hubo un error al generar la respuesta. Por favor, intenta de nuevo más tarde."
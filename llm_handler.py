# llm_handler.py
import config
import google.generativeai as genai
import ollama
from abc import ABC, abstractmethod

# ------------------- DEFINICIÓN DE LA INTERFAZ (CLASE ABSTRACTA) -------------------
class LLM(ABC):
    """
    Clase Base Abstracta que define la interfaz para cualquier modelo de lenguaje.
    Cualquier nuevo LLM que se agregue deberá heredar de esta clase.
    """
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Método que toma un prompt y devuelve la respuesta generada por el modelo.
        """
        pass

# ------------------- IMPLEMENTACIÓN PARA GEMINI -------------------
class GeminiLLM(LLM):
    """Implementación concreta para el modelo de Google Gemini."""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("No se proporcionó la API Key de Google Gemini.")
        
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config=generation_config,
            safety_settings=safety_settings
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error al contactar la API de Gemini: {e}")
            return "Hubo un error al generar la respuesta con Gemini. Por favor, intenta de nuevo más tarde."

# ------------------- IMPLEMENTACIÓN PARA OLLAMA -------------------
class OllamaLLM(LLM):
    """Implementación concreta para modelos servidos a través de Ollama."""
    def __init__(self, model: str, host: str = None):
        self.model = model
        # Si se especifica un host, se crea un cliente para ese host.
        # De lo contrario, usará el host por defecto (localhost:11434).
        self.client = ollama.Client(host=host) if host else ollama.Client()

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error al contactar el servidor de Ollama: {e}")
            return "Hubo un error al generar larespuesta con Ollama. Asegúrate de que el servidor de Ollama esté en ejecución."

# ------------------- FÁBRICA (FACTORY) PARA SELECCIONAR EL LLM -------------------
def get_llm_instance() -> LLM:
    """
    Lee la configuración y devuelve una instancia del LLM correspondiente.
    Este es el único lugar que necesitas modificar si agregas un nuevo proveedor.
    """
    provider = config.LLM_PROVIDER.lower()
    
    if provider == 'gemini':
        return GeminiLLM(api_key=config.GOOGLE_API_KEY)
    elif provider == 'ollama':
        return OllamaLLM(model=config.OLLAMA_MODEL, host=config.OLLAMA_HOST)
    else:
        raise ValueError(f"Proveedor de LLM no soportado: {provider}")

# ------------------- FUNCIÓN PRINCIPAL (SIN CAMBIOS EN SU LÓGICA) -------------------
def generate_answer_from_context(query: str, full_context_with_sources: str) -> str:
    """
    Construye el prompt y usa el LLM configurado para generar una respuesta.
    """
    if not full_context_with_sources:
        return "No se encontró información relevante en los documentos para responder."

    # La construcción del prompt es independiente del LLM, por lo que se mantiene igual.
    prompt = (
        "Eres un asistente experto de la Dirección General de Rentas de Salta, Argentina. Tu tarea es responder la pregunta del usuario basándote estricta y únicamente en el contexto proporcionado.\n"
        "Si la respuesta no se encuentra en el contexto, di explícitamente: 'Basado en la información proporcionada, no puedo responder a esa pregunta.'\n"
        "Sé conciso y responde en el mismo idioma que la pregunta.\n"
        f"**Contexto Proporcionado:**\n'''\n{full_context_with_sources}\n'''\n\n"
        f"**Pregunta del Usuario:**\n{query}\n\n"
        "**Respuesta:**"
    )
    
    try:
        # Obtenemos la instancia del LLM configurado (Gemini, Ollama, etc.)
        llm = get_llm_instance()
        # Generamos la respuesta usando la interfaz común (.generate)
        return llm.generate(prompt)
    except Exception as e:
        print(f"Error al obtener la instancia del LLM o al generar la respuesta: {e}")
        return "Hubo un error general en el sistema de generación de respuestas."
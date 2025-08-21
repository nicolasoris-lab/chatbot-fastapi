from pydantic import BaseModel
from typing import List, Dict, Any

class Question(BaseModel):
    """Modelo para la pregunta del usuario."""
    query: str
    n_results: int = 5

class Answer(BaseModel):
    """Modelo para la respuesta que contiene el contexto encontrado."""
    context: List[str]
    metadata: List[dict]

class GeneratedAnswer(BaseModel):
    """Modelo para la respuesta final generada por el LLM."""
    answer: str
    # --- CAMBIO CLAVE ---
    # Reemplazamos 'context' por 'sources' para que coincida con lo que
    # devuelve el endpoint /ask y para que la API sea más clara.
    sources: List[Dict[str, Any]]
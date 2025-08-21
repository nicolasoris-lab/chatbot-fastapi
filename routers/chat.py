from fastapi import APIRouter

import services
import llm_handler
from models import Question, GeneratedAnswer

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/", summary="Enviar un mensaje al chat (Modo Depuración)")
async def handle_chat_message(question: Question):
    """
    Endpoint de depuración para ver los resultados de la búsqueda sin llamar al LLM.
    """
    search_results = services.perform_similarity_search(question.query, question.n_results)
    
    # Devuelve los resultados crudos para revisión
    return {
        "pregunta": question.query,
        "contexto_encontrado": search_results.get('documents', [[]])[0],
        "metadatos": search_results.get('metadatas', [[]])[0]
    }

@router.post("/ask", response_model=GeneratedAnswer, summary="Preguntar al LLM usando RAG con Citación de Fuentes")
async def ask_llm(question: Question):
    """
    Realiza un proceso completo de RAG:
    1. Busca contexto y metadatos relevantes en la base de datos vectorial.
    2. Construye un contexto enriquecido con la información de las fuentes.
    3. Pasa la pregunta y el contexto a un LLM para generar una respuesta citada.
    """
    # 1. Obtenemos los resultados de la búsqueda
    search_results = services.perform_similarity_search(question.query, question.n_results)

    context_docs = search_results.get('documents', [[]])[0]
    context_metadatas = search_results.get('metadatas', [[]])[0]

    if not context_docs:
        return GeneratedAnswer(
            answer="Lo siento, no pude encontrar información relevante en mi base de datos para responder a tu pregunta.",
            sources=[] # Devolvemos una lista vacía de fuentes
        )

    # 2. <-- ¡AQUÍ ESTÁ LA MAGIA! Se construye el contexto enriquecido
    formatted_context_parts = []
    for doc, meta in zip(context_docs, context_metadatas):
        source_info = (
            f"---\n"
            f"Fuente: {meta.get('tipo_documento', 'N/A')} {meta.get('numero_documento', 'N/A')}\n"
            f"Publicación: {meta.get('fecha_publicacion', 'N/A')}\n"
            f"Artículo: {meta.get('articulo', 'N/A')}\n"
            f"Contenido: {doc}\n"
            f"---"
        )
        formatted_context_parts.append(source_info)
    
    full_context = "\n\n".join(formatted_context_parts)

    # 3. Se llama al handler del LLM, pero ahora con el contexto ya formateado
    generated_text = llm_handler.generate_answer_from_context(question.query, full_context)
    
    # 4. Devolvemos la respuesta y también los metadatos como fuentes
    return GeneratedAnswer(
        answer=generated_text,
        sources=context_metadatas # Pasamos los metadatos para que el frontend los pueda usar
    )
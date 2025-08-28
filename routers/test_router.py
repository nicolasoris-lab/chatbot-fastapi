from fastapi import APIRouter

from services import perform_similarity_search
import llm_handler
from models.chat_models import FilterPayload, Question, GeneratedAnswer
from services.search_service import search_with_filters

router = APIRouter(
    prefix="/test",
    tags=["Test"]
)

@router.post("/", summary="Enviar un mensaje al chat (Modo Depuración)")
async def handle_chat_message(question: Question):
    """
    Endpoint de depuración para ver los resultados de la búsqueda sin llamar al LLM.
    """
    search_results = perform_similarity_search(question.query, question.n_results)
    
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
    # Obtenemos los resultados de la búsqueda
    search_results = perform_similarity_search(question.query, question.n_results)

    context_docs = search_results.get('documents', [[]])[0]
    context_metadatas = search_results.get('metadatas', [[]])[0]

    if not context_docs:
        return GeneratedAnswer(
            answer="Lo siento, no pude encontrar información relevante en mi base de datos para responder a tu pregunta.",
            sources=[]
        )

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

    # Se llama al handler del LLM, pero ahora con el contexto ya formateado
    generated_text = llm_handler.generate_answer_from_context(question.query, full_context)
    
    # Devolvemos la respuesta y también los metadatos como fuentes
    return GeneratedAnswer(
        answer=generated_text,
        sources=context_metadatas
    )

# --- ENDPOINT PARA TESTEAR FILTROS ---
@router.post("/test-filter", summary="TEST: Probar filtros de metadatos directamente")
async def test_filter_documents(payload: FilterPayload):
    """
    Endpoint de testeo para validar la búsqueda por filtros de metadatos
    sin usar la extracción de texto. No llama al LLM.
    """
    # Construimos el diccionario de filtros a partir del payload
    filters = {
        key: value 
        for key, value in payload.dict().items() 
        if value is not None and key in ["tipo_documento", "numero_documento", "articulo"]
    }
    
    # Llamamos a la nueva función de servicio
    search_results = search_with_filters(
        filters=filters, 
        n_results=payload.n_results, 
        query=payload.query
    )
    
    # Devolvemos un resultado claro para el testeo
    return {
        "endpoint": "/test-filter",
        "filtros_aplicados": filters,
        "pregunta_semantica_opcional": payload.query,
        "contexto_encontrado": search_results.get('documents', [[]])[0],
        "metadatos_encontrados": search_results.get('metadatas', [[]])[0]
    }
# services/telegram_service.py

import config
import httpx
import re
import llm_handler
from services import perform_similarity_search

N_RESULTS_FOR_TELEGRAM = 5

def escape_markdown_v2(text: str) -> str:
    """Escapa los caracteres especiales de Markdown V2."""
    if not isinstance(text, str):
        text = str(text)
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def send_telegram_message(chat_id: int, text: str):
    """
    Envía un mensaje de texto a un chat específico de Telegram.
    Ahora solo se encarga de enviar, asumiendo que el texto ya está formateado.
    """
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2"
        }
        try:
            response = await client.post(f"{config.TELEGRAM_API_URL}/sendMessage", json=payload)
            response.raise_for_status()
            print(f"Respuesta enviada a Chat ID {chat_id}")
        except httpx.HTTPStatusError as e:
            print(f"Error al enviar mensaje: {e.response.status_code} - {e.response.text}")

def get_rag_response_for_telegram(user_query: str) -> str:
    """
    Realiza el proceso RAG completo, sanitiza los datos y formatea la salida para Telegram.
    """
    print(f"Ejecutando búsqueda de similitud para: '{user_query}'")
    
    search_results = perform_similarity_search(user_query, n_results=N_RESULTS_FOR_TELEGRAM)
    context_docs = search_results.get('documents', [[]])[0]
    context_metadatas = search_results.get('metadatas', [[]])[0]

    if not context_docs:
        # Sanitizamos también los mensajes de error por si acaso
        return escape_markdown_v2("Lo siento, no pude encontrar información relevante en mi base de datos para responder a tu pregunta.")

    # ... (Construcción del full_context para el LLM sigue igual) ...
    formatted_context_parts = []
    for doc, meta in zip(context_docs, context_metadatas):
        source_info = (
            f"---\n"
            f"Fuente: {meta.get('tipo_documento', 'N/A')} {meta.get('numero_documento', 'N/A')}\n"
            f"Artículo: {meta.get('articulo', 'N/A')}\n"
            f"Contenido: {doc}\n"
            f"---"
        )
        formatted_context_parts.append(source_info)
    full_context = "\n\n".join(formatted_context_parts)

    print("Generando respuesta con el LLM...")
    generated_answer = llm_handler.generate_answer_from_context(user_query, full_context)
    
    # --- ✅ LÓGICA DE FORMATEO Y SANITIZACIÓN MEJORADA ---

    # 1. Sanitizamos la respuesta del LLM primero
    safe_answer = escape_markdown_v2(generated_answer)

    # 2. Construimos las líneas de las fuentes sanitizando cada parte variable
    sources_text_parts = []
    for meta in context_metadatas:
        # Sanitizamos cada pieza de metadatos antes de insertarla
        tipo_doc = escape_markdown_v2(meta.get('tipo_documento', 'Doc'))
        num_doc = escape_markdown_v2(meta.get('numero_documento', ''))
        articulo = escape_markdown_v2(meta.get('articulo', 'N/A'))

        # Construimos la línea con sintaxis MarkdownV2 válida (escapando '-' y '.')
        source_line = f"\\- *{tipo_doc} {num_doc}*, Art\\. {articulo}"
        if source_line not in sources_text_parts:
            sources_text_parts.append(source_line)
    
    sources_text = "\n".join(sources_text_parts)

    LLM_NO_ANSWER_RESPONSE = 'Basado en la información proporcionada, no puedo responder a esa pregunta\.'

    if LLM_NO_ANSWER_RESPONSE in safe_answer:
        final_response = (
        f"{safe_answer}"
        )
    else:
        # 3. Unimos todo en la respuesta final
        final_response = (
            f"{safe_answer}\n\n"
            f"*Fuentes consultadas:*\n"
            f"{sources_text}"
        )

    
    return final_response
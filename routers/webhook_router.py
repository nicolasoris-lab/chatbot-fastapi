# routers/webhook_router.py

import config
from fastapi import APIRouter, Response

from models.telegram_models import TelegramUpdate
# ¡Importamos la nueva función del servicio!
from services.telegram_service import send_telegram_message, get_rag_response_for_telegram

router = APIRouter(
    prefix="/telegram",
    tags=["Telegram"]
)

@router.post(f"/webhook/{config.TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(update: TelegramUpdate):
    """
    Recibe los mensajes de Telegram, los procesa con la lógica RAG
    y devuelve una respuesta con fuentes.
    """
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        user_message = update.message.text
        
        print(f"Mensaje recibido de Chat ID {chat_id}: {user_message}")
        
        # 1. Obtener la respuesta completa del servicio RAG
        # Esta función ahora hace todo el trabajo pesado.
        response_text = get_rag_response_for_telegram(user_message)
        
        # 2. Enviar la respuesta formateada de vuelta al usuario
        await send_telegram_message(chat_id, response_text)
    
    return Response(status_code=200)
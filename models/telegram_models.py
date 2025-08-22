from typing import Optional
from pydantic import BaseModel

# --- Modelos Pydantic para los datos de Telegram ---
# Usamos Pydantic para validar y estructurar los datos que Telegram nos envía.
class TelegramChat(BaseModel):
    id: int

class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: Optional[str] # El texto del mensaje es opcional

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage]
import os
import uvicorn
from fastapi import FastAPI

import config
from routers import chat_router, document_router, webhook_router

# --- INICIALIZACIÓN DE LA APP ---
app = FastAPI(
    title="Servicio RAG con FastAPI y OpenAI",
    description="Sube PDFs y haz preguntas sobre su contenido usando un LLM.",
    version="3.0.0",
)

os.makedirs(config.TEMP_UPLOAD_DIR, exist_ok=True)

# --- INCLUIR ROUTERS ---
app.include_router(document_router.router)
app.include_router(chat_router.router)
app.include_router(webhook_router.router)

@app.get("/", tags=["Root"])
def read_root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {"status": "ok", "message": "API funcionando. Visita /docs para la documentación."}

# --- EJECUCIÓN ---
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
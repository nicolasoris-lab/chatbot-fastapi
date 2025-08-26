import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- PORT y HOST ---
PORT = int(os.environ.get("PORT", 8001))
HOST = os.getenv("HOST")

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configuración del LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # 'gemini' por defecto
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")

# --- Rutas de Archivos ---
CHROMA_DATA_PATH = "chroma_db"
TEMP_UPLOAD_DIR = "temp_uploads"

# --- Configuración de la Colección de ChromaDB ---
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

# --- Modelo de Embeddings ---
# Puedes cambiarlo por otros modelos de SentenceTransformers si lo deseas.
# https://www.sbert.net/docs/pretrained_models.html
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
# vector_db.py
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import config

print("Cargando el modelo de embeddings. Esto puede tardar unos momentos...")
# El modelo de embeddings no cambia, es independiente de la base de datos
embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
vector_size = embedding_model.get_sentence_embedding_dimension()
print("✅ Modelo de embeddings cargado.")

# Inicializa el cliente de Qdrant. Asume que Qdrant corre localmente.
# Puedes mover host y port a tu archivo config.py
client = QdrantClient(host="localhost", port=6333)

# Verifica si la colección ya existe. Si no, la crea.
try:
    collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
    print(f"✅ Colección '{config.COLLECTION_NAME}' ya existe.")
except Exception:
    print(f"Creando colección '{config.COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=config.COLLECTION_NAME,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    print(f"✅ Colección '{config.COLLECTION_NAME}' creada exitosamente.")

# Opcional: Para obtener el conteo de documentos al iniciar
try:
    count = client.get_collection(collection_name=config.COLLECTION_NAME).points_count
    print(f"La colección tiene actualmente {count} puntos/documentos.")
except Exception as e:
    print(f"No se pudo obtener el conteo de la colección: {e}")
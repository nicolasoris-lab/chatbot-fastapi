import chromadb
from sentence_transformers import SentenceTransformer
import config

print("Cargando el modelo de embeddings. Esto puede tardar unos momentos...")
embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
print("✅ Modelo de embeddings cargado.")

client = chromadb.PersistentClient(path=config.CHROMA_DATA_PATH)
collection = client.get_or_create_collection(name=config.COLLECTION_NAME)

print(f"✅ Colección '{config.COLLECTION_NAME}' cargada con {collection.count()} documentos.")
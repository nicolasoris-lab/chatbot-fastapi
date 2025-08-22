# inspector.py
import chromadb
import traceback
import config

try:
    # 1. Conéctate a tu base de datos
    client = chromadb.PersistentClient(path="./chroma_db")

    # 2. Obtén la colección
    # !!! REEMPLAZA "pdf_documents" si tu colección tiene otro nombre !!!
    collection = client.get_collection(name=config.COLLECTION_NAME)

    print(">>> Obteniendo TODOS los datos de la colección...")

    # 3. Usamos .get() pidiendo explícitamente documentos y metadatos
    # Esto nos mostrará la estructura cruda de lo que hay guardado.
    results = collection.get(
        include=["metadatas", "documents"]
    )

    print("\n>>> ¡Éxito! Esta es la estructura de datos cruda que devuelve ChromaDB:")
    print(results)

except Exception:
    print("\n--- OCURRIÓ UN ERROR ---")
    # Imprime el traceback completo para ver la línea exacta del error
    traceback.print_exc()
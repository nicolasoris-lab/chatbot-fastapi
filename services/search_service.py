# services/search.py
import re
from typing import Optional, List, Dict, Any
from fastapi import HTTPException

from qdrant_client.http import models
from vector_db import client, embedding_model
import config


def extract_key_number(query: str) -> str | None:
    match = re.search(r"(?:ley|decreto|resolucion|ley nro|decreto nro|ley n)\s*([\d\.\-\/]+)", query, re.IGNORECASE)
    if match:
        numero_con_separadores = match.group(1)
        numero_normalizado = re.sub(r'[\.\-\/]', '', numero_con_separadores)
        return numero_normalizado
    return None

def extract_article_number(query: str) -> str | None:
    match = re.search(r"(?:artículo|articulo|art)\.?\s*(\d+)", query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

# --- 💡 FUNCIÓN HELPER PARA FORMATEAR RESULTADOS ---
def _format_qdrant_results(results: List[models.ScoredPoint]) -> Dict[str, Any]:
    """Convierte la salida de Qdrant al formato que esperaba el router (similar a ChromaDB)."""
    if not results:
        return {'documents': [[]], 'metadatas': [[]]}

    documents = []
    metadatas = []
    for point in results:
        # El texto del documento está en el payload, lo extraemos.
        documents.append(point.payload.pop("texto", "")) 
        metadatas.append(point.payload)

    # Devolvemos el formato anidado que el router espera: {'documents': [[doc1, doc2]], ...}
    return {'documents': [documents], 'metadatas': [metadatas]}


# --- ✅ FUNCIÓN DE BÚSQUEDA PRINCIPAL ACTUALIZADA ---
def perform_similarity_search(query: str, n_results: int):
    """Realiza una búsqueda híbrida usando filtros de metadatos para Qdrant."""
    collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
    if collection_info.points_count == 0:
        raise HTTPException(status_code=404, detail="No hay documentos en la base de datos.")

    key_number = extract_key_number(query)
    article_number = extract_article_number(query)

    # Construcción de filtros para Qdrant
    filter_conditions = []
    if key_number:
        filter_conditions.append(models.FieldCondition(
            key="numero_normalizado",
            match=models.MatchValue(value=key_number)
        ))
    if article_number:
        filter_conditions.append(models.FieldCondition(
            key="articulo",
            match=models.MatchValue(value=article_number)
        ))
    
    qdrant_filter = models.Filter(must=filter_conditions) if filter_conditions else None

    if qdrant_filter:
        print(f"Aplicando filtro de metadatos: {qdrant_filter.dict()}")
    else:
        print("No se encontraron filtros. Realizando búsqueda semántica global.")

    query_embedding = embedding_model.encode(query).tolist()
    
    # Primer intento: búsqueda con filtros
    search_results = []
    if qdrant_filter:
        search_results = client.search(
            collection_name=config.COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=qdrant_filter,
            limit=n_results
        )

    # Fallback: si la búsqueda filtrada no arroja resultados, se hace una búsqueda global
    if not search_results:
        if qdrant_filter:
            print("La búsqueda filtrada no encontró nada. Intentando búsqueda semántica global.")
        
        search_results = client.search(
            collection_name=config.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=n_results
        )

    return _format_qdrant_results(search_results)


# --- ✅ FUNCIÓN DE TESTEO DE FILTROS ACTUALIZADA ---
def search_with_filters(filters: dict, n_results: int, query: str = ""):
    """Realiza una búsqueda en Qdrant usando un diccionario de filtros explícito."""
    collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
    if collection_info.points_count == 0:
        raise HTTPException(status_code=404, detail="No hay documentos en la base de datos.")

    filter_conditions = []
    for key, value in filters.items():
        db_key = "numero_normalizado" if key == "numero_documento" else key
        filter_conditions.append(models.FieldCondition(
            key=db_key,
            match=models.MatchValue(value=value)
        ))

    if not filter_conditions:
        raise HTTPException(status_code=400, detail="Se debe proveer al menos un filtro.")

    qdrant_filter = models.Filter(must=filter_conditions)
    print(f"TEST: Aplicando filtro de metadatos explícito: {qdrant_filter.dict()}")

    query_embedding = embedding_model.encode(query if query else " ").tolist()
    
    search_results = client.search(
        collection_name=config.COLLECTION_NAME,
        query_vector=query_embedding,
        query_filter=qdrant_filter,
        limit=n_results
    )

    return _format_qdrant_results(search_results)
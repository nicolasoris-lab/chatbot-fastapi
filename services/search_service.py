# services/search.py
import re
from typing import Optional
from fastapi import HTTPException
from vector_db import collection, embedding_model

def extract_key_number(query: str) -> str | None:
    """Extrae y limpia el número principal de una ley o decreto."""
    # Captura el número completo, ej: "2.675/12"
    match = re.search(r"(?:ley|decreto|resolucion|ley nro|decreto nro|ley n)\s*([\d\.\-\/]+)", query, re.IGNORECASE)
    if match:
        numero_con_separadores = match.group(1)
        # Usa re.sub para eliminar todos los puntos, guiones o barras.
        # "2.675/12" se convierte en "267512"
        numero_normalizado = re.sub(r'[\.\-\/]', '', numero_con_separadores)
        return numero_normalizado
    return None

def extract_article_number(query: str) -> str | None:
    """Extrae el número de un artículo de un texto de consulta."""
    match = re.search(r"(?:artículo|articulo|art)\.?\s*(\d+)", query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def perform_similarity_search(query: str, n_results: int):
    """Realiza una búsqueda híbrida usando filtros de metadatos para ley y/o artículo."""
    if collection.count() == 0:
        raise HTTPException(status_code=404, detail="No hay documentos en la base de datos.")

    key_number = extract_key_number(query)
    article_number = extract_article_number(query)

    where_filter: Optional[dict] = None
    
    conditions = []
    if key_number:
        conditions.append({"numero_normalizado": {"$eq": key_number}})
    if article_number:
        conditions.append({"articulo": {"$eq": article_number}})

    if len(conditions) > 1:
        where_filter = {"$and": conditions}
    elif len(conditions) == 1:
        where_filter = conditions[0]
    
    if where_filter: print(f"Aplicando filtro de metadatos: {where_filter}")
    else: print("No se encontraron filtros. Realizando búsqueda semántica global.")

    query_embedding = embedding_model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results, where=where_filter)
    
    if where_filter and (not results.get('documents') or not results['documents'][0]):
        print("La búsqueda filtrada no encontró nada. Intentando búsqueda semántica global.")
        results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    return results

# --- NUEVA FUNCIÓN PARA TESTEAR FILTROS ---
def search_with_filters(filters: dict, n_results: int, query: str = ""):
    """
    Realiza una búsqueda usando únicamente un diccionario de filtros explícito.
    Diseñada para testing. No tiene lógica de fallback.
    """
    if collection.count() == 0:
        raise HTTPException(status_code=404, detail="No hay documentos en la base de datos.")

    conditions = []
    for key, value in filters.items():
        # Renombramos 'numero_documento' a 'numero_normalizado' para la DB
        db_key = "numero_normalizado" if key == "numero_documento" else key
        conditions.append({db_key: {"$eq": value}})

    where_filter = None
    if len(conditions) > 1:
        where_filter = {"$and": conditions}
    elif len(conditions) == 1:
        where_filter = conditions[0]

    if not where_filter:
        raise HTTPException(status_code=400, detail="Se debe proveer al menos un filtro.")

    print(f"TEST: Aplicando filtro de metadatos explícito: {where_filter}")

    # La búsqueda semántica se hace sobre el texto 'query' opcional
    query_embedding = embedding_model.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding, 
        n_results=n_results, 
        where=where_filter
    )
    
    return results
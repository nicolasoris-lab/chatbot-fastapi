import os
import re
import shutil
import zipfile
from typing import Dict, Any

from fastapi import HTTPException
from pypdf import PdfReader
from vector_db import collection, embedding_model # Asegúrate de que estos se importen correctamente desde tu configuración

# --- 1. FUNCIÓN PARA EXTRAER METADATOS DEL CONTENIDO ---
def extract_document_metadata(text: str) -> Dict[str, Any]:
    """
    Extrae metadatos clave directamente del texto de un documento legal (Versión Definitiva).
    """
    metadata = {
        "tipo_documento": "Desconocido",
        "numero_documento": "S/N",
        "fecha_publicacion": "S/F",
        "organismo_emisor": "No especificado"
    }

    # --- CAMBIO CLAVE: Regex mucho más flexible ---
    # Busca "LEY" o "DECRETO", seguido de cualquier caracter (incluyendo ninguno), 
    # y luego un número que tenga al menos 4 dígitos.
    match = re.search(r"(LEY|DECRETO)\s*.*?\s*([\d\.\-\/]{4,})", text, re.IGNORECASE)
    
    if match:
        metadata["tipo_documento"] = match.group(1).capitalize()
        metadata["numero_documento"] = match.group(2).strip()

    # El resto de las extracciones pueden permanecer igual
    match_fecha = re.search(r"Publicado el día\s*(.*)", text, re.IGNORECASE)
    if match_fecha:
        metadata["fecha_publicacion"] = match_fecha.group(1).strip()
    
    match_org = re.search(r"Ministerio de ([\w\s]+)", text, re.IGNORECASE)
    if match_org:
        metadata["organismo_emisor"] = f"Ministerio de {match_org.group(1).strip()}"

    return metadata

# --- 2. CORAZÓN DEL PROCESAMIENTO: DIVISIÓN LÓGICA Y METADATOS NORMALIZADOS ---
def process_and_embed_pdf(pdf_path: str, original_filename: str):
    """
    Procesa un PDF, extrae metadatos, divide por artículos, normaliza datos clave
    y carga todo en la base de datos vectorial.
    """
    try:
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        
        if not full_text:
            print(f"Advertencia: El archivo {original_filename} está vacío o no se pudo leer el texto.")
            return

        doc_metadata = extract_document_metadata(full_text)
        doc_metadata["nombre_archivo"] = original_filename

        chunks_text = re.split(r'(?=Artículo \d+)', full_text, flags=re.IGNORECASE)
        chunks_text = [chunk.strip() for chunk in chunks_text if chunk and chunk.strip().lower().startswith('artículo')]

        if not chunks_text:
            chunks_text = [full_text]

        metadatas_to_add = []
        ids_to_add = []
        
        for i, chunk in enumerate(chunks_text):
            chunk_metadata = doc_metadata.copy()
            
            # **CAMBIO CLAVE: Normalizar el número de documento para búsqueda exacta**
            if doc_metadata.get("numero_documento") != "S/N":
                normalized_number = re.sub(r'[\.\-\/]', '', doc_metadata["numero_documento"])
                chunk_metadata["numero_normalizado"] = normalized_number

            article_match = re.search(r"Artículo (\d+)", chunk, re.IGNORECASE)
            article_num = article_match.group(1) if article_match else f"parrafo_{i}"
            chunk_metadata["articulo"] = article_num
            
            metadatas_to_add.append(chunk_metadata)
            ids_to_add.append(f"{original_filename}_{article_num}_{i}")
            
        embeddings = embedding_model.encode(chunks_text).tolist()
        print("metadatas_to_add", metadatas_to_add)
        collection.add(
            embeddings=embeddings,
            documents=chunks_text,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"Procesado y añadido '{original_filename}' con {len(chunks_text)} chunks lógicos.")

    except Exception as e:
        print(f"Error procesando el archivo {original_filename}: {e}")


# --- 3. FUNCIÓN PRINCIPAL PARA PROCESAR EL ZIP ---
def process_pdfs_from_zip(zip_path: str):
    try:
        extraction_path = os.path.join(os.path.dirname(zip_path), "extracted")
        if os.path.exists(extraction_path):
            shutil.rmtree(extraction_path)
        os.makedirs(extraction_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_path)

        pdf_files = [f for f in os.listdir(extraction_path) if f.lower().endswith(".pdf")]
        if not pdf_files:
            return 0

        for pdf_file in pdf_files:
            pdf_path = os.path.join(extraction_path, pdf_file)
            process_and_embed_pdf(pdf_path, pdf_file)

        shutil.rmtree(extraction_path)
        return len(pdf_files)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo subido no es un ZIP válido.")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


# --- 4. FUNCIÓN DE BÚSQUEDA USANDO METADATOS NORMALIZADOS ---
def perform_similarity_search(query: str, n_results: int):
    """
    Realiza una búsqueda híbrida usando filtros de metadatos para ley y/o artículo.
    """
    if collection.count() == 0:
        raise HTTPException(status_code=404, detail="No hay documentos en la base de datos.")

    # <-- 1. EXTRAEMOS AMBOS NÚMEROS
    key_number = extract_key_number(query)
    article_number = extract_article_number(query)
    
    where_filter = {}
    conditions = []

    # <-- 2. CONSTRUIMOS UNA LISTA DE CONDICIONES
    if key_number:
        print(f"Número de ley encontrado: '{key_number}'.")
        conditions.append({"numero_normalizado": {"$eq": key_number}})

    if article_number:
        print(f"Número de artículo encontrado: '{article_number}'.")
        conditions.append({"articulo": {"$eq": article_number}})

    # <-- 3. ARMAMOS EL FILTRO FINAL
    if len(conditions) > 1:
        # Si hay más de una condición, las unimos con un "Y" lógico ($and)
        where_filter = {"$and": conditions}
    elif len(conditions) == 1:
        # Si solo hay una, la usamos directamente
        where_filter = conditions[0]
    
    if where_filter:
        print(f"Aplicando filtro de metadatos: {where_filter}")
    else:
        print("No se encontraron filtros. Realizando búsqueda semántica global.")

    query_embedding = embedding_model.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter 
    )
    
    # Lógica de fallback si la búsqueda filtrada no arroja resultados
    if where_filter and (not results.get('documents') or not results['documents'][0]):
        print("La búsqueda filtrada no encontró nada. Intentando búsqueda semántica global.")
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

    return results


# --- 5. FUNCIÓN AUXILIAR PARA EXTRAER NÚMEROS DE LA CONSULTA ---
def extract_key_number(query: str) -> str | None:
    """
    Extrae el número principal de una ley o decreto y lo devuelve normalizado (sin puntos ni barras).
    """
    match = re.search(r"(?:ley|decreto|resolucion|ley nro|decreto nro|ley n)\s*([\d\.\-\/]+)", query, re.IGNORECASE)
    if match:
        # **CORRECCIÓN:** Normaliza el número aquí mismo para que "7.675" se convierta en "7675"
        number_str = match.group(1)
        return re.sub(r'[\.\-\/]', '', number_str)
    return None

def extract_article_number(query: str) -> str | None:
    """
    Extrae el número de un artículo de un texto de consulta.
    Ej: "qué dice el artículo 5" -> "5"
    """
    # Busca patrones como "artículo 5", "articulo 5", "art. 5", "art 5"
    match = re.search(r"(?:artículo|articulo|art)\.?\s*(\d+)", query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None
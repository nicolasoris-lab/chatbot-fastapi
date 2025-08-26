# services/ingestion.py
import os
import re
import shutil
import uuid
import zipfile
from typing import Dict, Any, List

from fastapi import HTTPException
from pypdf import PdfReader
from qdrant_client.http.models import PointStruct

import config
from vector_db import client, embedding_model

# --- NUEVA FUNCIÓN AUXILIAR PARA CHUNKING ---
def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Divide un texto largo en chunks de tamaño aproximado `chunk_size` con superposición.
    Prioriza dividir por párrafos para mantener el contexto.
    """
    if not text:
        return []

    # Primero, divide el texto en párrafos
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Si añadir el nuevo párrafo excede el tamaño, guardamos el chunk actual
        if len(current_chunk) + len(paragraph) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk)
            # Empezamos un nuevo chunk con superposición (última parte del chunk anterior)
            overlap_text = current_chunk[-chunk_overlap:]
            current_chunk = overlap_text + " ... " + paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph

    # No olvides añadir el último chunk que se estaba construyendo
    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def extract_document_metadata(text: str) -> Dict[str, Any]:
    """Extrae metadatos clave directamente del texto de un documento legal."""
    metadata = {
        "tipo_documento": "Desconocido", "numero_documento": "S/N",
        "fecha_publicacion": "S/F", "organismo_emisor": "No especificado"
    }
    match = re.search(r"(LEY|DECRETO|RESOLUCION)\s*.*?\s*([\d\.\-\/]{4,})", text, re.IGNORECASE)
    if match:
        metadata["tipo_documento"] = match.group(1).capitalize()
        metadata["numero_documento"] = match.group(2).strip()
    match_fecha = re.search(r"Publicado el día\s*(.*)", text, re.IGNORECASE)
    if match_fecha:
        metadata["fecha_publicacion"] = match_fecha.group(1).strip()
    match_org = re.search(r"Ministerio de ([\w\s]+)", text, re.IGNORECASE)
    if match_org:
        metadata["organismo_emisor"] = f"Ministerio de {match_org.group(1).strip()}"
    return metadata

def process_and_embed_pdf(pdf_path: str, original_filename: str):
    """Procesa un PDF ESTRUCTURADO (ley, decreto), lo divide por artículos y lo carga."""
    try:
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        
        print(f"\n--- [LEY/DECRETO] Procesando: {original_filename} ---")
        if not full_text.strip():
            print("❌ Error: El archivo está vacío o no se pudo extraer texto.")
            return

        print(f"✅ Texto extraído: {len(full_text)} caracteres.")
        doc_metadata = extract_document_metadata(full_text)
        doc_metadata["nombre_archivo"] = original_filename

        article_pattern = r'(?=Artículo\s*[\dºª]+\b)'
        chunks_text_raw = re.split(article_pattern, full_text, flags=re.IGNORECASE)
        #chunks_text = [chunk.strip() for chunk in chunks_text_raw if chunk.strip()]

        min_chunk_length = 50 # Define un mínimo de caracteres para que un chunk sea válido

        chunks_text = [
            chunk.strip() for chunk in chunks_text_raw 
            if chunk.strip() and len(chunk.strip()) > min_chunk_length
        ]
        
        print(f"📑 Documento dividido en {len(chunks_text)} chunks lógicos por artículo.")
        if not chunks_text:
            print(f"⚠️ Advertencia: No se generaron chunks válidos para '{original_filename}'.")
            return

        embeddings = embedding_model.encode(chunks_text).tolist()
        points_to_add = []
        for i, chunk in enumerate(chunks_text):
            chunk_metadata = doc_metadata.copy()
            
            if doc_metadata.get("numero_documento") != "S/N":
                numero_normalizado = re.sub(r'[\.\-\/]', '', doc_metadata["numero_documento"])
                chunk_metadata["numero_normalizado"] = numero_normalizado
            
            article_match = re.search(r"Artículo (\d+)", chunk, re.IGNORECASE)
            article_num = article_match.group(1) if article_match else f"parrafo_{i}"
            chunk_metadata["articulo"] = article_num
            chunk_metadata["texto"] = chunk
            
            unique_string_id = f"{original_filename}_{article_num}_{i}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string_id))

            points_to_add.append(
                PointStruct(id=point_id, vector=embeddings[i], payload=chunk_metadata)
            )
        
        print(f"📦 Preparando para subir {len(points_to_add)} puntos a Qdrant.")
        if points_to_add:
            client.upsert(
                collection_name=config.COLLECTION_NAME,
                points=points_to_add,
                wait=True
            )
            print(f"✔️ Carga a Qdrant completada para '{original_filename}'.")

    except Exception as e:
        print(f"❌ Error fatal procesando el archivo {original_filename}: {e}")

# --- FUNCIÓN DE CONTEXTO ---
def process_and_embed_pdf_context(pdf_path: str, original_filename: str):
    """Procesa un PDF DE CONTEXTO, lo divide semánticamente y lo carga en Qdrant."""
    try:
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        
        print(f"\n--- [CONTEXTO] Procesando: {original_filename} ---")
        if not full_text.strip():
            print("❌ Error: El archivo está vacío o no se pudo extraer texto.")
            return

        print(f"✅ Texto extraído: {len(full_text)} caracteres.")

        subtema = ""

        if "Convenios" in original_filename:
            subtema = "Convenios"

        if "Autoridades" in original_filename:
            subtema = "Autoridades"

        if "Mision" in original_filename:
            subtema = "Mision"

        if "DGR" in original_filename:
            subtema = "DGR"
        
        # 1. Definir los metadatos básicos para este documento de contexto.
        doc_metadata = {
            "tipo_documento": "Contexto", # ¡Metadato clave!
            "nombre_archivo": original_filename,
            "subtema": subtema
        }

        # 2. Dividir el texto usando la nueva función semántica.
        chunks_text = split_text_into_chunks(full_text, chunk_size=1200, chunk_overlap=200)
        
        print(f"📑 Documento dividido en {len(chunks_text)} chunks semánticos.")
        if not chunks_text:
            print(f"⚠️ Advertencia: No se generaron chunks para '{original_filename}'.")
            return
        
        # 3. Generar embeddings y crear los puntos para Qdrant.
        embeddings = embedding_model.encode(chunks_text).tolist()
        points_to_add = []
        for i, chunk in enumerate(chunks_text):
            chunk_metadata = doc_metadata.copy()
            chunk_metadata["texto"] = chunk
            
            # Generamos un ID único para cada chunk de contexto
            unique_string_id = f"{original_filename}_context_{i}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string_id))

            points_to_add.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[i],
                    payload=chunk_metadata
                )
            )

        print(f"📦 Preparando para subir {len(points_to_add)} puntos a Qdrant.")
        if points_to_add:
            client.upsert(
                collection_name=config.COLLECTION_NAME,
                points=points_to_add,
                wait=True
            )
            print(f"✔️ Carga a Qdrant completada para '{original_filename}'.")

    except Exception as e:
        print(f"❌ Error fatal procesando el archivo {original_filename}: {e}")


def process_pdfs_from_zip(zip_path: str, is_context: bool = False):
    """Función principal que orquesta la extracción y procesamiento de un ZIP."""
    try:
        extraction_path = os.path.join(os.path.dirname(zip_path), "extracted")
        if os.path.exists(extraction_path): shutil.rmtree(extraction_path)
        os.makedirs(extraction_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_path)

        pdf_files = [f for f in os.listdir(extraction_path) if f.lower().endswith(".pdf")]
        if not pdf_files: return 0

        for pdf_file in pdf_files:
            pdf_path = os.path.join(extraction_path, pdf_file)
            
            if is_context:
                process_and_embed_pdf_context(pdf_path, pdf_file)
            else:
                process_and_embed_pdf(pdf_path, pdf_file)

        shutil.rmtree(extraction_path)
        return len(pdf_files)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo subido no es un ZIP válido.")
    finally:
        if os.path.exists(zip_path): os.remove(zip_path)
# services/ingestion.py
import os
import re
import shutil
import zipfile
from typing import Dict, Any

from fastapi import HTTPException
from pypdf import PdfReader
from vector_db import client, embedding_model
from qdrant_client.http.models import PointStruct
import config

import uuid

def extract_document_metadata(text: str) -> Dict[str, Any]:
    """Extrae metadatos clave directamente del texto de un documento legal."""
    metadata = {
        "tipo_documento": "Desconocido", "numero_documento": "S/N",
        "fecha_publicacion": "S/F", "organismo_emisor": "No especificado"
    }
    # Expresión regular mejorada para capturar LEY, DECRETO o RESOLUCION
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
    """Procesa un PDF, extrae metadatos, lo divide y lo carga en Qdrant."""
    try:
        # ... (toda la lógica de lectura y chunking que ya corregimos se mantiene igual) ...
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        
        print(f"\n--- Procesando: {original_filename} ---")
        if not full_text.strip():
            print("❌ Error: El archivo está vacío o no se pudo extraer texto.")
            return

        print(f"✅ Texto extraído: {len(full_text)} caracteres.")
        doc_metadata = extract_document_metadata(full_text)
        doc_metadata["nombre_archivo"] = original_filename

        # Chunking logico
        # PCrea chunks en base a los articulos
        chunks_text_raw = re.split(r'(?=Artículo \d+)', full_text, flags=re.IGNORECASE)
        chunks_text = [chunk.strip() for chunk in chunks_text_raw if chunk.strip()]
        
        print(f"📑 Documento dividido en {len(chunks_text)} chunks lógicos.")

        if not chunks_text:
            print(f"⚠️ Advertencia: No se generaron chunks para '{original_filename}'. Saltando archivo.")
            return

        embeddings = embedding_model.encode(chunks_text).tolist()

        points_to_add = []
        for i, chunk in enumerate(chunks_text):
            chunk_metadata = doc_metadata.copy()
            
            # ... (la lógica de metadatos se mantiene igual) ...
            if doc_metadata.get("numero_documento") != "S/N":
                numero_con_separadores = doc_metadata["numero_documento"]
                numero_normalizado = re.sub(r'[\.\-\/]', '', numero_con_separadores)
                chunk_metadata["numero_normalizado"] = numero_normalizado
            
            article_match = re.search(r"Artículo (\d+)", chunk, re.IGNORECASE)
            article_num = article_match.group(1) if article_match else f"parrafo_{i}"
            chunk_metadata["articulo"] = article_num
            
            chunk_metadata["texto"] = chunk
            
            # --- ✅ 2. LÓGICA DE ID CORREGIDA ---
            # Primero, creamos la misma cadena de texto única que antes.
            unique_string_id = f"{original_filename}_{article_num}_{i}"
            
            # Luego, la convertimos a un UUID válido usando un "namespace".
            # Esto garantiza que la misma cadena siempre genere el mismo UUID.
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string_id))

            points_to_add.append(
                PointStruct(
                    id=point_id, # Usamos el nuevo ID en formato UUID
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
            print(f"✔️  Carga a Qdrant completada para '{original_filename}'.")

    except Exception as e:
        print(f"❌ Error fatal procesando el archivo {original_filename}: {e}")

def process_pdfs_from_zip(zip_path: str):
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
            process_and_embed_pdf(pdf_path, pdf_file)

        shutil.rmtree(extraction_path)
        return len(pdf_files)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo subido no es un ZIP válido.")
    finally:
        if os.path.exists(zip_path): os.remove(zip_path)
# services/ingestion.py
import os
import re
import shutil
import zipfile
from typing import Dict, Any

from fastapi import HTTPException
from pypdf import PdfReader
from vector_db import collection, embedding_model

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
    """Procesa un PDF, extrae metadatos, lo divide y lo carga en la DB vectorial."""
    try:
        # ... (código de lectura de PDF y extracción de metadatos sin cambios) ...
        reader = PdfReader(pdf_path)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        
        if not full_text:
            return

        doc_metadata = extract_document_metadata(full_text)
        doc_metadata["nombre_archivo"] = original_filename


        # Chunking logico por articulos
        # Usa la frase "Artículo X" como marcador para cortar el texto
        chunks_text = re.split(r'(?=Artículo \d+)', full_text, flags=re.IGNORECASE)
        chunks_text = [chunk.strip() for chunk in chunks_text if chunk and chunk.strip().lower().startswith('artículo')]
        if not chunks_text: chunks_text = [full_text]

        metadatas_to_add, ids_to_add = [], []
        for i, chunk in enumerate(chunks_text):
            chunk_metadata = doc_metadata.copy()
            
            # --- ✅ LÓGICA DE NORMALIZACIÓN MODIFICADA ---
            if doc_metadata.get("numero_documento") != "S/N":
                # Tomamos el número con puntos/barras (ej: "7675/11")
                numero_con_separadores = doc_metadata["numero_documento"]
                
                # Usamos re.sub para eliminar todos los puntos, guiones o barras.
                # "7675/11" se convierte en "767511"
                numero_normalizado = re.sub(r'[\.\-\/]', '', numero_con_separadores)
                
                # Asignamos directamente el número limpio y completo.
                chunk_metadata["numero_normalizado"] = numero_normalizado
            
            article_match = re.search(r"Artículo (\d+)", chunk, re.IGNORECASE)
            article_num = article_match.group(1) if article_match else f"parrafo_{i}"
            chunk_metadata["articulo"] = article_num
            
            metadatas_to_add.append(chunk_metadata)
            ids_to_add.append(f"{original_filename}_{article_num}_{i}")
        
        if not chunks_text:
            print(f"Advertencia: No se generaron chunks para '{original_filename}'. Saltando archivo.")
            return

        embeddings = embedding_model.encode(chunks_text).tolist()
        collection.add(
            embeddings=embeddings, documents=chunks_text,
            metadatas=metadatas_to_add, ids=ids_to_add
        )
        print(f"Procesado y añadido '{original_filename}' con {len(chunks_text)} chunks lógicos.")
    except Exception as e:
        print(f"Error procesando el archivo {original_filename}: {e}")

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
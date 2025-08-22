import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException

import config
from services import process_pdfs_from_zip
from vector_db import client

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@router.post("/upload/", summary="Cargar ZIP con PDFs")
async def upload_documents(file: UploadFile = File(...)):
    if file.content_type != "application/zip":
        raise HTTPException(status_code=400, detail="El archivo debe ser de tipo .zip")

    file_path = os.path.join(config.TEMP_UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    processed_count = process_pdfs_from_zip(file_path)

    # Obtiene la información de la colección para el conteo
    collection_info = client.get_collection(collection_name=config.COLLECTION_NAME)
    
    return {
        "message": f"{processed_count} archivos PDF procesados exitosamente.",
        "collection_count": f"La colección ahora tiene {collection_info.points_count} documentos.",
    }

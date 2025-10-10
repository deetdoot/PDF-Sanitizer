from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import io
from typing import List, Optional
import logging
import os
import pika
import json


def validate_file(file_content: bytes, filename: str) -> bool:
    """Validate if the file is a PDF or PNG"""
    try:
        # Check PDF magic number
        if file_content[:4] == b'%PDF':
            return True
        # Check PNG magic number (89 50 4E 47 0D 0A 1A 0A)
        if file_content[:8] == b'\x89PNG\r\n\x1a\n':
            return True
        return False
    except Exception:
        return False


async def upload_file(file: UploadFile = File(...), job_id: str = ""):
    """
    Upload a PDF or PNG file for processing

    - **file**: PDF or PNG file to upload
    """
    try:
        # Validate file type by extension
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in ['pdf', 'png']:
            raise HTTPException(status_code=400, detail="Only PDF and PNG files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        # Validate file content
        if not validate_file(file_content, file.filename):
            raise HTTPException(status_code=400, detail="Invalid file format")
        
        # Create file-like object
        file_buffer = io.BytesIO(file_content)

        upload_dir = "./uploads"
        upload_path = f"{upload_dir}/{job_id}.{file_extension}"

        # Ensure the upload directory exists
        os.makedirs(upload_dir, exist_ok=True)

        with open(upload_path, "wb") as f:
            f.write(file_buffer.getbuffer())

        return JSONResponse(
            content={
                "success": True,
                "message": f"{file_extension.upper()} File Upload Successful",
                "file_id": job_id,
                "file_type": file_extension,
                "filename": file.filename
            }
        )
        
    except HTTPException:
        raise

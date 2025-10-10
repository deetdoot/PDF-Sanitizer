from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import io
from typing import List, Optional
import logging
import os


def validate_pdf_file(file_content: bytes) -> bool:
    """Validate if the file is a PDF"""
    try:
        # Check PDF magic number
        if file_content[:4] == b'%PDF':
            return True
        return False
    except Exception:
        return False


async def upload_pdf(file: UploadFile = File(...), job_id: str = ""):
    """
    Upload a PDF file and extract its text content

    - **file**: PDF file to upload
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        # Validate PDF content
        if not validate_pdf_file(file_content):
            raise HTTPException(status_code=400, detail="Invalid PDF file")
        
        # Create file-like object
        pdf_file = io.BytesIO(file_content)
        
        # Save the file to a directory (e.g., ./uploads/)
        # Generate a unique UUID for the file name

        upload_dir = "./uploads"
        upload_path = f"{upload_dir}/{job_id}.pdf"

        # Ensure the upload directory exists
        os.makedirs(upload_dir, exist_ok=True)

        with open(upload_path, "wb") as f:
            f.write(pdf_file.getbuffer())


        return JSONResponse(
            content={
                "success": True,
                "message": "PDF File Upload Successful",
                "file_id": job_id
            }
        )
        
    except HTTPException:
        raise

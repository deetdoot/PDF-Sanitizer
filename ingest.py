from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import io
from typing import List, Optional
import logging
from upload_module.upload_pdf import upload_file
import pika, json
import uvicorn
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Reader API",
    description="A FastAPI application for reading and extracting text from PDF files",
    version="1.0.0"
)

#Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Ensure the 'ocr' queue exists
channel.queue_declare(queue='file_upload', durable=True)


# API Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "PDF Reader API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload-file/",
            "url": "/read-pdf-from-url/",
            "health": "/health/"
        }
    }

@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "PDF Reader API is running"}

@app.post("/upload-file/")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF file and extract its text content
    
    - **file**: PDF file to upload
    """

    job_id = str(uuid.uuid4())
    # Prepare your message
    file_ext = file.filename.split('.')[-1]
    pdf_job = {
        'job_id': job_id,
        'file_path': f'./uploads/{job_id}.{file_ext}'
    }

    # Publish it to RabbitMQ
    channel.basic_publish(
        exchange='',
        routing_key='file_upload',
        body=json.dumps(pdf_job),
        properties=pika.BasicProperties(
            delivery_mode=2  # make message persistent
        )
    )

    print("Sent job to file_upload queue:", pdf_job)
    #connection.close()


    return await upload_file(file, job_id)


if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

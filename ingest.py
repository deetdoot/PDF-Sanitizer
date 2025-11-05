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
import os
import time
from dotenv import load_dotenv

load_dotenv()  # load variables from .env into os.environ

# Prefer BACKEND_PORT, fall back to PORT, default to 8000
PORT = int(os.environ.get("BACKEND_PORT") or os.environ.get("PORT") or 8000)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Reader API",
    description="A FastAPI application for reading and extracting text from PDF files",
    version="1.0.0"
)

# RabbitMQ configuration
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')

print(RABBITMQ_HOST, RABBITMQ_PASS, RABBITMQ_PORT, RABBITMQ_USER)


# Global variables for RabbitMQ connection
connection = None
channel = None

def get_rabbitmq_connection(max_retries=10, retry_delay=5):
    """Get RabbitMQ connection with retry logic"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Connection attempt {attempt + 1}/{max_retries} to {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            conn = pika.BlockingConnection(parameters)
            logger.info(f"✓ Successfully connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return conn
        except pika.exceptions.AMQPConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"✗ Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.warning(f"   Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"✗ Failed to connect to RabbitMQ after {max_retries} attempts")
                logger.error(f"   Last error: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"✗ Unexpected error connecting to RabbitMQ: {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                logger.warning(f"   Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise

@app.on_event("startup")
async def startup_event():
    """Initialize RabbitMQ connection on startup"""
    global connection, channel
    logger.info(f"Starting up... Environment variables:")
    logger.info(f"  RABBITMQ_HOST: {RABBITMQ_HOST}")
    logger.info(f"  RABBITMQ_PORT: {RABBITMQ_PORT}")
    logger.info(f"  RABBITMQ_USER: {RABBITMQ_USER}")
    logger.info(f"Attempting to connect to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Ensure the 'file_upload' queue exists
    channel.queue_declare(queue='file_upload', durable=True)
    logger.info("✓ RabbitMQ connection initialized and queue declared")

@app.on_event("shutdown")
async def shutdown_event():
    """Close RabbitMQ connection on shutdown"""
    global connection
    if connection and not connection.is_closed:
        connection.close()
        logger.info("✓ RabbitMQ connection closed")


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
    """Health check endpoint for Docker healthcheck"""
    rabbitmq_connected = connection is not None and not connection.is_closed if connection else False
    return {
        "status": "healthy",
        "message": "PDF Reader API is running",
        "rabbitmq_connected": rabbitmq_connected,
        "rabbitmq_host": RABBITMQ_HOST,
        "rabbitmq_port": RABBITMQ_PORT
    }

@app.post("/upload-file/")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF file and extract its text content
    
    - **file**: PDF file to upload
    """
    global channel, connection
    
    # Check if RabbitMQ is connected
    if not channel or not connection or connection.is_closed:
        raise HTTPException(status_code=503, detail="RabbitMQ connection not available")

    job_id = str(uuid.uuid4())
    # Prepare your message
    file_ext = file.filename.split('.')[-1]
    pdf_job = {
        'job_id': job_id,
        'file_path': f'./uploads/{job_id}.{file_ext}'
    }

    try:
        # Publish it to RabbitMQ
        channel.basic_publish(
            exchange='',
            routing_key='file_upload',
            body=json.dumps(pdf_job),
            properties=pika.BasicProperties(
                delivery_mode=2  # make message persistent
            )
        )

        logger.info(f"Sent job to file_upload queue: {pdf_job}")
        
        return await upload_file(file, job_id)
    except Exception as e:
        logger.error(f"Error publishing to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")




if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)

# PII Detection and Redaction Pipeline

A FastAPI-based document processing pipeline that detects and redacts Personally Identifiable Information (PII) from PDF and image files using OCR and LLM-powered analysis.

## Features

- 📄 Upload PDF or PNG files for PII detection and redaction
- 🔍 OCR text extraction using PaddleOCR
- 🤖 AI-powered PII detection using Ollama (llama3.2)
- 🎯 Automatic redaction with calculated bounding boxes
- 🔄 RabbitMQ-based asynchronous processing pipeline
- � Structured JSON output with detection metadata
- 🚀 Fast and scalable multi-consumer architecture

## Prerequisites

- Python 3.11+
- RabbitMQ (message broker)
- Ollama with llama3.2 model installed

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/deetdoot/753-Final-Project.git
cd 753-Final-Project
```

### 2. Make Consumer Scripts Executable
```bash
cd consumers
chmod +x upload_consumer.py
chmod +x ocr_consumer.py
chmod +x llm_engine_consumer.py
chmod +x redactor_consumer.py
cd ..
```

### 3. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Start Required Services

**Start RabbitMQ:**
```bash
# Using Docker (recommended)
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management

# Or install locally and start the service
```

**Start Ollama with llama3.2:**
```bash
# Make sure Ollama is installed and running
ollama pull llama3.2
ollama serve
```

### 6. Start the Pipeline Components

Open **4 separate terminal windows** and activate the virtual environment in each:

**Terminal 1 - FastAPI Backend:**
```bash
source .venv/bin/activate
python ingest.py
```

**Terminal 2 - Upload Consumer:**
```bash
source .venv/bin/activate
cd consumers
python upload_consumer.py
```

**Terminal 3 - OCR Consumer:**
```bash
source .venv/bin/activate
cd consumers
python ocr_consumer.py
```

**Terminal 4 - LLM Engine Consumer:**
```bash
source .venv/bin/activate
cd consumers
python llm_engine_consumer.py
```

**Terminal 5 - Redactor Consumer:**
```bash
source .venv/bin/activate
cd consumers
python redactor_consumer.py
```

The FastAPI server will be available at: `http://localhost:5005`

## Usage

### 1. Access the API Documentation

Navigate to `http://localhost:5005/docs` in your browser to access the interactive Swagger UI.

### 2. Upload a File for PII Detection and Redaction

In the Swagger UI:
1. Click on **POST /upload-file**
2. Click **"Try it out"**
3. Choose a PDF or PNG file containing PII
4. Click **"Execute"**

**Example using curl:**
```bash
curl -X POST "http://localhost:5005/upload-file" \
  -F "file=@/path/to/your/document.pdf"
```

### 3. Check the Results

The pipeline will process your file through multiple stages:
1. **Upload** → File saved to `uploads/` folder
2. **OCR** → Text extraction, results in `consumers/output/{job_id}/`
3. **LLM Engine** → PII detection, results in `consumers/output/{job_id}/`
4. **Redactor** → Redacted file saved to `uploads/{filename}_redacted.{ext}`

**Output Locations:**
- **Redacted Files**: `uploads/{job_id}_redacted.pdf` or `uploads/{job_id}_redacted.png`
- **PII Detection JSON**: `consumers/output/{job_id}/pii_detections_{job_id}_res.json`
- **OCR Results**: `consumers/output/{job_id}/{job_id}_res.json`

## Example Input & Output

### Input Document
<img width="500" height="750" alt="a83e7c11-3e95-4856-ac29-e3d723f883ed" src="https://github.com/user-attachments/assets/a1c29c44-6cb8-4843-b7f6-94e299a189c4" />

### Redacted Output
<img width="500" height="750" alt="a83e7c11-3e95-4856-ac29-e3d723f883ed_redacted" src="https://github.com/user-attachments/assets/3b166625-8a57-45e6-8bad-3f0d3e6118a8" />

## Pipeline Architecture

The system uses a multi-stage processing pipeline with RabbitMQ queues:

```
FastAPI Upload
      ↓
[file_upload queue] → Upload Consumer → Saves file
      ↓
[ocr queue] → OCR Consumer → Extracts text (PaddleOCR)
      ↓
[llm_engine queue] → LLM Consumer → Detects PII (Ollama)
      ↓
[redactor queue] → Redactor Consumer → Redacts PII
      ↓
Final redacted file in uploads/
```

## API Endpoints

### 1. Health Check
- **GET** `/health`
- Returns the health status of the API and RabbitMQ connection

### 2. Upload File for PII Detection
- **POST** `/upload-file`
- Upload a PDF or PNG file for PII detection and redaction

**Parameters:**
- `file`: PDF or PNG file (form-data)

**Response:**
```json
{
  "message": "File uploaded successfully",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "file_path": "uploads/550e8400-e29b-41d4-a716-446655440000.pdf"
}
```

## PII Detection Categories

The system detects the following types of PII:

- 👤 **PERSON**: Names (full, partial, initials with surnames)
- 🎂 **AGE**: Age mentions and phrases
- 📧 **EMAIL**: Email addresses
- 📱 **PHONE**: Phone numbers and cell numbers
- 🆔 **SSN**: Social Security Numbers
- 🔢 **ACCOUNT_NUMBER**: Account numbers, license numbers
- 📍 **ADDRESS**: Street addresses
- 🌍 **LOCATION**: Cities, states, ZIP codes, GPS coordinates
- 💰 **FINANCIAL**: Bank info, credit cards, financial amounts
- ❓ **OTHER**: Other sensitive information

## Output Format

### PII Detection JSON
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_file": "/path/to/ocr/result.json",
  "total_text_blocks": 25,
  "total_pii_detections": 4,
  "categories_found": ["PERSON", "PHONE", "ADDRESS", "FINANCIAL"],
  "detections": [
    {
      "block_index": 6,
      "original_text": "Name: Jennifer Adams",
      "category": "PERSON",
      "detected_text": "Jennifer Adams",
      "bbox": [73, 223, 160, 237],
      "calculation_method": "calculated_single_block"
    }
  ]
}
```

## Interactive API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:5005/docs`
- **ReDoc**: `http://localhost:5005/redoc`

## Technologies Used

### Core Technologies
- **FastAPI**: High-performance web framework
- **RabbitMQ**: Message broker for queue-based processing
- **PaddleOCR**: Advanced OCR engine for text extraction
- **Ollama**: Local LLM inference with llama3.2
- **PyMuPDF (fitz)**: PDF processing and manipulation
- **Pillow**: Image processing and redaction

### Python Libraries
- **pika**: RabbitMQ client
- **requests**: HTTP client for Ollama API
- **aiofiles**: Async file operations
- **python-multipart**: File upload support
- **Pydantic**: Data validation

## Bounding Box Calculation

The system uses an intelligent string-based approach to calculate bounding boxes:

1. **Combines all OCR text** into a full string
2. **Finds detected PII position** using string indexing
3. **Calculates proportional coordinates** based on character position within text blocks
4. **Supports multi-block spanning** for PII that crosses multiple text regions

This approach provides more accurate redaction than relying solely on OCR block boundaries.

## Troubleshooting

### RabbitMQ Connection Issues
```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# View RabbitMQ logs
docker logs rabbitmq

# Restart RabbitMQ
docker restart rabbitmq
```

### Ollama Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull llama3.2 model
ollama pull llama3.2

# Restart Ollama service
ollama serve
```

### Check Queue Status
Visit RabbitMQ management UI: `http://localhost:15672`
- Username: `guest`
- Password: `guest`

## Project Structure

```
753-Final-Project/
├── ingest.py                 # FastAPI backend server
├── requirements.txt          # Python dependencies
├── uploads/                  # Uploaded and redacted files
├── consumers/
│   ├── upload_consumer.py   # File upload handler
│   ├── ocr_consumer.py      # OCR processing
│   ├── llm_engine_consumer.py  # PII detection
│   ├── redactor_consumer.py # Redaction processing
│   └── output/              # Processing results
├── sanitizer/
│   ├── llm_prompt.py        # LLM PII detection logic
│   ├── redactor.py          # Redaction implementation
│   └── output/              # Detection results
└── converters/              # Data conversion utilities
```

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on the GitHub repository.


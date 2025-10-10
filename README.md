# PDF Reader API

A FastAPI application for reading and extracting text from PDF files via API calls.

## Features

- 📄 Upload PDF files and extract text content
- 🌐 Download and read PDFs from URLs
- 🔧 Two extraction methods: PyPDF2 and pdfplumber
- ✅ Input validation and error handling
- 📊 Metadata extraction (title, author, page count, etc.)
- 🚀 Fast and asynchronous processing

## Installation

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## API Endpoints

### 1. Root Endpoint
- **GET** `/`
- Returns API information and available endpoints

### 2. Health Check
- **GET** `/health`
- Returns the health status of the API

### 3. Upload PDF File
- **POST** `/upload-pdf/`
- Upload a PDF file and extract its text content

**Parameters:**
- `file`: PDF file (form-data)
- `extraction_method`: "PyPDF2" or "pdfplumber" (optional, default: "pdfplumber")

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/upload-pdf/" \
  -F "file=@/path/to/your/document.pdf" \
  -F "extraction_method=pdfplumber"
```

### 4. Read PDF from URL
- **POST** `/read-pdf-from-url/`
- Download a PDF from a URL and extract its text content

**Request Body:**
```json
{
  "url": "https://example.com/document.pdf",
  "extraction_method": "pdfplumber"
}
```

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/read-pdf-from-url/" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "extraction_method": "pdfplumber"
  }'
```

## Response Format

All endpoints return a JSON response with the following structure:

```json
{
  "success": true,
  "message": "PDF processed successfully",
  "text_content": "Extracted text content from the PDF...",
  "page_count": 5,
  "metadata": {
    "method": "pdfplumber",
    "title": "Document Title",
    "author": "Document Author",
    "subject": "Document Subject",
    "filename": "document.pdf",
    "file_size": 1024000
  }
}
```

## Extraction Methods

### PyPDF2
- Fast and lightweight
- Good for simple text extraction
- May have issues with complex layouts

### pdfplumber (Recommended)
- More accurate text extraction
- Better handling of tables and complex layouts
- Slightly slower than PyPDF2

## Interactive API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Error Handling

The API includes comprehensive error handling:
- File validation (PDF format check)
- URL validation and download errors
- Text extraction errors
- Proper HTTP status codes and error messages

## Examples

### Python Example
```python
import requests

# Read PDF from URL
response = requests.post(
    "http://localhost:8000/read-pdf-from-url/",
    json={
        "url": "https://example.com/document.pdf",
        "extraction_method": "pdfplumber"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Extracted text: {data['text_content']}")
    print(f"Page count: {data['page_count']}")
else:
    print(f"Error: {response.json()}")
```

### JavaScript Example
```javascript
// Upload PDF file
const formData = new FormData();
formData.append('file', pdfFile);
formData.append('extraction_method', 'pdfplumber');

fetch('http://localhost:8000/upload-pdf/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Extracted text:', data.text_content);
    console.log('Page count:', data.page_count);
})
.catch(error => console.error('Error:', error));
```

## Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- PyPDF2: PDF processing library
- pdfplumber: Advanced PDF text extraction
- Requests: HTTP client for downloading PDFs
- Pydantic: Data validation
- python-multipart: File upload support
- aiofiles: Async file operations

## License

This project is open source and available under the MIT License.
# Pipeline Management Scripts

This directory contains several scripts to help you manage the document processing pipeline easily.

## Available Scripts

### 1. `simple_start.py` (Recommended)
**The easiest way to start all consumers**

```bash
python simple_start.py
```

**Features:**
- ✅ Simple and reliable
- ✅ Opens each consumer in a separate Terminal window (macOS)
- ✅ Easy to monitor each consumer individually
- ✅ Clear status messages
- ✅ Works cross-platform

### 2. `start_pipeline.py` (Advanced)
**Full-featured pipeline manager with monitoring**

```bash
python start_pipeline.py [options]
```

**Options:**
- `-v, --verbose` - Enable verbose logging
- `--stop-on-error` - Stop if any consumer fails to start  
- `--delay SECONDS` - Delay between starting each consumer (default: 2)

**Features:**
- ✅ Advanced process monitoring
- ✅ Graceful shutdown handling
- ✅ Comprehensive error handling
- ✅ Process monitoring and auto-restart detection
- ✅ Signal handling (Ctrl+C)

**Examples:**
```bash
python start_pipeline.py                 # Default settings
python start_pipeline.py -v              # Verbose output
python start_pipeline.py --delay 5       # 5 second delay between starts
python start_pipeline.py --stop-on-error # Stop if any consumer fails
```

### 3. `start_pipeline.sh` (Bash Script)
**Shell script for Unix/Linux systems**

```bash
./start_pipeline.sh
```

**Features:**
- ✅ Bash shell script
- ✅ Starts consumers in background
- ✅ Creates PID file for tracking
- ✅ Works with `stop_pipeline.sh`

### 4. `stop_pipeline.sh` (Bash Script) 
**Companion script to stop all consumers**

```bash
./stop_pipeline.sh
```

**Features:**
- ✅ Stops all consumers started with `start_pipeline.sh`
- ✅ Graceful shutdown with fallback to force kill
- ✅ Cleans up PID files

## Pipeline Components

The scripts start these consumers in order:

1. **OCR Consumer** (`ocr_consumer.py`)
   - Processes uploaded files
   - Performs OCR using PaddleOCR
   - Sends results to LLM Engine queue

2. **LLM Engine Consumer** (`llm_engine_consumer.py`)
   - Receives OCR results
   - Detects PII using LLM analysis
   - Sends results to Redactor queue

3. **Redactor Consumer** (`redactor_consumer.py`)
   - Receives PII detection results
   - Redacts sensitive information from documents
   - Saves redacted files

## Complete Workflow

1. **Start the pipeline:**
   ```bash
   python simple_start.py
   ```

2. **Start the API server:**
   ```bash
   python ingest.py
   ```

3. **Upload files via API:**
   - Files will be processed automatically through the pipeline
   - Check consumer logs for progress
   - Redacted files will be saved in the uploads folder

## Troubleshooting

### Common Issues:

1. **RabbitMQ not running:**
   ```bash
   brew services start rabbitmq  # macOS
   sudo systemctl start rabbitmq-server  # Linux
   ```

2. **Consumer fails to start:**
   - Check if the script files exist in the `consumers/` directory
   - Verify Python dependencies are installed
   - Check RabbitMQ connection

3. **Permission denied:**
   ```bash
   chmod +x start_pipeline.sh stop_pipeline.sh simple_start.py
   ```

### Monitoring:

- **Check running processes:**
  ```bash
  ps aux | grep python | grep consumer
  ```

- **Check RabbitMQ queues:**
  ```bash
  sudo rabbitmqctl list_queues
  ```

- **View consumer logs:**
  - Each consumer runs in its own Terminal window
  - Check individual windows for detailed logs

## Tips

- Use `simple_start.py` for development and testing
- Use `start_pipeline.py` for production with monitoring
- Each consumer can be started individually if needed
- The API server (`ingest.py`) is separate and should be started after consumers
- Upload test files to verify the complete pipeline works

## File Structure

```
753-Final Project/
├── simple_start.py          # Simple pipeline starter (recommended)
├── start_pipeline.py        # Advanced pipeline manager  
├── start_pipeline.sh        # Bash script version
├── stop_pipeline.sh         # Stop script for bash version
├── ingest.py               # API server (start separately)
├── consumers/
│   ├── ocr_consumer.py
│   ├── llm_engine_consumer.py
│   └── redactor_consumer.py
└── uploads/                # Where files are uploaded and redacted files saved
```
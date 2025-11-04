#!/bin/bash
# Simple bash script to start all consumers for the document processing pipeline

echo "============================================================"
echo "🔄 Starting Document Processing Pipeline"
echo "============================================================"

# Check if we're in the right directory
if [ ! -f "ingest.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Expected to find 'ingest.py' in current directory"
    exit 1
fi

# Function to start a consumer in the background
start_consumer() {
    local name="$1"
    local script="$2"
    local description="$3"
    
    echo "🚀 Starting $name..."
    echo "   Script: $script"
    echo "   Description: $description"
    
    cd consumers
    python "$script" &
    local pid=$!
    cd ..
    
    # Give the process a moment to start
    sleep 2
    
    # Check if the process is still running
    if kill -0 "$pid" 2>/dev/null; then
        echo "✅ $name started successfully (PID: $pid)"
        echo "$pid" >> .pipeline_pids
    else
        echo "❌ Failed to start $name"
        return 1
    fi
    
    echo "⏳ Waiting 3 seconds before starting next consumer..."
    sleep 3
    echo
}

# Create/clear the PID file
> .pipeline_pids

# Start all consumers
echo "📋 Starting consumers in sequence..."
echo

start_consumer "OCR Consumer" "ocr_consumer.py" "Processes files and performs OCR using PaddleOCR"
start_consumer "LLM Engine Consumer" "llm_engine_consumer.py" "Detects PII using LLM analysis"  
start_consumer "Redactor Consumer" "redactor_consumer.py" "Redacts detected PII from documents"

echo "============================================================"
echo "🎉 Pipeline startup complete!"
echo

# Show running processes
if [ -s .pipeline_pids ]; then
    echo "📊 Active Consumers:"
    while read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "   • Consumer running (PID: $pid)"
        fi
    done < .pipeline_pids
else
    echo "⚠️  No consumers are running"
fi

echo
echo "💡 Tips:"
echo "   • Start the API server with: python ingest.py"
echo "   • View consumer logs in their respective terminals"
echo "   • Stop all consumers with: ./stop_pipeline.sh"
echo "   • Or stop individual consumers by PID"
echo "============================================================"
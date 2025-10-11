#!/bin/bash
# Script to stop all consumers in the document processing pipeline

echo "🛑 Stopping Document Processing Pipeline..."

# Check if PID file exists
if [ ! -f ".pipeline_pids" ]; then
    echo "❌ No PID file found. Consumers may not be running or were started manually."
    echo "💡 You can manually stop processes using: ps aux | grep python | grep consumer"
    exit 1
fi

# Stop each process
echo "📋 Stopping consumers..."
while read -r pid; do
    if [ ! -z "$pid" ]; then
        if kill -0 "$pid" 2>/dev/null; then
            echo "   Stopping consumer (PID: $pid)..."
            kill "$pid"
            
            # Wait a moment for graceful shutdown
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "   Force stopping consumer (PID: $pid)..."
                kill -9 "$pid"
            fi
            
            echo "   ✅ Consumer stopped (PID: $pid)"
        else
            echo "   Consumer (PID: $pid) was already stopped"
        fi
    fi
done < .pipeline_pids

# Clean up PID file
rm -f .pipeline_pids

echo "🏁 All consumers stopped"
echo "💡 You may also want to stop the API server if it's running"
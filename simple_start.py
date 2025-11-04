#!/usr/bin/env python3
"""
Simple Pipeline Starter

A straightforward script to start all consumers for the document processing pipeline.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def main():
    print("=" * 60)
    print("🔄 Starting Document Processing Pipeline")
    print("=" * 60)
    
    # Get the project root and consumers directory
    project_root = Path(__file__).parent
    consumers_dir = project_root / "consumers"
    
    # Check if consumers directory exists
    if not consumers_dir.exists():
        print(f"❌ Error: Consumers directory not found: {consumers_dir}")
        return False
    
    # Consumer scripts to start
    consumers = [
        ("OCR Consumer", "ocr_consumer.py", "Processes files and performs OCR using PaddleOCR"),
        ("LLM Engine Consumer", "llm_engine_consumer.py", "Detects PII using LLM analysis"),
        ("Redactor Consumer", "redactor_consumer.py", "Redacts detected PII from documents")
    ]
    
    started_processes = []
    
    try:
        for name, script, description in consumers:
            script_path = consumers_dir / script
            
            if not script_path.exists():
                print(f"❌ Error: Script not found: {script}")
                continue
            
            print(f"🚀 Starting {name}...")
            print(f"   Script: {script}")
            print(f"   Description: {description}")
            
            # Start the consumer in a new terminal (macOS specific)
            if sys.platform == "darwin":  # macOS
                cmd = [
                    "osascript", "-e",
                    f'tell application "Terminal" to do script "cd \\"{consumers_dir}\\" && python \\"{script}\\""'
                ]
            else:  # Linux/Windows - run in background
                cmd = [sys.executable, str(script_path)]
            
            try:
                if sys.platform == "darwin":
                    subprocess.run(cmd, check=True)
                    print(f"✅ {name} started in new terminal window")
                else:
                    process = subprocess.Popen(
                        cmd,
                        cwd=str(consumers_dir),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    started_processes.append((name, process))
                    print(f"✅ {name} started in background (PID: {process.pid})")
                
            except Exception as e:
                print(f"❌ Failed to start {name}: {e}")
                continue
            
            # Wait between starting each consumer
            print("⏳ Waiting 3 seconds before starting next consumer...")
            time.sleep(3)
            print()
        
        print("=" * 60)
        print("🎉 Pipeline startup complete!")
        print()
        
        if sys.platform == "darwin":
            print("📋 Consumers started in separate Terminal windows")
            print("💡 Check each Terminal window to see the consumer logs")
        else:
            print("📊 Background Processes:")
            for name, process in started_processes:
                if process.poll() is None:
                    print(f"   • {name} (PID: {process.pid})")
                else:
                    print(f"   • {name} - ❌ Process exited")
        
        print()
        print("💡 Tips:")
        print("   • Start the API server with: python ingest.py")
        print("   • Upload files via the API to test the pipeline")
        print("   • Check consumer logs for processing status")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
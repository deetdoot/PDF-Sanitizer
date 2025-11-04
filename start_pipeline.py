#!/usr/bin/env python3
"""
Pipeline Startup Script

This script starts all the consumers for the document processing pipeline:
1. OCR Consumer - Processes files and performs OCR
2. LLM Engine Consumer - Detects PII using LLM analysis
3. Redactor Consumer - Redacts detected PII from documents

Usage:
    python start_pipeline.py [options]

Options:
    --help, -h          Show this help message
    --verbose, -v       Enable verbose logging
    --stop-on-error     Stop starting consumers if one fails
    --delay SECONDS     Delay between starting each consumer (default: 2)
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineManager:
    def __init__(self, verbose=False, stop_on_error=False, delay=2):
        self.verbose = verbose
        self.stop_on_error = stop_on_error
        self.delay = delay
        self.processes = []
        self.project_root = Path(__file__).parent
        self.consumers_dir = self.project_root / "consumers"
        
        # Consumer configurations
        self.consumers = [
            {
                'name': 'OCR Consumer',
                'script': 'ocr_consumer.py',
                'description': 'Processes files and performs OCR using PaddleOCR'
            },
            {
                'name': 'LLM Engine Consumer', 
                'script': 'llm_engine_consumer.py',
                'description': 'Detects PII using LLM analysis'
            },
            {
                'name': 'Redactor Consumer',
                'script': 'redactor_consumer.py', 
                'description': 'Redacts detected PII from documents'
            }
        ]
        
        # Set up signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"\nReceived signal {signum}. Shutting down consumers...")
        self.stop_all_consumers()
        sys.exit(0)
    
    def check_prerequisites(self):
        """Check if all consumer scripts exist"""
        logger.info("Checking prerequisites...")
        
        if not self.consumers_dir.exists():
            logger.error(f"Consumers directory not found: {self.consumers_dir}")
            return False
        
        missing_scripts = []
        for consumer in self.consumers:
            script_path = self.consumers_dir / consumer['script']
            if not script_path.exists():
                missing_scripts.append(consumer['script'])
        
        if missing_scripts:
            logger.error(f"Missing consumer scripts: {', '.join(missing_scripts)}")
            return False
        
        logger.info("✅ All consumer scripts found")
        return True
    
    def start_consumer(self, consumer):
        """Start a single consumer"""
        script_path = self.consumers_dir / consumer['script']
        
        logger.info(f"🚀 Starting {consumer['name']}...")
        logger.info(f"   Script: {consumer['script']}")
        logger.info(f"   Description: {consumer['description']}")
        
        try:
            # Start the consumer process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.consumers_dir),
                stdout=subprocess.PIPE if not self.verbose else None,
                stderr=subprocess.PIPE if not self.verbose else None,
                universal_newlines=True
            )
            
            # Give the process a moment to start
            time.sleep(1)
            
            # Check if the process started successfully
            poll_result = process.poll()
            if poll_result is not None:
                # Process exited immediately, there's an error
                stdout, stderr = process.communicate()
                logger.error(f"❌ Failed to start {consumer['name']}")
                if stdout:
                    logger.error(f"STDOUT: {stdout}")
                if stderr:
                    logger.error(f"STDERR: {stderr}")
                
                if self.stop_on_error:
                    return False
            else:
                # Process is running
                self.processes.append({
                    'name': consumer['name'],
                    'process': process,
                    'script': consumer['script']
                })
                logger.info(f"✅ {consumer['name']} started successfully (PID: {process.pid})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting {consumer['name']}: {e}")
            if self.stop_on_error:
                return False
            return True
    
    def start_all_consumers(self):
        """Start all consumers in sequence"""
        logger.info("=" * 60)
        logger.info("🔄 Starting Document Processing Pipeline")
        logger.info("=" * 60)
        
        if not self.check_prerequisites():
            return False
        
        successful_starts = 0
        
        for i, consumer in enumerate(self.consumers):
            if self.start_consumer(consumer):
                successful_starts += 1
            
            # Add delay between starting consumers (except for the last one)
            if i < len(self.consumers) - 1:
                logger.info(f"⏳ Waiting {self.delay} seconds before starting next consumer...")
                time.sleep(self.delay)
        
        logger.info("=" * 60)
        if successful_starts == len(self.consumers):
            logger.info("🎉 All consumers started successfully!")
            logger.info(f"📊 Running processes: {len(self.processes)}")
        else:
            logger.warning(f"⚠️  {successful_starts}/{len(self.consumers)} consumers started successfully")
        
        if self.processes:
            logger.info("\n📋 Active Consumers:")
            for proc_info in self.processes:
                logger.info(f"   • {proc_info['name']} (PID: {proc_info['process'].pid})")
        
        logger.info("=" * 60)
        return successful_starts > 0
    
    def stop_all_consumers(self):
        """Stop all running consumers"""
        if not self.processes:
            logger.info("No consumers to stop")
            return
        
        logger.info("🛑 Stopping all consumers...")
        
        for proc_info in self.processes:
            try:
                process = proc_info['process']
                if process.poll() is None:  # Process is still running
                    logger.info(f"   Stopping {proc_info['name']} (PID: {process.pid})...")
                    process.terminate()
                    
                    # Wait up to 5 seconds for graceful shutdown
                    try:
                        process.wait(timeout=5)
                        logger.info(f"   ✅ {proc_info['name']} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"   ⚠️  Force killing {proc_info['name']}...")
                        process.kill()
                        process.wait()
                        logger.info(f"   ✅ {proc_info['name']} force stopped")
                else:
                    logger.info(f"   {proc_info['name']} already stopped")
            except Exception as e:
                logger.error(f"   ❌ Error stopping {proc_info['name']}: {e}")
        
        self.processes.clear()
        logger.info("🏁 All consumers stopped")
    
    def monitor_consumers(self):
        """Monitor running consumers and handle if any exit"""
        if not self.processes:
            logger.info("No consumers to monitor")
            return
        
        logger.info("\n👀 Monitoring consumers... (Press Ctrl+C to stop all)")
        logger.info("💡 Tip: You can also start the API server with: python ingest.py")
        
        try:
            while self.processes:
                time.sleep(5)  # Check every 5 seconds
                
                # Check if any processes have exited
                for proc_info in self.processes[:]:  # Use slice to avoid modification during iteration
                    process = proc_info['process']
                    poll_result = process.poll()
                    
                    if poll_result is not None:
                        # Process has exited
                        if poll_result == 0:
                            logger.info(f"✅ {proc_info['name']} exited normally")
                        else:
                            logger.warning(f"⚠️  {proc_info['name']} exited with code {poll_result}")
                        
                        self.processes.remove(proc_info)
                
                if not self.processes:
                    logger.info("All consumers have stopped")
                    break
                    
        except KeyboardInterrupt:
            logger.info("\nKeyboard interrupt received")
        
        self.stop_all_consumers()

def main():
    parser = argparse.ArgumentParser(
        description="Start all consumers for the document processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python start_pipeline.py                 # Start all consumers with default settings
    python start_pipeline.py -v              # Start with verbose output
    python start_pipeline.py --delay 5       # Wait 5 seconds between starting each consumer
    python start_pipeline.py --stop-on-error # Stop if any consumer fails to start
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--stop-on-error', action='store_true',
                       help='Stop starting consumers if one fails')
    parser.add_argument('--delay', type=int, default=2,
                       help='Delay in seconds between starting each consumer (default: 2)')
    
    args = parser.parse_args()
    
    # Create and start the pipeline manager
    manager = PipelineManager(
        verbose=args.verbose,
        stop_on_error=args.stop_on_error,
        delay=args.delay
    )
    
    # Start all consumers
    if manager.start_all_consumers():
        # Monitor the consumers until interrupted
        manager.monitor_consumers()
    else:
        logger.error("Failed to start pipeline")
        sys.exit(1)

if __name__ == "__main__":
    main()
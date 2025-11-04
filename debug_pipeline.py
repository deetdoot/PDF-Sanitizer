#!/usr/bin/env python3
"""
Debug script to trace the entire pipeline flow and identify where messages are getting stuck
"""

import pika
import json
import sys
import time
from pathlib import Path

def check_queue_status():
    """Check the status of all queues"""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        
        queues = ['ocr', 'llm_engine', 'redactor']
        
        print("📊 Queue Status Check")
        print("=" * 50)
        
        queue_stats = {}
        for queue_name in queues:
            try:
                method = channel.queue_declare(queue=queue_name, durable=True, passive=True)
                message_count = method.method.message_count
                consumer_count = method.method.consumer_count
                
                queue_stats[queue_name] = {
                    'messages': message_count,
                    'consumers': consumer_count
                }
                
                status = "🟢 HEALTHY" if consumer_count > 0 else "🔴 NO CONSUMERS"
                print(f"{queue_name:12} | Messages: {message_count:2} | Consumers: {consumer_count} | {status}")
                
            except Exception as e:
                print(f"{queue_name:12} | ❌ ERROR: {e}")
        
        connection.close()
        return queue_stats
        
    except Exception as e:
        print(f"❌ Failed to connect to RabbitMQ: {e}")
        return {}

def test_llm_engine_flow():
    """Test sending a message to LLM engine and see if it flows to redactor"""
    
    # First check available files
    print("\n🔍 Checking Available Files")
    print("=" * 50)
    
    uploads_dir = Path("/Users/emtiazahamed/Desktop/753-Final Project/uploads")
    output_dir = Path("/Users/emtiazahamed/Desktop/753-Final Project/consumers/output")
    
    # Find a job that has all required files
    available_jobs = []
    for upload_file in uploads_dir.glob("*.png"):
        if "_redacted" in upload_file.name:
            continue
            
        job_id = upload_file.stem
        ocr_output_dir = output_dir / job_id
        ocr_result_file = ocr_output_dir / f"{job_id}_res.json"
        
        if ocr_result_file.exists():
            available_jobs.append({
                'job_id': job_id,
                'upload_file': upload_file,
                'ocr_result': ocr_result_file,
                'output_dir': ocr_output_dir
            })
    
    if not available_jobs:
        print("❌ No suitable jobs found for testing")
        print("   Need: Upload file + OCR result file")
        return False
    
    # Use the first available job
    test_job = available_jobs[0]
    print(f"✅ Found test job: {test_job['job_id']}")
    print(f"   Upload file: {test_job['upload_file']}")
    print(f"   OCR result: {test_job['ocr_result']}")
    
    # Send message to LLM engine queue
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        
        # Get queue status before
        print(f"\n📤 Sending message to LLM Engine queue...")
        
        llm_message = {
            'job_id': test_job['job_id'],
            'ocr_result_path': str(test_job['ocr_result']),
            'output_folder': str(test_job['output_dir']),
            'original_file_path': str(test_job['upload_file'])  # Include original file path
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='llm_engine',
            body=json.dumps(llm_message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        print(f"✅ Message sent to LLM Engine queue")
        print(f"   Job ID: {test_job['job_id']}")
        print(f"   Original file: {test_job['upload_file']}")
        
        connection.close()
        
        # Wait a moment and check queue status
        print(f"\n⏳ Waiting 10 seconds for processing...")
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test message: {e}")
        return False

def main():
    print("🔧 Pipeline Debug Tool")
    print("=" * 60)
    
    # Step 1: Check queue status
    queue_stats = check_queue_status()
    
    if not queue_stats:
        print("❌ Cannot proceed - RabbitMQ connection failed")
        return
    
    # Step 2: Check for issues
    issues_found = []
    
    for queue_name, stats in queue_stats.items():
        if stats['consumers'] == 0:
            issues_found.append(f"No consumers for {queue_name} queue")
        elif stats['consumers'] > 1:
            issues_found.append(f"Multiple consumers ({stats['consumers']}) for {queue_name} queue - might cause message distribution issues")
    
    if issues_found:
        print(f"\n⚠️  Issues Found:")
        for issue in issues_found:
            print(f"   • {issue}")
    else:
        print(f"\n✅ All queues have consumers")
    
    # Step 3: Test the flow
    print(f"\n🧪 Testing LLM Engine → Redactor Flow")
    print("=" * 50)
    
    success = test_llm_engine_flow()
    
    if success:
        # Check queue status after test
        print(f"\n📊 Queue Status After Test")
        print("=" * 50)
        final_stats = check_queue_status()
        
        print(f"\n💡 What to check next:")
        print(f"   1. Look at LLM Engine Consumer logs - did it process the message?")
        print(f"   2. Look at Redactor Consumer logs - did it receive a message?")
        print(f"   3. Check if PII detection file was created")
        print(f"   4. Check if redacted file was created in uploads folder")
    
if __name__ == "__main__":
    main()
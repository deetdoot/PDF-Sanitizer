#!/usr/bin/env python3
"""
End-to-end pipeline test - Upload a file and track it through the entire pipeline
"""

import requests
import time
import json
from pathlib import Path

def test_complete_pipeline():
    """Test the complete pipeline with a file upload"""
    
    print("🧪 End-to-End Pipeline Test")
    print("=" * 60)
    
    # Use an existing file for testing
    uploads_dir = Path("/Users/emtiazahamed/Desktop/753-Final Project/uploads")
    test_files = list(uploads_dir.glob("*.png"))
    
    if not test_files:
        print("❌ No test files found in uploads directory")
        return False
    
    # Use the first available PNG file
    test_file = test_files[0]
    print(f"📁 Using test file: {test_file.name}")
    
    try:
        # Upload the file
        print(f"\n📤 Uploading file to API...")
        
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post('http://localhost:8000/upload-file/', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   Response: {result}")
            
            # Extract job_id from response
            if 'file_id' in result:
                job_id = result['file_id']
            elif 'job_id' in result:
                job_id = result['job_id']
            else:
                print(f"❌ No file_id or job_id found in response")
                return False
            
            print(f"   Job ID: {job_id}")
            if 'filepath' in result:
                print(f"   Uploaded to: {result['filepath']}")
            
            # Track the pipeline progress
            print(f"\n🔄 Tracking pipeline progress...")
            
            output_dir = Path(f"/Users/emtiazahamed/Desktop/753-Final Project/consumers/output/{job_id}")
            uploads_dir = Path("/Users/emtiazahamed/Desktop/753-Final Project/uploads")
            
            stages = [
                ("OCR Processing", output_dir / f"{job_id}_res.json", 30),
                ("PII Detection", output_dir / f"pii_detections_{job_id}.json", 60),
                ("Redaction", uploads_dir / f"{job_id}_redacted.png", 90)
            ]
            
            for stage_name, expected_file, max_wait in stages:
                print(f"\n⏳ Waiting for {stage_name}...")
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    if expected_file.exists():
                        print(f"✅ {stage_name} complete! File: {expected_file}")
                        break
                    time.sleep(2)
                    print(".", end="", flush=True)
                else:
                    print(f"\n❌ {stage_name} timed out after {max_wait} seconds")
                    print(f"   Expected file: {expected_file}")
                    return False
            
            print(f"\n🎉 Complete pipeline test successful!")
            print(f"   Job ID: {job_id}")
            print(f"   All stages completed successfully")
            
            return True
            
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    
    if success:
        print(f"\n✅ Pipeline is working correctly!")
    else:
        print(f"\n❌ Pipeline test failed - check consumer logs")
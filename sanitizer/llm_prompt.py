import os
import requests
import json
from pathlib import Path

system_prompt = """You are a data sensitivity auditor.

Your goal is to identify and locate sensitive or personally identifiable information (PII)
within the provided text. Do NOT redact or rewrite anything. Only return the index ranges
and categories of detected sensitive elements.

Follow these steps:
1. Scan the input text carefully.
2. Identify spans (start_index, end_index) that contain sensitive information.
3. Categorize each as one of: NAME, EMAIL, PHONE, SSN, ADDRESS, DATE, FINANCIAL, SECURITY_KEY, LOCATION, OTHER.
4. Make sure all the params are there.
5. Return a valid JSON array with objects in this exact format. This is just an example, do NOT copy it:

[
  {"category": "CATEGORY_TYPE", "start": START_INDEX, "end": END_INDEX, "text": "DETECTED_TEXT"}
]

Example format (DO NOT copy these exact values):
- For a name at the beginning: {"category": "NAME", "start": 0, "end": 12, "text": "actual_name_found"}
- For an email elsewhere: {"category": "EMAIL", "start": 45, "end": 68, "text": "actual_email@found.com"}

Important rules:
- Use 0-based indexing for the actual text positions
- Include only the exact text that was detected in the provided input
- Do not copy the example values above
- Return empty array [] if no PII is found
- Output valid JSON only, no explanations or commentary
- Analyze ONLY the text provided below, not the examples above

CRITICAL: The examples above are just formatting guides. Analyze the actual text and return real findings."""


MODEL = "llava:7b"

# Path to the output folder
output_dir = Path("output/")
output_dir.mkdir(parents=True, exist_ok=True)

# Extract texts from the OCR JSON file
def extract_texts_from_ocr_json(json_path):
    """Extract rec_texts from OCR result JSON file"""
    try:
        with open(json_path, 'r') as f:
            ocr_data = json.load(f)
        
        # Get the rec_texts array and filter out empty strings
        texts = [text.strip() for text in ocr_data.get('rec_texts', []) if text.strip()]
        return texts
    except FileNotFoundError:
        print(f"Error: File not found at {json_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {json_path}")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []


# Extract bbox from the json file

def extract_bboxes_from_ocr_json(json_path):
    """Extract bounding boxes from OCR result JSON file"""
    try:
        with open(json_path, 'r') as f:
            ocr_data = json.load(f)
        
        # Get the bboxes array
        bboxes = ocr_data.get('rec_boxes', [])
        return bboxes
    except FileNotFoundError:
        print(f"Error: File not found at {json_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {json_path}")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

json_file_path = "/Users/emtiazahamed/Desktop/753-Final Project/consumers/output/73888bee-6075-42a2-bcf0-92c1b49e5964/73888bee-6075-42a2-bcf0-92c1b49e5964_res.json"


# Extract texts from the JSON file
texts = extract_texts_from_ocr_json(json_file_path)
bboxes = extract_bboxes_from_ocr_json(json_file_path)

def calculate_pii_bbox(start_char, end_char, text_length, original_bbox):
    """Calculate proportional bbox for detected PII substring"""
    if text_length == 0:
        return original_bbox
    
    start_ratio = start_char / text_length
    end_ratio = end_char / text_length
    
    x1, y1, x2, y2 = original_bbox
    bbox_width = x2 - x1
    
    pii_x1 = x1 + (start_ratio * bbox_width)
    pii_x2 = x1 + (end_ratio * bbox_width)
    
    return [int(pii_x1), int(y1), int(pii_x2), int(y2)]

all_detections = []


for i, text in enumerate(texts, start=1):
    payload = {
        "model": MODEL,
        "prompt": f"{system_prompt}\n\nText:\n{text}\n\nOutput JSON only:"
    }

    response = requests.post("http://localhost:11434/api/generate", json=payload, stream=False)
    output_text = ""

    # Ollama streams tokens; capture the output cleanly
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if "response" in data:
                output_text += data["response"]

    bbox_coordinate = bboxes[i-1]

    if output_text.strip():
        try:
            print(output_text)  # For debugging
            output_text = json.loads(output_text)
            
            
            for item in output_text:
                block_detections = []
                try:
                    start = item['start']
                    end = item['end']
                    detected_text = item['text']
                    category = item['category']
                    
                    # Calculate PII-specific bbox
                    pii_bbox = calculate_pii_bbox(start, end, len(text), bbox_coordinate)
                    print(f"PII BBox: {pii_bbox}")
                    print(f"Original BBox: {bbox_coordinate}")
                    detection_info = {
                        'block_index': i-1,  # 0-based index
                        'original_text': text,
                        'category': category,
                        'detected_text': detected_text,
                        'start_char': start,
                        'end_char': end,
                        'text_length': len(text),
                        'original_bbox': bbox_coordinate,
                        'pii_bbox': pii_bbox,
                        'confidence_score': None  # Can be added if available
                    }
                    
                    block_detections.append(detection_info)
                    all_detections.append(detection_info)
                    
                    print(f"Category: {category}, Text: '{detected_text}', Start: {start}, End: {end}")
                    print(f"PII BBox: {pii_bbox}")
                except:
                    continue

        except json.JSONDecodeError:
            print("Error: Output is not valid JSON")
            continue



# Save all detections to JSON file
job_id = Path(json_file_path).stem.split('_')[0]  # Extract job ID from filename
output_filename = f"pii_detections_{job_id}.json"
output_filepath = output_dir / output_filename

# Create summary information
summary_data = {
    "job_id": job_id,
    "source_file": json_file_path,
    "total_text_blocks": len(texts),
    "total_pii_detections": len(all_detections),
    "categories_found": list(set([d['category'] for d in all_detections])),
    "detections": all_detections
}

# Save to JSON file
try:
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== SUMMARY ===")
    print(f"Total PII detections: {len(all_detections)}")
    print(f"Categories found: {summary_data['categories_found']}")
    print(f"Results saved to: {output_filepath}")
    
except Exception as e:
    print(f"Error saving results to JSON: {e}")
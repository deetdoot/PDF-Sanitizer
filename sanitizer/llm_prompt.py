import os
import requests
import json
from pathlib import Path

def detect_pii_from_ocr(job_id: str, json_file_path: str, output_folder_path: str, model: str = "llama3.2"):
    """
    Main function to detect PII from OCR JSON file using structured outputs
    
    Args:
        job_id (str): Unique identifier for the job
        json_file_path (str): Path to the OCR JSON result file
        output_folder_path (str): Path to the output folder where results will be saved
        model (str): LLM model to use for PII detection
    
    Returns:
        str: Path to the generated PII detection JSON file
    """
    
    system_prompt = """You are a meticulous data sensitivity auditor.

Your mission is to exhaustively identify every occurrence of sensitive or personally identifiable information (PII) in the provided text array.

Detection checklist:
1. Review the entire text array thoroughly.
2. Capture every full or partial PERSON name (first, middle, last, initials with surnames, honorifics + names, etc.).
3. Identify any AGE mentions, including phrases like "45 years old".
4. Flag all contact details: emails, phone numbers, cell numbers.
5. Detect numeric identifiers such as SSN, account numbers, security keys, license numbers.
6. Mark any ADDRESS or LOCATION (street, city, state, ZIP, country, GPS coordinates).
7. Include FINANCIAL data (bank info, amounts tied to people, credit cards).
8. If unsure about the category but the text is sensitive, label it as OTHER.

Important rules:
- Only return the category and the exact text that was detected
- The text must match exactly what appears in the input
- Be thorough: analyze the complete text array
- Return empty array if no PII is found

Categories: PERSON, AGE, EMAIL, PHONE, SSN, ACCOUNT_NUMBER, ADDRESS, LOCATION, FINANCIAL, OTHER
"""
    # Create output folder if it doesn't exist
    output_dir = Path(output_folder_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define JSON schema for structured output
    pii_schema = {
        "type": "object",
        "properties": {
            "detections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["PERSON", "AGE", "EMAIL", "PHONE", "SSN", "ACCOUNT_NUMBER", "ADDRESS", "LOCATION", "FINANCIAL", "OTHER"]
                        },
                        "text": {
                            "type": "string"
                        }
                    },
                    "required": ["category", "text"]
                }
            }
        },
        "required": ["detections"]
    }


    def extract_data_from_ocr_json(json_path):
        """Extract rec_texts and rec_boxes from OCR result JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            # Get the rec_texts array and filter out empty strings
            texts = [text.strip() for text in ocr_data.get('rec_texts', []) if text.strip()]
            # Get the bboxes array
            bboxes = ocr_data.get('rec_boxes', [])
            
            return texts, bboxes, ocr_data
        except FileNotFoundError:
            print(f"Error: File not found at {json_path}")
            return [], [], {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file {json_path}")
            return [], [], {}
        except Exception as e:
            print(f"Error reading file: {e}")
            return [], [], {}

    def calculate_bbox_from_string_position(detected_text, full_text, texts, bboxes):
        """
        Calculate bounding box coordinates based on string position in full text
        
        Args:
            detected_text: The PII text that was detected
            full_text: Combined full text from all OCR blocks
            texts: List of individual text blocks
            bboxes: List of bounding boxes for each text block
        
        Returns:
            dict with bbox coordinates and metadata, or None if not found
        """
        # Find all occurrences of the detected text in the full string
        start_idx = full_text.find(detected_text)
        
        if start_idx == -1:
            print(f"Warning: Could not find '{detected_text}' in full text")
            return None
        
        end_idx = start_idx + len(detected_text)
        
        # Find which text block(s) contain this character range
        current_position = 0
        containing_blocks = []
        
        for block_idx, text in enumerate(texts):
            block_start = current_position
            block_end = current_position + len(text)
            
            # Check if this block overlaps with the detected text range
            if not (block_end < start_idx or block_start > end_idx):
                # Calculate the portion of detected text in this block
                overlap_start = max(start_idx, block_start)
                overlap_end = min(end_idx, block_end)
                
                # Calculate relative position within the block
                relative_start = overlap_start - block_start
                relative_end = overlap_end - block_start
                
                containing_blocks.append({
                    'block_idx': block_idx,
                    'text': text,
                    'bbox': bboxes[block_idx] if block_idx < len(bboxes) else None,
                    'relative_start': relative_start,
                    'relative_end': relative_end,
                    'char_length': len(text)
                })
            
            # Add 1 for space/newline between blocks
            current_position = block_end + 1
        
        if not containing_blocks:
            print(f"Warning: No containing blocks found for '{detected_text}'")
            return None
        
        # Calculate the combined bounding box
        if len(containing_blocks) == 1:
            # Single block - calculate precise coordinates within the block
            block = containing_blocks[0]
            if block['bbox'] is None:
                return None
            
            bbox = block['bbox']
            text_length = block['char_length']
            
            # Calculate proportional position within the bounding box
            # Assuming left-to-right text flow
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            
            # Calculate start and end X positions based on character position
            start_ratio = block['relative_start'] / text_length if text_length > 0 else 0
            end_ratio = block['relative_end'] / text_length if text_length > 0 else 1
            
            new_x1 = x1 + (width * start_ratio)
            new_x2 = x1 + (width * end_ratio)
            
            calculated_bbox = [int(new_x1), int(y1), int(new_x2), int(y2)]
            
            return {
                'bbox': calculated_bbox,
                'block_index': block['block_idx'],
                'original_text': block['text'],
                'method': 'calculated_single_block'
            }
        else:
            # Multiple blocks - use the bounding box of all involved blocks
            all_bboxes = [b['bbox'] for b in containing_blocks if b['bbox'] is not None]
            
            if not all_bboxes:
                return None
            
            # Calculate the minimum bounding rectangle that contains all boxes
            min_x1 = min(bbox[0] for bbox in all_bboxes)
            min_y1 = min(bbox[1] for bbox in all_bboxes)
            max_x2 = max(bbox[2] for bbox in all_bboxes)
            max_y2 = max(bbox[3] for bbox in all_bboxes)
            
            calculated_bbox = [int(min_x1), int(min_y1), int(max_x2), int(max_y2)]
            
            return {
                'bbox': calculated_bbox,
                'block_index': containing_blocks[0]['block_idx'],  # First block
                'original_text': ' '.join([b['text'] for b in containing_blocks]),
                'method': 'calculated_multi_block',
                'num_blocks': len(containing_blocks)
            }

    # Extract texts and bboxes from the JSON file
    texts, bboxes, ocr_data = extract_data_from_ocr_json(json_file_path)
    
    if not texts:
        print("No text found in OCR results")
        return ""

    # Create full text by joining all text blocks with spaces
    full_text = " ".join(texts)
    
    print(f"Analyzing {len(texts)} text blocks for PII...")
    print(f"Full text length: {len(full_text)} characters")

    # Combine all texts with indices for LLM analysis
    combined_text = "\n".join([f"[{i}] {text}" for i, text in enumerate(texts)])

    # Prepare payload with structured output format
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Analyze the following text array and identify all PII. Return as JSON.\n\n{combined_text}"
            }
        ],
        "format": pii_schema,
        "temperature": 0,
        "stream": False
    }

    try:
        response = requests.post("http://localhost:11434/api/chat", json=payload)
        response.raise_for_status()
        
        result = response.json()
        output_text = result.get('message', {}).get('content', '')

        print(f"\nLLM Response:\n{output_text}\n")

        # Parse the structured output
        all_detections = []
        
        if output_text.strip():
            try:
                pii_data = json.loads(output_text.strip())
                detections = pii_data.get('detections', [])
                
                if not isinstance(detections, list):
                    print("Error: LLM output detections is not an array")
                    detections = []
                
                # Process each detection
                for detection in detections:
                    category = detection.get('category', 'UNKNOWN')
                    detected_text = detection.get('text', '')
                    
                    if not detected_text:
                        continue
                    
                    # Calculate bounding box based on string position
                    bbox_info = calculate_bbox_from_string_position(
                        detected_text, 
                        full_text, 
                        texts, 
                        bboxes
                    )
                    
                    if not bbox_info:
                        print(f"Warning: Could not calculate bbox for '{detected_text}'")
                        continue
                    
                    # Create detection info
                    detection_info = {
                        'block_index': bbox_info['block_index'],
                        'original_text': bbox_info['original_text'],
                        'category': category,
                        'detected_text': detected_text,
                        'bbox': bbox_info['bbox'],
                        'calculation_method': bbox_info['method']
                    }
                    
                    if 'num_blocks' in bbox_info:
                        detection_info['spans_multiple_blocks'] = True
                        detection_info['num_blocks'] = bbox_info['num_blocks']
                    
                    all_detections.append(detection_info)
                    print(f"✓ Found {category}: '{detected_text}' using {bbox_info['method']}")
                    print(f"  Calculated bbox: {bbox_info['bbox']}")

            except json.JSONDecodeError as e:
                print(f"Error: Failed to parse LLM output as JSON: {e}")
                print(f"Output was: {output_text}")
                return ""

    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM API: {e}")
        return ""

    # Save all detections to JSON file
    filename = os.path.basename(json_file_path)
    output_filename = f"pii_detections_{filename}"
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
        
        return str(output_filepath)
        
    except Exception as e:
        print(f"Error saving results to JSON: {e}")
        return ""


def main():
    """Example usage of the PII detection function"""
    json_file_path = "/Users/emtiazahamed/Desktop/753-Final Project/consumers/output/aa2773ce-cae4-4d91-a1f3-94d33040915c/aa2773ce-cae4-4d91-a1f3-94d33040915c_res.json"
    output_folder_path = "output"
    job_id = "73888bee-6075-42a2-bcf0-92c1b49e5964"
    
    # Run PII detection
    result_file = detect_pii_from_ocr(job_id, json_file_path, output_folder_path)
    
    if result_file:
        print(f"\n✓ PII detection completed successfully: {result_file}")
    else:
        print("\n✗ PII detection failed")


if __name__ == "__main__":
    main()
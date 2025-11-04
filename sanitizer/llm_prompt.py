import os
import requests
import json
from pathlib import Path

def detect_pii_from_ocr(job_id: str, json_file_path: str, output_folder_path: str, model: str = "llava:7b"):
    """
    Main function to detect PII from OCR JSON file
    
    Args:
        json_file_path (str): Path to the OCR JSON result file
        output_folder_path (str): Path to the output folder where results will be saved
        model (str): LLM model to use for PII detection
    
    Returns:
        str: Path to the generated PII detection JSON file
    """
    
    system_prompt = """You are a meticulous data sensitivity auditor.

Your mission is to exhaustively identify every occurrence of sensitive or personally identifiable information (PII) in the provided text. Do NOT redact or rewrite anything. Only return the index ranges and categories of detected sensitive elements.

Detection checklist (apply to every token and phrase):
1. Review the entire text multiple times; do not stop after the first finding.
2. Capture every full or partial PERSON name (first, middle, last, initials with surnames, honorifics + names, etc.).
3. Identify any AGE mentions, including phrases like "45 years old".
4. Flag all contact details: emails, phone numbers, cell numbers, and formatted/unformatted strings that represent them.
5. Detect numeric identifiers such as SSN, account numbers, security keys, license numbers.
6. Mark any ADDRESS or LOCATION (street, city, state, ZIP, country, GPS coordinates).
7. Include FINANCIAL data (bank info, amounts tied to people, credit cards).
8. If unsure about the category but the text is sensitive, label it as OTHER.
9. Never skip ambiguous matches—include them with the best-fitting category.
10. Confirm every returned span has start/end indices that match the exact substring.

Return a JSON array of objects:
[
  {"category": "CATEGORY_TYPE", "start": START_INDEX, "end": END_INDEX, "text": "DETECTED_TEXT"}
]

Important rules:
- Use 0-based indexing on the provided text.
- Start index is inclusive; end index is exclusive.
- `text` must match exactly the substring between start and end.
- Do not include example data; analyze only the supplied text.
- Return [] only if absolutely no PII or sensitive info exists.
- Output valid JSON only with no extra commentary.

Be thorough: missing even one obvious piece of PII (especially names) is unacceptable.
Important rules:
- Use 0-based indexing for the actual text positions
- Include only the exact text that was detected in the provided input
- Do not copy the example values above
- Return empty array [] if no PII is found
- Output valid JSON only, no explanations or commentary
- Analyze ONLY the text provided below, not the examples above

CRITICAL: The examples above are just formatting guides. Analyze the actual text and return real findings. The indices should be relative to the specific text block provided, not a larger document."""

    # Create output folder if it doesn't exist
    output_dir = Path(output_folder_path)
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

    def calculate_pii_bbox(start_char, end_char, text_length, original_bbox):
        """
        Use the original OCR bounding box for PII redaction.
        
        Calculating precise character-level coordinates is unreliable due to:
        - Variable character spacing and font metrics
        - OCR positioning inaccuracies
        - Different character widths
        
        For security, it's better to redact the entire text block containing PII
        rather than risk missing sensitive data with imprecise calculations.
        """
        return original_bbox

    # Extract texts from the JSON file
    texts = extract_texts_from_ocr_json(json_file_path)
    bboxes = extract_bboxes_from_ocr_json(json_file_path)

    all_detections = []

    for i, text in enumerate(texts, start=1):
        payload = {
            "model": model,
            "prompt": f"{system_prompt}\n\nText:\n{text}\n\nOutput JSON only:",
            "temperature": 0.2,
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
    job_id = job_id  # Extract job ID from filename
    # Get the file name (last part of the path)
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
        
        # print(f"\n=== SUMMARY ===")
        # print(f"Total PII detections: {len(all_detections)}")
        # print(f"Categories found: {summary_data['categories_found']}")
        # print(f"Results saved to: {output_filepath}")
        
        return str(output_filepath)
        
    except Exception as e:
        print(f"Error saving results to JSON: {e}")
        return ""


def main():
    """Example usage of the PII detection function"""
    # Example parameters
    json_file_path = "/Users/emtiazahamed/Desktop/753-Final Project/consumers/output/73888bee-6075-42a2-bcf0-92c1b49e5964/73888bee-6075-42a2-bcf0-92c1b49e5964_res.json"
    output_folder_path = "output"
    
    # Run PII detection
    result_file = detect_pii_from_ocr(json_file_path, output_folder_path)
    
    if result_file:
        print(f"PII detection completed successfully: {result_file}")
    else:
        print("PII detection failed")


if __name__ == "__main__":
    main()
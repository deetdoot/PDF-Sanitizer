import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF for PDF handling

def load_pii_detections(pii_detection_path):
    """Load PII detection data from JSON file"""
    try:
        with open(pii_detection_path, 'r') as f:
            data = json.load(f)
        return data.get('detections', [])
    except Exception as e:
        print(f"Error loading PII detections: {e}")
        return []

def redact_png_image(original_file_path, pii_detections, output_path=None):
    """Draw black bounding boxes over PII regions in PNG image"""
    try:
        # Open the original image
        image = Image.open(original_file_path)
        
        # Create a drawing context
        draw = ImageDraw.Draw(image)
        
        # Draw black rectangles over each PII detection
        for detection in pii_detections:
            pii_bbox = detection.get('pii_bbox')
            if pii_bbox:
                # pii_bbox format: [x1, y1, x2, y2]
                x1, y1, x2, y2 = pii_bbox
                
                # Draw black rectangle
                draw.rectangle([x1, y1, x2, y2], fill='black', outline='black')
                
                print(f"Redacted {detection['category']}: '{detection['detected_text']}' at {pii_bbox}")
        
        # Save the redacted image
        if output_path is None:
            # Create output filename
            original_path = Path(original_file_path)
            output_path = original_path.parent / f"{original_path.stem}_redacted{original_path.suffix}"
        
        image.save(output_path)
        print(f"Redacted image saved to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"Error processing PNG image: {e}")
        return None

def redact_pdf_file(original_file_path, pii_detections, output_path=None):
    """Handle PDF file redaction - placeholder for future implementation"""
    print("PDF redaction not implemented yet - passing...")
    return None

def redact_file(pii_detection_path, original_file_path, output_path=None):
    """
    Main function to redact files based on PII detections
    
    Args:
        pii_detection_path (str): Path to PII detection JSON file
        original_file_path (str): Path to original image/PDF file
        output_path (str, optional): Output path for redacted file
    
    Returns:
        str: Path to redacted file if successful, None otherwise
    """
    # Load PII detections
    pii_detections = load_pii_detections(pii_detection_path)
    
    if not pii_detections:
        print("No PII detections found or error loading detections")
        return None
    
    print(f"Loaded {len(pii_detections)} PII detections")
    
    # Determine file type and process accordingly
    original_path = Path(original_file_path)
    file_extension = original_path.suffix.lower()
    
    if file_extension == '.png':
        return redact_png_image(original_file_path, pii_detections, output_path)
    elif file_extension == '.pdf':
        return redact_pdf_file(original_file_path, pii_detections, output_path)
    else:
        print(f"Unsupported file type: {file_extension}")
        return None

def main():
    """Command line interface for the redaction script"""
    parser = argparse.ArgumentParser(description='Redact PII from images and PDFs')
    parser.add_argument('pii_detection_path', help='Path to PII detection JSON file')
    parser.add_argument('original_file_path', help='Path to original image/PDF file')
    parser.add_argument('--output', '-o', help='Output path for redacted file')
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not Path(args.pii_detection_path).exists():
        print(f"Error: PII detection file not found: {args.pii_detection_path}")
        return
    
    if not Path(args.original_file_path).exists():
        print(f"Error: Original file not found: {args.original_file_path}")
        return
    
    # Process the file
    result = redact_file(args.pii_detection_path, args.original_file_path, args.output)
    
    if result:
        print(f"Redaction completed successfully: {result}")
    else:
        print("Redaction failed")

# Example usage as a module
def example_usage():
    """Example of how to use the redaction functions"""
    pii_detection_path = "sanitizer/output/pii_detections_a460b361-4867-43c1-ba26-f8d76dffd882.json"
    original_file_path = "uploads/a460b361-4867-43c1-ba26-f8d76dffd882.png"
    
    # Redact the file
    redacted_file = redact_file(pii_detection_path, original_file_path)
    
    if redacted_file:
        print(f"Successfully created redacted file: {redacted_file}")
    else:
        print("Redaction failed")

if __name__ == "__main__":
    main()
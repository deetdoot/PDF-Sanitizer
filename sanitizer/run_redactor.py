from redactor import redact_file

def run_redaction(pii_detections_path: str, original_file_path: str):
    """
    Run redaction on a file using PII detection results
    
    Args:
        pii_detections_path (str): Path to the PII detections JSON file
        original_file_path (str): Path to the original file to redact
        
    Returns:
        str: Path to the redacted file, or None if redaction failed
    """
    try:
        redacted_path = redact_file(pii_detections_path, original_file_path)
        return redacted_path
    except Exception as e:
        print(f"Error during redaction: {e}")
        return None

def main():
    """Example usage of the redaction function"""
    # Example parameters
    pii_path = "/Users/emtiazahamed/Desktop/753-Final Project/sanitizer/output/pii_detections_73888bee-6075-42a2-bcf0-92c1b49e5964.json"
    original_path = "/Users/emtiazahamed/Desktop/753-Final Project/uploads/73888bee-6075-42a2-bcf0-92c1b49e5964.png"
    
    # Run redaction
    redacted_path = run_redaction(pii_path, original_path)
    
    if redacted_path:
        print(f"Redaction completed successfully: {redacted_path}")
    else:
        print("Redaction failed")

if __name__ == "__main__":
    main()
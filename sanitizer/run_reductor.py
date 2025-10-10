from reductor import redact_file

# Redact a file
pii_path = "/Users/emtiazahamed/Desktop/753-Final Project/sanitizer/output/pii_detections_73888bee-6075-42a2-bcf0-92c1b49e5964.json"
original_path = "/Users/emtiazahamed/Desktop/753-Final Project/uploads/73888bee-6075-42a2-bcf0-92c1b49e5964.png"
redacted_path = redact_file(pii_path, original_path)
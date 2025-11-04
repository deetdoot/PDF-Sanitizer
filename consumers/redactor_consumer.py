import pika
import json
import logging
import sys
from pathlib import Path

# Setup project imports
def setup_project_imports():
    """Setup imports to work from any directory in the project"""
    current_file = Path(__file__).resolve()
    
    # Find project root by looking for key files
    project_root = None
    for parent in current_file.parents:
        if (parent / "ingest.py").exists() and (parent / "requirements.txt").exists():
            project_root = parent
            break
    
    if project_root and str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    return project_root

# Setup project imports
setup_project_imports()

# Now we can import from any module in the project
from sanitizer.redactor import redact_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedactorConsumer:
    def __init__(self, rabbitmq_host='localhost'):
        self.rabbitmq_host = rabbitmq_host
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.rabbitmq_host)
            )
            self.channel = self.connection.channel()
            
            # Declare Redactor queue
            self.channel.queue_declare(queue='redactor', durable=True)
            
            logger.info("Redactor Consumer connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_redactor_message(self, ch, method, properties, body):
        """Process Redactor messages for document redaction"""
        try:
            # Parse the message
            message = json.loads(body)
            job_id = message.get('job_id')
            original_file_path = message.get('original_file_path')
            output_folder = message.get('output_folder')
            pii_detections_path = message.get('pii_detections_path')
            all_pii_detections = message.get('all_pii_detections', [pii_detections_path] if pii_detections_path else [])

            logger.info(f"Starting redaction for job: {job_id}")
            logger.info(f"Original file path: {original_file_path}")
            logger.info(f"Output folder: {output_folder}")
            logger.info(f"All PII detections: {all_pii_detections}")
            
            # Verify the original file exists
            if not Path(original_file_path).exists():
                logger.error(f"Original file not found: {original_file_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            original_file = Path(original_file_path)
            is_pdf = original_file.suffix.lower() == '.pdf'
            
            if is_pdf:
                # Handle multi-page PDF
                self.process_pdf_redaction(job_id, original_file_path, all_pii_detections, output_folder)
            else:
                # Handle single image file
                if not all_pii_detections:
                    logger.error(f"No PII detection files provided for job: {job_id}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                
                # Use the first (and should be only) detection file for single images
                pii_file = all_pii_detections[0]
                if not Path(pii_file).exists():
                    logger.error(f"PII detections file not found: {pii_file}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                
                logger.info(f"Running single image redaction with:")
                logger.info(f"  PII file: {pii_file}")
                logger.info(f"  Original file: {original_file_path}")
                
                redacted_file_path = redact_file(pii_file, original_file_path)
                
                if redacted_file_path:
                    logger.info(f"Redaction completed successfully for job: {job_id}")
                    logger.info(f"Redacted file saved to: {redacted_file_path}")
                else:
                    logger.error(f"Redaction failed for job: {job_id}")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing redactor message: {e}")
            logger.error(traceback.format_exc())
            # Acknowledge and discard the message (single attempt only)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message for job {message.get('job_id', 'unknown')} discarded after failed attempt")
    
    def process_pdf_redaction(self, job_id, original_file_path, all_pii_detections, output_folder):
        """Process multi-page PDF redaction"""
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            
            original_file = Path(original_file_path)
            output_folder_path = Path(output_folder)
            
            logger.info(f"Processing PDF redaction for {len(all_pii_detections)} detection files")
            
            # Step 1: Convert PDF to high-quality PNG files (one per page)
            pdf_document = fitz.open(original_file_path)
            png_files = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                
                # Create high-quality transformation matrix for 300 DPI
                zoom_factor = 300 / 72  # 4.17x zoom for 300 DPI vs standard 72 DPI
                mat = fitz.Matrix(zoom_factor, zoom_factor)
                
                # Render page with high quality settings
                pix = page.get_pixmap(
                    matrix=mat,
                    alpha=False,  # No transparency for smaller file size and better quality
                    colorspace=fitz.csRGB  # Ensure RGB color space
                )
                
                # Create PNG filename: {job_id}-{index}.png
                png_filename = f"{job_id}-{page_num}.png"
                png_path = output_folder_path / png_filename
                
                pix.save(str(png_path))
                png_files.append(str(png_path))
                logger.info(f"Created high-quality PNG (300 DPI) for page {page_num}: {png_path}")
            
            pdf_document.close()
            
            # Step 2: Process each PII detection file and redact corresponding PNG
            redacted_png_files = []
            
            for pii_file in all_pii_detections:
                try:
                    if not Path(pii_file).exists():
                        logger.error(f"PII detection file not found: {pii_file} - skipping")
                        continue
                    
                    # Extract index from filename: pii_detections_job_id_INDEX_res.json
                    pii_filename = Path(pii_file).name
                    
                    # Find the pattern job_id_INDEX_res.json
                    import re
                    pattern = rf"{job_id}_(\d+)_res\.json"
                    match = re.search(pattern, pii_filename)
                    
                    if not match:
                        logger.error(f"Could not extract page index from PII filename: {pii_filename} - skipping")
                        continue
                    
                    page_index = int(match.group(1))
                    
                    if page_index >= len(png_files):
                        logger.error(f"Page index {page_index} out of range for {len(png_files)} pages - skipping")
                        continue
                    
                    # Get corresponding PNG file
                    png_file = png_files[page_index]
                    
                    logger.info(f"Processing page {page_index}: PII file {pii_file} -> PNG {png_file}")
                    
                    # Run redaction on the PNG
                    redacted_png = redact_file(pii_file, png_file)
                    
                    if redacted_png:
                        redacted_png_files.append((page_index, redacted_png))
                        logger.info(f"Successfully redacted page {page_index}: {redacted_png}")
                    else:
                        logger.error(f"Failed to redact page {page_index} - skipping")
                        
                except Exception as e:
                    logger.error(f"Error processing PII file {pii_file}: {e} - skipping")
                    continue
            
            # Step 3: Combine redacted PNGs back into high-quality PDF
            if redacted_png_files:
                # Sort by page index to maintain order
                redacted_png_files.sort(key=lambda x: x[0])
                
                # Create output PDF filename
                output_pdf_name = f"{original_file.stem}_redacted.pdf"
                output_pdf_path = original_file.parent / output_pdf_name
                
                # Convert PNGs to high-quality PDF
                try:
                    images = []
                    for page_index, png_path in redacted_png_files:
                        if Path(png_path).exists():
                            img = Image.open(png_path)
                            # Convert to RGB if needed for PDF compatibility
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            images.append(img)
                            logger.info(f"Added page {page_index} to PDF compilation: {png_path}")
                    
                    if images:
                        # Save as high-quality PDF
                        images[0].save(
                            str(output_pdf_path),
                            save_all=True,
                            append_images=images[1:] if len(images) > 1 else [],
                            format='PDF',
                            resolution=300.0,  # Match the 300 DPI from PNG conversion
                            quality=95,        # High quality for any JPEG compression
                            optimize=False     # Don't optimize to maintain quality
                        )
                        
                        logger.info(f"Successfully created high-quality redacted PDF: {output_pdf_path}")
                        logger.info(f"Processed {len(redacted_png_files)} pages out of {len(all_pii_detections)} detection files")
                    else:
                        logger.error(f"No valid images found for PDF creation for job {job_id}")
                        
                except Exception as e:
                    logger.error(f"Error creating PDF from images: {e}")
                    return
                
                # Clean up temporary PNG files
                for png_file in png_files:
                    try:
                        Path(png_file).unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete temporary PNG {png_file}: {e}")
                
                for _, redacted_png in redacted_png_files:
                    try:
                        Path(redacted_png).unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete redacted PNG {redacted_png}: {e}")
                        
            else:
                logger.error(f"No pages were successfully redacted for job {job_id}")
                
        except Exception as e:
            import traceback
            logger.error(f"Error in PDF redaction process: {e}")
            logger.error(traceback.format_exc())
    
    def start_consuming(self):
        """Start consuming messages from Redactor queue"""
        if not self.connect():
            logger.error("Cannot start consuming - connection failed")
            return
        
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='redactor',
                on_message_callback=self.process_redactor_message
            )
            
            logger.info("Starting Redactor consumer...")
            logger.info("To exit press CTRL+C")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping Redactor consumer...")
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            logger.error(f"Error in Redactor consumer: {e}")
            self.connection.close()

if __name__ == "__main__":
    consumer = RedactorConsumer()
    consumer.start_consuming()

import pika
import json
import logging
import time
from typing import Dict, Any
from pathlib import Path
from paddleocr import PPStructureV3
from paddleocr import PaddleOCR


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRConsumer:
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
            
            # Declare OCR queue
            self.channel.queue_declare(queue='ocr', durable=True)
            
            logger.info("OCR Consumer connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_ocr_message(self, ch, method, properties, body):
        """Process OCR messages"""
        try:
            # Parse the message
            message = json.loads(body)
            job_id = message.get('job_id')
            file_path = message.get('file_path')
            # Convert relative path to absolute path from project root
            print(file_path)
            # Resolve file_path to absolute path relative to project root if necessary
            file_path = Path(file_path)
            if not file_path.is_absolute():
                project_root = Path(__file__).resolve().parent.parent
                file_path = (project_root / file_path).resolve()
            file_path = str(file_path)


            logger.info(f"Starting OCR processing for job: {job_id}")
            logger.info(f"File path: {file_path}")
            


            ocr = PaddleOCR(
                use_doc_orientation_classify=False, # Disables document orientation classification model via this parameter
                use_doc_unwarping=False, # Disables text image rectification model via this parameter
                use_textline_orientation=False, # Disables text line orientation classification model via this parameter
            )
            ocr = PaddleOCR(lang="en") # Uses English model by specifying language parameter
            ocr = PaddleOCR(ocr_version="PP-OCRv4") # Uses other PP-OCR versions via version parameter
            ocr = PaddleOCR(device="cpu") # Enables GPU acceleration for model inference via device parameter
            ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            ) # Switch to PP-OCRv5_mobile models

            if Path(file_path).is_file():
                logger.info(f"File exists: {file_path}")
            else:
                logger.error(f"File does not exist: {file_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            result = ocr.predict(file_path)

            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            base_name = Path(file_path).stem
            
            for idx, res in enumerate(result):
                # Save image and JSON with job_id and file base name for uniqueness
                img_output_path = output_dir / job_id / f"output_{idx}.jpg"
                json_output_path = output_dir / job_id / f"output_{idx}.json"
                res.save_to_img(str(img_output_path))
                res.save_to_json(str(json_output_path))
            
            logger.info(f"OCR processing completed for job: {job_id}")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing OCR message: {e}")
            print("Error:", e)
            # Acknowledge and discard the message (single attempt only)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message for job {message.get('job_id', 'unknown')} discarded after failed attempt")
    
    def start_consuming(self):
        """Start consuming messages from OCR queue"""
        if not self.connect():
            logger.error("Cannot start consuming - connection failed")
            return
        
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='ocr',
                on_message_callback=self.process_ocr_message
            )
            
            logger.info("Starting OCR consumer...")
            logger.info("To exit press CTRL+C")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping OCR consumer...")
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            logger.error(f"Error in OCR consumer: {e}")
            self.connection.close()

if __name__ == "__main__":
    consumer = OCRConsumer()
    consumer.start_consuming()
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
from sanitizer.llm_prompt import detect_pii_from_ocr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMEngineConsumer:
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
            
            # Declare LLM Engine queue
            self.channel.queue_declare(queue='llm_engine', durable=True)
            
            # Declare Redactor queue
            self.channel.queue_declare(queue='redactor', durable=True)
            
            logger.info("LLM Engine Consumer connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_llm_message(self, ch, method, properties, body):
        """Process LLM Engine messages for PII detection"""
        try:
            # Parse the message
            message = json.loads(body)
            job_id = message.get('job_id')
            ocr_result_path = message.get('ocr_result_path')
            output_folder = message.get('output_folder')
            
            logger.info(f"Starting PII detection for job: {job_id}")
            logger.info(f"OCR result path: {ocr_result_path}")
            logger.info(f"Output folder: {output_folder}")
            
            # Verify the OCR result file exists
            if not Path(ocr_result_path).exists():
                logger.error(f"OCR result file not found: {ocr_result_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Run PII detection
            result_file = detect_pii_from_ocr(
                json_file_path=ocr_result_path,
                output_folder_path=output_folder
            )
            
            if result_file:
                logger.info(f"PII detection completed successfully for job: {job_id}")
                logger.info(f"Results saved to: {result_file}")
                
                # Send message to Redactor queue for redaction processing
                # Find the original file in uploads folder
                project_root = Path(__file__).parent.parent
                uploads_dir = project_root / "uploads"
                
                logger.info(f"Looking for original file in: {uploads_dir}")
                logger.info(f"Searching for pattern: {job_id}.*")
                
                # Look for the original file with the job_id (exclude redacted files)
                original_file = None
                matching_files = list(uploads_dir.glob(f"{job_id}.*"))
                logger.info(f"Found matching files: {matching_files}")
                
                for file_path in matching_files:
                    # Skip redacted files
                    if "_redacted" not in file_path.name:
                        original_file = str(file_path)
                        logger.info(f"Selected original file: {original_file}")
                        break
                
                if original_file:
                    redactor_message = {
                        'job_id': job_id,
                        'pii_detections_path': result_file,
                        'original_file_path': original_file,
                        'output_folder': output_folder
                    }
                    
                    logger.info(f"Preparing message for Redactor queue:")
                    logger.info(f"  Job ID: {job_id}")
                    logger.info(f"  PII detections: {result_file}")
                    logger.info(f"  Original file: {original_file}")
                    logger.info(f"  Output folder: {output_folder}")
                    
                    self.channel.basic_publish(
                        exchange='',
                        routing_key='redactor',
                        body=json.dumps(redactor_message),
                        properties=pika.BasicProperties(
                            delivery_mode=2,  # Make message persistent
                        )
                    )
                    
                    logger.info(f"✅ Successfully sent message to Redactor queue for job: {job_id}")
                    logger.info(f"Original file: {original_file}")
                else:
                    logger.error(f"❌ Original file not found in uploads folder for job: {job_id}")
                    logger.error(f"   Searched in: {uploads_dir}")
                    logger.error(f"   Pattern: {job_id}.*")
                    logger.error(f"   Available files: {list(uploads_dir.glob('*'))}")
                    
            else:
                logger.error(f"PII detection failed for job: {job_id}")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing LLM message: {e}")
            # Acknowledge and discard the message (single attempt only)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message for job {message.get('job_id', 'unknown')} discarded after failed attempt")
    
    def start_consuming(self):
        """Start consuming messages from LLM Engine queue"""
        if not self.connect():
            logger.error("Cannot start consuming - connection failed")
            return
        
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='llm_engine',
                on_message_callback=self.process_llm_message
            )
            
            logger.info("Starting LLM Engine consumer...")
            logger.info("To exit press CTRL+C")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping LLM Engine consumer...")
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            logger.error(f"Error in LLM Engine consumer: {e}")
            self.connection.close()

if __name__ == "__main__":
    consumer = LLMEngineConsumer()
    consumer.start_consuming()
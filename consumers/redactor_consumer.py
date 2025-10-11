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
            pii_detections_path = message.get('pii_detections_path')
            original_file_path = message.get('original_file_path')
            output_folder = message.get('output_folder')
            
            logger.info(f"Starting redaction for job: {job_id}")
            logger.info(f"PII detections path: {pii_detections_path}")
            logger.info(f"Original file path: {original_file_path}")
            logger.info(f"Output folder: {output_folder}")
            
            # Verify the PII detections file exists
            if not Path(pii_detections_path).exists():
                logger.error(f"PII detections file not found: {pii_detections_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Verify the original file exists
            if not Path(original_file_path).exists():
                logger.error(f"Original file not found: {original_file_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Run redaction using the redactor module
            logger.info(f"Running redaction with:")
            logger.info(f"  PII file: {pii_detections_path}")
            logger.info(f"  Original file: {original_file_path}")
            
            redacted_file_path = redact_file(pii_detections_path, original_file_path)
            
            if redacted_file_path:
                logger.info(f"Redaction completed successfully for job: {job_id}")
                logger.info(f"Redacted file saved to: {redacted_file_path}")
            else:
                logger.error(f"Redaction failed for job: {job_id}")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing redactor message: {e}")
            # Acknowledge and discard the message (single attempt only)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message for job {message.get('job_id', 'unknown')} discarded after failed attempt")
    
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

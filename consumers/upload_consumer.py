import pika
import json
import logging
import time
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileUploadConsumer:
    def __init__(self, rabbitmq_host=None):
        self.rabbitmq_host = rabbitmq_host or os.environ.get('RABBITMQ_HOST', 'localhost')
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.rabbitmq_host)
            )
            self.channel = self.connection.channel()
            
            # Declare queues
            self.channel.queue_declare(queue='file_upload', durable=True)
            self.channel.queue_declare(queue='ocr', durable=True)
            
            logger.info("Connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_file_upload_message(self, ch, method, properties, body):
        """Process messages from file_upload queue and forward to ocr queue"""
        try:
            # Parse the message
            message = json.loads(body)
            job_id = message.get('job_id')
            file_path = message.get('file_path')
            
            logger.info(f"Processing file upload job: {job_id}")
            
            # Prepare OCR message
            ocr_message = {
                'job_id': job_id,
                'file_path': file_path,
                'task': 'ocr_processing',
                'timestamp': time.time()
            }
            
            # Forward to OCR queue
            self.channel.basic_publish(
                exchange='',
                routing_key='ocr',
                body=json.dumps(ocr_message),
                properties=pika.BasicProperties(
                    delivery_mode=2  # make message persistent
                )
            )
            
            logger.info(f"Forwarded job {job_id} to OCR queue")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self):
        """Start consuming messages from file_upload queue"""
        if not self.connect():
            logger.error("Cannot start consuming - connection failed")
            return
        
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='file_upload',
                on_message_callback=self.process_file_upload_message
            )
            
            logger.info("Starting to consume messages from file_upload queue...")
            logger.info("To exit press CTRL+C")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            self.connection.close()

if __name__ == "__main__":
    consumer = FileUploadConsumer()
    consumer.start_consuming()
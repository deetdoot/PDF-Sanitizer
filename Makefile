.PHONY: help build up down restart logs clean test

help:
	@echo "PDF Processing Pipeline - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - View logs from all services"
	@echo "  make clean    - Remove all containers, volumes, and images"
	@echo "  make test     - Test the API endpoint"
	@echo "  make rabbitmq - Open RabbitMQ management UI"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started! Check status with 'make logs'"
	@echo "API available at: http://localhost:5005"
	@echo "RabbitMQ UI at: http://localhost:15672 (guest/guest)"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-ocr:
	docker-compose logs -f ocr-consumer

logs-rabbitmq:
	docker-compose logs -f rabbitmq

clean:
	docker-compose down -v
	docker system prune -f

test:
	@echo "Testing API health endpoint..."
	@curl -s http://localhost:5005/health | python -m json.tool || echo "Backend not running. Use 'make up' first."

rabbitmq:
	@open http://localhost:15672 2>/dev/null || xdg-open http://localhost:15672 2>/dev/null || echo "RabbitMQ UI: http://localhost:15672"

status:
	docker-compose ps

# Dropshipping System Makefile
# 개발 및 운영 작업을 단순화하는 명령어들

.PHONY: help build start stop restart logs clean test deploy backup health

# 기본 변수
COMPOSE_FILE_DEV = docker-compose.dev.yml
COMPOSE_FILE_PROD = docker-compose.prod.yml
COMPOSE_FILE_STAGING = docker-compose.staging.yml

# 도움말
help:
	@echo "Available commands:"
	@echo "  Development:"
	@echo "    dev-build      Build development containers"
	@echo "    dev-start      Start development environment"
	@echo "    dev-stop       Stop development environment"
	@echo "    dev-restart    Restart development environment"
	@echo "    dev-logs       Show development logs"
	@echo ""
	@echo "  Production:"
	@echo "    prod-build     Build production containers"
	@echo "    prod-start     Start production environment"
	@echo "    prod-stop      Stop production environment"
	@echo "    prod-restart   Restart production environment"
	@echo "    prod-logs      Show production logs"
	@echo ""
	@echo "  Staging:"
	@echo "    staging-build  Build staging containers"
	@echo "    staging-start  Start staging environment"
	@echo "    staging-stop   Stop staging environment"
	@echo ""
	@echo "  Testing:"
	@echo "    test           Run all tests"
	@echo "    test-unit      Run unit tests"
	@echo "    test-integration Run integration tests"
	@echo "    test-e2e       Run end-to-end tests"
	@echo ""
	@echo "  Operations:"
	@echo "    health         Check system health"
	@echo "    backup         Create database backup"
	@echo "    deploy         Deploy to production"
	@echo "    clean          Clean up containers and images"
	@echo "    reset          Reset all data (destructive)"

# 개발환경 명령어
dev-build:
	docker compose -f $(COMPOSE_FILE_DEV) build

dev-start:
	docker compose -f $(COMPOSE_FILE_DEV) up -d
	@echo "Development environment started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "MailHog: http://localhost:8025"
	@echo "pgAdmin: http://localhost:5050"

dev-stop:
	docker compose -f $(COMPOSE_FILE_DEV) down

dev-restart:
	docker compose -f $(COMPOSE_FILE_DEV) restart

dev-logs:
	docker compose -f $(COMPOSE_FILE_DEV) logs -f

# 스테이징환경 명령어
staging-build:
	docker compose -f $(COMPOSE_FILE_STAGING) build

staging-start:
	cp .env.development .env
	docker compose -f $(COMPOSE_FILE_STAGING) up -d
	@echo "Staging environment started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"

staging-stop:
	docker compose -f $(COMPOSE_FILE_STAGING) down

# 운영환경 명령어 (주의: 운영환경에서만 사용)
prod-build:
	docker compose -f $(COMPOSE_FILE_PROD) build

prod-start:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.production to .env and configure it."; \
		exit 1; \
	fi
	docker compose -f $(COMPOSE_FILE_PROD) up -d
	@echo "Production environment started!"

prod-stop:
	docker compose -f $(COMPOSE_FILE_PROD) down

prod-restart:
	docker compose -f $(COMPOSE_FILE_PROD) restart

prod-logs:
	docker compose -f $(COMPOSE_FILE_PROD) logs -f

# 테스트 명령어
test: test-lint test-unit test-integration

test-lint:
	@echo "Running code linting..."
	cd backend && python -m flake8 .
	cd frontend && npm run lint

test-unit:
	@echo "Running unit tests..."
	cd backend && python -m pytest tests/unit/ -v
	cd frontend && npm run test

test-integration:
	@echo "Running integration tests..."
	cd backend && python -m pytest tests/integration/ -v

test-e2e:
	@echo "Running end-to-end tests..."
	cd backend && python -m pytest tests/e2e/ -v

test-security:
	@echo "Running security tests..."
	cd backend && bandit -r . -f json -o bandit-report.json
	cd backend && safety check

# 운영 작업 명령어
health:
	@echo "Checking system health..."
	python3 scripts/health_check.py --format table

backup:
	@echo "Creating database backup..."
	python3 scripts/backup.py backup

deploy:
	@echo "Deploying to production..."
	@read -p "Are you sure you want to deploy to production? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		python3 scripts/deploy.py production; \
	else \
		echo "Deployment cancelled."; \
	fi

# 데이터베이스 관리
db-migrate:
	docker compose -f $(COMPOSE_FILE_DEV) exec backend alembic upgrade head

db-migration:
	@read -p "Enter migration message: " message; \
	docker compose -f $(COMPOSE_FILE_DEV) exec backend alembic revision --autogenerate -m "$$message"

db-reset:
	@echo "Resetting database..."
	docker compose -f $(COMPOSE_FILE_DEV) down -v
	docker compose -f $(COMPOSE_FILE_DEV) up -d db
	sleep 10
	docker compose -f $(COMPOSE_FILE_DEV) exec backend alembic upgrade head

# 정리 작업
clean:
	@echo "Cleaning up containers and images..."
	docker compose -f $(COMPOSE_FILE_DEV) down -v
	docker compose -f $(COMPOSE_FILE_STAGING) down -v
	docker system prune -f
	docker volume prune -f

clean-all:
	@echo "WARNING: This will remove ALL containers, images, and volumes!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose -f $(COMPOSE_FILE_DEV) down -v; \
		docker compose -f $(COMPOSE_FILE_STAGING) down -v; \
		docker compose -f $(COMPOSE_FILE_PROD) down -v; \
		docker system prune -a -f; \
		docker volume prune -f; \
	fi

reset: clean db-reset
	@echo "System reset complete!"

# 환경 설정
setup-dev:
	@echo "Setting up development environment..."
	cp .env.development .env
	$(MAKE) dev-build
	$(MAKE) dev-start
	sleep 30
	$(MAKE) db-migrate
	@echo "Development environment setup complete!"

setup-prod:
	@echo "Setting up production environment..."
	@if [ ! -f .env ]; then \
		cp .env.production .env; \
		echo "Please edit .env file with your production settings"; \
		exit 1; \
	fi
	$(MAKE) prod-build

# SSL 인증서 관리
ssl-cert:
	@echo "Generating SSL certificate..."
	mkdir -p nginx/ssl
	openssl genrsa -out nginx/ssl/privkey.pem 2048
	openssl req -new -key nginx/ssl/privkey.pem -out nginx/ssl/cert.csr
	openssl x509 -req -days 365 -in nginx/ssl/cert.csr -signkey nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem
	cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem

ssl-letsencrypt:
	@echo "Obtaining Let's Encrypt certificate..."
	@read -p "Enter your domain: " domain; \
	sudo certbot certonly --standalone -d $$domain --agree-tos
	sudo cp -L /etc/letsencrypt/live/$$domain/fullchain.pem ./nginx/ssl/
	sudo cp -L /etc/letsencrypt/live/$$domain/privkey.pem ./nginx/ssl/
	sudo cp -L /etc/letsencrypt/live/$$domain/chain.pem ./nginx/ssl/
	sudo chown $$USER:$$USER ./nginx/ssl/*

# 모니터링 관련
monitoring-start:
	docker compose -f $(COMPOSE_FILE_PROD) up -d prometheus grafana
	@echo "Monitoring started!"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin123)"

monitoring-stop:
	docker compose -f $(COMPOSE_FILE_PROD) stop prometheus grafana

# 로그 관리
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-db:
	docker compose logs -f db

logs-nginx:
	docker compose logs -f nginx

# 개발 도구
shell-backend:
	docker compose -f $(COMPOSE_FILE_DEV) exec backend bash

shell-db:
	docker compose -f $(COMPOSE_FILE_DEV) exec db psql -U dropshipping -d dropshipping_dev

shell-redis:
	docker compose -f $(COMPOSE_FILE_DEV) exec redis redis-cli

# 코드 품질
format:
	@echo "Formatting code..."
	cd backend && black . && isort .
	cd frontend && npm run format

lint-fix:
	@echo "Fixing linting issues..."
	cd backend && black . && isort . && flake8 . --max-line-length=88
	cd frontend && npm run lint:fix

# 문서 생성
docs:
	@echo "Generating API documentation..."
	cd backend && python -c "import main; print('API docs available at http://localhost:8000/docs')"

# 성능 테스트
perf-test:
	@echo "Running performance tests..."
	cd backend && python scripts/performance_test.py

# 보안 감사
security-audit:
	@echo "Running security audit..."
	$(MAKE) test-security
	docker run --rm -v $(PWD):/app -w /app hadolint/hadolint:latest hadolint Dockerfile || true
	docker run --rm -v $(PWD):/app -w /app aquasec/trivy fs . || true
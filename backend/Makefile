# 드롭시핑 시스템 Makefile

.PHONY: help build up down logs shell db-shell redis-shell backup restore clean

# 기본 타겟
help:
	@echo "Available commands:"
	@echo "  build     - Docker 이미지 빌드"
	@echo "  up        - 서비스 시작"
	@echo "  down      - 서비스 중지"
	@echo "  logs      - 로그 확인"
	@echo "  shell     - 백엔드 컨테이너 쉘 접속"
	@echo "  db-shell  - 데이터베이스 쉘 접속"
	@echo "  redis-shell - Redis 쉘 접속"
	@echo "  backup    - 데이터베이스 백업"
	@echo "  restore   - 데이터베이스 복원"
	@echo "  clean     - 사용하지 않는 리소스 정리"
	@echo "  migrate   - 데이터베이스 마이그레이션"
	@echo "  test      - 테스트 실행"

# Docker 이미지 빌드
build:
	docker-compose build --no-cache

# 서비스 시작
up:
	docker-compose up -d

# 서비스 중지
down:
	docker-compose down

# 로그 확인
logs:
	docker-compose logs -f

# 특정 서비스 로그
logs-backend:
	docker-compose logs -f backend

logs-db:
	docker-compose logs -f db

logs-redis:
	docker-compose logs -f redis

logs-nginx:
	docker-compose logs -f nginx

# 백엔드 컨테이너 쉘 접속
shell:
	docker-compose exec backend /bin/bash

# 데이터베이스 쉘 접속
db-shell:
	docker-compose exec db psql -U dropshipping -d dropshipping_db

# Redis 쉘 접속
redis-shell:
	docker-compose exec redis redis-cli

# 데이터베이스 백업
backup:
	docker-compose run --rm backup

# 데이터베이스 복원 (백업 파일 경로 지정 필요)
restore:
	@read -p "Enter backup file path: " file; \
	docker-compose exec db pg_restore -U dropshipping -d dropshipping_db -v /backups/$$file

# 마이그레이션 실행
migrate:
	docker-compose exec backend alembic upgrade head

# 새 마이그레이션 생성
migration:
	@read -p "Enter migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

# 테스트 실행
test:
	docker-compose exec backend python -m pytest tests/ -v

# 테스트 (커버리지 포함)
test-coverage:
	docker-compose exec backend python -m pytest tests/ --cov=app --cov-report=html

# 코드 품질 검사
lint:
	docker-compose exec backend flake8 app/
	docker-compose exec backend black --check app/
	docker-compose exec backend isort --check-only app/

# 코드 포매팅
format:
	docker-compose exec backend black app/
	docker-compose exec backend isort app/

# 서비스 상태 확인
status:
	docker-compose ps

# 헬스체크
health:
	@echo "Checking application health..."
	@curl -s http://localhost/health | jq '.'

# 메트릭 확인 (Prometheus)
metrics:
	@echo "Current metrics:"
	@curl -s http://localhost/metrics | head -20

# 환경 초기화 (개발용)
init-dev:
	cp .env.production .env
	@echo "Please edit .env file with your settings"
	docker-compose up -d db redis
	sleep 10
	docker-compose exec backend alembic upgrade head

# 프로덕션 배포
deploy:
	@echo "Starting production deployment..."
	docker-compose -f docker-compose.yml up -d --build
	@echo "Waiting for services to start..."
	sleep 30
	@echo "Running health check..."
	curl -f http://localhost/health || exit 1
	@echo "Deployment completed successfully!"

# 사용하지 않는 리소스 정리
clean:
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# 완전 초기화 (주의: 모든 데이터 삭제)
reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker system prune -a -f; \
		docker volume prune -f; \
		echo "Reset completed."; \
	else \
		echo "Reset cancelled."; \
	fi

# SSL 인증서 생성 (자체 서명)
ssl-cert:
	mkdir -p ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout ssl/key.pem -out ssl/cert.pem \
		-subj "/C=KR/ST=Seoul/L=Seoul/O=Dropshipping/CN=localhost"

# 모니터링 대시보드 접속 URL 출력
dashboard-urls:
	@echo "Monitoring Dashboards:"
	@echo "  Grafana: http://localhost:3000 (admin/admin123)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Application: http://localhost"
	@echo "  API Docs: http://localhost/docs"
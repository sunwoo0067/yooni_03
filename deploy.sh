#!/bin/bash

# Yooini 배포 스크립트
set -e

echo "🚀 Yooini 배포를 시작합니다..."

# 환경 확인
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    ENVIRONMENT="production"
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
    echo "📦 프로덕션 환경으로 배포합니다."
else
    ENVIRONMENT="development"
    COMPOSE_FILE="docker-compose.yml"
    ENV_FILE=".env"
    echo "🛠️ 개발 환경으로 배포합니다."
fi

# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 환경 파일 $ENV_FILE이 존재하지 않습니다."
    echo "   .env.example을 참고하여 생성해주세요."
    exit 1
fi

echo "✅ 환경 파일 확인: $ENV_FILE"

# Docker 이미지 빌드
echo "🔨 Docker 이미지를 빌드합니다..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f $COMPOSE_FILE build --no-cache
else
    docker-compose -f $COMPOSE_FILE build
fi

# 기존 컨테이너 정리 (프로덕션 환경에서만)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🧹 기존 컨테이너를 정리합니다..."
    docker-compose -f $COMPOSE_FILE down
fi

# 컨테이너 시작
echo "🚀 컨테이너를 시작합니다..."
docker-compose -f $COMPOSE_FILE up -d

# 데이터베이스 준비 대기
echo "⏳ 데이터베이스 준비를 기다립니다..."
sleep 10

# 데이터베이스 마이그레이션
echo "🗃️ 데이터베이스 마이그레이션을 실행합니다..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f $COMPOSE_FILE exec web python manage.py migrate
else
    docker-compose -f $COMPOSE_FILE exec web python manage.py migrate
fi

# 정적 파일 수집 (프로덕션 환경에서만)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "📁 정적 파일을 수집합니다..."
    docker-compose -f $COMPOSE_FILE exec web python manage.py collectstatic --noinput
fi

# 슈퍼유저 생성 확인
echo "👤 관리자 계정을 확인합니다..."
if [ "$ENVIRONMENT" = "production" ]; then
    echo "   프로덕션 환경에서는 수동으로 슈퍼유저를 생성해주세요:"
    echo "   docker-compose -f $COMPOSE_FILE exec web python manage.py createsuperuser"
else
    # 개발 환경에서는 기본 슈퍼유저 생성 (선택사항)
    echo "   개발 환경: 필요시 python manage.py createsuperuser 실행"
fi

# Celery 스케줄 설정
echo "⏰ Celery 주기적 작업을 설정합니다..."
docker-compose -f $COMPOSE_FILE exec web python manage.py setup_celery_beat

# 상태 확인
echo "🔍 서비스 상태를 확인합니다..."
docker-compose -f $COMPOSE_FILE ps

echo ""
echo "✅ 배포가 완료되었습니다!"
echo ""
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🌐 프로덕션 서비스 URL:"
    echo "   - 웹 애플리케이션: https://yourdomain.com"
    echo "   - 관리자: https://yourdomain.com/admin/"
    echo "   - Flower (Celery 모니터링): https://yourdomain.com:5555"
else
    echo "🌐 개발 서비스 URL:"
    echo "   - 웹 애플리케이션: http://localhost:8000"
    echo "   - 관리자: http://localhost:8000/admin/"
    echo "   - Flower (Celery 모니터링): http://localhost:5555"
fi
echo ""
echo "📊 모니터링:"
echo "   - 로그 확인: docker-compose -f $COMPOSE_FILE logs -f"
echo "   - 컨테이너 상태: docker-compose -f $COMPOSE_FILE ps"
echo "   - 서비스 중지: docker-compose -f $COMPOSE_FILE down"
echo ""
echo "🎉 Yooini 시스템이 정상적으로 시작되었습니다!"
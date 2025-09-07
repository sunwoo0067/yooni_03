#!/bin/bash
# Yooni Dropshipping System - Personal User Edition
# 개인 사용자용 간소화된 시작 스크립트 (Linux/macOS)

echo "=========================================="
echo "Yooni 드롭쉬핑 시스템 - 개인 사용자용"
echo "=========================================="

# 환경 변수 설정
export YOONI_ENV_MODE=personal
export APP_HOST=127.0.0.1
export APP_PORT=8000
export DEBUG=true

echo "🚀 개인 사용자 모드로 시스템 시작..."
echo "📋 설정 정보:"
echo "   - 환경 모드: $YOONI_ENV_MODE"
echo "   - 호스트: $APP_HOST"
echo "   - 포트: $APP_PORT"
echo "   - 디버그 모드: $DEBUG"
echo ""

# Python 가상 환경 활성화 (존재하는 경우)
if [ -f "../.venv/bin/activate" ]; then
    echo "🔧 Python 가상 환경 활성화 중..."
    source ../.venv/bin/activate
    echo ""
fi

# 필요한 디렉토리 생성
echo "📁 로그 및 업로드 디렉토리 확인 중..."
mkdir -p logs
mkdir -p uploads
mkdir -p backups
echo ""

# 백엔드 서버 시작
echo "🚀 백엔드 서버 시작 중..."
echo "   접속 주소: http://localhost:8000"
echo "   API 문서: http://localhost:8000/docs"
echo ""

python main_personal.py

echo ""
echo "🛑 시스템이 종료되었습니다."
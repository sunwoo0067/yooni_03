# 드랍쉬핑 자동화 시스템 설치 및 설정 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 과정](#설치-과정)
3. [환경 변수 설정](#환경-변수-설정)
4. [계정 설정](#계정-설정)
5. [API 키 설정](#api-키-설정)
6. [첫 상품 등록](#첫-상품-등록)
7. [대시보드 접속](#대시보드-접속)
8. [문제 해결](#문제-해결)

## 🖥️ 시스템 요구사항

### 최소 요구사항
- **운영체제**: Windows 10+ / macOS 10.14+ / Ubuntu 18.04+
- **CPU**: Intel i5 또는 AMD Ryzen 5 이상
- **메모리**: 8GB RAM 이상
- **저장공간**: 50GB 이상 여유공간
- **인터넷**: 안정적인 브로드밴드 연결

### 권장 사양
- **CPU**: Intel i7 또는 AMD Ryzen 7 이상
- **메모리**: 16GB RAM 이상
- **저장공간**: SSD 100GB 이상
- **네트워크**: 광랜 연결

### 필수 소프트웨어
- Python 3.9 이상
- Node.js 16 이상
- PostgreSQL 13 이상
- Redis 6 이상
- Docker (선택사항)

## 🚀 설치 과정

### 1. Python 환경 설정

```bash
# Python 버전 확인
python --version

# 가상환경 생성
python -m venv dropshipping_env

# 가상환경 활성화
# Windows
dropshipping_env\Scripts\activate
# macOS/Linux
source dropshipping_env/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설치

#### PostgreSQL 설치 (Windows)
```bash
# Chocolatey 사용
choco install postgresql

# 또는 공식 사이트에서 다운로드
# https://www.postgresql.org/download/windows/
```

#### PostgreSQL 설치 (macOS)
```bash
# Homebrew 사용
brew install postgresql
brew services start postgresql
```

#### PostgreSQL 설치 (Ubuntu)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Redis 설치

#### Windows
```bash
# WSL 사용 또는 Redis for Windows
# https://redis.io/download
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 4. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone https://github.com/your-repo/dropshipping-automation.git
cd dropshipping-automation

# 의존성 설치
pip install -r requirements.txt
npm install

# 데이터베이스 초기화
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

## 🔧 환경 변수 설정

### .env 파일 생성
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost:5432/dropshipping_db
REDIS_URL=redis://localhost:6379/0

# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI 서비스 API 키
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# 이미지 처리 서비스
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# 웹드라이버 설정
CHROME_DRIVER_PATH=/path/to/chromedriver
HEADLESS_MODE=True

# 알림 설정
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/system.log
```

### 환경별 설정

#### 개발 환경 (.env.development)
```env
DEBUG=True
LOG_LEVEL=DEBUG
API_RATE_LIMIT=100
CONCURRENT_TASKS=5
```

#### 운영 환경 (.env.production)
```env
DEBUG=False
LOG_LEVEL=INFO
API_RATE_LIMIT=1000
CONCURRENT_TASKS=20
CACHE_TIMEOUT=3600
```

## 👤 계정 설정

### 1. 마켓플레이스 계정 준비

#### 쿠팡 파트너스
1. **계정 생성**: [쿠팡 파트너스](https://partners.coupang.com) 가입
2. **사업자 등록**: 사업자등록증 업로드
3. **API 신청**: 개발자 센터에서 API 키 발급 신청
4. **승인 대기**: 보통 1-2주 소요

#### 네이버 쇼핑
1. **스마트스토어 개설**: [네이버 스마트스토어](https://sell.smartstore.naver.com)
2. **상품 등록 권한 확인**: 기본 상품 몇 개 수동 등록
3. **API 신청**: 네이버 개발자 센터에서 API 이용 신청

#### 11번가
1. **판매자 등록**: [11번가 판매자센터](https://sell.11st.co.kr)
2. **입점 심사**: 사업자 정보 및 상품 정보 제출
3. **API 연동**: 11번가 API 이용 신청

### 2. 도매 업체 계정

#### 젠트레이드
```python
# config/accounts.py에 추가
GENTRADE_CONFIG = {
    'username': 'your_username',
    'password': 'your_password',
    'api_key': 'your_api_key',
    'base_url': 'https://api.gentrade.co.kr'
}
```

#### 오너클랜
```python
OWNERSCLAN_CONFIG = {
    'member_id': 'your_member_id',
    'api_key': 'your_api_key',
    'secret_key': 'your_secret_key'
}
```

#### 도매꾹
```python
DOMEMEGGUK_CONFIG = {
    'username': 'your_username',
    'password': 'your_password',
    'company_code': 'your_company_code'
}
```

## 🔑 API 키 설정

### 1. OpenAI API 설정
```bash
# OpenAI 플랫폼에서 API 키 발급
# https://platform.openai.com/api-keys

# 사용량 제한 설정 (월 $100 권장)
# 결제 정보 등록 필수
```

### 2. 마켓플레이스 API 설정

#### 쿠팡 API
```python
# src/config/marketplace_config.py
COUPANG_CONFIG = {
    'access_key': 'your_access_key',
    'secret_key': 'your_secret_key',
    'vendor_id': 'your_vendor_id',
    'base_url': 'https://api-gateway.coupang.com'
}
```

#### 네이버 API
```python
NAVER_CONFIG = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'redirect_uri': 'your_redirect_uri',
    'base_url': 'https://api.commerce.naver.com'
}
```

### 3. API 키 보안 설정

```python
# src/security/key_manager.py
from cryptography.fernet import Fernet

class APIKeyManager:
    def __init__(self):
        self.cipher = Fernet(Fernet.generate_key())
    
    def encrypt_key(self, api_key: str) -> str:
        """API 키 암호화"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_key(self, encrypted_key: str) -> str:
        """API 키 복호화"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
```

## 📦 첫 상품 등록

### 1. 시스템 테스트

```bash
# 연결 테스트
python test_connections.py

# 기본 워크플로우 테스트
python -m pytest tests/test_basic_workflow.py -v
```

### 2. 수동 상품 등록 (테스트용)

```python
# scripts/manual_product_test.py
import asyncio
from src.pipeline.workflow_engine import WorkflowEngine

async def test_single_product():
    engine = WorkflowEngine()
    
    # 테스트 상품 정보
    test_product = {
        'name': '테스트 상품',
        'price': 10000,
        'category': '생활용품',
        'description': '테스트용 상품입니다.',
        'images': ['test_image.jpg']
    }
    
    # 워크플로우 실행
    result = await engine.process_single_product(test_product)
    print(f"등록 결과: {result}")

if __name__ == "__main__":
    asyncio.run(test_single_product())
```

### 3. 자동화 파이프라인 시작

```bash
# 일일 자동화 스케줄 시작
python scripts/start_daily_automation.py

# 실시간 주문 모니터링 시작
python scripts/start_order_monitoring.py
```

## 📊 대시보드 접속

### 1. 웹 서버 시작

```bash
# Django 개발 서버 시작
python manage.py runserver 0.0.0.0:8000

# 또는 Gunicorn 사용 (운영환경)
gunicorn dropshipping.wsgi:application --bind 0.0.0.0:8000
```

### 2. 대시보드 접속

```
http://localhost:8000/dashboard/
```

### 3. 초기 설정 마법사

1. **계정 연동**: 마켓플레이스 계정 연결
2. **카테고리 설정**: 주력 판매 카테고리 선택
3. **자동화 스케줄**: 상품 수집 및 등록 스케줄 설정
4. **알림 설정**: 텔레그램 봇 연결

### 4. 주요 기능 사용법

#### 상품 수집 설정
```javascript
// 대시보드에서 설정
{
    "schedule": "0 9 * * *",  // 매일 오전 9시
    "categories": ["생활용품", "패션", "전자제품"],
    "min_score": 70,
    "max_products": 100
}
```

#### 등록 스케줄 설정
```javascript
{
    "coupang": {
        "schedule": "0 10 * * *",
        "daily_limit": 50
    },
    "naver": {
        "schedule": "0 11 * * *",
        "daily_limit": 30
    }
}
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. 데이터베이스 연결 오류
```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 데이터베이스 권한 확인
sudo -u postgres psql
\l  # 데이터베이스 목록 확인
\du  # 사용자 권한 확인
```

#### 2. Redis 연결 오류
```bash
# Redis 서비스 확인
redis-cli ping

# Redis 로그 확인
sudo tail -f /var/log/redis/redis-server.log
```

#### 3. API 키 오류
```python
# API 키 테스트 스크립트
import requests

def test_api_key(api_key, endpoint):
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(endpoint, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
```

#### 4. 크롬 드라이버 오류
```bash
# 크롬 버전 확인
google-chrome --version

# 해당 버전의 드라이버 다운로드
# https://chromedriver.chromium.org/

# 드라이버 경로 설정
export PATH=$PATH:/path/to/chromedriver
```

### 로그 확인

#### 시스템 로그
```bash
# 전체 시스템 로그
tail -f logs/system.log

# 오류 로그만
grep ERROR logs/system.log

# 특정 모듈 로그
grep "product_collection" logs/system.log
```

#### 성능 모니터링
```python
# scripts/monitor_performance.py
import psutil
import asyncio

async def monitor_system():
    while True:
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        print(f"CPU: {cpu_percent}%")
        print(f"Memory: {memory.percent}%")
        
        await asyncio.sleep(60)
```

### 백업 및 복구

#### 데이터베이스 백업
```bash
# 일일 백업 스크립트
#!/bin/bash
DATE=$(date +%Y%m%d)
pg_dump dropshipping_db > backups/db_backup_$DATE.sql

# 백업 파일 압축
gzip backups/db_backup_$DATE.sql
```

#### 설정 파일 백업
```bash
# 중요 설정 파일들
cp .env config_backup/
cp src/config/*.py config_backup/
tar -czf config_backup_$(date +%Y%m%d).tar.gz config_backup/
```

### 지원 및 도움

#### 기술 지원
- **이메일**: support@dropshipping-system.com
- **문서**: https://docs.dropshipping-system.com
- **커뮤니티**: https://community.dropshipping-system.com

#### 자주 묻는 질문
1. **Q: 일일 상품 등록 한도는?**
   A: 플랫폼별로 다름. 쿠팡 50개, 네이버 30개 권장

2. **Q: AI 모델 비용은?**
   A: OpenAI API 기준 월 $50-100 예상

3. **Q: 서버 사양 권장사항은?**
   A: 최소 4코어 CPU, 8GB RAM, SSD 스토리지

#### 업데이트 확인
```bash
# 최신 버전 확인
git fetch origin
git status

# 업데이트 적용
git pull origin main
pip install -r requirements.txt --upgrade
python manage.py migrate
```

## 🎯 다음 단계

설치가 완료되면 다음 가이드들을 참고하세요:

1. **[OPERATION_GUIDE.md](OPERATION_GUIDE.md)** - 일일 운영 가이드
2. **[API_EXAMPLES.md](API_EXAMPLES.md)** - API 사용 예제
3. **[OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)** - 성능 최적화 가이드
4. **[EXPANSION_GUIDE.md](EXPANSION_GUIDE.md)** - 기능 확장 가이드

축하합니다! 드랍쉬핑 자동화 시스템 설치가 완료되었습니다. 🎉
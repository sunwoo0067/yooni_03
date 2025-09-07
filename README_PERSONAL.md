# 🚀 Yooni 드롭쉬핑 시스템 - 개인 사용자용

개인 사용자나 소규모 비즈니스를 위한 간소화된 드롭시핑 자동화 솔루션입니다.

## 📋 목차

- [개요](#개요)
- [주요 특징](#주요-특징)
- [시스템 요구사항](#시스템-요구사항)
- [빠른 시작](#빠른-시작)
- [설치 가이드](#설치-가이드)
- [사용법](#사용법)
- [설정](#설정)
- [문제 해결](#문제-해결)

## 🎯 개요

이 개인 사용자용 버전은 기업용 기능의 하위 호환으로, 개인 사용자나 소규모 비즈니스가 드롭시핑 자동화를 쉽게 시작할 수 있도록 설계되었습니다. 복잡한 설정과 고급 기능을 제거하고 핵심 기능만을 제공합니다.

## ✨ 주요 특징

### 🎯 간소화된 구조
- 단일 데이터베이스(SQLite) 사용
- 최소한의 환경 변수 설정
- 직관적인 웹 인터페이스

### 🔧 핵심 기능만 포함
- 상품 수집 (공급사 연동)
- 상품 등록 (마켓플레이스 연동)
- 주문 처리 자동화
- 기본적인 성과 분석

### 🚀 쉬운 설치 및 사용
- 클릭 한 번으로 시작 가능한 스크립트
- 자동 데이터베이스 초기화
- 상세한 설정 가이드

## 💻 시스템 요구사항

### 최소 사양
- **운영체제**: Windows 10 이상, macOS 10.15 이상, Ubuntu 18.04 이상
- **RAM**: 4GB 이상
- **저장공간**: 20GB 이상
- **Python**: 3.9 이상
- **Node.js**: 16 이상 (프론트엔드용)

### 권장 사양
- **운영체제**: Windows 11, macOS 12 이상, Ubuntu 20.04 이상
- **RAM**: 8GB 이상
- **저장공간**: 50GB 이상 (상품 이미지 및 로그 저장을 위해)
- **CPU**: 듀얼 코어 이상

## 🚀 빠른 시작

### Windows 사용자
```cmd
# 1. start_personal.bat 파일 실행
start_personal.bat
```

### macOS/Linux 사용자
```bash
# 1. 터미널에서 스크립트 실행
./start_personal.sh
```

### Docker 사용자
```bash
# 1. 개인 사용자용 Docker Compose 실행
docker-compose -f docker-compose.personal.yml up -d
```

## 🛠️ 설치 가이드

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/yooni-dropshipping-personal.git
cd yooni-dropshipping-personal
```

### 2. Python 가상 환경 설정
```bash
# 가상 환경 생성
python -m venv .venv

# 가상 환경 활성화
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements-personal.txt
```

### 4. 환경 설정
```bash
# .env.simple 파일을 .env로 복사
cp backend/.env.simple .env

# .env 파일 편집하여 API 키 등 설정
```

### 5. 프론트엔드 의존성 설치
```bash
cd frontend
npm install
```

## 💡 사용법

### 1. 서버 시작
```bash
# 백엔드 서버 시작
python backend/main_personal.py

# 또는 시작 스크립트 사용
./start_personal.bat  # Windows
./start_personal.sh   # macOS/Linux
```

### 2. 프론트엔드 시작
```bash
cd frontend
npm run dev
```

### 3. 웹 인터페이스 접속
- 백엔드: http://localhost:8000
- 프론트엔드: http://localhost:3000
- API 문서: http://localhost:8000/docs

## ⚙️ 설정

### 환경 변수
개인 사용자용으로 필요한 최소한의 환경 변수만 설정하면 됩니다:

```env
# 애플리케이션 설정
ENVIRONMENT=personal
PROJECT_NAME="Yooni Dropshipping - Personal Edition"

# 데이터베이스 (SQLite 사용)
DATABASE_URL=sqlite:///./yooni_personal.db

# 단일 사용자 모드
SINGLE_USER_MODE=true
SINGLE_USER_EMAIL=personal@yooni.local

# API 키 (필요한 것만 설정)
COUPANG_VENDOR_ID=your-coupang-vendor-id
COUPANG_ACCESS_KEY=your-coupang-access-key
```

### 공급사 API 키 설정
최소한 하나의 공급사 API 키를 설정해야 합니다:
- OwnerClan
- ZenTrade
- DoMaeKkuk

### 마켓플레이스 API 키 설정
최소한 하나의 마켓플레이스 API 키를 설정해야 합니다:
- Coupang
- Naver Smart Store

## 🔧 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음
- Python 가상 환경이 활성화되었는지 확인
- 필요한 의존성이 모두 설치되었는지 확인
- .env 파일이 올바르게 설정되었는지 확인

#### 2. 데이터베이스 연결 오류
- yooni_personal.db 파일이 생성되었는지 확인
- 데이터베이스 파일에 대한 읽기/쓰기 권한이 있는지 확인

#### 3. API 키 인증 오류
- API 키가 올바르게 입력되었는지 확인
- 해당 플랫폼의 API 키 생성 방법을 다시 확인

### 로그 확인
문제 발생 시 다음 로그 파일을 확인하세요:
- `backend/logs/personal_app.log`
- `frontend/logs/access.log`
- `frontend/logs/error.log`

### 지원 받기
문제가 지속될 경우 다음 정보를 포함하여 문의해주세요:
1. 사용 중인 운영체제 및 버전
2. Python 및 Node.js 버전
3. 오류 메시지 및 로그 내용
4. 재현 방법

---

<div align="center">

**⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요! ⭐**

개인 사용자용 Yooni 드롭쉬핑 시스템

</div>
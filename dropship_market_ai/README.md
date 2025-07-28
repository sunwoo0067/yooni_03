# Dropship Market AI System

AI 기반 드랍쉬핑 마켓 관리 시스템

## 주요 기능

### 1. 마켓 API 데이터 완전 수집
- 쿠팡, 네이버 쇼핑 등 주요 마켓플레이스 통합
- 상품 정보, 리뷰, 순위, 판매 데이터 실시간 수집
- 경쟁사 분석 및 가격 모니터링

### 2. 상품 순환 등록 시스템
- 노출 최적화를 위한 자동 재등록
- 순위 기반, 성과 기반, 계절별 순환 전략
- A/B 테스팅을 통한 최적 전략 도출

### 3. 딥러닝 기반 판매 예측
- LSTM 모델을 활용한 시계열 예측
- 7일 판매량 예측 (95% 신뢰도)
- 재고 최적화 및 수요 예측

### 4. 리뷰 감성 분석
- 한국어 BERT 모델 기반 감성 분석
- 제품 개선점 자동 추출
- 고객 유형 분류 및 인사이트 제공

### 5. 자동 마켓 최적화
- XGBoost 기반 가격 최적화
- 상품명, 키워드 A/B 테스팅
- 실시간 성과 모니터링 및 자동 조정

### 6. 통합 대시보드
- 실시간 매출/성과 모니터링
- 이상 징후 자동 감지 및 알림
- 일간/주간/월간 리포트

## 시스템 구조

```
dropship_market_ai/
├── src/
│   ├── collectors/      # 마켓플레이스 데이터 수집
│   ├── analyzers/       # 리뷰 분석, 감성 분석
│   ├── predictors/      # ML/DL 예측 모델
│   ├── optimizers/      # 자동 최적화 시스템
│   ├── database/        # 데이터베이스 모델
│   ├── dashboard/       # 대시보드 및 알림
│   ├── api/            # FastAPI 엔드포인트
│   └── utils/          # 유틸리티 함수
├── configs/            # 설정 파일
├── models/             # 학습된 ML 모델
├── scripts/            # 스케줄러 및 스크립트
└── tests/              # 테스트 코드
```

## 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설정

```bash
# PostgreSQL 및 Redis 실행 (Docker)
docker-compose up -d postgres redis

# 데이터베이스 마이그레이션
alembic upgrade head
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```env
# 마켓플레이스 API 키
COUPANG_API_KEY=your_api_key
COUPANG_SECRET_KEY=your_secret_key
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# 알림 설정
SLACK_WEBHOOK_URL=your_webhook_url
```

### 4. 애플리케이션 실행

```bash
# API 서버 실행
uvicorn src.api.main:app --reload

# 스케줄러 실행 (별도 터미널)
python scripts/scheduler.py
```

### 5. Docker로 전체 시스템 실행

```bash
docker-compose up
```

## API 문서

API 서버 실행 후 다음 URL에서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 주요 API 엔드포인트

### 대시보드
- `GET /api/v1/dashboard/summary` - 대시보드 요약
- `GET /api/v1/dashboard/metrics/daily` - 일일 메트릭스
- `GET /api/v1/dashboard/alerts/active` - 활성 알림

### 상품 관리
- `GET /api/v1/products` - 상품 목록
- `POST /api/v1/products/{id}/collect` - 데이터 수집
- `POST /api/v1/products/{id}/rotate` - 상품 순환

### 예측 및 최적화
- `GET /api/v1/predictions/sales/{product_id}` - 판매 예측
- `POST /api/v1/optimizations/price/{product_id}` - 가격 최적화
- `POST /api/v1/optimizations/ab-test` - A/B 테스트 생성

## 모니터링

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## 개발 가이드

### 새로운 마켓플레이스 추가

1. `src/collectors/` 에 새 수집기 클래스 생성
2. `BaseCollector` 상속 및 필수 메서드 구현
3. `config.yaml` 에 마켓플레이스 설정 추가

### ML 모델 추가

1. `src/predictors/` 에 예측 모델 클래스 생성
2. 학습 및 예측 메서드 구현
3. 스케줄러에 학습 작업 추가

## 라이선스

Proprietary - All rights reserved
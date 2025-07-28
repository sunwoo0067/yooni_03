# 🛍️ Simple Product Collector - MVP

단순화된 상품 수집 시스템 MVP 버전

## 📂 프로젝트 구조

```
simple_collector/
├── collectors/                 # 도매처별 수집기
│   ├── __init__.py
│   ├── base_collector.py      # 기본 수집기 클래스
│   ├── zentrade_collector.py  # 젠트레이드 (3,500개 전체)
│   ├── ownerclan_collector.py # 오너클랜 (2단계 수집)
│   └── domeggook_collector.py # 도매꾹 (카테고리 기반)
├── processors/                # 데이터 처리
│   ├── __init__.py
│   ├── excel_processor.py     # 엑셀 업로드 처리
│   └── incremental_sync.py    # 증분 수집
├── database/                  # 데이터베이스
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy 모델
│   └── connection.py         # DB 연결
├── api/                      # REST API
│   ├── __init__.py
│   ├── main.py              # FastAPI 메인
│   └── endpoints.py         # API 엔드포인트
├── config/                   # 설정
│   ├── __init__.py
│   └── settings.py          # 환경 설정
├── utils/                    # 유틸리티
│   ├── __init__.py
│   └── logger.py            # 로깅
├── requirements.txt          # 의존성
└── main.py                  # 애플리케이션 진입점
```

## 🎯 주요 기능

1. **도매처별 상품 수집**
   - 젠트레이드: 3,500개 전체 수집
   - 오너클랜: 2단계 수집 (코드 수집 → 상세 수집)
   - 도매꾹: 카테고리 기반 수집

2. **엑셀 업로드**
   - 공급사별 엑셀 파일 업로드
   - 자동 파싱 및 데이터베이스 저장

3. **증분 수집**
   - 신규 상품 감지
   - 업데이트된 상품 동기화

4. **단순한 API**
   - RESTful API
   - 기본적인 CRUD 작업

## 🔧 기술 스택

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Task Queue**: 없음 (동기식 처리)
- **Authentication**: 없음 (로컬 사용)
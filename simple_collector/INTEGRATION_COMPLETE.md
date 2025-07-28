# yoni_03 데이터베이스 통합 완료

## 현재 상태

기존 yoni_03 PostgreSQL 데이터베이스로 통합이 완료되었습니다.

### 데이터베이스 정보
- **연결 정보**: `postgresql://postgres:1234@localhost:5433/yoni_03`
- **PostgreSQL 버전**: 17.5

### 테이블 현황
Simple Collector 테이블이 이미 존재합니다:
- ✅ products (상품)
- ✅ suppliers (공급사) 
- ✅ collection_logs (수집 로그)
- ✅ excel_uploads (엑셀 업로드)

### 데이터 현황
- **총 상품 수**: 60개
  - zentrade: 12개
  - ownerclan: 21개
  - domeggook: 27개

## 실행 방법

### 1. 백엔드 서버 시작
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector
python main.py
# 메뉴에서 "2. API 서버 시작" 선택
```

### 2. 프론트엔드 시작
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector\frontend
npm install  # 처음 한 번만
npm run dev
```

### 3. 웹 브라우저 접속
http://localhost:3000

## 통합의 장점

1. **데이터 일원화**: 모든 상품 데이터가 하나의 DB에서 관리
2. **기존 인프라 활용**: 이미 실행 중인 PostgreSQL 사용
3. **백업/복구 통합**: 하나의 DB만 관리하면 됨
4. **성능 최적화**: PostgreSQL의 JSONB 타입 활용

## 주의사항

- 기존 backend 프로젝트와 같은 DB를 사용하므로 테이블명 충돌에 주의
- Simple Collector는 단순한 구조의 테이블만 사용 (products, suppliers 등)
- 필요시 스키마를 분리하여 격리 가능

## 다음 단계

1. ✅ 웹 인터페이스에서 상품 조회/수집 테스트
2. ✅ 실제 API 키 설정 및 연동
3. ⏳ 배치 스케줄러 구현
4. ⏳ 프로덕션 환경 배포
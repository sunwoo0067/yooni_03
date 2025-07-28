# Simple Product Collector - 웹 인터페이스

## 개요
Simple Product Collector의 React/TypeScript 기반 웹 관리 인터페이스입니다.

## 주요 기능
- **대시보드**: 전체 현황 및 통계 확인
- **상품 목록**: 수집된 상품 조회 및 검색
- **상품 수집**: 공급사별 전체/증분 수집 실행
- **엑셀 업로드**: 엑셀 파일로 상품 일괄 등록
- **설정**: API 키 및 수집 옵션 관리

## 기술 스택
- React 18
- TypeScript
- Material-UI (MUI)
- React Query
- Vite
- React Router

## 설치 및 실행

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 개발 서버 실행
```bash
npm run dev
```
- http://localhost:3000 에서 확인 가능
- API 서버는 http://localhost:8000 에서 실행되어야 함

### 3. 프로덕션 빌드
```bash
npm run build
```

## 프로젝트 구조
```
frontend/
├── src/
│   ├── api/         # API 클라이언트
│   ├── components/  # 공통 컴포넌트
│   ├── pages/       # 페이지 컴포넌트
│   │   ├── Dashboard.tsx    # 대시보드
│   │   ├── Products.tsx     # 상품 목록
│   │   ├── Collection.tsx   # 상품 수집
│   │   ├── ExcelUpload.tsx  # 엑셀 업로드
│   │   └── Settings.tsx     # 설정
│   ├── App.tsx      # 메인 앱 컴포넌트
│   └── main.tsx     # 엔트리 포인트
├── package.json
└── vite.config.ts
```

## API 연동
- Vite proxy 설정으로 `/api` 경로를 백엔드로 프록시
- React Query로 데이터 페칭 및 캐싱 관리
- Axios 인터셉터로 에러 처리

## 화면 구성

### 1. 대시보드
- 전체 상품 수, 활성 공급사 수
- 오늘 수집 건수, 수집 성공률
- 공급사별 상품 현황
- 최근 수집 활동 로그

### 2. 상품 목록
- 데이터 그리드로 상품 정보 표시
- 공급사별 필터링
- 상품코드, 상품명, 카테고리 검색
- 엑셀 다운로드 기능

### 3. 상품 수집
- 공급사별 수집 버튼
- 전체 수집 / 증분 수집 선택
- 실시간 수집 상태 모니터링
- 수집 기록 테이블

### 4. 엑셀 업로드
- 드래그 앤 드롭 파일 업로드
- 공급사별 템플릿 다운로드
- 업로드 진행률 표시
- 업로드 기록 관리

### 5. 설정
- 공급사별 API 키 설정
- 수집 옵션 (배치 크기, 재시도 횟수 등)
- 자동 동기화 설정
# Yooni Dropshipping Frontend

Yooni 드랍쉬핑 시스템의 React 기반 프론트엔드 애플리케이션입니다.

## 기술 스택

- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안정성
- **Vite** - 빌드 도구
- **Material-UI (MUI)** - UI 컴포넌트 라이브러리
- **Tailwind CSS** - 유틸리티 CSS 프레임워크
- **Redux Toolkit** - 상태 관리
- **React Query** - 서버 상태 관리
- **React Router v6** - 라우팅
- **Chart.js** - 데이터 시각화
- **Axios** - HTTP 클라이언트

## 시작하기

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

```env
VITE_API_URL=http://localhost:8000
```

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/       # 재사용 가능한 컴포넌트
│   │   ├── common/      # 공통 컴포넌트
│   │   └── layouts/     # 레이아웃 컴포넌트
│   ├── pages/           # 페이지 컴포넌트
│   │   ├── auth/        # 인증 관련 페이지
│   │   └── Dashboard.tsx # 대시보드
│   ├── services/        # API 서비스
│   ├── store/           # Redux 스토어
│   ├── hooks/           # 커스텀 훅
│   ├── types/           # TypeScript 타입 정의
│   ├── utils/           # 유틸리티 함수
│   └── styles/          # 글로벌 스타일
├── public/              # 정적 파일
└── index.html          # HTML 진입점
```

## 주요 기능

### 인증
- JWT 기반 인증
- 자동 토큰 갱신
- 로그인/로그아웃 관리

### 대시보드
- 실시간 통계 표시
- 차트 시각화 (매출, 주문, 재고)
- 최근 활동 내역

### 상품 관리
- 상품 목록 조회
- 상품 추가/수정/삭제
- 재고 관리

### 주문 관리
- 주문 목록 및 상태 관리
- 주문 상세 정보
- 배송 추적

### 고객 관리
- 고객 목록 조회
- 고객 상세 정보
- 구매 이력

## 빌드 및 배포

### 프로덕션 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

### 빌드 미리보기

```bash
npm run preview
```

## 코드 품질

### 린트 실행

```bash
npm run lint
```

### 타입 체크

```bash
npm run type-check
```

## 데모 계정

개발 환경에서는 다음 계정으로 로그인할 수 있습니다:

- 이메일: `admin@yooni.com`
- 비밀번호: `password123`

## API 연동

API 서버가 `http://localhost:8000`에서 실행 중이어야 합니다.
백엔드 README를 참고하여 API 서버를 먼저 시작하세요.

## 개발 가이드

### 새 페이지 추가

1. `src/pages/` 디렉토리에 새 컴포넌트 생성
2. `src/App.tsx`에 라우트 추가
3. `src/components/layouts/MainLayout.tsx`에 메뉴 항목 추가

### API 엔드포인트 추가

1. `src/services/api.ts`에 새 엔드포인트 추가
2. 필요시 `src/types/`에 타입 정의 추가

### 상태 관리

- 전역 상태: Redux Toolkit 사용
- 서버 상태: React Query 사용
- 로컬 상태: React useState/useReducer 사용
# UI 테스트 가이드

## 서버 실행

### 1. API 서버 (터미널 1)
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 프론트엔드 (터미널 2)
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector\frontend
npm install  # 처음 한 번만
npm run dev
```

## UI 기능 확인

### 1. 대시보드 (http://localhost:3000/dashboard)
- ✅ 전체 상품 수: 60개
- ✅ 공급사별 상품 수 표시
- ✅ 최근 수집 활동 로그

### 2. 상품 목록 (http://localhost:3000/products)
- ✅ 60개 상품 표시
- ✅ 공급사별 필터링
- ✅ 검색 기능
- ✅ 엑셀 다운로드

### 3. 상품 수집 (http://localhost:3000/collection)
- ✅ 테스트 모드/실제 API 모드 스위치
- ✅ 공급사별 수집 버튼
  - 전체 수집 버튼 클릭 → 백그라운드 수집 시작
  - 증분 수집 버튼 클릭 → 증분 수집 실행
- ✅ 실시간 수집 상태 표시 (5초마다 자동 갱신)
- ✅ 수집 로그 테이블

### 4. 엑셀 업로드 (http://localhost:3000/excel)
- ✅ 파일 드래그 앤 드롭
- ✅ 공급사별 템플릿 다운로드
- ✅ 업로드 진행률
- ✅ 업로드 기록

### 5. 설정 (http://localhost:3000/settings)
- ✅ 공급사별 API 키 설정
- ✅ 연결 테스트 버튼
- ✅ API 키 저장

## 수집 테스트 방법

### 테스트 모드 수집
1. Collection 페이지에서 "테스트 모드" 활성화
2. 원하는 공급사의 "전체 수집" 버튼 클릭
3. 상단에 "수집이 시작되었습니다" 알림 확인
4. 수집 로그 테이블에서 진행 상태 확인
5. "진행 중" → "완료" 상태 변경 확인

### 실제 API 수집
1. Settings 페이지에서 API 키 입력
2. "연결 테스트" 버튼으로 확인
3. Collection 페이지에서 "실제 API 모드" 활성화
4. "전체 수집" 버튼 클릭

## 현재 상태
- API 서버: ✅ 정상 작동
- 프론트엔드: ✅ 모든 기능 구현됨
- 데이터베이스: 60개 상품 저장됨

## 문제 해결

### CORS 오류
API 서버가 실행 중인지 확인 (http://localhost:8000)

### 데이터가 표시되지 않음
1. API 서버 재시작
2. 브라우저 새로고침 (F5)
3. 개발자 도구 (F12) 콘솔 확인
# 서버 실행 가이드

## 1. 백엔드 API 서버 실행

터미널 1에서:
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector
python main.py
# 메뉴에서 "2. API 서버 시작" 선택
```

또는 직접 실행:
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## 2. 프론트엔드 개발 서버 실행

터미널 2에서:
```bash
cd D:\new\win_with_claude\yooni_03\simple_collector\frontend
npm install  # 처음 한 번만
npm run dev
```

## 3. 웹 브라우저에서 접속

http://localhost:3000

## 4. 확인할 수 있는 기능들

### 대시보드
- 전체 상품 수: 60개
- 공급사별 상품 수
- 최근 수집 활동

### 상품 목록
- 수집된 60개 상품 확인
- 공급사별 필터링
- 검색 기능
- 엑셀 다운로드

### 상품 수집
- 테스트 모드로 추가 수집
- 수집 상태 실시간 확인

### 설정
- API 키 입력 (실제 키가 있다면)
- 연결 테스트

## 현재 데이터베이스 상태

- **zentrade**: 12개 상품
- **ownerclan**: 21개 상품
- **domeggook**: 27개 상품
- **전체**: 60개 상품

## 문제 해결

### 포트 충돌 시
```bash
# 8000번 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /PID [프로세스ID] /F
```

### 데이터베이스 초기화가 필요한 경우
```bash
python main.py
# 메뉴에서 "1. 데이터베이스 초기화" 선택
```
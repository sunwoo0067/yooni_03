@echo off
echo ========================================
echo 드롭시핑 시스템 사용자 테스트 시작
echo ========================================

echo 1. 가상환경 활성화...
call venv\Scripts\activate.bat

echo 2. 환경 변수 설정...
copy config\test.env .env

echo 3. 데이터베이스 초기화...
python scripts\init_test_db.py

echo 4. 테스트 데이터 로드...
python scripts\load_test_data.py

echo 5. API 서버 시작...
echo 서버가 시작됩니다. 브라우저에서 http://localhost:8000/docs 를 열어주세요.
echo 테스트를 중단하려면 Ctrl+C를 누르세요.
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause

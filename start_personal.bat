@echo off
REM Yooni Dropshipping System - Personal User Edition
REM 개인 사용자용 간소화된 시작 스크립트

echo ==========================================
echo Yooni 드롭쉬핑 시스템 - 개인 사용자용
echo ==========================================

REM 환경 변수 설정
set YOONI_ENV_MODE=personal
set APP_HOST=127.0.0.1
set APP_PORT=8000
set DEBUG=true

echo 🚀 개인 사용자 모드로 시스템 시작...
echo 📋 설정 정보:
echo    - 환경 모드: %YOONI_ENV_MODE%
echo    - 호스트: %APP_HOST%
echo    - 포트: %APP_PORT%
echo    - 디버그 모드: %DEBUG%
echo.

REM Python 가상 환경 활성화 (존재하는 경우)
if exist "..\.venv\Scripts\activate.bat" (
    echo 🔧 Python 가상 환경 활성화 중...
    call ..\.venv\Scripts\activate.bat
    echo.
)

REM 필요한 디렉토리 생성
echo 📁 로그 및 업로드 디렉토리 확인 중...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "backups" mkdir backups
echo.

REM 백엔드 서버 시작
echo 🚀 백엔드 서버 시작 중...
echo    접속 주소: http://localhost:8000
echo    API 문서: http://localhost:8000/docs
echo.

python main_personal.py

echo.
echo 🛑 시스템이 종료되었습니다.
pause
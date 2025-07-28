@echo off
echo Starting Simple Product Collector Servers...
echo.

REM Start API server in new window
start "API Server" cmd /k "cd /d %~dp0 && python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"

REM Wait a bit for API to start
timeout /t 3 /nobreak > nul

REM Start frontend in new window  
start "Frontend Server" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo Servers started!
echo API Server: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit...
pause > nul
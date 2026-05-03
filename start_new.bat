@echo off
title TTCS New Stack Launcher
color 0A

echo ========================================
echo  TTCS - Backend + Frontend
echo ========================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Run:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/3] Starting Backend on port 5000...
start "Backend - http://localhost:5000" cmd /k "cd /d ""%~dp0Backend"" && call ""%~dp0.venv\Scripts\activate.bat"" && uvicorn api.main:app --host 0.0.0.0 --port 5000 --reload"

echo [3/3] Starting Frontend on port 8000...
timeout /t 3 /nobreak >nul
start "Frontend - http://localhost:8000" cmd /k "cd /d ""%~dp0Frontend"" && python -m http.server 8000"

echo.
echo Backend:      http://localhost:5000
echo API docs:     http://localhost:5000/docs
echo Frontend:     http://localhost:8000
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8000

pause

@echo off
title Backend API
color 0A

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
uvicorn api.main:app --app-dir "Backend" --host 0.0.0.0 --port 5000 --reload

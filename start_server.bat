@echo off
cd /d "C:\Users\hlifc\OneDrive\Desktop\markt geschäft\smart-investor-mvp"
title Smart Investor Pro - Port 8000
echo ========================================
echo   Smart Investor Pro
echo   Starte Server auf http://localhost:8000
echo ========================================
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
if %errorlevel% neq 0 (
    echo.
    echo Fehler beim Starten. Python installiert?
    pause
)

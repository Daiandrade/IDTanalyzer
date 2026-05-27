@echo off
cd /d "%~dp0"

echo ========================================
echo IDT ANALYZER
echo ========================================
echo.

REM Limpa porta 8501
echo Limpando porta 8501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 2^>nul') do taskkill /F /PID %%a 2>nul
timeout /t 1 /nobreak >nul

echo.
echo Iniciando aplicacao...
echo.
echo ========================================
echo ACESSE: http://localhost:8501
echo ========================================
echo.

python -m streamlit run app.py

pause

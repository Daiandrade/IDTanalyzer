@echo off
echo ==========================================
echo   IDT Analyzer v2.0 - Thomson Reuters
echo ==========================================
echo.

REM Navega para o diretorio do projeto
cd /d "%~dp0"

REM Limpa porta 8501 se estiver em uso
echo Verificando porta 8501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 2^>nul') do (
    echo Liberando porta 8501...
    taskkill /F /PID %%a 2>nul
)
timeout /t 1 /nobreak >nul

echo.
echo Iniciando aplicacao Streamlit...
echo.
echo ================
==========================
echo  ACESSE: http://localhost:8501
echo ==========================================
echo.
echo Pressione CTRL+C para parar o servidor
echo.

REM Inicia o Streamlit
python -m streamlit run app.py

pause

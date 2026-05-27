@echo off
echo ========================================
echo INICIANDO APP COM DEBUG
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Verificando Python...
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    pause
    exit /b 1
)
echo.

echo [2/4] Verificando Streamlit...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo ERRO: Streamlit nao instalado!
    echo Instalando dependencias...
    pip install -r requirements.txt
)
echo.

echo [3/4] Matando processos antigos na porta 8501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo.

echo [4/4] Iniciando Streamlit...
echo.
echo ========================================
echo ACESSE: http://localhost:8501
echo ========================================
echo.
echo Pressione CTRL+C para parar
echo.

streamlit run app.py
pause

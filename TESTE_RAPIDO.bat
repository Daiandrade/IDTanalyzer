@echo off
echo ========================================
echo IDT Analyzer - Setup e Teste Rapido
echo ========================================
echo.

echo [1/4] Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado!
    echo Feche este terminal e abra um novo.
    pause
    exit /b 1
)
echo OK!
echo.

echo [2/4] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO: Falha ao instalar dependencias
    pause
    exit /b 1
)
echo OK!
echo.

echo [3/4] Gerando hashes de senha...
python generate_password.py
echo.
echo IMPORTANTE: Copie os hashes acima e cole no config_auth.yaml
echo Pressione qualquer tecla apos copiar os hashes...
pause
echo.

echo [4/4] Iniciando aplicacao...
echo.
echo O navegador abrira automaticamente em http://localhost:8501
echo.
echo Login: admin / admin123
echo.
echo Pressione Ctrl+C para parar o servidor
echo.
streamlit run app.py

pause

@echo off
echo ========================================
echo LIMPANDO CACHE E REINICIANDO APP
echo ========================================
echo.

echo [1/3] Parando processos Streamlit...
taskkill /F /IM streamlit.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] Limpando cache do Streamlit...
if exist ".streamlit\cache" rmdir /S /Q ".streamlit\cache"
if exist "%USERPROFILE%\.streamlit\cache" rmdir /S /Q "%USERPROFILE%\.streamlit\cache"

echo [3/3] Iniciando aplicacao...
echo.
echo ========================================
echo App iniciando em http://localhost:8501
echo ========================================
echo.
streamlit run app.py --server.headless true

@echo off
echo ==========================================
echo   Atualizar Base de Aderencia - PRODUCAO
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/4] Verificando status do Git...
git status

echo.
echo [2/4] Adicionando base de aderencia ao Git...
git add config/Aderencia.xlsm
git add .gitignore

echo.
echo [3/4] Criando commit...
git commit -m "Add: Base de aderencia para producao"

echo.
echo [4/4] Enviando para producao (GitHub)...
git push origin main

echo.
echo ==========================================
echo   CONCLUIDO!
echo ==========================================
echo.
echo A base de aderencia foi enviada para producao.
echo O Streamlit Cloud ira atualizar automaticamente em alguns minutos.
echo.

pause

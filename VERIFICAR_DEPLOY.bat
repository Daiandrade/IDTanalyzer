@echo off
chcp 65001 >nul
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║          VERIFICAR STATUS DO DEPLOY - PRODUÇÃO                ║
echo ║              IDT Analyzer - Thomson Reuters                   ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/5] Verificando último commit local...
echo ────────────────────────────────────────────────────────────────
git log --oneline -1
echo.

echo [2/5] Verificando se está sincronizado com GitHub...
echo ────────────────────────────────────────────────────────────────
git status -sb
echo.

echo [3/5] Verificando arquivo de aderência no repositório...
echo ────────────────────────────────────────────────────────────────
git ls-files | findstr /i "Aderencia"
if %ERRORLEVEL% EQU 0 (
    echo ✅ Arquivo rastreado pelo Git
) else (
    echo ❌ Arquivo NÃO está no Git!
)
echo.

echo [4/5] Informações do arquivo local...
echo ────────────────────────────────────────────────────────────────
if exist "config\Aderencia.xlsm" (
    dir "config\Aderencia.xlsm" | findstr /i "Aderencia"
    echo ✅ Arquivo existe localmente
) else (
    echo ❌ Arquivo NÃO existe localmente!
)
echo.

echo [5/5] Links úteis para verificação...
echo ────────────────────────────────────────────────────────────────
echo.
echo 📦 GitHub Repository:
echo    https://github.com/Daiandrade/IDTanalyzer
echo.
echo 🔍 Verificar último commit no GitHub:
echo    https://github.com/Daiandrade/IDTanalyzer/commits/main
echo.
echo 🚀 Streamlit Cloud Dashboard:
echo    https://share.streamlit.io/
echo.
echo 📊 Logs do App (após login no Streamlit):
echo    Dashboard → Seu App → ⋮ (menu) → Logs
echo.
echo ────────────────────────────────────────────────────────────────
echo.
echo ⏱️  TEMPO ESTIMADO DE DEPLOY:
echo     • GitHub sync: Imediato ✅
echo     • Streamlit detecta: ~30 segundos
echo     • Build completo: 2-5 minutos
echo     • App disponível: ~5 minutos total
echo.
echo ────────────────────────────────────────────────────────────────
echo.
echo 📋 CHECKLIST DE VERIFICAÇÃO:
echo.
echo    ☐ 1. Abrir GitHub e verificar se commit aparece
echo    ☐ 2. Verificar se arquivo config/Aderencia.xlsm está lá
echo    ☐ 3. Acessar Streamlit Cloud Dashboard
echo    ☐ 4. Verificar se app está "Building" ou "Running"
echo    ☐ 5. Aguardar build terminar (luz verde)
echo    ☐ 6. Abrir app em produção
echo    ☐ 7. Fazer login como admin
echo    ☐ 8. Ir em Configurações
echo    ☐ 9. Verificar se mostra "✅ Base configurada"
echo.
echo ────────────────────────────────────────────────────────────────
echo.

choice /C AG /M "Deseja abrir GitHub (G) ou aguardar (A)"
if errorlevel 2 (
    echo Abrindo GitHub no navegador...
    start https://github.com/Daiandrade/IDTanalyzer/commits/main
)

echo.
pause

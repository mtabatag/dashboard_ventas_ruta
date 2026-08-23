@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

set "PY=C:\Users\Marcos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONPATH="
set "PYTHONIOENCODING=utf-8"

echo ================================================
echo   FYS - Actualizacion del dashboard
echo ================================================
echo   (los archivos nuevos ya deben estar en sus
echo    carpetas Facturas\Pagos_procesados por mes)
echo.

echo [1/4] Respaldo de data\ ...
"%PY%" src\backup_data.py
if errorlevel 1 goto fallo_respaldo

echo.
echo [2/4] Pipeline (solo procesa archivos nuevos)...
"%PY%" src\run_pipeline.py
if errorlevel 1 goto fallo_pipeline

echo.
echo [3/4] Chequeo de calidad...
"%PY%" src\check_corrida.py
set "CHECK_RC=%errorlevel%"

echo.
echo [4/4] Registro en git...
"%PY%" src\git_commit_corrida.py --check %CHECK_RC%

echo.
if not "%CHECK_RC%"=="0" (
    echo ================================================
    echo   ATENCION: el chequeo detecto problemas.
    echo   El estado quedo registrado en git igualmente,
    echo   pero revisa los mensajes de arriba.
    echo ================================================
) else (
    echo V Corrida completa y saludable. Dashboard actualizado:
    echo   %~dp0dashboard\index.html
)
echo.
pause
exit /b 0

:fallo_pipeline
echo.
echo ==================================================
echo   ? El pipeline fallo. NO se registro en git.
echo   Los datos anteriores siguen en data\ y hay
echo   respaldo en data\backup\. Revisar mensajes arriba.
echo ==================================================
pause
exit /b 1

:fallo_respaldo
echo.
echo ? Fallo el respaldo previo: se aborta para proteger los datos.
pause
exit /b 1

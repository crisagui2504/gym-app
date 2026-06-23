@echo off
chcp 65001 >nul
title Gym Tracker - Dashboard (cerra esta ventana para detener)
setlocal
cd /d "%~dp0python-engine"

echo ============================================
echo            GYM TRACKER - DASHBOARD
echo ============================================
echo.

REM --- Crear entorno virtual la primera vez ---
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual por primera vez...
    py -m venv .venv
    echo [2/3] Instalando dependencias (esto tarda 1-2 min la primera vez)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

REM --- Verificar que las dependencias del dashboard esten instaladas ---
".venv\Scripts\python.exe" -c "import dash, plotly, pandas" 2>nul
if errorlevel 1 (
    echo Instalando dependencias faltantes...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo [3/3] Iniciando dashboard...
echo.
echo  El navegador se abrira solo en unos segundos.
echo  URL: http://127.0.0.1:8050
echo.
echo  (Para detener: cerra esta ventana)
echo ============================================

REM --- Abrir el navegador cuando el servidor este listo ---
start "" cmd /c "timeout /t 6 >nul & start http://127.0.0.1:8050"

REM --- Lanzar el dashboard (bloquea hasta cerrar) ---
".venv\Scripts\python.exe" dashboard.py

pause

@echo off
chcp 65001 >nul
title Gym Tracker - Dashboard
cd /d "%~dp0python-engine"

echo ============================================
echo            GYM TRACKER - DASHBOARD
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" goto setup
goto checkdeps

:setup
echo Creando entorno virtual por primera vez...
py -m venv .venv
if errorlevel 1 goto nopython
echo Instalando dependencias, tarda 1-2 minutos la primera vez...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
goto run

:checkdeps
".venv\Scripts\python.exe" -c "import dash, plotly, pandas" 2>nul
if errorlevel 1 goto instalar
goto run

:instalar
echo Instalando dependencias faltantes...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
goto run

:run
echo Iniciando dashboard...
echo.
echo  El navegador se abrira solo en unos segundos.
echo  Si no, entra a:  http://127.0.0.1:8050
echo.
echo  Para detener: cerra esta ventana.
echo ============================================
echo.
".venv\Scripts\python.exe" dashboard.py
echo.
echo El dashboard se detuvo.
pause
goto :eof

:nopython
echo.
echo ERROR: no se encontro Python.
echo Instala Python 3.10+ desde python.org y marca "Add Python to PATH".
echo.
pause
goto :eof

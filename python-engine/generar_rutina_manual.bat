@echo off
REM Generar la rutina A MANO, para cuando ni la VM (domingo 22:00) ni el
REM respaldo del PC (domingo 23:30) estaban encendidos. Doble clic y listo.
REM   - En domingo genera la semana que empieza manana (lunes).
REM   - Cualquier otro dia genera la semana en curso.
REM Usa la misma logica que los servidores (respaldo_semanal.py): trae la config
REM de la VM si responde y sube el plan a InfinityFree.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo.
echo  ==============================================
echo   GymTracker - generar la rutina de la semana
echo  ==============================================
echo.
echo   1) Generar solo si falta                       (lo normal)
echo   2) Regenerar aunque ya este subida
echo      (p.ej. registraste el entreno del domingo despues de las 22:00)
echo.
choice /c 12 /n /m "  Elige 1 o 2: "
if errorlevel 2 (set "ARG=--forzar") else (set "ARG=")
echo.

".venv\Scripts\python.exe" respaldo_semanal.py %ARG%
if errorlevel 1 (
    echo.
    echo   ALGO FALLO. Revisa respaldo.log y motor.log en esta carpeta.
) else (
    echo.
    echo   LISTO. Abre la app para ver la rutina.
)
echo.
pause

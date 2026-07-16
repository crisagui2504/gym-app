@echo off
REM Lanzador del motor semanal (para el Programador de tareas de Windows).
REM Se situa en su propia carpeta (python-engine) para encontrar .env / historial.csv,
REM y corre motor_semanal.py con el Python del entorno virtual.
cd /d "%~dp0"
".venv\Scripts\python.exe" motor_semanal.py

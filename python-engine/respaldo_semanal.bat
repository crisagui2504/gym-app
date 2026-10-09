@echo off
REM Respaldo del motor semanal (Programador de tareas de Windows, lunes 09:00).
REM Si la VM ya subio la rutina de la semana no hace nada; si no, la genera aqui.
cd /d "%~dp0"
".venv\Scripts\python.exe" respaldo_semanal.py

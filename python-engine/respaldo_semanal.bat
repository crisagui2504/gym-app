@echo off
REM Respaldo del motor semanal (Programador de tareas de Windows, domingo 23:30;
REM si el PC estaba apagado, corre en cuanto se enciende).
REM Si la rutina de la semana ya esta subida no hace nada; si no, la genera aqui.
cd /d "%~dp0"
".venv\Scripts\python.exe" respaldo_semanal.py

@echo off
chcp 65001 >nul
title GymTracker - Nuevo usuario
REM Asistente para darle GymTracker a otra persona. Guia: docs\NUEVO_USUARIO.md
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servidor\nuevo_usuario.ps1"

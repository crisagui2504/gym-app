@echo off
chcp 65001 >nul
title Construir Gym Tracker para subir
cd /d "%~dp0app"

echo ============================================
echo   Compilando la app Angular para subir...
echo ============================================
call npx ng build
if errorlevel 1 goto error

cd /d "%~dp0"
if exist "deploy" rmdir /s /q "deploy"
mkdir "deploy"
xcopy /e /i /y "app\dist\gym-rutinas\browser\*" "deploy\" >nul

echo.
echo ============================================
echo   LISTO.
echo ============================================
echo  Subi por FTP a tu htdocs el CONTENIDO de:
echo    %~dp0deploy
echo.
echo  - Sobrescribi index.html, main, polyfills y styles.
echo  - Borra del servidor los main-*.js / styles-*.css VIEJOS.
echo  - NO toques la carpeta  api/  (el backend PHP).
echo ============================================
pause
goto :eof

:error
echo.
echo ERROR al compilar. Revisa el mensaje de arriba.
pause

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
REM .htaccess: lo que no existe va a index.html (evita los 404 que InfinityFree castiga)
copy /y "infinityfree\.htaccess" "deploy\" >nul
REM API PHP completa, SIN config.php: las contrasenas del servidor nunca se pisan
mkdir "deploy\api"
xcopy /y "infinityfree\api\*.php" "deploy\api\" /exclude:%~dp0servidor\no_subir.txt >nul

echo.
echo ============================================
echo   LISTO.
echo ============================================
echo  Subi por FTP a tu htdocs TODA la carpeta (su contenido):
echo    %~dp0deploy
echo.
echo  - Trae la app, el .htaccess y la API (api\) sin config.php.
echo  - Borra del servidor los main-*.js / styles-*.css VIEJOS.
echo ============================================
pause
goto :eof

:error
echo.
echo ERROR al compilar. Revisa el mensaje de arriba.
pause

@echo off
chcp 65001 >nul
echo Creando acceso directo "Gym Tracker" en el escritorio...

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Gym Tracker.lnk'); ^
   $lnk.TargetPath = '%~dp0GymTracker (sin consola).vbs'; ^
   $lnk.WorkingDirectory = '%~dp0'; ^
   $lnk.IconLocation = '%SystemRoot%\System32\shell32.dll,137'; ^
   $lnk.Description = 'Abrir el dashboard de Gym Tracker'; ^
   $lnk.Save()"

echo.
echo Listo. Ya tenes el icono "Gym Tracker" en tu escritorio.
echo Hace doble clic ahi para abrir el dashboard cuando quieras.
echo.
pause

# Ejecuta el motor algoritmico local.
# Doble clic NO sirve: clic derecho -> "Ejecutar con PowerShell"
# o desde una terminal:  ./run.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\planificar.py"
Write-Host ""
Write-Host "Listo. Vuelve a la app Angular -> Ajustes -> Subir JSON si hace falta." -ForegroundColor Green
Read-Host "Pulsa Enter para cerrar"

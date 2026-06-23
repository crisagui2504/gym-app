# Lanza el dashboard de Gym Tracker en el navegador.
# Ejecutar desde python-engine/:  .\run_dashboard.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$venv = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    . $venv
} else {
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    py -m venv .venv
    . $venv
    pip install -r requirements.txt
}

# Instalar dependencias si faltan
python -c "import dash, plotly" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Abrir navegador y lanzar
Start-Process "http://127.0.0.1:8050"
python dashboard.py

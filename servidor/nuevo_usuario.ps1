# Asistente para darle GymTracker a OTRA persona (su propia copia).
# Lo abre "Nuevo usuario.bat". Guia completa: docs/NUEVO_USUARIO.md
#
# Hace, en orden, y pausando cuando te toca hacer algo en una pagina web:
#   1. Pide los datos de su InfinityFree y genera su config.php y su token.
#   2. La agrega a instancias/instancias.json.
#   3. Te dice que secretos poner en GitHub (y abre la pagina).
#   4. Sube el cambio a GitHub y espera a que su app quede publicada.
#   5. Te pide subir su config.php a su InfinityFree.
#   6. Instala su motor y su dashboard en la VM.
# Lo que tu ya tienes no se toca. Si algo falla, vuelve a ejecutarlo: retoma.

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

$Repo = 'crisagui2504/gym-app'
$Vm = 'azureuser@20.150.209.104'
$ClaveSsh = Join-Path $HOME '.ssh\id_gymvm'
$DominioVm = '20-150-209-104.sslip.io'
$Lista = Join-Path $Raiz 'instancias\instancias.json'

function Titulo($texto) {
    Write-Host ''
    Write-Host ('=' * 64) -ForegroundColor DarkGray
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host ('=' * 64) -ForegroundColor DarkGray
}
function Esperar($texto) {
    Write-Host ''
    Read-Host "$texto  (presiona Enter para seguir)" | Out-Null
}
function Fallar($texto) {
    Write-Host ''
    Write-Host "ERROR: $texto" -ForegroundColor Red
    Read-Host 'Presiona Enter para cerrar' | Out-Null
    exit 1
}
function Pedir($pregunta, $ejemplo) {
    while ($true) {
        $r = (Read-Host "$pregunta (ej. $ejemplo)").Trim()
        if ($r) { return $r }
        Write-Host '  No puede ir vacio.' -ForegroundColor Yellow
    }
}

Titulo 'Nuevo usuario de GymTracker'
Write-Host 'Antes de seguir debes haber hecho el PASO 1 de docs\NUEVO_USUARIO.md:'
Write-Host '  - una cuenta de hosting en InfinityFree para esa persona,'
Write-Host '  - su base de datos MySQL creada,'
Write-Host '  - y el archivo infinityfree\schema.sql importado en phpMyAdmin.'
Write-Host ''
Write-Host 'Ten a la mano su panel de InfinityFree (datos de MySQL y de FTP).'
Esperar 'Si ya lo hiciste'

foreach ($cmd in 'git', 'ssh') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Fallar "no encuentro '$cmd' en este PC." }
}
if (-not (Test-Path $ClaveSsh)) { Fallar "no encuentro la llave de la VM en $ClaveSsh" }

# ---------------------------------------------------------------- 1. datos
Titulo '1/6  Datos de la persona'
while ($true) {
    $nombre = (Pedir 'Nombre corto, en minusculas y sin acentos' 'ana').ToLower()
    if ($nombre -match '^[a-z][a-z0-9]{1,14}$' -and $nombre -ne 'gym') { break }
    Write-Host '  Solo letras minusculas y numeros, empezando con letra, 2 a 15 caracteres.' -ForegroundColor Yellow
}
$clave = $nombre.ToUpper()
$carpeta = Join-Path $Raiz "instancias\$nombre"
$archivoDatos = Join-Path $carpeta 'datos.json'
New-Item -ItemType Directory -Force $carpeta | Out-Null

$previo = $null
if (Test-Path $archivoDatos) {
    $previo = Get-Content $archivoDatos -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "Ya existe '$nombre' en este PC: se reutilizan su token y sus datos." -ForegroundColor Green
}

if ($previo) {
    $sitio = $previo.sitio; $ftpUsuario = $previo.ftp_usuario; $token = $previo.token
} else {
    $sitio = Pedir 'Direccion de SU sitio en InfinityFree' 'ana-gym.infinityfreeapp.com'
    $sitio = ($sitio -replace '^https?://', '' -replace '/api/?$', '' -replace '/+$', '').ToLower()
    Write-Host ''
    Write-Host 'Datos de MySQL (panel de InfinityFree -> MySQL Databases):'
    $dbHost = Pedir '  MySQL Host Name' 'sql123.infinityfree.com'
    $dbNombre = Pedir '  MySQL DB Name' 'if0_12345678_gym'
    $dbUsuario = Pedir '  MySQL User Name' 'if0_12345678'
    $seguro = Read-Host '  MySQL Password (no se ve al escribir)' -AsSecureString
    $dbPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro))
    if (-not $dbPass) { Fallar 'la contrasena de MySQL no puede ir vacia.' }
    Write-Host ''
    $ftpUsuario = Pedir 'Usuario FTP (panel -> FTP Details, empieza con if0_)' 'if0_12345678'

    # token: 48 caracteres hexadecimales al azar (solo 0-9 a-f: nada que escapar)
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = -join ($bytes | ForEach-Object { $_.ToString('x2') })

    $php = @"
<?php
// config.php de $nombre (generado por "Nuevo usuario.bat").
// Va en htdocs/api/ de SU sitio de InfinityFree. NUNCA en GitHub.
declare(strict_types=1);

const DB_HOST = '$dbHost';
const DB_NAME = '$dbNombre';
const DB_USER = '$dbUsuario';
const DB_PASS = '$($dbPass.Replace('\', '\\').Replace("'", "\'"))';

const API_TOKEN = '$token';

const ALLOWED_ORIGIN = '*';
"@
    [IO.File]::WriteAllText((Join-Path $carpeta 'config.php'), $php, (New-Object Text.UTF8Encoding $false))
    [ordered]@{ nombre = $nombre; sitio = $sitio; ftp_usuario = $ftpUsuario; token = $token } |
        ConvertTo-Json | Set-Content $archivoDatos -Encoding UTF8
    Write-Host ''
    Write-Host "Guardado en $carpeta (solo en este PC, git lo ignora)." -ForegroundColor Green
}
$api = "https://$sitio/api"

# ---------------------------------------------------------------- 2. lista
Titulo '2/6  Agregarla a instancias\instancias.json'
$json = Get-Content $Lista -Raw -Encoding UTF8 | ConvertFrom-Json
$entradas = @($json.instancias | Where-Object { $_ -and $_.nombre -ne $nombre })
$filas = @($entradas | ForEach-Object { '    {{"nombre": "{0}", "clave": "{1}", "api": "{2}"}}' -f $_.nombre, $_.clave, $_.api })
$filas += '    {{"nombre": "{0}", "clave": "{1}", "api": "{2}"}}' -f $nombre, $clave, $api
$texto = "{`n  `"instancias`": [`n" + ($filas -join ",`n") + "`n  ]`n}`n"
[IO.File]::WriteAllText($Lista, $texto, (New-Object Text.UTF8Encoding $false))
Write-Host $texto

# ---------------------------------------------------------------- 3. secretos
Titulo '3/6  Secretos en GitHub'
Write-Host 'Se abre la pagina de GitHub para crear secretos. Crea estos TRES'
Write-Host '(boton "New repository secret", uno por uno: Name y Secret):'
Write-Host ''
Write-Host "  Name: TOKEN_$clave" -ForegroundColor Yellow
Write-Host "  Secret: $token"
Write-Host '        (ya esta copiado: solo pega con Ctrl+V)'
Write-Host ''
Write-Host "  Name: FTP_USUARIO_$clave" -ForegroundColor Yellow
Write-Host "  Secret: $ftpUsuario"
Write-Host ''
Write-Host "  Name: FTP_PASSWORD_$clave" -ForegroundColor Yellow
Write-Host '  Secret: la contrasena de SU cuenta de hosting de InfinityFree'
Write-Host '          (panel -> FTP Details -> FTP Password; tu la pegas, este asistente no la ve)'
Set-Clipboard -Value $token
Start-Process "https://github.com/$Repo/settings/secrets/actions/new"
Esperar 'Cuando hayas creado los 3 secretos'

# ---------------------------------------------------------------- 4. GitHub
Titulo '4/6  Subir a GitHub y publicar su app'
git add -- 'instancias/instancias.json'
git diff --cached --quiet -- 'instancias/instancias.json'
$hayCambio = ($LASTEXITCODE -ne 0)
if ($hayCambio) {
    git commit -q -m "instancias: agregar $nombre" -- 'instancias/instancias.json'
    if ($LASTEXITCODE -ne 0) { Fallar 'git commit fallo.' }
    git push -q origin HEAD
    if ($LASTEXITCODE -ne 0) { Fallar 'git push fallo (revisa tu conexion o tu sesion de GitHub).' }
    $sha = (git rev-parse HEAD).Trim()
    Write-Host 'Subido. GitHub va a probar todo y publicar su app (unos 5 minutos)...'
    $run = $null
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 20
        try {
            $r = Invoke-RestMethod "https://api.github.com/repos/$Repo/actions/runs?head_sha=$sha&per_page=1"
            $run = $r.workflow_runs | Select-Object -First 1
        } catch { $run = $null }
        if ($run -and $run.status -eq 'completed') { break }
        Write-Host '  ...todavia trabajando' -ForegroundColor DarkGray
    }
    if (-not $run -or $run.status -ne 'completed') {
        Write-Host "No termino a tiempo. Revisalo en https://github.com/$Repo/actions" -ForegroundColor Yellow
    } else {
        $jobs = (Invoke-RestMethod "https://api.github.com/repos/$Repo/actions/runs/$($run.id)/jobs").jobs
        $suyo = $jobs | Where-Object { $_.name -like "*($nombre)*" } | Select-Object -First 1
        if ($suyo -and $suyo.conclusion -eq 'success') {
            Write-Host "Su app ya esta publicada en https://$sitio" -ForegroundColor Green
        } else {
            Write-Host "Algo fallo al publicar su app: $($run.html_url)" -ForegroundColor Red
            Write-Host '(lo mas comun: un secreto con el nombre mal escrito). Corrigelo y vuelve a ejecutar.'
            Esperar 'Si quieres seguir de todas formas'
        }
    }
} else {
    Write-Host 'Ya estaba en la lista: no hay nada nuevo que subir.'
    Write-Host "Si su app no esta publicada: GitHub -> Actions -> 'Probar y desplegar' -> Run workflow."
}

# ---------------------------------------------------------------- 5. config.php
Titulo '5/6  Subir SU config.php'
Write-Host 'Se abre la carpeta con su config.php. En SU panel de InfinityFree:'
Write-Host '  1. Online File Manager -> entra a htdocs -> entra a api'
Write-Host '  2. Upload -> elige el config.php de esa carpeta'
Write-Host '  (si no existe la carpeta api es que el paso 4 no publico su app: revisalo)'
Invoke-Item $carpeta
Start-Process 'https://dash.infinityfree.com'
Esperar 'Cuando config.php ya este en htdocs/api'

# ---------------------------------------------------------------- 6. VM
Titulo '6/6  Su motor y su dashboard en la VM'
Write-Host 'Conectando a la VM (la primera vez tarda 3-5 minutos)...'
$remoto = "cd ~/gym && git pull -q --ff-only && bash servidor/nueva_instancia.sh $nombre '$api' '$token'"
ssh -i $ClaveSsh -o BatchMode=yes -o ConnectTimeout=20 $Vm $remoto
if ($LASTEXITCODE -ne 0) { Fallar 'la instalacion en la VM no termino. Lee el mensaje de arriba y vuelve a ejecutar este asistente.' }

Titulo "LISTO: $nombre ya tiene GymTracker"
Write-Host "  Su app:        https://$sitio"
Write-Host "  Su dashboard:  https://$nombre.$DominioVm"
Write-Host ''
Write-Host 'Mandale esos dos enlaces. En su iPhone: abrir la app en Safari ->'
Write-Host 'Compartir -> Agregar a inicio. En su dashboard, pestana Configuracion,'
Write-Host 'elige su enfoque, split, dias de deporte y duracion, y presiona'
Write-Host '"Generar y guardar plan".'
Read-Host 'Presiona Enter para cerrar' | Out-Null

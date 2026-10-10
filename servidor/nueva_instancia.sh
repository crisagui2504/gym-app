#!/usr/bin/env bash
# Crea (o actualiza) la copia de GymTracker de OTRA persona en esta VM.
# Guia completa: docs/NUEVO_USUARIO.md. Normalmente lo ejecuta "Nuevo usuario.bat"
# desde el PC; a mano seria:
#
#   bash ~/gym/servidor/nueva_instancia.sh NOMBRE URL_DE_SU_API SU_TOKEN
#   bash ~/gym/servidor/nueva_instancia.sh ana https://ana-gym.infinityfreeapp.com/api 3f9a...
#
# Que hace (sin tocar NADA tuyo: tu carpeta ~/gym, tus servicios y tus datos):
#   - clona el repo en ~/gym-NOMBRE con su propio .env y config_usuario.json;
#   - crea sus servicios: gymtracker-NOMBRE-{motor,datos,recordatorio,dashboard};
#   - su dashboard queda en https://NOMBRE.<tu dominio sslip.io>;
#   - genera su primera rutina.
# Volver a ejecutarlo es seguro: actualiza en lugar de duplicar.
set -euo pipefail
{
N="${1:-}"
API="${2:-}"
TOKEN="${3:-}"
BASE="$HOME/gym"
DIR="$HOME/gym-$N"
REPO="https://github.com/crisagui2504/gym-app.git"
DOMINIO="$N.${DOMINIO:-20-150-209-104.sslip.io}"

if ! [[ "$N" =~ ^[a-z][a-z0-9]{1,14}$ ]]; then
    echo "ERROR: el nombre va en minusculas, sin espacios ni acentos, 2 a 15 letras (ej. ana, luis2)."
    exit 1
fi
test -d "$BASE/.git" || { echo "ERROR: no encuentro tu instalacion principal en $BASE"; exit 1; }

echo "==> memoria de respaldo"
# la VM tiene ~830 MB de RAM; cada dashboard usa ~150 MB. 1 GB de swap evita que
# el sistema mate procesos si se juntan el motor y dos dashboards a la vez.
if ! swapon --show | grep -q .; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile >/dev/null
    sudo swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    echo "    swap de 1 GB creado"
else
    echo "    ya habia swap"
fi

echo "==> codigo en $DIR"
if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull --ff-only -q
else
    git clone -q "$REPO" "$DIR"
fi
cd "$DIR/python-engine"

echo "==> entorno de Python (la primera vez tarda unos minutos)"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt gunicorn

echo "==> sus datos (.env y config)"
if [ -n "$API" ] && [ -n "$TOKEN" ]; then
    LUNES="$(TZ=America/Mexico_City .venv/bin/python -c 'import planificar; print(planificar.lunes_objetivo())' 2>/dev/null | tail -1)"
    if [ -f .env ] && grep -q '^MES_INICIO=' .env; then
        LUNES="$(grep '^MES_INICIO=' .env | cut -d= -f2)"   # al actualizar no se reinicia su mesociclo
    fi
    ( umask 077
      {
        echo "# GymTracker de $N (generado por nueva_instancia.sh)"
        echo "API_BASE_URL=$API"
        echo "API_TOKEN=$TOKEN"
        [ -n "$LUNES" ] && echo "MES_INICIO=$LUNES"   # su S1 empieza esta semana
        # las claves de los avisos push se comparten con la instalacion principal
        grep -E '^VAPID_(PRIVADA|PUBLICA)=' "$BASE/python-engine/.env" || true
      } > .env )
fi
test -f .env || { echo "ERROR: falta $DIR/python-engine/.env (pasa la URL de su API y su token)"; exit 1; }
if [ ! -f config_usuario.json ]; then
    # config inicial neutra (recomposicion, upper/lower, 90 min); la persona la
    # cambia en SU dashboard, pestana Configuracion
    .venv/bin/python -c 'from config_usuario import cargar_config, guardar_config; guardar_config(cargar_config())'
fi

echo "==> puerto de su dashboard"
sudo mkdir -p /etc/caddy/instancias
SITIO="/etc/caddy/instancias/$N.caddy"
if [ -f "$SITIO" ]; then
    PUERTO="$(grep -o '127.0.0.1:[0-9]*' "$SITIO" | cut -d: -f2)"
else
    PUERTO=8051
    while cat /etc/caddy/instancias/*.caddy 2>/dev/null | grep -q "127.0.0.1:$PUERTO\$"; do
        PUERTO=$((PUERTO + 1))
    done
fi
echo "    $PUERTO"

echo "==> servicios (gymtracker-$N-*)"
for f in "$DIR"/servidor/gymtracker-*.service "$DIR"/servidor/gymtracker-*.timer; do
    b="$(basename "$f")"
    nuevo="${b/gymtracker-/gymtracker-$N-}"
    sed -e "s#$BASE/#$DIR/#g" \
        -e "s#127.0.0.1:8050#127.0.0.1:$PUERTO#g" \
        -e "s#GymTracker - #GymTracker [$N] - #" \
        -e "s#22:00:00#22:15:00#" \
        -e "s#^Environment=TZ=America/Mexico_City#Environment=TZ=America/Mexico_City\nEnvironment=GYM_INSTANCIA=$N#" \
        "$f" | sudo tee "/etc/systemd/system/$nuevo" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now "gymtracker-$N-motor.timer" "gymtracker-$N-datos.timer" "gymtracker-$N-recordatorio.timer"
sudo systemctl enable "gymtracker-$N-dashboard.service" >/dev/null 2>&1
sudo systemctl restart "gymtracker-$N-dashboard.service"

echo "==> HTTPS para https://$DOMINIO"
printf '%s {\n\tencode gzip\n\treverse_proxy 127.0.0.1:%s\n}\n' "$DOMINIO" "$PUERTO" | sudo tee "$SITIO" >/dev/null
if ! grep -q '/etc/caddy/instancias/' /etc/caddy/Caddyfile; then
    echo 'import /etc/caddy/instancias/*.caddy' | sudo tee -a /etc/caddy/Caddyfile >/dev/null
fi
sudo caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 \
    || { echo "ERROR: la configuracion de Caddy no es valida; no se recarga (tu dashboard sigue igual)"; exit 1; }
sudo systemctl reload caddy

echo "==> conexion con su InfinityFree y primera rutina"
if TZ=America/Mexico_City GYM_INSTANCIA="$N" .venv/bin/python exportar_local.py >/tmp/gym_$N.log 2>&1; then
    echo "    conexion OK"
    TZ=America/Mexico_City GYM_INSTANCIA="$N" .venv/bin/python respaldo_semanal.py >>/tmp/gym_$N.log 2>&1 \
        && echo "    rutina de la semana: lista" \
        || echo "    AVISO: no se pudo generar la rutina (ver /tmp/gym_$N.log). Se reintenta sola el domingo."
else
    tail -5 /tmp/gym_$N.log
    echo
    echo "    AVISO: no pude conectar con $API"
    echo "    Revisa: 1) que subiste config.php a htdocs/api/  2) que la base de datos tiene las tablas"
    echo "    (schema.sql)  3) que el token es el mismo. Luego vuelve a ejecutar este script."
fi

echo
echo "LISTO: $N"
echo "  Su dashboard:  https://$DOMINIO   (el certificado HTTPS puede tardar 1 minuto la primera vez)"
echo "  Sus servicios: systemctl list-timers 'gymtracker-$N-*'"
exit 0
}

#!/usr/bin/env bash
# Instala o ACTUALIZA GymTracker en la VM (Ubuntu). Idempotente: se puede volver
# a ejecutar para desplegar cambios. Requisitos previos (los hace desplegar.sh
# desde el PC): ~/gym/python-engine/.env y config_usuario.json ya copiados.
#
#   bash ~/gym/servidor/instalar_vm.sh
#
set -euo pipefail

# Todo el script va entre llaves: bash lo lee COMPLETO antes de ejecutar. Sin
# esto, el "git pull" de mas abajo reescribia este mismo archivo a mitad de
# ejecucion y bash seguia leyendo lineas de la version vieja (asi quedo sin
# activar el timer del recordatorio en el primer despliegue).
{
REPO="https://github.com/crisagui2504/gym-app.git"
DIR="$HOME/gym"
DOMINIO="${DOMINIO:-20-150-209-104.sslip.io}"

echo "==> paquetes del sistema"
# un repo de terceros caido no debe tumbar el despliegue: el de Caddy
# (cloudsmith) empezo a responder "402 Payment Required" y con set -e el
# instalador moria aqui sin pasar las pruebas ni reiniciar el dashboard
sudo apt-get update -y -qq || echo "AVISO: apt-get update con errores (repo de terceros); se sigue"
sudo apt-get install -y -qq python3 python3-venv python3-pip git curl \
    debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null

echo "==> Caddy (proxy HTTPS) desde su repositorio oficial"
if ! command -v caddy >/dev/null 2>&1; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    sudo apt-get update -y -qq || true
    sudo apt-get install -y -qq caddy >/dev/null
fi

echo "==> codigo"
if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull --ff-only
else
    # el clon no trae .env ni config_usuario.json (estan en .gitignore): conservarlos
    TMP="$(mktemp -d)"
    cp -a "$DIR/python-engine/.env" "$DIR/python-engine/config_usuario.json" "$TMP/" 2>/dev/null || true
    rm -rf "$DIR"
    git clone -q "$REPO" "$DIR"
    cp -a "$TMP"/. "$DIR/python-engine/" 2>/dev/null || true
    rm -rf "$TMP"
fi

cd "$DIR/python-engine"
test -f .env || { echo "ERROR: falta $DIR/python-engine/.env (lo copia desplegar.sh)"; exit 1; }

echo "==> entorno de Python"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt gunicorn

echo "==> pruebas antes de activar nada"
.venv/bin/python tests/test_motor.py >/tmp/gym_test.log 2>&1 \
    || { tail -20 /tmp/gym_test.log; echo "ERROR: las pruebas fallan, no se despliega"; exit 1; }

echo "==> servicios systemd"
sudo cp "$DIR"/servidor/gymtracker-*.service "$DIR"/servidor/gymtracker-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gymtracker-motor.timer gymtracker-datos.timer gymtracker-recordatorio.timer
sudo systemctl enable gymtracker-dashboard.service
sudo systemctl restart gymtracker-dashboard.service
sudo systemctl start gymtracker-datos.service || true   # historial al dia ya

echo "==> Caddy ($DOMINIO)"
sed "s/__DOMINIO__/$DOMINIO/" "$DIR/servidor/Caddyfile" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl enable caddy >/dev/null 2>&1
sudo systemctl restart caddy

echo
echo "LISTO. Dashboard: https://$DOMINIO"
systemctl list-timers 'gymtracker-*' --no-pager
exit 0
}

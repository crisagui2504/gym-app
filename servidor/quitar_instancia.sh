#!/usr/bin/env bash
# Apaga la copia de GymTracker de otra persona en esta VM (la contraria de
# nueva_instancia.sh). NO borra sus datos: su carpeta ~/gym-NOMBRE se queda
# (historial, respaldos, config). Lo que esta en SU InfinityFree tampoco se toca.
#
#   bash ~/gym/servidor/quitar_instancia.sh NOMBRE
#
set -euo pipefail
N="${1:-}"
[[ "$N" =~ ^[a-z][a-z0-9]{1,14}$ ]] || { echo "ERROR: nombre no valido"; exit 1; }

echo "==> apagando gymtracker-$N-*"
for u in motor.timer datos.timer recordatorio.timer dashboard.service; do
    sudo systemctl disable --now "gymtracker-$N-$u" 2>/dev/null || true
done
sudo rm -f /etc/systemd/system/gymtracker-"$N"-*.service /etc/systemd/system/gymtracker-"$N"-*.timer
sudo systemctl daemon-reload

echo "==> quitando su direccion del dashboard"
sudo rm -f "/etc/caddy/instancias/$N.caddy"
sudo systemctl reload caddy

echo
echo "LISTO: $N apagado. Sus datos siguen en $HOME/gym-$N"
echo "Si tambien quieres borrarlos (no se puede deshacer):  rm -rf $HOME/gym-$N"

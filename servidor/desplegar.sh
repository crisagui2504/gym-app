#!/usr/bin/env bash
# Despliega o actualiza la VM DESDE EL PC (Git Bash). Copia por SSH lo que NO
# esta en git (.env con el token, config_usuario.json) y ejecuta el instalador.
#
#   bash servidor/desplegar.sh
#
set -euo pipefail
VM="${GYM_VM_HOST:-azureuser@20.150.209.104}"
KEY="$HOME/.ssh/id_gymvm"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)
SCP=(scp -q -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15)
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> secretos y config (por SSH, no por git)"
"${SSH[@]}" "$VM" 'mkdir -p ~/gym/python-engine'
"${SCP[@]}" "$RAIZ/python-engine/.env" "$RAIZ/python-engine/config_usuario.json" "$VM:~/gym/python-engine/"
"${SSH[@]}" "$VM" 'chmod 600 ~/gym/python-engine/.env'

echo "==> instalador"
"${SCP[@]}" "$RAIZ/servidor/instalar_vm.sh" "$VM:~/instalar_vm.sh"
"${SSH[@]}" "$VM" "sed -i 's/\r\$//' ~/instalar_vm.sh && bash ~/instalar_vm.sh"

#!/usr/bin/env bash
# Arma deploy-nutri/ con lo que se sube a htdocs/ de la app de NUTRICION
# (crisrodrigo.infinityfree.io): la app compilada (proyecto "nutri"), el
# .htaccess y SOLO los endpoints de nutricion y peso de infinityfree/api (los
# mismos archivos que GymTracker: una sola copia del codigo).
#
# config.php: a diferencia de GymTracker, aqui lo arma el CI con los secretos
# (NUTRI_PASSWORD, NUTRI_TOKEN) para que no haya que subirlo a mano. Sin esos
# secretos no se genera, y el workflow no sube nada.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf deploy-nutri
mkdir -p deploy-nutri/api
cp -r app/dist/nutri/browser/. deploy-nutri/
cp infinityfree/.htaccess deploy-nutri/

API=(bootstrap.php
     nutricion_tabla.php guardar_proteina.php get_nutricion.php guardar_meta_nutricion.php
     menu_tabla.php guardar_menu.php get_menu.php
     no_me_gusta_tabla.php guardar_no_me_gusta.php get_no_me_gusta.php
     peso_tabla.php guardar_peso.php get_peso.php)
for f in "${API[@]}"; do
    cp "infinityfree/api/$f" deploy-nutri/api/
done

if [ -n "${NUTRI_PASSWORD:-}" ] && [ -n "${NUTRI_TOKEN:-}" ]; then
    # PHP: cadenas entre comillas simples (se escapan \ y ')
    python3 - <<'PY'
import os
def php(v):
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
e = os.environ
lineas = [
    "<?php",
    "// Generado por el CI (servidor/armar_deploy_nutri.sh) con los secretos de GitHub. No editar.",
    "declare(strict_types=1);",
    "",
    f"const DB_HOST = {php(e['NUTRI_DB_HOST'])};",
    f"const DB_NAME = {php(e['NUTRI_DB_NAME'])};",
    f"const DB_USER = {php(e['NUTRI_DB_USER'])};",
    f"const DB_PASS = {php(e['NUTRI_PASSWORD'])};",
    f"const API_TOKEN = {php(e['NUTRI_TOKEN'])};",
    f"const ALLOWED_ORIGIN = {php(e['NUTRI_ORIGEN'])};",
    "",
]
open("deploy-nutri/api/config.php", "w", encoding="utf-8").write("\n".join(lineas))
PY
    echo "config.php generado (sin mostrar valores)"
else
    echo "Sin NUTRI_PASSWORD/NUTRI_TOKEN: no se genera config.php"
fi
ls deploy-nutri deploy-nutri/api

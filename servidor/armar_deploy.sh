#!/usr/bin/env bash
# Arma deploy/ con lo que se sube a htdocs/ de InfinityFree: la app compilada,
# el .htaccess y la API SIN config.php (las contrasenas viven solo en el
# servidor y nunca se pisan). Lo usa el CI para ti y para cada persona de
# instancias/instancias.json; es lo mismo que hace "Construir app para subir.bat".
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf deploy
mkdir -p deploy/api
cp -r app/dist/gym-rutinas/browser/. deploy/
cp infinityfree/.htaccess deploy/
for f in infinityfree/api/*.php; do
    case "$(basename "$f")" in
        config.php|config.example.php) ;;
        *) cp "$f" deploy/api/ ;;
    esac
done
test ! -e deploy/api/config.php
ls -la deploy deploy/api

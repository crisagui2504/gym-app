"""Descarga el historial de entrenos y lo guarda como historial.csv local.
Ese archivo es la fuente de datos del dashboard.
Reutiliza el solucionador de antibot de planificar.py.

Ademas guarda una copia fechada en backups/ (una por dia, se conservan las
ultimas 30): el historial vive en un hosting gratuito, asi que estas copias
locales son el verdadero respaldo de tus datos.
"""
from __future__ import annotations

import pathlib
from datetime import date

from planificar import api_config, sesion_infinityfree

# Cabeceras del CSV (esquema estable aunque no haya datos aun).
CABECERAS = (
    "id,fecha_entreno,ejercicio,tecnica,numero_serie,peso_kg,reps_hechas,rpe,"
    "tonelaje_serie,semana_inicio,dia_semana,nombre_dia,bloque,series_objetivo,"
    "reps_min,reps_max,peso_sugerido\n"
)

BACKUPS_MAX = 30


def _respaldar(texto: str) -> None:
    """Copia fechada en backups/ (sobrescribe la del dia; borra las mas viejas)."""
    carpeta = pathlib.Path(__file__).resolve().parent / "backups"
    carpeta.mkdir(exist_ok=True)
    (carpeta / f"historial-{date.today().isoformat()}.csv").write_text(texto, encoding="utf-8")
    viejos = sorted(carpeta.glob("historial-*.csv"))[:-BACKUPS_MAX]
    for v in viejos:
        v.unlink(missing_ok=True)


def main() -> None:
    base_url, token = api_config()
    sesion = sesion_infinityfree(base_url)
    respuesta = sesion.get(f"{base_url}/exportar_csv.php", params={"token": token}, timeout=30)
    respuesta.raise_for_status()

    texto = respuesta.text if respuesta.text.strip() else CABECERAS
    destino = pathlib.Path(__file__).resolve().parent / "historial.csv"
    destino.write_text(texto, encoding="utf-8")
    _respaldar(texto)
    filas = max(0, texto.strip().count("\n"))
    print(f"historial.csv actualizado: {destino} ({filas} filas de datos) + backup fechado")


if __name__ == "__main__":
    main()

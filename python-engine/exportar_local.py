"""Descarga el historial de entrenos y lo guarda como historial.csv local.
Ese archivo es la fuente de datos para Power BI (Sprint 5).
Reutiliza el solucionador de antibot de planificar.py.
"""
from __future__ import annotations

import pathlib

from planificar import api_config, sesion_infinityfree

# Cabeceras del CSV (para que Power BI tenga esquema aunque no haya datos aun).
CABECERAS = (
    "id,fecha_entreno,ejercicio,tecnica,numero_serie,peso_kg,reps_hechas,rpe,"
    "tonelaje_serie,semana_inicio,dia_semana,nombre_dia,bloque,series_objetivo,"
    "reps_min,reps_max,peso_sugerido\n"
)


def main() -> None:
    base_url, token = api_config()
    sesion = sesion_infinityfree(base_url)
    respuesta = sesion.get(f"{base_url}/exportar_csv.php", params={"token": token}, timeout=30)
    respuesta.raise_for_status()

    texto = respuesta.text if respuesta.text.strip() else CABECERAS
    destino = pathlib.Path(__file__).resolve().parent / "historial.csv"
    destino.write_text(texto, encoding="utf-8")
    filas = max(0, texto.strip().count("\n"))
    print(f"historial.csv actualizado: {destino} ({filas} filas de datos)")


if __name__ == "__main__":
    main()

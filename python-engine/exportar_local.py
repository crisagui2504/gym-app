"""Descarga el historial de entrenos y lo guarda como historial.csv local.
Ese archivo es la fuente de datos del dashboard.
Reutiliza el solucionador de antibot de planificar.py.

Ademas guarda una copia fechada en backups/ (una por dia, se conservan las
ultimas 30): el historial vive en un hosting gratuito, asi que estas copias
locales son el verdadero respaldo de tus datos.

Tambien baja el peso corporal (MySQL, tabla peso_corporal) a peso_corporal.csv,
con su propio backup fechado (backups/peso-AAAA-MM-DD.csv).
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
AQUI = pathlib.Path(__file__).resolve().parent


def _respaldar(texto: str, prefijo: str = "historial", raiz: pathlib.Path = AQUI) -> None:
    """Copia fechada en backups/ (sobrescribe la del dia; borra las mas viejas)."""
    carpeta = raiz / "backups"
    carpeta.mkdir(exist_ok=True)
    (carpeta / f"{prefijo}-{date.today().isoformat()}.csv").write_text(texto, encoding="utf-8")
    viejos = sorted(carpeta.glob(f"{prefijo}-*.csv"))[:-BACKUPS_MAX]
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

    # encuesta de la sesion: el dashboard la lee de aqui para mostrar el MISMO
    # plan que el motor sube (sin pedirla a InfinityFree en cada visita)
    import feedback
    fb = feedback.descargar_feedback(sesion, base_url, token, dias=120)
    fb.to_csv(destino.parent / feedback.CSV_FEEDBACK, index=False)
    print(f"{feedback.CSV_FEEDBACK} actualizado ({len(fb)} respuestas)")
    import pandas as pd
    prefs = feedback.descargar_preferencias(sesion, base_url, token)
    pd.DataFrame({"original": list(prefs), "reemplazo": list(prefs.values())}).to_csv(
        destino.parent / feedback.CSV_PREFERENCIAS, index=False)
    # proteina registrada en la app (para la pestana Peso corporal del dashboard)
    import nutricion
    nut = nutricion.descargar_nutricion(sesion, base_url, token)
    nut.to_csv(destino.parent / nutricion.CSV_NUTRICION, index=False)
    print(f"{nutricion.CSV_NUTRICION} actualizado ({len(nut)} dias)")
    exportar_peso(sesion, base_url, token)


def exportar_peso(sesion, base_url: str, token: str, raiz: pathlib.Path = AQUI):
    """Peso corporal: la fuente es MySQL (app y dashboard). Lo que solo este en el
    CSV local se sube antes de reescribirlo (la migracion de la primera vez, o un
    envio del dashboard que fallo). Devuelve los pesajes, o None sin servidor."""
    import nutricion
    ruta = raiz / nutricion.CSV_PESO
    dfp, subidos = nutricion.sincronizar_peso(sesion, base_url, token, ruta)
    if dfp is None:
        print(f"{nutricion.CSV_PESO} sin cambios (el servidor no respondio)")
        return None
    _respaldar(ruta.read_text(encoding="utf-8"), "peso", raiz)
    print(f"{nutricion.CSV_PESO} actualizado ({len(dfp)} pesajes, {subidos} subidos del CSV local) + backup fechado")
    # el ultimo pesaje manda (macros y meta de proteina de la app)
    if nutricion.alinear_peso_config(dfp):
        print(f"peso_corporal de tu config -> {dfp['peso'].iloc[-1]:.1f} kg (meta de nutricion resubida)")
    return dfp


if __name__ == "__main__":
    main()

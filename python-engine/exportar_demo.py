"""Datos de DEMOSTRACION para la app y el dashboard (modo demo oculto).

Un atleta virtual (simulador.py) entrena 9 semanas con una config que cubre
TODOS los tipos de dia (torso/pierna, basquet, cardio y descanso); despues el
motor planifica la semana siguiente con ese historial. Asi la demo ensena el
sistema real -pesos, notas del Coach, calibraciones- sin tocar ni un dato tuyo.

Las fechas se guardan como "dias antes del lunes de la semana de demo": la app
y el dashboard las colocan relativas a HOY, asi la demo nunca envejece.

Genera:
  app/src/app/demo.generado.ts        (plan de la semana + historial reciente)
  python-engine/demo_historial.csv    (historial completo para el dashboard)
Uso:  python exportar_demo.py
"""
from __future__ import annotations

import json
import pathlib
from datetime import date, timedelta

import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
DESTINO_TS = AQUI.parent / "app" / "src" / "app" / "demo.generado.ts"
DESTINO_CSV = AQUI / "demo_historial.csv"

CONFIG_DEMO = {
    "enfoque": "recomposicion", "split": "upper_lower", "prioridades": ["hombros"],
    "duracion_min": 75, "peso_corporal": 75,
    "deporte": {"nombre": "Basquetbol", "dias": [2], "minutos": 90},
}
SEMANAS = 9
INICIO = date(2026, 1, 5)          # fijo: la demo es determinista
DIAS_HISTORIAL_APP = 35            # la app solo necesita el ultimo mes


def generar() -> tuple[str, pd.DataFrame]:
    import planificar as pl
    import simulador as sim
    from generador import generar_plan

    # el atleta de la demo es generico: sin TU lista de mancuernas ni tus asistidas
    pl._cfg = lambda: {"peso_corporal": CONFIG_DEMO["peso_corporal"]}
    res = sim.simular(sim.PERFILES["intermedio"], semanas=SEMANAS, semilla=7, config=CONFIG_DEMO,
                      inicio=INICIO, devolver_historial=True)
    hist = res["historial"]
    lunes = INICIO + timedelta(weeks=SEMANAS)
    semana, reingreso, _ = pl.decidir_semana(hist, lunes, INICIO)
    filas = pl.generar_filas(hist, lunes.isoformat(), semana,
                             plan=generar_plan(CONFIG_DEMO, ciclo=SEMANAS // 5),
                             reingreso=reingreso, duracion_min=CONFIG_DEMO["duracion_min"])

    plan: dict[int, list[dict]] = {d: [] for d in range(1, 8)}
    for i, f in enumerate(filas, start=1):
        plan[int(f["dia_semana"])].append({
            "id": 900000 + i, "semana_inicio": "", "dia_semana": int(f["dia_semana"]),
            "nombre_dia": f["nombre_dia"], "bloque": f["bloque"], "orden": int(f["orden"]),
            "ejercicio": f["ejercicio"], "tecnica": f["tecnica"],
            "series_objetivo": float(f["series_objetivo"] or 0),
            "reps_min": f["reps_min"], "reps_max": f["reps_max"], "descanso_seg": f["descanso_seg"],
            "peso_sugerido": f["peso_sugerido"], "notas": f["notas"],
        })

    h = hist.copy()
    h["dias_atras"] = h["fecha_entreno"].map(lambda f: (lunes - f.date()).days)
    recientes = h[h["dias_atras"] <= DIAS_HISTORIAL_APP]
    historial_app = [
        {"dias_atras": int(r.dias_atras), "ejercicio": r.ejercicio, "tecnica": r.tecnica,
         "numero_serie": int(r.numero_serie), "peso_kg": float(r.peso_kg),
         "repeticiones": int(r.reps_hechas), "rpe": int(r.rpe)}
        for r in recientes.itertuples()
    ]
    ts = ("// GENERADO por python-engine/exportar_demo.py (atleta virtual de simulador.py).\n"
          "// Datos de DEMOSTRACION: nada de esto es tuyo. NO editar a mano.\n"
          f"export const DEMO_PLAN: Record<number, any[]> = {json.dumps(plan, ensure_ascii=False)};\n\n"
          f"export const DEMO_HISTORIAL: any[] = {json.dumps(historial_app, ensure_ascii=False)};\n")
    csv = h[["dias_atras", "ejercicio", "tecnica", "numero_serie", "peso_kg", "reps_hechas", "rpe",
             "tonelaje_serie", "bloque"]]
    return ts, csv


def cargar_historial_demo(hoy: date | None = None) -> pd.DataFrame:
    """Historial de la demo con fechas reales: termina el domingo pasado."""
    if not DESTINO_CSV.exists():
        return pd.DataFrame()
    d = pd.read_csv(DESTINO_CSV)
    hoy = hoy or date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    d["fecha_entreno"] = pd.to_datetime([lunes - timedelta(days=int(x)) for x in d["dias_atras"]])
    return d.drop(columns=["dias_atras"])


if __name__ == "__main__":
    ts, csv = generar()
    DESTINO_TS.write_text(ts, encoding="utf-8")
    csv.to_csv(DESTINO_CSV, index=False)
    print(f"{DESTINO_TS.name}: plan de {sum(1 for _ in ts)} bytes | {DESTINO_CSV.name}: {len(csv)} series")

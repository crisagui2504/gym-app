"""Escenarios de DEMOSTRACION con el motor real, para cualquier tipo de entreno.

Para una config cualquiera (enfoque, split, duracion, prioridades, deporte), un
atleta virtual (simulador.py) entrena dos mesociclos con ella y el motor
planifica las 5 semanas del siguiente (S1 base -> S5 deload). Asi la demo
ensena TODO el sistema -los 5 enfoques x 4 splits, cada semana del mesociclo- y
no solo la configuracion del usuario.

Lo usan:
  - la API publica de la demo (dashboard.py, /demo/api/...), que consume la app;
  - el modo demo del dashboard;
  - exportar_demo.py (el respaldo que la app lleva dentro por si la VM no responde).
Nunca lee ni escribe datos reales: corre con config_fija (sin la del usuario).
"""
from __future__ import annotations

import functools
import json
from datetime import date, timedelta

import pandas as pd

import enfoques as enf

SEMANAS_PREVIAS = 10            # dos mesociclos completos de historial
INICIO = date(2026, 1, 5)       # fijo: escenarios deterministas (y cacheables)
DIAS_HISTORIAL_APP = 35
DURACIONES = (60, 75, 90, 120)
PRIORIDADES = tuple(mid for mid, _ in enf.MUSCULOS_PRIORIZABLES)
DEPORTE = {"nombre": "Basquetbol", "dias": [2], "minutos": 90}

NOMBRE_SEMANA = {1: "S1 · Base", 2: "S2 · Rotación", 3: "S3 · Superar S1", 4: "S4 · Pico", 5: "S5 · Deload"}


def opciones() -> dict:
    return {
        "enfoques": [{"id": k, "nombre": v.nombre} for k, v in enf.ENFOQUES.items()],
        "splits": [{"id": k, "nombre": v.nombre} for k, v in enf.SPLITS.items()],
        "duraciones": list(DURACIONES),
        "prioridades": list(PRIORIDADES),
        "semanas": [{"n": n, "nombre": s} for n, s in NOMBRE_SEMANA.items()],
    }


def normalizar(params: dict | None) -> dict:
    """Config de demo valida a partir de lo que llegue (query, cookie...).
    Cualquier valor raro cae al por defecto: es una API publica."""
    p = params or {}
    enfoque = p.get("enfoque") if p.get("enfoque") in enf.ENFOQUES else "recomposicion"
    split = p.get("split") if p.get("split") in enf.SPLITS else "upper_lower"
    try:
        duracion = int(p.get("duracion") or 75)
    except (TypeError, ValueError):
        duracion = 75
    duracion = duracion if duracion in DURACIONES else 75
    prio = p.get("prioridades")
    if prio is None:
        prio = ["hombros"]                      # sin dato: la de por defecto
    if isinstance(prio, str):
        prio = [x for x in prio.split(",") if x]
    prio = [x for x in prio if x in PRIORIDADES][:3]   # lista vacia = sin prioridades
    dep = str(p.get("deporte", "1")).lower() not in ("0", "false", "no", "")
    return {"enfoque": enfoque, "split": split, "duracion_min": duracion, "prioridades": prio,
            "peso_corporal": 75, "deporte": DEPORTE if dep else None}


def clave(cfg: dict) -> str:
    return json.dumps(cfg, sort_keys=True, ensure_ascii=False)


@functools.lru_cache(maxsize=16)
def _escenario(clave_cfg: str) -> dict:
    import planificar as pl
    import simulador as sim
    from generador import generar_plan

    cfg = json.loads(clave_cfg)
    with pl.config_fija({"peso_corporal": cfg["peso_corporal"]}):
        res = sim.simular(sim.PERFILES["intermedio"], semanas=SEMANAS_PREVIAS, semilla=7, config=cfg,
                          inicio=INICIO, devolver_historial=True)
        hist = res["historial"]
        plan = generar_plan(cfg, ciclo=SEMANAS_PREVIAS // 5)
        semanas: dict[int, dict[int, list[dict]]] = {}
        n = 0
        for k in range(1, 6):
            lunes = INICIO + timedelta(weeks=SEMANAS_PREVIAS + k - 1)
            dias: dict[int, list[dict]] = {d: [] for d in range(1, 8)}
            for f in pl.generar_filas(hist, lunes.isoformat(), k, plan=plan, duracion_min=cfg["duracion_min"]):
                n += 1
                dias[int(f["dia_semana"])].append({
                    "id": 900000 + n, "semana_inicio": "", "dia_semana": int(f["dia_semana"]),
                    "nombre_dia": f["nombre_dia"], "bloque": f["bloque"], "orden": int(f["orden"]),
                    "ejercicio": f["ejercicio"], "tecnica": f["tecnica"],
                    "series_objetivo": float(f["series_objetivo"] or 0),
                    "reps_min": f["reps_min"], "reps_max": f["reps_max"], "descanso_seg": f["descanso_seg"],
                    "peso_sugerido": f["peso_sugerido"], "notas": f["notas"],
                })
            semanas[k] = dias
    lunes0 = INICIO + timedelta(weeks=SEMANAS_PREVIAS)
    h = hist.copy()
    h["dias_atras"] = h["fecha_entreno"].map(lambda f: (lunes0 - f.date()).days)
    return {"config": cfg, "semanas": semanas,
            "historial": h[["dias_atras", "ejercicio", "tecnica", "numero_serie", "peso_kg", "reps_hechas",
                            "rpe", "tonelaje_serie", "bloque"]]}


def escenario(cfg: dict) -> dict:
    return _escenario(clave(normalizar(cfg)))


def para_app(cfg: dict) -> dict:
    """Lo que necesita la app: las 5 semanas y el ultimo mes de historial."""
    e = escenario(cfg)
    h = e["historial"]
    h = h[h["dias_atras"] <= DIAS_HISTORIAL_APP]
    return {
        "config": e["config"],
        "nombres_semana": NOMBRE_SEMANA,
        "semanas": e["semanas"],
        "historial": [{"dias_atras": int(r.dias_atras), "ejercicio": r.ejercicio, "tecnica": r.tecnica,
                       "numero_serie": int(r.numero_serie), "peso_kg": float(r.peso_kg),
                       "repeticiones": int(r.reps_hechas), "rpe": int(r.rpe)} for r in h.itertuples()],
    }


def historial_dashboard(cfg: dict, hoy: date | None = None) -> pd.DataFrame:
    """Historial del escenario con fechas reales: termina el domingo pasado."""
    h = escenario(cfg)["historial"].copy()
    hoy = hoy or date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    h["fecha_entreno"] = pd.to_datetime([lunes - timedelta(days=int(x)) for x in h["dias_atras"]])
    return h.drop(columns=["dias_atras"])

"""Series semanales por musculo, comparadas con los landmarks de volumen.

Cuenta series EFECTIVAS con el mismo perfil de estimulo que usa el generador
(ejercicios_db.ESTIMULOS): un press de banca suma 1 serie de pecho y 0.5 de
triceps y de deltoide anterior. Es el conteo fraccional de Pelland et al. (2024)
—las series indirectas cuentan la mitad—, que predice la hipertrofia mejor que
contar solo el musculo principal o contarlo todo como serie completa.

Dentro de un grupo (pecho = clavicular + esternal) cada serie cuenta UNA vez,
por su submusculo mas estimulado: si se sumaran, un press de banca valdria 1.25
series de pecho.

Landmarks orientativos por semana (Israetel, Hoffmann & Smith 2021, RP):
  MEV = minimo que produce crecimiento, MAV = rango productivo, MRV = maximo
  del que te recuperas. Son de poblacion: tu encuesta (feedback.py) es la que
  ajusta donde estas TU dentro de ese rango.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import ejercicios_db as db

# grupo visible -> submusculos de ejercicios_db.SUBMUSCULOS
GRUPOS: dict[str, list[str]] = {
    "Pecho":            ["pecho_sup", "pecho_inf"],
    "Dorsal":           ["dorsal"],
    "Espalda alta":     ["espalda_alta"],
    "Hombro frontal":   ["delt_ant"],
    "Hombro lateral":   ["delt_lat"],
    "Hombro posterior": ["delt_post"],
    "Bíceps":           ["biceps"],
    "Tríceps":          ["triceps"],
    "Cuádriceps":       ["cuadriceps"],
    "Isquios":          ["isquios"],
    "Glúteo":           ["gluteo", "gluteo_med"],
    "Gemelo":           ["gemelo"],
    "Abdomen":          ["abdomen"],
}

# (MEV, MAV desde, MAV hasta, MRV) en series por semana
LANDMARKS: dict[str, tuple[int, int, int, int]] = {
    "Pecho":            (8, 12, 20, 22),
    "Dorsal":           (8, 12, 20, 25),
    "Espalda alta":     (6, 10, 18, 25),
    "Hombro frontal":   (0, 6, 8, 12),
    "Hombro lateral":   (8, 16, 22, 26),
    "Hombro posterior": (6, 16, 22, 26),
    "Bíceps":           (8, 14, 20, 26),
    "Tríceps":          (6, 10, 14, 18),
    "Cuádriceps":       (8, 12, 18, 20),
    "Isquios":          (6, 10, 16, 20),
    "Glúteo":           (0, 4, 12, 16),
    "Gemelo":           (8, 12, 16, 20),
    "Abdomen":          (0, 16, 20, 25),
}

RPE_MIN_EFECTIVA = 6     # por debajo es calentamiento / aproximacion: no cuenta


def _perfiles() -> dict[str, dict[str, float]]:
    return {e.nombre.strip().lower(): db.estimulo_de(e) for e in db.EJERCICIOS}


def series_por_grupo(df: pd.DataFrame, desde: date, hasta: date) -> dict[str, float]:
    """Series efectivas por grupo entre `desde` (incluido) y `hasta` (excluido)."""
    out = {g: 0.0 for g in GRUPOS}
    if df.empty:
        return out
    perf = _perfiles()
    d = df[(df["fecha_entreno"] >= pd.Timestamp(desde)) & (df["fecha_entreno"] < pd.Timestamp(hasta))]
    if "rpe" in d:
        d = d[d["rpe"].isna() | (d["rpe"] >= RPE_MIN_EFECTIVA)]
    for nombre, n in d["ejercicio"].value_counts().items():
        est = perf.get(db.nombre_canonico(str(nombre)).strip().lower())
        if not est:
            continue
        for g, subs in GRUPOS.items():
            v = max((est.get(s, 0.0) for s in subs), default=0.0)
            if v:
                out[g] += v * int(n)
    return {g: round(v, 1) for g, v in out.items()}


def zona(grupo: str, series: float) -> str:
    mev, mav_lo, mav_hi, mrv = LANDMARKS[grupo]
    if series > mrv:
        return "sobre MRV"
    if series >= mav_lo:
        return "productivo" if series <= mav_hi else "alto"
    if series >= mev:
        return "mínimo"
    return "bajo"


def semanas_recientes(hoy: date) -> tuple[date, date, date]:
    """(lunes de la semana pasada, lunes de esta, lunes de la proxima)."""
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes - timedelta(days=7), lunes, lunes + timedelta(days=7)

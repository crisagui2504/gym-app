"""Motor de planificacion (metodologia del informe v3).

Genera el plan de la semana objetivo a partir de la plantilla (plan_template),
el historial real y la posicion en el mesociclo de 4 semanas:
  S1 = establecer base, S2-S3 = sobrecarga progresiva, S4 = semana pico.
Aplica progresion distinta por bloque (Top Set / Back-off / Volumen / Aislamiento)
y deload reactivo por estancamiento. Empuja el plan completo al servidor.
"""
from __future__ import annotations

import io
import os
import re
from datetime import date, timedelta
from urllib.parse import urlparse

import pandas as pd
import requests
from Crypto.Cipher import AES
from dotenv import load_dotenv

from plan_template import PLAN, Fila

# ---- Antibot InfinityFree (reto __test / aes.js) ----
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_RETO = re.compile(
    r'toNumbers\("([0-9a-f]+)"\),b=toNumbers\("([0-9a-f]+)"\),c=toNumbers\("([0-9a-f]+)"\)'
)

MICROCARGAS_MULTI = {"press", "remo", "sentadilla", "prensa", "peso muerto", "hip thrust"}


def api_config() -> tuple[str, str]:
    load_dotenv()
    base_url = os.environ["API_BASE_URL"].rstrip("/")
    token = os.environ["API_TOKEN"]
    return base_url, token


def sesion_infinityfree(base_url: str) -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": _UA})
    host = urlparse(base_url).hostname or ""
    primera = sesion.get(f"{base_url}/get_rutina_hoy.php", timeout=30)
    reto = _RETO.search(primera.text)
    if reto:
        a, b, c = (bytes.fromhex(x) for x in reto.groups())
        cookie = AES.new(a, AES.MODE_CBC, b).decrypt(c).hex()
        sesion.cookies.set("__test", cookie, domain=host)
    return sesion


def descargar_historial(sesion: requests.Session, base_url: str, token: str) -> pd.DataFrame:
    r = sesion.get(f"{base_url}/exportar_csv.php", params={"token": token}, timeout=30)
    r.raise_for_status()
    if not r.text.strip():
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty:
        return df
    df["fecha_entreno"] = pd.to_datetime(df["fecha_entreno"], errors="coerce")
    for col in ("peso_kg", "reps_hechas", "rpe", "tonelaje_serie"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---- Fechas y mesociclo ----
def lunes_objetivo() -> date:
    hoy = date.today()
    if hoy.weekday() == 6:  # domingo -> proxima semana
        return hoy + timedelta(days=1)
    return hoy - timedelta(days=hoy.weekday())  # lunes de esta semana


def semana_mesociclo(objetivo: date, inicio: date) -> int:
    """Ciclo de 5 semanas: S1 base, S2 rotacion, S3 superar S1, S4 pico, S5 deload."""
    delta = (objetivo - inicio).days
    return (max(0, delta) // 7) % 5 + 1


# ---- Utilidades de historial ----
def _norm(s: str) -> str:
    return str(s).strip().lower()


def ultimas_y_records(df: pd.DataFrame) -> tuple[dict, dict, set]:
    """Devuelve (ultima, record_mes, estancados) por (ejercicio, tecnica)."""
    if df.empty or "ejercicio" not in df:
        return {}, {}, set()
    df = df.copy()
    df["k"] = list(zip(df["ejercicio"].map(_norm), df["tecnica"].map(_norm)))
    ultima: dict = {}
    record: dict = {}
    estancados: set = set()
    hace_mes = pd.Timestamp(date.today() - timedelta(days=28))

    for k, g in df.groupby("k"):
        g = g.sort_values("fecha_entreno")
        ult_fecha = g["fecha_entreno"].max()
        sesion = g[g["fecha_entreno"] == ult_fecha]
        peso = float(sesion["peso_kg"].max())
        reps = int(sesion.loc[sesion["peso_kg"] == peso, "reps_hechas"].max())
        rpe = float(sesion["rpe"].mean()) if sesion["rpe"].notna().any() else 8.0
        ultima[k] = (peso, reps, rpe)
        record[k] = float(g[g["fecha_entreno"] >= hace_mes]["peso_kg"].max() or peso)

        # estancamiento: 3 semanas sin subir tonelaje
        sem = g.set_index("fecha_entreno").resample("W-MON")["tonelaje_serie"].sum().tail(3)
        if len(sem) >= 3 and sem.iloc[2] <= sem.iloc[1] <= sem.iloc[0]:
            estancados.add(k)
    return ultima, record, estancados


def microcarga(ejercicio: str) -> float:
    n = ejercicio.lower()
    return 2.5 if any(p in n for p in MICROCARGAS_MULTI) else 1.25


def redondear(v: float, paso: float = 1.25) -> float:
    return round(round(v / paso) * paso, 2)


# ---- Reglas de progresion por bloque ----
def _es(tec: str | None, *claves: str) -> bool:
    t = _norm(tec or "")
    return any(c in t for c in claves)


def peso_top_set(fila: Fila, lp, mes_best, micro, semana, estancado) -> float | None:
    if lp is None:
        return fila.peso_base
    peso, reps, rpe = lp
    if estancado and rpe >= 9:
        return redondear(peso * 0.9)  # deload reactivo (Ley II)
    if reps >= (fila.reps_max or 8) and rpe <= 9:
        nuevo = peso + micro
    elif reps < (fila.reps_min or 1):
        nuevo = peso * 0.95
    else:
        nuevo = peso + (micro if rpe <= 8 else 0)
    if semana == 4:  # semana pico: superar el mejor del mes
        nuevo = max(nuevo, (mes_best or peso) + micro)
    return redondear(nuevo)


def peso_volumen(fila: Fila, lp, micro) -> float | None:
    if lp is None:
        return fila.peso_base
    peso, reps, rpe = lp
    if reps >= (fila.reps_max or 12) and rpe <= 8:
        return redondear(peso + micro)
    return redondear(peso)


def nota_semana(semana: int) -> str:
    return {
        1: "S1: establece tu base, no al maximo absoluto.",
        2: "S2: rotacion Bloque B + supera el Top Set de la semana pasada.",
        3: "S3: supera los registros de S1.",
        4: "S4 PICO: supera TODOS los Top Sets del mes.",
        5: "S5 DELOAD: mismo peso, 50% volumen, sin Bloque C. Recuperacion.",
    }[semana]


def generar_filas(df: pd.DataFrame, semana_inicio: str, semana: int) -> list[dict]:
    ultima, record, estancados = ultimas_y_records(df)
    filas: list[dict] = []
    top_del_dia: dict[tuple[int, str], float | None] = {}

    # semana efectiva para la logica de progresion: deload (S5) usa S4 como referencia
    semana_prog = min(semana, 4)

    for f in PLAN:
        # ── Filtrar por semana especifica del ejercicio ──────────────────────
        if f.semanas is not None and semana_prog not in f.semanas:
            continue

        # ── S5 Deload: omitir Bloque C completo ─────────────────────────────
        if semana == 5 and "C -" in f.bloque:
            continue

        micro = microcarga(f.ejercicio)
        clave = (_norm(f.ejercicio), _norm(f.tecnica or ""))
        lp = ultima.get(clave)
        peso = None
        nota = f.notas

        if _es(f.tecnica, "top set"):
            if semana == 5:
                # Deload: mantener peso de la ultima sesion, sin progression
                peso = redondear(lp[0]) if lp else f.peso_base
            else:
                peso = peso_top_set(f, lp, record.get(clave), micro, semana_prog, clave in estancados)
            top_del_dia[(f.dia, _norm(f.ejercicio))] = peso
            nota = f"{f.notas or ''} {nota_semana(semana)}".strip()

        elif _es(f.tecnica, "back-off", "back off"):
            ts = top_del_dia.get((f.dia, _norm(f.ejercicio)))
            peso = redondear(ts * 0.8) if ts else (lp[0] if lp else f.peso_base)

        elif _es(f.tecnica, "tradicional", "amrap", "drop", "rest-pause", "rest pause", "superserie"):
            peso = peso_volumen(f, lp, micro)

        else:
            peso = f.peso_base  # cardio / descanso / farmer's carry

        # ── S5 Deload: reducir a 1 serie en Bloque A y B ────────────────────
        series_real = 1 if semana == 5 and "C -" not in f.bloque and f.tecnica else f.series

        filas.append(
            {
                "semana_inicio": semana_inicio,
                "dia_semana": f.dia,
                "nombre_dia": f.nombre_dia,
                "bloque": f.bloque,
                "orden": f.orden,
                "ejercicio": f.ejercicio,
                "tecnica": f.tecnica,
                "series_objetivo": series_real,
                "reps_min": f.reps_min,
                "reps_max": f.reps_max,
                "descanso_seg": f.descanso,
                "peso_sugerido": peso,
                "notas": nota,
            }
        )
    return filas


def sincronizar_plan(sesion: requests.Session, base_url: str, token: str, semana_inicio: str, filas: list[dict]) -> None:
    payload = {"semana_inicio": semana_inicio, "rutina": filas}
    r = sesion.post(
        f"{base_url}/actualizar_plan.php",
        json=payload,
        headers={"X-API-Token": token},
        timeout=60,
    )
    r.raise_for_status()
    print(r.json())


def main() -> None:
    base_url, token = api_config()
    objetivo = (
        date.fromisoformat(os.environ["SEMANA_SIGUIENTE"])
        if os.getenv("SEMANA_SIGUIENTE")
        else lunes_objetivo()
    )
    inicio = date.fromisoformat(os.environ["MES_INICIO"]) if os.getenv("MES_INICIO") else objetivo
    semana = semana_mesociclo(objetivo, inicio)
    semana_inicio = objetivo.isoformat()

    sesion = sesion_infinityfree(base_url)
    historial = descargar_historial(sesion, base_url, token)
    filas = generar_filas(historial, semana_inicio, semana)

    tipo = "DELOAD" if semana == 5 else f"S{semana}/4"
    print(f"Semana objetivo {semana_inicio} | Mesociclo: {tipo} | {len(filas)} filas")
    if os.getenv("DRY_RUN"):
        for f in filas:
            if f["tecnica"]:
                print(f"  D{f['dia_semana']} [{f['bloque']}] {f['ejercicio']} ({f['tecnica']}) -> {f['peso_sugerido']} kg x{f['reps_min']}-{f['reps_max']} desc {f['descanso_seg']}s")
        print("DRY_RUN: no se envio nada al servidor.")
        return

    sincronizar_plan(sesion, base_url, token, semana_inicio, filas)
    print(f"Plan de la semana {semana_inicio} ({tipo}) sincronizado.")


if __name__ == "__main__":
    main()

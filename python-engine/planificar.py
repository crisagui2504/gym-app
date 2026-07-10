"""Motor de planificacion (metodologia del informe v3).

Genera el plan de la semana objetivo a partir de la plantilla (plan_template),
el historial real y la posicion en el mesociclo de 4 semanas:
  S1 = establecer base, S2-S3 = sobrecarga progresiva, S4 = semana pico.
Aplica progresion distinta por bloque (Top Set / Back-off / Volumen / Aislamiento)
y deload reactivo por estancamiento. Empuja el plan completo al servidor.

Reglas de progresion (ajustadas a evidencia 2022-2025, ver docs/CAMBIOS_EVIDENCIA.md):
  - Doble progresion estricta: primero llenar el rango de reps, luego subir carga.
  - El RPE que gobierna la progresion es el de las series de trabajo; la serie
    final prescrita al fallo (AMRAP/Rest-Pause/Drop) se excluye del promedio.
  - El PR de la S4 se intenta solo si la ultima sesion completo el rango con
    RPE <= 8 (progresion ganada, no forzada por calendario).
  - S5 deload: misma intensidad, 50% de volumen, cero series al fallo.
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

from plan_template import Fila
from generador import obtener_plan

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
    for col in ("peso_kg", "reps_hechas", "rpe", "tonelaje_serie", "numero_serie"):
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


def _familia(tec) -> str:
    """Familia de progresion de una tecnica.

    El historial se agrupa por familia (no por el texto exacto de la tecnica)
    para que la progresion no se corte cuando la tecnica del mismo ejercicio
    rota entre semanas (Tradicional <-> AMRAP <-> Drop Set <-> Rest-Pause)."""
    t = _norm(tec)
    if "top set" in t:
        return "top set"
    if "back" in t:
        return "back-off"
    return "volumen"


def ultimas_y_records(df: pd.DataFrame) -> tuple[dict, dict, set]:
    """Devuelve (ultima, record_mes, estancados) por (ejercicio, familia_tecnica)."""
    if df.empty or "ejercicio" not in df:
        return {}, {}, set()
    df = df.copy()
    df["k"] = list(zip(df["ejercicio"].map(_norm), df["tecnica"].map(_familia)))
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
        # RPE de trabajo: si la ultima serie fue prescrita al fallo (AMRAP,
        # Rest-Pause o Drop Set), se excluye del promedio. Ese RPE 10 es
        # intencional y no debe bloquear la condicion de progresion (RPE <= 8).
        trabajo = sesion
        if len(sesion) > 1 and "numero_serie" in sesion:
            ult_serie = sesion["numero_serie"].max()
            tec_ult = _norm(sesion.loc[sesion["numero_serie"] == ult_serie, "tecnica"].iloc[0])
            if any(x in tec_ult for x in ("amrap", "rest", "drop")):
                trabajo = sesion[sesion["numero_serie"] < ult_serie]
        rpe = float(trabajo["rpe"].mean()) if trabajo["rpe"].notna().any() else 8.0
        ultima[k] = (peso, reps, rpe)
        mes = g[g["fecha_entreno"] >= hace_mes]["peso_kg"].max()
        record[k] = float(mes) if pd.notna(mes) else peso

        # estancamiento: 3 semanas sin subir tonelaje
        sem = g.set_index("fecha_entreno").resample("W-MON")["tonelaje_serie"].sum().tail(3)
        if len(sem) >= 3 and sem.iloc[2] <= sem.iloc[1] <= sem.iloc[0]:
            estancados.add(k)
    return ultima, record, estancados


def fatiga_global(df: pd.DataFrame) -> bool:
    """Deload reactivo global: RPE promedio semanal >= 9 en las ultimas 2
    semanas con datos. Es la misma senal que muestra el dashboard en la
    pestana de fatiga; ahora el motor tambien actua sobre ella."""
    if df.empty or "rpe" not in df or df["rpe"].notna().sum() == 0:
        return False
    sem = df.set_index("fecha_entreno")["rpe"].resample("W-MON").mean().dropna().tail(2)
    return len(sem) >= 2 and bool((sem >= 9).all())


def marca_anterior(lp) -> str:
    """Texto 'a superar' para la tarjeta de la app (doble progresion visible)."""
    if not lp:
        return ""
    peso, reps, rpe = lp
    if peso and peso > 0:
        return f"Anterior: {peso:g} kg x {reps} @RPE {rpe:.0f}."
    return f"Anterior: {reps} reps @RPE {rpe:.0f}."


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
        nuevo = peso + micro          # rango completado -> sube la carga
    elif reps < (fila.reps_min or 1):
        nuevo = peso * 0.95           # no llego al rango -> baja 5%
    else:
        nuevo = peso                  # dentro del rango -> progresa en reps (doble progresion)
    # S4 pico: intentar superar el mejor del mes SOLO si el rendimiento reciente
    # lo respalda (rango completo con RPE <= 8). Un PR forzado por calendario
    # con fatiga acumulada es riesgo de lesion, no sobrecarga progresiva.
    if semana == 4 and reps >= (fila.reps_max or 8) and rpe <= 8:
        nuevo = max(nuevo, (mes_best or peso) + micro)
    return redondear(nuevo)


def peso_volumen(fila: Fila, lp, micro) -> float | None:
    if lp is None:
        return fila.peso_base
    peso, reps, rpe = lp
    if peso <= 0:
        return fila.peso_base  # peso corporal: progresa por reps, no por carga
    if reps >= (fila.reps_max or 12) and rpe <= 8:
        return redondear(peso + micro)
    return redondear(peso)


def nota_semana(semana: int) -> str:
    return {
        1: "S1: establece tu base, no al maximo absoluto.",
        2: "S2: rotacion Bloque B + supera el Top Set de la semana pasada.",
        3: "S3: supera los registros de S1.",
        4: "S4 PICO: intenta superar tus Top Sets del mes SOLO si llegas con el rango completo y RPE <= 8.",
        5: "S5 DELOAD: mismo peso, 50% volumen, sin Bloque C ni series al fallo. Recuperacion.",
    }[semana]


def generar_filas(df: pd.DataFrame, semana_inicio: str, semana: int,
                  plan: list[Fila] | None = None) -> list[dict]:
    ultima, record, estancados = ultimas_y_records(df)
    filas: list[dict] = []
    top_del_dia: dict[tuple[int, str], float | None] = {}

    # plan base segun la config del usuario (enfoque/split/prioridades)
    if plan is None:
        plan = obtener_plan()

    # semana efectiva para la logica de progresion: deload (S5) usa S4 como referencia
    semana_prog = min(semana, 4)

    for f in plan:
        # ── Filtrar por semana especifica del ejercicio ──────────────────────
        if f.semanas is not None and semana_prog not in f.semanas:
            continue

        # ── S5 Deload: omitir Bloque C completo ─────────────────────────────
        if semana == 5 and "C -" in f.bloque:
            continue

        micro = microcarga(f.ejercicio)
        clave = (_norm(f.ejercicio), _familia(f.tecnica))
        lp = ultima.get(clave)
        peso = None
        nota = f.notas
        tecnica_out = f.tecnica

        # S5 Deload: cero series al fallo. Las tecnicas de intensidad se
        # sustituyen por trabajo tradicional lejos del fallo (RIR 3-4).
        if semana == 5 and _es(f.tecnica, "amrap", "rest", "drop"):
            tecnica_out = "Tradicional"
            nota = "S5 DELOAD: sin fallo, deja 3-4 reps en reserva."

        marca = marca_anterior(lp) if semana != 5 else ""

        if _es(f.tecnica, "top set"):
            if semana == 5:
                # Deload: mantener peso de la ultima sesion, sin progression
                peso = redondear(lp[0]) if lp else f.peso_base
            else:
                peso = peso_top_set(f, lp, record.get(clave), micro, semana_prog, clave in estancados)
            top_del_dia[(f.dia, _norm(f.ejercicio))] = peso
            nota = f"{marca} {f.notas or ''} {nota_semana(semana)}".strip()

        elif _es(f.tecnica, "back-off", "back off"):
            ts = top_del_dia.get((f.dia, _norm(f.ejercicio)))
            peso = redondear(ts * 0.8) if ts else (lp[0] if lp else f.peso_base)

        elif _es(f.tecnica, "tradicional", "amrap", "drop", "rest-pause", "rest pause", "superserie"):
            peso = peso_volumen(f, lp, micro)
            if marca:
                nota = f"{marca} {nota or ''}".strip()

        else:
            peso = f.peso_base  # cardio / descanso / farmer's carry

        # ── Peso corporal / core: progresion por repeticiones ───────────────
        # Sin carga externa la unica sobrecarga es hacer mas reps: si el rango
        # se completo lejos del fallo, el rango objetivo sube (hasta 30 reps;
        # despues, lastre).
        reps_min_out, reps_max_out = f.reps_min, f.reps_max
        if (semana != 5 and lp and (lp[0] or 0) <= 0 and not peso and f.reps_max
                and f.bloque not in ("Cardio", "Descanso")
                and lp[1] >= f.reps_max and lp[2] <= 8):
            delta = min(lp[1] - f.reps_max + 1, max(0, 30 - f.reps_max))
            if delta > 0:
                reps_min_out = (f.reps_min or 0) + delta
                reps_max_out = f.reps_max + delta
                nota = f"Sube el objetivo: {reps_min_out}-{reps_max_out} reps. {nota or ''}".strip()

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
                "tecnica": tecnica_out,
                "series_objetivo": series_real,
                "reps_min": reps_min_out,
                "reps_max": reps_max_out,
                "descanso_seg": f.descanso,
                "peso_sugerido": peso,
                "notas": nota[:255] if nota else nota,  # plan_rutina.notas VARCHAR(255)
            }
        )

    # Recortar volumen para que la sesion entre en la duracion objetivo
    from config_usuario import cargar_config
    return _recortar_duracion(filas, int(cargar_config().get("duracion_min", 90)))


# Max de ejercicios (movimientos) de pesas por dia segun la duracion objetivo.
_CAP_MOVIMIENTOS = {60: 5, 75: 6, 90: 8, 120: 11}


def _recortar_duracion(filas: list[dict], duracion_min: int) -> list[dict]:
    """Limita los ejercicios de pesas por dia (ya filtrados por semana).
    Recorta el Bloque C desde el final hasta entrar en el tiempo.
    La superserie biceps+triceps se recorta como unidad (ambos o ninguno):
    si se quitara solo un miembro, el otro quedaria 'en superserie' sin pareja."""
    cap = _CAP_MOVIMIENTOS.get(duracion_min, 8)
    por_dia: dict[int, list[dict]] = {}
    for f in filas:
        por_dia.setdefault(f["dia_semana"], []).append(f)

    quitar: set[tuple[int, str]] = set()
    for dia, fdia in por_dia.items():
        movs: list[str] = []
        for f in fdia:
            b = (f["bloque"] or "")[:1]
            if b in ("A", "B", "C") and f["ejercicio"] not in movs:
                movs.append(f["ejercicio"])
        if len(movs) <= cap:
            continue
        es_super = {f["ejercicio"] for f in fdia if (f["tecnica"] or "") == "Superserie"}
        c_movs = [m for m in movs
                  if any(f["ejercicio"] == m and (f["bloque"] or "").startswith("C") for f in fdia)]
        # unidades de recorte: los miembros consecutivos de la superserie van juntos
        unidades: list[list[str]] = []
        for m in c_movs:
            if m in es_super and unidades and unidades[-1][0] in es_super:
                unidades[-1].append(m)
            else:
                unidades.append([m])
        restantes = len(movs)
        for unidad in reversed(unidades):
            if restantes <= cap:
                break
            for m in unidad:
                quitar.add((dia, m))
            restantes -= len(unidad)

    return [f for f in filas if (f["dia_semana"], f["ejercicio"]) not in quitar]


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

    # Deload reactivo global: si la fatiga acumulada es alta (RPE semanal >= 9
    # dos semanas seguidas), se adelanta la descarga sin esperar a la S5.
    if semana != 5 and fatiga_global(historial):
        print("DELOAD REACTIVO: RPE promedio semanal >= 9 las ultimas 2 semanas. "
              "Se adelanta la semana de descarga.")
        semana = 5

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

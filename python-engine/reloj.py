"""El reloj (Amazfit -> Zepp -> Apple Salud) dentro del motor.

La app lee la exportacion de Salud EN EL TELEFONO (app/src/app/salud.ts) y sube
solo los totales por dia a InfinityFree (guardar_reloj.php): sueno, pulso
nocturno, pasos, peso y entrenos. Aqui se bajan (get_reloj.php) y sirven para:

1. RECUPERACION (planificar.decidir_semana): una noche completa de menos de 5 h, o
   el pulso nocturno 5+ lpm por encima de tu linea base, cuenta como "dia malo"
   igual que contestar "dormi mal" en la app; con 3 en la semana se adelanta la
   descarga (feedback.DIAS_MALOS_DELOAD). El pulso en reposo que sube sobre tu
   propia base es la senal clasica de fatiga acumulada o de una enfermedad que
   empieza (Buchheit 2014; Radin et al. 2020, Lancet Digit Health). Las noches de
   menos de 3 h NO cuentan: casi siempre es el reloj que no se uso toda la noche.
2. DURACION REAL (planificar.generar_filas): si tus sesiones (entreno de Fuerza
   iniciado en el reloj) duran mas o menos de lo que el motor estima, el recorte
   y el relleno de la sesion se calibran con tu ritmo real.
3. ENTRENOS SIN ANOTAR: el reloj registro fuerza un dia sin series en la app.
4. PASOS (nutricion.evaluar): si la bascula se frena y tus pasos bajaron, primero
   se recuperan los pasos antes de bajar calorias. El peso de Zepp pasa a Nutri
   los dias sin pesaje (exportar_local).

Las calorias del reloj NO se usan: los relojes se equivocan 20-40 % en gasto
energetico (Shcherbina et al. 2017, J Pers Med).
"""
from __future__ import annotations

import pathlib
from datetime import date, timedelta

import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
CSV_DIAS = "reloj_dias.csv"          # copias locales para el dashboard (las escribe exportar_local)
CSV_ENTRENOS = "reloj_entrenos.csv"
COLUMNAS_DIAS = ["fecha", "sueno_min", "pulso_noche", "pulso_reposo", "hrv", "pasos", "peso"]
COLUMNAS_ENTRENOS = ["inicio", "fin", "tipo", "minutos", "pulso_prom"]

# ── Recuperacion ─────────────────────────────────────────────────────────────
NOCHE_INCOMPLETA_MIN = 180   # < 3 h: el reloj no se uso toda la noche (no es dato)
NOCHE_CORTA_MIN = 300        # < 5 h: noche mala (una sola ya afecta el rendimiento)
SUENO_META_H = 7.0           # adultos: 7 h o mas (consenso AASM/SRS, Watson et al. 2015)
PULSO_ALTO_LPM = 5           # pulso nocturno >= base + 5 lpm: dia malo
BASE_NOCHES_MIN = 7          # sin 7 noches de base el criterio del pulso no se usa
BASE_DIAS = 28               # la base: mediana de las noches de las 4 semanas previas

# ── Duracion real de la sesion ───────────────────────────────────────────────
TIPOS_FUERZA = {"TraditionalStrengthTraining", "FunctionalStrengthTraining"}
RITMO_SESIONES_MIN = 3       # sesiones con reloj Y series anotadas para calibrar
RITMO_DIAS = 42              # se miran las ultimas 6 semanas
RITMO_TOPE = (0.8, 1.3)      # el ajuste nunca pasa de -20 % / +30 % del estimado
RITMO_VALIDO = (0.6, 1.8)    # fuera de esto la sesion se ignora (reloj olvidado prendido...)
SERIES_MIN_SESION = 6        # sesiones con menos series anotadas no calibran (incompletas)

# ── Pasos ────────────────────────────────────────────────────────────────────
PASOS_CAIDA = 0.15           # caida de 15 %+ contra las 3 semanas previas
PASOS_DIAS_MIN = 4           # dias con pasos para que el promedio de la semana cuente


def _vacios() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.DataFrame(columns=COLUMNAS_DIAS), pd.DataFrame(columns=COLUMNAS_ENTRENOS)


def normalizar(dias: pd.DataFrame, entrenos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = dias.copy() if dias is not None and not dias.empty else pd.DataFrame(columns=COLUMNAS_DIAS)
    e = entrenos.copy() if entrenos is not None and not entrenos.empty else pd.DataFrame(columns=COLUMNAS_ENTRENOS)
    for c in COLUMNAS_DIAS:
        if c not in d:
            d[c] = None
    for c in COLUMNAS_ENTRENOS:
        if c not in e:
            e[c] = None
    d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
    for c in COLUMNAS_DIAS[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["fecha"]).sort_values("fecha").drop_duplicates("fecha", keep="last")
    e["inicio"] = pd.to_datetime(e["inicio"], errors="coerce")
    e["fin"] = pd.to_datetime(e["fin"], errors="coerce")
    e["minutos"] = pd.to_numeric(e["minutos"], errors="coerce")
    e["pulso_prom"] = pd.to_numeric(e["pulso_prom"], errors="coerce")
    e["tipo"] = e["tipo"].astype(str)
    e = e.dropna(subset=["inicio", "minutos"]).sort_values("inicio")
    return d[COLUMNAS_DIAS].reset_index(drop=True), e[COLUMNAS_ENTRENOS].reset_index(drop=True)


def descargar(sesion, base_url: str, token: str, dias: int = 120) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """(dias, entrenos) del servidor. Sin endpoint, sin red o sin datos: None
    (el motor sigue igual que sin reloj)."""
    try:
        r = sesion.get(f"{base_url}/get_reloj.php", params={"dias": dias},
                       headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        j = r.json()
        if not j.get("ok"):
            return None
    except Exception as e:  # noqa: BLE001
        print(f"Reloj no disponible ({e.__class__.__name__}): plan sin datos del reloj.")
        return None
    return normalizar(pd.DataFrame(j.get("dias") or []), pd.DataFrame(j.get("entrenos") or []))


def guardar_csv(dias: pd.DataFrame, entrenos: pd.DataFrame, carpeta=AQUI) -> None:
    carpeta = pathlib.Path(carpeta)
    dias.to_csv(carpeta / CSV_DIAS, index=False, date_format="%Y-%m-%d")
    entrenos.to_csv(carpeta / CSV_ENTRENOS, index=False, date_format="%Y-%m-%d %H:%M:%S")


def leer_csv(carpeta=AQUI) -> tuple[pd.DataFrame, pd.DataFrame]:
    carpeta = pathlib.Path(carpeta)
    try:
        d = pd.read_csv(carpeta / CSV_DIAS) if (carpeta / CSV_DIAS).exists() else None
        e = pd.read_csv(carpeta / CSV_ENTRENOS) if (carpeta / CSV_ENTRENOS).exists() else None
    except Exception:  # noqa: BLE001
        return _vacios()
    return normalizar(d, e)


# ── 1. Recuperacion ──────────────────────────────────────────────────────────
def _noches(dias: pd.DataFrame) -> pd.DataFrame:
    """Noches completas (3 h o mas de sueno registrado)."""
    if dias is None or dias.empty:
        return pd.DataFrame(columns=COLUMNAS_DIAS)
    return dias[dias["sueno_min"] >= NOCHE_INCOMPLETA_MIN]


def base_pulso(dias: pd.DataFrame, objetivo: date, ventana: int = 7) -> float | None:
    """Tu pulso nocturno de referencia: mediana de las 4 semanas ANTES de la semana
    que se evalua (asi una semana mala no se esconde subiendo su propia base)."""
    n = _noches(dias)               # solo noches completas: en 1-2 h el pulso no es representativo
    if n.empty:
        return None
    fin = pd.Timestamp(objetivo - timedelta(days=ventana))
    previas = n[(n["fecha"] >= fin - pd.Timedelta(days=BASE_DIAS)) & (n["fecha"] < fin)]["pulso_noche"].dropna()
    return float(previas.median()) if len(previas) >= BASE_NOCHES_MIN else None


def dias_malos(dias: pd.DataFrame, objetivo: date, ventana: int = 7) -> dict[date, str]:
    """{fecha: motivo} de la semana antes de `objetivo` que cuentan como dia malo."""
    if dias is None or dias.empty:
        return {}
    semana = dias[(dias["fecha"] >= pd.Timestamp(objetivo - timedelta(days=ventana)))
                  & (dias["fecha"] < pd.Timestamp(objetivo))]
    base = base_pulso(dias, objetivo, ventana)
    out: dict[date, str] = {}
    for f in semana.itertuples():
        sueno = f.sueno_min
        if pd.isna(sueno) or sueno < NOCHE_INCOMPLETA_MIN:
            continue                # sin noche completa no hay dato (ni de sueno ni de pulso)
        if sueno < NOCHE_CORTA_MIN:
            out[f.fecha.date()] = f"dormiste {sueno / 60:.1f} h"
        elif base is not None and pd.notna(f.pulso_noche) and f.pulso_noche >= base + PULSO_ALTO_LPM:
            out[f.fecha.date()] = f"pulso nocturno {f.pulso_noche:.0f} (tu base {base:.0f})"
    return out


def aviso_sueno(dias: pd.DataFrame, objetivo: date, ventana: int = 7) -> str | None:
    """Aviso (no cambia el plan) si dormiste en promedio menos de 7 h (3+ noches)."""
    s = promedio_sueno(dias, objetivo, ventana)
    if not s or s[1] < 3 or s[0] >= SUENO_META_H:
        return None
    return (f"SUENO: promedio {s[0]:.1f} h en {s[1]} noches (reloj). Con menos de 7 h, en deficit "
            "se pierde mas musculo y menos grasa (Nedeltcheva 2010): dormir mas es lo que mas te ayuda.")


# ── 2. Duracion real ─────────────────────────────────────────────────────────
def _min_por_serie(tecnica: str | None, bloque: str | None) -> float:
    """Minutos de una serie anotada: ~45 s de trabajo + el descanso que pone el
    generador (enfoques.DESC), la misma cuenta que planificar._minutos_serie."""
    from enfoques import DESC
    t = (tecnica or "").lower()
    b = (bloque or "")[:1].upper()
    if "top" in t:
        d = DESC["top_set"]
    elif "back" in t:
        d = DESC["back_off"]
    elif "rest" in t:
        d = DESC["rest_pause"]
    elif "drop" in t:
        d = DESC["drop_set"]
    elif "super" in t:
        d = DESC["superserie"]
    elif b == "C":
        d = DESC["aislamiento"]
    else:
        d = DESC["volumen"]
    return (d + 45) / 60


def minutos_estimados(series: pd.DataFrame) -> float:
    """Lo que el motor habria estimado para las series anotadas de un dia."""
    from planificar import CALENTAMIENTO_MIN, CAMBIO_MIN
    bloque = series["bloque"] if "bloque" in series else pd.Series([None] * len(series), index=series.index)
    tecnica = series["tecnica"] if "tecnica" in series else pd.Series([None] * len(series), index=series.index)
    total = sum(_min_por_serie(None if pd.isna(t) else str(t), None if pd.isna(b) else str(b))
                for t, b in zip(tecnica, bloque))
    return total + CALENTAMIENTO_MIN + CAMBIO_MIN * series["ejercicio"].nunique()


def _sesiones(entrenos: pd.DataFrame, historial: pd.DataFrame, hoy: date, dias: int) -> list[tuple[date, float, float]]:
    """(fecha, minutos reloj, minutos estimados) de las sesiones de fuerza con
    reloj Y series anotadas ese mismo dia."""
    if entrenos is None or entrenos.empty or historial is None or historial.empty:
        return []
    desde = pd.Timestamp(hoy - timedelta(days=dias))
    fz = entrenos[entrenos["tipo"].isin(TIPOS_FUERZA) & (entrenos["inicio"] >= desde)
                  & (entrenos["inicio"] < pd.Timestamp(hoy))]
    if fz.empty:
        return []
    h = historial.copy()
    h["_f"] = pd.to_datetime(h["fecha_entreno"], errors="coerce").dt.date
    out = []
    for fecha, real in fz.groupby(fz["inicio"].dt.date)["minutos"].sum().items():
        series = h[h["_f"] == fecha]
        if len(series) >= SERIES_MIN_SESION:
            out.append((fecha, float(real), minutos_estimados(series)))
    return out


def ritmo_sesiones(entrenos: pd.DataFrame, historial: pd.DataFrame, hoy: date) -> tuple[float, int]:
    """(factor, sesiones): cuanto duran tus sesiones reales contra el estimado del
    motor. 1.0 si no hay suficientes sesiones con reloj y series anotadas."""
    ratios = [r / e for _, r, e in _sesiones(entrenos, historial, hoy, RITMO_DIAS)
              if e > 0 and RITMO_VALIDO[0] <= r / e <= RITMO_VALIDO[1]]
    if len(ratios) < RITMO_SESIONES_MIN:
        return 1.0, len(ratios)
    f = float(pd.Series(ratios).median())
    f = round(max(RITMO_TOPE[0], min(RITMO_TOPE[1], f)) * 20) / 20     # pasos de 5 %
    return (1.0 if abs(f - 1.0) < 0.05 else f), len(ratios)


def aviso_ritmo(factor: float, n: int, duracion_min: int) -> str | None:
    if factor == 1.0:
        return None
    pct = round((factor - 1) * 100)
    que = "mas" if pct > 0 else "menos"
    accion = "recorta" if pct > 0 else "llena"
    return (f"TIEMPO REAL: tus sesiones duran {abs(pct)} % {que} de lo estimado ({n} con reloj). "
            f"El motor {accion} la sesion para que quepa en tus {duracion_min} min reales.")


# ── 3. Entrenos sin anotar ───────────────────────────────────────────────────
def entrenos_sin_anotar(entrenos: pd.DataFrame, historial: pd.DataFrame, objetivo: date,
                        dias: int = 14) -> list[tuple[date, float]]:
    """Dias con entreno de fuerza en el reloj (20+ min) y ninguna serie en la app."""
    if entrenos is None or entrenos.empty:
        return []
    fz = entrenos[entrenos["tipo"].isin(TIPOS_FUERZA) & (entrenos["minutos"] >= 20)
                  & (entrenos["inicio"] >= pd.Timestamp(objetivo - timedelta(days=dias)))
                  & (entrenos["inicio"] < pd.Timestamp(objetivo))]
    anotados: set[date] = set()
    if historial is not None and not historial.empty:
        anotados = set(pd.to_datetime(historial["fecha_entreno"], errors="coerce").dt.date.dropna())
    por_dia = fz.groupby(fz["inicio"].dt.date)["minutos"].sum()
    return [(f, float(m)) for f, m in por_dia.items() if f not in anotados]


def aviso_sin_anotar(faltan: list[tuple[date, float]]) -> str | None:
    if not faltan:
        return None
    dias = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
    lista = ", ".join(f"{dias[f.weekday()]} {f.day} ({m:.0f} min)" for f, m in faltan)
    return (f"SIN ANOTAR: el reloj registro fuerza el {lista} y la app no tiene series de ese dia. "
            "El motor no lo cuenta para tu progreso: guarda el entreno en la app al terminar.")


def promedio_sueno(dias: pd.DataFrame, objetivo: date, ventana: int = 7) -> tuple[float, int] | None:
    """(horas promedio, noches) de las noches completas de la semana antes de `objetivo`."""
    n = _noches(dias)
    if n.empty:
        return None
    n = n[(n["fecha"] >= pd.Timestamp(objetivo - timedelta(days=ventana))) & (n["fecha"] < pd.Timestamp(objetivo))]
    return (float(n["sueno_min"].mean()) / 60, len(n)) if len(n) else None


def texto_telefono(dias: pd.DataFrame | None, objetivo: date, ritmo: float, n_ritmo: int,
                   sin_anotar: list[tuple[date, float]]) -> str | None:
    """La notificacion del domingo con lo que vio el reloj (None si no hay nada que decir)."""
    partes: list[str] = []
    s = promedio_sueno(dias, objetivo)
    if s and s[1] >= 3 and s[0] < SUENO_META_H:
        partes.append(f"Dormiste {s[0]:.1f} h en promedio (meta: 7 h).")
    malos = dias_malos(dias, objetivo)
    if malos:
        partes.append(f"{len(malos)} noche{'s' if len(malos) > 1 else ''} mala{'s' if len(malos) > 1 else ''} "
                      "contaron para tu recuperación.")
    if ritmo != 1.0:
        pct = round((ritmo - 1) * 100)
        partes.append(f"Tus sesiones duran {abs(pct)} % {'más' if pct > 0 else 'menos'} de lo estimado: "
                      "la semana ya viene ajustada.")
    if sin_anotar:
        dias_sem = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
        partes.append("Fuerza sin anotar: " + ", ".join(f"{dias_sem[f.weekday()]} {f.day}" for f, _ in sin_anotar) + ".")
    return " ".join(partes) or None


# ── 4. Pasos ─────────────────────────────────────────────────────────────────
def pasos_semana(dias: pd.DataFrame, hoy: date) -> dict | None:
    """{'semana': promedio de los ultimos 7 dias, 'antes': de las 3 semanas previas,
    'cambio': fraccion}. None sin datos suficientes."""
    if dias is None or dias.empty:
        return None
    p = dias.dropna(subset=["pasos"])
    p = p[p["pasos"] > 0]
    fin = pd.Timestamp(hoy)
    sem = p[(p["fecha"] > fin - pd.Timedelta(days=7)) & (p["fecha"] <= fin)]["pasos"]
    ant = p[(p["fecha"] > fin - pd.Timedelta(days=28)) & (p["fecha"] <= fin - pd.Timedelta(days=7))]["pasos"]
    if len(sem) < PASOS_DIAS_MIN or len(ant) < 2 * PASOS_DIAS_MIN:
        return None
    s, a = float(sem.mean()), float(ant.mean())
    return {"semana": round(s), "antes": round(a), "cambio": round((s - a) / a, 3) if a > 0 else 0.0}


# ── Peso del reloj -> Nutri ──────────────────────────────────────────────────
def pasar_pesos(sesion, base_url: str, token: str, dias: pd.DataFrame, hoy: date | None = None) -> int:
    """Sube a la API de pesos (Nutri) los pesajes del reloj en dias sin pesaje.
    Devuelve cuantos subio; nunca lanza (sin red: se intenta la proxima vez)."""
    try:
        import nutricion
        servidor = nutricion.descargar_peso(sesion, base_url, token)
        if servidor is None:
            return 0
        return sum(bool(nutricion.subir_peso(sesion, base_url, token, f.isoformat(), kg, None))
                   for f, kg in pesos_nuevos(dias, servidor, hoy or date.today()))
    except Exception as e:  # noqa: BLE001
        print(f"Pesos del reloj no pasados a Nutri ({e.__class__.__name__}).")
        return 0


def pesos_nuevos(dias: pd.DataFrame, pesos_servidor: pd.DataFrame | None, hoy: date,
                 ventana: int = 30) -> list[tuple[date, float]]:
    """Pesajes del reloj de los ultimos `ventana` dias en fechas SIN pesaje en Nutri
    (el que anotas tu siempre manda: nunca se pisa)."""
    if dias is None or dias.empty:
        return []
    ya: set[date] = set()
    if pesos_servidor is not None and not pesos_servidor.empty:
        ya = set(pd.to_datetime(pesos_servidor["fecha"], errors="coerce").dt.date.dropna())
    d = dias.dropna(subset=["peso"])
    d = d[(d["fecha"] >= pd.Timestamp(hoy - timedelta(days=ventana))) & (d["fecha"] <= pd.Timestamp(hoy))]
    return [(f.fecha.date(), round(float(f.peso), 1)) for f in d.itertuples()
            if f.fecha.date() not in ya and 30 <= f.peso <= 250]

"""Volumen autorregulado por la encuesta de la sesion (estilo RP Hypertrophy).

La app pregunta, por cada musculo trabajado:
  al EMPEZAR   agujetas de la vez anterior  1 nada | 2 sanaron justo | 3 aun duelen
  al TERMINAR  bombeo                       1 poco | 2 bueno | 3 brutal
               carga de trabajo             1 facil | 2 justa | 3 demasiado
y, por ejercicio, si molesto alguna ARTICULACION (dolor=1).

Reglas (por musculo y semana del mesociclo en curso):
  - no se recupera (agujetas 3) o la carga fue demasiada (carga 3)  -> -1 serie
  - se recupera de sobra (agujetas 1) sin carga ni bombeo extremos  -> +1 serie
    (sin dato de agujetas, solo una carga "facil" con bombeo bajo cuenta como margen)
  - lo demas                                                         ->  0
El ajuste se ACUMULA dentro del mesociclo (asi sube el volumen semana a semana,
de MEV hacia MRV) con tope [-2, +3], y se reinicia con cada mesociclo nuevo.
No se aplica en deload ni en reingreso: ahi el volumen lo fija la seguridad.

Dolor articular en un ejercicio: 1 vez -> no se le suman series y lleva aviso;
2 sesiones distintas en 3 semanas -> se cambia por otro del mismo patron.

Referencias: Israetel, Hoffmann & Smith, Scientific Principles of Hypertrophy
Training (2021) - landmarks MEV/MAV/MRV y progresion de volumen por feedback;
Schoenfeld et al. (2017) dosis-respuesta del volumen.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

import ejercicios_db as db

AJUSTE_MIN, AJUSTE_MAX = -2, 3      # series por musculo y semana respecto al plan base
SERIES_MAX_FILA = 5                 # nunca mas de 5 series en un mismo ejercicio
SERIES_MIN_FILA = 2                 # quitar series no deja un ejercicio en 1
EXTRA_MAX_DIA = 3                   # una sesion no crece mas de 3 series (cabe en el tiempo)
DOLOR_PARA_CAMBIAR = 2              # sesiones con dolor articular para sustituir el ejercicio
VENTANA_DOLOR = 21                  # dias en los que se cuentan esas sesiones

# tecnicas de VOLUMEN: a las que se suman/quitan series. El Top Set y su
# Back-off no se tocan (son la referencia de fuerza de la semana).
_VOLUMEN = ("tradicional", "amrap", "drop", "rest", "superserie")


def _norm(s) -> str:
    return str(s or "").strip().lower()


def descargar_feedback(sesion, base_url: str, token: str, dias: int = 42) -> pd.DataFrame:
    """Respuestas de la encuesta. Si el endpoint aun no esta subido o falla, un
    DataFrame vacio: sin encuesta el plan es el de siempre, nunca un error."""
    try:
        r = sesion.get(f"{base_url}/get_feedback.php", params={"dias": dias},
                       headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        filas = r.json().get("feedback") or []
    except Exception as e:  # noqa: BLE001
        print(f"Encuesta no disponible ({e.__class__.__name__}): plan sin ajuste por feedback.")
        return pd.DataFrame()
    return normalizar(pd.DataFrame(filas))


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    for c in ("bombeo", "carga", "agujetas", "dolor"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    return df.dropna(subset=["fecha"]).reset_index(drop=True)


def _delta_semana(g: pd.DataFrame) -> int:
    agujetas = g["agujetas"].max()
    carga = g["carga"].max()
    bombeo = g["bombeo"].max()
    if agujetas == 3 or carga == 3:
        return -1
    if agujetas == 1 and carga != 3 and bombeo != 3:
        return 1
    if pd.isna(agujetas) and carga == 1 and (pd.isna(bombeo) or bombeo == 1):
        return 1
    return 0


def ajustes_por_musculo(fb: pd.DataFrame, inicio_meso: date, objetivo: date) -> dict[str, int]:
    """Series a sumar/quitar por musculo para la semana `objetivo`, acumulando las
    semanas YA terminadas del mesociclo en curso (de inicio_meso a objetivo)."""
    if fb.empty:
        return {}
    m = fb[(fb["tipo"] == "musculo")
           & (fb["fecha"] >= pd.Timestamp(inicio_meso))
           & (fb["fecha"] < pd.Timestamp(objetivo))]
    if m.empty:
        return {}
    m = m.assign(semana=m["fecha"].dt.to_period("W-SUN"))
    total: dict[str, int] = {}
    for (musculo, _), g in m.groupby(["clave", "semana"]):
        total[musculo] = total.get(musculo, 0) + _delta_semana(g)
    return {k: max(AJUSTE_MIN, min(AJUSTE_MAX, v)) for k, v in total.items() if v}


def dolor_por_ejercicio(fb: pd.DataFrame, objetivo: date) -> dict[str, int]:
    """Sesiones (fechas distintas) con dolor articular por ejercicio en la ventana."""
    if fb.empty:
        return {}
    d = fb[(fb["tipo"] == "ejercicio") & (fb["dolor"] == 1)
           & (fb["fecha"] >= pd.Timestamp(objetivo - timedelta(days=VENTANA_DOLOR)))
           & (fb["fecha"] < pd.Timestamp(objetivo))]
    return {_norm(k): int(g["fecha"].nunique()) for k, g in d.groupby("clave")}


def _por_nombre() -> dict[str, db.Ejercicio]:
    return {_norm(e.nombre): e for e in db.EJERCICIOS}


def sustituir_por_dolor(plan: list, dolor: dict[str, int]) -> tuple[list, list[str]]:
    """Cambia los ejercicios con dolor articular repetido por otro del MISMO
    patron que encaje en su bloque y no este ya ese dia. Antes que el resto de
    la logica: el peso del sustituto sale del historial o de estimar_peso."""
    if not dolor:
        return plan, []
    cat = _por_nombre()
    usados_dia: dict[int, set[str]] = {}
    for f in plan:
        usados_dia.setdefault(f.dia, set()).add(_norm(f.ejercicio))
    cambio: dict[tuple[int, str], str] = {}
    avisos: list[str] = []
    nuevo = []
    for f in plan:
        n = _norm(f.ejercicio)
        clave = (f.dia, n)
        if dolor.get(n, 0) >= DOLOR_PARA_CAMBIAR and clave not in cambio:
            ej = cat.get(n)
            letra = (f.bloque or "")[:1]
            if ej is not None:
                for alt in db.por_patron(ej.patron, letra if letra in "ABC" else None):
                    if _norm(alt.nombre) not in usados_dia[f.dia] and _norm(alt.nombre) not in dolor:
                        cambio[clave] = alt.nombre
                        usados_dia[f.dia].add(_norm(alt.nombre))
                        avisos.append(f"Dia {f.dia}: {f.ejercicio} -> {alt.nombre} "
                                      f"(dolor articular en {dolor[n]} sesiones)")
                        break
        if clave in cambio:
            nota = (f"Cambiado por {f.ejercicio}: reportaste dolor articular {dolor[n]} veces. "
                    f"{f.notas or ''}").strip()
            f = replace(f, ejercicio=cambio[clave], notas=nota[:255])
        nuevo.append(f)
    return nuevo, avisos


def aplicar_ajustes(filas: list[dict], ajustes: dict[str, int], dolor: dict[str, int]) -> list[str]:
    """Suma/quita series (en sitio) a los ejercicios de VOLUMEN de cada musculo,
    repartidas por turnos entre sus ejercicios de la semana. Devuelve avisos."""
    if not ajustes and not dolor:
        return []
    cat = _por_nombre()
    avisos: list[str] = []
    extra_dia: dict[int, int] = {}

    def _musculo(f) -> str | None:
        e = cat.get(_norm(db.nombre_canonico(f["ejercicio"])))
        return e.musculo if e else None

    def _es_volumen(f) -> bool:
        t = _norm(f["tecnica"])
        return (any(k in t for k in _VOLUMEN)
                and (f["bloque"] or "")[:4] in ("A - ", "B - ", "C - "))

    # dolor puntual (1 vez): sin series extra y con aviso en la nota
    for f in filas:
        if dolor.get(_norm(f["ejercicio"]), 0) == 1:
            f["notas"] = (f"Reportaste molestia ARTICULAR aqui: tecnica impecable y, si "
                          f"vuelve, usa 🔄 alternativas (a la 2da el motor lo cambia). "
                          f"{f['notas'] or ''}").strip()[:255]

    for musculo, k in sorted(ajustes.items()):
        cand = [f for f in filas if _musculo(f) == musculo and _es_volumen(f)
                and dolor.get(_norm(f["ejercicio"]), 0) == 0]
        if not cand:
            continue
        hechos, i, vueltas = 0, 0, 0
        while hechos < abs(k) and vueltas < len(cand) * 3:
            f = cand[i % len(cand)]
            i += 1
            vueltas += 1
            s = int(f["series_objetivo"])
            if k > 0 and s < SERIES_MAX_FILA and extra_dia.get(f["dia_semana"], 0) < EXTRA_MAX_DIA:
                f["series_objetivo"] = s + 1
                extra_dia[f["dia_semana"]] = extra_dia.get(f["dia_semana"], 0) + 1
                hechos += 1
            elif k < 0 and s > SERIES_MIN_FILA:
                f["series_objetivo"] = s - 1
                hechos += 1
        if hechos:
            signo = "+" if k > 0 else "-"
            motivo = ("te recuperas de sobra" if k > 0
                      else "dolor muscular que no se va o carga excesiva")
            avisos.append(f"{musculo}: {signo}{hechos} series ({motivo})")
            for f in cand:
                if f.get("_marcado"):
                    continue
                f["_marcado"] = True
                f["notas"] = (f"Volumen {musculo} {signo}{hechos} por tu encuesta ({motivo}). "
                              f"{f['notas'] or ''}").strip()[:255]
    for f in filas:
        f.pop("_marcado", None)
    return avisos


def inicio_mesociclo(objetivo: date, semana: int) -> date:
    """Lunes en que empezo el mesociclo de la semana `objetivo` (semana 1-5)."""
    return objetivo - timedelta(weeks=max(1, min(5, semana)) - 1)


CSV_FEEDBACK = "feedback.csv"   # copia local para el dashboard (la escribe exportar_local)


def ajustes_para(fb: pd.DataFrame, objetivo: date, inicio: date) -> tuple[dict[str, int], dict[str, int]]:
    """(ajustes por musculo, dolor por ejercicio) para la semana `objetivo`.
    Lo usan el motor y el dashboard: asi los dos muestran el MISMO plan."""
    from planificar import semana_mesociclo
    semana_cal = semana_mesociclo(objetivo, inicio)
    return (ajustes_por_musculo(fb, inicio_mesociclo(objetivo, semana_cal), objetivo),
            dolor_por_ejercicio(fb, objetivo))


def leer_csv(carpeta) -> pd.DataFrame:
    import pathlib
    ruta = pathlib.Path(carpeta) / CSV_FEEDBACK
    if not ruta.exists():
        return pd.DataFrame()
    try:
        return normalizar(pd.read_csv(ruta))
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


# ── Bienestar diario ("¿Como te sientes hoy?" y "¿Como dormiste?") ──────────
# Los cuestionarios subjetivos de bienestar reflejan la carga de entrenamiento
# MEJOR que los marcadores objetivos (Saw, Main & Gastin 2016, revision
# sistematica, Br J Sports Med). Un dia malo suelto es ruido; varios en la misma
# semana son la senal. Escala: 1 bien | 2 normal/regular | 3 sin energia/mal.
DIAS_MALOS_AVISO = 2
DIAS_MALOS_DELOAD = 3


def dias_malos(fb: pd.DataFrame, objetivo: date, dias: int = 7) -> int:
    """Dias de la ultima semana con energia o sueno en 3 (sin energia / mal)."""
    if fb.empty or "tipo" not in fb:
        return 0
    d = fb[(fb["tipo"] == "dia") & (fb["carga"] == 3)
           & (fb["fecha"] >= pd.Timestamp(objetivo - timedelta(days=dias)))
           & (fb["fecha"] < pd.Timestamp(objetivo))]
    return int(d["fecha"].nunique())


# ── "Usar siempre": preferencias de ejercicio ────────────────────────────────
CSV_PREFERENCIAS = "preferencias.csv"   # copia local para el dashboard (exportar_local)


def descargar_preferencias(sesion, base_url: str, token: str) -> dict[str, str]:
    """{original (normalizado): reemplazo}. Sin endpoint o sin red: {} (plan normal)."""
    try:
        r = sesion.get(f"{base_url}/get_preferencias.php", headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        filas = r.json().get("preferencias") or []
    except Exception as e:  # noqa: BLE001
        print(f"Preferencias no disponibles ({e.__class__.__name__}): plan sin cambios fijos.")
        return {}
    return {_norm(f["original"]): str(f["reemplazo"]).strip() for f in filas if f.get("original") and f.get("reemplazo")}


def leer_preferencias_csv(carpeta) -> dict[str, str]:
    import pathlib
    ruta = pathlib.Path(carpeta) / CSV_PREFERENCIAS
    if not ruta.exists():
        return {}
    try:
        d = pd.read_csv(ruta)
        return {_norm(o): str(r).strip() for o, r in zip(d["original"], d["reemplazo"])}
    except Exception:  # noqa: BLE001
        return {}


def aplicar_preferencias(plan: list, prefs: dict[str, str]) -> tuple[list, list[str]]:
    """Cambia cada ejercicio por el que elegiste "para siempre" en la app.
    Solo si el reemplazo existe en el catalogo, es del MISMO patron de movimiento
    y no esta ya ese dia (evita un dia con dos veces el mismo ejercicio)."""
    if not prefs:
        return plan, []
    cat = _por_nombre()

    def _comparten(a, b) -> bool:
        # el plan trae las variantes de varias semanas del mesociclo: solo choca
        # con filas de las MISMAS semanas (None = todas)
        return a is None or b is None or bool(set(a) & set(b))

    avisos: list[str] = []
    descartadas: set[str] = set()
    nuevo = list(plan)
    for i, f in enumerate(plan):
        n = _norm(f.ejercicio)
        reemplazo = prefs.get(n)
        if not reemplazo:
            continue
        orig, alt = cat.get(n), cat.get(_norm(reemplazo))
        if orig is None or alt is None or alt.patron != orig.patron:
            if n not in descartadas:
                descartadas.add(n)
                avisos.append(f"Preferencia ignorada: {reemplazo} no sustituye a {f.ejercicio} "
                              f"(no esta en el catalogo o es otro patron de movimiento)")
            continue
        choca = any(g.dia == f.dia and _norm(g.ejercicio) == _norm(alt.nombre) and _comparten(g.semanas, f.semanas)
                    for g in nuevo)
        if not choca:
            nota = f"PREFERENCIA: usas {alt.nombre} en lugar de {f.ejercicio}. {f.notas or ''}".strip()
            nuevo[i] = replace(f, ejercicio=alt.nombre, notas=nota[:255])
    return nuevo, avisos

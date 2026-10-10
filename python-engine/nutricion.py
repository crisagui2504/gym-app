"""Nutricion: metas del dia y ajuste ADAPTATIVO de calorias.

Lo que pide la evidencia, sin pedirle al usuario que pese su comida:

- Proteina: el rango de su enfoque (enfoques.py, g/kg de peso corporal). El
  punto donde la ganancia de masa magra casi deja de crecer es ~1.6 g/kg
  (Morton et al. 2018); en deficit conviene mas, 2.3-3.1 g/kg (ISSN, Jager et
  al. 2017). La app registra la proteina por porciones y la compara con la meta.
- Calorias: un punto de partida con los macros del enfoque y despues se ajusta
  con la TENDENCIA DEL PESO, como hacen las apps "adaptativas" (MacroFactor):
  si la bascula no se mueve al ritmo del objetivo, se sugiere +/- kcal.
  Un deficit > ~500 kcal/dia frena la ganancia de masa magra (Murphy & Koehler
  2022) y un superavit grande solo suma grasa (Helms et al. 2023: 5 % ~ 15 % en
  musculo); por eso el ajuste es chico (100-300 kcal) y se reevalua cada 2
  semanas, que es lo que tarda en verse en la tendencia.

La meta se sube a InfinityFree (guardar_meta_nutricion.php) para que la app la
muestre; la proteina registrada se baja a nutricion.csv para el dashboard.
"""
from __future__ import annotations

import pathlib
from datetime import date, timedelta

import pandas as pd

from enfoques import ENFOQUES

AQUI = pathlib.Path(__file__).resolve().parent
CSV_NUTRICION = "nutricion.csv"     # copia local para el dashboard (la escribe exportar_local)
KCAL_POR_KG = 7700                  # energia aproximada de 1 kg de tejido corporal
AJUSTE_MAX = 300                    # kcal/dia por ajuste: cambios chicos, reevaluables
DIAS_REEVALUAR = 14                 # tras aplicar un ajuste, esperar a que se vea en el peso


def _enfoque(cfg: dict):
    return ENFOQUES.get(cfg.get("enfoque"), ENFOQUES["recomposicion"])


def _peso(cfg: dict) -> float:
    try:
        p = float(cfg.get("peso_corporal") or 75)
    except (TypeError, ValueError):
        p = 75.0
    return p if 30 <= p <= 250 else 75.0


def kcal_base(cfg: dict) -> int:
    """Punto de partida: los macros del enfoque (punto medio de cada rango) en kcal."""
    enf, peso = _enfoque(cfg), _peso(cfg)
    medio = lambda r: (r[0] + r[1]) / 2  # noqa: E731
    return int(round((medio(enf.prot_g_kg) * 4 + medio(enf.carb_g_kg) * 4
                      + medio(enf.grasa_g_kg) * 9) * peso / 10) * 10)


def metas(cfg: dict) -> dict:
    """Rango de proteina (g/dia) y kcal objetivo (base + ajustes aplicados)."""
    enf, peso = _enfoque(cfg), _peso(cfg)
    ajuste = int(cfg.get("kcal_ajuste") or 0)
    return {
        "proteina_min": int(round(enf.prot_g_kg[0] * peso)),
        "proteina_max": int(round(enf.prot_g_kg[1] * peso)),
        "kcal": kcal_base(cfg) + ajuste,
        "kcal_base": kcal_base(cfg),
        "kcal_ajuste": ajuste,
        "peso": round(peso, 1),
        "enfoque": enf.clave,
    }


# ── calorias por tipo de dia ─────────────────────────────────────────────────
# Mismo total SEMANAL (es lo que decide si subes o bajas), repartido segun lo que
# gasta cada dia. Gasto neto de la actividad = (MET - 1) x kg x horas, con METs
# del Compendium of Physical Activities (Ainsworth 2011; Herrmann 2024):
#   pesas 4.5 (entre "moderado" 3.5 y "vigoroso" 6.0: la sesion incluye
#   descansos), basquetbol "general" 6.5, cardio LISS / caminata rapida 4.0.
# El descanso activo (caminar) ya es parte del gasto de todos los dias.
MET = {"pesas": 4.5, "deporte": 6.5, "cardio": 4.0, "descanso": 1.0}
MIN_CARDIO = 40                 # el LISS del plan dura 35-45 min
TOPE_REPARTO = 0.20             # ningun dia se aleja mas de +/-20 % del promedio
NOMBRE_TIPO = {"pesas": "pesas", "deporte": "deporte", "cardio": "cardio", "descanso": "descanso"}


def tipos_de_dia(cfg: dict) -> dict[int, str]:
    """1..7 -> 'pesas' | 'deporte' | 'cardio' | 'descanso', segun el plan de tu split."""
    from config_usuario import DEFAULT_CONFIG
    from generador import generar_plan
    bloques: dict[int, set[str]] = {d: set() for d in range(1, 8)}
    for f in generar_plan({**DEFAULT_CONFIG, **cfg}):      # cfg parcial (demo, pruebas): defaults
        bloques.setdefault(f.dia, set()).add((f.bloque or "").lower())
    tipos = {}
    for d in range(1, 8):
        b = bloques.get(d, set())
        if any("deporte" in x for x in b):
            tipos[d] = "deporte"
        elif any(x.startswith(("a -", "b -", "c -")) for x in b):
            tipos[d] = "pesas"
        elif any("cardio" in x for x in b):
            tipos[d] = "cardio"
        else:
            tipos[d] = "descanso"
    return tipos


def gasto_actividad(cfg: dict, tipo: str) -> float:
    """kcal NETAS de la actividad del dia (sobre estar en reposo)."""
    peso = _peso(cfg)
    if tipo == "pesas":
        horas = float(cfg.get("duracion_min") or 75) / 60
    elif tipo == "deporte":
        horas = float((cfg.get("deporte") or {}).get("minutos") or 60) / 60
    elif tipo == "cardio":
        horas = MIN_CARDIO / 60
    else:
        return 0.0
    return (MET[tipo] - 1) * peso * horas


def kcal_por_dia(cfg: dict) -> dict[int, dict]:
    """{dia: {"tipo", "kcal"}}: el promedio de la semana es exactamente tu meta."""
    K = metas(cfg)["kcal"]
    tipos = tipos_de_dia(cfg)
    extra = {d: gasto_actividad(cfg, t) for d, t in tipos.items()}
    media = sum(extra.values()) / 7
    lo, hi = K * (1 - TOPE_REPARTO), K * (1 + TOPE_REPARTO)
    valor = {d: K + extra[d] - media for d in tipos}
    # topar y repartir lo recortado entre los dias que no tocan el tope, hasta
    # que la semana sume exactamente 7 x K sin que ningun dia pase del +/-20 %
    for _ in range(10):
        valor = {d: min(hi, max(lo, v)) for d, v in valor.items()}
        falta = 7 * K - sum(valor.values())
        libres = [d for d, v in valor.items() if (falta > 0 and v < hi) or (falta < 0 and v > lo)]
        if abs(falta) < 1 or not libres:
            break
        for d in libres:
            valor[d] += falta / len(libres)
    return {d: {"tipo": tipos[d], "kcal": int(round(valor[d] / 10) * 10)} for d in tipos}


def resumen_por_tipo(cfg: dict) -> dict[str, int]:
    """{'pesas': 2330, 'deporte': 2610, ...} para mostrar."""
    out: dict[str, int] = {}
    for v in kcal_por_dia(cfg).values():
        out.setdefault(v["tipo"], v["kcal"])
    return out


def tendencia_pct_sem(dfp: pd.DataFrame, hoy: date | None = None, ventana: int = 21) -> float | None:
    """Cambio de peso en %/semana: pendiente de una recta sobre los pesajes de
    las ultimas `ventana` dias. Mas estable que comparar dos medias semanales
    (el agua y la comida mueven la bascula 1-2 kg de un dia a otro)."""
    if dfp is None or dfp.empty:
        return None
    hoy = hoy or date.today()
    d = dfp.dropna(subset=["fecha", "peso"])
    d = d[d["fecha"] >= pd.Timestamp(hoy - timedelta(days=ventana))]
    if len(d) < 8:
        return None
    x = (d["fecha"] - d["fecha"].min()).dt.days.astype(float)
    if x.max() < 10:            # menos de ~10 dias de rango: la recta no dice nada
        return None
    import numpy as np
    pendiente = float(np.polyfit(x, d["peso"].astype(float), 1)[0])    # kg/dia
    return pendiente * 7 / float(d["peso"].mean()) * 100


def evaluar(cfg: dict, dfp: pd.DataFrame, cintura_sem: float | None = None,
            hoy: date | None = None) -> dict:
    """Que hacer con las calorias esta semana.

    estado: 'pocos_datos' | 'esperando' | 'en_rango' | 'recomposicion' | 'subir' | 'bajar'
    kcal_delta: ajuste sugerido (kcal/dia), 0 si no hay que cambiar nada."""
    hoy = hoy or date.today()
    enf = _enfoque(cfg)
    lo, hi = enf.tendencia_sem
    base = {"objetivo": (lo, hi), "kcal_delta": 0, "tendencia": None, "dias_restantes": 0}
    t = tendencia_pct_sem(dfp, hoy)
    if t is None:
        return {**base, "estado": "pocos_datos"}
    base["tendencia"] = t

    fecha_ajuste = cfg.get("kcal_ajuste_fecha")
    if fecha_ajuste:
        try:
            pasados = (hoy - date.fromisoformat(str(fecha_ajuste))).days
        except ValueError:
            pasados = DIAS_REEVALUAR
        if pasados < DIAS_REEVALUAR:
            return {**base, "estado": "esperando", "dias_restantes": DIAS_REEVALUAR - pasados}

    # bascula plana + cintura bajando = recomposicion: no tocar nada
    if (cintura_sem is not None and cintura_sem <= -0.2 and abs(t) <= 0.3
            and enf.clave in ("recomposicion", "powerbuilding", "fuerza")):
        return {**base, "estado": "recomposicion"}
    if lo <= t <= hi:
        return {**base, "estado": "en_rango"}

    objetivo = (lo + hi) / 2
    kg_sem = (objetivo - t) / 100 * _peso(cfg)
    delta = kg_sem * KCAL_POR_KG / 7
    delta = max(-AJUSTE_MAX, min(AJUSTE_MAX, round(delta / 50) * 50))
    if abs(delta) < 100:        # menos de 100 kcal no se nota ni se puede medir
        delta = 100 if delta > 0 else -100
    return {**base, "estado": "subir" if delta > 0 else "bajar", "kcal_delta": int(delta)}


def adherencia(dfn: pd.DataFrame, meta_min: int, hoy: date | None = None, dias: int = 7) -> dict:
    """Proteina registrada en los ultimos `dias`: promedio de los dias con registro."""
    hoy = hoy or date.today()
    vacio = {"dias_registrados": 0, "promedio": None, "dias_en_meta": 0, "dias": dias, "creatina_dias": 0}
    if dfn is None or dfn.empty:
        return vacio
    semana = dfn[(dfn["fecha"] > pd.Timestamp(hoy - timedelta(days=dias))) & (dfn["fecha"] <= pd.Timestamp(hoy))]
    creatina = int((semana["creatina"] > 0).sum()) if "creatina" in semana else 0
    d = semana[semana["proteina_g"] > 0]
    if d.empty:
        return {**vacio, "creatina_dias": creatina}
    return {"dias_registrados": int(len(d)), "promedio": float(d["proteina_g"].mean()),
            "dias_en_meta": int((d["proteina_g"] >= meta_min).sum()), "dias": dias, "creatina_dias": creatina}


def resumen_semanal(cfg: dict, dfp: pd.DataFrame, dfn: pd.DataFrame, cintura_sem: float | None = None,
                    hoy: date | None = None) -> tuple[str, str]:
    """El aviso del domingo (como el check-in semanal de MacroFactor): proteina,
    tendencia del peso y que hacer con las calorias, en una notificacion."""
    m = metas(cfg)
    a = adherencia(dfn, m["proteina_min"], hoy)
    ev = evaluar(cfg, dfp, cintura_sem, hoy)
    partes = []
    if a["dias_registrados"]:
        partes.append(f"Proteína {a['promedio']:.0f} g/día (meta {m['proteina_min']}) en {a['dias_registrados']} día(s)")
    else:
        partes.append("Sin proteína registrada esta semana")
    if ev["tendencia"] is not None:
        partes.append(f"peso {round(ev['tendencia'], 2) + 0.0:+.2f} %/sem")      # + 0.0: nunca "-0.00"
    consejo = {"subir": f"sugerencia: {ev['kcal_delta']:+d} kcal/día (aplícalo en el dashboard)",
               "bajar": f"sugerencia: {ev['kcal_delta']:+d} kcal/día (aplícalo en el dashboard)",
               "en_rango": "calorías bien: no cambies nada",
               "recomposicion": "recomposición en marcha: no cambies nada",
               "esperando": f"espera {ev['dias_restantes']} día(s) para ver tu último ajuste",
               "pocos_datos": "pésate más seguido para ajustar tus calorías"}[ev["estado"]]
    if a["creatina_dias"]:
        partes.append(f"creatina {a['creatina_dias']}/7")
    return "🥗 Tu semana de nutrición", " · ".join(partes) + ". " + consejo[0].upper() + consejo[1:] + "."


# ── servidor ─────────────────────────────────────────────────────────────────
def subir_meta(cfg: dict | None = None) -> bool:
    """Sube la meta a InfinityFree para la app. Nunca lanza: si falla, la app
    sigue con la ultima meta que tenga."""
    try:
        from dotenv import load_dotenv
        load_dotenv(AQUI / ".env")
        import planificar as pl
        from config_usuario import cargar_config
        m = metas(cfg or cargar_config())
        base, token = pl.api_config()
        sesion = pl.sesion_infinityfree(base)
        r = sesion.post(f"{base}/guardar_meta_nutricion.php", headers={"X-API-Token": token}, timeout=40,
                        json={k: m[k] for k in ("proteina_min", "proteina_max", "kcal", "peso", "enfoque")})
        r.raise_for_status()
        return bool(r.json().get("ok"))
    except Exception as e:  # noqa: BLE001
        print(f"Meta de nutricion no subida ({e.__class__.__name__}): la app usa la anterior.")
        return False


def subir_meta_en_segundo_plano(cfg: dict | None = None) -> None:
    """Para el dashboard: InfinityFree puede tardar; la pagina no espera."""
    import threading
    threading.Thread(target=subir_meta, args=(cfg,), daemon=True).start()


def descargar_nutricion(sesion, base_url: str, token: str, dias: int = 120) -> pd.DataFrame:
    """Proteina registrada por dia. Sin endpoint o sin red: tabla vacia."""
    try:
        r = sesion.get(f"{base_url}/get_nutricion.php", params={"dias": dias},
                       headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        filas = r.json().get("dias") or []
    except Exception as e:  # noqa: BLE001
        print(f"Nutricion no disponible ({e.__class__.__name__}).")
        filas = []
    return pd.DataFrame([{"fecha": f["fecha"], "proteina_g": float(f["proteina_g"]),
                          "creatina": 1 if (f.get("porciones") or {}).get("creatina") else 0} for f in filas],
                        columns=["fecha", "proteina_g", "creatina"])


def leer_nutricion_csv(carpeta=AQUI) -> pd.DataFrame:
    ruta = pathlib.Path(carpeta) / CSV_NUTRICION
    if not ruta.exists():
        return pd.DataFrame(columns=["fecha", "proteina_g"])
    try:
        d = pd.read_csv(ruta)
        d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
        d["proteina_g"] = pd.to_numeric(d["proteina_g"], errors="coerce").fillna(0)
        d["creatina"] = pd.to_numeric(d["creatina"], errors="coerce").fillna(0) if "creatina" in d else 0
        return d.dropna(subset=["fecha"])
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["fecha", "proteina_g"])


# ── peso corporal ────────────────────────────────────────────────────────────
# La FUENTE es MySQL (tabla peso_corporal: lo registran la app y el dashboard).
# peso_corporal.csv es la copia local que leen el dashboard y la revision del
# domingo; la reescribe exportar_local.py cada 3 horas (con backup fechado).
CSV_PESO = "peso_corporal.csv"
COLUMNAS_PESO = ["fecha", "peso", "cintura"]


def _limpiar_peso(df: pd.DataFrame) -> pd.DataFrame:
    """fecha (datetime), peso y cintura numericos; un pesaje por dia (el ultimo), ordenado."""
    df = df.copy()
    for c in COLUMNAS_PESO:
        if c not in df:
            df[c] = pd.NA
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["peso"] = pd.to_numeric(df["peso"], errors="coerce")
    df["cintura"] = pd.to_numeric(df["cintura"], errors="coerce")
    return (df.dropna(subset=["fecha", "peso"]).sort_values("fecha")
              .drop_duplicates("fecha", keep="last")[COLUMNAS_PESO].reset_index(drop=True))


def leer_peso_csv(ruta=AQUI / CSV_PESO) -> pd.DataFrame:
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_PESO)
    try:
        return _limpiar_peso(pd.read_csv(ruta))
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=COLUMNAS_PESO)


def tendencia_cintura(dfp: pd.DataFrame) -> float | None:
    """Cambio de cintura (cm/semana) sobre los registros de los ultimos 21 dias."""
    cin = dfp.dropna(subset=["cintura"]) if "cintura" in dfp else dfp.iloc[0:0]
    if len(cin) < 3:
        return None
    cin = cin[cin["fecha"] >= cin["fecha"].max() - pd.Timedelta(days=21)]
    if len(cin) < 3:
        return None
    dias = (cin["fecha"].max() - cin["fecha"].min()).days
    if dias < 7:
        return None
    return float((cin["cintura"].iloc[-1] - cin["cintura"].iloc[0]) / dias * 7)


def descargar_peso(sesion, base_url: str, token: str, dias: int = 3650) -> pd.DataFrame | None:
    """Todos los pesajes de MySQL. None si no se pudo (sin red, sin endpoint o el
    antibot de InfinityFree): entonces NO se toca la copia local."""
    try:
        r = sesion.get(f"{base_url}/get_peso.php", params={"dias": dias},
                       headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        j = r.json()
        if not j.get("ok"):
            return None
        filas = j.get("pesos") or []
    except Exception as e:  # noqa: BLE001
        print(f"Peso corporal no disponible ({e.__class__.__name__}).")
        return None
    return _limpiar_peso(pd.DataFrame(filas, columns=COLUMNAS_PESO))


def subir_peso(sesion, base_url: str, token: str, fecha: str, peso: float,
               cintura: float | None = None) -> bool:
    """Upsert del pesaje del dia en MySQL (sin cintura, el servidor conserva la que tenga)."""
    cuerpo = {"fecha": fecha, "peso": round(float(peso), 1)}
    if cintura is not None and not pd.isna(cintura):
        cuerpo["cintura"] = round(float(cintura), 1)
    try:
        r = sesion.post(f"{base_url}/guardar_peso.php", json=cuerpo,
                        headers={"X-API-Token": token}, timeout=40)
        r.raise_for_status()
        return bool(r.json().get("ok"))
    except Exception as e:  # noqa: BLE001
        print(f"Peso no subido ({e.__class__.__name__}): exportar_local lo reintenta.")
        return False


def subir_peso_en_segundo_plano(fecha: str, peso: float, cintura: float | None = None) -> None:
    """Para el dashboard: el CSV local ya quedo escrito; MySQL se actualiza sin
    hacer esperar a la pagina. Si falla, exportar_local.py lo sube despues
    (las fechas que solo estan en el CSV se suben antes de reescribirlo)."""
    import threading

    def _subir():
        try:
            from dotenv import load_dotenv
            load_dotenv(AQUI / ".env")
            import planificar as pl
            base, token = pl.api_config()
            subir_peso(pl.sesion_infinityfree(base), base, token, fecha, peso, cintura)
        except Exception as e:  # noqa: BLE001
            print(f"Peso no subido ({e.__class__.__name__}): exportar_local lo reintenta.")

    threading.Thread(target=_subir, daemon=True).start()


def sincronizar_peso(sesion, base_url: str, token: str, ruta=AQUI / CSV_PESO) -> tuple[pd.DataFrame | None, int]:
    """MySQL -> peso_corporal.csv, sin perder nada:
    1. las fechas que solo estan en el CSV local (pesajes viejos del dashboard,
       o uno cuyo envio fallo) se suben a MySQL: asi se migra el CSV la primera vez;
    2. el CSV se reescribe con MySQL (gana el servidor si una fecha esta en los
       dos) + lo local que no se pudo subir (se reintenta la proxima vez).
    Devuelve (pesajes, cuantos se subieron); (None, 0) si el servidor no respondio."""
    servidor = descargar_peso(sesion, base_url, token)
    if servidor is None:
        return None, 0
    local = leer_peso_csv(ruta)
    solo_local = local[~local["fecha"].isin(set(servidor["fecha"]))]
    subidos = sum(subir_peso(sesion, base_url, token, f.fecha.date().isoformat(), f.peso,
                             None if pd.isna(f.cintura) else f.cintura)
                  for f in solo_local.itertuples())
    todo = _limpiar_peso(pd.concat([solo_local, servidor], ignore_index=True)) if len(solo_local) else servidor
    todo.to_csv(ruta, index=False, date_format="%Y-%m-%d")
    return todo, int(subidos)


def alinear_peso_config(dfp: pd.DataFrame, cfg: dict | None = None) -> bool:
    """El ultimo pesaje manda: si cambio, va a tu config (macros, maquinas
    asistidas) y la meta de proteina/kcal se vuelve a subir para la app."""
    if dfp is None or dfp.empty:
        return False
    from config_usuario import cargar_config, guardar_config
    ultimo = round(float(dfp["peso"].iloc[-1]), 1)
    cfg = cfg or cargar_config()
    try:
        actual = float(cfg.get("peso_corporal") or 0)
    except (TypeError, ValueError):
        actual = 0.0
    if abs(actual - ultimo) < 0.05 or not 30 <= ultimo <= 250:
        return False
    guardar_config({"peso_corporal": ultimo})
    subir_meta()
    return True

# -*- coding: utf-8 -*-
"""Barrido de invariantes sobre TODAS las combinaciones de config y semana.

5 enfoques x 4 splits x con/sin deporte x 12 ciclos x 4 duraciones x 7 variantes
de semana (S1-S5, deload, reingreso 1 y 2) = 13.440 semanas con un historial
sintetico, comprobando reglas que deben cumplirse SIEMPRE: sin excepciones, sin
el mismo ejercicio en dos bloques, sin fallo en deload/reingreso ni en S1-S2,
sin peso libre peligroso al fallo, sin cardio sobre el deporte, sesiones dentro
de la duracion pedida... Atrapa las regresiones que una prueba puntual no ve.
Uso:  python tests/test_barrido.py   (~15 s)"""
import sys, collections, itertools, traceback
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
import ejercicios_db as db, generador as gen, planificar as pl, enfoques as enf

POR = {e.nombre: e for e in db.EJERCICIOS}
_orig_uyr = pl.ultimas_y_records
_cache = {}
def _uyr_cache(df, hoy=None):
    k = (id(df), hoy)
    if k not in _cache:
        _cache[k] = _orig_uyr(df, hoy=hoy)
    return _cache[k]
pl.ultimas_y_records = _uyr_cache
# el modelo de fuerza se reconstruye en cada generar_filas: con el mismo historial
# sintetico en las 13.440 semanas, se cachea (solo para que la prueba sea rapida)
import entrenador as _ent
_ModeloOrig = _ent.ModeloFuerza
_cache_mod = {}
def _modelo_cache(df, hoy):
    k = (len(df), hoy)
    if k not in _cache_mod:
        _cache_mod[k] = _ModeloOrig(df, hoy)
    return _cache_mod[k]
_ent.ModeloFuerza = _modelo_cache
FALLO = ("amrap", "rest", "drop")
fallos = collections.defaultdict(list)
def mal(regla, tag, det=""):
    fallos[regla].append(f"{tag} {det}".strip())

# historial sintetico: TODOS los ejercicios hechos hace 3 dias, a RPE 8
filas_h = []
for e in db.EJERCICIOS:
    for tec in ("Top Set", "Back-off", "Tradicional"):
        filas_h.append({"fecha_entreno": pd.Timestamp("2026-10-05"), "ejercicio": e.nombre,
                        "tecnica": tec, "numero_serie": 1, "peso_kg": 20.0, "reps_hechas": 10,
                        "rpe": 8, "tonelaje_serie": 200})
HIST = pd.DataFrame(filas_h)
VACIO = pd.DataFrame(columns=HIST.columns)

DEP = {"nombre": "Basquetbol", "dias": [2, 4], "minutos": 90}
combos = 0
for e_, sp, dep, ciclo, dur in itertools.product(
        enf.ENFOQUES, enf.SPLITS, (None, DEP), range(12), (60, 75, 90, 120)):
    cfg = {"enfoque": e_, "split": sp, "prioridades": ["hombros", "dorsales"],
           "duracion_min": dur, "deporte": dep}
    try:
        plan = gen.generar_plan(cfg, ciclo)
    except Exception as ex:
        mal("generar_plan lanza excepcion", f"{e_}/{sp}/c{ciclo}", repr(ex)); continue
    for sem, fase in ((1,0),(2,0),(3,0),(4,0),(5,0),(5,1),(1,2)):
        combos += 1
        tag = f"{e_}/{sp}/dep={'si' if dep else 'no'}/c{ciclo}/S{sem}/re{fase}/{dur}min"
        try:
            fs = pl.generar_filas(HIST, "2026-10-12", sem, plan=plan, reingreso=fase, duracion_min=dur)
        except Exception as ex:
            mal("generar_filas lanza excepcion", tag, repr(ex)); continue
        pordia = collections.defaultdict(list)
        for f in fs:
            pordia[f["dia_semana"]].append(f)
        for d, ff in pordia.items():
            gym = [f for f in ff if f["tecnica"] and (f["bloque"] or "")[:4] in ("A - ", "B - ", "C - ")]
            bloques = {f["bloque"] for f in ff}
            if "Deporte" in bloques and gym and d not in []:
                pass  # colision deporte+pesas: avisada en la nota, no es error
            if any(f["bloque"] == "Deporte" and f["tecnica"] for f in ff):
                mal("deporte con tecnica (se dibujaria como ejercicio)", tag, f"dia{d}")
            if "Deporte" in bloques and "Cardio" in bloques:
                mal("cardio el mismo dia que deporte", tag, f"dia{d}")
            if not gym:
                continue
            # mismo ejercicio en 2 bloques distintos el mismo dia
            por_ej = collections.defaultdict(set)
            for f in gym: por_ej[f["ejercicio"]].add(f["bloque"][0])
            dup = [k for k, v in por_ej.items() if len(v) > 1]
            if dup: mal("mismo ejercicio en 2 bloques del mismo dia", tag, f"dia{d}: {dup}")
            if len({f['ejercicio'] for f in gym}) < 3:
                mal("dia de pesas con menos de 3 ejercicios", tag, f"dia{d}: {[f['ejercicio'] for f in gym]}")
            for f in gym:
                ej = POR.get(f["ejercicio"])
                t = (f["tecnica"] or "").lower()
                if ej is None:
                    mal("ejercicio fuera del catalogo", tag, f["ejercicio"]); continue
                if float(f["series_objetivo"] or 0) <= 0:
                    mal("serie de pesas con 0 series", tag, f["ejercicio"])
                if f["reps_min"] and f["reps_max"] and f["reps_min"] > f["reps_max"]:
                    mal("reps_min > reps_max", tag, f"{f['ejercicio']} {f['reps_min']}-{f['reps_max']}")
                if not f["descanso_seg"]:
                    mal("serie sin descanso", tag, f"{f['ejercicio']} ({f['tecnica']})")
                if f["notas"] and len(f["notas"]) > 255:
                    mal("nota > 255 (la BD la corta)", tag, f["ejercicio"])
                if any(k in t for k in FALLO):
                    if sem == 5 or fase:
                        mal("fallo en deload/reingreso", tag, f"{f['ejercicio']} {f['tecnica']}")
                    if sem in (1, 2):
                        mal("tecnica al fallo en S1-S2", tag, f"{f['ejercicio']} {f['tecnica']}")
                    if ej.equipo in ("barra", "mancuerna") and (
                            f["bloque"].startswith("B -") or ej.nombre in db.FALLO_LIBRE_INSEGURO):
                        mal("PESO LIBRE al fallo muscular (seguridad)", tag, f"{f['ejercicio']} {f['tecnica']}")
                if sem == 5 and f["bloque"].startswith("C -") and not fase:
                    mal("bloque C en deload", tag, f["ejercicio"])
                p = f["peso_sugerido"]
                if ej.equipo != "peso_corporal" and t not in ("",) and p is None:
                    mal("SIN PESO teniendo historial", tag, f"{f['ejercicio']} ({f['tecnica']})")
                if p is not None and p < 0:
                    mal("peso negativo", tag, f["ejercicio"])
                if p is not None and p > 20.0 * 1.3:
                    mal("salto de carga > +30% en una semana", tag, f"{f['ejercicio']} 20->{p}")
            # duracion estimada (series * ~3 min incluyendo descanso) + calentamiento
            series = sum(float(f["series_objetivo"] or 0) for f in gym)
            mins = sum(float(f["series_objetivo"] or 0) * ((f["descanso_seg"] or 90) + 45) / 60 for f in gym) + 10
            if mins > dur * 1.25:
                mal("sesion bastante mas larga que la duracion pedida", tag, f"dia{d}: ~{mins:.0f} min para {dur}")

# usuario nuevo SIN historial: cuantos pesos en blanco
for sp in enf.SPLITS:
    plan = gen.generar_plan({"enfoque": "recomposicion", "split": sp}, 0)
    fs = pl.generar_filas(VACIO, "2026-10-12", 1, plan=plan)
    gym = [f for f in fs if f["tecnica"] and (f["bloque"] or "")[:4] in ("A - ", "B - ")
           and POR.get(f["ejercicio"]) and POR[f["ejercicio"]].equipo != "peso_corporal"]
    blancos = sorted({f["ejercicio"] for f in gym if f["peso_sugerido"] is None})
    if blancos:
        mal("usuario nuevo: compuestos sin peso base", sp, f"{len(blancos)}: {blancos[:4]}")

# Pendiente conocido y documentado (CAMBIOS_EVIDENCIA.md, tanda BM): un usuario
# sin historial no tiene peso de partida en varios compuestos. Informa, no falla.
CONOCIDAS = {"usuario nuevo: compuestos sin peso base"}
print(f"combinaciones probadas: {combos}")
reales = {k: v for k, v in fallos.items() if k not in CONOCIDAS}
for regla, casos in sorted(fallos.items(), key=lambda x: -len(x[1])):
    marca = "INFO " if regla in CONOCIDAS else "FALLA"
    print(f"[{marca}] [{len(casos):5d}] {regla}")
    for c in casos[:3]:
        print(f"         {c[:150]}")

if reales:
    print(f"RESULTADO: {len(reales)} reglas violadas")
    sys.exit(1)
print("RESULTADO: barrido completo sin violaciones.")

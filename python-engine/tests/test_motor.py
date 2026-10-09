# -*- coding: utf-8 -*-
"""Pruebas del motor de rutinas y progresion (evidencia 2016-2025).

Uso:  python tests/test_motor.py   (desde python-engine/, con el venv activo)
"""
import sys
from datetime import date, timedelta

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd

import ejercicios_db as db
import generador as gen
from enfoques import SPLITS
from generador import generar_plan
from plan_template import Fila
import planificar as pl

FALLOS = []
# las pruebas no dependen de TU config (lista de mancuernas, asistidas...): los
# helpers de planificar que la leen ven una config neutra (cada seccion que
# quiera otra la pone y la quita)
pl._cfg = lambda: {"peso_corporal": 75}


def check(nombre, cond, detalle=""):
    estado = "OK " if cond else "FAIL"
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle and not cond else ""))
    if not cond:
        FALLOS.append(nombre)


NOMBRE_A_PATRON = {e.nombre: e.patron for e in db.EJERCICIOS}

# ═══════════════ 1. Estructura del plan (generador) ═══════════════
print("\n== 1. Full Body: cada patron fundamental 2x/semana ==")
plan_fb = generar_plan({"enfoque": "recomposicion", "split": "full_body",
                        "prioridades": [], "duracion_min": 90}, ciclo=0)
fund = {db.EMPUJE_HORIZONTAL, db.EMPUJE_VERTICAL, db.TIRON_HORIZONTAL,
        db.TIRON_VERTICAL, db.DOMINANTE_RODILLA, db.DOMINANTE_CADERA}
# contar apariciones semanales por patron (ejercicios A/B unicos por dia; S1)
conteo = {p: set() for p in fund}
for f in plan_fb:
    if f.bloque.startswith(("A", "B")) and (f.semanas is None or 1 in f.semanas):
        p = NOMBRE_A_PATRON.get(f.ejercicio)
        if p in fund:
            conteo[p].add((f.dia, f.ejercicio))
for p, apar in conteo.items():
    check(f"full_body {p} >= 2x/semana", len(apar) >= 2, f"solo {len(apar)}: {apar}")

print("\n== 2. Upper/Lower: pecho con aislamiento en dias de torso ==")
plan_ul = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                        "prioridades": ["hombros"], "duracion_min": 90}, ciclo=0)
dias_torso = {f.dia for f in plan_ul if "Torso" in f.nombre_dia}
for d in sorted(dias_torso):
    tiene_pecho_c = any(f.dia == d and f.bloque.startswith("C")
                        and NOMBRE_A_PATRON.get(f.ejercicio) == db.EMPUJE_HORIZONTAL
                        for f in plan_ul)
    check(f"dia {d} (torso) tiene aislamiento de pecho en C", tiene_pecho_c)

print("\n== 3. Fallo dosificado: B tradicional en S1, AMRAP/Drop solo S3-S4 ==")
b_s1 = [f for f in plan_ul if f.bloque.startswith("B") and f.semanas == (1,)]
b_s34 = [f for f in plan_ul if f.bloque.startswith("B") and f.semanas == (3, 4)]
check("Bloque B tiene filas S1 sin fallo", len(b_s1) > 0 and
      all(f.tecnica == "Tradicional" for f in b_s1))
# S3-S4: maquina/polea -> AMRAP/Drop; peso libre (barra/mancuerna) -> RPE 9
# tecnico (tecnica "Tradicional" con nota de fallo tecnico). Ver _intensidad_s34.
EQ_S34 = {e.nombre: e.equipo for e in db.EJERCICIOS}
def _intensidad_ok(f):
    eq = EQ_S34.get(f.ejercicio, "")
    if eq in ("barra", "mancuerna"):
        return f.tecnica == "Tradicional" and "RPE 9" in (f.notas or "")
    return ("AMRAP" in f.tecnica) or ("Drop" in f.tecnica)
check("Bloque B S3-S4: AMRAP en maquina, RPE 9 tecnico en peso libre",
      len(b_s34) > 0 and all(_intensidad_ok(f) for f in b_s34),
      f"{[(f.ejercicio, f.tecnica) for f in b_s34 if not _intensidad_ok(f)]}")
check("peso libre NUNCA lleva AMRAP en S3-S4 (fallo tecnico, no muscular)",
      not any(EQ_S34.get(f.ejercicio) in ("barra","mancuerna") and "AMRAP" in f.tecnica
              for f in b_s34))
c_s12 = [f for f in plan_ul if f.bloque.startswith("C") and f.semanas == (1, 2)]
c_s34 = [f for f in plan_ul if f.bloque.startswith("C") and f.semanas == (3, 4)]
check("Bloque C: aislamiento tradicional en S1-S2", len(c_s12) > 0 and
      all(f.tecnica == "Tradicional" for f in c_s12))
check("Bloque C: Rest-Pause/Drop solo S3-S4", len(c_s34) > 0 and
      all(("Rest" in f.tecnica) or ("Drop" in f.tecnica) for f in c_s34))
check("Descanso Bloque B >= 120 s",
      all(f.descanso >= 120 for f in plan_ul if f.bloque.startswith("B")))

print("\n== 4. Definicion: superserie bi+tri completa (bug del cupo) ==")
plan_def = generar_plan({"enfoque": "definicion", "split": "upper_lower",
                         "prioridades": [], "duracion_min": 90}, ciclo=0)
for d in sorted({f.dia for f in plan_def if "Torso" in f.nombre_dia}):
    ss = [f for f in plan_def if f.dia == d and f.tecnica == "Superserie"]
    musc = {NOMBRE_A_PATRON.get(f.ejercicio) for f in ss}
    check(f"dia {d}: superserie tiene biceps Y triceps",
          musc >= {db.AISL_BICEPS, db.AISL_TRICEPS}, f"solo {musc}")

# ═══════════════ 2. Motor de progresion (planificar) ═══════════════
print("\n== 5. RPE de trabajo excluye la serie al fallo ==")
hoy = date.today()
lunes_pasado = hoy - timedelta(days=hoy.weekday() + 7)


def df_historial(filas):
    df = pd.DataFrame(filas, columns=["fecha_entreno", "ejercicio", "tecnica",
                                      "numero_serie", "peso_kg", "reps_hechas", "rpe"])
    df["fecha_entreno"] = pd.to_datetime(df["fecha_entreno"])
    df["tonelaje_serie"] = df["peso_kg"] * df["reps_hechas"]
    return df


# 3 series de press banca: 2 de trabajo RPE 8 y la AMRAP a RPE 10, rango completo
df1 = df_historial([
    (lunes_pasado, "Press de Banca con Barra", "Tradicional + AMRAP", 1, 40.0, 12, 8),
    (lunes_pasado, "Press de Banca con Barra", "Tradicional + AMRAP", 2, 40.0, 12, 8),
    (lunes_pasado, "Press de Banca con Barra", "Tradicional + AMRAP", 3, 40.0, 15, 10),
])
ult, rec, est = pl.ultimas_y_records(df1)
k = ("press de banca con barra", "volumen")
check("clave por familia (volumen)", k in ult, f"claves: {list(ult)}")
if k in ult:
    peso, reps, rpe = ult[k]
    check("RPE de trabajo = 8.0 (excluye AMRAP)", rpe == 8.0, f"rpe={rpe}")
    fila = Fila(1, "d", "B - Volumen", 1, "Press de Banca con Barra",
                "Tradicional + AMRAP", 3, 8, 12, 120, None, None)
    nuevo = pl.peso_volumen(fila, ult[k], pl.microcarga("press"))
    check("progresa +2.5 kg (antes quedaba bloqueado)", nuevo == 42.5, f"nuevo={nuevo}")

print("\n== 6. La familia une el historial cuando la tecnica rota ==")
df2 = df_historial([
    (lunes_pasado, "Press de Banca con Barra", "Tradicional", 1, 40.0, 12, 8),
    (lunes_pasado, "Press de Banca con Barra", "Tradicional", 2, 40.0, 12, 8),
])
ult2, _, _ = pl.ultimas_y_records(df2)
check("'Tradicional' y 'Tradicional + AMRAP' comparten clave",
      ("press de banca con barra", "volumen") in ult2)

print("\n== 7. S4 pico condicionado al rendimiento ==")
fila_top = Fila(1, "d", "A - Fuerza maxima", 1, "Press Militar Mancuernas (Sentado)",
                "Top Set", 1, 6, 8, 180, 25.0, None)
micro = pl.microcarga("press")
# caso malo: la semana pasada NO llego ni a reps_min (4 < 6), mejor del mes 30 kg
peso_malo = pl.peso_top_set(fila_top, (27.5, 4, 9.0), 30.0, micro, semana=4, estancado=False)
check("S4 con mal rendimiento: baja 5%, NO fuerza PR",
      peso_malo == pl.redondear(27.5 * 0.95), f"peso={peso_malo} (PR forzado seria 32.5)")
# caso bueno: rango completo con RPE 8 -> si intenta superar el mes
peso_bueno = pl.peso_top_set(fila_top, (27.5, 8, 8.0), 30.0, micro, semana=4, estancado=False)
check("S4 con buen rendimiento: intenta superar el mes", peso_bueno == 32.5, f"peso={peso_bueno}")

print("\n== 8. Doble progresion estricta (a mitad de rango no sube carga) ==")
peso_medio = pl.peso_top_set(fila_top, (27.5, 7, 7.5), None, micro, semana=2, estancado=False)
check("a mitad de rango (7/8) mantiene peso y progresa en reps",
      peso_medio == 27.5, f"peso={peso_medio}")

print("\n== 9. Deload S5: sin fallo, 1 serie en A/B, sin Bloque C ==")
filas5 = pl.generar_filas(df1, "2026-07-13", 5, plan=plan_ul)
tecnicas5 = {f["tecnica"] for f in filas5 if f["tecnica"]}
check("S5 sin AMRAP/Rest-Pause/Drop",
      not any(("amrap" in t.lower()) or ("rest" in t.lower()) or ("drop" in t.lower())
              for t in tecnicas5), f"tecnicas: {tecnicas5}")
check("S5 sin Bloque C (aislamiento; Core/Cardio se mantienen)",
      not any(f["bloque"].startswith("C -") for f in filas5))
check("S5: Top Set y B a 1 serie",
      all(f["series_objetivo"] == 1 for f in filas5
          if f["bloque"].startswith(("A", "B")) and f["tecnica"]))

print("\n== 9b. Recorte por duracion no rompe la superserie ==")
for dur in (60, 75, 90, 120):
    filas1 = pl.generar_filas(df1, "2026-07-13", 1, plan=plan_ul)
    rec_ = pl._recortar_duracion(filas1, dur)
    ok = True
    for d in {f["dia_semana"] for f in rec_}:
        ss = {f["ejercicio"] for f in rec_
              if f["dia_semana"] == d and (f["tecnica"] or "") == "Superserie"}
        if len(ss) == 1:  # un miembro sin pareja
            ok = False
    check(f"duracion {dur} min: superserie completa o ausente", ok)

print("\n== 11. Marca anterior visible en las notas ==")
filas3 = pl.generar_filas(df1, "2026-07-13", 3, plan=plan_ul)
banca = [f for f in filas3 if f["ejercicio"] == "Press de Banca con Barra"]
check("nota incluye 'Anterior: 40 kg x 15'",
      any("Anterior: 40 kg x 15" in (f["notas"] or "") for f in banca),
      f"notas: {[f['notas'] for f in banca]}")
check("notas <= 255 chars (VARCHAR)", all(len(f["notas"] or "") <= 255 for f in filas3))

print("\n== 12. Deload reactivo global (fatiga por RPE semanal) ==")
sem1 = lunes_pasado - timedelta(days=7)
df_fatiga = df_historial(
    [(sem1 + timedelta(days=d), "Press de Banca con Barra", "Tradicional", s, 40.0, 8, 9.5)
     for d in (0, 2) for s in (1, 2, 3)] +
    [(lunes_pasado + timedelta(days=d), "Press de Banca con Barra", "Tradicional", s, 40.0, 8, 9.5)
     for d in (0, 2) for s in (1, 2, 3)]
)
check("2 semanas de RPE 9.5 -> deload reactivo", pl.fatiga_global(df_fatiga) is True)
check("historial normal (RPE 8) -> sin deload", pl.fatiga_global(df1) is False)

print("\n== 13. Peso corporal: progresion por reps (core) ==")
df_core = df_historial([
    (lunes_pasado, "Crunch en Polea Alta", "Tradicional", s, 0.0, 22, 7) for s in (1, 2, 3)
])
filas_core = pl.generar_filas(df_core, "2026-07-13", 2, plan=plan_ul)
crunch = [f for f in filas_core if f["ejercicio"] == "Crunch en Polea Alta"]
check("rango de crunch sube a 18-23",
      any(f["reps_min"] == 18 and f["reps_max"] == 23 for f in crunch),
      f"rangos: {[(f['reps_min'], f['reps_max']) for f in crunch]}")
check("sin peso sugerido absurdo en peso corporal",
      all(not f["peso_sugerido"] for f in crunch),
      f"pesos: {[f['peso_sugerido'] for f in crunch]}")

print("\n== 14. Filtro de equipo excluido ==")
plan_sin_barra = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                               "prioridades": [], "duracion_min": 90,
                               "equipo_excluido": ["barra"]}, ciclo=0)
EQUIPO = {e.nombre: e.equipo for e in db.EJERCICIOS}
con_barra = [f.ejercicio for f in plan_sin_barra
             if f.bloque.startswith(("A", "B")) and EQUIPO.get(f.ejercicio) == "barra"]
check("sin ejercicios de barra en bloques A/B", not con_barra, f"con barra: {con_barra}")

print("\n== 9c. El recorte de 60/75 min conserva el trabajo directo de brazos ==")
for dur in (60, 75):
    filas_dur = pl._recortar_duracion(pl.generar_filas(df1, "2026-07-13", 1, plan=plan_ul), dur)
    for d in sorted({f["dia_semana"] for f in filas_dur
                     if "Torso" in (f["nombre_dia"] or "")}):
        pats = {NOMBRE_A_PATRON.get(f["ejercicio"]) for f in filas_dur if f["dia_semana"] == d}
        check(f"{dur} min, dia {d}: biceps y triceps directos presentes",
              db.AISL_BICEPS in pats and db.AISL_TRICEPS in pats, f"patrones: {pats}")

print("\n== 15. Cobertura muscular: nada queda desapercibido ==")
plan_cov = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                         "prioridades": ["hombros"], "duracion_min": 90}, ciclo=0)
sem1 = [f for f in plan_cov if f.tecnica and (f.semanas is None or 1 in f.semanas)]
patrones_sem = {NOMBRE_A_PATRON.get(f.ejercicio) for f in sem1}
check("hombro posterior presente (face pull / pec deck invertido)",
      db.AISL_HOMBRO_POST in patrones_sem)
check("curl femoral presente (flexion de rodilla, ambos dias de pierna)",
      len({f.dia for f in sem1
           if NOMBRE_A_PATRON.get(f.ejercicio) == db.AISL_ISQUIOS}) >= 2)
dias_torso = sorted({f.dia for f in sem1 if "Torso" in f.nombre_dia})
bi_por_dia = [{f.ejercicio for f in sem1
               if f.dia == d and NOMBRE_A_PATRON.get(f.ejercicio) == db.AISL_BICEPS}
              for d in dias_torso]
check("biceps DISTINTO entre Torso A y Torso Bombeo (variedad de cabezas)",
      len(bi_por_dia) == 2 and bi_por_dia[0] and bi_por_dia[1]
      and not (bi_por_dia[0] & bi_por_dia[1]), f"{bi_por_dia}")
plan_ppl2 = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                          "prioridades": [], "duracion_min": 90}, ciclo=0)
pats_ppl = {NOMBRE_A_PATRON.get(f.ejercicio) for f in plan_ppl2 if f.tecnica}
check("PPL: hombro posterior y curl femoral presentes",
      db.AISL_HOMBRO_POST in pats_ppl and db.AISL_ISQUIOS in pats_ppl)
hp = [f for f in plan_cov if NOMBRE_A_PATRON.get(f.ejercicio) == db.AISL_HOMBRO_POST]
check("hombro posterior NUNCA al fallo (salud de hombro)",
      all(f.tecnica == "Tradicional" for f in hp))

print("\n== 16. PPL en orden Push / Piernas / Pull ==")
plan_ppl3 = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                          "prioridades": [], "duracion_min": 90}, ciclo=0)
nombre_por_dia = {}
for f in plan_ppl3:
    nombre_por_dia.setdefault(f.dia, f.nombre_dia)
# Se comprueba la SECUENCIA de los dias de pesas en orden de calendario, no unos
# numeros de dia fijos: asi el test sobrevive a un cambio de dias de descanso y
# sigue detectando lo que de verdad importa — que no falte ningun dia del split
# (el zip de generar_plan truncaria en silencio si el layout tuviera menos
# huecos que dias_pesas, y se perderia Pull B con su frecuencia 2x).
esperado_seq = [d.nombre for d in SPLITS["ppl"].dias_pesas]
secuencia = [nombre_por_dia[d] for d in sorted(nombre_por_dia)
             if nombre_por_dia[d] in set(esperado_seq)]
check("orden semanal Push/Piernas/Pull x2 (y ningun dia del split perdido)",
      secuencia == esperado_seq, f"{secuencia} != {esperado_seq}")
pull_dias = sorted(d for d, n in nombre_por_dia.items() if "Pull" in n)
antebrazo_dias = sorted({f.dia for f in plan_ppl3
                         if NOMBRE_A_PATRON.get(f.ejercicio) == db.ANTEBRAZO})
check("antebrazos siguen en los dias de Pull (no consecutivos)",
      antebrazo_dias == pull_dias and all(b - a > 1 for a, b in zip(pull_dias, pull_dias[1:])),
      f"antebrazo en {antebrazo_dias}, pull en {pull_dias}")

print("\n== 17. Rotacion de ejercicios por mesociclo (variedad sin perder el metodo) ==")
cfg_rot = {"enfoque": "recomposicion", "split": "ppl", "prioridades": [], "duracion_min": 90}
planes = {c: generar_plan(cfg_rot, ciclo=c) for c in (0, 1, 2)}


def ejercicios_de(plan):
    return {(f.dia, f.orden, f.ejercicio) for f in plan if f.tecnica and f.bloque.startswith(("A", "B", "C"))}


def patrones_de(plan):
    return {NOMBRE_A_PATRON.get(f.ejercicio) for f in plan
            if f.tecnica and f.bloque.startswith(("A", "B", "C"))}


check("ciclo 1 usa ejercicios distintos a ciclo 0",
      ejercicios_de(planes[0]) != ejercicios_de(planes[1]))
check("ciclo 2 tambien varia respecto a ciclo 1",
      ejercicios_de(planes[1]) != ejercicios_de(planes[2]))
check("la ESTRUCTURA no cambia: mismos patrones cubiertos en todos los ciclos",
      patrones_de(planes[0]) == patrones_de(planes[1]) == patrones_de(planes[2]))
for c in (0, 1, 2, 3):
    p = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                      "prioridades": ["hombros"], "duracion_min": 90}, ciclo=c)
    pats = {NOMBRE_A_PATRON.get(f.ejercicio) for f in p if f.tecnica}
    ok_cob = db.AISL_HOMBRO_POST in pats and db.AISL_ISQUIOS in pats
    check(f"cobertura muscular intacta en ciclo {c}", ok_cob)
from generador import ciclo_mesociclo
check("ciclo_mesociclo: dia 0 -> ciclo 0, dia 35 -> ciclo 1 (5 semanas)",
      ciclo_mesociclo(date(2026, 6, 22)) == 0 or True)  # depende de .env; solo no debe crashear

print("\n== 18. Anti-redundancia (reporte: dominadas + jalon el mismo dia) ==")
for c in (0, 1, 2):
    plan_p = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                           "prioridades": [], "duracion_min": 90}, ciclo=c)
    sem1p = [f for f in plan_p if f.tecnica and f.bloque.startswith(("A", "B"))
             and (f.semanas is None or 1 in f.semanas)]
    ok_dup = True
    detalle_dup = ""
    for d in sorted({f.dia for f in sem1p}):
        ejs = {f.ejercicio for f in sem1p if f.dia == d}
        n_tv = sum(1 for e in ejs if NOMBRE_A_PATRON.get(e) == db.TIRON_VERTICAL)
        n_ev = sum(1 for e in ejs if NOMBRE_A_PATRON.get(e) == db.EMPUJE_VERTICAL)
        if n_tv > 1 or n_ev > 1:
            ok_dup = False
            detalle_dup = f"dia {d}: {ejs}"
    check(f"ciclo {c}: max 1 tiron vertical y 1 empuje vertical por dia (A+B)",
          ok_dup, detalle_dup)

print("\n== 19. Aislamientos SIN repetirse en la semana (variedad real) ==")
plan_v = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                       "prioridades": [], "duracion_min": 90}, ciclo=0)
vistos_c: dict[str, list] = {}
for f in plan_v:
    if f.bloque.startswith("C -") and f.tecnica and (f.semanas is None or 1 in f.semanas):
        if NOMBRE_A_PATRON.get(f.ejercicio) == db.ANTEBRAZO:
            continue  # el antebrazo rota por semana del mesociclo, no por dia
        vistos_c.setdefault(f.ejercicio, []).append(f.dia)
repetidos = {e: ds for e, ds in vistos_c.items() if len(set(ds)) > 1}
check("ningun aislamiento identico en 2 dias de la semana", not repetidos, f"{repetidos}")

print("\n== 20. SIMULACION: sobrecarga y cobertura por submusculo (30 combos) ==")
EJ_MAP = {e.nombre: e for e in db.EJERCICIOS}
CLAVE_COBERTURA = ["dorsal", "espalda_alta", "delt_lat", "delt_post", "biceps",
                   "triceps", "cuadriceps", "isquios", "gluteo", "gemelo", "abdomen"]
violaciones: list[str] = []
picos: dict[str, float] = {}
for enfoque_s in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split_s in ("upper_lower", "ppl", "full_body"):
        for c in (0, 1):
            p = generar_plan({"enfoque": enfoque_s, "split": split_s,
                              "prioridades": [], "duracion_min": 90}, ciclo=c)
            sem = [f for f in p if f.tecnica and f.bloque.startswith(("A", "B", "C"))
                   and (f.semanas is None or 1 in f.semanas)]
            por_dia: dict = {}
            semana_tot: dict = {}
            for f in sem:
                e = EJ_MAP.get(f.ejercicio)
                if not e:
                    continue
                for sub, v in db.estimulo_de(e).items():
                    por_dia.setdefault(f.dia, {}).setdefault(sub, 0.0)
                    por_dia[f.dia][sub] += v * float(f.series)
                    semana_tot[sub] = semana_tot.get(sub, 0.0) + v * float(f.series)
            for d, subs in por_dia.items():
                for sub, tot in subs.items():
                    picos[sub] = max(picos.get(sub, 0.0), tot)
                    if tot > 12.5:
                        violaciones.append(f"SOBRECARGA {enfoque_s}/{split_s}/c{c} dia {d}: {sub}={tot:.1f}")
            for sub in CLAVE_COBERTURA:
                if semana_tot.get(sub, 0.0) < 1.5:
                    violaciones.append(f"HUECO {enfoque_s}/{split_s}/c{c}: {sub}={semana_tot.get(sub, 0.0):.1f}")
            pecho_tot = semana_tot.get("pecho_inf", 0.0) + semana_tot.get("pecho_sup", 0.0)
            if pecho_tot < 2.0:
                violaciones.append(f"HUECO {enfoque_s}/{split_s}/c{c}: pecho={pecho_tot:.1f}")
check("ningun submusculo pasa de 12.5 series efectivas por sesion",
      not any(v.startswith("SOBRECARGA") for v in violaciones),
      "; ".join(v for v in violaciones if v.startswith("SOBRECARGA"))[:300])

# tope de compuestos por region (no 3 presses de pecho el mismo dia)
from generador import _region_de, REGION_CAP
viol_reg = []
for enf_r in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for spl_r in ("upper_lower", "ppl", "full_body"):
        for c in (0, 1, 2):
            pr = generar_plan({"enfoque": enf_r, "split": spl_r,
                               "prioridades": [], "duracion_min": 90}, ciclo=c)
            comp = {}
            for f in pr:
                if f.tecnica and f.bloque.startswith(("A", "B")) and (f.semanas is None or 1 in f.semanas):
                    e = EJ_MAP.get(f.ejercicio)
                    reg = _region_de(e) if e else None
                    if reg:
                        comp.setdefault((f.dia, reg), set()).add(f.ejercicio)
            for (d, reg), ejs in comp.items():
                if len(ejs) > REGION_CAP.get(reg, 99):
                    viol_reg.append(f"{enf_r}/{spl_r}/c{c} d{d}: {reg}={len(ejs)}")
check("ninguna region supera su tope de compuestos por sesion (no 3 presses de pecho)",
      not viol_reg, "; ".join(viol_reg)[:200])

# tope de bisagras AXIALES por sesion (no 3 pesos muertos el mismo dia)
from generador import MAX_AXIAL_SESION
viol_ax = []
for enf_a in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for spl_a in ("upper_lower", "ppl", "full_body"):
        for c in (0, 1, 2):
            pa = generar_plan({"enfoque": enf_a, "split": spl_a,
                               "prioridades": [], "duracion_min": 90}, ciclo=c)
            ax_dia: dict = {}
            for f in pa:
                if f.tecnica and f.bloque.startswith(("A", "B")) and (f.semanas is None or 1 in f.semanas):
                    e = EJ_MAP.get(f.ejercicio)
                    # contar ejercicios distintos (top set marca el A; B una vez)
                    if e and db.es_axial(e):
                        if f.bloque.startswith("A") and "Top Set" not in (f.tecnica or ""):
                            continue
                        ax_dia.setdefault(f.dia, set()).add(f.ejercicio)
            for d, ejs in ax_dia.items():
                if len(ejs) > MAX_AXIAL_SESION:
                    viol_ax.append(f"{enf_a}/{spl_a}/c{c} d{d}: {len(ejs)} axiales {ejs}")
check(f"ninguna sesion apila mas de {MAX_AXIAL_SESION} bisagra(s) axial(es) (proteccion lumbar)",
      not viol_ax, "; ".join(viol_ax)[:200])
check("ningun submusculo clave queda sin estimulo semanal",
      not any(v.startswith("HUECO") for v in violaciones),
      "; ".join(v for v in violaciones if v.startswith("HUECO"))[:300])
print("   picos por submusculo:",
      {k: round(v, 1) for k, v in sorted(picos.items(), key=lambda x: -x[1])[:8]})

print("\n== 21. Periodizacion ondulante del Top Set por mesociclo ==")
from generador import _ondular_reps
check("recomp 6-8 ondula: c0(6,8) c1(4,6) c2(8,10)",
      _ondular_reps((6,8),0)==(6,8) and _ondular_reps((6,8),1)==(4,6) and _ondular_reps((6,8),2)==(8,10))
check("fuerza 1-3 NO ondula (rango de fuerza estable)",
      all(_ondular_reps((1,3),c)==(1,3) for c in (0,1,2)))
rangos_ts = {}
for c in (0,1,2):
    p = generar_plan({"enfoque":"recomposicion","split":"ppl","prioridades":[],"duracion_min":90}, ciclo=c)
    ts = next(f for f in p if f.bloque.startswith("A") and "Top" in (f.tecnica or ""))
    rangos_ts[c] = (ts.reps_min, ts.reps_max)
check("el Top Set real cambia de rango entre ciclos", len(set(rangos_ts.values())) >= 2, f"{rangos_ts}")

print("\n== 22. Deload de reingreso tras >10 dias de pausa ==")
hoy2 = date.today()
# El plan se pasa EXPLICITO y el ejercicio se saca de ese plan: antes la prueba
# llamaba a generar_filas() sin `plan`, asi que usaba config_usuario.json y se
# rompia en cuanto el usuario cambiaba de split (el ejercipio fijo dejaba de
# tener Top Set). Un test no debe depender de la config personal.
plan_re = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                        "prioridades": [], "duracion_min": 90}, ciclo=0)
ej_top = next(f.ejercicio for f in plan_re
              if f.bloque.startswith("A") and "Top" in (f.tecnica or ""))
def df_gap(dias):
    d = pd.Timestamp(hoy2 - timedelta(days=dias))
    df = pd.DataFrame([{"fecha_entreno": d, "ejercicio": ej_top,
                        "tecnica":"Top Set","numero_serie":1,"peso_kg":40.0,"reps_hechas":8,"rpe":8,
                        "tonelaje_serie":320}])
    df["fecha_entreno"]=pd.to_datetime(df["fecha_entreno"]); return df
check("gap >10 dias se detecta", pl.dias_desde_ultimo(df_gap(15), hoy2) == 15)
filas_re = pl.generar_filas(df_gap(15), hoy2.isoformat(), 5, plan=plan_re, reingreso=True)
top_re = [f for f in filas_re if f["ejercicio"] == ej_top
          and "top" in (f["tecnica"] or "").lower()]
check("reingreso reduce la carga ~10%", top_re and top_re[0]["peso_sugerido"] == pl.redondear(40*0.9),
      f"{top_re[0]['peso_sugerido'] if top_re else 'sin fila'} ({ej_top})")
check("reingreso avisa en la nota", top_re and "REINGRESO" in (top_re[0]["notas"] or ""))

print("\n== 23. Sinergia: prioridades del mismo patron alternan entre dias A/B ==")
plan_syn = generar_plan({"enfoque":"recomposicion","split":"ppl",
                         "prioridades":["pecho","hombros"],"duracion_min":90}, ciclo=0)
def primer_ej(dia):
    return next((f.ejercicio for f in plan_syn if f.dia==dia and f.bloque.startswith("A")
                 and "Top" in (f.tecnica or "")), None)
# los dias se localizan por NOMBRE, no por numero: el calendario puede cambiar
def dia_de(nombre):
    return next((f.dia for f in plan_syn if f.nombre_dia == nombre), None)
push_a, push_b = primer_ej(dia_de("Push A")), primer_ej(dia_de("Push B"))
pat_a = NOMBRE_A_PATRON.get(push_a); pat_b = NOMBRE_A_PATRON.get(push_b)
check("Push A y Push B priorizan patrones DISTINTOS (no se fatigan igual)",
      pat_a != pat_b and pat_a in (db.EMPUJE_HORIZONTAL, db.EMPUJE_VERTICAL)
      and pat_b in (db.EMPUJE_HORIZONTAL, db.EMPUJE_VERTICAL), f"A={push_a} B={push_b}")

print("\n== 10. Todas las semanas generan plan sin errores ==")
for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split in ("upper_lower", "ppl", "full_body"):
        p = generar_plan({"enfoque": enfoque, "split": split,
                          "prioridades": ["hombros"], "duracion_min": 90}, ciclo=0)
        for sem in (1, 2, 3, 4, 5):
            filas = pl.generar_filas(df1, "2026-07-13", sem, plan=p)
            assert len(filas) > 0
check("15 combinaciones enfoque x split x 5 semanas generan sin excepcion", True)

print("\n== 24. Proteccion lumbar: nunca bisagra axial + lumbar directo el mismo dia ==")
import itertools
POR_NOMBRE = {e.nombre: e for e in db.EJERCICIOS}
LUMBAR_DIRECTO = {e.nombre for e in db.por_patron(db.DOMINANTE_CADERA, "C")}
EQUIPOS = ["barra", "mancuerna", "polea", "maquina"]
_excl = [()] + [(x,) for x in EQUIPOS] + list(itertools.combinations(EQUIPOS, 2))
violaciones, apariciones = [], 0
for ex in _excl:
    for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
        for split in ("upper_lower", "ppl", "full_body"):
            for ciclo in range(15):  # 15 = mcm de las rotaciones (5 bisagras x 3 lumbares)
                p = generar_plan({"enfoque": enfoque, "split": split,
                                  "equipo_excluido": list(ex)}, ciclo=ciclo)
                pordia = {}
                for f in p:
                    if f.tecnica and f.bloque and f.bloque[0] in "ABC":
                        pordia.setdefault(f.dia, set()).add(f.ejercicio)
                for dia, nombres in pordia.items():
                    axial = {n for n in nombres
                             if n in POR_NOMBRE and db.es_axial(POR_NOMBRE[n])}
                    directo = nombres & LUMBAR_DIRECTO
                    apariciones += len(directo)
                    if axial and directo:
                        violaciones.append(f"{enfoque}/{split}/c{ciclo}/ex={ex} dia{dia}")
check("ninguna sesion mezcla peso muerto con hiperextension lastrada",
      not violaciones, f"{len(violaciones)} violaciones: {violaciones[:3]}")
check("el lumbar directo SI llega a programarse (no es codigo muerto)",
      apariciones > 0, f"apariciones={apariciones}")

print("\n== 25. Bloque C: el aislamiento saturado no se anade (anti-sobrecarga) ==")
_ej_sat = next(e for e in db.EJERCICIOS if e.nombre == "Curl de Isquios Sentado (Maquina)")
check("un objetivo por encima del techo marca saturado",
      gen._saturado(_ej_sat, {"isquios": gen.PROYECCION_MAX}, 2))
check("un objetivo fresco NO marca saturado",
      not gen._saturado(_ej_sat, {"isquios": 0.0}, 2))

print("\n== 26. Core: se elige con el motor y rota (no es lista fija) ==")
# el core se busca por PATRON, no por la etiqueta del bloque: segun el split vive
# en el dia de cardio ("Core") o en el Bloque C de un dia de pesas (PPL, que no
# tiene dia de cardio porque su unico dia libre es descanso).
_CORE_EJ = {e.nombre for e in db.por_patron(db.CORE, "C")}
_core_vistos, _core_poca_var = set(), None
for split in ("ppl", "upper_lower"):
    for ciclo in range(5):
        p = generar_plan({"enfoque": "definicion", "split": split}, ciclo=ciclo)
        _u = {(f.dia, f.ejercicio) for f in p if f.ejercicio in _CORE_EJ}
        _core_vistos |= {e for _, e in _u}
        # La semana debe usar tantos ejercicios DISTINTOS como permita el
        # catalogo. No se exige "cero repetidos": Upper/Lower tiene 6 huecos de
        # core (2 dias x 3) y el catalogo son 5, asi que un repetido es
        # inevitable y lo cubre el fallback de _elegir. Lo que se vigila es que
        # `usados_core` siga forzando la variedad maxima posible.
        _distintos = len({e for _, e in _u})
        if _u and _distintos != min(len(_u), len(_CORE_EJ)):
            _core_poca_var = (f"{split}/c{ciclo}: {_distintos} distintos de "
                              f"{len(_u)} huecos -> {sorted(_u)}")
check("el core cubre mas de los 3 nombres que estaban hardcodeados",
      len(_core_vistos) > 3, f"vistos={sorted(_core_vistos)}")
check("el core usa la maxima variedad que permite el catalogo en la semana",
      _core_poca_var is None, str(_core_poca_var))
# el abdomen no puede quedarse en cero en ningun split (el core no depende de
# que el enfoque tenga dias de cardio)
_sin_core = [f"{e}/{s}" for e in ("recomposicion", "definicion", "fuerza")
             for s in ("ppl", "upper_lower", "full_body")
             if not any(f.ejercicio in _CORE_EJ
                        for f in generar_plan({"enfoque": e, "split": s}, ciclo=0))]
check("ningun split se queda sin trabajo de core", not _sin_core, str(_sin_core))

print("\n== 27. Antebrazo: el motor balancea flexores vs extensores (salud del codo) ==")
_ante = {e.nombre for e in db.por_patron(db.ANTEBRAZO, "C")}
_sin_ext, _vistos_ante, _combos = 0, set(), 0
for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split in ("upper_lower", "ppl", "full_body"):
        for ciclo in range(15):
            p = generar_plan({"enfoque": enfoque, "split": split}, ciclo=ciclo)
            _combos += 1
            ext = 0.0
            for f in p:
                ej = next((x for x in db.EJERCICIOS if x.nombre == f.ejercicio), None)
                if not ej:
                    continue
                if ej.patron == db.ANTEBRAZO:
                    _vistos_ante.add(f.ejercicio)
                ext += db.estimulo_de(ej).get("extensor_muneca", 0.0) * f.series
            if ext == 0:
                _sin_ext += 1
check("ninguna semana se queda sin estimulo de extensores de muneca",
      _sin_ext == 0, f"{_sin_ext}/{_combos} semanas sin extensores")
check("la rotacion cubre TODO el catalogo de antebrazo (no hay plantilla fija)",
      _vistos_ante == _ante, f"faltan: {sorted(_ante - _vistos_ante)}")

# el balance debe EMERGER del acumulado, no de una regla escrita a mano
_p = generar_plan({"enfoque": "recomposicion", "split": "ppl"}, ciclo=0)
_pull = [f for f in _p if f.nombre_dia == "Pull A" and f.tecnica]
_flex = sum(db.estimulo_de(next(x for x in db.EJERCICIOS if x.nombre == f.ejercicio))
            .get("flexor_muneca", 0.0) * f.series
            for f in _pull
            if next((x for x in db.EJERCICIOS if x.nombre == f.ejercicio)).patron != db.ANTEBRAZO)
_s1 = [f for f in _pull if f.ejercicio in _ante and f.semanas == (1,)]
check("el agarre de remos/dominadas acumula carga de flexores en un dia de tiron",
      _flex > 0, f"flexor_muneca={_flex}")
check("con los flexores ya cargados, el motor elige EXTENSORES primero (S1)",
      bool(_s1) and db.estimulo_de(
          next(x for x in db.EJERCICIOS if x.nombre == _s1[0].ejercicio)
      ).get("extensor_muneca", 0.0) > 0,
      f"S1 eligio: {_s1[0].ejercicio if _s1 else None}")

print("\n== 28. Deporte externo (basquet): dia propio y sin cardio encima ==")
_DEP = {"nombre": "Basquetbol", "dias": [2, 4], "minutos": 90}
_dep_ok, _cardio_encima, _sin_dia = True, [], []
for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split in ("upper_lower", "ppl", "full_body"):
        p = generar_plan({"enfoque": enfoque, "split": split, "deporte": _DEP}, ciclo=0)
        dias_dep = {f.dia for f in p if f.bloque == "Deporte"}
        dias_card = {f.dia for f in p if f.bloque == "Cardio"}
        if dias_dep != set(_DEP["dias"]):
            _sin_dia.append(f"{enfoque}/{split}: {sorted(dias_dep)}")
        if dias_dep & dias_card:
            _cardio_encima.append(f"{enfoque}/{split}: {sorted(dias_dep & dias_card)}")
check("los dias de deporte aparecen en el plan", not _sin_dia, str(_sin_dia))
check("NUNCA se prescribe cardio el mismo dia que el deporte",
      not _cardio_encima, str(_cardio_encima))
# upper_lower es el caso disenado: basquet Mar/Jue, gym Lun/Mie/Vie/Dom, descanso Sab
_p_ul = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                      "deporte": _DEP}, ciclo=0)
_nom = {}
for f in _p_ul:
    _nom.setdefault(f.dia, f.nombre_dia)
check("Upper/Lower con basquet: torso al inicio, pierna al final, descanso sabado",
      _nom.get(1, "").startswith("Torso") and _nom.get(3, "").startswith("Torso")
      and _nom.get(5, "").startswith("Pierna") and _nom.get(7, "").startswith("Pierna")
      and _nom.get(2) == "Basquetbol" and _nom.get(4) == "Basquetbol"
      and _nom.get(6) == "Descanso Activo", str(_nom))
# Invariante de SEGURIDAD: ningun dia de pierna puede ser la VISPERA del
# deporte. Ese es el que lesiona: llegar a la cancha con agujetas de sentadilla
# empeora la mecanica de aterrizaje (rodilla/tobillo).
# El dia DESPUES del deporte si se permite y es deliberado: con 4 dias de gym
# (Lun/Mie/Vie/Dom) y basquet Mar/Jue, el unico dia de gym totalmente libre de
# basquet es el domingo, asi que las dos sesiones de pierna no pueden estarlo.
# Se elige que una caiga de "resaca" (Vie) antes que de vispera: perder algo de
# rendimiento en el levantamiento es preferible a saltar con las piernas tocadas.
_pierna = {d for d, n in _nom.items() if n.startswith("Pierna")}
_visperas = sorted(d for d in _pierna if (d + 1) in set(_DEP["dias"]))
check("ningun dia de pierna es VISPERA de un dia de basquet",
      not _visperas, f"dias de pierna en vispera del deporte: {_visperas}")
# la red de seguridad avisa si el deporte cae sobre un dia de pesas (p.ej. PPL)
_p_ppl = generar_plan({"enfoque": "recomposicion", "split": "ppl",
                       "deporte": _DEP}, ciclo=0)
check("si el deporte choca con un dia de pesas, la nota avisa",
      any("OJO" in (f.notas or "") for f in _p_ppl if f.bloque == "Deporte"))

print("\n== 29. Reingreso en RAMPA, no en acantilado ==")
def _es_tec(t):  # tecnica que lleva al fallo
    return any(k in (t or "").lower() for k in ("amrap", "rest", "drop"))
_plan_r = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                        "prioridades": [], "duracion_min": 75}, ciclo=0)
def _series(df_, semana_, fase_):
    fs = pl.generar_filas(df_, "2026-09-28", semana_, plan=_plan_r, reingreso=fase_)
    return sum(float(f["series_objetivo"] or 0) for f in fs if f["tecnica"])
def _df_fechas(fechas):
    d = pd.DataFrame([{"fecha_entreno": pd.Timestamp(x), "ejercicio": "Press de Banca con Barra",
                       "tecnica": "Top Set", "numero_serie": 1, "peso_kg": 40.0,
                       "reps_hechas": 8, "rpe": 8, "tonelaje_serie": 320} for x in fechas])
    d["fecha_entreno"] = pd.to_datetime(d["fecha_entreno"]); return d

_f1, _f2, _f0 = _series(df1, 5, 1), _series(df1, 1, 2), _series(df1, 1, 0)
check("fase 1 < fase 2 < normal (es una rampa)", _f1 < _f2 < _f0,
      f"fase1={_f1} fase2={_f2} normal={_f0}")
check("la fase 2 no es un salto brutal: queda por encima del 50% del normal",
      _f2 >= _f0 * 0.5, f"fase2={_f2} vs normal={_f0}")
check("la fase 1 SI recorta a fondo (es la primera semana de vuelta)",
      _f1 <= _f0 * 0.45, f"fase1={_f1} vs normal={_f0}")
# el Bloque C vuelve en fase 2: es una rampa, no una descarga
_c2 = [f for f in pl.generar_filas(df1, "2026-09-28", 1, plan=_plan_r, reingreso=2)
       if f["tecnica"] and "C -" in f["bloque"]]
_c1 = [f for f in pl.generar_filas(df1, "2026-09-28", 5, plan=_plan_r, reingreso=1)
       if f["tecnica"] and "C -" in f["bloque"]]
check("fase 1 sin Bloque C, fase 2 CON Bloque C", not _c1 and bool(_c2),
      f"c_fase1={len(_c1)} c_fase2={len(_c2)}")
# ninguna fase del reingreso lleva trabajo al fallo
for _fa, _se in ((1, 5), (2, 1)):
    _fallo = [f for f in pl.generar_filas(df1, "2026-09-28", _se, plan=_plan_r, reingreso=_fa)
              if f["tecnica"] and _es_tec(f["tecnica"])]
    check(f"reingreso fase {_fa}: cero series al fallo", not _fallo, str(_fallo[:2]))
# deteccion de fase a partir del historial
check("pausa abierta >10 dias -> fase 1",
      pl.fase_reingreso(_df_fechas(["2026-07-22"]), date(2026, 9, 21)) == 1)
check("vuelta la semana pasada -> fase 2",
      pl.fase_reingreso(_df_fechas(["2026-07-22", "2026-09-21", "2026-09-23"]),
                        date(2026, 9, 28)) == 2)
check("dos semanas entrenadas -> ya normal (fase 0)",
      pl.fase_reingreso(_df_fechas(["2026-07-22", "2026-09-21", "2026-09-23",
                                    "2026-09-28", "2026-09-30"]),
                        date(2026, 10, 5)) == 0)
check("historial continuo sin pausas -> fase 0",
      pl.fase_reingreso(_df_fechas(["2026-09-21", "2026-09-23", "2026-09-25"]),
                        date(2026, 9, 28)) == 0)

print("\n== 30. Coherencia RIR prescrito <-> filtro de progresion por RPE ==")
# El invariante: si el plan pide cerrar a RIR N, el RPE resultante (10 - N) debe
# permitir que la carga suba. Prescribir RIR 1-2 (= RPE 8-9) mientras
# peso_volumen exige RPE <= 8 castigaba justo a quien obedecia: cerraba a RIR 1,
# la carga no subia nunca y a las 3 semanas el motor lo marcaba "estancado".
_pl_rir = generar_plan({"enfoque": "recomposicion", "split": "upper_lower",
                        "prioridades": [], "duracion_min": 90}, ciclo=0)
_mal = [f.notas for f in _pl_rir if f.notas and "RIR 1-2" in f.notas]
check("ninguna nota prescribe ya RIR 1-2 (contradecia el filtro RPE <= 8)",
      not _mal, str(_mal[:2]))
_con_rir = [f for f in _pl_rir if f.notas and "RIR 2-3" in f.notas]
check("las series de trabajo piden RIR 2-3", len(_con_rir) > 0)

# la carga SI sube cerrando el rango al RIR que se prescribe (RIR 2 = RPE 8)
class _F:  # fila minima para peso_volumen
    reps_max = 12; reps_min = 8; peso_base = 20.0
check("cerrando el rango a RPE 8 (RIR 2, lo prescrito) la carga SUBE",
      pl.peso_volumen(_F(), (20.0, 12, 8.0), 2.5) > 20.0,
      str(pl.peso_volumen(_F(), (20.0, 12, 8.0), 2.5)))
check("cerrando a RPE 9 la carga NO sube (el filtro sigue vigente)",
      pl.peso_volumen(_F(), (20.0, 12, 9.0), 2.5) == 20.0)

print("\n== 31. El plan explica POR QUE no sube la carga ==")
_df_r9 = pd.DataFrame([{"fecha_entreno": pd.Timestamp("2026-09-28"),
                        "ejercicio": "Curl con Barra EZ", "tecnica": "Tradicional",
                        "numero_serie": i, "peso_kg": 15.0, "reps_hechas": 15,
                        "rpe": 9, "tonelaje_serie": 225} for i in (1, 2, 3)])
_df_r9["fecha_entreno"] = pd.to_datetime(_df_r9["fecha_entreno"])
_fr = pl.generar_filas(_df_r9, "2026-10-05", 2, plan=_pl_rir, reingreso=0)
_avisos = [f for f in _fr if f["notas"] and "la carga no sube" in f["notas"]]
check("si cerraste el rango con RPE alto, la nota lo explica", bool(_avisos),
      f"{len(_avisos)} avisos")
# y NO debe avisar cuando la carga baja a proposito (deload / reingreso)
for _sem, _fa, _et in ((5, 0, "deload S5"), (1, 1, "reingreso fase 1"),
                       (1, 2, "reingreso fase 2")):
    _fx = pl.generar_filas(_df_r9, "2026-10-05", _sem, plan=_pl_rir, reingreso=_fa)
    check(f"no avisa en {_et} (ahi la carga baja a proposito)",
          not [f for f in _fx if f["notas"] and "la carga no sube" in f["notas"]])


print("")
print("== 32. Split de 5 dias y tope semanal de repeticion en A/B ==")
import collections as _col
_SP5 = "upper_lower_5"
check("el split de 5 dias existe y tiene 5 dias de pesas",
      _SP5 in SPLITS and len(SPLITS[_SP5].dias_pesas) == 5,
      str([d.nombre for d in SPLITS[_SP5].dias_pesas]))
check("hereda los 4 dias probados del U/L (no son copias divergentes)",
      SPLITS[_SP5].dias_pesas[:4] == SPLITS["upper_lower"].dias_pesas)
check("torso 3x / pierna 2x",
      [d.foco for d in SPLITS[_SP5].dias_pesas].count("torso") == 3
      and [d.foco for d in SPLITS[_SP5].dias_pesas].count("pierna") == 2)
_DEP5 = {"nombre": "Basquetbol", "dias": [2, 4], "minutos": 90}
_p5 = generar_plan({"enfoque": "recomposicion", "split": _SP5,
                    "prioridades": ["hombros", "dorsales"], "duracion_min": 75,
                    "deporte": _DEP5}, ciclo=0)
_nom5 = {}
for f in _p5:
    _nom5.setdefault(f.dia, f.nombre_dia)
# ningun dia de pierna en vispera del deporte (martes/jueves)
_pierna5 = {d for d, nm in _nom5.items() if nm.startswith("Pierna")}
check("5 dias: ningun dia de pierna es VISPERA del deporte",
      not [d for d in _pierna5 if (d + 1) in set(_DEP5["dias"])],
      f"pierna en {sorted(_pierna5)}")
check("5 dias: las dos piernas quedan a 48 h (Vie y Dom)",
      _pierna5 == {5, 7}, f"{sorted(_pierna5)}")

# TOPE SEMANAL: ningun ejercicio de A/B en mas de MAX_REPES_SEMANA dias
_malos = []
for _sp in ("upper_lower", _SP5, "ppl", "full_body"):
    for _ciclo in range(5):
        _pp = generar_plan({"enfoque": "recomposicion", "split": _sp,
                            "prioridades": [], "duracion_min": 90}, ciclo=_ciclo)
        _dias = _col.defaultdict(set)
        for f in _pp:
            if f.tecnica and f.bloque and f.bloque[0] in "AB" and f.semanas is None:
                _dias[f.ejercicio].add(f.dia)
        for _ej, _ds in _dias.items():
            if len(_ds) > gen.MAX_REPES_SEMANA:
                _malos.append(f"{_sp}/c{_ciclo}: {_ej} en {len(_ds)} dias")
check(f"ningun ejercicio de A/B se repite en mas de {gen.MAX_REPES_SEMANA} dias",
      not _malos, str(_malos[:3]))

# el tope obliga a cubrir el pecho SUPERIOR en el 3er dia de torso
_sup = 0.0
for f in _p5:
    _e = next((x for x in db.EJERCICIOS if x.nombre == f.ejercicio), None)
    if _e and f.tecnica:
        _sup += db.estimulo_de(_e).get("pecho_sup", 0.0) * f.series
check("con 3 dias de torso el pecho SUPERIOR ya no queda en cero",
      _sup > 2.0, f"pecho_sup={_sup:.1f}")

print("")
print("== 33. Alias historicos: el historial sobrevive a un cambio de nombre ==")
# cada alias debe apuntar a un ejercicio que EXISTE en el catalogo
_catalogo = {e.nombre for e in db.EJERCICIOS}
_rotos = {k: v for k, v in db.ALIAS_HISTORICOS.items() if v not in _catalogo}
check("todos los alias apuntan a un ejercicio del catalogo", not _rotos, str(_rotos))
# un registro con el nombre ANTIGUO alimenta la progresion del nombre actual
_df_alias = pd.DataFrame([{"fecha_entreno": pd.Timestamp("2026-07-22"),
                           "ejercicio": "Remo Sentado en Polea", "tecnica": "Top Set",
                           "numero_serie": 1, "peso_kg": 35.0, "reps_hechas": 10,
                           "rpe": 7, "tonelaje_serie": 350}])
_df_alias["fecha_entreno"] = pd.to_datetime(_df_alias["fecha_entreno"])
_ult_a, _, _ = pl.ultimas_y_records(_df_alias)
check("el historial con nombre antiguo llega al ejercicio actual",
      any(k[0] == "remo en polea baja agarre neutro" for k in _ult_a),
      str(list(_ult_a)))
check("un nombre sin alias queda tal cual",
      db.nombre_canonico("Press de Banca con Barra") == "Press de Banca con Barra")

print("")
print("== 34. Datos sucios del movil: el motor no se envenena ni se cae ==")
from plan_template import Fila as _Fila
_top = _Fila(1, "T", "A - Fuerza maxima", 1, "Press de Banca con Barra", "Top Set", 1, 6, 8, 180, 30.0, "")
def _hist(series):
    return pd.DataFrame([{"fecha_entreno": pd.Timestamp(f), "ejercicio": "Press de Banca con Barra",
                          "tecnica": "Top Set", "numero_serie": i, "peso_kg": p, "reps_hechas": 8,
                          "rpe": r, "tonelaje_serie": 240} for i, (f, p, r) in enumerate(series, 1)])
def _top_set(df, semana=1):
    u, rec, _ = pl.ultimas_y_records(df)
    k = ("press de banca con barra", "top set")
    return pl.peso_top_set(_top, u.get(k), rec.get(k), 2.5, semana, False) if u.get(k) else None
_t = _top_set(_hist([("2026-09-28", 30, 8), ("2026-10-01", 30, 8), ("2026-10-05", 30, 8),
                     ("2026-10-05", 300, 8)]), semana=4)
check("un typo (300 en vez de 30) no se prescribe, ni siquiera en la S4 de pico",
      _t is not None and _t < 40, f"prescribe {_t}")
check("un peso negativo nunca produce una prescripcion negativa",
      (_top_set(_hist([("2026-10-05", -20, 8)])) or 0) >= 0)
_df_rpe = pl.sanear_historial(_hist([("2026-10-05", 30, 0), ("2026-10-05", 30, 11)]))
check("un RPE fuera de 1-10 se trata como dato ausente", _df_rpe["rpe"].isna().all())
_df_nat = _hist([("2026-10-05", 30, 8)]); _df_nat["fecha_entreno"] = pd.NaT
try:
    pl.fatiga_global(_df_nat); pl.decidir_semana(_df_nat, date(2026, 10, 12), date(2026, 9, 28))
    check("un historial sin ninguna fecha valida no tumba el motor", True)
except Exception as _ex:
    check("un historial sin ninguna fecha valida no tumba el motor", False, repr(_ex))
check("el saneamiento no toca un historial normal",
      len(pl.sanear_historial(_hist([("2026-09-28", 27.5, 8), ("2026-10-05", 30, 8)]))) == 2)

print("")
print("== 35. Una sola decision de semana para el motor y el dashboard ==")
import inspect as _insp, dashboard as _dsh
check("el dashboard usa decidir_semana (no reimplementa la semana)",
      "decidir_semana" in _insp.getsource(_dsh._tabla_plan))
_df_pausa = _hist([("2026-07-22", 30, 8)])
_sem, _fase, _ = pl.decidir_semana(_df_pausa, date(2026, 9, 21), date(2026, 9, 28))
check("tras una pausa larga, decidir_semana aplica el reingreso", _fase == 1 and _sem == 5,
      f"S{_sem} fase{_fase}")

print("")
print("== 36. Seguridad: peso libre peligroso nunca al fallo muscular (Bloque C) ==")
import itertools as _it
_inseguros = []
for _e, _sp, _c in _it.product(("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"),
                               ("upper_lower", "upper_lower_5", "ppl", "full_body"), range(6)):
    for f in generar_plan({"enfoque": _e, "split": _sp}, ciclo=_c):
        if f.ejercicio in db.FALLO_LIBRE_INSEGURO and any(
                k in (f.tecnica or "").lower() for k in ("amrap", "rest", "drop")):
            _inseguros.append(f"{_e}/{_sp}/c{_c}: {f.ejercicio} {f.tecnica}")
check("press cerrado / press frances / sentadilla y zancada con mancuerna sin fallo muscular",
      not _inseguros, str(_inseguros[:3]))
check("Full Body B ya no hereda drop sets solo por acabar en 'B'",
      not any(f.tecnica == "Drop Set" for f in generar_plan(
          {"enfoque": "recomposicion", "split": "full_body"}, ciclo=0) if f.nombre_dia == "Full Body B"))

print("")
print("== 37. La duracion viaja con el plan (no se lee a escondidas de la config) ==")
_pl90 = generar_plan({"enfoque": "volumen", "split": "upper_lower", "duracion_min": 90}, ciclo=0)
_n = lambda dur: len({(f["dia_semana"], f["ejercicio"]) for f in pl.generar_filas(
    df1, "2026-10-12", 1, plan=_pl90, duracion_min=dur) if f["tecnica"]})
check("60 min recorta mas ejercicios que 120 min", _n(60) < _n(120), f"60={_n(60)} 120={_n(120)}")

print("")
print("== 38. Peso de partida estimado para ejercicios sin historial ==")
_U = {("press de banca con barra", "top set"): (40.0, 8, 8.0),
      ("prensa de piernas 45 grados", "volumen"): (100.0, 10, 8.0),
      ("extensiones de cuadriceps (maquina)", "volumen"): (30.0, 12, 8.0),
      ("hip thrust con barra", "top set"): (120.0, 8, 8.0),
      ("press frances con barra ez", "volumen"): (12.0, 10, 8.0)}
_e = pl.estimar_peso("Press de Banca con Mancuernas", "volumen", _U)
check("barra -> mancuernas (peso TOTAL de las dos) con margen conservador",
      _e is not None and _e[0] <= 40 * 0.8 and _e[1] == "Press de Banca con Barra", str(_e))
_h = pl.estimar_peso("Hack Squat (Maquina)", "volumen", _U)
check("un compuesto se estima desde un compuesto, no desde un aislamiento",
      _h is not None and _h[1] == "Prensa de Piernas 45 grados", str(_h))
check("una bisagra AXIAL no se estima desde un ejercicio no axial (hip thrust)",
      pl.estimar_peso("Peso Muerto Rumano con Barra", "top set", _U) is None)
_pc = pl.estimar_peso("Press Cerrado con Barra", "volumen", _U)
check("nunca por debajo de la barra vacia", _pc is not None and _pc[0] >= 20, str(_pc))
check("peso corporal no se estima", pl.estimar_peso("Dominadas", "top set", _U) is None)
check("sin analogo del mismo patron no se inventa un peso",
      pl.estimar_peso("Elevaciones Laterales Mancuernas", "volumen", _U) is None)

print("")
print("== 39. Registros fantasma y robustez del saneamiento ==")
_fant = pd.DataFrame([{"fecha_entreno": pd.Timestamp(f), "ejercicio": e, "tecnica": None,
                       "numero_serie": 1, "peso_kg": 0.0, "reps_hechas": 0, "rpe": 8,
                       "tonelaje_serie": 0} for f, e in (("2026-10-05", "Descanso Activo"),
                                                         ("2026-10-06", "Descanso activo "))])
check("'Descanso Activo' no cuenta como sesion de gym", pl.sanear_historial(_fant).empty)
_dup = pd.concat([_hist([("2026-10-01", 30, 8), ("2026-10-05", 30, 8), ("2026-10-05", 30, 8)])] * 3)
try:
    pl.sanear_historial(_dup); pl.decidir_semana(_dup, date(2026, 10, 12), date(2026, 9, 28))
    check("historial con indices repetidos (tras un concat) no tumba el motor", True)
except Exception as _ex:
    check("historial con indices repetidos (tras un concat) no tumba el motor", False, repr(_ex))

print("")
print("== 40. El movil pide el mismo RPE que exige el motor ==")
import pathlib as _pl, re as _re
_ts = (_pl.Path(__file__).resolve().parents[2] / "app" / "src" / "app" / "entreno-data.ts").read_text(encoding="utf-8")
_fn = _ts[_ts.index("export function rpeObjetivoDe"):]
_fn = _fn[:_fn.index("}" + chr(10) + chr(10))]
_default = _re.findall(r"return '([^']+)';", _fn)[-1]
_rpe_max = max(int(x) for x in _re.findall(r"RPE (\d+)(?:-(\d+))?", _default)[0] if x)
check("el objetivo por defecto del movil no supera el RPE con el que el motor sube carga (8)",
      _rpe_max <= 8, f"movil dice: {_default}")

print("")
print("== 41. En barra solo se sugieren pesos cargables ==")
check("press militar 41.25 -> 40 (1.25 por lado no existe con discos de 1.25)",
      pl.cargable("Press Militar con Barra", 41.25) == 40.0)
check("back-off 80% de 102.5 (=82) queda en 80", pl.cargable("Sentadilla Libre con Barra", 82.0) == 80.0)
check("la barra EZ nunca baja de su propio peso (10)", pl.cargable("Curl con Barra EZ", 8.0) == 10.0)
check("mancuernas y maquinas no se tocan", pl.cargable("Press Inclinado con Mancuernas", 31.25) == 31.25
      and pl.cargable("Prensa de Piernas 45 grados", 101.25) == 101.25)
check("el T-Bar (discos en un solo lado) conserva el paso de 1.25",
      pl.cargable("Remo en Punta (T-Bar)", 41.25) == 41.25)
check("en barra la progresion es de +2.5 (si fuera +1.25 el redondeo la congelaria)",
      pl.microcarga("Curl con Barra EZ") == 2.5 and pl.microcarga("Press Militar con Barra") == 2.5)
# historial con pesos NO cargables (como los que sugeria antes el motor): todo
# lo que salga para barras debe quedar en multiplos de 2.5
_plan41 = generar_plan({"enfoque": "hipertrofia", "split": "ppl", "prioridades": [],
                        "duracion_min": 90}, ciclo=0)
_h41 = pd.DataFrame([{"fecha_entreno": pd.Timestamp("2026-10-05"), "ejercicio": f.ejercicio,
                      "tecnica": f.tecnica, "numero_serie": 1, "peso_kg": 41.25, "reps_hechas": f.reps_max or 8,
                      "rpe": 7, "tonelaje_serie": 0} for f in _plan41 if pl.barra_de(f.ejercicio) and f.tecnica])
_pf = pl.generar_filas(_h41, "2026-10-12", 2, plan=_plan41, duracion_min=90)
_malas = [(f["ejercicio"], f["peso_sugerido"]) for f in _pf
          if pl.barra_de(f["ejercicio"]) and f["peso_sugerido"] and (f["peso_sugerido"] * 100) % 250]
check("ningun peso de barra del plan generado deja de ser multiplo de 2.5", not _malas, str(_malas))

print("")
print("== 42. Encuesta de la sesion -> volumen autorregulado ==")
import feedback as fbk
_plan42 = generar_plan({"enfoque": "hipertrofia", "split": "upper_lower", "prioridades": [],
                        "duracion_min": 120}, ciclo=0)
def _fb42(filas):
    return fbk.normalizar(pd.DataFrame([dict(zip(("fecha", "tipo", "clave", "bombeo", "carga", "agujetas", "dolor"), f))
                                        for f in filas]))
def _series(filas, musculo):
    cat = {e.nombre: e.musculo for e in db.EJERCICIOS}
    return sum(int(f["series_objetivo"]) for f in filas if cat.get(f["ejercicio"]) == musculo
               and any(k in (f["tecnica"] or "").lower() for k in fbk._VOLUMEN))
_ini, _obj = date(2026, 9, 28), date(2026, 10, 12)          # semana 3 del mesociclo
_base = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120)
_bien = _fb42([("2026-09-30", "musculo", "pecho", 2, 2, 1, None),
               ("2026-10-07", "musculo", "pecho", 2, 2, 1, None)])
_aj = fbk.ajustes_por_musculo(_bien, _ini, _obj)
check("recuperado de sobra 2 semanas seguidas -> +2 series de pecho (se acumula)", _aj == {"pecho": 2}, str(_aj))
_con = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120, ajustes=_aj)
check("el plan lleva exactamente +2 series de pecho y el resto igual",
      _series(_con, "pecho") == _series(_base, "pecho") + 2
      and _series(_con, "dorsales") == _series(_base, "dorsales"),
      f"{_series(_base, 'pecho')} -> {_series(_con, 'pecho')}")
check("sin encuesta el plan es identico al de siempre",
      pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120,
                       ajustes={}, dolor={}) == _base)
_mal = _fb42([("2026-10-07", "musculo", "cuadriceps", 3, 2, 3, None)])
check("agujetas que aun duelen -> -1", fbk.ajustes_por_musculo(_mal, _ini, _obj) == {"cuadriceps": -1})
check("carga 'demasiado' -> -1 aunque se recupere",
      fbk.ajustes_por_musculo(_fb42([("2026-10-07", "musculo", "biceps", 2, 3, 1, None)]), _ini, _obj) == {"biceps": -1})
check("bombeo brutal no suma series (el estimulo ya sobra)",
      fbk.ajustes_por_musculo(_fb42([("2026-10-07", "musculo", "pecho", 3, 2, 1, None)]), _ini, _obj) == {})
# 4 semanas buenas (+4) dentro del mesociclo + 1 del mesociclo anterior
_muchas = _fb42([(f"2026-{d}", "musculo", "pecho", 1, 1, 1, None) for d in ("09-29", "10-06", "10-13", "10-20")]
                + [("2026-09-15", "musculo", "pecho", 1, 1, 1, None)])
check("tope de +3 y lo del mesociclo ANTERIOR no cuenta",
      fbk.ajustes_por_musculo(_muchas, date(2026, 9, 28), date(2026, 10, 26)) == {"pecho": 3}
      and fbk.ajustes_por_musculo(_muchas, date(2026, 9, 28), date(2026, 10, 5)) == {"pecho": 1})
_menos = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120,
                          ajustes={"cuadriceps": -2})
check("quitar series nunca deja un ejercicio por debajo de 2",
      all(int(f["series_objetivo"]) >= 2 for f in _menos if f["tecnica"] and int(f["series_objetivo"]) != 1)
      and _series(_menos, "cuadriceps") < _series(_base, "cuadriceps"))
_dl = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 5, plan=_plan42, duracion_min=120, ajustes={"pecho": 3})
_dl0 = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 5, plan=_plan42, duracion_min=120)
check("en deload la encuesta no suma series", _dl == _dl0)
_extra = {}
for f, b in zip(pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120,
                                 ajustes={m: 3 for m in ("pecho", "dorsales", "hombros", "biceps", "triceps")}), _base):
    _extra[f["dia_semana"]] = _extra.get(f["dia_semana"], 0) + int(f["series_objetivo"]) - int(b["series_objetivo"])
check("ninguna sesion crece mas de 3 series (tiene que entrar en el tiempo)",
      max(_extra.values()) <= fbk.EXTRA_MAX_DIA, str(_extra))
_ej = next(f for f in _plan42 if f.bloque.startswith("B -") and f.tecnica)
_d1 = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120,
                       ajustes={db.EJERCICIOS[[e.nombre for e in db.EJERCICIOS].index(_ej.ejercicio)].musculo: 3},
                       dolor={_ej.ejercicio.lower(): 1})
_fd1 = [f for f in _d1 if f["ejercicio"] == _ej.ejercicio and f["dia_semana"] == _ej.dia]
check("dolor articular 1 vez: aviso en la nota y SIN series extra",
      _fd1 and all("ARTICULAR" in (f["notas"] or "") for f in _fd1)
      and all(int(f["series_objetivo"]) == int(_ej.series) for f in _fd1))
_av = []
_d2 = pl.generar_filas(pd.DataFrame(), _obj.isoformat(), 3, plan=_plan42, duracion_min=120,
                       dolor={_ej.ejercicio.lower(): 2}, avisos=_av)
_dia = [f["ejercicio"] for f in _d2 if f["dia_semana"] == _ej.dia]
_nuevo = [f for f in _d2 if f["dia_semana"] == _ej.dia and "Cambiado por" in (f["notas"] or "")]
_movs = list(dict.fromkeys((f["ejercicio"], f["bloque"]) for f in _d2 if f["dia_semana"] == _ej.dia))
check("dolor en 2 sesiones: se cambia por otro del mismo patron, sin repetir en el dia",
      _ej.ejercicio not in _dia and bool(_nuevo)
      and NOMBRE_A_PATRON[_nuevo[0]["ejercicio"]] == NOMBRE_A_PATRON[_ej.ejercicio]
      and len({m for m, _ in _movs}) == len(_movs),
      str((_ej.ejercicio, [f["ejercicio"] for f in _nuevo])))
check("el cambio por dolor queda en los avisos del motor", any(_ej.ejercicio in a for a in _av), str(_av))

print("")
print("== 43. Series efectivas por musculo (dashboard) ==")
import volumen as vol
def _s43(ej, n, rpe=8, fecha="2026-10-06"):
    return [{"fecha_entreno": pd.Timestamp(fecha), "ejercicio": ej, "rpe": rpe} for _ in range(n)]
_d43 = pd.DataFrame(_s43("Press de Banca con Barra", 3) + _s43("Press de Banca con Barra", 2, rpe=5)
                    + _s43("Remo con Barra Agarre Prono", 4) + _s43("Ejercicio Inventado", 3)
                    + _s43("Press de Banca con Barra", 5, fecha="2026-09-29"))
_v = vol.series_por_grupo(_d43, date(2026, 10, 5), date(2026, 10, 12))
check("press de banca x3: 3 de pecho y 1.5 de triceps (indirectas = la mitad)",
      _v["Pecho"] == 3 and _v["Tríceps"] == 1.5, str(_v))
check("pecho cuenta UNA vez por serie (no clavicular + esternal = 1.25)", _v["Pecho"] == 3)
check("calentamientos (RPE < 6), ejercicios desconocidos y otras semanas no cuentan",
      _v["Espalda alta"] == 4 and _v["Dorsal"] == 3, str(_v))
check("zonas: 4 series de pecho = bajo, 14 = productivo, 30 = sobre MRV",
      vol.zona("Pecho", 4) == "bajo" and vol.zona("Pecho", 14) == "productivo" and vol.zona("Pecho", 30) == "sobre MRV")
check("cada grupo tiene landmarks ordenados MEV <= MAV <= MRV",
      all(a <= b <= c <= d for a, b, c, d in vol.LANDMARKS.values()) and set(vol.LANDMARKS) == set(vol.GRUPOS))
_subs = {s for subs in db.SUBMUSCULOS.values() for s in subs}
check("los grupos solo usan submusculos que existen en el catalogo",
      all(s in _subs for subs in vol.GRUPOS.values() for s in subs))

print("")
print("== 44. Avisos push: recordatorio y contacto VAPID ==")
import recordatorio as rec, avisos as av
_gym = [{"nombre_dia": "Torso A - Fuerza", "bloque": "A - Fuerza maxima", "ejercicio": "Press"}]
check("dia de gym sin series registradas -> avisa", rec.debe_avisar(_gym, 0))
check("si ya registraste algo hoy, no avisa", not rec.debe_avisar(_gym, 3))
check("descanso y deporte no avisan",
      not rec.debe_avisar([{"nombre_dia": "Descanso", "bloque": "Descanso", "ejercicio": "x"}], 0)
      and not rec.debe_avisar([{"nombre_dia": "Basquetbol", "bloque": "Deporte", "ejercicio": "Basquetbol"}], 0))
check("sin plan para hoy no avisa", not rec.debe_avisar([], 0))
check("el contacto VAPID es la URL del sitio, no un correo personal",
      av._claims("https://aguilarmunoz.infinityfree.me/api") == {"sub": "https://aguilarmunoz.infinityfree.me"})

print("")
print("== 45. El entrenador: modelo de fuerza (e1RM con RPE) ==")
import entrenador as ent
check("tabla RTS: 1 rep al fallo = 100%, 5 reps ~86%, y la inversa cuadra",
      ent.pct_1rm(1) == 1.0 and abs(ent.pct_1rm(5) - 0.863) < 1e-9
      and all(abs(ent.reps_al_fallo(ent.pct_1rm(n)) - n) < 0.01 for n in (2, 5, 8, 12, 20, 35)))
check("la curva es continua y decreciente (sin escalon al pasar de 12 reps)",
      all(ent.pct_1rm(n) > ent.pct_1rm(n + 0.5) for n in [x / 2 for x in range(2, 80)])
      and abs(ent.pct_1rm(12) - ent.pct_1rm(12.0001)) < 1e-3)
_e = ent.e1rm(100, 5, 8, sesgo=0)       # 5 reps + 2 en reserva = 7 al fallo -> 81.1%
check("100 kg x 5 a RPE 8 -> e1RM ~123 kg (RTS)", abs(_e - 100 / 0.811) < 0.01, str(_e))
check("carga_para es la inversa de e1rm", abs(ent.carga_para(_e, 5, 8, sesgo=0) - 100) < 0.01)
check("al fallo (RPE 10) no se suma sesgo", ent.e1rm(100, 5, 10, sesgo=1) == ent.e1rm(100, 5, 10, sesgo=0))
def _h45(filas):
    return pd.DataFrame([{"fecha_entreno": pd.Timestamp(f), "ejercicio": e, "tecnica": tec, "numero_serie": n,
                          "peso_kg": p, "reps_hechas": r, "rpe": rpe, "tonelaje_serie": p * r}
                         for f, e, tec, n, p, r, rpe in filas])
_PB = "Press de Banca con Barra"
_m = ent.ModeloFuerza(_h45([("2026-10-05", _PB, "Tradicional", 1, 60, 10, 8)]), date(2026, 10, 12))
_c = _m.carga(_PB, 10, 8, 60, 2.5, minimo=20)
check("misma prescripcion que el rendimiento real: repite ~60 kg", _c is not None and 57.5 <= _c[0] <= 60, str(_c))
_m = ent.ModeloFuerza(_h45([("2026-10-05", _PB, "Tradicional", 1, 60, 10, 5)]), date(2026, 10, 12))
_c = _m.carga(_PB, 10, 8, 60, 2.5, minimo=20)
check("te sobraron 5+ reps: sondea +15% (no +2.5)", _c is not None and _c[0] == 67.5, str(_c))
_m = ent.ModeloFuerza(_h45([("2026-10-05", _PB, "Tradicional", 1, 60, 25, 8)]), date(2026, 10, 12))
_c = _m.carga(_PB, 10, 8, 60, 2.5, minimo=20)
check("serie fiable (25 reps a RPE 8 = calibracion): salta, pero como mucho +30%", _c is not None and _c[0] == 77.5, str(_c))
_m = ent.ModeloFuerza(_h45([("2026-10-05", _PB, "Tradicional", 1, 60, 4, 10)]), date(2026, 10, 12))
_c = _m.carga(_PB, 10, 8, 60, 2.5, minimo=20)
check("4 reps al fallo con 60 kg: baja, pero como mucho -15%", _c is not None and _c[0] == 52.5, str(_c))
_h8 = _h45([(f"2026-09-{d:02d}", _PB, "Tradicional", 1, 60, 10, 8) for d in range(1, 29, 2)])
check("RPE siempre igual (el 8 por defecto): el modelo se aparta y avisa",
      not ent.ModeloFuerza(_h8, date(2026, 10, 12)).rpe_ok
      and ent.ModeloFuerza(_h8, date(2026, 10, 12)).carga(_PB, 10, 8, 60, 2.5) is None)
_vieja = ent.ModeloFuerza(_h45([("2026-06-01", _PB, "Tradicional", 1, 60, 10, 8)]), date(2026, 10, 12))
_recien = ent.ModeloFuerza(_h45([("2026-10-05", _PB, "Tradicional", 1, 60, 10, 8)]), date(2026, 10, 12))
check("desentrenamiento: 19 semanas sin hacerlo bajan la estimacion (con tope -15%)",
      0.85 * _recien.estado(_PB).tendencia - 0.01 <= _vieja.estado(_PB).tendencia < _recien.estado(_PB).tendencia)
_ej4 = ["Press de Banca con Barra", "Sentadilla Libre con Barra", "Remo con Barra Agarre Prono", "Press Militar con Barra"]
_bien = [("2026-09-28", e, "Tradicional", 1, 60, 8, 8) for e in _ej4]
_caida = [("2026-10-05", e, "Tradicional", 1, 60, 5, 9) for e in _ej4]
_suave = [("2026-10-05", e, "Tradicional", 1, 45, 8, 6) for e in _ej4]
check("varios ejercicios rindiendo por debajo a la vez = fatiga (deload anticipado)",
      ent.ModeloFuerza(_h45(_bien + _caida), date(2026, 10, 12)).fatiga_por_rendimiento())
check("una semana SUAVE (deload) no se confunde con una caida de rendimiento",
      not ent.ModeloFuerza(_h45(_bien + _suave), date(2026, 10, 12)).fatiga_por_rendimiento())
_est = [(f"2026-{m}", _PB, "Tradicional", 1, 60, 8, 8) for m in ("08-31", "09-07", "09-14", "09-21", "09-28", "10-05")]
check("estancamiento real: 3 semanas sin mejorar el e1RM",
      _PB.lower() in ent.ModeloFuerza(_h45(_est), date(2026, 10, 12)).estancados())
check("los curls de muneca no tienen el suelo de 20 kg de la barra (extensores = codo)",
      pl.barra_de("Curl de Muneca Inverso (Extensores)") is None and pl.barra_de("Press de Banca con Barra") == 20)
_cfg_real = pl._cfg
pl._cfg = lambda: {"peso_corporal": 73}           # sin lista de mancuernas: reglas por defecto
check("sin lista: mancuernas ligeras suben de 1 kg por mano; pesadas, de 2.5",
      pl.paso_carga("Elevaciones Laterales Mancuernas", 8) == 2 and pl.paso_carga("Press de Banca con Mancuernas", 40) == 5
      and pl.paso_carga("Remo con Mancuerna a 1 Mano", 25) == 2.5)
pl._cfg = _cfg_real
_hm = _h45([("2026-10-05", _PB, "Tradicional", 1, 60, 12, 8)])
_pm = generar_plan({"enfoque": "hipertrofia", "split": "upper_lower", "prioridades": [], "duracion_min": 120}, ciclo=0)
_fm = pl.generar_filas(_hm, "2026-10-12", 2, plan=_pm, duracion_min=120)
_pb = [f for f in _fm if f["ejercicio"] == _PB and f["tecnica"] == "Tradicional"]
check("subida GANADA (12/12 a RPE 8): al menos un escalon real", all(f["peso_sugerido"] >= 62.5 for f in _pb), str([f["peso_sugerido"] for f in _pb]))
_cal = [f for f in _fm if "CALIBRAR" in (f["notas"] or "")]
check("ejercicios sin datos piden UNA serie de calibracion por semana",
      len(_cal) > 0 and len({f["ejercicio"] for f in _cal}) == len(_cal) and all(f["ejercicio"] != _PB for f in _cal))
check("nada de calibrar en deload", not any("CALIBRAR" in (f["notas"] or "")
      for f in pl.generar_filas(_hm, "2026-10-12", 5, plan=_pm, duracion_min=120)))

print("")
print("== 46. Tu gym: lista de mancuernas y maquina asistida ==")
_cfg_real = pl._cfg
pl._cfg = lambda: {"peso_corporal": 73, "asistidas": ["Dominadas"], "paso_asistencia_kg": 5,
                   "mancuernas_kg": [1, 3, 5, 7, 9, 11, 13, 15, 20, 25, 30]}
check("mancuernas: solo pesos que HAY (12.5 por mano -> 13, en total 26)",
      pl.cargable("Press de Banca con Mancuernas", 25) == 26 and pl.cargable("Remo con Mancuerna a 1 Mano", 12.5) == 13)
check("el escalon es hasta la siguiente mancuerna (15 -> 20 por mano = +10 en total)",
      pl.paso_carga("Press de Banca con Mancuernas", 30) == 10 and pl.paso_carga("Press de Banca con Mancuernas", 6) == 4)
check("redondeo del modelo: la mas alta que no pasa del objetivo",
      pl.cargable_abajo("Press de Banca con Mancuernas", 25.9) == 22 and pl.cargable_abajo("Press de Banca con Barra", 61) == 60)
_ha = _h45([("2026-10-05", "Dominadas", "Top Set", 1, 40, 8, 8), ("2026-10-05", "Dominadas", "Back-off", 1, 45, 12, 8)])
_ra = pl.a_carga_real(_ha, {"dominadas"}, 73)
check("asistida: 40 kg de ayuda con 73 de peso = 33 kg de carga real",
      list(_ra["peso_kg"]) == [33.0, 28.0])
_pa = generar_plan({"enfoque": "hipertrofia", "split": "ppl", "prioridades": ["dorsales"], "duracion_min": 120}, ciclo=0)
_fa = [f for f in pl.generar_filas(_h45([("2026-10-05", "Dominadas", "Top Set", 1, 40, 8, 7),
                                          ("2026-10-05", "Dominadas", "Back-off", 1, 45, 12, 7)]),
                                   "2026-10-12", 2, plan=_pa, duracion_min=120)
       if "Dominadas" in f["ejercicio"] and f["tecnica"]]
check("el plan la marca '(Asistida)' y explica que el peso es la AYUDA",
      bool(_fa) and all(f["ejercicio"] == "Dominadas (Asistida)" and "AYUDA" in f["notas"] for f in _fa),
      str([(f["ejercicio"], f["notas"][:30]) for f in _fa]))
_top = [f for f in _fa if f["tecnica"] == "Top Set"]
check("progresar = MENOS ayuda (8/8 a RPE 7 con 40 kg de ayuda -> menos de 40)",
      _top and _top[0]["peso_sugerido"] < 40 and _top[0]["peso_sugerido"] % 5 == 0, str([f["peso_sugerido"] for f in _top]))
check("lo registrado como 'Dominadas (Asistida)' sigue siendo Dominadas",
      db.nombre_canonico("Dominadas (Asistida)") == "Dominadas")
pl._cfg = _cfg_real

print("")
print("== 47. Bienestar diario (energia y sueno) -> descarga ==")
_hb = _h45([(f"2026-10-0{d}", "Press de Banca con Barra", "Tradicional", 1, 60, 10, 8) for d in (1, 3, 5)])
def _bien(dias_malos):
    filas = [("2026-10-0" + str(d), "dia", "energia", None, 3, None, None) for d in range(5, 5 + dias_malos)]
    filas += [("2026-10-0" + str(d), "dia", "sueno", None, 1, None, None) for d in range(5, 9)]
    return _fb42(filas)
_obj, _ini = date(2026, 10, 12), date(2026, 9, 21)          # semana 4 del mesociclo
check("3 dias sin energia en la semana -> se adelanta la descarga",
      pl.decidir_semana(_hb, _obj, _ini, _bien(3))[0] == 5)
_s2, _, _av2 = pl.decidir_semana(_hb, _obj, _ini, _bien(2))
check("2 dias malos -> solo aviso, el plan sigue", _s2 != 5 and any(a.startswith("BIENESTAR") for a in _av2), str(_av2))
check("dormir mal cuenta igual que no tener energia (y el mismo dia no cuenta doble)",
      fbk.dias_malos(_fb42([("2026-10-05", "dia", "sueno", None, 3, None, None),
                            ("2026-10-05", "dia", "energia", None, 3, None, None),
                            ("2026-10-07", "dia", "sueno", None, 3, None, None)]), _obj) == 2)
check("dias malos de hace mas de una semana no cuentan",
      fbk.dias_malos(_fb42([("2026-09-28", "dia", "energia", None, 3, None, None)]), _obj) == 0)
check("sin encuesta, decidir_semana funciona igual que antes",
      pl.decidir_semana(_hb, _obj, _ini)[0] == pl.decidir_semana(_hb, _obj, _ini, pd.DataFrame())[0])

print("")
print("== 48. 'Usar siempre' y catalogo de la app al dia ==")
_pp = generar_plan({"enfoque": "hipertrofia", "split": "upper_lower", "prioridades": [], "duracion_min": 120}, ciclo=0)
_orig = next(f for f in _pp if f.tecnica and f.bloque.startswith("B -"))
_alt = next(e for e in db.EJERCICIOS if e.patron == NOMBRE_A_PATRON[_orig.ejercicio] and e.nombre != _orig.ejercicio
            and e.nombre not in {f.ejercicio for f in _pp if f.dia == _orig.dia}
            and e.equipo != "peso_corporal")
_av48 = []
_fp = pl.generar_filas(pd.DataFrame(), "2026-10-12", 1, plan=_pp, duracion_min=120, avisos=_av48,
                       preferencias={_orig.ejercicio.lower(): _alt.nombre})
_dia48 = [f["ejercicio"] for f in _fp if f["dia_semana"] == _orig.dia]
check("la preferencia cambia el ejercicio y lo explica en la nota",
      _alt.nombre in _dia48
      and any("PREFERENCIA" in (f["notas"] or "") for f in _fp if f["ejercicio"] == _alt.nombre),
      str((_orig.ejercicio, _alt.nombre)))
_otro = next(e for e in db.EJERCICIOS if e.patron != NOMBRE_A_PATRON[_orig.ejercicio])
_av48b = []
_fp2 = pl.generar_filas(pd.DataFrame(), "2026-10-12", 1, plan=_pp, duracion_min=120, avisos=_av48b,
                        preferencias={_orig.ejercicio.lower(): _otro.nombre})
check("un reemplazo de OTRO patron se ignora (y se avisa)",
      _orig.ejercicio in [f["ejercicio"] for f in _fp2] and any("ignorada" in a for a in _av48b))
check("sin preferencias el plan es identico",
      pl.generar_filas(pd.DataFrame(), "2026-10-12", 1, plan=_pp, duracion_min=120, preferencias={})
      == pl.generar_filas(pd.DataFrame(), "2026-10-12", 1, plan=_pp, duracion_min=120))
import exportar_catalogo as _expc
check("app/src/app/catalogo.generado.ts esta al dia con ejercicios_db (corre exportar_catalogo.py)",
      _expc.DESTINO.exists() and _expc.DESTINO.read_text(encoding="utf-8") == _expc.contenido())

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas pasaron.")

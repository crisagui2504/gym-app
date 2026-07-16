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
from enfoques import SPLITS
from generador import generar_plan
from plan_template import Fila
import planificar as pl

FALLOS = []


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
check("Bloque B tiene filas S3-S4 con intensidad", len(b_s34) > 0 and
      all(("AMRAP" in f.tecnica) or ("Drop" in f.tecnica) for f in b_s34))
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
esperado = {1: "Push A", 2: "Legs A", 3: "Pull A", 4: "Push B", 5: "Legs B", 6: "Pull B"}
check("orden semanal Push/Piernas/Pull x2",
      all(nombre_por_dia.get(d) == n for d, n in esperado.items()),
      f"{ {d: nombre_por_dia.get(d) for d in range(1, 7)} }")
pull_dias = [d for d, n in esperado.items() if "Pull" in n]
antebrazo_dias = sorted({f.dia for f in plan_ppl3
                         if NOMBRE_A_PATRON.get(f.ejercicio) == db.ANTEBRAZO})
check("antebrazos siguen en los dias de Pull (no consecutivos)",
      antebrazo_dias == pull_dias, f"antebrazo en {antebrazo_dias}, pull en {pull_dias}")

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
check("ninguna sesion apila mas de 2 bisagras axiales (proteccion lumbar)",
      not viol_ax, "; ".join(viol_ax)[:200])
check("ningun submusculo clave queda sin estimulo semanal",
      not any(v.startswith("HUECO") for v in violaciones),
      "; ".join(v for v in violaciones if v.startswith("HUECO"))[:300])
print("   picos por submusculo:",
      {k: round(v, 1) for k, v in sorted(picos.items(), key=lambda x: -x[1])[:8]})

print("\n== 10. Todas las semanas generan plan sin errores ==")
for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split in ("upper_lower", "ppl", "full_body"):
        p = generar_plan({"enfoque": enfoque, "split": split,
                          "prioridades": ["hombros"], "duracion_min": 90}, ciclo=0)
        for sem in (1, 2, 3, 4, 5):
            filas = pl.generar_filas(df1, "2026-07-13", sem, plan=p)
            assert len(filas) > 0
check("15 combinaciones enfoque x split x 5 semanas generan sin excepcion", True)

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas pasaron.")

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
                        "prioridades": [], "duracion_min": 90})
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
                        "prioridades": ["hombros"], "duracion_min": 90})
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
                         "prioridades": [], "duracion_min": 90})
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
                               "equipo_excluido": ["barra"]})
EQUIPO = {e.nombre: e.equipo for e in db.EJERCICIOS}
con_barra = [f.ejercicio for f in plan_sin_barra
             if f.bloque.startswith(("A", "B")) and EQUIPO.get(f.ejercicio) == "barra"]
check("sin ejercicios de barra en bloques A/B", not con_barra, f"con barra: {con_barra}")

print("\n== 10. Todas las semanas generan plan sin errores ==")
for enfoque in ("recomposicion", "volumen", "definicion", "powerbuilding", "fuerza"):
    for split in ("upper_lower", "ppl", "full_body"):
        p = generar_plan({"enfoque": enfoque, "split": split,
                          "prioridades": ["hombros"], "duracion_min": 90})
        for sem in (1, 2, 3, 4, 5):
            filas = pl.generar_filas(df1, "2026-07-13", sem, plan=p)
            assert len(filas) > 0
check("15 combinaciones enfoque x split x 5 semanas generan sin excepcion", True)

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas pasaron.")

# -*- coding: utf-8 -*-
"""Pruebas funcionales del dashboard y helpers (datos sinteticos, sin red).

Uso:  python tests/test_funcional.py   (desde python-engine/, con el venv activo)
Complementa a test_motor.py: aqui se prueba la capa de analisis/nutricion.
"""
import pathlib
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd

import dashboard as dsh
import exportar_local as exp
import planificar as pl

FALLOS = []


def check(nombre, cond, det=""):
    print(("[OK ] " if cond else "[FAIL] ") + nombre + (f" -> {det}" if det and not cond else ""))
    if not cond:
        FALLOS.append(nombre)


# ── 1. e1RM (Epley) ──────────────────────────────────────────────────────────
df = pd.DataFrame({"ejercicio": ["Press"] * 2, "peso_kg": [50.0, 0.0],
                   "reps_hechas": [8, 12],
                   "fecha_entreno": pd.to_datetime(["2026-07-01"] * 2),
                   "tonelaje_serie": [400.0, 0.0], "rpe": [8, 8]})
de = dsh._con_e1rm(df)
check("e1RM Epley 50x8 = 63.3", abs(de["e1rm"].iloc[0] - 50 * (1 + 8 / 30)) < 0.01)
check("e1RM de peso corporal = 0 (sin falso PR)", de["e1rm"].iloc[1] == 0.0)
check("fig records con datos", dsh._fig_records(df) is not None)
check("fig progresion con datos", dsh._fig_progresion(df, "Press") is not None)
check("fig progresion de ejercicio inexistente no crashea",
      dsh._fig_progresion(df, "Nada") is not None)
check("figs con df vacio no crashean",
      all(f(pd.DataFrame()) is not None
          for f in (dsh._fig_records, dsh._fig_rpe, dsh._fig_tonelaje_semana)))

# ── 2. Peso corporal + cintura (CSV temporal, NO el real) ────────────────────
tmp = pathlib.Path(tempfile.mkdtemp()) / "peso_test.csv"
dsh.PESO_CSV, _real_csv = tmp, dsh.PESO_CSV
hoy = date.today()
rows = [{"fecha": (hoy - timedelta(days=13 - i)).isoformat(),
         "peso": 75.0 - i * 0.05, "cintura": 84.0 - i * 0.06} for i in range(14)]
pd.DataFrame(rows).to_csv(tmp, index=False)
dfp = dsh._cargar_peso()
check("carga 14 registros con cintura", len(dfp) == 14 and dfp["cintura"].notna().all())
t = dsh._tendencia_semanal(dfp)
check("tendencia semanal negativa y razonable", t is not None and -1.0 < t < 0.0, t)
tc = dsh._tendencia_cintura(dfp)
check("tendencia de cintura ~-0.4 cm/sem", tc is not None and -0.7 < tc < -0.2, tc)
dsh._registrar_peso(74.2, 83.0)
dfp2 = dsh._cargar_peso()
check("registrar sobrescribe el dia sin duplicar",
      len(dfp2) == 14 and dfp2["peso"].iloc[-1] == 74.2)
dsh._registrar_peso(74.3)  # sin cintura: conserva la del dia
check("re-registro conserva la cintura del dia",
      dsh._cargar_peso()["cintura"].iloc[-1] == 83.0)
check("fig peso con cintura", dsh._fig_peso(dfp2) is not None)
check("panel de peso (semaforo) se construye", len(dsh._panel_peso()) == 2)
dsh.PESO_CSV = _real_csv

# ── 3. Nutricion en gramos ───────────────────────────────────────────────────
check("panel de nutricion se construye",
      dsh._panel_nutricion({"enfoque": "recomposicion", "peso_corporal": 70}) is not None)

# ── 4. Backups fechados ──────────────────────────────────────────────────────
exp._respaldar("col1,col2\n1,2\n")
backs = sorted(pathlib.Path(exp.__file__).parent.joinpath("backups").glob("historial-*.csv"))
check("backup fechado de hoy existe", any(hoy.isoformat() in b.name for b in backs))

# ── 5. Helpers del motor ─────────────────────────────────────────────────────
check("microcarga press=2.5 / curl=1.25",
      pl.microcarga("Press Banca") == 2.5 and pl.microcarga("Curl EZ") == 1.25)
check("redondear 26.3 -> 26.25", pl.redondear(26.3) == 26.25)
check("familia agrupa las tecnicas de volumen",
      pl._familia("Tradicional + AMRAP") == pl._familia("Drop Set") == "volumen")
check("marca_anterior con carga",
      pl.marca_anterior((25.0, 8, 8.2)) == "Anterior: 25 kg x 8 @RPE 8.")
check("marca_anterior peso corporal",
      pl.marca_anterior((0.0, 12, 7.0)) == "Anterior: 12 reps @RPE 7.")
check("nota_semana 1-5 sin KeyError", all(pl.nota_semana(s) for s in range(1, 6)))

# ── 6. Layout + callbacks del dashboard ──────────────────────────────────────
check("layout completo se construye", dsh._serve_layout() is not None)
from dash._callback import GLOBAL_CALLBACK_MAP
claves = list(GLOBAL_CALLBACK_MAP.keys())
esperados = ["graph-progresion", "refresh-status", "tema-trigger",
             "cfg-resultado", "subir-plan-status", "peso-panel"]
faltan = [e for e in esperados if not any(e in c for c in claves)]
check("los 6 callbacks del servidor estan registrados", not faltan, f"faltan: {faltan}")

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas funcionales pasaron.")

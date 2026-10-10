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
_pp = dsh._panel_peso()
check("panel de peso: grafica + calorias adaptativas + proteina",
      len(_pp) == 3 and "adaptativas" in str(_pp[1]) and "Prote" in str(_pp[2]))
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
print("== Modo demo del dashboard: aislado y de solo lectura ==")
import demo_motor as _dm
import exportar_demo as _dem
_cfg_ruta = pathlib.Path(dsh.__file__).resolve().parent / "config_usuario.json"
_cfg_antes = _cfg_ruta.read_text(encoding="utf-8") if _cfg_ruta.exists() else None
with dsh.server.test_request_context("/", headers={"Cookie": "gym_demo=1"}):
    _df, _estado = dsh._cargar_df()
    check("con la cookie de demo se ven los datos del atleta virtual", _estado == "demo" and len(_df) > 100)
    check("la demo termina la semana pasada (fechas relativas a hoy)",
          _df["fecha_entreno"].max().date() < __import__("datetime").date.today())
    check("en demo no se muestran tu peso ni tu encuesta",
          "oculto" in str(dsh._panel_peso()) and dsh._panel_encuesta() is None)
    check("en demo la configuracion muestra la de la DEMO y avisa que no toca la tuya",
          "no se toca" in str(dsh._tab_config_children()))
    check("en demo ningun otro callback escribe",
          "no se sube" in str(dsh._subir_plan(1)) and "oculto" in str(dsh._guardar_peso_cb(1, 80, None))
          and "NoUpdate" in type(dsh._cambiar_tema(1)).__name__
          and "Modo demo" in str(dsh._refrescar_datos(1)[0]))
    _meso = str(dsh._tabla_mesociclo(_df))
    check("en demo el mesociclo muestra las 5 semanas", all(s in _meso for s in ("S1", "S2", "S3", "S4", "S5")))

import alimentos_mx as _alx
_precios_antes = _alx.PRECIOS_USUARIO.read_text(encoding="utf-8") if _alx.PRECIOS_USUARIO.exists() else None
with dsh.server.test_request_context("/", headers={"Cookie": "gym_demo=1"}):
    _mv = str(dsh._generar_menu_cb(1, ["carnes", "pescado"], []))
    check("en demo se puede generar el menu (vegetariano) y se ve la lista del super",
          "Lista del s" in _mv and "Pollo" not in _mv and "Atún" not in _mv)
    check("en demo los precios no se guardan", "no se guardan" in str(dsh._guardar_precios_cb(1, [])[1]))
check("tus precios siguen intactos despues de usar la demo",
      _precios_antes == (_alx.PRECIOS_USUARIO.read_text(encoding="utf-8") if _alx.PRECIOS_USUARIO.exists() else None))

# guardar la config en demo: va a una COOKIE, nunca al archivo
_cli = dsh.server.test_client()
_cli.set_cookie("gym_demo", "1")
_r = _cli.post("/_dash-update-component", json={
    "output": "cfg-resultado.children", "outputs": {"id": "cfg-resultado", "property": "children"},
    "inputs": [{"id": "cfg-guardar", "property": "n_clicks", "value": 1}],
    "state": [{"id": "cfg-enfoque", "property": "value", "value": "fuerza"},
              {"id": "cfg-split", "property": "value", "value": "ppl"},
              {"id": "cfg-prioridades", "property": "value", "value": ["pecho"]},
              {"id": "cfg-peso", "property": "value", "value": 99},
              {"id": "cfg-duracion", "property": "value", "value": 60},
              {"id": "cfg-equipo", "property": "value", "value": []}],
    "changedPropIds": ["cfg-guardar.n_clicks"]})
_sc = _r.headers.get("Set-Cookie", "")
check("en demo, guardar la configuracion la pone en la cookie de la demo",
      _r.status_code == 200 and "gym_demo_cfg=fuerza|ppl|60|pecho" in _sc, f"{_r.status_code} {_sc[:120]}")
# la cookie tal cual la devolvio el servidor (como la reenviaria el navegador)
with dsh.server.test_request_context("/", headers={"Cookie": "gym_demo=1; " + _sc.split(";")[0]}):
    check("la demo usa el tipo de entreno elegido (PPL fuerza)",
          dsh._demo_cfg()["split"] == "ppl" and dsh._demo_cfg()["enfoque"] == "fuerza")
check("tu config sigue intacta despues de usar la demo",
      _cfg_antes == (_cfg_ruta.read_text(encoding="utf-8") if _cfg_ruta.exists() else None))
with dsh.server.test_request_context("/"):
    check("sin la cookie, el dashboard no esta en demo", dsh._cargar_df()[1] != "demo")
_cli = dsh.server.test_client()
check("/demo pone la cookie y /demo/salir quita las dos",
      "gym_demo=1" in _cli.get("/demo").headers.get("Set-Cookie", "")
      and all(f"{c}=;" in " ".join(_cli.get("/demo/salir").headers.getlist("Set-Cookie"))
              for c in ("gym_demo", "gym_demo_cfg")))

print()
print("== API publica de la demo (la usa la app) ==")
_o = _cli.get("/demo/api/opciones")
check("/demo/api/opciones lista enfoques, splits y las 5 semanas, con CORS",
      _o.headers.get("Access-Control-Allow-Origin") == "*"
      and len(_o.json["enfoques"]) >= 5 and len(_o.json["splits"]) >= 4 and len(_o.json["semanas"]) == 5)
_e = _cli.get("/demo/api/escenario?enfoque=fuerza&split=ppl&duracion=60")
_sem = _e.json["semanas"] if _e.status_code == 200 else {}
check("/demo/api/escenario genera las 5 semanas x 7 dias del tipo pedido",
      _e.headers.get("Access-Control-Allow-Origin") == "*" and sorted(_sem) == ["1", "2", "3", "4", "5"]
      and all(sorted(_sem[s]) == [str(d) for d in range(1, 8)] for s in _sem)
      and _e.json["config"]["split"] == "ppl")
check("S5 es deload: menos series que S4",
      sum(f["series_objetivo"] for d in _sem["5"].values() for f in d)
      < sum(f["series_objetivo"] for d in _sem["4"].values() for f in d))
check("la API tolera parametros basura (cae a la config por defecto)",
      _cli.get("/demo/api/escenario?enfoque=<x>&split=../../etc&duracion=abc").json["config"]["split"] == "upper_lower")
_todos = [(e, s) for e in _dm.opciones()["enfoques"] for s in _dm.opciones()["splits"]][:3]
check("cualquier enfoque x split genera dias con ejercicios",
      all(any(_dm.escenario({"enfoque": e["id"], "split": s["id"]})["semanas"][1][d] for d in range(1, 8))
          for e, s in _todos))
_ts = (pathlib.Path(_dem.DESTINO_TS)).read_text(encoding="utf-8")
check("el respaldo de la app existe y trae las 5 semanas y las opciones",
      "DEMO_ESCENARIO" in _ts and "DEMO_OPCIONES" in _ts and _ts.strip() == _dem.generar().strip())

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas funcionales pasaron.")

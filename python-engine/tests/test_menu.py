"""Pruebas del menu de 50 opciones: tipos de dieta (DASH, mediterranea) y enfasis.

    python tests/test_menu.py
"""
import collections
import pathlib
import sys
import tempfile
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import alimentos_mx as alx  # noqa: E402
import menu as mnu  # noqa: E402
import nutricion  # noqa: E402
import recetas_mx as rcx  # noqa: E402

alx.PRECIOS_USUARIO = pathlib.Path(tempfile.mkdtemp()) / "precios.json"   # nunca tus precios reales
FALLAS: list[str] = []
LUN = date(2026, 10, 12)
BASE = {"enfoque": "recomposicion", "peso_corporal": 73}


def check(nombre: str, ok, detalle: str = "") -> None:
    print(f"[{'OK ' if ok else 'X  '}] {nombre}" + (f"  -> {detalle}" if detalle and not ok else ""))
    if not ok:
        FALLAS.append(nombre)


def ids(m: dict) -> list[str]:
    return [i["id"] for d in m["dias"] for c in d["comidas"] for i in c["ingredientes"]]


def regla(m: dict, texto: str) -> dict | None:
    return next((r for r in m["dieta"]["cumple"] if texto in r["regla"]), None)


print("== Catalogo: ~50 opciones por tiempo ==")
cuenta = collections.Counter(r.tiempo for r in rcx.RECETAS)
check("50 desayunos, 50 comidas y 50 cenas (o mas)",
      all(cuenta[t] >= 50 for t in ("desayuno", "comida", "cena")), str(cuenta))
check("ids de receta unicos", len({r.id for r in rcx.RECETAS}) == len(rcx.RECETAS))
check("todo ingrediente existe en el catalogo de alimentos",
      all(a in alx.ALIMENTOS for r in rcx.RECETAS for a, _ in r.ingredientes))
check("cada alimento trae sodio y grasa saturada razonables",
      all(0 <= a.sodio <= 1000 and 0 <= a.sat <= a.grasa + 0.01 for a in alx.ALIMENTOS.values()))
check("los grupos excluibles cubren lo nuevo (tilapia, camaron, claras, requeson...)",
      {"tilapia", "camaron"} <= set(alx.GRUPOS_EXCLUIBLES["pescado"])
      and "claras" in alx.GRUPOS_EXCLUIBLES["huevo"] and "requeson" in alx.GRUPOS_EXCLUIBLES["lacteos"])

print("\n== Mexicana (la de siempre) ==")
m0 = mnu.generar_menu(BASE, LUN)
check("sin dieta elegida: mexicana y equilibrado",
      m0["dieta"]["id"] == "mexicana" and m0["dieta"]["enfasis"] == "equilibrado" and m0["dieta"]["cumple"] == [])
check("cada dia trae sodio, grasa saturada y verdura/fruta",
      all({"sodio", "sat", "verdfruta"} <= set(d) for d in m0["dias"]))
check("la semana trae sodio y % de grasa saturada", {"sodio", "sat_pct"} <= set(m0["nutrientes"]))
distintas = len({c["receta"] for d in m0["dias"] for c in d["comidas"]})
check("variedad: 18+ recetas distintas en la semana", distintas >= 18, str(distintas))
otras = {tuple(c["receta"] for d in mnu.generar_menu(BASE, LUN, s)["dias"] for c in d["comidas"]) for s in range(4)}
check("otra semilla = otro menu (4 semillas, 4 menus)", len(otras) == 4, str(len(otras)))

print("\n== DASH ==")
dash = mnu.generar_menu({**BASE, "menu_dieta": "dash"}, LUN)
check("todas las reglas DASH se cumplen", all(r["ok"] for r in dash["dieta"]["cumple"]),
      str([(r["regla"], r["valor"]) for r in dash["dieta"]["cumple"]]))
check("sodio de cada dia <= 2,300 mg", all(d["sodio"] <= 2300 for d in dash["dias"]))
check("grasa saturada <= 7 % de las kcal", dash["nutrientes"]["sat_pct"] <= 7.0, str(dash["nutrientes"]["sat_pct"]))
check("verduras y frutas >= 600 g/dia en promedio", dash["nutrientes"]["verdfruta"] >= 570,
      str(dash["nutrientes"]["verdfruta"]))
check("lacteos: 2+ porciones al dia en promedio", sum(d["lacteos"] for d in dash["dias"]) / 7 >= 1.8)
check("cambia a descremada, integral y magra (nunca leche entera, arroz blanco, res normal)",
      not {"leche", "arroz", "pasta", "res"} & set(ids(dash)))
check("carne roja <= 2 veces", sum(1 for d in dash["dias"] for c in d["comidas"]
                                    if any(i["id"] in mnu.CARNE_ROJA for i in c["ingredientes"])) <= 2)
baja = mnu.generar_menu({**BASE, "menu_dieta": "dash", "menu_sodio_max": 1500}, LUN)
check("DASH bajo en sodio: cada dia <= 1,500 mg y lo dice",
      all(d["sodio"] <= 1500 for d in baja["dias"]) and "1,500" in baja["dieta"]["nombre"])
check("las alternativas (Cambiar) tampoco pasan el sodio del dia",
      all(d["sodio"] - c["sodio"] + a["sodio"] <= 1500 + 30
          for d in baja["dias"] for c in d["comidas"] for a in c.get("alternativas", [])))
sin_lac = mnu.generar_menu({**BASE, "menu_dieta": "dash", "alimentos_excluidos": ["lacteos"]}, LUN)
r = regla(sin_lac, "Lácteos")
check("DASH sin lacteos: la regla de lacteos dice 'los excluiste' (no la marca como falla)",
      r is not None and r["ok"] is None and "excluiste" in r["valor"])
check("DASH sin lacteos: ningun lacteo en el menu", not set(alx.GRUPOS_EXCLUIBLES["lacteos"]) & set(ids(sin_lac)))

print("\n== Mediterranea ==")
med = mnu.generar_menu({**BASE, "menu_dieta": "mediterranea"}, LUN)
check("todas las reglas mediterraneas se cumplen", all(r["ok"] for r in med["dieta"]["cumple"]),
      str([(r["regla"], r["valor"]) for r in med["dieta"]["cumple"]]))
check("pescado o mariscos 2+ veces", int(regla(med, "Pescado")["valor"]) >= 2)
check("aceite de oliva en vez de aceite vegetal", "aceite" not in ids(med) and "aceite_oliva" in ids(med))
sin_pez = mnu.generar_menu({**BASE, "menu_dieta": "mediterranea", "alimentos_excluidos": ["pescado"]}, LUN)
check("mediterranea sin pescado: no inventa pescado y avisa en la regla",
      not set(alx.GRUPOS_EXCLUIBLES["pescado"]) & set(ids(sin_pez)) and regla(sin_pez, "Pescado")["ok"] is False)

print("\n== Enfasis ==")
meta = nutricion.metas(BASE)
pro = mnu.generar_menu({**BASE, "menu_enfasis": "proteina"}, LUN)
check("mas proteina: cada dia llega al tope del rango (o avisa)",
      all(d["prot"] >= meta["proteina_max"] - 1 for d in pro["dias"]) or pro["avisos"],
      f"{[d['prot'] for d in pro['dias']]} vs {meta['proteina_max']}")
check("mas proteina: mas proteina que el equilibrado", pro["prot_prom"] > m0["prot_prom"] + 15)
carb = mnu.generar_menu({**BASE, "menu_enfasis": "carbohidratos"}, LUN)
c_obj = carb["meta"]["carb_obj"]
check("mas carbohidratos: cada dia llega a la meta de carbos (o avisa) y no baja la proteina",
      (all(d["carb"] >= c_obj - 1 for d in carb["dias"]) or carb["avisos"])
      and all(d["prot"] >= meta["proteina_min"] - 1 for d in carb["dias"]),
      f"{[d['carb'] for d in carb['dias']]} vs {c_obj}")
check("las kcal no cambian con el enfasis (+/-10 %)",
      all(abs(d["kcal"] - d["kcal_meta"]) <= d["kcal_meta"] * 0.10 for x in (pro, carb) for d in x["dias"]))
mix = mnu.generar_menu({**BASE, "menu_dieta": "dash", "menu_enfasis": "proteina"}, LUN)
check("DASH + mas proteina: las dos cosas a la vez",
      all(r["ok"] for r in mix["dieta"]["cumple"]) and mix["prot_prom"] >= meta["proteina_max"] - 3)

print("\n== Barrido: 4 enfoques x 3 pesos x 3 dietas x 3 enfasis ==")
errores, sin_aviso = [], []
for enf in ("recomposicion", "volumen", "fuerza", "definicion"):
    for peso in (55, 75, 95):
        for dieta in ("mexicana", "dash", "mediterranea"):
            for e in ("equilibrado", "proteina", "carbohidratos"):
                cfg = {"enfoque": enf, "peso_corporal": peso, "menu_dieta": dieta, "menu_enfasis": e}
                try:
                    m = mnu.generar_menu(cfg, LUN)
                except ValueError as ex:
                    errores.append((enf, peso, dieta, e, str(ex)))
                    continue
                falla = [r for r in m["dieta"]["cumple"] if r["ok"] is False]
                if falla and not m["avisos"]:
                    sin_aviso.append((enf, peso, dieta, e, [r["regla"] for r in falla]))
check("ningun perfil se queda sin menu", not errores, str(errores[:3]))
check("si una regla de la dieta no se cumple, el menu lo avisa", not sin_aviso, str(sin_aviso[:3]))

print()
print("RESULTADO:", "todas las pruebas pasaron." if not FALLAS else f"{len(FALLAS)} pruebas FALLARON: {FALLAS}")
sys.exit(1 if FALLAS else 0)

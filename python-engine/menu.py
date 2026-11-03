"""Menu semanal BARATO que cumple tus calorias y tu proteina.

Para cada dia prueba todas las combinaciones de desayuno x comida x cena x
tamano de porcion x colacion (~70 mil, con numpy tarda milisegundos) y elige
la MAS BARATA que:
  - queda a +/-6 % de tus kcal objetivo (nutricion.metas: enfoque + ajustes), y
  - llega a tu proteina minima (rango g/kg del enfoque x tu peso).
La variedad se cuida con penalizaciones: repetir una receta en la semana
"cuesta" de mas y cada receta tiene un tope de veces; la comida y la cena del
mismo dia nunca repiten la fuente de proteina.

Comida mexicana de diario de casa (pollo, carne, huevo, frijol, tortilla,
arroz...). Como en casa, la comida se cocina para 2 dias: lo que sobra del
lunes es la comida del martes (y asi miercoles-jueves y viernes-sabado). Los
precios son de productos reales (productos_mx.py: Chedraui, Walmart, Sam's,
3B, mercado y tortilleria) y la lista del super redondea a paquetes enteros.
Resultado: los 7 dias, la lista del super por tienda y el costo.
"""
from __future__ import annotations

import copy
import json
import math
import pathlib
import random
from datetime import date, timedelta

import numpy as np

import alimentos_mx as alx
import nutricion
import productos_mx as pmx
from dataclasses import replace
from recetas_mx import POCO_COMUNES, RECETAS, Receta

AQUI = pathlib.Path(__file__).resolve().parent
MENU_LOCAL = AQUI / "menu_semana.json"       # copia para el dashboard (ignorada por git)
NO_ME_GUSTA_LOCAL = AQUI / "no_me_gusta.json"  # copia de lo que marcaste en la app o el dashboard
ESCALAS = (0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)  # tamano de las 3 comidas del dia
TOLERANCIA_KCAL = 0.05
MAX_HUEVO_DIA = 200          # g: 4 huevos al dia como mucho (variedad, no salud)
TOPE_USOS = {"desayuno": 2, "comida": 1, "cena": 1, "colacion": 2}   # con ~50 opciones por tiempo
PENALIZA_REPETIR = 9.0       # $ "virtuales" por cada vez que la receta ya salio
NOMBRES_DIA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
RUIDO = 4.0                  # $ virtuales de azar por receta (variedad entre semanas)
NUEVO_INGREDIENTE = 5.0      # $ virtuales por cada ingrediente que no esta ya en tu lista de la semana
SAL_G_MG = 393               # mg de sodio en 1 g de sal (cloruro de sodio)
POR_TIEMPO_DIA = 18          # recetas de cada tiempo que se combinan cada dia (de ~50; cambia el dia a dia)
POR_COLACION_DIA = 24        # colaciones que entran cada dia (de ~70): la memoria de la VM no da para todas
# La comida se cocina para 2 dias: dia (0 = lunes) en que se comen las sobras -> dia en que se cocino
SOBRAS_DE = {1: 0, 3: 2, 5: 4}
DIAS_COCINA = set(SOBRAS_DE.values())
# Veces por semana como mucho (comidas): que no salga soya o sardina diario por baratas
MAX_SEMANA = {"soya": 2, "habas": 1, "tofu": 2, "sardina": 2, "camaron": 2, "lentejas": 3, "garbanzo": 3,
              "pollo_rostizado": 3}
# Las 4 comidas que se cocinan en la semana, como en casa: pollo hasta 2 veces y
# res, cerdo, pescado o una sin carne (frijol, lentejas, soya, huevo) una vez cada
# una. Sin esto saldria pollo y soya diario por ser lo mas barato. Solo aplica si
# comes carne (si la excluiste, no hay de donde variar).
FAMILIA = {"pollo": "pollo", "pechuga": "pollo", "pollo_rostizado": "pollo", "res": "res", "res_magra": "res",
           "cerdo": "cerdo", "atun": "pescado", "sardina": "pescado", "tilapia": "pescado", "camaron": "pescado"}
MAX_FAMILIA = {"pollo": 2, "res": 1, "cerdo": 1, "pescado": 1, "sin_carne": 1}


def familia(r: Receta) -> str:
    return FAMILIA.get(_fuente(r), "sin_carne")
N_ALTERNATIVAS = {"colacion": 20, "comida": 4}      # "Cambiar" en la app; desayuno y cena, 3

# Grupos para las reglas de cada dieta
CARNE_ROJA = {"res", "res_magra", "cerdo"}
CARNE = {"pollo", "pechuga", "pollo_rostizado", "res", "res_magra", "cerdo", "jamon", "salchicha"}
PESCADO = {"atun", "sardina", "tilapia", "camaron"}
NUECES = {"nuez", "almendra", "cacahuate", "crema_cacahuate", "chia", "pepitas"}
LACTEO_PORCION = {"leche": 250, "leche_light": 250, "yogur": 200, "yogur_griego": 200,
                  "queso_fresco": 40, "panela": 40, "requeson": 60, "queso_oaxaca": 30,
                  "cottage": 100}     # g de una porcion

# Tipos de dieta (patrones de alimentacion con evidencia). Cada uno puede
# CAMBIAR ingredientes (leche entera -> descremada...) y poner REGLAS diarias o
# semanales que el generador respeta.
#   DASH (NHLBI): sodio <= 2,300 mg (o 1,500 en la version baja), 4-5 porciones
#     de verduras y 4-5 de frutas, 2-3 de lacteos bajos en grasa, cereales
#     integrales, carnes magras y poca grasa saturada.
#   Mediterranea (piramide de la Fundacion Dieta Mediterranea / PREDIMED):
#     aceite de oliva como grasa, pescado >= 2 veces/semana, carne roja < 2,
#     leguminosas y nueces seguido, mucha verdura y fruta.
#   Mexicana (Guias Alimentarias 2023, Plato del Bien Comer): la de siempre.
DIETAS = {
    "mexicana": {"nombre": "Mexicana equilibrada (Plato del Bien Comer)", "cambios": {}, "sodio_max": None,
                 "sat_pct": None, "verdfruta": (0, 0), "lacteos_min": 0, "roja_max": None, "pescado_min": 0},
    "dash": {"nombre": "DASH (presión arterial)",
             "cambios": {"leche": "leche_light", "arroz": "arroz_integral", "pasta": "pasta_integral",
                         "res": "res_magra", "pollo": "pechuga", "queso_fresco": "panela"},
             "sodio_max": 2300, "sal_g": 2.0, "sat_pct": 0.07, "verdfruta": (400, 600), "lacteos_min": 2, "roja_max": 2,
             "pescado_min": 0},
    "mediterranea": {"nombre": "Mediterránea",
                     "cambios": {"aceite": "aceite_oliva", "res": "res_magra"},
                     "sodio_max": None, "sat_pct": 0.09, "verdfruta": (350, 500), "lacteos_min": 0,
                     "roja_max": 1, "pescado_min": 2},
    # Vegetariana (lacto-ovo): sin carne ni pescado; la proteina sale de huevo, lacteos,
    # leguminosas y soya (Position of the Academy of Nutrition and Dietetics, 2016).
    "vegetariana": {"nombre": "Vegetariana (con huevo y lácteos)", "cambios": {}, "sodio_max": None,
                    "sat_pct": 0.10, "verdfruta": (400, 500), "lacteos_min": 0, "roja_max": None, "pescado_min": 0,
                    "excluye": ("carnes", "pescado")},
    # Flexitariana: casi siempre sin carne; carne (pollo, res, cerdo...) en comida o cena
    # hasta 5 veces por semana y roja 1; pescado al menos 1 (EAT-Lancet 2019).
    "flexitariana": {"nombre": "Flexitariana (poca carne)", "cambios": {"res": "res_magra"}, "sodio_max": None,
                     "sat_pct": 0.10, "verdfruta": (400, 500), "lacteos_min": 0, "roja_max": 1, "pescado_min": 1,
                     "carne_max": 5},
    # Baja en carbohidratos MODERADA (<= 30 % de las kcal): misma perdida de grasa que
    # una baja en grasa con las mismas kcal y proteina (DIETFITS, Gardner 2018); sirve si
    # asi te llenas mas. No es keto: tortilla y fruta van, en menos cantidad.
    "baja_carbos": {"nombre": "Baja en carbohidratos (moderada)", "cambios": {}, "sodio_max": None,
                    "sat_pct": 0.10, "verdfruta": (400, 500), "lacteos_min": 0, "roja_max": None, "pescado_min": 0,
                    "carb_pct": 0.30},
    # Control de glucosa (diabetes tipo 2 o prediabetes): carbohidratos <= 45 % de las kcal,
    # integrales y fibra >= 14 g por 1,000 kcal (ADA Standards of Care 2026; consulta a tu medico).
    "glucosa": {"nombre": "Control de glucosa (diabetes y prediabetes)",
                "cambios": {"arroz": "arroz_integral", "pasta": "pasta_integral", "bolillo": "pan_integral",
                            "cereal": "avena", "tortilla_harina": "tortilla"},
                "sodio_max": None, "sat_pct": 0.10, "verdfruta": (400, 500), "lacteos_min": 0, "roja_max": None,
                "pescado_min": 0, "carb_pct": 0.45, "fibra_1000": 14},
}
# Para que sirve cada una (el dashboard lo muestra al elegir)
PARA_QUE = {
    "mexicana": "Comer normal y barato: la de diario.",
    "dash": "Bajar la presión arterial: poca sal y más verdura, fruta y lácteos.",
    "mediterranea": "Salud del corazón: aceite de oliva, pescado y poca carne roja.",
    "vegetariana": "Sin carne ni pescado: proteína de huevo, lácteos, frijol, lentejas y soya.",
    "flexitariana": "Comer menos carne sin dejarla: la mayoría de las comidas sin carne.",
    "baja_carbos": "Bajar grasa si te llenas más con proteína y verdura: menos tortilla, arroz y pan.",
    "glucosa": "Diabetes o prediabetes: menos carbohidratos, integrales y mucha fibra.",
}
ENFASIS = {"equilibrado": "Equilibrado", "proteina": "Más proteína", "carbohidratos": "Más carbohidratos"}

# Estrategias segun tu objetivo (se combinan con cualquier dieta y enfasis).
# Lo que mas pesa es el TOTAL de proteina y de kcal (eso ya lo pone tu enfoque);
# esto acomoda el dia para sacarle mas provecho:
#   musculo  (ganar musculo / recomposicion): >= 0.4 g/kg de proteina en desayuno,
#            comida y cena, y una colacion con >= 0.24 g/kg = 4 tomas al dia
#            (Schoenfeld y Aragon 2018, JISSN; Moore 2015: 0.24 g/kg por toma).
#   saciedad (perder grasa): la misma proteina por comida (la que mas llena y
#            cuida el musculo en deficit), fibra >= 14 g por 1,000 kcal (en POUNDS
#            Lost la fibra predijo la perdida de peso), >= 500 g de verdura y fruta
#            y grasa <= 30 % de las kcal (Helms 2014: 15-30 % en definicion).
ESTRATEGIAS = {
    "ninguna": {"nombre": "", "prot_comida": 0.0, "prot_colacion": 0.0, "fibra_1000": 0, "verdfruta": 0,
                "grasa_pct": None},
    "musculo": {"nombre": "Proteína repartida (músculo)", "prot_comida": 0.4, "prot_colacion": 0.24,
                "fibra_1000": 0, "verdfruta": 0, "grasa_pct": None},
    "saciedad": {"nombre": "Saciedad (pérdida de grasa)", "prot_comida": 0.4, "prot_colacion": 0.0,
                 "fibra_1000": 14, "verdfruta": 500, "grasa_pct": 0.30},
}


def estrategia_de(cfg: dict) -> tuple[str, dict]:
    """La estrategia elegida; "auto" (la de fabrica) sale de tu enfoque."""
    e = cfg.get("menu_estrategia") or "auto"
    if e == "auto":
        e = "saciedad" if cfg.get("enfoque") == "definicion" else "musculo"
    return (e, ESTRATEGIAS[e]) if e in ESTRATEGIAS else ("ninguna", ESTRATEGIAS["ninguna"])


def dieta_de(cfg: dict) -> tuple[str, dict]:
    clave = cfg.get("menu_dieta") if cfg.get("menu_dieta") in DIETAS else "mexicana"
    d = dict(DIETAS[clave])
    if clave == "dash" and int(cfg.get("menu_sodio_max") or 2300) <= 1500:
        d["sodio_max"] = 1500
        d["sal_g"] = 0.75
        d["nombre"] = "DASH bajo en sodio (1,500 mg)"
    # La mayor parte del sodio viene de la sal y de lo procesado: el limite DASH es
    # de TODO el dia, asi que a los alimentos les toca el limite menos la sal que
    # vas a usar al cocinar (2 g ~ 1/3 de cucharadita; 0.75 g en la version baja).
    d["sodio_alimentos"] = int((d["sodio_max"] - d["sal_g"] * SAL_G_MG) // 50 * 50) if d["sodio_max"] else None
    return clave, d


def _con_dieta(r: Receta, cambios: dict[str, str], fuera: set[str]) -> Receta:
    """La receta con los cambios de la dieta (si el sustituto no esta excluido)."""
    if not cambios:
        return r
    nuevos = tuple((cambios[a] if a in cambios and cambios[a] not in fuera else a, g) for a, g in r.ingredientes)
    return r if nuevos == r.ingredientes else replace(r, ingredientes=nuevos)


def excluidos(cfg: dict) -> set[str]:
    """Alimentos que no comes: ids sueltos o grupos (carnes, pescado, lacteos...)."""
    fuera: set[str] = set()
    for x in cfg.get("alimentos_excluidos") or []:
        fuera.update(alx.GRUPOS_EXCLUIBLES.get(x, [x]))
    if not cfg.get("menu_suplementos", False):
        fuera.add("proteina_polvo")          # solo si lo activas: comida primero
    fuera |= no_me_gusta()[1]
    return fuera


def cucharadita(g: float) -> str:
    """Gramos de sal en medidas de cocina (1 cucharadita rasa ~ 6 g)."""
    for limite, txt in ((0.5, "una pizca"), (1.25, "≈ ⅛ de cucharadita"), (1.75, "≈ ¼ de cucharadita"),
                        (2.5, "≈ ⅓ de cucharadita"), (4.0, "≈ ½ cucharadita"), (5.25, "≈ ¾ de cucharadita")):
        if g < limite:
            return txt
    return "≈ 1 cucharadita"


def no_me_gusta() -> tuple[set[str], set[str]]:
    """(recetas, alimentos) que marcaste "no me gusta" (copia local de MySQL)."""
    try:
        d = json.loads(NO_ME_GUSTA_LOCAL.read_text(encoding="utf-8"))
        validos_r = {r.id for r in RECETAS}
        return ({x for x in d.get("recetas", []) if x in validos_r},
                {x for x in d.get("alimentos", []) if x in alx.ALIMENTOS})
    except (OSError, ValueError, AttributeError):
        return set(), set()


def _guardar_no_me_gusta(recetas: set[str], alimentos: set[str]) -> None:
    NO_ME_GUSTA_LOCAL.write_text(json.dumps({"recetas": sorted(recetas), "alimentos": sorted(alimentos)},
                                            ensure_ascii=False), encoding="utf-8")


def _api():
    from dotenv import load_dotenv
    load_dotenv(AQUI / ".env")
    import planificar as pl
    base, token = pl.nutri_api_config()          # los "no me gusta" viven en la app de nutricion
    return pl.sesion_infinityfree(base), base, token


def descargar_no_me_gusta() -> bool:
    """Baja lo que marcaste en la app. Si el servidor no responde, se queda la copia local."""
    try:
        sesion, base, token = _api()
        r = sesion.get(f"{base}/get_no_me_gusta.php", headers={"X-API-Token": token}, timeout=20)
        r.raise_for_status()
        j = r.json()
        if not j.get("ok"):
            return False
        _guardar_no_me_gusta(set(j.get("recetas") or []), set(j.get("alimentos") or []))
        return True
    except Exception as e:  # noqa: BLE001
        print(f"No me gusta no disponible ({e.__class__.__name__}): se usa la copia local.")
        return False


def fijar_no_me_gusta(recetas: set[str], alimentos: set[str]) -> None:
    """Lo que elegiste en el dashboard: se guarda local y se manda a MySQL solo lo que cambio."""
    antes_r, antes_a = no_me_gusta()
    _guardar_no_me_gusta(set(recetas), set(alimentos))
    cambios = ([("receta", x, False) for x in set(recetas) - antes_r] + [("receta", x, True) for x in antes_r - set(recetas)]
               + [("alimento", x, False) for x in set(alimentos) - antes_a]
               + [("alimento", x, True) for x in antes_a - set(alimentos)])
    if not cambios:
        return
    try:
        sesion, base, token = _api()
        for tipo, x, baja in cambios:
            sesion.post(f"{base}/guardar_no_me_gusta.php", headers={"X-API-Token": token}, timeout=20,
                        json={"tipo": tipo, "id": x, **({"baja": True} if baja else {})}).raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"No me gusta no subido ({e.__class__.__name__}): queda en la copia local.")


def _valores(r: Receta, precios: dict[str, float]) -> tuple[float, float, float]:
    kcal = prot = costo = 0.0
    for aid, g in r.ingredientes:
        a = alx.ALIMENTOS[aid]
        kcal += a.kcal * g / 100
        prot += a.prot * g / 100
        costo += precios[aid] * g / 1000
    return kcal, prot, costo


def _fuente(r: Receta) -> str:
    """Ingrediente que mas proteina aporta (para no repetirlo comida y cena)."""
    return max(r.ingredientes, key=lambda x: alx.ALIMENTOS[x[0]].prot * x[1])[0]


def _fuente_servida(m: dict) -> str:
    """Lo mismo, de una comida ya servida (con sus gramos)."""
    return max(m["ingredientes"], key=lambda i: alx.ALIMENTOS[i["id"]].prot * i["g"])["id"]


def _redondear(aid: str, g: float) -> float:
    a = alx.ALIMENTOS[aid]
    if a.unidad == "pieza" and a.g_unidad <= 60:        # huevo, tortilla: piezas enteras
        return max(a.g_unidad, round(g / a.g_unidad) * a.g_unidad)
    return max(5.0, round(g / 5) * 5)


def _servir(r: Receta, escala: float, precios: dict[str, float]) -> dict:
    """Receta con las cantidades ya escaladas y redondeadas (los totales salen de ahi)."""
    ing, kcal, prot, carb, grasa, costo = [], 0.0, 0.0, 0.0, 0.0, 0.0
    fibra = hierro = calcio = sodio = sat = verdfruta = lacteos = 0.0
    for aid, g in r.ingredientes:
        a = alx.ALIMENTOS[aid]
        gg = _redondear(aid, g * escala)
        ing.append({"id": aid, "nombre": a.nombre, "g": gg, "texto": alx.cantidad_legible(a, gg)})
        sodio += a.sodio * gg / 100
        sat += a.sat * gg / 100
        verdfruta += gg if a.grupo == "verduras_frutas" else 0
        lacteos += gg / LACTEO_PORCION[aid] if aid in LACTEO_PORCION else 0
        kcal += a.kcal * gg / 100
        prot += a.prot * gg / 100
        carb += a.carb * gg / 100
        grasa += a.grasa * gg / 100
        fibra += a.fibra * gg / 100
        hierro += a.hierro * gg / 100
        calcio += a.calcio * gg / 100
        costo += precios[aid] * gg / 1000
    return {"tiempo": r.tiempo, "receta": r.id, "nombre": r.nombre, "como": r.como, "pasos": list(r.pasos),
            "ingredientes": ing, "kcal": round(kcal), "prot": round(prot, 1),
            "carb": round(carb), "grasa": round(grasa), "fibra": round(fibra, 1),
            "hierro": round(hierro, 1), "calcio": round(calcio), "sodio": round(sodio), "sat": round(sat, 1),
            "verdfruta": round(verdfruta), "lacteos": round(lacteos, 1), "costo": round(costo, 2)}


def generar_menu(cfg: dict, semana_inicio: date, semilla: int | None = None,
                 precios: dict[str, float] | None = None) -> dict:
    """El menu de la semana. Con presupuesto (menu_presupuesto, $ por semana para
    todo el hogar): si el menu normal no cabe, se cambia variedad por precio
    (se permite repetir mas las recetas baratas) hasta caber; si ni asi, se
    avisa cuanto es lo minimo posible con tus calorias y tu proteina."""
    hogar = factor_hogar(cfg)
    tope = cfg.get("menu_presupuesto")
    m = _generar(cfg, semana_inicio, semilla, precios)
    if tope:
        tope = float(tope)
        intentos = [m]
        if m["costo_semana"] * hogar > tope:
            for variedad, extra in ((0.5, 0), (0.2, 1), (0.0, 2)):
                intentos.append(_generar(cfg, semana_inicio, semilla, precios, variedad, extra))
                if intentos[-1]["costo_semana"] * hogar <= tope:
                    break
        caben = [x for x in intentos if x["costo_semana"] * hogar <= tope]
        m = caben[0] if caben else min(intentos, key=lambda x: x["costo_semana"])
        costo_hogar = round(m["costo_semana"] * hogar, 2)
        m["presupuesto"] = {"tope": round(tope), "costo": costo_hogar, "cabe": bool(caben),
                            "menos_variedad": m is not intentos[0]}
        if not caben:
            m["avisos"].append(f"Con tus calorías y tu proteína, lo más barato posible es ~${costo_hogar:,.0f} "
                               f"a la semana (tu tope: ${tope:,.0f}). Para bajarlo: repite más frijol, huevo "
                               "y soya, o corrige precios que estén altos.")
    return m


def factor_hogar(cfg: dict) -> float:
    """Para cuantos cocinas: adultos + ninos (un nino come ~60 % de una porcion adulta)."""
    adultos = max(1, int(cfg.get("menu_adultos") or 1))
    ninos = max(0, int(cfg.get("menu_ninos") or 0))
    return round(adultos + 0.6 * ninos, 2)


def _vector(r: Receta | None, precios: dict[str, float]) -> np.ndarray:
    """kcal, prot, carb, costo, sodio, sat, verdfruta(g), lacteos(porciones), huevo(g), roja, pescado, nuez,
    fibra, grasa."""
    v = np.zeros(15)
    if r is None:
        return v
    for aid, g in r.ingredientes:
        a = alx.ALIMENTOS[aid]
        v[:6] += np.array([a.kcal, a.prot, a.carb, precios[aid] / 10, a.sodio, a.sat]) * g / 100
        v[6] += g if a.grupo == "verduras_frutas" else 0
        v[7] += g / LACTEO_PORCION[aid] if aid in LACTEO_PORCION else 0
        v[8] += g if aid == "huevo" else 0
        v[9] = max(v[9], 1.0 if aid in CARNE_ROJA else 0.0)
        v[10] = max(v[10], 1.0 if aid in PESCADO else 0.0)
        v[11] = max(v[11], 1.0 if aid in NUECES else 0.0)
        v[12] += a.fibra * g / 100
        v[13] += a.grasa * g / 100
        v[14] = max(v[14], 1.0 if aid in CARNE else 0.0)
    return v


def _afinidad(v: np.ndarray, dieta: dict) -> float:
    """Que tanto ayuda una receta a cumplir la dieta (verdura, lacteo, pescado, poca sal)."""
    a = v[6] + 150 * v[7] * (dieta["lacteos_min"] > 0) + 400 * v[10] * (dieta["pescado_min"] > 0)
    return a - (v[4] * 0.2 if dieta["sodio_max"] else 0) - 300 * v[9] * (dieta["roja_max"] is not None)


def _generar(cfg: dict, semana_inicio: date, semilla: int | None = None, precios: dict[str, float] | None = None,
             variedad: float = 1.0, topes_extra: int = 0) -> dict:
    meta = nutricion.metas(cfg)
    K_sem, P_min = float(meta["kcal"]), float(meta["proteina_min"])
    enfasis = cfg.get("menu_enfasis") if cfg.get("menu_enfasis") in ENFASIS else "equilibrado"
    # "mas proteina": el tope del rango de tu enfoque; "mas carbohidratos": el tope
    # de su rango de carbos (g/kg x peso), para dias de mucho entreno o deporte
    P_obj = float(meta["proteina_max"]) if enfasis == "proteina" else P_min
    enf, peso = nutricion._enfoque(cfg), nutricion._peso(cfg)
    C_obj = enf.carb_g_kg[1] * peso if enfasis == "carbohidratos" else 0.0
    clave_dieta, dieta = dieta_de(cfg)
    clave_est, est = estrategia_de(cfg)
    if dieta.get("carb_pct") and dieta["carb_pct"] < 0.4 and est["grasa_pct"]:
        est = {**est, "grasa_pct": None}
    # la colacion: 0.24 g/kg con tope de 20 g (la dosis clasica en la que la sintesis
    # de musculo se aplana; mas que eso en una colacion ya no es practico)
    P_comida, P_colacion = est["prot_comida"] * peso, min(est["prot_colacion"] * peso, 20.0)
    por_dia = nutricion.kcal_por_dia(cfg)
    precios = precios or alx.precios()
    fuera = excluidos(cfg)
    for grupo in dieta.get("excluye", ()):
        fuera |= set(alx.GRUPOS_EXCLUIBLES[grupo])
    no_recetas, _ = no_me_gusta()
    disp = [_con_dieta(r, dieta["cambios"], fuera) for r in RECETAS if r.id not in no_recetas]
    disp = [r for r in disp if not any(aid in fuera for aid, _ in r.ingredientes)]
    if clave_dieta not in ("dash", "mediterranea", "vegetariana"):   # comida de casa: sin tofu ni hummus
        disp = [r for r in disp if r.id not in POCO_COMUNES]
    sobras = bool(cfg.get("menu_sobras", True))   # la comida se cocina para 2 dias
    grupos = {t: [r for r in disp if r.tiempo == t] for t in ("desayuno", "comida", "cena", "colacion")}
    for t in ("desayuno", "comida", "cena"):
        if not grupos[t]:
            raise ValueError(f"Con lo que excluiste no queda ninguna receta de {t}.")
    rng = random.Random(semilla if semilla is not None else semana_inicio.toordinal())
    vec = {r.id: _vector(r, precios) for r in disp}
    esc = np.array(ESCALAS)
    vf_min, vf_ideal = dieta["verdfruta"]

    usos: dict[str, int] = {}
    uso_ing: dict[str, int] = {}         # comidas de la semana con soya, sardina... (MAX_SEMANA)
    familias: dict[str, int] = {}        # comidas cocinadas con pollo, res, cerdo, pescado o sin carne
    variar_carne = (len({familia(r) for r in grupos["comida"]} - {"sin_carne"}) >= 3
                    and not dieta.get("carne_max"))       # la flexitariana ya limita la carne
    comprados: set[str] = set()          # lo que ya esta en la lista del super de esta semana
    semana = {"roja": 0, "pescado": 0, "carne": 0}
    dias, avisos = [], []
    hechos: list[dict] = []              # por dia: recetas elegidas y la comida servida (para las sobras)
    for i in range(7):
        K = float(por_dia[i + 1]["kcal"])
        # sobras: la comida de hoy es la que se cocino ayer, con la misma porcion
        de_ayer = hechos[SOBRAS_DE[i]] if sobras and i in SOBRAS_DE else None

        def escoger(lista: list[Receta], tiempo: str, cuantas: int = POR_TIEMPO_DIA) -> list[Receta]:
            """~18 de ~50: las 5 mas baratas por kcal, las mas llenadoras, las 4 que mejor cumplen la dieta
            (y las 4 con mas proteina o carbos si pediste enfasis) + el resto al azar."""
            libres = [r for r in lista if usos.get(r.id, 0) < TOPE_USOS[tiempo] + topes_extra] or list(lista)
            if len(libres) <= cuantas:
                return libres
            fijas = sorted(libres, key=lambda r: vec[r.id][3] / max(vec[r.id][0], 1))[:5]
            # las 3 con mas kcal y las 2 con mas proteina: que siempre alcance para 3,500+ kcal
            fijas += [r for r in sorted(libres, key=lambda r: -vec[r.id][0]) if r not in fijas][:3]
            fijas += [r for r in sorted(libres, key=lambda r: -vec[r.id][1]) if r not in fijas][:2]
            if clave_dieta != "mexicana":
                fijas += [r for r in sorted(libres, key=lambda r: -_afinidad(vec[r.id], dieta)) if r not in fijas][:4]
            if enfasis != "equilibrado":
                col = 1 if enfasis == "proteina" else 2
                fijas += [r for r in sorted(libres, key=lambda r: -vec[r.id][col] / max(vec[r.id][0], 1))
                          if r not in fijas][:4]
            if P_comida:        # que entren las que llegan a la proteina por comida
                fijas += [r for r in sorted(libres, key=lambda r: -vec[r.id][1] / max(vec[r.id][0], 1))
                          if r not in fijas][:3]
            if est["fibra_1000"]:
                fijas += [r for r in sorted(libres, key=lambda r: -vec[r.id][12] / max(vec[r.id][0], 1))
                          if r not in fijas][:3]
            resto = [r for r in libres if r not in fijas]
            return fijas + rng.sample(resto, max(0, cuantas - len(fijas)))

        if de_ayer:
            C = [de_ayer["recetas"]["comida"]]
        else:
            comidas = grupos["comida"]
            if sobras and i in DIAS_COCINA:      # hoy se cocina para 2 dias: solo lo que aguanta
                comidas = [r for r in comidas if "olla" in r.tags] or comidas
            if (variar_carne and clave_dieta == "mexicana" and i == max(DIAS_COCINA)
                    and not (familias.get("res") or familias.get("cerdo"))):
                # en la semana va al menos una comida de res o de cerdo (la ultima que se cocina)
                comidas = [r for r in comidas if familia(r) in ("res", "cerdo")] or comidas
            C = escoger(comidas, "comida")
        D, N = escoger(grupos["desayuno"], "desayuno"), escoger(grupos["cena"], "cena")
        SN = [None] + escoger(grupos["colacion"], "colacion", POR_COLACION_DIA)
        VD, VC, VN = (np.array([vec[r.id] for r in L]) for L in (D, C, N))
        VS = np.array([_vector(r, precios) if r is None else vec[r.id] for r in SN])
        # la comida de sobras va con la porcion con que se cocino; lo demas, con la del dia
        esc_c = np.full_like(esc, de_ayer["s_comida"]) if de_ayer else esc

        def suma(col: int) -> np.ndarray:
            """(D, C, N, S, SN) del indicador `col`: las 3 comidas escaladas + la colacion."""
            base = (VD[:, col][:, None, None] + VN[:, col][None, None, :])[..., None, None] * esc[None, None, None, :, None]
            return (base + VC[:, col][None, :, None, None, None] * esc_c[None, None, None, :, None]
                    + VS[:, col][None, None, None, None, :])

        kcal, prot, carb, costo = suma(0), suma(1), suma(2), suma(3)
        fibra, grasa = suma(12), suma(13)
        # proteina de cada comida fuerte (con su porcion) y de la colacion
        prot_ok = np.ones(1, bool)
        if P_comida:
            prot_ok = ((VD[:, 1][:, None, None, None, None] * esc[None, None, None, :, None] >= P_comida * 0.97)
                       & (VC[:, 1][None, :, None, None, None] * esc_c[None, None, None, :, None] >= P_comida * 0.97)
                       & (VN[:, 1][None, None, :, None, None] * esc[None, None, None, :, None] >= P_comida * 0.97))
        if P_colacion:
            prot_ok = prot_ok & (VS[:, 1][None, None, None, None, :] >= P_colacion * 0.97)
        sodio, sat, verdfruta, lacteos, huevos = suma(4), suma(5), suma(6), suma(7), suma(8)

        def pen(lista):
            v = np.array([usos.get(r.id, 0) * PENALIZA_REPETIR * variedad if r else 0.0 for r in lista])
            tope = np.array([(usos.get(r.id, 0) >= TOPE_USOS[r.tiempo] + topes_extra
                              or any(uso_ing.get(a, 0) >= MAX_SEMANA[a] for a, _ in r.ingredientes if a in MAX_SEMANA)
                              or (r.tiempo == "comida" and variar_carne
                                  and familias.get(familia(r), 0) >= MAX_FAMILIA[familia(r)]))
                             if r else False for r in lista])
            return v, tope
        vd, td = pen(D)
        vc, tc = pen(C) if not de_ayer else (np.zeros(1), np.zeros(1, bool))   # las sobras se repiten a proposito
        vn, tn = pen(N)
        vs, ts = pen(SN)
        castigo = (vd[:, None, None, None, None] + vc[None, :, None, None, None]
                   + vn[None, None, :, None, None] + vs[None, None, None, None, :])
        tope_usos = (td[:, None, None, None, None] | tc[None, :, None, None, None]
                     | tn[None, None, :, None, None] | ts[None, None, None, None, :])
        # reglas semanales de la dieta: carne roja con tope; pescado que falta, con premio
        roja = VC[:, 9][None, :, None, None, None] + VN[:, 9][None, None, :, None, None]
        roja_tope = (semana["roja"] + roja > dieta["roja_max"]) if dieta["roja_max"] is not None else np.zeros(1, bool)
        if dieta.get("carne_max") is not None:
            carne = VC[:, 14][None, :, None, None, None] + VN[:, 14][None, None, :, None, None]
            roja_tope = roja_tope | (semana["carne"] + carne > dieta["carne_max"])
        falta_pescado = max(0, dieta["pescado_min"] - semana["pescado"])
        pescado_hoy = bool(falta_pescado and (i in (1, 4) or (7 - i) <= falta_pescado))   # repartido en la semana
        pez = np.minimum(1, VC[:, 10][None, :, None, None, None] + VN[:, 10][None, None, :, None, None])
        premio_pescado = -25.0 * pez if falta_pescado else np.zeros(1)
        # lo que la dieta pide a diario y se premia/castiga en $ virtuales
        suave = np.zeros(1)
        if vf_ideal:
            suave = suave + np.maximum(0, vf_ideal - verdfruta) * 0.06            # $6 por 100 g de verdura/fruta faltante
        if dieta["lacteos_min"]:
            suave = suave + np.maximum(0, dieta["lacteos_min"] - lacteos) * 10.0
        if dieta["pescado_min"]:
            suave = suave - VS[:, 11][None, None, None, None, :] * 1.0          # nueces de colacion
        # un poco de azar por receta: dos menus igual de baratos no salen siempre igual
        rd, rc, rn = (np.array([rng.uniform(0, RUIDO * variedad) for _ in L]) for L in (D, C, N))
        if de_ayer:
            rc = np.zeros(1)
        ruido = ((rd[:, None, None, None, None] + rc[None, :, None, None, None] + rn[None, None, :, None, None])
                 * esc[None, None, None, :, None])          # crece con la porcion, como el costo
        desvio = np.abs(kcal - K)
        # Como Mealime: preferir recetas que reusan lo que ya compraste en la semana
        # (menos cosas distintas en la lista y menos paquetes a medias)
        nd, nc, nn, ns = (np.array([len({a for a, _ in r.ingredientes} - comprados) if r else 0 for r in L], float)
                          for L in (D, C, N, SN))
        reuso = NUEVO_INGREDIENTE * (nd[:, None, None, None, None] + nc[None, :, None, None, None]
                                     + nn[None, None, :, None, None] + ns[None, None, None, None, :])
        objetivo = costo + castigo + ruido + desvio * 0.01 + suave + premio_pescado + reuso
        mucho_huevo = huevos > MAX_HUEVO_DIA + 1
        fuente_c = np.array([_fuente(r) for r in C])
        fuente_n = np.array([_fuente(r) for r in N])
        fuente_s = np.array([_fuente(r) if r else "" for r in SN])
        # comida y cena no repiten proteina; la colacion tampoco la de la cena (burrito y burritos el mismo dia)
        misma_fuente = ((fuente_c[:, None] == fuente_n[None, :])[None, :, :, None, None]
                        | (fuente_n[:, None] == fuente_s[None, :])[None, None, :, None, :])

        def est_ok(kc, fib, gra, vf):
            """La estrategia completa (solo en las etapas con la dieta completa)."""
            ok = True
            if est["fibra_1000"]:
                ok = ok & (fib * 1000 >= est["fibra_1000"] * kc)
            if est["verdfruta"]:
                ok = ok & (vf >= est["verdfruta"])
            if est["grasa_pct"]:
                ok = ok & (gra * 9 <= est["grasa_pct"] * kc)
            return ok

        def dieta_ok(nivel, sod, sa, kc, vf, lac, pescado, cb=0.0, fib=0.0):
            """nivel 2: la dieta completa (verdura ideal, lacteos, pescado del dia);
            1: lo basico (sodio, grasa saturada, verdura minima, carbohidratos, fibra); 0: nada."""
            ok = True
            if nivel and dieta.get("carb_pct"):
                ok = ok & (cb * 4 <= dieta["carb_pct"] * kc)
            if nivel and dieta.get("fibra_1000"):
                ok = ok & (fib * 1000 >= dieta["fibra_1000"] * kc)
            if nivel and dieta["sodio_alimentos"]:
                ok = ok & (sod <= dieta["sodio_alimentos"])
            if nivel and dieta["sat_pct"]:
                ok = ok & (sa * 9 <= dieta["sat_pct"] * kc)
            if nivel and vf_min:
                ok = ok & (vf >= (vf_ideal if nivel == 2 else vf_min))
            if nivel == 2 and dieta["lacteos_min"]:
                ok = ok & (lac >= dieta["lacteos_min"])
            if nivel == 2 and pescado_hoy:
                ok = ok & (pescado > 0)
            return ok

        elegido, aviso = None, None
        # Etapas (de lo ideal a lo posible). Cada una dice si exige: el enfasis
        # (mas proteina/carbos), la dieta (sodio, grasa saturada, verduras), la
        # proteina minima y la variedad. Se avisa de lo que se tuvo que soltar.
        etapas = (
            (TOLERANCIA_KCAL, True, 2, True, True), (0.08, True, 2, True, True), (0.08, True, 1, True, True),
            (0.08, False, 2, True, True), (0.08, False, 1, True, True), (0.08, False, 0, True, True),
            (0.08, False, 0, False, True), (0.08, False, 1, True, False), (0.10, False, 0, False, False),
        )
        for tol, con_enfasis, con_dieta, con_prot, con_variedad in etapas:
            P = P_obj if con_enfasis else P_min
            bloqueo = mucho_huevo | ((tope_usos | misma_fuente | roja_tope) if con_variedad else False)
            pre = (desvio <= K * (tol + 0.05)) & ~bloqueo
            if con_prot:
                pre &= prot >= P * 0.95
            if con_enfasis and C_obj:
                pre &= carb >= C_obj * 0.95
            if con_dieta:
                pre &= dieta_ok(con_dieta, sodio * 0.97, sat * 0.97, kcal, verdfruta * 1.03, lacteos * 1.05, pez,
                                carb * 0.97, fibra * 1.03)
            if con_dieta == 2:
                pre &= prot_ok & est_ok(kcal, fibra * 1.03, grasa * 0.97, verdfruta * 1.03)
            obj = objetivo if con_prot else (-prot + costo * 0.05 + castigo * 0.1 + desvio * 0.005)
            obj = np.where(pre, obj, np.inf)
            n_ok = int(np.isfinite(obj).sum())
            if not n_ok:
                continue
            k = min(n_ok, 600)
            planos = np.argpartition(obj, k - 1, axis=None)[:k]
            planos = planos[np.argsort(obj.ravel()[planos])]
            for plano in planos:
                d_i, c_i, n_i, s_i, sn_i = (int(x) for x in np.unravel_index(plano, obj.shape))
                s = ESCALAS[s_i]
                s_c = de_ayer["s_comida"] if de_ayer else s
                cand = [_servir(D[d_i], s, precios), _servir(C[c_i], s_c, precios), _servir(N[n_i], s, precios)]
                if SN[sn_i]:
                    cand.insert(2, _servir(SN[sn_i], 1.0, precios))
                tot = {k_: sum(c[k_] for c in cand)
                       for k_ in ("kcal", "prot", "carb", "sodio", "sat", "verdfruta", "lacteos", "fibra", "grasa")}
                fuertes = [c["prot"] for c in cand if c["tiempo"] != "colacion"]
                col = [c["prot"] for c in cand if c["tiempo"] == "colacion"]
                est_real = (min(fuertes) >= P_comida - 0.5 and (not P_colacion or (col and col[0] >= P_colacion - 0.5))
                            and bool(est_ok(tot["kcal"], tot["fibra"] * 1.02, tot["grasa"], tot["verdfruta"] * 1.03)))
                huevo_real = sum(x["g"] for c in cand for x in c["ingredientes"] if x["id"] == "huevo")
                if (abs(tot["kcal"] - K) <= K * tol and huevo_real <= MAX_HUEVO_DIA
                        and (not con_prot or tot["prot"] >= P)
                        and (not (con_enfasis and C_obj) or tot["carb"] >= C_obj)
                        and (not con_dieta or bool(dieta_ok(con_dieta, tot["sodio"], tot["sat"], tot["kcal"],
                                                            tot["verdfruta"] * 1.03, tot["lacteos"] * 1.05,
                                                            vec[C[c_i].id][10] + vec[N[n_i].id][10],
                                                            tot["carb"], tot["fibra"] * 1.02)))
                        and (con_dieta != 2 or est_real)):
                    elegido = (d_i, c_i, n_i, sn_i, cand, s)
                    break
            if elegido:
                sueltos = []
                if enfasis != "equilibrado" and not con_enfasis:
                    sueltos.append("el énfasis en " + ("proteína" if enfasis == "proteina" else "carbohidratos"))
                if clave_dieta != "mexicana" and not con_dieta:
                    sueltos.append("alguna regla de la dieta " + dieta["nombre"].split(" (")[0])
                if clave_est != "ninguna" and con_dieta != 2:
                    sueltos.append("la estrategia " + est["nombre"].split(" (")[0].lower())
                if not con_prot:
                    sueltos.append("tu proteína mínima (suma una porción del botón Proteína)")
                if not con_variedad:
                    sueltos.append("la variedad (repite más de lo normal)")
                if sueltos:
                    aviso = "este día no se pudo cumplir " + ", ".join(sueltos) + "."
                break
        if not elegido:
            raise ValueError("No hay combinación posible: revisa lo que excluiste.")
        d_i, c_i, n_i, sn_i, elegidas, s_dia = elegido
        recetas_dia = {"desayuno": D[d_i], "comida": C[c_i], "cena": N[n_i], "colacion": SN[sn_i]}
        huevo_dia = sum(x["g"] for c in elegidas for x in c["ingredientes"] if x["id"] == "huevo")
        sodio_dia = sum(c["sodio"] for c in elegidas)
        fecha = semana_inicio + timedelta(days=i)
        for c in elegidas:
            if c["tiempo"] == "comida" and de_ayer:
                # las sobras: misma comida y mismas opciones que el dia en que se cocino (la app las
                # cambia juntas), pero solo las que tambien caben hoy (sodio, huevo, proteina de la cena)
                libre = (dieta["sodio_alimentos"] - (sodio_dia - c["sodio"])) if dieta["sodio_alimentos"] else None
                h0 = sum(x["g"] for x in c["ingredientes"] if x["id"] == "huevo")
                cena_fuente = _fuente(recetas_dia["cena"])
                comunes = [a for a in de_ayer["comida"].get("alternativas", [])
                           if (libre is None or a["sodio"] <= libre)
                           and sum(x["g"] for x in a["ingredientes"] if x["id"] == "huevo") - h0 <= MAX_HUEVO_DIA - huevo_dia
                           and _fuente_servida(a) != cena_fuente]
                de_ayer["comida"]["alternativas"] = comunes
                c["alternativas"] = copy.deepcopy(comunes)
                c["sobras"] = {"de": de_ayer["fecha"], "dia": NOMBRES_DIA[SOBRAS_DE[i]]}
                continue
            otra = recetas_dia["cena" if c["tiempo"] == "comida" else "comida"] if c["tiempo"] in ("comida", "cena") else None
            sodio_libre = (dieta["sodio_alimentos"] - (sodio_dia - c["sodio"])) if dieta["sodio_alimentos"] else None
            minimo = (P_colacion if c["tiempo"] == "colacion" else P_comida) * 0.97   # la misma tolerancia del menu
            opciones = grupos[c["tiempo"]]
            if c["tiempo"] == "comida" and sobras and i in DIAS_COCINA:
                opciones = [r for r in opciones if "olla" in r.tags] or opciones
                c["rinde"] = 2                   # se cocina para hoy y manana
            c["alternativas"] = _alternativas(c, opciones, 1.0 if c["tiempo"] == "colacion" else s_dia,
                                              precios, _fuente(otra) if otra else None,
                                              MAX_HUEVO_DIA - huevo_dia, n=N_ALTERNATIVAS.get(c["tiempo"], 3),
                                              sodio_libre=sodio_libre,
                                              sin_roja=dieta["roja_max"] is not None and semana["roja"] >= dieta["roja_max"],
                                              prot_min=minimo + 0.5 if c["prot"] >= minimo else 0.0)
        for t, r in recetas_dia.items():
            if r:
                if not (t == "comida" and de_ayer):
                    usos[r.id] = usos.get(r.id, 0) + 1
                    if t == "comida":
                        familias[familia(r)] = familias.get(familia(r), 0) + 1
                comprados.update(a for a, _ in r.ingredientes)
                for a in {a for a, _ in r.ingredientes} & set(MAX_SEMANA):
                    uso_ing[a] = uso_ing.get(a, 0) + 1
        hechos.append({"recetas": recetas_dia, "fecha": fecha.isoformat(),
                       "s_comida": de_ayer["s_comida"] if de_ayer else s_dia,
                       "comida": next(c for c in elegidas if c["tiempo"] == "comida")})
        semana["roja"] += int(vec[C[c_i].id][9] + vec[N[n_i].id][9])
        semana["carne"] += int(vec[C[c_i].id][14] + vec[N[n_i].id][14])
        semana["pescado"] += int(vec[C[c_i].id][10] + vec[N[n_i].id][10])
        tot = {k_: sum(c[k_] for c in elegidas)
               for k_ in ("kcal", "prot", "carb", "grasa", "fibra", "hierro", "calcio", "sodio", "sat", "verdfruta",
                          "lacteos", "costo")}
        if aviso:
            avisos.append(f"{NOMBRES_DIA[i]}: {aviso[0].upper()}{aviso[1:]}")
        dias.append({"dia": i + 1, "nombre": NOMBRES_DIA[i], "fecha": fecha.isoformat(), "comidas": elegidas,
                     "tipo": por_dia[i + 1]["tipo"], "kcal_meta": int(K),
                     "kcal": round(tot["kcal"]), "prot": round(tot["prot"]), "carb": round(tot["carb"]),
                     "grasa": round(tot["grasa"]), "fibra": round(tot["fibra"]), "hierro": round(tot["hierro"], 1),
                     "calcio": round(tot["calcio"]), "sodio": round(tot["sodio"]), "sat": round(tot["sat"], 1),
                     "verdfruta": round(tot["verdfruta"]), "lacteos": round(tot["lacteos"], 1),
                     "costo": round(tot["costo"], 2),
                     "prot_comidas": [round(c["prot"]) for c in elegidas if c["tiempo"] != "colacion"],
                     "prot_colacion": next((round(c["prot"]) for c in elegidas if c["tiempo"] == "colacion"), None),
                     "sal_g": (round(max(0.0, (dieta["sodio_max"] - tot["sodio"]) / SAL_G_MG), 1)
                               if dieta["sodio_max"] else None)})

    hogar = factor_hogar(cfg)
    lista = lista_super(dias, precios, hogar, tiendas_de(cfg))
    ref = alx.precio_referencia()
    costo_sem = round(sum(d["costo"] for d in dias), 2)
    usados = {ing["id"] for d in dias for c in d["comidas"]
              for x in [c, *c.get("alternativas", [])] for ing in x["ingredientes"]}
    return {
        "semana_inicio": semana_inicio.isoformat(),
        "meta": {"kcal": round(K_sem), "proteina_min": round(P_min), "proteina_max": meta["proteina_max"],
                 "proteina_obj": round(P_obj), "carb_obj": round(C_obj) if C_obj else None,
                 "enfoque": meta["enfoque"], "peso": meta["peso"],
                 "kcal_por_tipo": nutricion.resumen_por_tipo(cfg)},
        "dieta": {"id": clave_dieta, "nombre": dieta["nombre"], "enfasis": enfasis, "enfasis_nombre": ENFASIS[enfasis],
                  "estrategia": clave_est, "estrategia_nombre": est["nombre"],
                  "cumple": cumplimiento_dieta(dias, dieta, semana, fuera)
                  + cumplimiento_estrategia(dias, est, P_comida, P_colacion)},
        "dias": dias,
        "lista": lista,
        "costo_caja": round(sum(f["costo"] for f in lista), 2),     # lo que pagas en la tienda (paquetes enteros)
        "despensa": round(sum(f.get("queda", 0) for f in lista), 2),  # de eso, lo que rinde para otras semanas
        "tiendas": [{"id": t, "nombre": n} for t, n in pmx.TIENDAS.items()],
        "tiendas_usadas": sorted(tiendas_de(cfg) or pmx.TIENDAS, key=pmx.ORDEN_TIENDAS.index),
        "sobras": sobras,
        "costo_semana": costo_sem,
        "costo_dia": round(costo_sem / 7, 2),
        "kcal_prom": round(sum(d["kcal"] for d in dias) / 7),
        "prot_prom": round(sum(d["prot"] for d in dias) / 7),
        "carb_prom": round(sum(d["carb"] for d in dias) / 7),
        "excluidos": sorted(fuera),
        "no_me_gusta": {"recetas": sorted(no_recetas), "alimentos": sorted(no_me_gusta()[1])},
        "avisos": avisos,
        "cocina": cocina_por_adelantado(dias, hogar),
        "hogar": {"adultos": max(1, int(cfg.get("menu_adultos") or 1)), "ninos": max(0, int(cfg.get("menu_ninos") or 0)),
                  "factor": hogar},
        "nutrientes": nutrientes_semana(dias, K_sem, fuera),
        # lo que la app necesita para rehacer la lista y la cocina si cambias comidas
        "alimentos": {aid: _ficha(alx.ALIMENTOS[aid], precios[aid], ref[aid]) for aid in sorted(usados)},
        "nota": "Cantidades en crudo (frijol, lentejas, arroz y avena en seco). Precios de productos reales de "
                "Chedraui, Walmart y Sam's (2-nov-2026), del folleto de 3B y del mercado (estimado con la Central "
                "de Abasto); cambian por ciudad. Corrígelos con lo que pagas.",
    }


def cumplimiento_estrategia(dias: list[dict], est: dict, p_comida: float, p_colacion: float) -> list[dict]:
    """Las reglas de la estrategia contra lo que trae el menu."""
    reglas = []
    if p_comida:
        v = min(min(d["prot_comidas"]) for d in dias)
        reglas.append({"regla": f"Proteína en desayuno, comida y cena ≥ {p_comida:.0f} g (0.4 g/kg)",
                       "valor": f"mín. {v} g", "ok": v >= p_comida - 1})
    if p_colacion:
        n = sum(1 for d in dias if (d["prot_colacion"] or 0) >= p_colacion - 1)
        reglas.append({"regla": f"4.ª toma de proteína: colación ≥ {p_colacion:.0f} g", "valor": f"{n} de 7 días",
                       "ok": n == 7, "nota": "Si cenas temprano, cómela antes de dormir."})
    if est["fibra_1000"]:
        v = sum(d["fibra"] for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 1000
        reglas.append({"regla": f"Fibra ≥ {est['fibra_1000']} g por cada 1,000 kcal", "valor": f"{v:.0f} g",
                       "ok": v >= est["fibra_1000"] - 0.3})
    if est["verdfruta"]:
        v = sum(d["verdfruta"] for d in dias) / 7
        reglas.append({"regla": f"Verduras y frutas ≥ {est['verdfruta']} g al día (llenan con pocas kcal)",
                       "valor": f"{v:.0f} g", "ok": v >= est["verdfruta"] * 0.97})
    if est["grasa_pct"]:
        v = sum(d["grasa"] * 9 for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 100
        reglas.append({"regla": f"Grasa ≤ {est['grasa_pct'] * 100:.0f} % de las kcal", "valor": f"{v:.0f} %",
                       "ok": v <= est["grasa_pct"] * 100 + 0.5})
    return reglas


def cumplimiento_dieta(dias: list[dict], dieta: dict, semana: dict, fuera: set[str] = frozenset()) -> list[dict]:
    """Cada regla de la dieta contra lo que de verdad trae el menu (promedios o conteos)."""
    prom = lambda k: sum(d[k] for d in dias) / 7  # noqa: E731
    reglas = []
    if dieta["sodio_max"]:
        v = max(d["sodio"] for d in dias)
        sal = min(d["sal_g"] for d in dias)
        reglas.append({"regla": f"Sodio de los alimentos ≤ {dieta['sodio_alimentos']:,} mg al día",
                       "valor": f"máx. {v:,.0f} mg", "ok": v <= dieta["sodio_alimentos"] + 5})
        reglas.append({"regla": f"Sal para cocinar dentro de {dieta['sodio_max']:,} mg de sodio",
                       "valor": f"≥ {sal:.1f} g al día ({cucharadita(sal)})", "ok": sal >= dieta["sal_g"] - 0.05,
                       "nota": "Mídela: es toda la sal del día, en la olla y en la mesa."})
    if dieta["sat_pct"]:
        v = sum(d["sat"] * 9 for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 100
        reglas.append({"regla": f"Grasa saturada ≤ {dieta['sat_pct'] * 100:.0f} % de las kcal",
                       "valor": f"{v:.1f} %", "ok": v <= dieta["sat_pct"] * 100 + 0.05})
    if dieta["verdfruta"][1]:
        v = prom("verdfruta")
        reglas.append({"regla": f"Verduras y frutas ≥ {dieta['verdfruta'][1]} g al día",
                       "valor": f"{v:.0f} g", "ok": v >= dieta["verdfruta"][1] * 0.95})
    if dieta["lacteos_min"] and set(LACTEO_PORCION) <= set(fuera):
        reglas.append({"regla": "Lácteos bajos en grasa: 2-3 porciones al día", "valor": "los excluiste",
                       "ok": None, "nota": "Cubre el calcio con tofu, sardina, chía, almendra o tortilla de maíz."})
    elif dieta["lacteos_min"]:
        v = prom("lacteos")
        reglas.append({"regla": f"Lácteos bajos en grasa: {dieta['lacteos_min']}-3 porciones al día",
                       "valor": f"{v:.1f}", "ok": v >= dieta["lacteos_min"] * 0.9})
    if dieta["roja_max"] is not None:
        reglas.append({"regla": f"Carne roja ≤ {dieta['roja_max']} {'vez' if dieta['roja_max'] == 1 else 'veces'} por semana",
                       "valor": str(semana["roja"]), "ok": semana["roja"] <= dieta["roja_max"]})
    if dieta.get("excluye"):
        hay = sum(1 for d in dias for c in d["comidas"] for i in c["ingredientes"]
                  if i["id"] in CARNE or i["id"] in PESCADO)
        reglas.append({"regla": "Sin carne ni pescado", "valor": "ninguna" if not hay else f"{hay} veces", "ok": not hay})
    if dieta.get("carne_max") is not None:
        reglas.append({"regla": f"Comidas y cenas con carne ≤ {dieta['carne_max']} por semana",
                       "valor": str(semana.get("carne", 0)), "ok": semana.get("carne", 0) <= dieta["carne_max"]})
    if dieta.get("carb_pct"):
        v = sum(d["carb"] * 4 for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 100
        reglas.append({"regla": f"Carbohidratos ≤ {dieta['carb_pct'] * 100:.0f} % de las kcal", "valor": f"{v:.0f} %",
                       "ok": v <= dieta["carb_pct"] * 100 + 0.5})
    if dieta.get("fibra_1000"):
        v = sum(d["fibra"] for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 1000
        reglas.append({"regla": f"Fibra ≥ {dieta['fibra_1000']} g por cada 1,000 kcal", "valor": f"{v:.0f} g",
                       "ok": v >= dieta["fibra_1000"] - 0.3})
    if dieta["pescado_min"]:
        reglas.append({"regla": f"Pescado o mariscos ≥ {dieta['pescado_min']} veces por semana",
                       "valor": str(semana["pescado"]), "ok": semana["pescado"] >= dieta["pescado_min"]})
    return reglas


def _alternativas(elegida: dict, opciones: list[Receta], escala: float, precios: dict[str, float],
                  fuente_prohibida: str | None, huevo_libre: float, n: int = 3,
                  sodio_libre: float | None = None, sin_roja: bool = False, prot_min: float = 0.0) -> list[dict]:
    """Hasta `n` recetas del mismo tiempo, parecidas a la elegida: kcal a +/-12 %
    (colaciones +/-50 %: son muchas y chicas), al menos 85 % de su proteina, sin
    repetir la proteina de la otra comida fuerte ni pasarse de huevo. Las mas
    baratas primero."""
    k0, p0 = elegida["kcal"], elegida["prot"]
    huevo0 = sum(i["g"] for i in elegida["ingredientes"] if i["id"] == "huevo")
    tol = 0.50 if elegida["tiempo"] == "colacion" else 0.12
    min_prot = 0.5 if elegida["tiempo"] == "colacion" else 0.85      # una colacion es fruta o algo ligero
    escalas = (1.0,) if elegida["tiempo"] == "colacion" else ESCALAS
    salida = []
    for r in opciones:
        if r.id == elegida["receta"] or (fuente_prohibida and _fuente(r) == fuente_prohibida):
            continue
        if sin_roja and any(aid in CARNE_ROJA for aid, _ in r.ingredientes):
            continue
        mejor = None
        for e in escalas:
            m = _servir(r, e, precios)
            huevo = sum(i["g"] for i in m["ingredientes"] if i["id"] == "huevo")
            if (abs(m["kcal"] - k0) <= k0 * tol and m["prot"] >= max(p0 * min_prot, prot_min - 0.5)
                    and huevo - huevo0 <= huevo_libre
                    and (sodio_libre is None or m["sodio"] <= sodio_libre)):
                if mejor is None or abs(m["kcal"] - k0) < abs(mejor["kcal"] - k0):
                    mejor = m
        if mejor:
            salida.append((familia(r), mejor))
    salida.sort(key=lambda x: x[1]["costo"])
    if elegida["tiempo"] == "comida":
        # para "Cambiar" en una comida: primero una de cada carne distinta (pollo -> res, cerdo, pescado),
        # luego las demas, siempre de la mas barata a la mas cara
        fam0 = FAMILIA.get(max(elegida["ingredientes"], key=lambda i: alx.ALIMENTOS[i["id"]].prot * i["g"])["id"],
                           "sin_carne")
        vistas, primero, resto = {fam0}, [], []
        for fam, m in salida:
            (primero if fam not in vistas else resto).append(m)
            vistas.add(fam)
        return (primero + resto)[:n]
    return [m for _, m in salida][:n]


def _ficha(a: "alx.Alimento", precio: float, ref: float | None = None) -> dict:
    """Lo que la app necesita para rehacer la lista: precio, productos reales por tienda y cuanto dura."""
    return {"nombre": a.nombre, "precio_kg": round(precio, 2), "compra": a.compra, "g_compra": a.g_compra,
            "piezas": list(a.piezas), "seco_por_taza": a.seco_por_taza, "grupo": a.grupo,
            "unidad": a.unidad, "g_unidad": a.g_unidad,
            "propio": ref is not None and abs(precio - ref) > 0.005,      # corregiste el precio en el dashboard
            "dura": pmx.dura(a.id), "productos": pmx.ficha(a.id)}


# Lo que se cocina en olla grande dos veces por semana (las leguminosas tardan
# horas); lo cocido dura 3-4 dias en el refri (USDA, "Leftovers and Food Safety").
# Las comidas de cada dia se cocinan para 2 dias (ver SOBRAS_DE).
PARA_COCINAR = {"frijol": "en olla (2 h, o 40 min en olla exprés)", "lentejas": "en olla (30-40 min)",
                "garbanzo": "remojo la noche anterior y olla (1½ h)", "habas": "en olla (1 h)"}
TANDAS = (("Domingo", "para lunes a miércoles", (1, 2, 3)), ("Miércoles en la noche", "para jueves a domingo", (4, 5, 6, 7)))


# Referencias diarias: fibra >= 25 g (OMS) y ~14 g por cada 1,000 kcal (Dietary
# Guidelines for Americans 2020-2025); hierro 8 mg hombres / 18 mg mujeres de
# 19-50 anos y calcio 1,000 mg (NIH, Office of Dietary Supplements).
FIBRA_MIN = 25
HIERRO_H, HIERRO_M = 8, 18
CALCIO_REF = 1000


def nutrientes_semana(dias: list[dict], kcal: float, fuera: set[str] | None = None) -> dict:
    prom = {k: round(sum(d.get(k, 0) for d in dias) / 7, 1)
            for k in ("fibra", "hierro", "calcio", "sodio", "verdfruta")}
    prom["sat_pct"] = round(sum(d.get("sat", 0) * 9 for d in dias) / max(1, sum(d["kcal"] for d in dias)) * 100, 1)
    consejos = []
    if prom["fibra"] < FIBRA_MIN:
        consejos.append("Fibra baja: más frijol, lentejas, verduras y fruta con cáscara.")
    if prom["calcio"] < CALCIO_REF * 0.9:
        # solo sugiere lo que SI comes
        fuera = fuera or set()
        fuentes = [n for ids, n in ((("leche", "yogur", "queso_fresco", "panela"), "leche, yogur o queso"),
                                    (("sardina",), "sardina (con su hueso)"),
                                    (("nopales",), "nopales"), (("soya",), "soya texturizada"))
                   if not all(i in fuera for i in ids)]
        consejos.append("Calcio bajo: suma " + ", ".join(fuentes) + "; la tortilla nixtamalizada también aporta.")
    consejos.append("El hierro del frijol y las lentejas se absorbe mejor con vitamina C: limón, jitomate o naranja.")
    return {**prom, "fibra_min": FIBRA_MIN, "fibra_rec": round(14 * kcal / 1000), "hierro_h": HIERRO_H,
            "hierro_m": HIERRO_M, "calcio_ref": CALCIO_REF, "consejos": consejos}


def cocina_por_adelantado(dias: list[dict], factor: float = 1.0) -> list[dict]:
    """Que cocinar y cuando: la comida de cada dia de cocina (para 2 dias) y las ollas de frijol."""
    salida = []
    for d in dias:
        c = next((x for x in d["comidas"] if x["tiempo"] == "comida"), None)
        if not c or c.get("rinde", 1) < 2:
            continue
        otro = next((dd for dd in dias for x in dd["comidas"]
                     if x["tiempo"] == "comida" and (x.get("sobras") or {}).get("de") == d["fecha"]), None)
        veces = 2 if otro else 1
        tareas = [{"id": c["receta"], "g": round(sum(i["g"] for i in c["ingredientes"]) * veces * factor),
                   "texto": f"{c['nombre']} × {veces} porciones: "
                   + ", ".join(alx.cantidad_legible(alx.ALIMENTOS[i["id"]], i["g"] * veces * factor)
                               for i in c["ingredientes"])}]
        salida.append({"cuando": d["nombre"], "para": f"comida de hoy y de mañana ({otro['nombre'].lower()})"
                       if otro else "comida de hoy", "tareas": tareas})
    for cuando, para, nums in TANDAS:
        total: dict[str, float] = {}
        for d in dias:
            if d["dia"] in nums:
                for c in d["comidas"]:
                    for ing in c["ingredientes"]:
                        if ing["id"] in PARA_COCINAR:
                            total[ing["id"]] = total.get(ing["id"], 0) + ing["g"] * factor
        tareas = []
        for aid in PARA_COCINAR:
            if total.get(aid):
                extra = PARA_COCINAR[aid]
                texto = alx.cantidad_legible(alx.ALIMENTOS[aid], total[aid])
                tareas.append({"id": aid, "g": round(total[aid]), "texto": texto[0].upper() + texto[1:]
                               + (f" — {extra}" if extra else "")})
        if tareas:
            salida.append({"cuando": cuando, "para": para, "tareas": tareas})
    return salida


ORDEN_GRUPO = {"origen_animal": 0, "leguminosas": 1, "cereales": 2, "verduras_frutas": 3, "grasas": 4}


def _peso(g: float) -> str:
    """750 g · 1.25 kg · 2 kg"""
    if g < 1000:
        return f"{g:.0f} g"
    return f"{g / 1000:.2f}".rstrip("0").rstrip(".") + " kg"


def texto_compra(a: "alx.Alimento", op: dict, g_comer: float) -> str:
    """Que pedir: '2 × Frijol negro Chedraui 900 g', '1.25 kg (≈ 7 plátanos)', '3 piezas'."""
    p = op["producto"]
    if p.granel:
        txt = _peso(op["g_compra"])
        if a.piezas[0] and a.g_unidad > 1:
            n = max(1, round(g_comer / a.g_unidad))
            txt += f" (≈ {n} {a.piezas[0] if n == 1 else a.piezas[1]})"
        return txt
    if "(pieza" in p.nombre:
        return f"{op['n']} pieza{'s' if op['n'] != 1 else ''}"
    return f"{op['n']} × {p.nombre}" if op["n"] > 1 else p.nombre


def texto_sobra(a: "alx.Alimento", op: dict, g_comer: float) -> str:
    """'te sobran ≈ 10 huevos (rinden para otra semana)' o '' si casi no sobra."""
    sobra = op["sobra"]
    if sobra < max(40.0, 0.12 * g_comer):
        return ""
    cuanto = alx.cantidad_legible(a, sobra) if a.unidad in ("pieza", "lata") and a.g_unidad > 1 else _peso(sobra)
    if pmx.dura(a.id) >= 4 or op["merma"] <= sobra * 0.25:       # despensa, o fresco que alcanzas a usar
        return f"te sobran ≈ {cuanto} para otras semanas"
    return f"sobran ≈ {cuanto}: úsalo pronto o congélalo"


def fila_lista(aid: str, g: float, precios: dict[str, float], ref: dict[str, float],
               tiendas: set[str] | None = None) -> dict:
    """Una fila de la lista: el producto real mas conveniente de tus tiendas, lo que pagas y
    lo que te sobra, mas las otras tiendas para comparar."""
    a = alx.ALIMENTOS[aid]
    fila = {"id": aid, "nombre": a.nombre, "g": round(g), "grupo": a.grupo}
    propio = abs(precios[aid] - ref[aid]) > 0.005
    ops = [] if propio else pmx.elegir(aid, g, g, tiendas)
    if not ops:                       # tu precio, o ningun producto en tus tiendas: por kilo
        return {**fila, "tienda": "otra", "producto": "", "compra": alx.compra_legible(a, g),
                "costo": round(precios[aid] * g / 1000, 2), "sobra": "", "queda": 0.0,
                "fuente": "tu precio" if propio else alx.fuente_de(aid), "otras": [], "sin_precio": []}
    o = ops[0]
    p = o["producto"]
    otras, vistas = [], {p.tienda}
    for x in ops[1:]:
        if x["producto"].tienda not in vistas:
            vistas.add(x["producto"].tienda)
            otras.append({"tienda": x["producto"].tienda, "producto": x["producto"].nombre, "costo": round(x["pagas"], 2)})
    sin_precio = [q.nombre for q in pmx.PRODUCTOS.get(aid, []) if not q.precio and (tiendas is None or q.tienda in tiendas)]
    return {**fila, "tienda": p.tienda, "producto": p.nombre, "compra": texto_compra(a, o, g),
            "costo": round(o["pagas"], 2), "sobra": texto_sobra(a, o, g), "queda": round(o["queda"], 2),
            "fuente": p.fuente, "otras": otras[:2], "sin_precio": sin_precio}


def lista_super(dias: list[dict], precios: dict[str, float] | None = None, factor: float = 1.0,
                tiendas: set[str] | None = None) -> list[dict]:
    """Lo de los 7 dias, para todo el hogar (factor = adultos + 0.6 x ninos), en productos
    reales: paquetes enteros, por tienda (las que usas; None = todas)."""
    precios = precios or alx.precios()
    ref = alx.precio_referencia()
    total: dict[str, float] = {}
    for d in dias:
        for c in d["comidas"]:
            for ing in c["ingredientes"]:
                total[ing["id"]] = total.get(ing["id"], 0) + ing["g"] * factor
    filas = [fila_lista(aid, g, precios, ref, tiendas) for aid, g in total.items()]
    orden_t = {t: i for i, t in enumerate(pmx.ORDEN_TIENDAS)}
    filas.sort(key=lambda f: (orden_t.get(f["tienda"], 9), ORDEN_GRUPO.get(f["grupo"], 9), -f["costo"]))
    return filas


def tiendas_de(cfg: dict) -> set[str] | None:
    """Las tiendas donde compras (dashboard); None = todas."""
    t = {x for x in (cfg.get("menu_tiendas") or []) if x in pmx.TIENDAS}
    return t or None


# ── guardar / subir ──────────────────────────────────────────────────────────
def guardar_local(menu: dict) -> None:
    MENU_LOCAL.write_text(json.dumps(menu, ensure_ascii=False), encoding="utf-8")


def leer_local() -> dict | None:
    if not MENU_LOCAL.exists():
        return None
    try:
        return json.loads(MENU_LOCAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def subir_menu(menu: dict) -> bool:
    """Sube el menu a InfinityFree para la app. Nunca lanza."""
    try:
        from dotenv import load_dotenv
        load_dotenv(AQUI / ".env")
        import planificar as pl
        base, token = pl.nutri_api_config()      # el menu lo muestra la app de nutricion
        sesion = pl.sesion_infinityfree(base)
        r = sesion.post(f"{base}/guardar_menu.php", headers={"X-API-Token": token}, timeout=60,
                        json={"semana_inicio": menu["semana_inicio"], "menu": menu})
        r.raise_for_status()
        return bool(r.json().get("ok"))
    except Exception as e:  # noqa: BLE001
        print(f"Menu no subido ({e.__class__.__name__}): la app conserva el anterior.")
        return False


def generar_y_publicar(cfg: dict | None = None, semana_inicio: date | None = None,
                       semilla: int | None = None, subir: bool = True) -> dict:
    """Lo que hacen el motor semanal y el boton del dashboard."""
    from config_usuario import cargar_config
    import planificar as pl
    cfg = cfg or cargar_config()
    if subir:
        descargar_no_me_gusta()          # lo que marcaste en la app cuenta para el menu nuevo
    menu = generar_menu(cfg, semana_inicio or pl.lunes_objetivo(), semilla)
    guardar_local(menu)
    if subir:
        subir_menu(menu)
    return menu


if __name__ == "__main__":
    import sys
    from config_usuario import cargar_config
    m = generar_menu(cargar_config(), date.today() - timedelta(days=date.today().weekday()))
    print(f"Por tipo de dia: {m['meta']['kcal_por_tipo']}")
    print(f"Semana {m['semana_inicio']}: ${m['costo_semana']:.0f} (${m['costo_dia']:.0f}/día) | "
          f"{m['kcal_prom']} kcal y {m['prot_prom']} g de proteína en promedio "
          f"(meta {m['meta']['kcal']} kcal, {m['meta']['proteina_min']} g)")
    for d in m["dias"]:
        print(f"\n{d['nombre']} ({d['tipo']}, meta {d['kcal_meta']}): {d['kcal']} kcal, {d['prot']} g prot, ${d['costo']:.0f}")
        for c in d["comidas"]:
            print(f"  [{c['tiempo']}] {c['nombre']}: " + ", ".join(i["texto"] for i in c["ingredientes"]))
    print("\nLISTA DEL SÚPER")
    for f in m["lista"]:
        print(f"  {f['nombre']}: {f['compra']}  ~${f['costo']:.0f}")
    sys.exit(0)

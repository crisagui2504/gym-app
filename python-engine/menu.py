"""Menu semanal BARATO que cumple tus calorias y tu proteina.

Para cada dia prueba todas las combinaciones de desayuno x comida x cena x
tamano de porcion x colacion (~70 mil, con numpy tarda milisegundos) y elige
la MAS BARATA que:
  - queda a +/-6 % de tus kcal objetivo (nutricion.metas: enfoque + ajustes), y
  - llega a tu proteina minima (rango g/kg del enfoque x tu peso).
La variedad se cuida con penalizaciones: repetir una receta en la semana
"cuesta" de mas y cada receta tiene un tope de veces; la comida y la cena del
mismo dia nunca repiten la fuente de proteina.

Comida mexicana de diario (frijol, huevo, tortilla, pollo, atun, lentejas,
soya...) con precios de Profeco donde hay dato y estimados editables donde no
(alimentos_mx.py). Resultado: los 7 dias, la lista del super y el costo.
"""
from __future__ import annotations

import json
import math
import pathlib
import random
from datetime import date, timedelta

import numpy as np

import alimentos_mx as alx
import nutricion
from dataclasses import replace
from recetas_mx import RECETAS, Receta

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

# Grupos para las reglas de cada dieta
CARNE_ROJA = {"res", "res_magra", "cerdo"}
PESCADO = {"atun", "sardina", "tilapia", "camaron"}
NUECES = {"nuez", "almendra", "cacahuate", "crema_cacahuate", "chia"}
LACTEO_PORCION = {"leche": 250, "leche_light": 250, "yogur": 200, "yogur_griego": 200,
                  "queso_fresco": 40, "panela": 40, "requeson": 60}     # g de una porcion

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
}
ENFASIS = {"equilibrado": "Equilibrado", "proteina": "Más proteína", "carbohidratos": "Más carbohidratos"}


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
    base, token = pl.api_config()
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
    return {"tiempo": r.tiempo, "receta": r.id, "nombre": r.nombre, "como": r.como,
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
    """kcal, prot, carb, costo, sodio, sat, verdfruta(g), lacteos(porciones), huevo(g), roja, pescado, nuez."""
    v = np.zeros(12)
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
    por_dia = nutricion.kcal_por_dia(cfg)
    precios = precios or alx.precios()
    fuera = excluidos(cfg)
    no_recetas, _ = no_me_gusta()
    disp = [_con_dieta(r, dieta["cambios"], fuera) for r in RECETAS if r.id not in no_recetas]
    disp = [r for r in disp if not any(aid in fuera for aid, _ in r.ingredientes)]
    grupos = {t: [r for r in disp if r.tiempo == t] for t in ("desayuno", "comida", "cena", "colacion")}
    for t in ("desayuno", "comida", "cena"):
        if not grupos[t]:
            raise ValueError(f"Con lo que excluiste no queda ninguna receta de {t}.")
    rng = random.Random(semilla if semilla is not None else semana_inicio.toordinal())
    vec = {r.id: _vector(r, precios) for r in disp}
    esc = np.array(ESCALAS)
    vf_min, vf_ideal = dieta["verdfruta"]

    usos: dict[str, int] = {}
    comprados: set[str] = set()          # lo que ya esta en la lista del super de esta semana
    semana = {"roja": 0, "pescado": 0}
    dias, avisos = [], []
    for i in range(7):
        K = float(por_dia[i + 1]["kcal"])

        def escoger(lista: list[Receta], tiempo: str) -> list[Receta]:
            """~18 de ~50: las 5 mas baratas por kcal, las mas llenadoras, las 4 que mejor cumplen la dieta
            (y las 4 con mas proteina o carbos si pediste enfasis) + el resto al azar."""
            libres = [r for r in lista if usos.get(r.id, 0) < TOPE_USOS[tiempo] + topes_extra] or list(lista)
            if len(libres) <= POR_TIEMPO_DIA:
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
            resto = [r for r in libres if r not in fijas]
            return fijas + rng.sample(resto, max(0, POR_TIEMPO_DIA - len(fijas)))

        D, C, N = escoger(grupos["desayuno"], "desayuno"), escoger(grupos["comida"], "comida"), escoger(grupos["cena"], "cena")
        SN = [None] + grupos["colacion"]
        VD, VC, VN = (np.array([vec[r.id] for r in L]) for L in (D, C, N))
        VS = np.array([_vector(r, precios) if r is None else vec[r.id] for r in SN])

        def suma(col: int) -> np.ndarray:
            """(D, C, N, S, SN) del indicador `col`: las 3 comidas escaladas + la colacion."""
            base = VD[:, col][:, None, None] + VC[:, col][None, :, None] + VN[:, col][None, None, :]
            return base[..., None, None] * esc[None, None, None, :, None] + VS[:, col][None, None, None, None, :]

        kcal, prot, carb, costo = suma(0), suma(1), suma(2), suma(3)
        sodio, sat, verdfruta, lacteos, huevos = suma(4), suma(5), suma(6), suma(7), suma(8)

        def pen(lista):
            v = np.array([usos.get(r.id, 0) * PENALIZA_REPETIR * variedad if r else 0.0 for r in lista])
            tope = np.array([usos.get(r.id, 0) >= TOPE_USOS[r.tiempo] + topes_extra if r else False for r in lista])
            return v, tope
        vd, td = pen(D)
        vc, tc = pen(C)
        vn, tn = pen(N)
        vs, ts = pen(SN)
        castigo = (vd[:, None, None, None, None] + vc[None, :, None, None, None]
                   + vn[None, None, :, None, None] + vs[None, None, None, None, :])
        tope_usos = (td[:, None, None, None, None] | tc[None, :, None, None, None]
                     | tn[None, None, :, None, None] | ts[None, None, None, None, :])
        # reglas semanales de la dieta: carne roja con tope; pescado que falta, con premio
        roja = VC[:, 9][None, :, None, None, None] + VN[:, 9][None, None, :, None, None]
        roja_tope = (semana["roja"] + roja > dieta["roja_max"]) if dieta["roja_max"] is not None else np.zeros(1, bool)
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
        misma_fuente = (fuente_c[:, None] == fuente_n[None, :])[None, :, :, None, None]

        def dieta_ok(nivel, sod, sa, kc, vf, lac, pescado):
            """nivel 2: la dieta completa (verdura ideal, lacteos, pescado del dia);
            1: lo basico (sodio, grasa saturada, verdura minima); 0: nada."""
            ok = True
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
                pre &= dieta_ok(con_dieta, sodio * 0.97, sat * 0.97, kcal, verdfruta * 1.03, lacteos * 1.05, pez)
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
                cand = [_servir(D[d_i], s, precios), _servir(C[c_i], s, precios), _servir(N[n_i], s, precios)]
                if SN[sn_i]:
                    cand.insert(2, _servir(SN[sn_i], 1.0, precios))
                tot = {k_: sum(c[k_] for c in cand)
                       for k_ in ("kcal", "prot", "carb", "sodio", "sat", "verdfruta", "lacteos")}
                huevo_real = sum(x["g"] for c in cand for x in c["ingredientes"] if x["id"] == "huevo")
                if (abs(tot["kcal"] - K) <= K * tol and huevo_real <= MAX_HUEVO_DIA
                        and (not con_prot or tot["prot"] >= P)
                        and (not (con_enfasis and C_obj) or tot["carb"] >= C_obj)
                        and (not con_dieta or bool(dieta_ok(con_dieta, tot["sodio"], tot["sat"], tot["kcal"],
                                                            tot["verdfruta"] * 1.03, tot["lacteos"] * 1.05,
                                                            vec[C[c_i].id][10] + vec[N[n_i].id][10])))):
                    elegido = (d_i, c_i, n_i, sn_i, cand, s)
                    break
            if elegido:
                sueltos = []
                if enfasis != "equilibrado" and not con_enfasis:
                    sueltos.append("el énfasis en " + ("proteína" if enfasis == "proteina" else "carbohidratos"))
                if clave_dieta != "mexicana" and not con_dieta:
                    sueltos.append("alguna regla de la dieta " + dieta["nombre"].split(" (")[0])
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
        for c in elegidas:
            otra = recetas_dia["cena" if c["tiempo"] == "comida" else "comida"] if c["tiempo"] in ("comida", "cena") else None
            sodio_libre = (dieta["sodio_alimentos"] - (sodio_dia - c["sodio"])) if dieta["sodio_alimentos"] else None
            c["alternativas"] = _alternativas(c, grupos[c["tiempo"]], 1.0 if c["tiempo"] == "colacion" else s_dia,
                                              precios, _fuente(otra) if otra else None,
                                              MAX_HUEVO_DIA - huevo_dia, sodio_libre=sodio_libre,
                                              sin_roja=dieta["roja_max"] is not None and semana["roja"] >= dieta["roja_max"])
        for r in recetas_dia.values():
            if r:
                usos[r.id] = usos.get(r.id, 0) + 1
                comprados.update(a for a, _ in r.ingredientes)
        semana["roja"] += int(vec[C[c_i].id][9] + vec[N[n_i].id][9])
        semana["pescado"] += int(vec[C[c_i].id][10] + vec[N[n_i].id][10])
        fecha = semana_inicio + timedelta(days=i)
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
                     "sal_g": (round(max(0.0, (dieta["sodio_max"] - tot["sodio"]) / SAL_G_MG), 1)
                               if dieta["sodio_max"] else None)})

    hogar = factor_hogar(cfg)
    lista = lista_super(dias, precios, hogar)
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
                  "cumple": cumplimiento_dieta(dias, dieta, semana, fuera)},
        "dias": dias,
        "lista": lista,
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
        "alimentos": {aid: _ficha(alx.ALIMENTOS[aid], precios[aid]) for aid in sorted(usados)},
        "nota": "Cantidades en crudo (frijol, lentejas, arroz y avena en seco). Precios de referencia: "
                "Profeco 2026 donde hay dato; el resto estimado. Corrígelos con lo que pagas.",
    }


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
    if dieta["pescado_min"]:
        reglas.append({"regla": f"Pescado o mariscos ≥ {dieta['pescado_min']} veces por semana",
                       "valor": str(semana["pescado"]), "ok": semana["pescado"] >= dieta["pescado_min"]})
    return reglas


def _alternativas(elegida: dict, opciones: list[Receta], escala: float, precios: dict[str, float],
                  fuente_prohibida: str | None, huevo_libre: float, n: int = 3,
                  sodio_libre: float | None = None, sin_roja: bool = False) -> list[dict]:
    """Hasta `n` recetas del mismo tiempo, parecidas a la elegida: kcal a +/-12 %
    (colaciones +/-40 %), al menos 85 % de su proteina, sin repetir la proteina
    de la otra comida fuerte ni pasarse de huevo. Las mas baratas primero."""
    k0, p0 = elegida["kcal"], elegida["prot"]
    huevo0 = sum(i["g"] for i in elegida["ingredientes"] if i["id"] == "huevo")
    tol = 0.40 if elegida["tiempo"] == "colacion" else 0.12
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
            if (abs(m["kcal"] - k0) <= k0 * tol and m["prot"] >= p0 * min_prot and huevo - huevo0 <= huevo_libre
                    and (sodio_libre is None or m["sodio"] <= sodio_libre)):
                if mejor is None or abs(m["kcal"] - k0) < abs(mejor["kcal"] - k0):
                    mejor = m
        if mejor:
            salida.append(mejor)
    salida.sort(key=lambda m: m["costo"])
    return salida[:n]


def _ficha(a: "alx.Alimento", precio: float) -> dict:
    return {"nombre": a.nombre, "precio_kg": round(precio, 2), "compra": a.compra, "g_compra": a.g_compra,
            "piezas": list(a.piezas), "seco_por_taza": a.seco_por_taza, "grupo": a.grupo}


# lo que conviene cocinar por adelantado; lo cocido dura 3-4 dias en el refri
# (USDA, "Leftovers and Food Safety"), por eso se cocina dos veces por semana
PARA_COCINAR = {"frijol": "en olla", "lentejas": "en olla", "arroz": "", "pollo": "cocer y deshebrar",
                "pechuga": "cocer y deshebrar"}
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
    salida = []
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


def lista_super(dias: list[dict], precios: dict[str, float] | None = None, factor: float = 1.0) -> list[dict]:
    """Lo de los 7 dias, para todo el hogar (factor = adultos + 0.6 x ninos)."""
    precios = precios or alx.precios()
    total: dict[str, float] = {}
    for d in dias:
        for c in d["comidas"]:
            for ing in c["ingredientes"]:
                total[ing["id"]] = total.get(ing["id"], 0) + ing["g"] * factor
    orden = {"leguminosas": 0, "origen_animal": 1, "cereales": 2, "verduras_frutas": 3, "grasas": 4}
    filas = []
    for aid, g in total.items():
        a = alx.ALIMENTOS[aid]
        filas.append({"id": aid, "nombre": a.nombre, "g": round(g), "compra": alx.compra_legible(a, g),
                      "costo": round(precios[aid] * g / 1000, 2), "grupo": a.grupo,
                      "fuente": "tu precio" if precios[aid] != a.precio_kg else a.fuente})
    filas.sort(key=lambda f: (orden.get(f["grupo"], 9), -f["costo"]))
    return filas


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
        base, token = pl.api_config()
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

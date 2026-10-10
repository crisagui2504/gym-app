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
from recetas_mx import RECETAS, Receta

AQUI = pathlib.Path(__file__).resolve().parent
MENU_LOCAL = AQUI / "menu_semana.json"       # copia para el dashboard (ignorada por git)
ESCALAS = (0.75, 1.0, 1.25, 1.5, 1.75, 2.0)  # tamano de las 3 comidas del dia
TOLERANCIA_KCAL = 0.05
MAX_HUEVO_DIA = 200          # g: 4 huevos al dia como mucho (variedad, no salud)
TOPE_USOS = {"desayuno": 3, "comida": 2, "cena": 2, "colacion": 3}
PENALIZA_REPETIR = 9.0       # $ "virtuales" por cada vez que la receta ya salio
NOMBRES_DIA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def excluidos(cfg: dict) -> set[str]:
    """Alimentos que no comes: ids sueltos o grupos (carnes, pescado, lacteos...)."""
    fuera: set[str] = set()
    for x in cfg.get("alimentos_excluidos") or []:
        fuera.update(alx.GRUPOS_EXCLUIBLES.get(x, [x]))
    if not cfg.get("menu_suplementos", False):
        fuera.add("proteina_polvo")          # solo si lo activas: comida primero
    return fuera


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
    fibra = hierro = calcio = 0.0
    for aid, g in r.ingredientes:
        a = alx.ALIMENTOS[aid]
        gg = _redondear(aid, g * escala)
        ing.append({"id": aid, "nombre": a.nombre, "g": gg, "texto": alx.cantidad_legible(a, gg)})
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
            "hierro": round(hierro, 1), "calcio": round(calcio), "costo": round(costo, 2)}


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


def _generar(cfg: dict, semana_inicio: date, semilla: int | None = None, precios: dict[str, float] | None = None,
             variedad: float = 1.0, topes_extra: int = 0) -> dict:
    meta = nutricion.metas(cfg)
    K_sem, P = float(meta["kcal"]), float(meta["proteina_min"])
    # kcal de CADA dia segun lo que gasta (pesas, deporte, cardio, descanso); la
    # semana promedia exactamente tu meta. La proteina es la misma todos los dias.
    por_dia = nutricion.kcal_por_dia(cfg)
    precios = precios or alx.precios()
    fuera = excluidos(cfg)
    disp = [r for r in RECETAS if not any(aid in fuera for aid, _ in r.ingredientes)]
    grupos = {t: [r for r in disp if r.tiempo == t] for t in ("desayuno", "comida", "cena", "colacion")}
    for t in ("desayuno", "comida", "cena"):
        if not grupos[t]:
            raise ValueError(f"Con lo que excluiste no queda ninguna receta de {t}.")
    rng = random.Random(semilla if semilla is not None else semana_inicio.toordinal())

    def arr(lista):
        v = np.array([_valores(r, precios) for r in lista]) if lista else np.zeros((0, 3))
        return v[:, 0], v[:, 1], v[:, 2]

    D, C, N = grupos["desayuno"], grupos["comida"], grupos["cena"]
    SN = [None] + grupos["colacion"]
    kd, pd_, cd = arr(D)
    kc, pc, cc = arr(C)
    kn, pn, cn = arr(N)
    ks = np.array([0.0] + [_valores(r, precios)[0] for r in SN[1:]])
    ps = np.array([0.0] + [_valores(r, precios)[1] for r in SN[1:]])
    cs = np.array([0.0] + [_valores(r, precios)[2] for r in SN[1:]])
    esc = np.array(ESCALAS)

    def huevo(lista):
        return np.array([sum(g for aid, g in r.ingredientes if aid == "huevo") if r else 0.0 for r in lista])
    hb = huevo(D)[:, None, None] + huevo(C)[None, :, None] + huevo(N)[None, None, :]
    huevos = hb[..., None, None] * esc[None, None, None, :, None] + huevo(SN)[None, None, None, None, :]
    fuente_c = np.array([_fuente(r) for r in C])
    fuente_n = np.array([_fuente(r) for r in N])
    misma = (fuente_c[:, None] == fuente_n[None, :]).astype(float)        # (C, N)

    # base de las 3 comidas: (D, C, N); luego x escala y + colacion -> (D, C, N, S, SN)
    kb = kd[:, None, None] + kc[None, :, None] + kn[None, None, :]
    pb = pd_[:, None, None] + pc[None, :, None] + pn[None, None, :]
    cb = cd[:, None, None] + cc[None, :, None] + cn[None, None, :]
    kcal = kb[..., None, None] * esc[None, None, None, :, None] + ks[None, None, None, None, :]
    prot = pb[..., None, None] * esc[None, None, None, :, None] + ps[None, None, None, None, :]
    costo = cb[..., None, None] * esc[None, None, None, :, None] + cs[None, None, None, None, :]

    usos: dict[str, int] = {}
    dias, avisos = [], []
    for i in range(7):
        K = float(por_dia[i + 1]["kcal"])

        def pen(lista, idx_offset=0):
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
        # un poco de azar en la comida: "otro menu" da otro menu, no el mismo
        ruido = np.array([rng.uniform(0, 2.5 * variedad) for _ in range(len(C))])[None, :, None, None, None]
        desvio = np.abs(kcal - K)
        objetivo = costo + castigo + ruido + desvio * 0.01      # $1 por cada 100 kcal de desvio
        mucho_huevo = huevos > MAX_HUEVO_DIA + 1          # este tope nunca se relaja
        misma_fuente = (misma > 0)[None, :, :, None, None]
        elegido = None
        aviso = None
        # La cuenta de arriba es ANTES de redondear (huevos y tortillas enteros mueven
        # las kcal). Se revisan los mejores candidatos con sus totales REALES y se
        # toma el primero que cumple. Etapas: normal -> mas holgura -> sin la
        # proteina (no se alcanza con comida; se avisa) -> y si con lo que excluiste
        # quedan pocas recetas, se relaja la VARIEDAD (repetir recetas, misma
        # proteina comida y cena) antes que dejarte sin menu.
        etapas = ((TOLERANCIA_KCAL, True, True), (0.08, True, True), (0.08, False, True),
                  (0.08, True, False), (0.10, False, False))
        for tol, exige_prot, con_variedad in etapas:
            bloqueo = mucho_huevo | ((tope_usos | misma_fuente) if con_variedad else False)
            pre = (desvio <= K * (tol + 0.05)) & ~bloqueo
            if exige_prot:
                pre &= prot >= P * 0.95
                obj = objetivo
            else:
                obj = -prot + costo * 0.05 + castigo * 0.1 + desvio * 0.005
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
                kc_real = sum(c["kcal"] for c in cand)
                pr_real = sum(c["prot"] for c in cand)
                huevo_real = sum(i["g"] for c in cand for i in c["ingredientes"] if i["id"] == "huevo")
                if (abs(kc_real - K) <= K * tol and huevo_real <= MAX_HUEVO_DIA
                        and (not exige_prot or pr_real >= P)):
                    elegido = (d_i, c_i, n_i, sn_i, cand, s)
                    break
            if elegido:
                if not exige_prot:
                    aviso = ("No se alcanza tu proteína con estas recetas y calorías: suma una porción "
                             "de las del botón Proteína (atún, huevo) o activa los suplementos.")
                elif not con_variedad:
                    aviso = "Con lo que excluiste quedan pocas recetas: este día repite más de lo normal."
                break
        if not elegido:
            raise ValueError("No hay combinación posible: revisa lo que excluiste.")
        d_i, c_i, n_i, sn_i, elegidas, s_dia = elegido
        # alternativas para "Cambiar" esta comida (parecidas en kcal y proteina)
        recetas_dia = {"desayuno": D[d_i], "comida": C[c_i], "cena": N[n_i], "colacion": SN[sn_i]}
        huevo_dia = sum(ing["g"] for c in elegidas for ing in c["ingredientes"] if ing["id"] == "huevo")
        for c in elegidas:
            otra = recetas_dia["cena" if c["tiempo"] == "comida" else "comida"] if c["tiempo"] in ("comida", "cena") else None
            c["alternativas"] = _alternativas(c, grupos[c["tiempo"]], 1.0 if c["tiempo"] == "colacion" else s_dia,
                                              precios, _fuente(otra) if otra else None,
                                              MAX_HUEVO_DIA - huevo_dia)
        for r in (D[d_i], C[c_i], N[n_i], SN[sn_i]):
            if r:
                usos[r.id] = usos.get(r.id, 0) + 1
        fecha = semana_inicio + timedelta(days=i)
        tot = {k: sum(c[k] for c in elegidas)
               for k in ("kcal", "prot", "carb", "grasa", "fibra", "hierro", "calcio", "costo")}
        if aviso:
            avisos.append(f"{NOMBRES_DIA[i]}: {aviso}")
        dias.append({"dia": i + 1, "nombre": NOMBRES_DIA[i], "fecha": fecha.isoformat(), "comidas": elegidas,
                     "tipo": por_dia[i + 1]["tipo"], "kcal_meta": int(K),
                     "kcal": round(tot["kcal"]), "prot": round(tot["prot"]), "carb": round(tot["carb"]),
                     "grasa": round(tot["grasa"]), "fibra": round(tot["fibra"]), "hierro": round(tot["hierro"], 1),
                     "calcio": round(tot["calcio"]), "costo": round(tot["costo"], 2)})

    hogar = factor_hogar(cfg)
    lista = lista_super(dias, precios, hogar)
    costo_sem = round(sum(d["costo"] for d in dias), 2)
    usados = {ing["id"] for d in dias for c in d["comidas"]
              for x in [c, *c.get("alternativas", [])] for ing in x["ingredientes"]}
    return {
        "semana_inicio": semana_inicio.isoformat(),
        "meta": {"kcal": round(K_sem), "proteina_min": round(P), "proteina_max": meta["proteina_max"],
                 "enfoque": meta["enfoque"], "peso": meta["peso"],
                 "kcal_por_tipo": nutricion.resumen_por_tipo(cfg)},
        "dias": dias,
        "lista": lista,
        "costo_semana": costo_sem,
        "costo_dia": round(costo_sem / 7, 2),
        "kcal_prom": round(sum(d["kcal"] for d in dias) / 7),
        "prot_prom": round(sum(d["prot"] for d in dias) / 7),
        "excluidos": sorted(fuera),
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


def _alternativas(elegida: dict, opciones: list[Receta], escala: float, precios: dict[str, float],
                  fuente_prohibida: str | None, huevo_libre: float, n: int = 3) -> list[dict]:
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
        mejor = None
        for e in escalas:
            m = _servir(r, e, precios)
            huevo = sum(i["g"] for i in m["ingredientes"] if i["id"] == "huevo")
            if abs(m["kcal"] - k0) <= k0 * tol and m["prot"] >= p0 * min_prot and huevo - huevo0 <= huevo_libre:
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
    prom = {k: round(sum(d.get(k, 0) for d in dias) / 7, 1) for k in ("fibra", "hierro", "calcio")}
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

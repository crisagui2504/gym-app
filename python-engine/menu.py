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
    for aid, g in r.ingredientes:
        a = alx.ALIMENTOS[aid]
        gg = _redondear(aid, g * escala)
        ing.append({"id": aid, "nombre": a.nombre, "g": gg, "texto": alx.cantidad_legible(a, gg)})
        kcal += a.kcal * gg / 100
        prot += a.prot * gg / 100
        carb += a.carb * gg / 100
        grasa += a.grasa * gg / 100
        costo += precios[aid] * gg / 1000
    return {"tiempo": r.tiempo, "receta": r.id, "nombre": r.nombre, "como": r.como,
            "ingredientes": ing, "kcal": round(kcal), "prot": round(prot, 1),
            "carb": round(carb), "grasa": round(grasa), "costo": round(costo, 2)}


def generar_menu(cfg: dict, semana_inicio: date, semilla: int | None = None,
                 precios: dict[str, float] | None = None) -> dict:
    meta = nutricion.metas(cfg)
    K, P = float(meta["kcal"]), float(meta["proteina_min"])
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
        def pen(lista, idx_offset=0):
            v = np.array([usos.get(r.id, 0) * PENALIZA_REPETIR if r else 0.0 for r in lista])
            tope = np.array([usos.get(r.id, 0) >= TOPE_USOS[r.tiempo] if r else False for r in lista])
            return v, tope
        vd, td = pen(D)
        vc, tc = pen(C)
        vn, tn = pen(N)
        vs, ts = pen(SN)
        castigo = (vd[:, None, None, None, None] + vc[None, :, None, None, None]
                   + vn[None, None, :, None, None] + vs[None, None, None, None, :])
        bloqueo = (td[:, None, None, None, None] | tc[None, :, None, None, None]
                   | tn[None, None, :, None, None] | ts[None, None, None, None, :])
        # un poco de azar en la comida: "otro menu" da otro menu, no el mismo
        ruido = np.array([rng.uniform(0, 2.5) for _ in range(len(C))])[None, :, None, None, None]
        desvio = np.abs(kcal - K)
        objetivo = costo + castigo + ruido + desvio * 0.01      # $1 por cada 100 kcal de desvio
        bloqueo = bloqueo | (huevos > MAX_HUEVO_DIA + 1) | (misma > 0)[None, :, :, None, None]
        elegido = None
        aviso = None
        # La cuenta de arriba es ANTES de redondear (huevos y tortillas enteros mueven
        # las kcal). Se revisan los mejores candidatos con sus totales REALES y se
        # toma el primero que cumple. Etapas: normal -> mas holgura -> sin la
        # proteina (no se alcanza con comida; se avisa).
        for tol, exige_prot in ((TOLERANCIA_KCAL, True), (0.08, True), (0.08, False)):
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
                    elegido = (d_i, c_i, n_i, sn_i, cand)
                    break
            if elegido:
                if not exige_prot:
                    aviso = ("No se alcanza tu proteína con estas recetas y calorías: suma una porción "
                             "de las del botón Proteína (atún, huevo) o activa los suplementos.")
                break
        if not elegido:
            raise ValueError("No hay combinación posible: revisa lo que excluiste.")
        d_i, c_i, n_i, sn_i, elegidas = elegido
        for r in (D[d_i], C[c_i], N[n_i], SN[sn_i]):
            if r:
                usos[r.id] = usos.get(r.id, 0) + 1
        fecha = semana_inicio + timedelta(days=i)
        tot = {k: sum(c[k] for c in elegidas) for k in ("kcal", "prot", "carb", "grasa", "costo")}
        if aviso:
            avisos.append(f"{NOMBRES_DIA[i]}: {aviso}")
        dias.append({"dia": i + 1, "nombre": NOMBRES_DIA[i], "fecha": fecha.isoformat(), "comidas": elegidas,
                     "kcal": round(tot["kcal"]), "prot": round(tot["prot"]), "carb": round(tot["carb"]),
                     "grasa": round(tot["grasa"]), "costo": round(tot["costo"], 2)})

    lista = lista_super(dias, precios)
    costo_sem = round(sum(d["costo"] for d in dias), 2)
    return {
        "semana_inicio": semana_inicio.isoformat(),
        "meta": {"kcal": round(K), "proteina_min": round(P), "proteina_max": meta["proteina_max"],
                 "enfoque": meta["enfoque"], "peso": meta["peso"]},
        "dias": dias,
        "lista": lista,
        "costo_semana": costo_sem,
        "costo_dia": round(costo_sem / 7, 2),
        "kcal_prom": round(sum(d["kcal"] for d in dias) / 7),
        "prot_prom": round(sum(d["prot"] for d in dias) / 7),
        "excluidos": sorted(fuera),
        "avisos": avisos,
        "nota": "Cantidades en crudo (frijol, lentejas, arroz y avena en seco). Precios de referencia: "
                "Profeco 2026 donde hay dato; el resto estimado. Corrígelos con lo que pagas.",
    }


def lista_super(dias: list[dict], precios: dict[str, float] | None = None) -> list[dict]:
    precios = precios or alx.precios()
    total: dict[str, float] = {}
    for d in dias:
        for c in d["comidas"]:
            for ing in c["ingredientes"]:
                total[ing["id"]] = total.get(ing["id"], 0) + ing["g"]
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
    print(f"Semana {m['semana_inicio']}: ${m['costo_semana']:.0f} (${m['costo_dia']:.0f}/día) | "
          f"{m['kcal_prom']} kcal y {m['prot_prom']} g de proteína en promedio "
          f"(meta {m['meta']['kcal']} kcal, {m['meta']['proteina_min']} g)")
    for d in m["dias"]:
        print(f"\n{d['nombre']}: {d['kcal']} kcal, {d['prot']} g prot, ${d['costo']:.0f}")
        for c in d["comidas"]:
            print(f"  [{c['tiempo']}] {c['nombre']}: " + ", ".join(i["texto"] for i in c["ingredientes"]))
    print("\nLISTA DEL SÚPER")
    for f in m["lista"]:
        print(f"  {f['nombre']}: {f['compra']}  ~${f['costo']:.0f}")
    sys.exit(0)

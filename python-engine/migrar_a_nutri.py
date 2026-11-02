"""Copia UNA VEZ tus datos de comida de GymTracker a la app de nutricion.

Desde la fase 2, la app de nutricion (crisrodrigo.infinityfree.io) es la unica
fuente de la proteina, el peso, la meta, el menu y los "no me gusta"
(planificar.nutri_api_config). Este script trae lo que ya tenias en la base de
GymTracker. Solo AGREGA lo que le falta a la de nutricion: nunca pisa algo que
ya anotaste alla. Correrlo dos veces es seguro (la segunda no copia nada).

Uso (en la VM o en el PC, con NUTRI_API_BASE_URL y NUTRI_API_TOKEN en el .env):
    python migrar_a_nutri.py --probar     # solo dice que copiaria
    python migrar_a_nutri.py
"""
from __future__ import annotations

import sys
from datetime import date


def _get(api, archivo: str, **params) -> dict:
    sesion, base, token = api
    r = sesion.get(f"{base}/{archivo}", params=params or None, headers={"X-API-Token": token}, timeout=60)
    r.raise_for_status()
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"{archivo}: {j.get('error')}")
    return j


def _post(api, archivo: str, cuerpo: dict) -> bool:
    sesion, base, token = api
    r = sesion.post(f"{base}/{archivo}", json=cuerpo, headers={"X-API-Token": token}, timeout=60)
    r.raise_for_status()
    return bool(r.json().get("ok"))


def migrar(origen, destino, probar: bool = False, hoy: date | None = None) -> dict[str, int]:
    """origen/destino: (sesion, base_url, token). Devuelve cuanto se copio (o se copiaria)."""
    hoy = hoy or date.today()
    copia = {"proteina": 0, "peso": 0, "no_me_gusta": 0, "meta": 0, "menu": 0}

    def subir(clave: str, archivo: str, cuerpo: dict) -> None:
        if probar or _post(destino, archivo, cuerpo):
            copia[clave] += 1

    # proteina del dia (con sus porciones: creatina, "Lo comi"...)
    o, d = _get(origen, "get_nutricion.php", dias=180), _get(destino, "get_nutricion.php", dias=180)
    ya = {str(x["fecha"])[:10] for x in d.get("dias") or []}
    for x in o.get("dias") or []:
        if str(x["fecha"])[:10] not in ya:
            subir("proteina", "guardar_proteina.php", {"fecha": str(x["fecha"])[:10], "proteina_g": float(x["proteina_g"]),
                                                       "porciones": x.get("porciones") or {}})
    # meta: solo si la de nutricion aun no tiene (el motor la vuelve a calcular despues)
    if o.get("meta") and not d.get("meta"):
        m = o["meta"]
        subir("meta", "guardar_meta_nutricion.php", {k: m.get(k) for k in ("proteina_min", "proteina_max", "kcal", "peso", "enfoque")})

    # peso y cintura
    o, d = _get(origen, "get_peso.php", dias=3650), _get(destino, "get_peso.php", dias=3650)
    ya = {str(x["fecha"])[:10] for x in d.get("pesos") or []}
    for x in o.get("pesos") or []:
        if str(x["fecha"])[:10] not in ya:
            cuerpo = {"fecha": str(x["fecha"])[:10], "peso": float(x["peso"])}
            if x.get("cintura") is not None:
                cuerpo["cintura"] = float(x["cintura"])
            subir("peso", "guardar_peso.php", cuerpo)

    # "no me gusta" del menu
    o, d = _get(origen, "get_no_me_gusta.php"), _get(destino, "get_no_me_gusta.php")
    for tipo, clave in (("receta", "recetas"), ("alimento", "alimentos")):
        for x in sorted(set(o.get(clave) or []) - set(d.get(clave) or [])):
            subir("no_me_gusta", "guardar_no_me_gusta.php", {"tipo": tipo, "id": x})

    # menu de la semana (si la de nutricion aun no tiene uno)
    o, d = _get(origen, "get_menu.php", fecha=hoy.isoformat()), _get(destino, "get_menu.php", fecha=hoy.isoformat())
    if o.get("menu") and not d.get("menu"):
        subir("menu", "guardar_menu.php", {"semana_inicio": o["menu"]["semana_inicio"], "menu": o["menu"]})
    return copia


def main() -> int:
    import planificar as pl
    probar = "--probar" in sys.argv
    base_g, token_g = pl.api_config()
    base_n, token_n = pl.nutri_api_config()
    if base_n == base_g:
        print("No hay app de nutricion en el .env (NUTRI_API_BASE_URL y NUTRI_API_TOKEN): nada que migrar.")
        return 1
    origen = (pl.sesion_infinityfree(base_g), base_g, token_g)
    destino = (pl.sesion_infinityfree(base_n), base_n, token_n)
    copia = migrar(origen, destino, probar)
    verbo = "Se copiaria" if probar else "Copiado"
    print(f"{verbo} de GymTracker a nutricion: " + ", ".join(f"{k} {v}" for k, v in copia.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

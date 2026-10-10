"""Alimentos comunes y baratos de Mexico para el menu semanal (menu.py).

Nutrimentos por 100 g del alimento TAL COMO SE USA EN LA RECETA (crudo; las
leguminosas, el arroz, la avena y la pasta en SECO). Valores aproximados de
USDA FoodData Central y tablas mexicanas (SMAE / INCMNSZ): sirven para
planear, no para una dieta clinica.

Precios en pesos por kg (o por litro) de la parte que se come:
  - "Profeco": promedios nacionales publicados por Profeco en 2026
    (huevo, pollo y frijol: mayo; canasta PACIC: septiembre).
  - "estimado": referencia de octubre de 2026 SIN fuente oficial. Varian
    mucho por ciudad y tienda: corrigelos con lo que pagas (pestana Menu del
    dashboard -> precios_alimentos.json).
El pollo entero de Profeco ($38.9/kg) se convierte a carne aprovechable con
un rendimiento de ~65 % (hueso y piel): ~$60 por kg de carne.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

AQUI = pathlib.Path(__file__).resolve().parent
PRECIOS_USUARIO = AQUI / "precios_alimentos.json"     # tus precios (los edita el dashboard)


@dataclass(frozen=True)
class Alimento:
    id: str
    nombre: str
    kcal: float          # por 100 g
    prot: float
    carb: float
    grasa: float
    precio_kg: float     # MXN por kg (o L) de lo que se come
    fuente: str          # "Profeco ..." | "estimado"
    grupo: str           # verduras_frutas | cereales | leguminosas | origen_animal | grasas
    unidad: str = "g"    # como se muestra en la receta: g | pieza | taza | lata | ml
    g_unidad: float = 1  # gramos por unidad mostrada
    compra: str = "kg"   # como se compra: kg | pieza | L | lata
    g_compra: float = 1000
    seco_por_taza: float = 0   # leguminosas/cereales: g en seco por taza ya cocida
    piezas: tuple[str, str] = ("", "")   # ("huevo", "huevos") para decir "3 huevos"


_P_MAY = "Profeco may-2026"
_P_SEP = "Profeco sep-2026 (PACIC)"
_EST = "estimado"

ALIMENTOS: dict[str, Alimento] = {a.id: a for a in [
    # ── leguminosas (lo mas barato por gramo de proteina) ──
    Alimento("frijol", "Frijol", 341, 21.6, 62.4, 1.4, 24.15, _P_MAY, "leguminosas", seco_por_taza=66),
    Alimento("lentejas", "Lentejas", 352, 24.6, 63.4, 1.1, 38, _EST, "leguminosas", seco_por_taza=70),
    Alimento("soya", "Soya texturizada", 330, 50.0, 30.0, 1.0, 55, _EST, "leguminosas"),
    # ── origen animal ──
    Alimento("huevo", "Huevo", 143, 12.6, 0.7, 9.5, 47.4, _P_MAY, "origen_animal", "pieza", 50, "pieza", 50, piezas=("huevo", "huevos")),
    Alimento("pollo", "Pollo (pierna y muslo)", 180, 18.5, 0, 11.5, 59.8, _P_MAY + " (entero, 65 % carne)", "origen_animal"),
    Alimento("pechuga", "Pechuga de pollo", 120, 22.5, 0, 2.6, 115, _EST, "origen_animal"),
    Alimento("res", "Carne molida de res", 250, 17.2, 0, 19.6, 100.55, _P_SEP, "origen_animal"),
    Alimento("cerdo", "Cerdo (pierna)", 143, 21.0, 0, 6.0, 67.5, _P_SEP, "origen_animal"),
    Alimento("atun", "Atún en agua", 116, 25.5, 0, 0.8, 140, _EST, "origen_animal", "lata", 100, "lata", 100),
    Alimento("sardina", "Sardina en tomate", 186, 17.8, 1.5, 12.0, 56, _EST, "origen_animal", "g", 1, "lata", 425),
    Alimento("leche", "Leche", 61, 3.2, 4.8, 3.3, 19.5, _P_SEP, "origen_animal", "ml", 1, "L", 1000),
    Alimento("yogur", "Yogur natural", 61, 3.5, 4.7, 3.3, 42, _EST, "origen_animal", "taza", 250, "kg", 1000),
    Alimento("queso_fresco", "Queso fresco", 299, 18.0, 3.0, 24.0, 130, _EST, "origen_animal"),
    Alimento("panela", "Queso panela", 260, 20.0, 2.0, 19.0, 150, _EST, "origen_animal"),
    # ── cereales y tuberculos ──
    Alimento("tortilla", "Tortilla de maíz", 218, 5.7, 44.6, 2.9, 27, _EST, "cereales", "pieza", 30, "kg", 1000, piezas=("tortilla", "tortillas")),
    Alimento("arroz", "Arroz", 360, 6.6, 79.3, 0.6, 26, _EST, "cereales", seco_por_taza=55),
    Alimento("avena", "Avena", 389, 16.9, 66.3, 6.9, 42, _EST, "cereales", "taza", 80),
    Alimento("pasta", "Pasta para sopa", 371, 13.0, 74.7, 1.5, 35, _EST, "cereales"),
    Alimento("papa", "Papa", 77, 2.0, 17.5, 0.1, 43.28, _P_SEP, "cereales", "pieza", 150, piezas=("papa", "papas")),
    # ── verduras y frutas ──
    Alimento("jitomate", "Jitomate", 18, 0.9, 3.9, 0.2, 19.1, _P_SEP, "verduras_frutas", "pieza", 120, piezas=("jitomate", "jitomates")),
    Alimento("cebolla", "Cebolla", 40, 1.1, 9.3, 0.1, 38.37, _P_SEP, "verduras_frutas", "pieza", 150, piezas=("cebolla", "cebollas")),
    Alimento("zanahoria", "Zanahoria", 41, 0.9, 9.6, 0.2, 12.14, _P_SEP, "verduras_frutas", "pieza", 70, piezas=("zanahoria", "zanahorias")),
    Alimento("calabacita", "Calabacita", 17, 1.2, 3.1, 0.3, 28, _EST, "verduras_frutas", "pieza", 200, piezas=("calabacita", "calabacitas")),
    Alimento("nopales", "Nopales", 16, 1.3, 3.3, 0.1, 25, _EST, "verduras_frutas", "pieza", 80, piezas=("nopal", "nopales")),
    Alimento("espinaca", "Espinaca", 23, 2.9, 3.6, 0.4, 40, _EST, "verduras_frutas"),
    Alimento("chile", "Chile serrano o jalapeño", 32, 1.7, 6.7, 0.4, 35, _EST, "verduras_frutas", "pieza", 15, piezas=("chile", "chiles")),
    Alimento("platano", "Plátano", 89, 1.1, 22.8, 0.3, 15.22, _P_SEP, "verduras_frutas", "pieza", 120, piezas=("plátano", "plátanos")),
    Alimento("manzana", "Manzana", 52, 0.3, 13.8, 0.2, 37.4, _P_SEP, "verduras_frutas", "pieza", 150, piezas=("manzana", "manzanas")),
    Alimento("naranja", "Naranja", 47, 0.9, 11.8, 0.1, 22, _EST, "verduras_frutas", "pieza", 130, piezas=("naranja", "naranjas")),
    Alimento("limon", "Limón", 29, 1.1, 9.3, 0.3, 16.85, _P_SEP, "verduras_frutas", "pieza", 40, piezas=("limón", "limones")),
    # ── grasas ──
    Alimento("aguacate", "Aguacate", 160, 2.0, 8.5, 14.7, 60, _EST, "grasas", "pieza", 140, piezas=("aguacate", "aguacates")),
    Alimento("aceite", "Aceite vegetal", 884, 0, 0, 100, 31, _P_SEP, "grasas", "g", 1, "L", 920),
    Alimento("cacahuate", "Cacahuate natural", 567, 25.8, 16.1, 49.2, 90, _EST, "grasas"),
    Alimento("crema_cacahuate", "Crema de cacahuate", 588, 25.0, 20.0, 50.0, 130, _EST, "grasas"),
    # ── suplemento (solo si hace falta: es lo mas caro por gramo de proteina) ──
    Alimento("proteina_polvo", "Proteína en polvo", 380, 75.0, 8.0, 5.0, 600, _EST, "origen_animal", "scoop", 32),
]}

# lo que se puede excluir de golpe desde el dashboard
GRUPOS_EXCLUIBLES = {
    "carnes": ["pollo", "pechuga", "res", "cerdo"],
    "pescado": ["atun", "sardina"],
    "lacteos": ["leche", "yogur", "queso_fresco", "panela"],
    "huevo": ["huevo"],
    "suplementos": ["proteina_polvo"],
}


def precios() -> dict[str, float]:
    """Precio por kg de cada alimento: el tuyo si lo corregiste, si no el de referencia."""
    base = {a.id: a.precio_kg for a in ALIMENTOS.values()}
    if PRECIOS_USUARIO.exists():
        try:
            for k, v in json.loads(PRECIOS_USUARIO.read_text(encoding="utf-8")).items():
                if k in base and isinstance(v, (int, float)) and 0 < v < 5000:
                    base[k] = float(v)
        except (json.JSONDecodeError, OSError):
            pass
    return base


def guardar_precios(nuevos: dict[str, float]) -> None:
    """Guarda SOLO los precios que difieren de la referencia."""
    ref = {a.id: a.precio_kg for a in ALIMENTOS.values()}
    propios = {k: round(float(v), 2) for k, v in nuevos.items()
               if k in ref and v and 0 < float(v) < 5000 and abs(float(v) - ref[k]) > 0.005}
    PRECIOS_USUARIO.write_text(json.dumps(propios, indent=2, ensure_ascii=False), encoding="utf-8")


def cantidad_legible(a: Alimento, gramos: float) -> str:
    """La cantidad con el alimento: '3 huevos', '½ jitomate', '1 lata de atún en agua',
    '60 g de frijol en seco (≈ 1 taza cocida)', '375 ml de leche'."""
    nombre = a.nombre.lower()
    if a.unidad in ("pieza", "lata", "scoop", "taza") and a.g_unidad > 1:
        n = round(gramos / a.g_unidad * 2) / 2                # medios: "½ aguacate"
        if n == 0:
            return f"{gramos:.0f} g de {nombre}"
        txt = _fraccion(n)
        if a.unidad == "pieza" and a.piezas[0]:
            return f"{txt} {a.piezas[0] if n <= 1 else a.piezas[1]}"
        plural = {"pieza": "piezas", "lata": "latas", "scoop": "scoops", "taza": "tazas"}[a.unidad]
        return f"{txt} {a.unidad if n <= 1 else plural} de {nombre}"
    if a.unidad == "ml":
        return f"{gramos:.0f} ml de {nombre}"
    if a.seco_por_taza:
        tazas = round(gramos / a.seco_por_taza * 2) / 2
        extra = (f" (≈ {_fraccion(tazas)} taza{'s' if tazas > 1 else ''} cocida{'s' if tazas > 1 else ''})"
                 if tazas else "")
        return f"{gramos:.0f} g de {nombre} en seco{extra}"
    return f"{gramos:.0f} g de {nombre}"


def _fraccion(n: float) -> str:
    entero = int(n)
    medio = (n - entero) >= 0.5
    if entero == 0:
        return "½"
    return f"{entero}½" if medio else f"{entero}"


def compra_legible(a: Alimento, gramos: float) -> str:
    """Cantidad para la lista del super, en la unidad en que se compra."""
    if a.compra in ("pieza", "lata"):
        import math
        n = math.ceil(gramos / a.g_compra - 0.05)
        if a.compra == "pieza" and a.piezas[0]:
            return f"{n} {a.piezas[0] if n == 1 else a.piezas[1]}"
        return f"{n} {a.compra}{'s' if n != 1 else ''}"
    if a.compra == "L":
        return f"{gramos / 1000:.1f} L".replace(".0 L", " L")
    kg = gramos / 1000
    return f"{kg:.2f} kg" if kg < 1 else f"{kg:.1f} kg"

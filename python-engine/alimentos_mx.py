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
    fibra: float = 0     # g por 100 g
    hierro: float = 0    # mg por 100 g
    calcio: float = 0    # mg por 100 g
    sat: float = 0       # grasa saturada, g por 100 g
    sodio: float = 0     # mg por 100 g (del alimento, SIN la sal que se agrega al cocinar)


_P_MAY = "Profeco may-2026"
_P_SEP = "Profeco sep-2026 (PACIC)"
_EST = "estimado"

ALIMENTOS: dict[str, Alimento] = {a.id: a for a in [
    # ── leguminosas (lo mas barato por gramo de proteina) ──
    Alimento("frijol", "Frijol", 341, 21.6, 62.4, 1.4, 24.15, _P_MAY, "leguminosas", seco_por_taza=66, fibra=15.5, hierro=5.0, calcio=123, sat=0.4, sodio=5),
    Alimento("lentejas", "Lentejas", 352, 24.6, 63.4, 1.1, 38, _EST, "leguminosas", seco_por_taza=70, fibra=10.7, hierro=6.5, calcio=35, sat=0.2, sodio=6),
    Alimento("soya", "Soya texturizada", 330, 50.0, 30.0, 1.0, 55, _EST, "leguminosas", fibra=18.0, hierro=9.2, calcio=240, sat=0.1, sodio=20),
    # ── origen animal ──
    Alimento("huevo", "Huevo", 143, 12.6, 0.7, 9.5, 47.4, _P_MAY, "origen_animal", "pieza", 50, "pieza", 50, piezas=("huevo", "huevos"), fibra=0, hierro=1.75, calcio=56, sat=3.1, sodio=142),
    Alimento("pollo", "Pollo (pierna y muslo)", 180, 18.5, 0, 11.5, 59.8, _P_MAY + " (entero, 65 % carne)", "origen_animal", fibra=0, hierro=0.9, calcio=11, sat=3.0, sodio=85),
    Alimento("pechuga", "Pechuga de pollo", 120, 22.5, 0, 2.6, 115, _EST, "origen_animal", fibra=0, hierro=0.4, calcio=5, sat=0.6, sodio=45),
    Alimento("res", "Carne molida de res", 250, 17.2, 0, 19.6, 100.55, _P_SEP, "origen_animal", fibra=0, hierro=2.0, calcio=18, sat=7.5, sodio=66),
    Alimento("cerdo", "Cerdo (pierna)", 143, 21.0, 0, 6.0, 67.5, _P_SEP, "origen_animal", fibra=0, hierro=0.9, calcio=6, sat=2.0, sodio=55),
    Alimento("atun", "Atún en agua", 116, 25.5, 0, 0.8, 140, _EST, "origen_animal", "lata", 100, "lata", 100, fibra=0, hierro=1.3, calcio=14, sat=0.2, sodio=250),
    Alimento("sardina", "Sardina en tomate", 186, 17.8, 1.5, 12.0, 56, _EST, "origen_animal", "g", 1, "lata", 425, fibra=0, hierro=2.3, calcio=240, sat=3.0, sodio=400),
    Alimento("leche", "Leche", 61, 3.2, 4.8, 3.3, 19.5, _P_SEP, "origen_animal", "ml", 1, "L", 1000, fibra=0, hierro=0.03, calcio=113, sat=1.9, sodio=44),
    Alimento("yogur", "Yogur natural", 61, 3.5, 4.7, 3.3, 42, _EST, "origen_animal", "taza", 250, "kg", 1000, fibra=0, hierro=0.05, calcio=121, sat=2.1, sodio=46),
    Alimento("queso_fresco", "Queso fresco", 299, 18.0, 3.0, 24.0, 130, _EST, "origen_animal", fibra=0, hierro=0.2, calcio=566, sat=13.0, sodio=750),
    Alimento("panela", "Queso panela", 260, 20.0, 2.0, 19.0, 150, _EST, "origen_animal", fibra=0, hierro=0.3, calcio=500, sat=11.0, sodio=600),
    # ── cereales y tuberculos ──
    Alimento("tortilla", "Tortilla de maíz", 218, 5.7, 44.6, 2.9, 27, _EST, "cereales", "pieza", 30, "kg", 1000, piezas=("tortilla", "tortillas"), fibra=6.3, hierro=1.2, calcio=100, sat=0.4, sodio=45),
    Alimento("arroz", "Arroz", 360, 6.6, 79.3, 0.6, 26, _EST, "cereales", seco_por_taza=55, fibra=1.3, hierro=0.8, calcio=9, sat=0.2, sodio=5),
    Alimento("avena", "Avena", 389, 16.9, 66.3, 6.9, 42, _EST, "cereales", "taza", 80, fibra=10.6, hierro=4.7, calcio=54, sat=1.2, sodio=2),
    Alimento("pasta", "Pasta para sopa", 371, 13.0, 74.7, 1.5, 35, _EST, "cereales", fibra=3.2, hierro=1.3, calcio=21, sat=0.3, sodio=6),
    Alimento("papa", "Papa", 77, 2.0, 17.5, 0.1, 43.28, _P_SEP, "cereales", "pieza", 150, piezas=("papa", "papas"), fibra=2.2, hierro=0.8, calcio=12, sat=0, sodio=6),
    # ── verduras y frutas ──
    Alimento("jitomate", "Jitomate", 18, 0.9, 3.9, 0.2, 19.1, _P_SEP, "verduras_frutas", "pieza", 120, piezas=("jitomate", "jitomates"), fibra=1.2, hierro=0.3, calcio=10, sat=0, sodio=5),
    Alimento("cebolla", "Cebolla", 40, 1.1, 9.3, 0.1, 38.37, _P_SEP, "verduras_frutas", "pieza", 150, piezas=("cebolla", "cebollas"), fibra=1.7, hierro=0.2, calcio=23, sat=0, sodio=4),
    Alimento("zanahoria", "Zanahoria", 41, 0.9, 9.6, 0.2, 12.14, _P_SEP, "verduras_frutas", "pieza", 70, piezas=("zanahoria", "zanahorias"), fibra=2.8, hierro=0.3, calcio=33, sat=0, sodio=69),
    Alimento("calabacita", "Calabacita", 17, 1.2, 3.1, 0.3, 28, _EST, "verduras_frutas", "pieza", 200, piezas=("calabacita", "calabacitas"), fibra=1.0, hierro=0.4, calcio=16, sat=0.1, sodio=8),
    Alimento("nopales", "Nopales", 16, 1.3, 3.3, 0.1, 25, _EST, "verduras_frutas", "pieza", 80, piezas=("nopal", "nopales"), fibra=2.2, hierro=0.6, calcio=164, sat=0, sodio=21),
    Alimento("espinaca", "Espinaca", 23, 2.9, 3.6, 0.4, 40, _EST, "verduras_frutas", fibra=2.2, hierro=2.7, calcio=99, sat=0.1, sodio=79),
    Alimento("chile", "Chile serrano o jalapeño", 32, 1.7, 6.7, 0.4, 35, _EST, "verduras_frutas", "pieza", 15, piezas=("chile", "chiles"), fibra=3.7, hierro=0.9, calcio=13, sat=0, sodio=10),
    Alimento("platano", "Plátano", 89, 1.1, 22.8, 0.3, 15.22, _P_SEP, "verduras_frutas", "pieza", 120, piezas=("plátano", "plátanos"), fibra=2.6, hierro=0.3, calcio=5, sat=0.1, sodio=1),
    Alimento("manzana", "Manzana", 52, 0.3, 13.8, 0.2, 37.4, _P_SEP, "verduras_frutas", "pieza", 150, piezas=("manzana", "manzanas"), fibra=2.4, hierro=0.1, calcio=6, sat=0, sodio=1),
    Alimento("naranja", "Naranja", 47, 0.9, 11.8, 0.1, 22, _EST, "verduras_frutas", "pieza", 130, piezas=("naranja", "naranjas"), fibra=2.4, hierro=0.1, calcio=40, sat=0, sodio=0),
    Alimento("limon", "Limón", 29, 1.1, 9.3, 0.3, 16.85, _P_SEP, "verduras_frutas", "pieza", 40, piezas=("limón", "limones"), fibra=2.8, hierro=0.6, calcio=26, sat=0, sodio=2),
    # ── grasas ──
    Alimento("aguacate", "Aguacate", 160, 2.0, 8.5, 14.7, 60, _EST, "grasas", "pieza", 140, piezas=("aguacate", "aguacates"), fibra=6.7, hierro=0.6, calcio=12, sat=2.1, sodio=7),
    Alimento("aceite", "Aceite vegetal", 884, 0, 0, 100, 31, _P_SEP, "grasas", "g", 1, "L", 920, fibra=0, hierro=0, calcio=0, sat=10.0, sodio=0),
    Alimento("cacahuate", "Cacahuate natural", 567, 25.8, 16.1, 49.2, 90, _EST, "grasas", fibra=8.5, hierro=4.6, calcio=92, sat=6.3, sodio=18),
    Alimento("crema_cacahuate", "Crema de cacahuate", 588, 25.0, 20.0, 50.0, 130, _EST, "grasas", fibra=6.0, hierro=1.9, calcio=45, sat=10.0, sodio=300),
    # ── agregados para el menu de 50 opciones y las dietas DASH / mediterranea ──
    Alimento("garbanzo", "Garbanzo", 364, 19.3, 61.0, 6.0, 40, _EST, "leguminosas", seco_por_taza=65,
             fibra=17.4, hierro=6.2, calcio=105, sat=0.6, sodio=24),
    Alimento("habas", "Habas secas", 341, 26.1, 58.0, 1.5, 45, _EST, "leguminosas", seco_por_taza=60,
             fibra=25.0, hierro=6.7, calcio=103, sat=0.3, sodio=13),
    Alimento("tofu", "Tofu firme", 144, 15.8, 2.8, 8.7, 120, _EST, "leguminosas",
             fibra=2.3, hierro=2.7, calcio=350, sat=1.3, sodio=14),
    Alimento("claras", "Claras de huevo", 52, 10.9, 0.7, 0.2, 70, _EST, "origen_animal",
             hierro=0.1, calcio=7, sat=0, sodio=166),
    Alimento("res_magra", "Bistec de res magro", 130, 22.0, 0, 4.5, 180, _EST, "origen_animal",
             hierro=2.4, calcio=12, sat=1.8, sodio=60),
    Alimento("tilapia", "Filete de tilapia", 96, 20.1, 0, 1.7, 110, _EST, "origen_animal",
             hierro=0.6, calcio=10, sat=0.6, sodio=52),
    Alimento("camaron", "Camarón", 85, 20.0, 0, 0.5, 220, _EST, "origen_animal",
             hierro=0.5, calcio=64, sat=0.1, sodio=120),
    Alimento("leche_light", "Leche descremada", 34, 3.4, 5.0, 0.1, 24, _EST, "origen_animal", "ml", 1, "L", 1000,
             calcio=122, sat=0.1, sodio=42),
    Alimento("yogur_griego", "Yogur griego natural", 73, 9.5, 4.0, 2.0, 90, _EST, "origen_animal", "taza", 250,
             calcio=110, sat=1.3, sodio=35),
    Alimento("requeson", "Requesón", 98, 11.0, 3.4, 4.3, 90, _EST, "origen_animal",
             hierro=0.1, calcio=83, sat=2.7, sodio=364),
    Alimento("arroz_integral", "Arroz integral", 362, 7.5, 76.0, 2.7, 40, _EST, "cereales", seco_por_taza=55,
             fibra=3.4, hierro=1.5, calcio=9, sat=0.5, sodio=4),
    Alimento("pasta_integral", "Pasta integral", 348, 14.6, 73.0, 1.4, 45, _EST, "cereales",
             fibra=9.0, hierro=3.6, calcio=40, sat=0.3, sodio=8),
    Alimento("pan_integral", "Pan integral", 247, 13.0, 41.0, 3.4, 75, _EST, "cereales", "pieza", 30,
             piezas=("rebanada de pan integral", "rebanadas de pan integral"),
             fibra=7.0, hierro=2.5, calcio=160, sat=0.7, sodio=450),
    Alimento("amaranto", "Amaranto inflado", 374, 13.6, 66.0, 7.0, 90, _EST, "cereales",
             fibra=6.7, hierro=7.6, calcio=159, sat=1.5, sodio=4),
    Alimento("camote", "Camote", 86, 1.6, 20.0, 0.1, 30, _EST, "cereales", "pieza", 200, piezas=("camote", "camotes"),
             fibra=3.0, hierro=0.6, calcio=30, sat=0, sodio=55),
    Alimento("elote", "Elote (granos)", 86, 3.3, 19.0, 1.4, 30, _EST, "cereales",
             fibra=2.7, hierro=0.5, calcio=2, sat=0.3, sodio=15),
    Alimento("brocoli", "Brócoli", 34, 2.8, 6.6, 0.4, 45, _EST, "verduras_frutas",
             fibra=2.6, hierro=0.7, calcio=47, sat=0, sodio=33),
    Alimento("champinon", "Champiñones", 22, 3.1, 3.3, 0.3, 80, _EST, "verduras_frutas",
             fibra=1.0, hierro=0.5, calcio=3, sat=0, sodio=5),
    Alimento("chayote", "Chayote", 19, 0.8, 4.5, 0.1, 20, _EST, "verduras_frutas", "pieza", 250,
             piezas=("chayote", "chayotes"), fibra=1.7, hierro=0.3, calcio=17, sat=0, sodio=2),
    Alimento("ejotes", "Ejotes", 31, 1.8, 7.0, 0.2, 40, _EST, "verduras_frutas",
             fibra=2.7, hierro=1.0, calcio=37, sat=0, sodio=6),
    Alimento("pepino", "Pepino", 15, 0.7, 3.6, 0.1, 20, _EST, "verduras_frutas", "pieza", 250,
             piezas=("pepino", "pepinos"), fibra=0.5, hierro=0.3, calcio=16, sat=0, sodio=2),
    Alimento("lechuga", "Lechuga", 15, 1.4, 2.9, 0.2, 25, _EST, "verduras_frutas",
             fibra=1.3, hierro=0.9, calcio=36, sat=0, sodio=28),
    Alimento("pimiento", "Pimiento morrón", 26, 1.0, 6.0, 0.3, 60, _EST, "verduras_frutas", "pieza", 150,
             piezas=("pimiento", "pimientos"), fibra=2.1, hierro=0.4, calcio=7, sat=0, sodio=4),
    Alimento("tomate_verde", "Tomate verde", 32, 1.0, 5.8, 1.0, 25, _EST, "verduras_frutas",
             fibra=1.9, hierro=0.6, calcio=7, sat=0.1, sodio=1),
    Alimento("fresa", "Fresa", 32, 0.7, 7.7, 0.3, 60, _EST, "verduras_frutas",
             fibra=2.0, hierro=0.4, calcio=16, sat=0, sodio=1),
    Alimento("papaya", "Papaya", 43, 0.5, 11.0, 0.3, 25, _EST, "verduras_frutas",
             fibra=1.7, hierro=0.3, calcio=20, sat=0.1, sodio=8),
    Alimento("melon", "Melón", 34, 0.8, 8.2, 0.2, 25, _EST, "verduras_frutas",
             fibra=0.9, hierro=0.2, calcio=9, sat=0, sodio=16),
    Alimento("pina", "Piña", 50, 0.5, 13.0, 0.1, 25, _EST, "verduras_frutas",
             fibra=1.4, hierro=0.3, calcio=13, sat=0, sodio=1),
    Alimento("mango", "Mango", 60, 0.8, 15.0, 0.4, 35, _EST, "verduras_frutas", "pieza", 200,
             piezas=("mango", "mangos"), fibra=1.6, hierro=0.2, calcio=11, sat=0.1, sodio=1),
    Alimento("guayaba", "Guayaba", 68, 2.6, 14.3, 1.0, 35, _EST, "verduras_frutas", "pieza", 60,
             piezas=("guayaba", "guayabas"), fibra=5.4, hierro=0.3, calcio=18, sat=0.3, sodio=2),
    Alimento("nuez", "Nuez", 654, 15.0, 14.0, 65.0, 250, _EST, "grasas",
             fibra=6.7, hierro=2.9, calcio=98, sat=6.1, sodio=2),
    Alimento("almendra", "Almendra", 579, 21.0, 22.0, 50.0, 230, _EST, "grasas",
             fibra=12.5, hierro=3.7, calcio=269, sat=3.8, sodio=1),
    Alimento("chia", "Chía", 486, 17.0, 42.0, 31.0, 120, _EST, "grasas",
             fibra=34.0, hierro=7.7, calcio=631, sat=3.3, sodio=16),
    Alimento("aceite_oliva", "Aceite de oliva", 884, 0, 0, 100, 217, _EST, "grasas", "g", 1, "L", 920,
             sat=14.0, sodio=2),
    # ── suplemento (solo si hace falta: es lo mas caro por gramo de proteina) ──
    Alimento("proteina_polvo", "Proteína en polvo", 380, 75.0, 8.0, 5.0, 600, _EST, "origen_animal", "scoop", 32, fibra=0, hierro=1.0, calcio=400, sat=2.5, sodio=200),
]}

# lo que se puede excluir de golpe desde el dashboard
GRUPOS_EXCLUIBLES = {
    "carnes": ["pollo", "pechuga", "res", "res_magra", "cerdo"],
    "pescado": ["atun", "sardina", "tilapia", "camaron"],
    "lacteos": ["leche", "leche_light", "yogur", "yogur_griego", "queso_fresco", "panela", "requeson"],
    "huevo": ["huevo", "claras"],
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

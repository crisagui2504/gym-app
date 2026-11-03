"""Productos REALES para la lista del super: que se compra, en que tienda y a cuanto.

Cada alimento del menu (alimentos_mx.py) tiene sus presentaciones de verdad:
"Frijol Negro Chedraui 900 g", "Huevo blanco Aurrera 30 pzas", "Pechuga sin
hueso (charola, por kg)"... La lista redondea a paquetes enteros, elige la
opcion mas barata de las tiendas que usas y dice que te sobra (lo de despensa
rinde para otras semanas; lo fresco no).

De donde salen los precios (2 de noviembre de 2026, salvo donde se dice):
  - Chedraui: catalogo publico de chedraui.com.mx.
  - Walmart y Sam's Club: paginas de walmart.com.mx y sams.com.mx.
  - Tiendas 3B: no publica precios en linea; los que hay son del folleto
    (agosto 2026) o de notas de prensa. El resto aparece como "precio en
    tienda" para que sepas que marca buscar.
  - Mercado o tianguis: ESTIMADO = precio de mayoreo de la Central de Abasto
    de la CDMX (SNIIM, 29-oct-2026) + 30 % de margen de un puesto.
  - Tortilleria: promedio nacional del SNIIM (abril 2026).
Los precios cambian por ciudad y por semana: son para planear.

`g` es el contenido del paquete TAL COMO SE COMPRA y `rinde` la parte que se
come (sin hueso, cascara o liquido): las recetas cuentan lo que se come.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

TIENDAS: dict[str, str] = {
    "mercado": "Mercado o tianguis",
    "tortilleria": "Tortillería",
    "3b": "Tiendas 3B",
    "walmart": "Walmart",
    "chedraui": "Chedraui",
    "sams": "Sam's Club",
}
ORDEN_TIENDAS = list(TIENDAS)

CH = "chedraui.com.mx, 2-nov-2026"
WM = "walmart.com.mx, 2-nov-2026"
SM = "sams.com.mx, 2-nov-2026"
B3 = "folleto de Tiendas 3B, ago-2026"
B3_PRENSA = "Criterio Hidalgo (precios en 3B), ene-2026"
B3_SIN = "3B no publica precios en línea"
MER = "estimado: Central de Abasto CDMX (SNIIM, 29-oct-2026) + 30 %"
TOR = "SNIIM: promedio nacional de tortillería, abr-2026"
MARGEN_MERCADO = 1.30


@dataclass(frozen=True)
class Producto:
    tienda: str
    nombre: str
    g: float                 # contenido como se compra (g o ml); a granel, 1000 (el precio es por kg)
    precio: float | None     # MXN del paquete (a granel: por kg); None = sin precio en linea
    granel: bool = False     # se pide lo que necesitas, en pasos de `paso` g
    paso: float = 250.0
    rinde: float = 1.0       # parte que se come
    fuente: str = ""


def _pq(tienda: str, nombre: str, g: float, precio: float | None, rinde: float = 1.0,
        fuente: str | None = None) -> Producto:
    """Un paquete (bolsa, lata, caja, pieza...)."""
    fuentes = {"chedraui": CH, "walmart": WM, "sams": SM, "3b": B3 if precio else B3_SIN}
    return Producto(tienda, nombre, g, precio, False, 0.0, rinde, fuente or fuentes.get(tienda, ""))


def _kg(tienda: str, nombre: str, precio_kg: float, paso: float = 250, rinde: float = 1.0,
        fuente: str | None = None) -> Producto:
    """A granel o por kilo (carniceria del super, frutas y verduras)."""
    fuentes = {"chedraui": CH, "walmart": WM, "sams": SM, "3b": B3_PRENSA}
    return Producto(tienda, nombre, 1000, precio_kg, True, paso, rinde, fuente or fuentes.get(tienda, ""))


def _mer(nombre: str, mayoreo_kg: float, paso: float = 250, rinde: float = 1.0) -> Producto:
    """Mercado: mayoreo de la Central de Abasto + el margen del puesto."""
    return Producto("mercado", nombre, 1000, round(mayoreo_kg * MARGEN_MERCADO, 1), True, paso, rinde, MER)


def _pza_mer(nombre: str, g_pieza: float, mayoreo_pieza: float, rinde: float = 1.0) -> Producto:
    """Mercado, por pieza (lechuga, elote, nopal, pina)."""
    return Producto("mercado", nombre, g_pieza, round(mayoreo_pieza * MARGEN_MERCADO, 1), False, 0.0, rinde, MER)


PRODUCTOS: dict[str, list[Producto]] = {
    # ── leguminosas ──
    "frijol": [
        _pq("sams", "Frijol negro Member's Mark 3 kg", 3000, 74.67),
        _pq("chedraui", "Frijol negro Chedraui 2.2 kg", 2200, 46.5),
        _pq("chedraui", "Frijol negro Chedraui 900 g", 900, 23.0),
        _pq("3b", "Frijol negro Santini 900 g", 900, None),
    ],
    "lentejas": [
        _pq("walmart", "Lentejas Great Value 500 g", 500, 16.0),
        _pq("walmart", "Lentejas Schettino 500 g", 500, 16.0),
        _pq("walmart", "Lentejas La Merced 500 g", 500, 17.0),
    ],
    "garbanzo": [
        _pq("walmart", "Garbanzo Great Value 500 g", 500, 20.0),
        _pq("chedraui", "Garbanzo Schettino 500 g", 500, 21.0),
    ],
    "habas": [
        _pq("walmart", "Haba Great Value 500 g", 500, 65.0),
        _pq("chedraui", "Haba Verde Valle 500 g", 500, 79.0),
    ],
    "soya": [_pq("chedraui", "Soya texturizada Ufasoy 330 g", 330, 19.9)],
    "tofu": [_pq("chedraui", "Tofu firme Mori-Nu 307 g", 307, 60.0)],
    # ── origen animal ──
    "huevo": [
        _pq("walmart", "Huevo blanco Aurrera 30 pzas", 1500, 57.0),
        _pq("walmart", "Huevo blanco El Calvario 30 pzas", 1500, 65.0),
        _pq("chedraui", "Huevo blanco El Calvario 30 pzas", 1500, 65.0),
        _pq("walmart", "Huevo blanco Aurrera 18 pzas", 900, 38.0),
        _pq("chedraui", "Huevo blanco Bachoco 18 pzas", 900, 41.0),
        _pq("sams", "Huevo blanco San Juan 90 pzas", 4500, 194.37),
        _pq("3b", "Huevo blanco Docenera Cresta Roja 12 pzas", 600, None),
    ],
    "claras": [
        _pq("walmart", "Claras de huevo San Juan 1 kg", 1000, 47.0, fuente="walmart.com.mx (listado)"),
        _pq("sams", "Claras de huevo San Juan 6 × 500 g", 3000, 140.15),
    ],
    "pollo": [
        _kg("walmart", "Pierna y muslo de pollo (charola ~800 g, por kg)", 32.0, 800, 0.7),
        _kg("chedraui", "Pierna y muslo de pollo Crío (por kg)", 32.0, 400, 0.7),
        _pq("sams", "Pierna de pollo (paquete ~2 kg)", 2000, 155.27, 0.7),
        _kg("chedraui", "Pierna y muslo sin piel (por kg)", 112.0, 250, 0.8),
    ],
    "pechuga": [
        _kg("chedraui", "Pechuga de pollo sin hueso congelada (por kg)", 120.0, 500),
        _kg("walmart", "Pechuga con hueso corte americano (charola ~800 g, por kg)", 89.0, 800, 0.78),
        _kg("walmart", "Pechuga de pollo sin hueso (charola 600-700 g, por kg)", 172.0, 650),
        _pq("sams", "Pechuga de pollo sin hueso (paquete ~2.1 kg)", 2100, 348.62),
        _pq("sams", "Pechuga de pollo Just Bare sin hueso 1.5 kg", 1500, 244.49),
    ],
    "pollo_rostizado": [
        _pq("chedraui", "Pollo rostizado (1 pieza, ≈ 650 g de carne)", 1100, 99.9, 0.6),
        _pq("sams", "Pollo rostizado Member's Mark (1 pieza, ≈ 780 g de carne)", 1300, 120.7, 0.6),
    ],
    "res": [
        _kg("chedraui", "Carne molida de res (por kg)", 136.0, 250),
        _pq("chedraui", "Carne molida SuKarne 80/20 400 g", 400, 76.0),
        _pq("sams", "Carne molida de res 90/10 (paquete ~1.75 kg)", 1750, 325.30),
    ],
    "res_magra": [
        _kg("chedraui", "Bistec de res del 7 (por kg)", 159.0, 250),
        _kg("3b", "Bistec de res (por kg)", 180.0, 250),
        _kg("chedraui", "Bistec de res pulpa blanca (por kg)", 225.0, 250),
        _pq("sams", "Bistec de res Member's Mark (paquete ~1.15 kg)", 1150, 396.31),
    ],
    "cerdo": [
        _kg("chedraui", "Chuleta de cerdo natural (por kg)", 97.0, 250, 0.85),
        _kg("chedraui", "Pulpa de cerdo (por kg)", 108.0, 250),
        _pq("sams", "Carne molida de cerdo (paquete ~1.75 kg)", 1750, 182.08),
    ],
    "atun": [
        _pq("chedraui", "Atún en agua Ancla Jumbo 295 g", 295, 28.0, 0.7),
        _pq("sams", "Atún en agua Tuny 8 latas de 140 g", 1120, 148.34, 0.71),
        _pq("chedraui", "Atún en agua Tuny 130 g", 130, 23.0, 0.71),
        _pq("chedraui", "Atún Herdez en agua 130 g", 130, 24.0, 0.71),
        _pq("sams", "Atún en agua Dolores 8 latas de 140 g", 1120, 158.56, 0.71),
        _pq("3b", "Atún en agua Tunrico 140 g", 140, None, 0.71),
    ],
    "sardina": [
        _pq("chedraui", "Sardinas Guaymex en tomate 425 g", 425, 48.0),
        _pq("chedraui", "Sardinas Dolores en tomate 425 g", 425, 48.0),
        _pq("sams", "Sardinas Guaymex en tomate 6 latas de 425 g", 2550, 251.65),
        _pq("3b", "Sardinas en tomate Nautilus", 425, None),
    ],
    "tilapia": [
        _kg("chedraui", "Filete de tilapia (por kg)", 103.0, 250),
        _pq("chedraui", "Filete de tilapia Neptuno 500 g", 500, 107.0),
        _pq("chedraui", "Filete de tilapia Rivera 1 kg", 1000, 221.0),
    ],
    "camaron": [
        _kg("chedraui", "Camarón coctel (pulpa, por kg)", 199.0, 250),
        _kg("chedraui", "Camarón pacotilla Selecto (por kg)", 339.15, 250),
    ],
    "jamon": [
        _pq("3b", "Jamón de pierna Sparta 200 g", 200, 30.0),
        _pq("chedraui", "Jamón de pavo Sabori Virginia 400 g", 400, 62.5),
        _pq("chedraui", "Jamón de pavo FUD Virginia 450 g", 450, 75.0),
        _pq("sams", "Pechuga de pavo FUD Virginia 1 kg", 1000, 252.68),
    ],
    "leche": [
        _pq("walmart", "Leche Great Value entera 1.5 L", 1500, 31.0),
        _pq("sams", "Leche entera Member's Mark 3.78 L", 3780, 89.0),
        _pq("chedraui", "Leche Lala entera UHT 1 L", 1000, 30.0),
        _pq("walmart", "Leche Lala entera UHT 6 × 1 L", 6000, 160.0),
        _pq("sams", "Leche entera Member's Mark 12 × 1 L", 12000, 298.71),
        _pq("3b", "Leche entera UHT Vaca Blanca 1 L", 1000, None),
    ],
    "leche_light": [
        _pq("walmart", "Leche Great Value descremada light 1 L", 1000, 24.0),
        _pq("chedraui", "Leche Santa Clara light 1 L", 1000, 33.0),
    ],
    "yogur": [
        _pq("chedraui", "Yoghurt Yoplait batido natural 1 kg", 1000, 47.0),
        _pq("sams", "Yogurt Yoplait batido natural + fresa 2 × 1 kg", 2000, 102.3),
        _pq("3b", "Yogurt Vaca Blanca 1 kg", 1000, None),
    ],
    "yogur_griego": [
        _pq("sams", "Yogurt griego Yoplait natural 2 × 1 kg", 2000, 168.8),
        _pq("chedraui", "Yogurt griego Danone natural sin azúcar 900 g", 900, 83.5),
        _pq("chedraui", "Yogurt griego Lala natural sin azúcar 900 g", 900, 87.5),
        _pq("chedraui", "Yogurt griego Oikos natural 900 g", 900, 90.0),
        _pq("sams", "Yogurt griego Oikos Selecto natural 2 × 900 g", 1800, 186.18),
    ],
    "queso_fresco": [
        _pq("chedraui", "Queso fresco Zwan 360 g", 360, 60.5),
        _kg("chedraui", "Queso fresco rallado El Ciervo (por kg)", 142.0, 250),
    ],
    "panela": [
        _pq("chedraui", "Queso panela Lala 400 g", 400, 60.8),
        _pq("chedraui", "Queso panela Aguascalientes 400 g", 400, 94.0),
        _pq("chedraui", "Queso panela Lala 1 kg", 1000, 192.0),
    ],
    "queso_oaxaca": [
        _pq("3b", "Queso Oaxaca Vaca Blanca 400 g", 400, 69.0),
        _pq("sams", "Queso Oaxaca Canbe 1 kg", 1000, 131.96),
        _pq("chedraui", "Queso Oaxaca La Villita 400 g", 400, 75.0),
        _pq("chedraui", "Queso Oaxaca Esmeralda 400 g", 400, 104.0),
    ],
    "requeson": [
        _pq("chedraui", "Requesón Santa Inés 400 g", 400, 75.5),
        _pq("chedraui", "Requesón Bionda 500 g", 500, 91.0),
    ],
    "cottage": [
        _pq("chedraui", "Queso cottage Lala 350 g", 350, 55.2),
        _pq("chedraui", "Queso cottage Santa Clara 500 g", 500, 77.5),
    ],
    "proteina_polvo": [],          # sin dato confiable: se usa el estimado de alimentos_mx
    # ── cereales y tuberculos ──
    "tortilla": [
        _kg("tortilleria", "Tortillas de maíz (por kg)", 24.18, 250, fuente=TOR),
        _kg("chedraui", "Tortilla de maíz de la tortillería de Chedraui (por kg)", 13.4, 500),
        _pq("chedraui", "Tortilla de maíz Guerreras 800 g", 800, 33.5),
    ],
    "tortilla_harina": [
        _pq("3b", "Tortillas de harina Tiara 552 g", 552, 24.0),
        _pq("chedraui", "Tortillas de harina Tía Rosa 30 pzas (765 g)", 765, 55.0),
        _kg("chedraui", "Tortilla de harina de la tortillería (por kg)", 29.0, 500),
    ],
    "arroz": [
        _pq("walmart", "Arroz Aurrera extra 900 g", 900, 15.0),
        _pq("walmart", "Arroz Great Value súper extra 900 g", 900, 18.0),
        _pq("sams", "Arroz Member's Mark grano largo 3 kg", 3000, 54.22),
        _pq("chedraui", "Arroz Schettino extra 900 g", 900, 23.0),
        _pq("3b", "Arroz súper extra Camposanto", 900, None),
    ],
    "arroz_integral": [
        _pq("chedraui", "Arroz integral La Merced 750 g", 750, 26.5),
        _pq("chedraui", "Arroz integral SOS 1 kg", 1000, 33.0),
    ],
    "avena": [
        _pq("chedraui", "Avena en hojuela Chedraui 1 kg", 1000, 25.0),
        _pq("chedraui", "Avena Granvita tradicional 425 g", 425, 32.0),
        _pq("3b", "Avena natural Quick Total", 400, None),
    ],
    "pasta": [
        _pq("chedraui", "Pasta para sopa La Moderna 220 g (fideo, codo…)", 220, 12.5),
        _pq("chedraui", "Spaghetti La Moderna 220 g", 220, 12.0),
        _pq("sams", "Fideo Member's Mark 3 kg", 3000, 51.15),
        _pq("3b", "Pasta Fontina 200 g (fideo, codo, spaghetti)", 200, None),
    ],
    "pasta_integral": [
        _pq("chedraui", "Spaghetti La Moderna integral 200 g", 200, 12.0),
        _pq("chedraui", "Espagueti integral Nutrioli 200 g", 200, 15.0),
    ],
    "papa": [
        _mer("Papa blanca (a granel)", 14.0, 500, 0.85),
        _kg("chedraui", "Papa blanca (por kg)", 48.9, 500, 0.85),
    ],
    "camote": [
        _mer("Camote (a granel)", 14.0, 500, 0.8),
        _kg("chedraui", "Camote amarillo (por kg)", 44.5, 500, 0.8),
    ],
    "elote": [
        _pza_mer("Elote (pieza, ≈ 150 g de granos)", 270, 7.5, 0.56),
        _pq("chedraui", "Elote (pieza, ≈ 150 g de granos)", 270, 12.5, 0.56),
        _pq("chedraui", "Granos de elote Herdez 400 g (lata)", 400, 18.5, 0.62),
    ],
    "pan_integral": [
        _pq("chedraui", "Pan de caja integral Selecto 680 g", 680, 48.0),
        _pq("chedraui", "Pan Bimbo integral 620 g", 620, 55.0),
        _pq("3b", "Pan integral Molino Blanco", 600, None),
    ],
    "bolillo": [_pq("chedraui", "Bolillo (pieza)", 65, 2.6, fuente=CH)],
    "tostada": [
        _pq("chedraui", "Tostadas horneadas Del Barrio 500 g", 500, 49.0),
        _pq("chedraui", "Tostadas horneadas Mission 240 g", 240, 37.0),
        _pq("3b", "Tostadas de maíz horneadas Trita", 300, None),
    ],
    "galletas_saladas": [
        _pq("chedraui", "Galletas Saladitas Gamesa 20 paquetitos (≈ 340 g)", 340, 41.0),
        _pq("chedraui", "Galletas Habaneras integrales 117 g", 117, 20.0),
        _pq("3b", "Galletas cracker Milena", 200, None),
    ],
    "galletas_maria": [
        _pq("chedraui", "Galletas Marías Chedraui 850 g", 850, 55.0),
        _pq("chedraui", "Galletas Marías Gamesa 170 g", 170, 25.0),
    ],
    "palomitas": [
        _pq("walmart", "Maíz palomero Schettino 500 g", 500, 13.5, fuente="walmart.com.mx (listado)"),
        _pq("sams", "Maíz palomero Schettino 5 × 500 g", 2500, 57.29),
    ],
    "granola": [
        _pq("chedraui", "Granola Tita Nene tradicional 425 g", 425, 36.5),
        _pq("chedraui", "Granola Granvita 0 % azúcar 600 g", 600, 88.0),
        _pq("3b", "Granola Quick Avena Total", 400, None),
    ],
    "cereal": [
        _pq("chedraui", "Corn Flakes Nestlé bolsa 630 g", 630, 57.0),
        _pq("chedraui", "Corn Flakes Kellogg's 540 g", 540, 68.0),
        _pq("3b", "Cereal corn flakes EarthFlakes", 500, None),
    ],
    "pan_molido": [
        _pq("chedraui", "Pan molido Bimbo 400 g", 400, 46.0),
        _kg("chedraui", "Pan molido de la panadería (por kg)", 54.9, 250),
    ],
    "amaranto": [
        _pq("walmart", "Amaranto Dulcerel natural 250 g", 250, 31.0),
        _pq("chedraui", "Amaranto Olype 400 g", 400, 71.0),
    ],
    # ── verduras y frutas ──
    "jitomate": [
        _mer("Jitomate saladet (a granel)", 32.0, 250, 0.95),
        _kg("chedraui", "Tomate saladet (por kg)", 39.9, 250, 0.95),
    ],
    "cebolla": [
        _mer("Cebolla blanca (a granel)", 19.0, 250, 0.9),
        _kg("chedraui", "Cebolla blanca (por kg)", 61.9, 250, 0.9),
    ],
    "zanahoria": [
        _mer("Zanahoria (a granel)", 7.92, 250, 0.89),
        _kg("chedraui", "Zanahoria (por kg)", 14.9, 250, 0.89),
    ],
    "calabacita": [
        _mer("Calabacita italiana (a granel)", 12.8, 250, 0.95),
        _kg("chedraui", "Calabaza italiana (por kg)", 39.8, 250, 0.95),
    ],
    "chayote": [
        _mer("Chayote sin espinas (a granel)", 7.22, 300, 0.85),
        _kg("chedraui", "Chayote sin espinas (por kg)", 19.9, 300, 0.85),
    ],
    "nopales": [
        _pza_mer("Nopal limpio (pieza)", 85, 1.9, 0.95),
        _kg("chedraui", "Nopal (por kg)", 43.9, 250, 0.95),
    ],
    "espinaca": [
        _mer("Espinaca (manojo, a granel)", 42.0, 300, 0.72),
        _pq("chedraui", "Espinaca La Huerta 500 g", 500, 44.5),
    ],
    "chile": [
        _mer("Chile jalapeño o serrano (a granel)", 15.0, 100, 0.9),
        _kg("chedraui", "Chile jalapeño (por kg)", 20.0, 100, 0.9),
    ],
    "poblano": [
        _mer("Chile poblano (a granel)", 42.0, 250, 0.8),
        _kg("chedraui", "Chile poblano (por kg)", 61.0, 250, 0.8),
    ],
    "pimiento": [
        _mer("Pimiento morrón (a granel)", 41.67, 250, 0.82),
        _kg("chedraui", "Pimiento verde (por kg)", 75.0, 250, 0.82),
    ],
    "tomate_verde": [
        _mer("Tomate verde (a granel)", 28.0, 250, 0.9),
        _kg("chedraui", "Tomate verde (por kg)", 46.0, 250, 0.9),
    ],
    "brocoli": [
        _mer("Brócoli (a granel)", 14.0, 500, 0.61),
        _kg("chedraui", "Brócoli (por kg)", 39.9, 500, 0.61),
    ],
    "ejotes": [
        _mer("Ejote (a granel)", 25.0, 250, 0.88),
        _kg("chedraui", "Ejote (por kg)", 49.9, 250, 0.88),
    ],
    "champinon": [
        _pq("chedraui", "Champiñón Monteblanco 225 g", 225, 34.9, 0.97),
        _kg("chedraui", "Champiñón (por kg)", 109.9, 250, 0.97),
    ],
    "lechuga": [
        _pza_mer("Lechuga romana (pieza)", 450, 7.5, 0.85),
        _pq("chedraui", "Lechuga romana (pieza)", 450, 23.9, 0.85),
    ],
    "pepino": [_mer("Pepino (a granel)", 17.27, 250, 0.9)],
    "aguacate": [
        _mer("Aguacate Hass (a granel)", 33.33, 200, 0.74),
        _kg("chedraui", "Aguacate Hass (por kg)", 41.9, 200, 0.74),
    ],
    "limon": [
        _mer("Limón sin semilla (a granel)", 10.0, 250, 0.7),
        _kg("chedraui", "Limón sin semilla (por kg)", 29.9, 250, 0.7),
    ],
    "platano": [
        _mer("Plátano Chiapas (a granel)", 12.78, 500, 0.64),
        _kg("chedraui", "Plátano Chiapas (por kg)", 18.0, 500, 0.64),
    ],
    "manzana": [
        _mer("Manzana roja (a granel)", 35.79, 500, 0.9),
        _kg("chedraui", "Manzana Fuji (por kg)", 59.9, 500, 0.9),
    ],
    "naranja": [
        _mer("Naranja Valencia (a granel)", 11.8, 1000, 0.73),
        _pq("chedraui", "Naranja en arpilla 5 kg", 5000, 198.9, 0.73),
    ],
    "mandarina": [
        _mer("Mandarina (a granel)", 21.0, 500, 0.74),
        _kg("chedraui", "Mandarina (por kg)", 75.9, 500, 0.74),
    ],
    "toronja": [
        _mer("Toronja (a granel)", 13.0, 500, 0.5),
        _kg("chedraui", "Toronja (por kg)", 24.9, 500, 0.5),
    ],
    "papaya": [
        _mer("Papaya maradol (a granel)", 26.0, 1000, 0.67),
        _kg("chedraui", "Papaya maradol (por kg)", 39.9, 1000, 0.67),
    ],
    "melon": [
        _mer("Melón chino (a granel)", 23.68, 1500, 0.51),
        _kg("chedraui", "Melón chino (por kg)", 29.9, 1500, 0.51),
    ],
    "sandia": [
        _mer("Sandía (a granel, por rebanada o pieza)", 15.0, 1000, 0.52),
        _kg("chedraui", "Sandía sin semilla (por kg)", 23.9, 1000, 0.52),
    ],
    "pina": [
        _pza_mer("Piña mediana (pieza, ≈ 1.6 kg)", 1600, 30.0, 0.51),
        _kg("chedraui", "Piña gota miel (por kg)", 29.9, 1600, 0.51),
    ],
    "mango": [_mer("Mango ataulfo (a granel)", 25.0, 500, 0.69)],
    "guayaba": [_mer("Guayaba (a granel)", 35.0, 250, 0.9)],
    "fresa": [
        _mer("Fresa (a granel)", 56.25, 250, 0.94),
        _pq("chedraui", "Fresa domo 454 g", 454, 83.9, 0.94),
    ],
    "jicama": [
        _mer("Jícama (a granel)", 18.0, 500, 0.9),
        _kg("chedraui", "Jícama (por kg)", 35.9, 500, 0.9),
    ],
    "pera": [
        _mer("Pera d'Anjou (a granel)", 40.0, 500, 0.9),
        _kg("chedraui", "Pera mantequilla (por kg)", 52.0, 500, 0.9),
    ],
    "uva": [
        _mer("Uva globo (a granel)", 37.5, 500, 0.96),
        _kg("chedraui", "Uva roja sin semilla (por kg)", 89.0, 500, 0.96),
    ],
    # ── grasas, semillas y sazon ──
    "aceite": [
        _pq("chedraui", "Aceite vegetal Ave 850 ml", 850, 32.0),
        _pq("chedraui", "Aceite vegetal 123 1 L", 1000, 40.0),
        _pq("3b", "Aceite de canola Radora", 900, None),
    ],
    "aceite_oliva": [
        _pq("chedraui", "Aceite de oliva Carbonell 750 ml", 750, 161.5),
        _pq("chedraui", "Aceite de oliva Carbonell 500 ml", 500, 117.0),
    ],
    "cacahuate": [
        _pq("chedraui", "Cacahuate tostado Chedraui 454 g", 454, 57.5),
        _mer("Cacahuate con cáscara (a granel)", 48.0, 250, 0.7),
        _pq("3b", "Cacahuate salado Konichiwa", 200, None),
    ],
    "crema_cacahuate": [
        _pq("chedraui", "Crema de cacahuate Selecto 454 g", 454, 69.0),
        _pq("chedraui", "Crema de cacahuate Aladino 1.1 kg", 1100, 159.0),
        _pq("3b", "Crema de cacahuate Dulsa", 400, None),
    ],
    "nuez": [
        _pq("chedraui", "Nuez de Castilla con cáscara, malla 500 g", 500, 115.0, 0.45),
        _kg("chedraui", "Nuez en mitades (por kg)", 520.0, 100),
    ],
    "almendra": [
        _pq("chedraui", "Almendras naturales First Street 907 g", 907, 344.0),
        _kg("chedraui", "Almendra natural (por kg)", 389.0, 100),
    ],
    "chia": [
        _pq("chedraui", "Chía De la Reyna 100 g", 100, 19.9),
        _pq("sams", "Chía orgánica Member's Mark 1.5 kg", 1500, 224.03),
    ],
    "pepitas": [
        _pq("chedraui", "Pepita de calabaza Okko 200 g", 200, 75.0),
        _pq("walmart", "Pepita de calabaza Okko 200 g", 200, 77.0),
    ],
    "mole": [
        _pq("chedraui", "Mole La Costeña 235 g", 235, 55.0),
        _pq("chedraui", "Mole en pasta Xiqueño 500 g", 500, 81.0),
    ],
}

# Semanas que dura lo que te sobra (cerrado o en el refri / congelador). Lo que
# dura una semana o menos se cuenta como merma; lo demas rinde para las que siguen.
DURA_SEMANAS: dict[str, float] = {
    **{a: 26 for a in ("frijol", "lentejas", "garbanzo", "habas", "soya", "arroz", "arroz_integral", "avena", "pasta",
                       "pasta_integral", "aceite", "aceite_oliva", "chia", "palomitas", "atun", "sardina",
                       "proteina_polvo")},
    **{a: 12 for a in ("pollo", "pechuga", "res", "res_magra", "cerdo", "tilapia", "camaron",   # congelando en porciones
                       "amaranto", "crema_cacahuate", "almendra", "pan_molido", "mole")},
    **{a: 8 for a in ("leche", "leche_light", "cacahuate", "nuez", "pepitas", "galletas_maria")},
    **{a: 6 for a in ("granola", "cereal", "tostada")},
    **{a: 4 for a in ("huevo", "galletas_saladas")},
    **{a: 3 for a in ("yogur_griego", "papa", "cebolla", "camote", "manzana", "tortilla_harina")},
    **{a: 2 for a in ("yogur", "panela", "queso_oaxaca", "claras", "zanahoria", "limon", "naranja", "jicama", "toronja",
                      "tofu")},
    **{a: 1.5 for a in ("queso_fresco", "cottage", "jamon", "pan_integral", "chayote")},
}
# lo demas (verdura y fruta fresca, tortilla, bolillo, requeson, pollo rostizado): 1 semana o menos


def dura(aid: str) -> float:
    return DURA_SEMANAS.get(aid, 1.0)


def con_precio(aid: str, tiendas: set[str] | None = None) -> list[Producto]:
    return [p for p in PRODUCTOS.get(aid, []) if p.precio and (tiendas is None or p.tienda in tiendas)]


def precio_kg(p: Producto) -> float:
    """$ por kg de lo que se come."""
    return p.precio / (p.g / 1000) / p.rinde


def referencia(aid: str) -> Producto | None:
    """El producto con el precio mas bajo por kg de lo que se come (para planear el menu)."""
    ps = con_precio(aid)
    return min(ps, key=precio_kg) if ps else None


def compra(p: Producto, g_comer: float, g_semana: float, aid: str) -> dict:
    """Cuanto comprar de `p` para comer `g_comer` g: paquetes enteros (o kilos en pasos de
    `paso`), lo que pagas, lo que te sobra y lo que de eso rinde para las semanas que siguen."""
    g_bruto = g_comer / p.rinde
    if p.granel:
        g_compra = max(p.paso, math.ceil(g_bruto / p.paso - 0.02) * p.paso)
        n, pagas = 0, p.precio * g_compra / 1000
    else:
        n = max(1, math.ceil(g_bruto / p.g - 0.02))
        g_compra, pagas = n * p.g, n * p.precio
    sobra = max(0.0, g_compra * p.rinde - g_comer)            # en gramos de lo que se come
    usable = min(sobra, g_semana * max(0.0, dura(aid) - 1))   # lo que alcanzas a comer antes de que se eche a perder
    valor = usable / 1000 * precio_kg(p)
    return {"producto": p, "n": n, "g_compra": g_compra, "pagas": pagas, "sobra": sobra, "merma": sobra - usable,
            "queda": valor, "efectivo": pagas - valor + 0.02 * pagas}


def elegir(aid: str, g_comer: float, g_semana: float | None = None,
           tiendas: set[str] | None = None) -> list[dict]:
    """Opciones de compra de mas conveniente a menos (una por producto con precio)."""
    g_semana = g_comer if g_semana is None else g_semana
    ops = [compra(p, g_comer, g_semana, aid) for p in con_precio(aid, tiendas)]
    return sorted(ops, key=lambda o: (o["efectivo"], o["pagas"]))


def ficha(aid: str) -> list[dict]:
    """Los productos del alimento para la app (que rehace la lista si cambias comidas o tiendas)."""
    return [{"t": p.tienda, "n": p.nombre, "g": p.g, "p": p.precio, "gr": p.granel, "paso": p.paso, "r": p.rinde}
            for p in PRODUCTOS.get(aid, [])]

"""Recetas mexicanas caseras, baratas y altas en proteina (menu.py las combina).

Cada receta da los gramos de UNA porcion base (crudo / leguminosas y cereales
en seco, como en alimentos_mx.py). El generador escala las porciones para
llegar a tus calorias. La sal, el ajo, las especias y la salsa casera no se
cuentan (casi no aportan ni cuestan).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Receta:
    id: str
    nombre: str
    tiempo: str                      # desayuno | comida | cena | colacion
    ingredientes: tuple[tuple[str, float], ...]
    como: str = ""                   # una o dos frases de preparacion
    tags: tuple[str, ...] = field(default=())


def _r(id_, nombre, tiempo, ingredientes, como="", tags=()):
    return Receta(id_, nombre, tiempo, tuple(ingredientes), como, tuple(tags))


RECETAS: list[Receta] = [
    # ── desayunos ───────────────────────────────────────────────────────────
    _r("huevos_mexicana", "Huevos a la mexicana con frijoles", "desayuno",
       [("huevo", 100), ("jitomate", 60), ("cebolla", 20), ("chile", 5), ("aceite", 5),
        ("tortilla", 60), ("frijol", 30)],
       "Sofríe jitomate, cebolla y chile picados; agrega los huevos batidos. Con frijoles de la olla."),
    _r("huevos_nopales", "Huevos con nopales", "desayuno",
       [("huevo", 100), ("nopales", 120), ("jitomate", 40), ("cebolla", 15), ("aceite", 5), ("tortilla", 60)],
       "Asa los nopales en tiras, agrega jitomate y cebolla, y al final los huevos."),
    _r("tacos_huevo_papa", "Tacos de huevo con papa", "desayuno",
       [("huevo", 100), ("papa", 100), ("aceite", 5), ("tortilla", 60), ("jitomate", 40)],
       "Papa en cubitos dorada en poco aceite; revuelve con el huevo. Salsa de jitomate asado."),
    _r("chilaquiles_huevo", "Chilaquiles rojos con huevo", "desayuno",
       [("tortilla", 90), ("jitomate", 100), ("chile", 10), ("cebolla", 15), ("huevo", 100),
        ("queso_fresco", 20), ("aceite", 5)],
       "Tortilla en triángulos horneada o tostada en comal; báñala en salsa de jitomate y chile. Huevo estrellado encima."),
    _r("avena_platano", "Avena con leche y plátano", "desayuno",
       [("avena", 50), ("leche", 250), ("platano", 100), ("cacahuate", 10)],
       "Cuece la avena en la leche 5 minutos; plátano en rodajas y cacahuate picado."),
    _r("licuado_avena", "Licuado de avena, plátano y crema de cacahuate", "desayuno",
       [("leche", 300), ("avena", 40), ("platano", 100), ("crema_cacahuate", 15)],
       "Todo a la licuadora. Para llevar."),
    _r("yogur_avena_fruta", "Yogur con avena y manzana", "desayuno",
       [("yogur", 250), ("avena", 40), ("manzana", 120), ("cacahuate", 10)],
       "Yogur natural con avena cruda, manzana picada y cacahuate."),
    _r("quesadillas_frijol", "Quesadillas de panela con frijoles", "desayuno",
       [("tortilla", 90), ("panela", 60), ("frijol", 25), ("jitomate", 40)],
       "Tortillas en comal con panela; frijoles de la olla y salsa."),
    _r("molletes_tortilla", "Tostadas de frijol con huevo", "desayuno",
       [("tortilla", 60), ("frijol", 35), ("huevo", 100), ("jitomate", 50), ("cebolla", 15)],
       "Tortillas tostadas en comal, frijoles machacados, huevo cocido y pico de gallo."),

    # ── comidas ─────────────────────────────────────────────────────────────
    _r("tinga_pollo", "Tinga de pollo con frijoles", "comida",
       [("pollo", 130), ("jitomate", 120), ("cebolla", 40), ("chile", 10), ("aceite", 5),
        ("tortilla", 90), ("frijol", 30)],
       "Pollo cocido y deshebrado en salsa de jitomate con cebolla fileteada y chipotle o chile. En tostadas o tacos."),
    _r("arroz_frijol_huevo", "Arroz con frijoles y huevo", "comida",
       [("arroz", 60), ("frijol", 60), ("huevo", 100), ("zanahoria", 50), ("aceite", 5), ("tortilla", 30)],
       "Arroz a la mexicana con zanahoria, frijoles de la olla y huevo estrellado. Clásico y baratísimo."),
    _r("lentejas_guisadas", "Lentejas guisadas con verduras", "comida",
       [("lentejas", 80), ("jitomate", 80), ("cebolla", 30), ("zanahoria", 50), ("papa", 80),
        ("aceite", 5), ("tortilla", 60)],
       "Lentejas en caldillo de jitomate con zanahoria y papa (30-40 min en olla, 15 en olla exprés)."),
    _r("picadillo", "Picadillo de res con arroz", "comida",
       [("res", 100), ("papa", 100), ("zanahoria", 60), ("jitomate", 60), ("cebolla", 20),
        ("arroz", 50), ("tortilla", 60), ("aceite", 5)],
       "Carne molida con papa y zanahoria en cubitos y salsa de jitomate."),
    _r("pollo_verduras_arroz", "Pollo con calabacitas y arroz", "comida",
       [("pollo", 150), ("calabacita", 120), ("zanahoria", 60), ("arroz", 60), ("aceite", 5), ("tortilla", 30)],
       "Pollo en piezas dorado y luego guisado con las verduras en un poco de agua."),
    _r("atun_tostadas", "Tostadas de atún con aguacate", "comida",
       [("atun", 100), ("jitomate", 60), ("cebolla", 20), ("limon", 20), ("aguacate", 40),
        ("tortilla", 90), ("frijol", 30)],
       "Atún escurrido con pico de gallo y limón sobre tostadas con frijoles."),
    _r("sopa_fideo_pollo", "Sopa de fideo y pollo deshebrado", "comida",
       [("pasta", 50), ("pollo", 120), ("jitomate", 60), ("zanahoria", 40), ("aceite", 5), ("aguacate", 30),
        ("tortilla", 30)],
       "Fideo dorado en caldillo de jitomate; pollo deshebrado y aguacate encima."),
    _r("cerdo_nopales", "Cerdo en salsa con nopales y frijoles", "comida",
       [("cerdo", 130), ("nopales", 100), ("jitomate", 80), ("chile", 10), ("frijol", 40), ("arroz", 40),
        ("tortilla", 60), ("aceite", 5)],
       "Cerdo en cubos guisado en salsa de jitomate y chile con nopales."),
    _r("soya_mexicana", "Soya a la mexicana con arroz y frijoles", "comida",
       [("soya", 50), ("jitomate", 100), ("cebolla", 30), ("chile", 10), ("calabacita", 80), ("arroz", 60),
        ("frijol", 40), ("tortilla", 60), ("aceite", 5)],
       "Soya hidratada (10 min en agua caliente, exprimida) guisada como picadillo. Rinde como carne, cuesta la mitad.",
       ("vegetariano",)),
    _r("caldo_pollo", "Caldo de pollo con verduras", "comida",
       [("pollo", 150), ("papa", 100), ("zanahoria", 80), ("calabacita", 80), ("arroz", 40), ("tortilla", 60),
        ("limon", 20)],
       "Pollo hervido con las verduras; arroz aparte. Limón y chile al gusto."),
    _r("sardinas_entomatadas", "Sardinas entomatadas con arroz", "comida",
       [("sardina", 150), ("jitomate", 60), ("cebolla", 20), ("arroz", 60), ("frijol", 40), ("tortilla", 60)],
       "Sardina en su salsa con cebolla y jitomate; arroz y frijoles."),
    _r("enfrijoladas_pollo", "Enfrijoladas de pollo", "comida",
       [("tortilla", 120), ("frijol", 70), ("pollo", 90), ("queso_fresco", 20), ("cebolla", 20), ("aceite", 5)],
       "Tortillas pasadas por frijol licuado, rellenas de pollo; queso y cebolla encima."),
    _r("albondigas", "Albóndigas en caldillo con arroz", "comida",
       [("res", 110), ("arroz", 60), ("jitomate", 120), ("chile", 5), ("cebolla", 20), ("calabacita", 80),
        ("tortilla", 30)],
       "Albóndigas de res con un poco de arroz crudo dentro, cocidas en caldillo de jitomate con calabacita."),
    _r("lentejas_huevo", "Lentejas con huevo cocido y arroz", "comida",
       [("lentejas", 60), ("huevo", 100), ("arroz", 50), ("jitomate", 60), ("cebolla", 20), ("zanahoria", 40),
        ("aceite", 5)],
       "Lentejas en caldillo; huevo cocido en mitades y arroz a la mexicana.", ("vegetariano",)),

    _r("pechuga_nopales", "Pechuga asada con nopales y frijoles", "comida",
       [("pechuga", 150), ("nopales", 120), ("jitomate", 60), ("cebolla", 20), ("frijol", 40), ("tortilla", 60)],
       "Pechuga aplanada a la plancha con sal y limón; nopales asados y frijoles de la olla. Magro y rendidor."),
    _r("pechuga_verduras", "Pechuga en salsa verde con calabacitas", "comida",
       [("pechuga", 150), ("calabacita", 150), ("chile", 10), ("cebolla", 20), ("arroz", 40), ("tortilla", 30)],
       "Pechuga en cubos cocida en salsa verde con calabacitas."),

    # ── cenas ───────────────────────────────────────────────────────────────
    _r("tacos_frijol_queso", "Tacos de frijol con queso", "cena",
       [("tortilla", 90), ("frijol", 50), ("queso_fresco", 40), ("jitomate", 40)],
       "Frijoles refritos (con poquito aceite o sin él), queso desmoronado y salsa.", ("vegetariano",)),
    _r("quesadillas_nopales", "Quesadillas de panela con nopales", "cena",
       [("tortilla", 90), ("panela", 60), ("nopales", 100)],
       "Nopales asados en tiras dentro de quesadillas de panela.", ("vegetariano",)),
    _r("huevos_espinaca", "Huevos revueltos con espinaca", "cena",
       [("huevo", 100), ("espinaca", 80), ("cebolla", 15), ("aceite", 5), ("tortilla", 60)],
       "Espinaca y cebolla salteadas, luego el huevo.", ("vegetariano",)),
    _r("atun_mexicana", "Atún a la mexicana en tacos", "cena",
       [("atun", 100), ("jitomate", 60), ("cebolla", 20), ("chile", 5), ("tortilla", 60), ("aguacate", 30)],
       "Atún salteado con jitomate, cebolla y chile."),
    _r("tostadas_soya", "Tostadas de tinga de soya", "cena",
       [("soya", 40), ("jitomate", 80), ("cebolla", 30), ("chile", 5), ("tortilla", 90), ("aceite", 5),
        ("frijol", 20)],
       "Soya hidratada en salsa de tinga (jitomate, cebolla, chipotle) sobre tostadas con frijol.",
       ("vegetariano",)),
    _r("avena_cena", "Avena con leche y manzana", "cena",
       [("avena", 50), ("leche", 250), ("manzana", 120)],
       "Avena cocida en leche con manzana y canela.", ("vegetariano",)),
    _r("calabacitas_queso", "Calabacitas con queso y huevo", "cena",
       [("calabacita", 150), ("jitomate", 50), ("queso_fresco", 40), ("huevo", 50), ("tortilla", 60), ("aceite", 5)],
       "Calabacitas a la mexicana con queso fresco y un huevo revuelto.", ("vegetariano",)),
    _r("ensalada_pollo", "Ensalada de pollo con aguacate", "cena",
       [("pollo", 120), ("espinaca", 60), ("jitomate", 60), ("aguacate", 40), ("limon", 20), ("tortilla", 30)],
       "Pollo deshebrado con espinaca, jitomate y aguacate; limón y sal."),
    _r("tacos_pechuga", "Tacos de pechuga con verduras", "cena",
       [("pechuga", 120), ("cebolla", 30), ("calabacita", 80), ("tortilla", 60), ("limon", 20)],
       "Pechuga en tiras salteada con cebolla y calabacita; limón y salsa."),
    _r("atun_ensalada", "Ensalada de atún con jitomate", "cena",
       [("atun", 100), ("jitomate", 120), ("cebolla", 20), ("limon", 20), ("espinaca", 50), ("tortilla", 30)],
       "Atún con jitomate, cebolla y espinaca; limón. Ligera y muy proteica."),
    _r("yogur_cena", "Yogur con plátano y cacahuate", "cena",
       [("yogur", 250), ("platano", 100), ("cacahuate", 20)],
       "Rápido para noches sin ganas de cocinar.", ("vegetariano",)),

    # ── colaciones (entre comidas) ──────────────────────────────────────────
    _r("col_platano", "Plátano", "colacion", [("platano", 120)]),
    _r("col_manzana", "Manzana", "colacion", [("manzana", 150)]),
    _r("col_naranja", "Naranjas", "colacion", [("naranja", 260)]),
    _r("col_cacahuate", "Puño de cacahuates", "colacion", [("cacahuate", 30)]),
    _r("col_yogur", "Yogur natural", "colacion", [("yogur", 200)]),
    _r("col_leche", "Vaso de leche", "colacion", [("leche", 250)]),
    _r("col_huevo", "Huevos cocidos", "colacion", [("huevo", 100)]),
    _r("col_tostada_frijol", "Tostada con frijoles", "colacion", [("tortilla", 30), ("frijol", 20)]),
    _r("col_proteina", "Licuado de proteína con agua", "colacion", [("proteina_polvo", 32)],
       "Solo si con comida no llegas a tu proteína: es lo más caro por gramo."),
]

POR_ID = {r.id: r for r in RECETAS}

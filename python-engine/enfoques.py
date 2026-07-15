"""Enfoques de entrenamiento y tipos de split.

Cada ENFOQUE traduce un objetivo (recomposicion, volumen, etc.) a parametros
concretos de programacion segun la teoria del informe v3 (Secciones 4, 5 y F):
rangos de reps por bloque, tecnicas, descansos y guia de macros.

Cada SPLIT define la distribucion semanal de dias y que patrones de movimiento
entrena cada dia, respetando la frecuencia 2x/semana por patron.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import ejercicios_db as db


# ── Descansos por tecnica (segundos) ─────────────────────────────────────────
# "volumen" (compuestos del Bloque B) usa >= 2 min: con 90 s se pierden reps en
# las series siguientes y con ello volumen efectivo (Schoenfeld 2016 y metas
# posteriores recomiendan >= 2 min en multiarticulares). 90 s queda solo para
# aislamientos monoarticulares.
DESC = {
    "top_set":   180,
    "back_off":  120,
    "volumen":   120,
    "rest_pause": 90,
    "drop_set":  90,
    "aislamiento": 90,
    "superserie": 60,
    "core":      60,
}


@dataclass(frozen=True)
class Bloque:
    """Parametros de un bloque para un enfoque dado."""
    tecnica_a: str          # tecnica del Bloque A
    reps_top: tuple[int, int]
    reps_backoff: tuple[int, int]
    tecnica_b: str          # tecnica del Bloque B
    reps_b: tuple[int, int]
    tecnica_c: str          # tecnica del Bloque C
    reps_c: tuple[int, int]
    n_ejercicios_b: int     # cuantos compuestos secundarios en B
    n_ejercicios_c: int     # cuantos aislamientos en C
    series_b: int = 3
    series_c: int = 2


@dataclass(frozen=True)
class Enfoque:
    clave: str
    nombre: str
    descripcion: str
    bloque: Bloque
    macros: str             # guia nutricional resumida (texto)
    cardio_dias: int        # dias de cardio LISS por semana
    nota: str = ""
    # rangos estructurados en g/kg de peso corporal — el dashboard los usa
    # para mostrar los gramos diarios ya calculados
    prot_g_kg: tuple[float, float] = (1.8, 2.2)
    carb_g_kg: tuple[float, float] = (3.0, 5.0)
    grasa_g_kg: tuple[float, float] = (0.8, 1.2)
    # tendencia de peso corporal objetivo, en % del peso por semana
    tendencia_sem: tuple[float, float] = (-0.25, 0.25)


# ── Enfoques disponibles ─────────────────────────────────────────────────────
ENFOQUES: dict[str, Enfoque] = {
    "recomposicion": Enfoque(
        clave="recomposicion",
        nombre="Recomposicion Corporal",
        descripcion="Perder grasa y ganar musculo a la vez. El enfoque por defecto del plan.",
        bloque=Bloque(
            tecnica_a="Top Set", reps_top=(6, 8), reps_backoff=(8, 12),
            tecnica_b="Tradicional + AMRAP", reps_b=(8, 12),
            tecnica_c="Rest-Pause", reps_c=(12, 15),
            n_ejercicios_b=2, n_ejercicios_c=3,
        ),
        macros="Proteina 1.8-2.2 g/kg | Carbos 3-5 g/kg | Grasas 0.8-1.2 g/kg | Deficit 200-400 kcal | Creatina 3-5 g/dia",
        prot_g_kg=(1.8, 2.2), carb_g_kg=(3, 5), grasa_g_kg=(0.8, 1.2),
        tendencia_sem=(-0.5, 0.0),
        cardio_dias=2,
        nota="Hombro/pierna prioritarios. Tension mecanica + estres metabolico equilibrados. En deficit, dormir 7-9 h es requisito, no consejo.",
    ),
    "volumen": Enfoque(
        clave="volumen",
        nombre="Volumen (Bulk)",
        descripcion="Maximizar ganancia muscular en superavit calorico controlado.",
        bloque=Bloque(
            tecnica_a="Top Set", reps_top=(6, 8), reps_backoff=(8, 12),
            tecnica_b="Tradicional + AMRAP", reps_b=(8, 12),
            tecnica_c="Rest-Pause", reps_c=(10, 15),
            n_ejercicios_b=3, n_ejercicios_c=4,   # mas volumen en B y C
        ),
        macros="Proteina 1.6-2.0 g/kg | Carbos 4-6 g/kg | Grasas 1.0-1.2 g/kg | Superavit +200-400 kcal | Creatina 3-5 g/dia",
        prot_g_kg=(1.6, 2.0), carb_g_kg=(4, 6), grasa_g_kg=(1.0, 1.2),
        tendencia_sem=(0.25, 0.5),
        cardio_dias=1,
        nota="Mayor volumen en Bloque B (doc F.2). Ritmo objetivo: +0.2-0.4 kg/semana (~0.25-0.5% del peso corporal); mas rapido es mayormente grasa.",
    ),
    "definicion": Enfoque(
        clave="definicion",
        nombre="Definicion (Cut)",
        descripcion="Maximizar perdida de grasa reteniendo musculo en deficit.",
        bloque=Bloque(
            tecnica_a="Top Set", reps_top=(5, 8), reps_backoff=(8, 10),
            tecnica_b="Tradicional + AMRAP", reps_b=(8, 12),
            tecnica_c="Drop Set", reps_c=(12, 15),
            n_ejercicios_b=2, n_ejercicios_c=2,   # reduce Bloque C (doc F.2)
        ),
        macros="Proteina 2.3-2.5 g/kg | Carbos 2-4 g/kg | Grasas 0.8-1.0 g/kg | Deficit 400-600 kcal | Creatina 3-5 g/dia",
        prot_g_kg=(2.3, 2.5), carb_g_kg=(2, 4), grasa_g_kg=(0.8, 1.0),
        tendencia_sem=(-1.0, -0.5),
        cardio_dias=3,
        nota="Mantener intensidad (peso del Top Set) para retener musculo. Mas cardio.",
    ),
    "powerbuilding": Enfoque(
        clave="powerbuilding",
        nombre="Powerbuilding",
        descripcion="Combinar fuerza maxima e hipertrofia. Top Sets mas pesados.",
        bloque=Bloque(
            tecnica_a="Top Set", reps_top=(3, 5), reps_backoff=(6, 8),
            tecnica_b="Tradicional + AMRAP", reps_b=(6, 10),
            tecnica_c="Rest-Pause", reps_c=(10, 12),
            n_ejercicios_b=2, n_ejercicios_c=3,
        ),
        macros="Proteina 1.8-2.2 g/kg | Carbos 4-6 g/kg | Grasas 1.0 g/kg | Mantenimiento o leve superavit | Creatina 3-5 g/dia",
        prot_g_kg=(1.8, 2.2), carb_g_kg=(4, 6), grasa_g_kg=(1.0, 1.0),
        tendencia_sem=(-0.25, 0.25),
        cardio_dias=1,
        nota="Top Set 3-5 reps (mas peso, menos reps). Descansos completos.",
    ),
    "fuerza": Enfoque(
        clave="fuerza",
        nombre="Fuerza Pura",
        descripcion="Maximizar fuerza en los basicos. Esquemas de 1-3 reps al 85-95%.",
        bloque=Bloque(
            tecnica_a="Top Set", reps_top=(1, 3), reps_backoff=(3, 5),
            tecnica_b="Tradicional", reps_b=(4, 6),
            tecnica_c="Tradicional", reps_c=(8, 12),
            n_ejercicios_b=2, n_ejercicios_c=2, series_b=4, series_c=3,
        ),
        macros="Proteina 1.8-2.2 g/kg | Carbos 4-6 g/kg | Grasas 1.0 g/kg | Mantenimiento | Creatina 3-5 g/dia",
        prot_g_kg=(1.8, 2.2), carb_g_kg=(4, 6), grasa_g_kg=(1.0, 1.0),
        tendencia_sem=(-0.25, 0.25),
        cardio_dias=1,
        nota="Volumen reducido, intensidad neural alta. Referencia 5/3/1. "
             "Top Sets de 1-3 reps SIN pasar de RPE 9: el PR se gana, nunca se fuerza.",
    ),
}


# ── Splits: estructura de dias y patrones ────────────────────────────────────
# Cada dia de pesas: (nombre_dia, foco, patrones_A, patrones_B, patrones_C_extra)
#   patrones_A : compuestos pesados (el primero recibe la prioridad si aplica)
#   patrones_B : compuestos secundarios
#   patrones_C : aislamientos fijos del dia (ademas, el generador agrega
#                aislamientos de los musculos trabajados)
@dataclass(frozen=True)
class DiaPlan:
    nombre: str
    foco: str               # "torso" | "pierna" | "push" | "pull" | "full"
    patrones_a: list[str]
    patrones_b: list[str]
    patrones_c: list[str]


@dataclass(frozen=True)
class Split:
    clave: str
    nombre: str
    descripcion: str
    dias_pesas: list[DiaPlan]   # en orden; el generador les asigna dia_semana
    cardio_label: str = "Cardio LISS + Core"


P = db  # alias corto

SPLITS: dict[str, Split] = {
    "upper_lower": Split(
        clave="upper_lower",
        nombre="Upper / Lower (4 dias pesas)",
        descripcion="Torso/Pierna x2. Cada grupo 2x/semana. El split del plan original.",
        dias_pesas=[
            # Orden del Bloque C = prioridad ante el recorte por tiempo (se corta
            # desde el final): primero lo que NADIE mas cubre (brazos directos,
            # curl femoral), al final lo redundante con los compuestos del dia
            # (aislamiento de pecho, extension de cuadriceps).
            DiaPlan("Torso A - Fuerza", "torso",
                    [P.EMPUJE_VERTICAL, P.TIRON_HORIZONTAL],
                    [P.EMPUJE_HORIZONTAL, P.TIRON_VERTICAL],
                    [P.AISL_BICEPS, P.AISL_TRICEPS, P.AISL_HOMBRO, P.EMPUJE_HORIZONTAL]),
            # curl femoral en ambos dias de pierna: la flexion de rodilla no la
            # cubre ningun compuesto (RDL = cadera; el femoral corto queda fuera)
            DiaPlan("Pierna A - Fuerza", "pierna",
                    [P.DOMINANTE_RODILLA, P.DOMINANTE_CADERA],
                    [P.DOMINANTE_RODILLA],
                    [P.AISL_ISQUIOS, P.PANTORRILLA, P.DOMINANTE_RODILLA, P.AISL_HOMBRO]),
            # hombro POSTERIOR en el 2do dia de torso (el lateral ya se cubre en
            # Torso A y, si hay prioridad de hombro, tambien en los dias de pierna)
            DiaPlan("Torso Bombeo", "torso",
                    [P.EMPUJE_VERTICAL, P.TIRON_HORIZONTAL],
                    [P.EMPUJE_HORIZONTAL, P.TIRON_VERTICAL],
                    [P.AISL_BICEPS, P.AISL_TRICEPS, P.AISL_HOMBRO_POST, P.EMPUJE_HORIZONTAL]),
            DiaPlan("Pierna Bombeo", "pierna",
                    [P.DOMINANTE_CADERA, P.DOMINANTE_RODILLA],
                    [P.DOMINANTE_CADERA],
                    [P.AISL_ISQUIOS, P.PANTORRILLA, P.DOMINANTE_RODILLA, P.AISL_HOMBRO]),
        ],
    ),
    "ppl": Split(
        clave="ppl",
        nombre="Push / Piernas / Pull (6 dias pesas)",
        descripcion="Empuje / Pierna / Tiron x2. Las piernas separan los dos dias de "
                    "torso: hombros, codos y agarre llegan mas frescos a cada sesion.",
        dias_pesas=[
            DiaPlan("Push A", "push",
                    [P.EMPUJE_VERTICAL, P.EMPUJE_HORIZONTAL], [P.EMPUJE_HORIZONTAL],
                    [P.AISL_HOMBRO, P.AISL_TRICEPS]),
            DiaPlan("Legs A", "pierna",
                    [P.DOMINANTE_RODILLA, P.DOMINANTE_CADERA], [P.DOMINANTE_RODILLA],
                    [P.AISL_ISQUIOS, P.PANTORRILLA, P.DOMINANTE_RODILLA]),
            DiaPlan("Pull A", "pull",
                    [P.TIRON_HORIZONTAL, P.TIRON_VERTICAL], [P.TIRON_VERTICAL],
                    [P.AISL_BICEPS, P.AISL_HOMBRO_POST]),
            DiaPlan("Push B", "push",
                    [P.EMPUJE_HORIZONTAL, P.EMPUJE_VERTICAL], [P.EMPUJE_VERTICAL],
                    [P.AISL_HOMBRO, P.AISL_TRICEPS]),
            DiaPlan("Legs B", "pierna",
                    [P.DOMINANTE_CADERA, P.DOMINANTE_RODILLA], [P.DOMINANTE_CADERA],
                    [P.AISL_ISQUIOS, P.PANTORRILLA]),
            DiaPlan("Pull B", "pull",
                    [P.TIRON_VERTICAL, P.TIRON_HORIZONTAL], [P.TIRON_HORIZONTAL],
                    [P.AISL_BICEPS, P.AISL_HOMBRO_POST]),
        ],
    ),
    "full_body": Split(
        clave="full_body",
        nombre="Full Body (3 dias pesas)",
        descripcion="Cuerpo completo x3. Ideal con poca disponibilidad.",
        # 2 patrones en A + 2 en B por dia = 12 huecos -> los 6 patrones
        # fundamentales quedan 2x/semana (antes empuje vertical, tiron vertical
        # y dominante de cadera quedaban 1x, rompiendo la regla de frecuencia).
        dias_pesas=[
            DiaPlan("Full Body A", "full",
                    [P.DOMINANTE_RODILLA, P.EMPUJE_HORIZONTAL],
                    [P.TIRON_HORIZONTAL, P.DOMINANTE_CADERA],
                    [P.AISL_HOMBRO, P.AISL_BICEPS]),
            DiaPlan("Full Body B", "full",
                    [P.DOMINANTE_CADERA, P.EMPUJE_VERTICAL],
                    [P.TIRON_VERTICAL, P.DOMINANTE_RODILLA],
                    [P.AISL_HOMBRO_POST, P.AISL_TRICEPS]),
            DiaPlan("Full Body C", "full",
                    [P.EMPUJE_VERTICAL, P.TIRON_HORIZONTAL],
                    [P.EMPUJE_HORIZONTAL, P.TIRON_VERTICAL],
                    [P.PANTORRILLA, P.AISL_BICEPS]),
        ],
    ),
}


# Equipo que el usuario puede marcar como NO disponible en su gimnasio
# (el generador sustituye por alternativas del mismo patron; el peso corporal
# siempre esta disponible y no se puede excluir)
EQUIPOS_FILTRABLES = [
    ("barra", "Barra"),
    ("mancuerna", "Mancuernas"),
    ("polea", "Poleas"),
    ("maquina", "Maquinas"),
]

# Musculos que el usuario puede marcar como prioritarios (rezagados)
MUSCULOS_PRIORIZABLES = [
    ("hombros", "Hombros"),
    ("cuadriceps", "Cuadriceps"),
    ("gluteos", "Gluteos / Cadena posterior"),
    ("pecho", "Pecho"),
    ("dorsales", "Espalda"),
    ("biceps", "Biceps"),
    ("triceps", "Triceps"),
]

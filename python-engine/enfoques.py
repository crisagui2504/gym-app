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


# ── Descansos por tecnica (segundos), tabla del informe v3 ───────────────────
DESC = {
    "top_set":   180,
    "back_off":  120,
    "volumen":   90,
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
    macros: str             # guia nutricional resumida
    cardio_dias: int        # dias de cardio LISS por semana
    nota: str = ""


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
        macros="Proteina 1.6-2.2 g/kg | Carbos 3-5 g/kg | Grasas 0.8-1.2 g/kg | Deficit 200-400 kcal",
        cardio_dias=2,
        nota="Hombro/pierna prioritarios. Tension mecanica + estres metabolico equilibrados.",
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
        macros="Proteina 1.6-2.0 g/kg | Carbos 4-6 g/kg | Grasas 1.0-1.2 g/kg | Superavit +200-400 kcal",
        cardio_dias=1,
        nota="Mayor volumen en Bloque B (doc F.2). Aceptar +0.3-0.5 kg/semana.",
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
        macros="Proteina 2.3-2.5 g/kg | Carbos 2-4 g/kg | Grasas 0.8-1.0 g/kg | Deficit 400-600 kcal",
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
        macros="Proteina 1.8-2.2 g/kg | Carbos 4-6 g/kg | Grasas 1.0 g/kg | Mantenimiento o leve superavit",
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
        macros="Proteina 1.8-2.2 g/kg | Carbos 4-6 g/kg | Grasas 1.0 g/kg | Mantenimiento",
        cardio_dias=1,
        nota="Volumen reducido, intensidad neural alta. Referencia 5/3/1.",
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
            DiaPlan("Torso A - Fuerza", "torso",
                    [P.EMPUJE_VERTICAL, P.TIRON_HORIZONTAL],
                    [P.EMPUJE_HORIZONTAL, P.TIRON_VERTICAL],
                    [P.AISL_HOMBRO, P.AISL_BICEPS, P.AISL_TRICEPS]),
            DiaPlan("Pierna A - Fuerza", "pierna",
                    [P.DOMINANTE_RODILLA, P.DOMINANTE_CADERA],
                    [P.DOMINANTE_RODILLA],
                    [P.DOMINANTE_RODILLA, P.DOMINANTE_CADERA, P.PANTORRILLA, P.AISL_HOMBRO]),
            DiaPlan("Torso Bombeo", "torso",
                    [P.EMPUJE_VERTICAL, P.TIRON_HORIZONTAL],
                    [P.EMPUJE_HORIZONTAL, P.TIRON_VERTICAL],
                    [P.AISL_HOMBRO, P.AISL_BICEPS, P.AISL_TRICEPS]),
            DiaPlan("Pierna Bombeo", "pierna",
                    [P.DOMINANTE_CADERA, P.DOMINANTE_RODILLA],
                    [P.DOMINANTE_CADERA],
                    [P.DOMINANTE_CADERA, P.DOMINANTE_RODILLA, P.PANTORRILLA, P.AISL_HOMBRO]),
        ],
    ),
    "ppl": Split(
        clave="ppl",
        nombre="Push / Pull / Legs (6 dias pesas)",
        descripcion="Empuje / Tiron / Pierna x2. Mayor frecuencia y volumen.",
        dias_pesas=[
            DiaPlan("Push A", "push",
                    [P.EMPUJE_VERTICAL, P.EMPUJE_HORIZONTAL], [P.EMPUJE_HORIZONTAL],
                    [P.AISL_HOMBRO, P.AISL_TRICEPS]),
            DiaPlan("Pull A", "pull",
                    [P.TIRON_HORIZONTAL, P.TIRON_VERTICAL], [P.TIRON_VERTICAL],
                    [P.AISL_BICEPS, P.AISL_HOMBRO]),
            DiaPlan("Legs A", "pierna",
                    [P.DOMINANTE_RODILLA, P.DOMINANTE_CADERA], [P.DOMINANTE_RODILLA],
                    [P.DOMINANTE_RODILLA, P.PANTORRILLA]),
            DiaPlan("Push B", "push",
                    [P.EMPUJE_HORIZONTAL, P.EMPUJE_VERTICAL], [P.EMPUJE_VERTICAL],
                    [P.AISL_HOMBRO, P.AISL_TRICEPS]),
            DiaPlan("Pull B", "pull",
                    [P.TIRON_VERTICAL, P.TIRON_HORIZONTAL], [P.TIRON_HORIZONTAL],
                    [P.AISL_BICEPS, P.AISL_HOMBRO]),
            DiaPlan("Legs B", "pierna",
                    [P.DOMINANTE_CADERA, P.DOMINANTE_RODILLA], [P.DOMINANTE_CADERA],
                    [P.DOMINANTE_CADERA, P.PANTORRILLA]),
        ],
    ),
    "full_body": Split(
        clave="full_body",
        nombre="Full Body (3 dias pesas)",
        descripcion="Cuerpo completo x3. Ideal con poca disponibilidad.",
        dias_pesas=[
            DiaPlan("Full Body A", "full",
                    [P.DOMINANTE_RODILLA, P.EMPUJE_HORIZONTAL], [P.TIRON_HORIZONTAL],
                    [P.AISL_HOMBRO, P.AISL_BICEPS]),
            DiaPlan("Full Body B", "full",
                    [P.DOMINANTE_CADERA, P.EMPUJE_VERTICAL], [P.TIRON_VERTICAL],
                    [P.AISL_HOMBRO, P.AISL_TRICEPS]),
            DiaPlan("Full Body C", "full",
                    [P.DOMINANTE_RODILLA, P.TIRON_HORIZONTAL], [P.EMPUJE_HORIZONTAL],
                    [P.PANTORRILLA, P.AISL_BICEPS]),
        ],
    ),
}


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

"""Base de datos de ejercicios comunes, organizada por patron de movimiento.

Filosofia (informe v3, Seccion 3): el entrenamiento se estructura por PATRONES,
no por musculos. Los 6 patrones fundamentales + aislamientos y accesorios.

Cada ejercicio se etiqueta para que el generador pueda construir rutinas validas:
  patron   : el patron de movimiento al que pertenece
  musculo  : musculo primario (ids compatibles con la app Angular)
  equipo   : barra | mancuerna | polea | maquina | peso_corporal
  bloques  : en que bloques encaja -> 'A' (compuesto pesado), 'B' (secundario),
             'C' (aislamiento / accesorio)
  peso_base: punto de partida sugerido en kg (None = se aprende del historial)
  pref     : preferencia de seleccion (menor = mas comun / prioritario)
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Patrones de movimiento ───────────────────────────────────────────────────
EMPUJE_HORIZONTAL = "empuje_horizontal"
EMPUJE_VERTICAL   = "empuje_vertical"
TIRON_HORIZONTAL  = "tiron_horizontal"
TIRON_VERTICAL    = "tiron_vertical"
DOMINANTE_RODILLA = "dominante_rodilla"
DOMINANTE_CADERA  = "dominante_cadera"
# Accesorios / aislamientos
AISL_HOMBRO      = "aislamiento_hombro"        # deltoide LATERAL (elevaciones)
AISL_HOMBRO_POST = "aislamiento_hombro_post"   # deltoide POSTERIOR + manguito (face pull)
AISL_BICEPS      = "aislamiento_biceps"
AISL_TRICEPS     = "aislamiento_triceps"
AISL_ISQUIOS     = "aislamiento_isquios"       # flexion de rodilla (curl femoral)
PANTORRILLA      = "pantorrilla"
ANTEBRAZO        = "antebrazo"
CORE             = "core"
CARDIO           = "cardio"


@dataclass(frozen=True)
class Ejercicio:
    nombre: str
    patron: str
    musculo: str
    equipo: str
    bloques: tuple[str, ...]
    peso_base: float | None = None
    pref: int = 5


# ── Catalogo ─────────────────────────────────────────────────────────────────
EJERCICIOS: list[Ejercicio] = [
    # ===================== EMPUJE HORIZONTAL (pecho/triceps) ==================
    Ejercicio("Press de Banca con Barra",          EMPUJE_HORIZONTAL, "pecho",  "barra",     ("A", "B"), 36.0, 1),
    Ejercicio("Press Inclinado con Mancuernas",    EMPUJE_HORIZONTAL, "pecho",  "mancuerna", ("A", "B"), None, 2),
    Ejercicio("Press de Banca con Mancuernas",     EMPUJE_HORIZONTAL, "pecho",  "mancuerna", ("A", "B"), None, 3),
    Ejercicio("Press Inclinado con Barra",         EMPUJE_HORIZONTAL, "pecho",  "barra",     ("A", "B"), None, 4),
    Ejercicio("Fondos en Paralelas",               EMPUJE_HORIZONTAL, "pecho",  "peso_corporal", ("B",), None, 5),
    Ejercicio("Press Pecho en Maquina",            EMPUJE_HORIZONTAL, "pecho",  "maquina",   ("B",), None, 6),
    Ejercicio("Pec Deck (Aperturas Maquina)",      EMPUJE_HORIZONTAL, "pecho",  "maquina",   ("C",), None, 7),
    Ejercicio("Aperturas con Mancuernas",          EMPUJE_HORIZONTAL, "pecho",  "mancuerna", ("C",), None, 8),
    Ejercicio("Cruce de Poleas",                   EMPUJE_HORIZONTAL, "pecho",  "polea",     ("C",), None, 9),

    # ===================== EMPUJE VERTICAL (hombro) ===========================
    Ejercicio("Press Militar Mancuernas (Sentado)", EMPUJE_VERTICAL, "hombros", "mancuerna", ("A", "B"), 25.0, 1),
    Ejercicio("Press Arnold con Mancuernas",        EMPUJE_VERTICAL, "hombros", "mancuerna", ("A", "B"), None, 2),
    Ejercicio("Press Militar con Barra",            EMPUJE_VERTICAL, "hombros", "barra",     ("A", "B"), None, 3),
    Ejercicio("Press Hombro en Maquina",            EMPUJE_VERTICAL, "hombros", "maquina",   ("B",), None, 4),

    # ===================== TIRON HORIZONTAL (espalda media) ===================
    Ejercicio("Remo con Mancuerna a 1 Mano",       TIRON_HORIZONTAL, "dorsales", "mancuerna", ("A", "B"), 15.0, 1),
    Ejercicio("Remo con Barra Agarre Prono",       TIRON_HORIZONTAL, "dorsales", "barra",     ("A", "B"), None, 2),
    Ejercicio("Remo en Polea Baja Agarre Neutro",  TIRON_HORIZONTAL, "dorsales", "polea",     ("B",), None, 3),
    Ejercicio("Remo en Maquina Martillo",          TIRON_HORIZONTAL, "dorsales", "maquina",   ("B",), None, 4),
    Ejercicio("Remo en Punta (T-Bar)",             TIRON_HORIZONTAL, "dorsales", "barra",     ("B",), None, 5),

    # ===================== TIRON VERTICAL (dorsal ancho) ======================
    Ejercicio("Jalon al Pecho Agarre Amplio",      TIRON_VERTICAL, "dorsales", "polea",     ("B",), None, 1),
    Ejercicio("Dominadas",                         TIRON_VERTICAL, "dorsales", "peso_corporal", ("A", "B"), None, 2),
    Ejercicio("Jalon Unilateral en Polea",         TIRON_VERTICAL, "dorsales", "polea",     ("B",), None, 3),
    Ejercicio("Jalon Agarre Neutro",               TIRON_VERTICAL, "dorsales", "polea",     ("B",), None, 4),

    # ===================== DOMINANTE DE RODILLA (cuadriceps) ==================
    Ejercicio("Sentadilla Libre con Barra",        DOMINANTE_RODILLA, "cuadriceps", "barra",     ("A", "B"), None, 1),
    Ejercicio("Prensa de Piernas 45 grados",       DOMINANTE_RODILLA, "cuadriceps", "maquina",   ("A", "B"), None, 2),
    Ejercicio("Hack Squat (Maquina)",              DOMINANTE_RODILLA, "cuadriceps", "maquina",   ("A", "B"), None, 3),
    Ejercicio("Sentadilla Bulgara con Mancuernas", DOMINANTE_RODILLA, "cuadriceps", "mancuerna", ("B",), None, 4),
    Ejercicio("Zancadas con Mancuernas",           DOMINANTE_RODILLA, "cuadriceps", "mancuerna", ("B",), None, 5),
    Ejercicio("Sentadilla con Mancuernas (Goblet)", DOMINANTE_RODILLA, "cuadriceps", "mancuerna", ("B",), None, 6),
    Ejercicio("Step Up con Mancuernas",            DOMINANTE_RODILLA, "cuadriceps", "mancuerna", ("B",), None, 7),
    Ejercicio("Extensiones de Cuadriceps (Maquina)", DOMINANTE_RODILLA, "cuadriceps", "maquina", ("C",), None, 8),

    # ===================== DOMINANTE DE CADERA (isquios/gluteo) ===============
    Ejercicio("Hip Thrust con Barra",              DOMINANTE_CADERA, "gluteos", "barra",     ("A", "B"), None, 1),
    Ejercicio("Peso Muerto Rumano con Barra",      DOMINANTE_CADERA, "isquios", "barra",     ("A", "B"), None, 2),
    Ejercicio("Peso Muerto Rumano con Mancuernas", DOMINANTE_CADERA, "isquios", "mancuerna", ("A", "B"), None, 3),
    Ejercicio("Peso Muerto Convencional",          DOMINANTE_CADERA, "isquios", "barra",     ("A",), None, 4),
    Ejercicio("Peso Muerto Sumo con Barra",        DOMINANTE_CADERA, "gluteos", "barra",     ("A", "B"), None, 5),
    Ejercicio("Extensiones Lumbares en Maquina",   DOMINANTE_CADERA, "lumbar",  "maquina",   ("B", "C"), None, 6),

    # ===================== AISLAMIENTO ISQUIOS (flexion de rodilla) ===========
    # El RDL/hip thrust NO cubre la flexion de rodilla: el curl femoral es el
    # unico que carga la cabeza corta del biceps femoral. Patron propio para
    # que el generador nunca lo deje fuera.
    Ejercicio("Curl de Isquios Tumbado (Maquina)", AISL_ISQUIOS, "isquios", "maquina", ("C",), None, 1),
    Ejercicio("Curl de Isquios Sentado (Maquina)", AISL_ISQUIOS, "isquios", "maquina", ("C",), None, 2),

    # ===================== AISLAMIENTO HOMBRO (deltoides lateral) =============
    Ejercicio("Elevaciones Laterales Mancuernas",  AISL_HOMBRO, "hombros", "mancuerna", ("C",), None, 1),
    Ejercicio("Elevaciones Laterales Polea Baja",  AISL_HOMBRO, "hombros", "polea",     ("C",), None, 2),
    Ejercicio("Elevaciones Laterales en Maquina",  AISL_HOMBRO, "hombros", "maquina",   ("C",), None, 3),

    # ===================== HOMBRO POSTERIOR + MANGUITO ========================
    # Patron propio: si vive dentro de "hombro" el generador siempre elige
    # elevaciones laterales y el deltoide posterior queda sin entrenar.
    Ejercicio("Face Pull Polea Alta",              AISL_HOMBRO_POST, "hombros", "polea",   ("C",), None, 1),
    Ejercicio("Pec Deck Invertido",                AISL_HOMBRO_POST, "hombros", "maquina", ("C",), None, 2),

    # ===================== AISLAMIENTO BICEPS =================================
    Ejercicio("Curl con Barra EZ",                 AISL_BICEPS, "biceps", "barra",     ("C",), None, 1),
    Ejercicio("Curl con Mancuernas",               AISL_BICEPS, "biceps", "mancuerna", ("C",), None, 2),
    Ejercicio("Curl Martillo con Mancuernas",      AISL_BICEPS, "biceps", "mancuerna", ("C",), None, 3),
    Ejercicio("Curl Polea Baja Cuerda",            AISL_BICEPS, "biceps", "polea",     ("C",), None, 4),
    Ejercicio("Curl Concentrado",                  AISL_BICEPS, "biceps", "mancuerna", ("C",), None, 5),

    # ===================== AISLAMIENTO TRICEPS ================================
    Ejercicio("Extension Triceps Polea Cuerda",    AISL_TRICEPS, "triceps", "polea",     ("C",), None, 1),
    Ejercicio("Extension Triceps Polea Barra",     AISL_TRICEPS, "triceps", "polea",     ("C",), None, 2),
    Ejercicio("Press Frances con Barra EZ",        AISL_TRICEPS, "triceps", "barra",     ("C",), None, 3),
    Ejercicio("Extension Triceps sobre Cabeza",    AISL_TRICEPS, "triceps", "mancuerna", ("C",), None, 4),
    Ejercicio("Fondos en Banco",                   AISL_TRICEPS, "triceps", "peso_corporal", ("C",), None, 5),

    # ===================== PANTORRILLA =======================================
    Ejercicio("Elevaciones de Pantorrilla De Pie", PANTORRILLA, "gemelos", "maquina", ("C",), None, 1),
    Ejercicio("Elevaciones de Pantorrilla Sentado", PANTORRILLA, "gemelos", "maquina", ("C",), None, 2),

    # ===================== ANTEBRAZO =========================================
    Ejercicio("Curl Invertido con Barra EZ",       ANTEBRAZO, "antebrazos", "barra",         ("C",), None, 1),
    Ejercicio("Farmer's Carry",                    ANTEBRAZO, "antebrazos", "mancuerna",     ("C",), None, 2),
    Ejercicio("Curl de Muneca con Barra (Flexores)", ANTEBRAZO, "antebrazos", "barra",       ("C",), None, 3),
    Ejercicio("Curl de Muneca Inverso (Extensores)", ANTEBRAZO, "antebrazos", "barra",       ("C",), None, 4),
    Ejercicio("Pinzamiento de Disco",              ANTEBRAZO, "antebrazos", "peso_corporal", ("C",), None, 5),
    Ejercicio("Rodillo de Muneca (Wrist Roller)",  ANTEBRAZO, "antebrazos", "peso_corporal", ("C",), None, 6),

    # ===================== CORE ==============================================
    Ejercicio("Plancha Frontal",                   CORE, "abdomen", "peso_corporal", ("C",), None, 1),
    Ejercicio("Elevaciones de Piernas Colgado",    CORE, "abdomen", "peso_corporal", ("C",), None, 2),
    Ejercicio("Crunch en Polea Alta",              CORE, "abdomen", "polea",         ("C",), None, 3),
    Ejercicio("Rueda Abdominal",                   CORE, "abdomen", "peso_corporal", ("C",), None, 4),

    # ===================== CARDIO ============================================
    Ejercicio("Eliptica",                          CARDIO, "abdomen", "maquina", ("C",), None, 1),
    Ejercicio("Bicicleta Estatica",                CARDIO, "abdomen", "maquina", ("C",), None, 2),
    Ejercicio("Caminata Inclinada",                CARDIO, "abdomen", "maquina", ("C",), None, 3),
]


# ── Helpers de consulta ──────────────────────────────────────────────────────
def por_patron(patron: str, bloque: str | None = None) -> list[Ejercicio]:
    """Ejercicios de un patron, opcionalmente filtrados por bloque, ordenados por pref."""
    res = [e for e in EJERCICIOS if e.patron == patron]
    if bloque:
        res = [e for e in res if bloque in e.bloques]
    return sorted(res, key=lambda e: e.pref)


# Mapa: musculo prioritario -> patron que lo entrena en compuesto pesado
MUSCULO_A_PATRON = {
    "hombros":    EMPUJE_VERTICAL,
    "pecho":      EMPUJE_HORIZONTAL,
    "dorsales":   TIRON_HORIZONTAL,
    "espalda":    TIRON_HORIZONTAL,
    "cuadriceps": DOMINANTE_RODILLA,
    "gluteos":    DOMINANTE_CADERA,
    "isquios":    DOMINANTE_CADERA,
}

# Etiquetas legibles de patrones (para el dashboard)
PATRON_LABEL = {
    EMPUJE_HORIZONTAL: "Empuje Horizontal",
    EMPUJE_VERTICAL:   "Empuje Vertical",
    TIRON_HORIZONTAL:  "Tiron Horizontal",
    TIRON_VERTICAL:    "Tiron Vertical",
    DOMINANTE_RODILLA: "Dominante de Rodilla",
    DOMINANTE_CADERA:  "Dominante de Cadera",
    AISL_HOMBRO:       "Hombro lateral (aislamiento)",
    AISL_HOMBRO_POST:  "Hombro posterior / manguito",
    AISL_BICEPS:       "Biceps",
    AISL_TRICEPS:      "Triceps",
    AISL_ISQUIOS:      "Isquios (curl femoral)",
    PANTORRILLA:       "Pantorrilla",
    ANTEBRAZO:         "Antebrazo",
    CORE:              "Core",
    CARDIO:            "Cardio",
}

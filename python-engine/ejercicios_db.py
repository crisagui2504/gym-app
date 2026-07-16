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
    Ejercicio("Jalon al Pecho Agarre Amplio",      TIRON_VERTICAL, "dorsales", "polea",     ("A", "B"), None, 1),
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
    # accesorio de lumbar, solo Bloque C: no debe competir como compuesto de
    # volumen con los pesos muertos (la espalda baja ya trabaja estabilizando)
    Ejercicio("Extensiones Lumbares en Maquina",   DOMINANTE_CADERA, "lumbar",  "maquina",   ("C",), None, 6),

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

# ═════════════════════════════════════════════════════════════════════════════
# ESTIMULO POR SUBMUSCULO — la ponderacion fina que pide el balance del plan.
#
# Cada nodo muscular (espalda, hombro, pecho, pierna...) se divide en las
# subregiones que la anatomia funcional distingue, y cada ejercicio declara
# CUANTO estimula cada una, en "series efectivas" por serie realizada:
#   1.0  = motor primario (el ejercicio existe para ese submusculo)
#   0.75 = motor fuerte
#   0.5  = secundario claro (sinergista con carga significativa)
#   0.25 = accesorio (isometrico o rango parcial)
# Criterio: anatomia funcional + literatura EMG (p. ej. remos = trapecio
# medio/romboides con dorsal fuerte; jalones/dominadas = dorsal ancho puro;
# press inclinado = pecho clavicular; RDL = isquios sin flexion de rodilla).
#
# El generador usa esto para (1) elegir el ejercicio que aporta el estimulo
# MENOS repetido del dia (rendimientos decrecientes: dosis-respuesta) y
# (2) simular que ninguna subregion se sobrecargue ni quede en cero.
# ═════════════════════════════════════════════════════════════════════════════

SUBMUSCULOS = {
    "espalda": ["dorsal", "espalda_alta", "trapecio_sup", "lumbar"],
    "hombro":  ["delt_ant", "delt_lat", "delt_post"],
    "pecho":   ["pecho_sup", "pecho_inf"],
    "brazo":   ["biceps", "triceps", "antebrazo"],
    "pierna":  ["cuadriceps", "isquios", "gluteo", "aductor", "gemelo"],
    "core":    ["abdomen"],
}

ESTIMULOS: dict[str, dict[str, float]] = {
    # ── Empuje horizontal ────────────────────────────────────────────────────
    "Press de Banca con Barra":           {"pecho_inf": 1.0, "delt_ant": 0.5, "triceps": 0.5},
    "Press Inclinado con Mancuernas":     {"pecho_sup": 1.0, "delt_ant": 0.5, "triceps": 0.5},
    "Press de Banca con Mancuernas":      {"pecho_inf": 1.0, "pecho_sup": 0.25, "delt_ant": 0.5, "triceps": 0.5},
    "Press Inclinado con Barra":          {"pecho_sup": 1.0, "delt_ant": 0.5, "triceps": 0.5},
    "Fondos en Paralelas":                {"pecho_inf": 1.0, "triceps": 0.75, "delt_ant": 0.5},
    "Press Pecho en Maquina":             {"pecho_inf": 1.0, "delt_ant": 0.5, "triceps": 0.5},
    "Pec Deck (Aperturas Maquina)":       {"pecho_inf": 1.0, "pecho_sup": 0.25},
    "Aperturas con Mancuernas":           {"pecho_inf": 1.0, "pecho_sup": 0.25},
    "Cruce de Poleas":                    {"pecho_inf": 1.0, "pecho_sup": 0.25},
    # ── Empuje vertical ──────────────────────────────────────────────────────
    "Press Militar Mancuernas (Sentado)": {"delt_ant": 1.0, "delt_lat": 0.5, "triceps": 0.5, "pecho_sup": 0.25},
    "Press Arnold con Mancuernas":        {"delt_ant": 1.0, "delt_lat": 0.5, "triceps": 0.5},
    "Press Militar con Barra":            {"delt_ant": 1.0, "delt_lat": 0.5, "triceps": 0.5, "trapecio_sup": 0.25},
    "Press Hombro en Maquina":            {"delt_ant": 1.0, "delt_lat": 0.5, "triceps": 0.5},
    # ── Tiron horizontal (remos: espalda alta con dorsal fuerte) ────────────
    "Remo con Mancuerna a 1 Mano":        {"espalda_alta": 1.0, "dorsal": 0.75, "biceps": 0.5, "delt_post": 0.25},
    "Remo con Barra Agarre Prono":        {"espalda_alta": 1.0, "dorsal": 0.75, "biceps": 0.5, "lumbar": 0.25},
    "Remo en Polea Baja Agarre Neutro":   {"dorsal": 1.0, "espalda_alta": 0.75, "biceps": 0.5},
    "Remo en Maquina Martillo":           {"espalda_alta": 1.0, "dorsal": 0.75, "biceps": 0.5},
    "Remo en Punta (T-Bar)":              {"espalda_alta": 1.0, "dorsal": 0.75, "biceps": 0.5, "lumbar": 0.25},
    # ── Tiron vertical (dorsal ancho casi puro) ──────────────────────────────
    "Jalon al Pecho Agarre Amplio":       {"dorsal": 1.0, "espalda_alta": 0.25, "biceps": 0.5},
    "Dominadas":                          {"dorsal": 1.0, "espalda_alta": 0.5, "biceps": 0.5, "abdomen": 0.25},
    "Jalon Unilateral en Polea":          {"dorsal": 1.0, "espalda_alta": 0.25, "biceps": 0.5},
    "Jalon Agarre Neutro":                {"dorsal": 1.0, "biceps": 0.5},
    # ── Dominante de rodilla ─────────────────────────────────────────────────
    "Sentadilla Libre con Barra":         {"cuadriceps": 1.0, "gluteo": 0.75, "aductor": 0.5, "lumbar": 0.25},
    "Prensa de Piernas 45 grados":        {"cuadriceps": 1.0, "gluteo": 0.5, "aductor": 0.25},
    "Hack Squat (Maquina)":               {"cuadriceps": 1.0, "gluteo": 0.5},
    "Sentadilla Bulgara con Mancuernas":  {"cuadriceps": 1.0, "gluteo": 0.75, "aductor": 0.25},
    "Zancadas con Mancuernas":            {"cuadriceps": 1.0, "gluteo": 0.75},
    "Sentadilla con Mancuernas (Goblet)": {"cuadriceps": 1.0, "gluteo": 0.5, "abdomen": 0.25},
    "Step Up con Mancuernas":             {"cuadriceps": 1.0, "gluteo": 0.75},
    "Extensiones de Cuadriceps (Maquina)": {"cuadriceps": 1.0},
    # ── Dominante de cadera ──────────────────────────────────────────────────
    "Hip Thrust con Barra":               {"gluteo": 1.0, "isquios": 0.5, "cuadriceps": 0.25},
    "Peso Muerto Rumano con Barra":       {"isquios": 1.0, "gluteo": 0.75, "lumbar": 0.5, "antebrazo": 0.25, "espalda_alta": 0.25},
    "Peso Muerto Rumano con Mancuernas":  {"isquios": 1.0, "gluteo": 0.75, "lumbar": 0.5, "antebrazo": 0.25},
    "Peso Muerto Convencional":           {"gluteo": 1.0, "isquios": 0.75, "lumbar": 0.75, "cuadriceps": 0.25, "antebrazo": 0.5},
    "Peso Muerto Sumo con Barra":         {"gluteo": 1.0, "aductor": 0.75, "isquios": 0.5, "cuadriceps": 0.5, "lumbar": 0.5},
    "Extensiones Lumbares en Maquina":    {"lumbar": 1.0, "gluteo": 0.5, "isquios": 0.5},
    # ── Isquios (flexion de rodilla) ─────────────────────────────────────────
    "Curl de Isquios Tumbado (Maquina)":  {"isquios": 1.0, "gemelo": 0.25},
    "Curl de Isquios Sentado (Maquina)":  {"isquios": 1.0},
    # ── Hombro lateral ───────────────────────────────────────────────────────
    "Elevaciones Laterales Mancuernas":   {"delt_lat": 1.0, "trapecio_sup": 0.25},
    "Elevaciones Laterales Polea Baja":   {"delt_lat": 1.0, "trapecio_sup": 0.25},
    "Elevaciones Laterales en Maquina":   {"delt_lat": 1.0, "trapecio_sup": 0.25},
    # ── Hombro posterior / manguito ──────────────────────────────────────────
    "Face Pull Polea Alta":               {"delt_post": 1.0, "espalda_alta": 0.5, "trapecio_sup": 0.25},
    "Pec Deck Invertido":                 {"delt_post": 1.0, "espalda_alta": 0.5},
    # ── Biceps ───────────────────────────────────────────────────────────────
    "Curl con Barra EZ":                  {"biceps": 1.0, "antebrazo": 0.25},
    "Curl con Mancuernas":                {"biceps": 1.0, "antebrazo": 0.25},
    "Curl Martillo con Mancuernas":       {"biceps": 0.75, "antebrazo": 0.75},
    "Curl Polea Baja Cuerda":             {"biceps": 1.0, "antebrazo": 0.25},
    "Curl Concentrado":                   {"biceps": 1.0},
    # ── Triceps ──────────────────────────────────────────────────────────────
    "Extension Triceps Polea Cuerda":     {"triceps": 1.0},
    "Extension Triceps Polea Barra":      {"triceps": 1.0},
    "Press Frances con Barra EZ":         {"triceps": 1.0},
    "Extension Triceps sobre Cabeza":     {"triceps": 1.0},
    "Fondos en Banco":                    {"triceps": 1.0, "pecho_inf": 0.25, "delt_ant": 0.25},
    # ── Pantorrilla ──────────────────────────────────────────────────────────
    "Elevaciones de Pantorrilla De Pie":  {"gemelo": 1.0},
    "Elevaciones de Pantorrilla Sentado": {"gemelo": 1.0},
    # ── Antebrazo ────────────────────────────────────────────────────────────
    "Curl Invertido con Barra EZ":        {"antebrazo": 1.0, "biceps": 0.5},
    "Farmer's Carry":                     {"antebrazo": 1.0, "trapecio_sup": 0.5, "abdomen": 0.25},
    "Curl de Muneca con Barra (Flexores)": {"antebrazo": 1.0},
    "Curl de Muneca Inverso (Extensores)": {"antebrazo": 1.0},
    "Pinzamiento de Disco":               {"antebrazo": 1.0},
    "Rodillo de Muneca (Wrist Roller)":   {"antebrazo": 1.0},
    # ── Core ─────────────────────────────────────────────────────────────────
    "Plancha Frontal":                    {"abdomen": 1.0},
    "Elevaciones de Piernas Colgado":     {"abdomen": 1.0, "antebrazo": 0.25},
    "Crunch en Polea Alta":               {"abdomen": 1.0},
    "Rueda Abdominal":                    {"abdomen": 1.0, "dorsal": 0.25},
}


def estimulo_de(e: Ejercicio) -> dict[str, float]:
    """Perfil de estimulo por submusculo de un ejercicio (con fallback seguro
    al musculo primario si un ejercicio nuevo aun no esta ponderado)."""
    return ESTIMULOS.get(e.nombre, {e.musculo: 1.0})


# Bisagras de cadera con carga AXIAL sobre la columna (erectores espinales muy
# exigidos). Apilar varias el mismo dia es fatiga sistemica y riesgo lumbar,
# aunque el volumen por submusculo no supere el techo. El Hip Thrust (espalda
# apoyada) y el Curl Femoral (sin carga espinal) NO son axiales.
BISAGRA_AXIAL: frozenset[str] = frozenset({
    "Peso Muerto Rumano con Barra",
    "Peso Muerto Rumano con Mancuernas",
    "Peso Muerto Convencional",
    "Peso Muerto Sumo con Barra",
})


def es_axial(e: Ejercicio) -> bool:
    """True si el ejercicio carga axialmente la columna (peso muerto / RDL)."""
    return e.nombre in BISAGRA_AXIAL


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

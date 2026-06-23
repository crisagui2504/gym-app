"""Plantilla del plan de entrenamiento (metodologia del informe v3).

Estructura semanal Upper/Lower, 4 sesiones de pesas + 2 cardio + 1 descanso.
Bloques: A (Fuerza: Top Set + Back-off), B (Volumen: AMRAP/Drop), C (Aislamiento:
Rest-Pause/Drop/Superserie). Los descansos siguen la tabla del informe.

Cada fila: dia_semana (1=Lun..7=Dom), nombre_dia, bloque, orden, ejercicio,
tecnica, series, reps_min, reps_max, descanso_seg, peso_base, notas.
peso_base = punto de partida sugerido (None = se aprende del historial).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fila:
    dia: int
    nombre_dia: str
    bloque: str
    orden: int
    ejercicio: str
    tecnica: str | None
    series: float
    reps_min: int | None
    reps_max: int | None
    descanso: int | None
    peso_base: float | None
    notas: str | None


# Descansos por tecnica (segundos) segun el informe.
DESC_TOP = 180
DESC_BACKOFF = 120
DESC_VOL = 90
DESC_RP = 90       # entre series de rest-pause (intra es 10s, dentro de la tecnica)
DESC_DROP = 90     # entre series de drop set (intra es 0s)
DESC_SUPER = 90
DESC_AISLAM = 60

PLAN: list[Fila] = [
    # ===================== LUNES (1) — Torso A · Fuerza =====================
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 1, 'Press Militar Mancuernas (Sentado)', 'Top Set', 1, 6, 8, DESC_TOP, 25.0, 'Hombro prioritario. Supera la semana pasada.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 2, 'Press Militar Mancuernas (Sentado)', 'Back-off', 2, 8, 12, DESC_BACKOFF, 20.0, '80% del Top Set.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 3, 'Remo con Mancuerna a 1 Mano', 'Top Set', 1, 6, 8, DESC_TOP, 15.0, 'Por brazo.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 4, 'Remo con Mancuerna a 1 Mano', 'Back-off', 2, 8, 12, DESC_BACKOFF, 12.0, '80% del Top Set. Por brazo.'),
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 5, 'Press de Banca con Barra', 'Tradicional + AMRAP', 3, 8, 12, DESC_VOL, 36.0, 'Ultima serie al fallo (AMRAP).'),
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 6, 'Jalon al Pecho Agarre Amplio', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None, 'Ultima serie al fallo (AMRAP).'),
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 7, 'Elevaciones Laterales Polea Baja', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 8, 'Curl con Barra EZ', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 9, 'Extension Triceps Polea Cuerda', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),

    # ===================== MARTES (2) — Pierna A · Fuerza =====================
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 1, 'Sentadilla Libre con Barra', 'Top Set', 1, 5, 8, DESC_TOP, None, 'Cuadriceps prioritario. Supera la semana pasada.'),
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 2, 'Sentadilla Libre con Barra', 'Back-off', 2, 8, 12, DESC_BACKOFF, None, '80% del Top Set.'),
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 3, 'Peso Muerto Rumano con Mancuernas', 'Tradicional', 3, 10, 12, DESC_VOL, None, 'Lumbar controlada.'),
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 4, 'Prensa de Piernas 45 grados', 'Tradicional + AMRAP', 3, 10, 15, DESC_VOL, None, 'Ultima serie al fallo (AMRAP).'),
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 5, 'Zancadas con Mancuernas', 'Tradicional', 3, 12, 12, DESC_VOL, None, '12 pasos por pierna.'),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 6, 'Extensiones de Cuadriceps (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 7, 'Curl de Isquios Sentado (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 8, 'Elevaciones de Pantorrilla De Pie', 'Tradicional', 3, 15, 20, DESC_AISLAM, None, None),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 9, 'Elevaciones Laterales Mancuernas', 'Rest-Pause', 2, 12, 15, DESC_RP, None, 'Extra hombro.'),

    # ===================== MIERCOLES (3) — Cardio LISS + Core =====================
    Fila(3, 'Cardio LISS + Core', 'Cardio', 1, 'Eliptica', 'Zona 2', 1, 35, 45, None, None, 'Ritmo conversacional. Minutos, no reps.'),
    Fila(3, 'Cardio LISS + Core', 'Core', 2, 'Plancha Frontal', 'Tradicional', 3, None, None, DESC_AISLAM, None, 'Al fallo (min 30 seg).'),
    Fila(3, 'Cardio LISS + Core', 'Core', 3, 'Elevaciones de Piernas Colgado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None, None),
    Fila(3, 'Cardio LISS + Core', 'Core', 4, 'Crunch en Polea Alta', 'Tradicional', 3, 15, 15, DESC_AISLAM, None, None),

    # ===================== JUEVES (4) — Descanso activo =====================
    Fila(4, 'Descanso Activo', 'Descanso', 1, 'Descanso Activo', None, 0, None, None, None, None, 'Camina 10-12k pasos, 2.5-3 L agua, proteina, dormir 7-9h.'),

    # ===================== VIERNES (5) — Torso Bombeo =====================
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 1, 'Press Arnold con Mancuernas', 'Top Set', 1, 6, 8, DESC_TOP, None, 'Hombro prioritario.'),
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 2, 'Press Arnold con Mancuernas', 'Back-off', 2, 10, 12, DESC_BACKOFF, None, '80% del Top Set.'),
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 3, 'Remo en Polea Baja Agarre Neutro', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None, 'Ultima serie al fallo (AMRAP).'),
    Fila(5, 'Torso Bombeo', 'B - Volumen', 4, 'Press Inclinado con Mancuernas', 'Drop Set', 3, 10, 12, DESC_DROP, None, 'Ultima serie Drop: fallo -> -20% -> fallo.'),
    Fila(5, 'Torso Bombeo', 'B - Volumen', 5, 'Jalon Unilateral en Polea', 'Drop Set', 3, 12, 12, DESC_DROP, None, 'Ultima serie Drop.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 6, 'Face Pull Polea Alta', 'Tradicional', 3, 15, 15, DESC_AISLAM, None, None),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 7, 'Pec Deck Invertido', 'Tradicional', 3, 15, 15, DESC_AISLAM, None, 'Maxima contraccion.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 8, 'Curl Polea Baja Cuerda', 'Superserie', 3, 12, 15, DESC_SUPER, None, 'Superserie con triceps.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 9, 'Extension Triceps Polea Barra', 'Superserie', 3, 12, 15, DESC_SUPER, None, 'Superserie con biceps.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 10, 'Curl Invertido con Barra EZ', 'Tradicional', 3, 12, 15, DESC_AISLAM, None, 'Antebrazo, al final.'),

    # ===================== SABADO (6) — Pierna Bombeo =====================
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 1, 'Hip Thrust con Barra', 'Top Set', 1, 6, 8, DESC_TOP, None, 'Gluteo prioritario. Aprieta 1 seg arriba.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 2, 'Hip Thrust con Barra', 'Back-off', 2, 10, 12, DESC_BACKOFF, None, '80% del Top Set.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 3, 'Peso Muerto Rumano con Barra', 'Top Set', 1, 5, 8, DESC_TOP, None, 'Cadena posterior.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 4, 'Peso Muerto Rumano con Barra', 'Back-off', 2, 8, 12, DESC_BACKOFF, None, '80% del Top Set.'),
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 5, 'Sentadilla Bulgara con Mancuernas', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None, 'Ultima serie al fallo. Por pierna.'),
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 6, 'Extensiones Lumbares en Maquina', 'Tradicional', 3, 15, 15, DESC_VOL, None, None),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 7, 'Curl de Isquios Tumbado (Maquina)', 'Drop Set', 2, 12, 15, DESC_DROP, None, 'Fallo -> -20% -> fallo.'),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 8, 'Extensiones de Cuadriceps (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None, None),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 9, 'Elevaciones de Pantorrilla Sentado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None, None),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 10, 'Elevaciones Laterales Polea Baja', 'Rest-Pause', 2, 12, 15, DESC_RP, None, 'Extra hombro.'),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 11, "Farmer's Carry", 'Tradicional', 3, None, None, DESC_AISLAM, None, 'Antebrazo. 30-40 metros por mano.'),

    # ===================== DOMINGO (7) — Cardio LISS + Core =====================
    Fila(7, 'Cardio LISS + Core', 'Cardio', 1, 'Eliptica', 'Zona 2', 1, 35, 45, None, None, 'Zona 2. Tambien vale bici o caminata inclinada.'),
    Fila(7, 'Cardio LISS + Core', 'Core', 2, 'Plancha Frontal', 'Tradicional', 3, None, None, DESC_AISLAM, None, 'Al fallo.'),
    Fila(7, 'Cardio LISS + Core', 'Core', 3, 'Crunch en Polea Alta', 'Tradicional', 3, 15, 20, DESC_AISLAM, None, None),
    Fila(7, 'Cardio LISS + Core', 'Core', 4, 'Elevaciones de Piernas Colgado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None, None),
]

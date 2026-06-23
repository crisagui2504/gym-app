"""Plantilla del plan de entrenamiento (metodologia del informe v3).

NOTA: desde la version con generador dinamico, el plan ACTIVO lo construye
generador.py a partir de config_usuario.json (enfoque + split + prioridades).
Este modulo aporta la dataclass `Fila` (que sigue siendo la unidad del plan) y
conserva `PLAN` como referencia/plantilla fija del enfoque Recomposicion original.

Estructura semanal Upper/Lower, 4 dias de pesas + 2 cardio + 1 descanso.
Ciclo de 5 semanas: S1 base, S2 rotacion Bloque B, S3 superar S1, S4 pico,
S5 deload de volumen (gestionado por planificar.py).

Campo semanas: tuple con los numeros de semana en que aparece la fila
(None = todas las semanas del ciclo S1-S4; el deload se maneja en el motor).

Descansos segun tabla del informe v3:
  Bloque A Top Set  → 3 min
  Bloque A Back-off → 2 min
  Bloque B AMRAP    → 90 s
  Bloque C RP       → 90 s entre series (10 s micro-descanso intra-serie)
  Bloque C Drop Set → 90 s entre series (0 s entre drops intra-serie)
  Bloque C Aislam.  → 90 s
  Superserie        → 60 s entre rondas
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
    semanas: tuple[int, ...] | None = None  # None = todas las semanas S1-S4


# ── Descansos por tecnica (segundos) ────────────────────────────────────────
DESC_TOP     = 180   # Bloque A — Top Set
DESC_BACKOFF = 120   # Bloque A — Back-off
DESC_VOL     = 90    # Bloque B — AMRAP / Tradicional
DESC_RP      = 90    # Bloque C — entre series Rest-Pause (10 s intra-serie)
DESC_DROP    = 90    # Bloque C — entre series Drop Set (0 s entre drops)
DESC_AISLAM  = 90    # Bloque C — Aislamiento Tradicional  [doc: 90 s]
DESC_SUPER   = 60    # Bloque C — Superserie antagonista   [doc: 60 s entre rondas]

PLAN: list[Fila] = [
    # ═══════════════════════════════════════════════════════════════════════
    # LUNES (1) — Torso A · Fuerza
    # Hombro prioritario: Press Militar siempre primero.
    # ═══════════════════════════════════════════════════════════════════════

    # ── Bloque A (todas las semanas) ────────────────────────────────────────
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 1,
         'Press Militar Mancuernas (Sentado)', 'Top Set', 1, 6, 8, DESC_TOP, 25.0,
         'HOMBRO PRIMERO. Supera el peso o la rep de la semana pasada.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 2,
         'Press Militar Mancuernas (Sentado)', 'Back-off', 2, 8, 12, DESC_BACKOFF, 20.0,
         '80% del Top Set.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 3,
         'Remo con Mancuerna a 1 Mano', 'Top Set', 1, 6, 8, DESC_TOP, 15.0,
         'Por brazo. Codo cerca del cuerpo.'),
    Fila(1, 'Torso A - Fuerza', 'A - Fuerza maxima', 4,
         'Remo con Mancuerna a 1 Mano', 'Back-off', 2, 8, 12, DESC_BACKOFF, 12.0,
         '80% del Top Set. Por brazo.'),

    # ── Bloque B S1 / S3 / S4 — ejercicios estandar ────────────────────────
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 5,
         'Press de Banca con Barra', 'Tradicional + AMRAP', 3, 8, 12, DESC_VOL, 36.0,
         'Ultima serie al fallo (AMRAP).', semanas=(1, 3, 4)),
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 6,
         'Jalon al Pecho Agarre Amplio', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None,
         'Ultima serie al fallo (AMRAP).', semanas=(1, 3, 4)),

    # ── Bloque B S2 — rotacion de angulo ────────────────────────────────────
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 5,
         'Press Inclinado con Mancuernas', 'Tradicional + AMRAP', 3, 8, 12, DESC_VOL, None,
         'S2: angulo inclinado vs plano. Ultima serie al fallo.', semanas=(2,)),
    Fila(1, 'Torso A - Fuerza', 'B - Volumen', 6,
         'Remo con Barra Agarre Prono', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None,
         'S2: barra vs mancuerna. Ultima serie al fallo.', semanas=(2,)),

    # ── Bloque C (todas las semanas) ────────────────────────────────────────
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 7,
         'Elevaciones Laterales Polea Baja', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Fallo -> 10 s -> fallo. Codo ligeramente flexionado.'),
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 8,
         'Curl con Barra EZ', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Fallo -> 10 s -> fallo.'),
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 9,
         'Extension Triceps Polea Cuerda', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Fallo -> 10 s -> fallo.'),

    # ── Antebrazos al final (semana especifica) ─────────────────────────────
    Fila(1, 'Torso A - Fuerza', 'C - Aislamiento', 10,
         'Rodillo de Muneca (Wrist Roller)', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S3: antebrazos completo, rango total de muneca.', semanas=(3,)),

    # ═══════════════════════════════════════════════════════════════════════
    # MARTES (2) — Pierna A · Fuerza
    # Cuadriceps prioritario. Elevaciones laterales al final (hombro 4x/sem).
    # ═══════════════════════════════════════════════════════════════════════

    # ── Bloque A (todas las semanas) ────────────────────────────────────────
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 1,
         'Sentadilla Libre con Barra', 'Top Set', 1, 5, 8, DESC_TOP, None,
         'CUADRICEPS PRIMERO. Supera el peso o la rep de la semana pasada.'),
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 2,
         'Sentadilla Libre con Barra', 'Back-off', 2, 8, 12, DESC_BACKOFF, None,
         '80% del Top Set.'),
    Fila(2, 'Pierna A - Fuerza', 'A - Fuerza maxima', 3,
         'Peso Muerto Rumano con Mancuernas', 'Tradicional', 3, 10, 12, DESC_VOL, None,
         'Mantenimiento de cadena posterior. Lumbar controlada.'),

    # ── Bloque B S1 / S3 / S4 ───────────────────────────────────────────────
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 4,
         'Prensa de Piernas 45 grados', 'Tradicional + AMRAP', 3, 10, 15, DESC_VOL, None,
         'Ultima serie al fallo (AMRAP).', semanas=(1, 3, 4)),
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 5,
         'Zancadas con Mancuernas', 'Tradicional', 3, 12, 12, DESC_VOL, None,
         '12 pasos por pierna.', semanas=(1, 3, 4)),

    # ── Bloque B S2 — rotacion ───────────────────────────────────────────────
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 4,
         'Sentadilla con Mancuernas (Goblet)', 'Tradicional + AMRAP', 3, 12, 15, DESC_VOL, None,
         'S2: patron rodilla desde angulo diferente. Ultima serie al fallo.', semanas=(2,)),
    Fila(2, 'Pierna A - Fuerza', 'B - Volumen', 5,
         'Step Up con Mancuernas', 'Tradicional', 3, 10, 12, DESC_VOL, None,
         'S2: unilateral. 10-12 pasos por pierna.', semanas=(2,)),

    # ── Bloque C (todas las semanas) ────────────────────────────────────────
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 6,
         'Extensiones de Cuadriceps (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Fallo -> 10 s -> fallo.'),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 7,
         'Curl de Isquios Sentado (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Fallo -> 10 s -> fallo.'),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 8,
         'Elevaciones de Pantorrilla De Pie', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         None),

    # ── Extra hombro (deltoides lateral, recupera en 24-48h) ───────────────
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 9,
         'Elevaciones Laterales Mancuernas', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Extra hombro (4x/sem). Fallo -> 10 s -> fallo.'),

    # ── Antebrazos al final (semana especifica) ─────────────────────────────
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 10,
         "Farmer's Carry", 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S1/S3: agarre funcional, 30-40 m por mano.', semanas=(1, 3)),
    Fila(2, 'Pierna A - Fuerza', 'C - Aislamiento', 10,
         'Pinzamiento de Disco', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S2: 4 dedos + pulgar, 20-30 seg por mano.', semanas=(2,)),

    # ═══════════════════════════════════════════════════════════════════════
    # MIERCOLES (3) — Cardio LISS + Core
    # ═══════════════════════════════════════════════════════════════════════
    Fila(3, 'Cardio LISS + Core', 'Cardio', 1,
         'Eliptica', 'Zona 2', 1, 35, 45, None, None,
         'Ritmo conversacional. Registrar minutos, no reps.'),
    Fila(3, 'Cardio LISS + Core', 'Core', 2,
         'Plancha Frontal', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'Al fallo (minimo 30 seg).'),
    Fila(3, 'Cardio LISS + Core', 'Core', 3,
         'Elevaciones de Piernas Colgado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         None),
    Fila(3, 'Cardio LISS + Core', 'Core', 4,
         'Crunch en Polea Alta', 'Tradicional', 3, 15, 15, DESC_AISLAM, None,
         None),

    # ═══════════════════════════════════════════════════════════════════════
    # JUEVES (4) — Descanso Activo
    # ═══════════════════════════════════════════════════════════════════════
    Fila(4, 'Descanso Activo', 'Descanso', 1,
         'Descanso Activo', None, 0, None, None, None, None,
         'Camina 10-12k pasos. 2.5-3 L agua. Proteina. Dormir 7-9h.'),

    # ═══════════════════════════════════════════════════════════════════════
    # VIERNES (5) — Torso Bombeo
    # Hombro prioritario: Press Arnold siempre primero.
    # ═══════════════════════════════════════════════════════════════════════

    # ── Bloque A (todas las semanas) ────────────────────────────────────────
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 1,
         'Press Arnold con Mancuernas', 'Top Set', 1, 6, 8, DESC_TOP, None,
         'HOMBRO PRIMERO. Supera el Top Set.'),
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 2,
         'Press Arnold con Mancuernas', 'Back-off', 2, 10, 12, DESC_BACKOFF, None,
         '80% del Top Set.'),
    Fila(5, 'Torso Bombeo', 'A - Fuerza maxima', 3,
         'Remo en Polea Baja Agarre Neutro', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None,
         'Ultima serie al fallo (AMRAP).'),

    # ── Bloque B S1 / S3 / S4 ───────────────────────────────────────────────
    Fila(5, 'Torso Bombeo', 'B - Volumen', 4,
         'Press Inclinado con Mancuernas', 'Drop Set', 3, 10, 12, DESC_DROP, None,
         'Ultima serie: fallo -> -20% -> fallo.', semanas=(1, 3, 4)),
    Fila(5, 'Torso Bombeo', 'B - Volumen', 5,
         'Jalon Unilateral en Polea', 'Drop Set', 3, 12, 12, DESC_DROP, None,
         'Ultima serie Drop.', semanas=(1, 3, 4)),

    # ── Bloque B S2 — rotacion ───────────────────────────────────────────────
    Fila(5, 'Torso Bombeo', 'B - Volumen', 4,
         'Fondos en Paralelas', 'Drop Set', 3, 8, 12, DESC_DROP, None,
         'S2: fondos -> asistido si falla tecnica. Ultima serie Drop.', semanas=(2,)),
    Fila(5, 'Torso Bombeo', 'B - Volumen', 5,
         'Remo en Maquina Martillo', 'Drop Set', 3, 12, 12, DESC_DROP, None,
         'S2: maquina vs polea, curva de fuerza diferente. Ultima serie Drop.', semanas=(2,)),

    # ── Bloque C (todas las semanas) ────────────────────────────────────────
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 6,
         'Face Pull Polea Alta', 'Tradicional', 3, 15, 15, DESC_AISLAM, None,
         'Manguito y trapecio medio. Maximo rango.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 7,
         'Pec Deck Invertido', 'Tradicional', 3, 15, 15, DESC_AISLAM, None,
         'Maxima contraccion en el punto medio.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 8,
         'Curl Polea Baja Cuerda', 'Superserie', 3, 12, 15, DESC_SUPER, None,
         'Superserie con triceps. 60 s entre rondas.'),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 9,
         'Extension Triceps Polea Barra', 'Superserie', 3, 12, 15, DESC_SUPER, None,
         'Superserie con biceps. 60 s entre rondas.'),

    # ── Antebrazos al final (semana especifica) ─────────────────────────────
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 10,
         'Curl Invertido con Barra EZ', 'Tradicional', 3, 12, 15, DESC_AISLAM, None,
         'S1/S3: braquiorradial + extensores. 3 x 12-15.', semanas=(1, 3)),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 10,
         'Curl de Muneca con Barra (Flexores)', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         'S2: flexores directos. Apoya antebrazos en banco.', semanas=(2,)),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 11,
         'Curl de Muneca Inverso (Extensores)', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         'S2: extensores, equilibra los flexores.', semanas=(2,)),
    Fila(5, 'Torso Bombeo', 'C - Aislamiento', 10,
         'Rodillo de Muneca (Wrist Roller)', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S4 PICO: antebrazo completo, rango total. 3 series.', semanas=(4,)),

    # ═══════════════════════════════════════════════════════════════════════
    # SABADO (6) — Pierna Bombeo
    # Cadena posterior prioritaria. Elevaciones laterales al final.
    # ═══════════════════════════════════════════════════════════════════════

    # ── Bloque A (todas las semanas) ────────────────────────────────────────
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 1,
         'Hip Thrust con Barra', 'Top Set', 1, 6, 8, DESC_TOP, None,
         'GLUTEO PRIMERO. Aprieta 1 seg arriba. Supera el Top Set.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 2,
         'Hip Thrust con Barra', 'Back-off', 2, 10, 12, DESC_BACKOFF, None,
         '80% del Top Set.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 3,
         'Peso Muerto Rumano con Barra', 'Top Set', 1, 5, 8, DESC_TOP, None,
         'Cadena posterior. Barra roza las piernas en el descenso.'),
    Fila(6, 'Pierna Bombeo', 'A - Fuerza maxima', 4,
         'Peso Muerto Rumano con Barra', 'Back-off', 2, 8, 12, DESC_BACKOFF, None,
         '80% del Top Set.'),

    # ── Bloque B S1 / S3 / S4 ───────────────────────────────────────────────
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 5,
         'Sentadilla Bulgara con Mancuernas', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None,
         'Ultima serie al fallo. Por pierna.', semanas=(1, 3, 4)),
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 6,
         'Extensiones Lumbares en Maquina', 'Tradicional', 3, 15, 15, DESC_VOL, None,
         'Control total. No hiperextender.', semanas=(1, 3, 4)),

    # ── Bloque B S2 — rotacion ───────────────────────────────────────────────
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 5,
         'Prensa de Piernas 45 grados', 'Drop Set', 3, 10, 15, DESC_DROP, None,
         'S2: cuadriceps ligero en dia de cadena posterior. Ultima serie Drop.', semanas=(2,)),
    Fila(6, 'Pierna Bombeo', 'B - Volumen', 6,
         'Peso Muerto Sumo con Barra', 'Tradicional + AMRAP', 3, 10, 12, DESC_VOL, None,
         'S2: stance ancho, enfasis en aductores y gluteo. Ultima serie al fallo.', semanas=(2,)),

    # ── Bloque C (todas las semanas) ────────────────────────────────────────
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 7,
         'Curl de Isquios Tumbado (Maquina)', 'Drop Set', 2, 12, 15, DESC_DROP, None,
         'Fallo -> -20% -> fallo.'),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 8,
         'Extensiones de Cuadriceps (Maquina)', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Mantenimiento cuad. Fallo -> 10 s -> fallo.'),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 9,
         'Elevaciones de Pantorrilla Sentado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         None),

    # ── Extra hombro ─────────────────────────────────────────────────────────
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 10,
         'Elevaciones Laterales Polea Baja', 'Rest-Pause', 2, 12, 15, DESC_RP, None,
         'Extra hombro (4x/sem). Fallo -> 10 s -> fallo.'),

    # ── Antebrazos al final (semana especifica) ─────────────────────────────
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 11,
         "Farmer's Carry", 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S4 PICO: 30-40 m por mano. Agarre funcional.', semanas=(4,)),
    Fila(6, 'Pierna Bombeo', 'C - Aislamiento', 11,
         'Pinzamiento de Disco', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'S3: 20-30 seg por mano. 4 dedos + pulgar.', semanas=(3,)),

    # ═══════════════════════════════════════════════════════════════════════
    # DOMINGO (7) — Cardio LISS + Core
    # ═══════════════════════════════════════════════════════════════════════
    Fila(7, 'Cardio LISS + Core', 'Cardio', 1,
         'Eliptica', 'Zona 2', 1, 35, 45, None, None,
         'Zona 2. Tambien vale bici o caminata inclinada.'),
    Fila(7, 'Cardio LISS + Core', 'Core', 2,
         'Plancha Frontal', 'Tradicional', 3, None, None, DESC_AISLAM, None,
         'Al fallo.'),
    Fila(7, 'Cardio LISS + Core', 'Core', 3,
         'Crunch en Polea Alta', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         None),
    Fila(7, 'Cardio LISS + Core', 'Core', 4,
         'Elevaciones de Piernas Colgado', 'Tradicional', 3, 15, 20, DESC_AISLAM, None,
         None),
]

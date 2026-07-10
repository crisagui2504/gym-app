"""Generador dinamico de planes de entrenamiento.

A partir de una configuracion de usuario (enfoque + split + prioridades) construye
un plan semanal completo (list[Fila]) aplicando las reglas del informe v3:

  - Estructura por PATRONES de movimiento, no por musculos (Seccion 3).
  - Cada patron 2x/semana (Seccion 2.2).
  - Bloques A (Top Set + Back-off) / B (Volumen/AMRAP/Drop) / C (aislamiento) (Seccion 4).
  - Musculo prioritario PRIMERO en el Bloque A (Seccion 6, "Prioridad de Orden").
  - Frecuencia extra del musculo prioritario al final de otros dias (Seccion 6.1).
  - Antebrazos SIEMPRE al final, en dias no consecutivos (Seccion 8.1).
  - Rotacion del Bloque B en la Semana 2 (Seccion 9).
  - Descansos por tecnica segun la tabla del informe (Seccion 7).
  - Gestion de fatiga (evidencia 2022-2025, ver docs/CAMBIOS_EVIDENCIA.md):
    S1-S2 a RIR 1-2; las tecnicas de intensidad (AMRAP / Rest-Pause / Drop)
    solo en S3-S4 y solo en la ultima serie del ejercicio.

El resultado usa la misma dataclass Fila que consume planificar.py, asi que el
motor de sobrecarga progresiva sigue funcionando sin cambios.
"""
from __future__ import annotations

import ejercicios_db as db
from config_usuario import cargar_config
from enfoques import DESC, ENFOQUES, SPLITS, Enfoque, Split, DiaPlan
from plan_template import Fila

# ── Layout de cada split: que dia de la semana (1=Lun..7=Dom) ────────────────
# pesas: dia_semana de cada DiaPlan (en orden). libres: dias para cardio/descanso.
LAYOUTS: dict[str, dict] = {
    "upper_lower": {"pesas": [1, 2, 5, 6], "libres": [3, 7, 4]},
    "ppl":         {"pesas": [1, 2, 3, 4, 5, 6], "libres": [7]},
    "full_body":   {"pesas": [1, 3, 5], "libres": [2, 4, 7, 6]},
}

# Dias de pesas (indice 0-based) que reciben trabajo de antebrazo (no consecutivos)
ANTEBRAZO_EN_DIAS = {
    "upper_lower": [1, 2],      # Pierna A (Mar) y Torso Bombeo (Vie)
    "ppl":         [1, 4],      # Pull A y Pull B
    "full_body":   [0, 2],      # FB A y FB C
}

# Rotacion de antebrazo por semana del mesociclo
ANTEBRAZO_SEMANA = {
    1: ("Farmer's Carry", "S1/S3: agarre funcional, 30-40 m por mano."),
    2: ("Curl de Muneca con Barra (Flexores)", "S2: flexores directos."),
    3: ("Pinzamiento de Disco", "S3: pinch grip, 20-30 seg por mano."),
    4: ("Rodillo de Muneca (Wrist Roller)", "S4 PICO: antebrazo completo."),
}


def _patron_prioritario(dia: DiaPlan, prioridades: list[str]) -> list[str]:
    """Reordena los patrones del Bloque A para que el musculo debil vaya primero."""
    patrones = list(dia.patrones_a)
    for musculo in prioridades:
        patron = db.MUSCULO_A_PATRON.get(musculo)
        if patron in patrones:
            patrones.remove(patron)
            patrones.insert(0, patron)
            break
    return patrones


def _nota_pc(ej, nota: str) -> str:
    """Agrega la ruta de progresion a los ejercicios de peso corporal
    (dominadas, fondos...): sin esto no tienen forma de sobrecargar."""
    if ej.equipo == "peso_corporal":
        return f"{nota} Peso corporal: si superas el rango en todas las series, agrega lastre (+2.5 kg).".strip()
    return nota


def _elegir(patron: str, bloque: str, usados: set[str], orden_pref: int = 0,
            excluidos: frozenset[str] = frozenset()):
    """Devuelve el ejercicio mas preferido de un patron/bloque que no este usado.
    orden_pref=1 devuelve el segundo mas preferido (para rotacion del Bloque B).
    excluidos = equipo que el gym no tiene; si no queda opcion, el filtro se
    ignora antes que dejar el patron sin ejercicio."""
    todos = db.por_patron(patron, bloque)
    disponibles = [e for e in todos if e.equipo not in excluidos] or todos
    opciones = [e for e in disponibles if e.nombre not in usados]
    if not opciones:
        opciones = disponibles  # permite repetir si no hay alternativa
    if not opciones:
        return None
    return opciones[min(orden_pref, len(opciones) - 1)]


def _dia_pesas(dia: DiaPlan, dia_sem: int, enf: Enfoque, prioridades: list[str],
               con_antebrazo: bool, variante: int = 0,
               excluidos: frozenset[str] = frozenset()) -> list[Fila]:
    b = enf.bloque
    filas: list[Fila] = []
    usados: set[str] = set()
    orden = 1

    # En piernas, el 2do dia del foco respeta el orden de diseno del split
    # (Pierna A = rodilla primero; Pierna Bombeo = cadera primero).
    if dia.foco == "pierna" and variante > 0:
        patrones_a = list(dia.patrones_a)
    else:
        patrones_a = _patron_prioritario(dia, prioridades)

    # ── BLOQUE A — Top Set + Back-off (musculo prioritario primero) ──────────
    for patron in patrones_a:
        # el 2do dia del mismo foco usa el ejercicio alternativo (variedad)
        ej = _elegir(patron, "A", usados, orden_pref=variante, excluidos=excluidos)
        if not ej:
            continue
        usados.add(ej.nombre)
        es_prio = db.MUSCULO_A_PATRON.get(prioridades[0] if prioridades else "") == patron
        nota_prio = f"{ej.musculo.upper()} PRIMERO. " if es_prio else ""
        filas.append(Fila(dia_sem, dia.nombre, "A - Fuerza maxima", orden, ej.nombre,
                          b.tecnica_a, 1, b.reps_top[0], b.reps_top[1], DESC["top_set"],
                          ej.peso_base,
                          _nota_pc(ej, f"{nota_prio}Supera el Top Set de la semana pasada.")))
        orden += 1
        filas.append(Fila(dia_sem, dia.nombre, "A - Fuerza maxima", orden, ej.nombre,
                          "Back-off", 2, b.reps_backoff[0], b.reps_backoff[1],
                          DESC["back_off"], None, "80% del Top Set."))
        orden += 1

    # ── BLOQUE B — Volumen (RIR 1-2; fallo solo en S3-S4) ───────────────────
    # Evidencia (Refalo 2023, Robinson 2024): entrenar a 1-3 reps en reserva
    # produce hipertrofia comparable al fallo con bastante menos fatiga. El
    # fallo se reserva para la mitad final del mesociclo, cuando el pico lo pide.
    es_bombeo = "Bombeo" in dia.nombre or "B" == dia.nombre[-1:]
    tecnica_b = "Drop Set" if es_bombeo and enf.clave in ("recomposicion", "volumen") else b.tecnica_b
    patrones_b = (dia.patrones_b * b.n_ejercicios_b)[:b.n_ejercicios_b]
    for patron in patrones_b:
        ej = _elegir(patron, "B", usados, excluidos=excluidos)
        if ej:
            usados.add(ej.nombre)
            nota_fallo = ("Ultima serie al fallo (AMRAP)." if "AMRAP" in tecnica_b else
                          "Ultima serie Drop: fallo -> -20% -> fallo." if "Drop" in tecnica_b else "")
            if nota_fallo:
                # S1: base sin fallo; S3-S4: se agrega la tecnica de intensidad
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  "Tradicional", b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, "Deja 1-2 reps en reserva (RIR 1-2)."),
                                  semanas=(1,)))
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  tecnica_b, b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, f"Series previas RIR 1-2. {nota_fallo}"),
                                  semanas=(3, 4)))
            else:
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  tecnica_b, b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, "Deja 1-2 reps en reserva (RIR 1-2)."),
                                  semanas=(1, 3, 4)))
            # alternativo (S2) - rotacion de angulo: estimulo nuevo, sin fallo
            alt = _elegir(patron, "B", usados, orden_pref=1, excluidos=excluidos)
            if alt and alt.nombre != ej.nombre:
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, alt.nombre,
                                  "Tradicional", b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], alt.peso_base,
                                  _nota_pc(alt, "S2: rotacion de angulo. RIR 1-2."),
                                  semanas=(2,)))
            orden += 1

    # ── BLOQUE C — Aislamiento / accesorios ──────────────────────────────────
    patrones_c = list(dia.patrones_c)
    # frecuencia extra del musculo prioritario (Seccion 6.1)
    for musculo in prioridades:
        if musculo == "hombros" and db.AISL_HOMBRO not in patrones_c:
            patrones_c.append(db.AISL_HOMBRO)

    # detectar superserie biceps+triceps
    tiene_bi = db.AISL_BICEPS in patrones_c
    tiene_tri = db.AISL_TRICEPS in patrones_c

    n_c = 0
    for patron in patrones_c:
        # el triceps de la superserie no consume cupo ni puede ser recortado:
        # la pareja bi+tri cuenta como UN movimiento (comparten los 60 s de
        # descanso). Antes, con n_ejercicios_c bajo (Definicion), el triceps se
        # recortaba y quedaba un biceps "en superserie" sin pareja.
        es_tri_pareado = patron == db.AISL_TRICEPS and tiene_bi
        exento = (patron in (db.AISL_HOMBRO, db.AISL_HOMBRO_POST, db.PANTORRILLA)
                  or es_tri_pareado)
        if n_c >= b.n_ejercicios_c and not exento:
            continue
        # orden_pref=variante: el 2do dia del mismo foco usa el aislamiento
        # alternativo (curl EZ vs mancuernas, laterales mancuerna vs polea...)
        # para cubrir cabezas/angulos distintos, no repetir el mismo estimulo.
        ej = _elegir(patron, "C", usados, orden_pref=variante, excluidos=excluidos)
        if not ej:
            continue
        usados.add(ej.nombre)
        extra = " Extra hombro (frecuencia 4x/sem)." if patron == db.AISL_HOMBRO and "hombros" in prioridades else ""
        reps_lo, reps_hi = (15, 20) if patron in (db.PANTORRILLA, db.AISL_HOMBRO_POST) else b.reps_c

        # tecnica: superserie si biceps/triceps juntos; pantorrilla tradicional
        if patron == db.AISL_HOMBRO_POST:
            # salud de hombro: trabajo ligero y controlado, nunca al fallo
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base,
                              "Deltoide posterior + manguito. Lento y controlado, RIR 2-3."))
        elif patron == db.AISL_BICEPS and tiene_tri:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Superserie", b.series_c, reps_lo, reps_hi, DESC["superserie"],
                              ej.peso_base, ("Superserie con triceps. 60 s entre rondas. RIR 1-2." + extra).strip()))
        elif es_tri_pareado:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Superserie", b.series_c, reps_lo, reps_hi, DESC["superserie"],
                              ej.peso_base, ("Superserie con biceps. 60 s entre rondas. RIR 1-2." + extra).strip()))
        elif patron == db.PANTORRILLA:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, extra.strip()))
        elif "Rest" in b.tecnica_c or "Drop" in b.tecnica_c:
            # tecnica de intensidad solo en S3-S4 y solo en la ULTIMA serie;
            # S1-S2 tradicional lejos del fallo (gestion de fatiga)
            desc_c = DESC["drop_set"] if "Drop" in b.tecnica_c else DESC["rest_pause"]
            nota_c = ("Ultima serie Rest-Pause: fallo -> 10 s -> fallo. Series previas RIR 1-2."
                      if "Rest" in b.tecnica_c else
                      "Ultima serie Drop: fallo -> -20% -> fallo. Series previas RIR 1-2.")
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, ("Deja 1-2 reps en reserva (RIR 1-2)." + extra).strip(),
                              semanas=(1, 2)))
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              b.tecnica_c, b.series_c, reps_lo, reps_hi, desc_c,
                              ej.peso_base, (nota_c + extra).strip(), semanas=(3, 4)))
        else:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              b.tecnica_c, b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, ("Deja 1-2 reps en reserva (RIR 1-2)." + extra).strip()))
        orden += 1
        if not es_tri_pareado:
            n_c += 1

    # ── ANTEBRAZO — siempre al final, rotando por semana ─────────────────────
    if con_antebrazo:
        for sem, (nombre_ej, nota) in ANTEBRAZO_SEMANA.items():
            ej = next((e for e in db.EJERCICIOS if e.nombre == nombre_ej), None)
            if ej:
                reps = (None, None) if "Carry" in nombre_ej or "Pinzamiento" in nombre_ej or "Rodillo" in nombre_ej else (12, 15)
                filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                                  "Tradicional", 3, reps[0], reps[1], DESC["aislamiento"],
                                  None, nota, semanas=(sem,)))
        orden += 1

    return filas


def _dia_cardio(dia_sem: int, enf: Enfoque) -> list[Fila]:
    nombre = "Cardio LISS + Core"
    filas = [
        Fila(dia_sem, nombre, "Cardio", 1, "Eliptica", "Zona 2", 1, 35, 45, None, None,
             "Ritmo conversacional. Registrar minutos, no reps."),
    ]
    core = ["Plancha Frontal", "Crunch en Polea Alta", "Elevaciones de Piernas Colgado"]
    for i, ej in enumerate(core, start=2):
        filas.append(Fila(dia_sem, nombre, "Core", i, ej, "Tradicional", 3,
                          None if ej == "Plancha Frontal" else 15,
                          None if ej == "Plancha Frontal" else 20,
                          DESC["core"], None, "Al fallo." if ej == "Plancha Frontal" else ""))
    return filas


def _dia_descanso(dia_sem: int) -> list[Fila]:
    return [Fila(dia_sem, "Descanso Activo", "Descanso", 1, "Descanso Activo", None, 0,
                 None, None, None, None,
                 "Camina 10-12k pasos. 2.5-3 L agua. Proteina. Dormir 7-9h.")]


def generar_plan(config: dict | None = None) -> list[Fila]:
    """Construye el plan semanal completo a partir de la config del usuario."""
    cfg = config or cargar_config()
    enf = ENFOQUES.get(cfg["enfoque"], ENFOQUES["recomposicion"])
    split = SPLITS.get(cfg["split"], SPLITS["upper_lower"])
    prioridades = cfg.get("prioridades", [])
    excluidos = frozenset(cfg.get("equipo_excluido", []))
    layout = LAYOUTS[split.clave]
    antebrazo_dias = ANTEBRAZO_EN_DIAS.get(split.clave, [])

    filas: list[Fila] = []

    # Dias de pesas (variante = cuantas veces ya aparecio ese foco -> variedad de ejercicio)
    foco_visto: dict[str, int] = {}
    for i, (dia_plan, dia_sem) in enumerate(zip(split.dias_pesas, layout["pesas"])):
        variante = foco_visto.get(dia_plan.foco, 0)
        foco_visto[dia_plan.foco] = variante + 1
        filas += _dia_pesas(dia_plan, dia_sem, enf, prioridades,
                            con_antebrazo=i in antebrazo_dias, variante=variante,
                            excluidos=excluidos)

    # Dias libres -> cardio (hasta enf.cardio_dias) y luego descanso
    for j, dia_sem in enumerate(layout["libres"]):
        if j < enf.cardio_dias:
            filas += _dia_cardio(dia_sem, enf)
        else:
            filas += _dia_descanso(dia_sem)

    # Ordenar por dia de la semana y luego por orden
    filas.sort(key=lambda f: (f.dia, f.orden))
    return filas


def obtener_plan() -> list[Fila]:
    """Plan actual segun la config guardada. Punto de entrada para planificar.py."""
    return generar_plan(cargar_config())


if __name__ == "__main__":
    plan = obtener_plan()
    cfg = cargar_config()
    print(f"Enfoque: {cfg['enfoque']} | Split: {cfg['split']} | Prioridades: {cfg['prioridades']}")
    print(f"Total de filas: {len(plan)}\n")
    dia_actual = None
    for f in plan:
        if f.dia != dia_actual:
            dia_actual = f.dia
            print(f"\n=== Dia {f.dia}: {f.nombre_dia} ===")
        if f.tecnica:
            sem = f" {f.semanas}" if f.semanas else ""
            print(f"  [{f.bloque[:1]}] {f.ejercicio} ({f.tecnica}) {f.reps_min}-{f.reps_max}{sem}")

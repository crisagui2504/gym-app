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
    S1-S2 a RIR 2-3; las tecnicas de intensidad (AMRAP / Rest-Pause / Drop)
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
    # Upper/Lower con basquet los martes y jueves: gym Lun/Mie/Vie/Dom, descanso
    # el sabado. Los numeros van EMPAREJADOS POSICIONALMENTE con
    # SPLITS["upper_lower"].dias_pesas = [Torso A, Pierna A, Torso Bombeo,
    # Pierna Bombeo], de ahi el orden 1,5,3,7 (no es un typo):
    #   Torso A -> 1 (Lun) | Pierna A -> 5 (Vie)
    #   Torso Bombeo -> 3 (Mie) | Pierna Bombeo -> 7 (Dom)
    # O sea: TORSO al principio de la semana y PIERNA al final. Asi los dias de
    # basquet (Mar y Jue) caen entre dias de torso y llegan con las piernas
    # descansadas: aterrizar un salto con agujetas de sentadilla es riesgo de
    # rodilla y tobillo. Ademas las dos sesiones de pierna quedan a 48 h.
    "upper_lower": {"pesas": [1, 5, 3, 7], "libres": [2, 4, 6]},
    # PPL: descanso el JUEVES. Con 6 dias de pesas solo cabe 1 dia libre, y el
    # jueves es el unico que parte la semana en los dos bloques naturales del
    # split (A: Lun-Mie / B: Vie-Dom). Con el martes quedarian 5 dias seguidos.
    # Upper/Lower de 5 DIAS (gym Lun/Mie/Vie/Sab/Dom, deporte Mar y Jue).
    # Emparejado posicionalmente con dias_pesas = [Torso A, Pierna A, Torso
    # Bombeo, Pierna Bombeo, Torso C], de ahi el orden 1,5,3,7,6:
    #   Torso A -> 1 (Lun) | Pierna A -> 5 (Vie) | Torso Bombeo -> 3 (Mie)
    #   Pierna Bombeo -> 7 (Dom) | Torso C -> 6 (Sab)
    # Las dos piernas quedan viernes y domingo: ninguna en vispera del deporte,
    # y a 48 h entre si con el sabado (torso) en medio.
    "upper_lower_5": {"pesas": [1, 5, 3, 7, 6], "libres": [2, 4]},
    "ppl":         {"pesas": [1, 2, 3, 5, 6, 7], "libres": [4]},
    "full_body":   {"pesas": [1, 3, 5], "libres": [2, 4, 7, 6]},
}

# Dias de pesas (indice 0-based) que reciben trabajo de antebrazo (no consecutivos)
ANTEBRAZO_EN_DIAS = {
    "upper_lower": [1, 2],      # Pierna A (Vie) y Torso Bombeo (Mie)
    "upper_lower_5": [1, 2],    # Pierna A (Vie) y Torso Bombeo (Mie)
    "ppl":         [2, 5],      # Pull A (Mie) y Pull B (Dom) en orden Push/Piernas/Pull
    "full_body":   [0, 2],      # FB A y FB C
}

# Antebrazo: metadatos de EJECUCION (no un calendario). Que ejercicio toca cada
# semana lo decide _elegir con el estimulo acumulado, no una tabla fija.
ANTEBRAZO_SIN_REPS = frozenset({
    "Farmer's Carry", "Pinzamiento de Disco", "Rodillo de Muneca (Wrist Roller)",
})
ANTEBRAZO_NOTA = {
    "Farmer's Carry": "agarre funcional, 30-40 m por mano.",
    "Pinzamiento de Disco": "pinch grip, 20-30 seg por mano.",
    "Rodillo de Muneca (Wrist Roller)": "antebrazo completo, subir y bajar controlado.",
    "Curl de Muneca con Barra (Flexores)": "flexores directos. RIR 2-3.",
    "Curl de Muneca Inverso (Extensores)": ("extensores de muneca. Peso ligero y "
                                            "excentrico lento: salud del codo "
                                            "(epicondilitis), no fuerza."),
    "Curl Invertido con Barra EZ": "braquiorradial + extensores. RIR 2-3.",
    "Curl Zottman con Mancuernas": ("sube supinado, BAJA pronado y lento: el "
                                    "excentrico es el objetivo."),
    "Extension de Muneca con Banda": ("excentrico lento (3-4 s). Prevencion de "
                                      "epicondilitis: sin dolor, no buscar fallo."),
}


def _patron_prioritario(dia: DiaPlan, prioridades: list[str], variante: int = 0) -> list[str]:
    """Reordena los patrones del Bloque A para que el musculo debil vaya primero.

    Sinergia: si DOS prioridades comparten el mismo dia (p. ej. pecho y hombros,
    ambos de empuje), no se pueden dar al 100% juntas — una fatiga a la otra.
    Se alterna cual va primero entre los dias del mismo foco (Push A prioriza
    una, Push B la otra) via `variante`."""
    patrones = list(dia.patrones_a)
    aplicables = [m for m in prioridades if db.MUSCULO_A_PATRON.get(m) in patrones]
    if not aplicables:
        return patrones
    elegido = db.MUSCULO_A_PATRON[aplicables[variante % len(aplicables)]]
    patrones.remove(elegido)
    patrones.insert(0, elegido)
    return patrones


def _nota_pc(ej, nota: str) -> str:
    """Agrega la ruta de progresion a los ejercicios de peso corporal
    (dominadas, fondos...): sin esto no tienen forma de sobrecargar."""
    if ej.equipo == "peso_corporal":
        return f"{nota} Peso corporal: si superas el rango en todas las series, agrega lastre (+2.5 kg).".strip()
    return nota


def _intensidad_s34(ej, tecnica_b: str, nota_fallo: str) -> tuple[str, str]:
    """Técnica y nota de la última serie en S3-S4 según el equipo del ejercicio.

    Fallo técnico vs muscular: en peso LIBRE (barra/mancuerna), llevar un
    compuesto al RPE 10 real es peligroso — la postura (erectores, core) falla
    antes que el músculo objetivo. Por eso el peso libre se topa en RPE 9
    (fallo técnico). El AMRAP/Drop al fallo total solo se prescribe en máquina,
    polea o peso corporal, donde ir al fallo es seguro."""
    if ej.equipo in ("barra", "mancuerna"):
        return "Tradicional", ("Series previas RIR 2-3. Última serie a RPE 9 "
                               "(fallo TÉCNICO: detente si la postura se rompe, NO al fallo muscular).")
    return tecnica_b, f"Series previas RIR 2-3. {nota_fallo}"


def _ondular_reps(rango: tuple[int, int], ciclo: int) -> tuple[int, int]:
    """Periodización ONDULANTE entre mesociclos: para que el mismo patrón no se
    estanque por acomodación del SNC, el rango del Top Set ondula por ciclo —
    ciclo%3==0 base, ==1 más pesado (-2 reps), ==2 más ligero (+2 reps).
    Solo aplica a rangos de hipertrofia (mínimo >=4); los de fuerza pura
    (1-3) y powerbuilding (3-5) se dejan estables."""
    lo, hi = rango
    if lo is None or lo < 4:
        return rango
    delta = {0: 0, 1: -2, 2: +2}[ciclo % 3]
    nlo = max(3, lo + delta)
    return (nlo, max(nlo + 1, hi + delta))


def ciclo_mesociclo(fecha=None) -> int:
    """Numero de mesociclo (0, 1, 2...) transcurrido desde MES_INICIO.

    Cada ciclo dura 5 semanas (35 dias). Se usa para ROTAR la seleccion de
    ejercicios entre mesociclos: mismo algoritmo y mismos patrones, pero el
    siguiente ejercicio preferido de cada grupo (variacion con intencion,
    Fonseca 2014) para que el plan no sea tedioso. La progresion no se pierde:
    el historial es por ejercicio y se retoma donde quedo."""
    import os

    from datetime import date as _date
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    ini = os.getenv("MES_INICIO")
    if not ini:
        return 0
    try:
        inicio = _date.fromisoformat(ini)
    except ValueError:
        return 0
    hoy = fecha or _date.today()
    return max(0, (hoy - inicio).days // 35)


# Techo util de series efectivas por submusculo y sesion (~8-10 duras; margen
# para el estimulo indirecto). Pasado esto, mas series son volumen basura:
# fatiga sin estimulo adicional (dosis-respuesta con techo por sesion).
PROYECCION_MAX = 10.0

# Tope de ejercicios COMPUESTOS (Bloque A+B) por region en una misma sesion.
# Evita el problema que reporto la usuaria: 3 presses de pecho el mismo dia
# (2 de ellos planos = estimulo casi identico). Cada region grande tiene un
# maximo de compuestos utiles por sesion segun su tamano y n de subregiones:
#   pecho     -> 2 presses (uno plano + uno inclinado, no tres)
#   press_hombro -> 1 (no hacen falta 2 press verticales)
#   espalda   -> 3 (jalon + 2 remos; tiene mas subregiones)
#   cuadriceps-> 2  |  cadera -> 3 (gluteo+isquios+aductor)
_REGION_SUB = {
    "pecho_inf": "pecho", "pecho_sup": "pecho",
    "delt_ant": "press_hombro",
    "dorsal": "espalda", "espalda_alta": "espalda", "trapecio_sup": "espalda",
    "cuadriceps": "cuadriceps",
    "gluteo": "cadera", "isquios": "cadera", "aductor": "cadera", "lumbar": "cadera",
}
REGION_CAP = {"pecho": 2, "press_hombro": 1, "espalda": 3, "cuadriceps": 2, "cadera": 3}

# Maximo de bisagras AXIALES (peso muerto / RDL) por sesion. Se fija en 1: UN
# peso muerto pesado en el Bloque A (el ancla) basta; los demas huecos de cadena
# posterior se llenan con hip thrust / curl femoral (gluteo e isquios SIN carga
# espinal). Apilar 2-3 pesos muertos es fatiga sistemica y riesgo lumbar aunque
# el volumen por submusculo cuadre. La espalda baja ya recibe carga estabilizando
# la sentadilla y el peso muerto principal.
MAX_AXIAL_SESION = 1

# Veces que un MISMO ejercicio de Bloque A/B puede repetirse en la semana.
# El Bloque C ya tenia variedad garantizada (`usados_c_semana` no repite ningun
# aislamiento), pero A y B no tenian nada: con 3 dias del mismo foco, el press de
# banca plano salia los TRES dias y el pecho SUPERIOR se quedaba a cero. Y no lo
# arreglaba rotar, porque no es un empate: el press militar del Bloque A etiqueta
# pecho_sup 0.25, que acumulado (x3 series) deja al press inclinado en 0.6 de
# ganancia frente al 1.0 del plano, asi que el plano gana siempre. El tope obliga
# a que la 3a exposicion sea otro angulo — variacion con intencion (Fonseca 2014)
# y el objetivo declarado del modelo de submusculos: que ninguna subregion quede
# en cero. Con 2 dias por foco (U/L de 4 dias, PPL) el tope no se alcanza y el
# comportamiento es identico al de antes.
MAX_REPES_SEMANA = 2


def _region_de(ej) -> str | None:
    """Region de un ejercicio segun su submusculo PRIMARIO (el de mayor peso)."""
    est = db.estimulo_de(ej)
    if not est:
        return None
    primario = max(est, key=est.get)
    return _REGION_SUB.get(primario)


def _saturado(ej, acumulado: dict[str, float], series: float) -> bool:
    """True si anadir este ejercicio dejaria TODOS sus submusculos primarios
    por encima del techo de la sesion — seria sobrecargar sin ganancia."""
    primarios = [(s, v) for s, v in db.estimulo_de(ej).items() if v >= 0.75]
    return bool(primarios) and all(
        acumulado.get(s, 0.0) + v * series > PROYECCION_MAX for s, v in primarios)


def _ganancia(ej, acumulado: dict[str, float]) -> float:
    """Estimulo marginal que aporta un candidato dado lo YA acumulado en el dia.

    Cada submusculo rinde con retornos decrecientes (dosis-respuesta): una
    serie sobre un musculo fresco vale mas que sobre uno ya castigado. Asi,
    tras unas dominadas (dorsal), un remo (espalda alta) gana a otro jalon
    (dorsal de nuevo) — el problema real que reporto la usuaria.

    Se puntua el MEJOR objetivo (max), no la suma de todos los submusculos.
    Sumar premiaba al ejercicio con mas etiquetas: bastaba un 0.25 accesorio
    para romper un empate que debia resolver la rotacion, y en el bloque de
    aislamiento ganaba el candidato MENOS aislado (el press cerrado le ganaba
    a la extension sobre cabeza por sus etiquetas de pecho y se llevaba las 6
    posiciones de la rotacion, anulandola). Las etiquetas accesorias siguen
    acumulando fatiga en `acumulado`; lo que no hacen es elegir el ejercicio.

    v al cuadrado: manda el objetivo real (v >= 0.75); un accesorio de 0.25
    apenas puntua. Redondeo a 0.1: los casi-empates los resuelve el orden
    canonico de preferencia + rotacion del mesociclo."""
    est = db.estimulo_de(ej)
    if not est:
        return 0.0  # cardio: no aporta estimulo hipertrofico
    return round(max(v * v / (1.0 + acumulado.get(s, 0.0))
                     for s, v in est.items()), 1)


def _elegir(patron: str, bloque: str, usados: set[str], orden_pref: int = 0,
            excluidos: frozenset[str] = frozenset(),
            acumulado: dict[str, float] | None = None):
    """Devuelve el mejor ejercicio de un patron/bloque que no este usado.

    - Sin `acumulado`: rotacion pura por preferencia (orden_pref, circular) —
      se usa en el Bloque A para que los basicos pesados sean estables y la
      progresion sea comparable semana a semana.
    - Con `acumulado`: se elige el candidato con MAYOR ganancia marginal de
      estimulo por submusculo (evita redundancia tipo dominadas + jalon);
      los empates se resuelven por el orden de rotacion del mesociclo.
    excluidos = equipo que el gym no tiene; si no queda opcion, el filtro se
    ignora antes que dejar el patron sin ejercicio."""
    todos = db.por_patron(patron, bloque)
    disponibles = [e for e in todos if e.equipo not in excluidos] or todos
    opciones = [e for e in disponibles if e.nombre not in usados]
    if not opciones:
        opciones = disponibles  # permite repetir si no hay alternativa
    if not opciones:
        return None
    idx = orden_pref % len(opciones)
    if acumulado is None:
        return opciones[idx]
    # orden rotado como desempate estable (max devuelve el primero que empata)
    rotadas = opciones[idx:] + opciones[:idx]
    return max(rotadas, key=lambda e: _ganancia(e, acumulado))


def _dia_pesas(dia: DiaPlan, dia_sem: int, enf: Enfoque, prioridades: list[str],
               con_antebrazo: bool, variante: int = 0,
               excluidos: frozenset[str] = frozenset(), ciclo: int = 0,
               usados_c_semana: set[str] | None = None,
               usados_ab_semana: dict[str, int] | None = None) -> list[Fila]:
    b = enf.bloque
    filas: list[Fila] = []
    usados: set[str] = set()
    orden = 1

    # Estimulo acumulado del dia por submusculo (en series efectivas):
    # cada ejercicio elegido lo alimenta y los bloques B/C lo usan para
    # elegir el candidato que MENOS repita lo ya trabajado.
    # ejercicios de A/B que ya agotaron su cupo semanal (ver MAX_REPES_SEMANA)
    def _agotados() -> frozenset[str]:
        if not usados_ab_semana:
            return frozenset()
        return frozenset(k for k, v in usados_ab_semana.items() if v >= MAX_REPES_SEMANA)

    def _anotar(nombre: str) -> None:
        if usados_ab_semana is not None:
            usados_ab_semana[nombre] = usados_ab_semana.get(nombre, 0) + 1

    est_dia: dict[str, float] = {}
    # compuestos por region en la sesion (para el tope anti-redundancia)
    comp_region: dict[str, int] = {}
    axiales = {"n": 0}  # bisagras axiales usadas en la sesion (dict = mutable en closure)

    def _acumular(ej, series: float, compuesto: bool = False) -> None:
        for sub, v in db.estimulo_de(ej).items():
            est_dia[sub] = est_dia.get(sub, 0.0) + v * series
        if compuesto:
            reg = _region_de(ej)
            if reg:
                comp_region[reg] = comp_region.get(reg, 0) + 1
            if db.es_axial(ej):
                axiales["n"] += 1

    # En piernas, el 2do dia del foco respeta el orden de diseno del split
    # (Pierna A = rodilla primero; Pierna Bombeo = cadera primero).
    if dia.foco == "pierna" and variante > 0:
        patrones_a = list(dia.patrones_a)
    else:
        patrones_a = _patron_prioritario(dia, prioridades, variante)

    # Prioridad en el Bloque B: si un musculo prioritario tiene su patron en el
    # Bloque B de este dia (p. ej. pecho en Upper/Lower, cuyo torso lleva empuje
    # VERTICAL en A y HORIZONTAL en B), se sube a A intercambiandolo con un
    # patron NO prioritario, para darle el trato de compuesto pesado y fresco.
    patrones_b_dia = list(dia.patrones_b)
    for musculo in prioridades:
        pat = db.MUSCULO_A_PATRON.get(musculo)
        if pat and pat in patrones_b_dia and pat not in patrones_a:
            cede = next((x for x in patrones_a
                         if not any(db.MUSCULO_A_PATRON.get(m) == x for m in prioridades)), None)
            if cede:
                patrones_a[patrones_a.index(cede)] = pat
                patrones_b_dia[patrones_b_dia.index(pat)] = cede
                patrones_a.insert(0, patrones_a.pop(patrones_a.index(pat)))
            break

    # ── BLOQUE A — Top Set + Back-off (musculo prioritario primero) ──────────
    for patron in patrones_a:
        # el 2do dia del mismo foco usa el ejercicio alternativo (variedad)
        ej = _elegir(patron, "A", usados | _agotados(), orden_pref=variante + ciclo,
                     excluidos=excluidos)
        if not ej:
            continue
        usados.add(ej.nombre)
        _anotar(ej.nombre)
        _acumular(ej, 3, compuesto=True)  # top set (1) + back-off (2)
        es_prio = (patron == patrones_a[0]
                   and any(db.MUSCULO_A_PATRON.get(m) == patron for m in prioridades))
        nota_prio = f"{ej.musculo.upper()} PRIMERO. " if es_prio else ""
        # Top Set con periodizacion ondulante por mesociclo (anti-acomodacion)
        rt_lo, rt_hi = _ondular_reps(b.reps_top, ciclo)
        fase = {0: "", 1: " (ciclo pesado)", 2: " (ciclo ligero)"}[ciclo % 3]
        filas.append(Fila(dia_sem, dia.nombre, "A - Fuerza maxima", orden, ej.nombre,
                          b.tecnica_a, 1, rt_lo, rt_hi, DESC["top_set"],
                          ej.peso_base,
                          _nota_pc(ej, f"{nota_prio}Supera el Top Set de la semana pasada.{fase}")))
        orden += 1
        filas.append(Fila(dia_sem, dia.nombre, "A - Fuerza maxima", orden, ej.nombre,
                          "Back-off", 2, b.reps_backoff[0], b.reps_backoff[1],
                          DESC["back_off"], None, "80% del Top Set."))
        orden += 1

    # ── BLOQUE B — Volumen (RIR 2-3; fallo solo en S3-S4) ───────────────────
    # Evidencia (Refalo 2023, Robinson 2024): entrenar a 1-3 reps en reserva
    # produce hipertrofia comparable al fallo con bastante menos fatiga. El
    # fallo se reserva para la mitad final del mesociclo, cuando el pico lo pide.
    #
    # Por que RIR 2-3 y no 1-2: peso_volumen() solo sube la carga si la sesion
    # anterior cerro el rango con RPE <= 8, o sea RIR 2 o mas. Prescribir RIR 1-2
    # (= RPE 8-9) contradecia ese filtro: quien obedecia al pie de la letra y
    # cerraba a RIR 1 no volvia a ver una subida de peso, y a las 3 semanas de
    # tonelaje plano el motor lo marcaba como "estancado" y le bajaba la carga.
    # Se castigaba justo al que cumplia. La prescripcion y el filtro ahora dicen
    # lo mismo, y RIR 2-3 sigue dentro del rango con evidencia (1-3).
    # Dia "bombeo" = 2do dia de un foco pareado (Torso/Pierna Bombeo, Push/Legs/
    # Pull B). Antes bastaba con que el nombre acabase en "B", y "Full Body B" (que
    # no tiene pareja) heredaba drop sets por accidente de nomenclatura.
    es_bombeo = ("Bombeo" in dia.nombre
                 or (dia.foco in ("push", "pull", "pierna") and dia.nombre.endswith(" B")))
    tecnica_b = "Drop Set" if es_bombeo and enf.clave in ("recomposicion", "volumen") else b.tecnica_b
    patrones_b = (patrones_b_dia * b.n_ejercicios_b)[:b.n_ejercicios_b]
    # en dias de Drop Set el candidato debe permitir bajar el peso -20%:
    # los ejercicios de peso corporal (dominadas, fondos) quedan fuera
    excl_b = excluidos | frozenset({"peso_corporal"}) if "Drop" in tecnica_b else excluidos
    for patron in patrones_b:
        # si ya se alcanzo el tope de bisagras axiales, se excluyen del pool:
        # el acumulador elige entonces hip thrust / curl femoral (cadena
        # posterior sin carga espinal) en vez de un 3er peso muerto pesado
        bloq_axial = db.BISAGRA_AXIAL if axiales["n"] >= MAX_AXIAL_SESION else frozenset()
        ej = _elegir(patron, "B", usados | bloq_axial | _agotados(), orden_pref=ciclo,
                     excluidos=excl_b,
                     acumulado=est_dia)
        # corte DURO del tope axial: si el fallback de _elegir devolvio igual un
        # peso muerto (no quedaban opciones no-axiales), se omite el hueco antes
        # que meter una 2da bisagra pesada (riesgo lumbar)
        if ej and db.es_axial(ej) and axiales["n"] >= MAX_AXIAL_SESION:
            continue
        if ej and _saturado(ej, est_dia, b.series_b):
            # todo candidato util ya esta al tope de la sesion: mas series de
            # esto seria volumen basura -> el slot se omite (anti-sobrecarga)
            continue
        reg = _region_de(ej) if ej else None
        if reg and comp_region.get(reg, 0) >= REGION_CAP.get(reg, 99):
            # la region ya tiene sus compuestos utiles del dia (p.ej. 2 presses
            # de pecho): un 3ro seria redundante -> se omite el slot
            continue
        if ej:
            usados.add(ej.nombre)
            _anotar(ej.nombre)
            _acumular(ej, b.series_b, compuesto=True)
            nota_fallo = ("Ultima serie al fallo (AMRAP)." if "AMRAP" in tecnica_b else
                          "Ultima serie Drop: fallo -> -20% -> fallo." if "Drop" in tecnica_b else "")
            if nota_fallo:
                # S1: base sin fallo; S3-S4: tecnica de intensidad, pero con
                # fallo TECNICO (RPE 9) si es peso libre — ver _intensidad_s34
                tec_s34, nota_s34 = _intensidad_s34(ej, tecnica_b, nota_fallo)
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  "Tradicional", b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, "Deja 2-3 reps en reserva (RIR 2-3)."),
                                  semanas=(1,)))
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  tec_s34, b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, nota_s34),
                                  semanas=(3, 4)))
            else:
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, ej.nombre,
                                  tecnica_b, b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], ej.peso_base,
                                  _nota_pc(ej, "Deja 2-3 reps en reserva (RIR 2-3)."),
                                  semanas=(1, 3, 4)))
            # alternativo (S2) - rotacion de angulo: estimulo nuevo, sin fallo.
            # respeta el tope axial: la rotacion no debe meter un 2do peso muerto
            bloq_axial_s2 = db.BISAGRA_AXIAL if axiales["n"] >= MAX_AXIAL_SESION else frozenset()
            alt = _elegir(patron, "B", usados | bloq_axial_s2, orden_pref=1, excluidos=excl_b)
            if (alt and alt.nombre != ej.nombre
                    and not (db.es_axial(alt) and axiales["n"] >= MAX_AXIAL_SESION)):
                filas.append(Fila(dia_sem, dia.nombre, "B - Volumen", orden, alt.nombre,
                                  "Tradicional", b.series_b, b.reps_b[0], b.reps_b[1],
                                  DESC["volumen"], alt.peso_base,
                                  _nota_pc(alt, "S2: rotacion de angulo. RIR 2-3."),
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
        # CORE exento como la pantorrilla y los rotadores: es trabajo corto y de
        # poca fatiga que ningun compuesto cubre. Sin la exencion se recortaba en
        # los enfoques con n_ejercicios_c bajo (Definicion = 2) y el abdomen se
        # quedaba otra vez en cero.
        exento = (patron in (db.AISL_HOMBRO, db.AISL_HOMBRO_POST, db.ROTADORES,
                             db.PANTORRILLA, db.CORE)
                  or es_tri_pareado)
        if n_c >= b.n_ejercicios_c and not exento:
            continue
        # orden_pref=variante: el 2do dia del mismo foco usa el aislamiento
        # alternativo (curl EZ vs mancuernas, laterales mancuerna vs polea...)
        # para cubrir cabezas/angulos distintos, no repetir el mismo estimulo.
        # LUMBAR DIRECTO — solo si la sesion NO llevo bisagra axial. Los
        # erectores ya trabajan isometricamente y al limite en un peso muerto o
        # un RDL: anadirles hiperextensiones lastradas encima es exactamente la
        # sobrecarga lumbar que se corrigio en Legs B. Si el dia salio con hip
        # thrust / prensa (sin carga espinal), el lumbar no recibio nada y el
        # accesorio directo si esta justificado. Condicional, no plantilla.
        if patron == db.DOMINANTE_CADERA and axiales["n"] > 0:
            continue
        ej = _elegir(patron, "C", usados | (usados_c_semana or set()),
                     orden_pref=variante + ciclo, excluidos=excluidos,
                     acumulado=est_dia)
        if not ej:
            continue
        # ANTI-SOBRECARGA del Bloque C: mismo guarda que ya tenia el Bloque B.
        # Sin el, el aislamiento se anadia SIEMPRE, aunque todos sus objetivos
        # estuviesen al tope de la sesion: series basura que solo suman fatiga.
        if _saturado(ej, est_dia, b.series_c):
            continue
        usados.add(ej.nombre)
        if usados_c_semana is not None:
            usados_c_semana.add(ej.nombre)  # variedad: no repetir el aislamiento en la semana
        _acumular(ej, b.series_c)
        extra = " Extra hombro (frecuencia 4x/sem)." if patron == db.AISL_HOMBRO and "hombros" in prioridades else ""
        reps_lo, reps_hi = (15, 20) if patron in (db.PANTORRILLA, db.AISL_HOMBRO_POST, db.ROTADORES) else b.reps_c

        # tecnica: superserie si biceps/triceps juntos; pantorrilla tradicional
        if patron in (db.AISL_HOMBRO_POST, db.ROTADORES):
            # salud de hombro: trabajo ligero y controlado, nunca al fallo
            nota_h = ("Deltoide posterior. Lento y controlado, RIR 2-3." if patron == db.AISL_HOMBRO_POST
                      else "Manguito rotador (prehab). Peso ligero, muy controlado, RIR 3-4.")
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, nota_h))
        elif patron == db.AISL_BICEPS and tiene_tri:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Superserie", b.series_c, reps_lo, reps_hi, DESC["superserie"],
                              ej.peso_base, ("Superserie con triceps. 60 s entre rondas. RIR 2-3." + extra).strip()))
        elif es_tri_pareado:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Superserie", b.series_c, reps_lo, reps_hi, DESC["superserie"],
                              ej.peso_base, ("Superserie con biceps. 60 s entre rondas. RIR 2-3." + extra).strip()))
        elif patron == db.PANTORRILLA:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, extra.strip()))
        elif patron == db.CORE:
            # nunca rest-pause/drop, y los isometricos (plancha, Pallof) no
            # llevan repeticiones: se miden en tiempo bajo tension
            iso = ej.nombre in CORE_ISOMETRICO
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c,
                              None if iso else 15, None if iso else 20,
                              DESC["core"], ej.peso_base,
                              "Isometrico: aguanta sin perder la postura." if iso
                              else "Core. Controlado, sin tirar de la lumbar."))
        elif "Rest" in b.tecnica_c or "Drop" in b.tecnica_c:
            # tecnica de intensidad solo en S3-S4 y solo en la ULTIMA serie;
            # S1-S2 tradicional lejos del fallo (gestion de fatiga)
            desc_c = DESC["drop_set"] if "Drop" in b.tecnica_c else DESC["rest_pause"]
            nota_c = ("Ultima serie Rest-Pause: fallo -> 10 s -> fallo. Series previas RIR 2-3."
                      if "Rest" in b.tecnica_c else
                      "Ultima serie Drop: fallo -> -20% -> fallo. Series previas RIR 2-3.")
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, ("Deja 2-3 reps en reserva (RIR 2-3)." + extra).strip(),
                              semanas=(1, 2)))
            if ej.nombre in db.FALLO_LIBRE_INSEGURO:
                # mismo guarda que el Bloque B (_intensidad_s34): fallo TECNICO,
                # no muscular. Ver FALLO_LIBRE_INSEGURO.
                filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                                  "Tradicional", b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                                  ej.peso_base,
                                  ("Series previas RIR 2-3. Ultima serie a RPE 9 (fallo TECNICO: "
                                   "para si la postura se rompe, NO al fallo muscular sin ayudante)."
                                   + extra).strip(), semanas=(3, 4)))
            else:
                filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                                  b.tecnica_c, b.series_c, reps_lo, reps_hi, desc_c,
                                  ej.peso_base, (nota_c + extra).strip(), semanas=(3, 4)))
        else:
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              b.tecnica_c, b.series_c, reps_lo, reps_hi, DESC["aislamiento"],
                              ej.peso_base, ("Deja 2-3 reps en reserva (RIR 2-3)." + extra).strip()))
        orden += 1
        if not es_tri_pareado:
            n_c += 1

    # ── ANTEBRAZO — al final, elegido por el motor (una semana cada uno) ──────
    # Antes era una plantilla fija de 4 nombres por semana: los extensores de
    # muneca NO se entrenaban nunca. Eso importa mas que la estetica — cada remo,
    # dominada y peso muerto entrena los FLEXORES en isometrico (agarre), asi que
    # se hipertrofian solos mientras los extensores quedan debiles tirando de la
    # insercion del codo (epicondilitis lateral).
    #
    # Ahora se elige con el mismo motor que el resto: como `est_dia` ya trae la
    # carga de agarre acumulada del dia, la ganancia marginal del ejercicio de
    # extensores es la mas alta y sale primero SIN reglas especiales. El balance
    # flexor/extensor emerge de los datos, no de una lista escrita a mano.
    if con_antebrazo:
        usados_ante: set[str] = set()
        est_ante = dict(est_dia)  # parte de la fatiga real de agarre del dia
        for sem in (1, 2, 3, 4):
            ej = _elegir(db.ANTEBRAZO, "C", usados_ante, orden_pref=ciclo,
                         excluidos=excluidos, acumulado=est_ante)
            if not ej:
                break
            usados_ante.add(ej.nombre)
            for sub, v in db.estimulo_de(ej).items():
                est_ante[sub] = est_ante.get(sub, 0.0) + v * 3
            sin_reps = ej.nombre in ANTEBRAZO_SIN_REPS
            filas.append(Fila(dia_sem, dia.nombre, "C - Aislamiento", orden, ej.nombre,
                              "Tradicional", 3,
                              None if sin_reps else 12, None if sin_reps else 15,
                              DESC["aislamiento"], None,
                              f"S{sem}: {ANTEBRAZO_NOTA.get(ej.nombre, 'RIR 2-3.')}",
                              semanas=(sem,)))
        orden += 1

    return filas


CORE_ISOMETRICO = frozenset({"Plancha Frontal", "Pallof Press en Polea"})


def _dia_cardio(dia_sem: int, enf: Enfoque, ciclo: int = 0,
                excluidos: frozenset[str] = frozenset(),
                usados_core: set[str] | None = None) -> list[Fila]:
    """Cardio LISS + core. El core se ELIGE con el motor (patron CORE, rotacion
    por mesociclo), no con una lista fija: antes eran 3 nombres hardcodeados y
    la rueda abdominal y el Pallof press no salian nunca. Mismo volumen (3 x 3),
    misma dosis: lo que cambia es que ahora rota y cubre el catalogo."""
    nombre = "Cardio LISS + Core"
    # la modalidad tambien rota por mesociclo (antes era siempre la eliptica y
    # la bicicleta y la caminata no salian nunca). Zona 2 = mismo estimulo.
    modalidades = db.por_patron(db.CARDIO, "C")
    modo = modalidades[ciclo % len(modalidades)] if modalidades else None
    filas = [
        Fila(dia_sem, nombre, "Cardio", 1, modo.nombre if modo else "Eliptica",
             "Zona 2", 1, 35, 45, None, None,
             "Ritmo conversacional. Registrar minutos, no reps."),
    ]
    usados: set[str] = set()
    est_core: dict[str, float] = {}
    orden = 2
    for i in range(3):
        ej = _elegir(db.CORE, "C", usados | (usados_core or set()),
                     orden_pref=ciclo + i, excluidos=excluidos, acumulado=est_core)
        if not ej:
            break
        usados.add(ej.nombre)
        if usados_core is not None:
            usados_core.add(ej.nombre)  # variedad entre los dias de cardio de la semana
        for sub, v in db.estimulo_de(ej).items():
            est_core[sub] = est_core.get(sub, 0.0) + v * 3
        iso = ej.nombre in CORE_ISOMETRICO
        filas.append(Fila(dia_sem, nombre, "Core", orden, ej.nombre, "Tradicional", 3,
                          None if iso else 15, None if iso else 20,
                          DESC["core"], None,
                          "Isometrico: aguanta sin perder la postura." if iso else ""))
        orden += 1
    return filas


def _dia_deporte(dia_sem: int, dep: dict, choca_con_pesas: bool = False) -> list[Fila]:
    """Dia de deporte fuera del gym (basquet, futbol...).

    Aparece en el plan para que la semana sea la real, y sobre todo para que el
    motor NO mande cardio encima: un deporte de equipo ya es acondicionamiento
    intervalado. La nota avisa de lo que el deporte castiga de verdad."""
    nombre = dep.get("nombre") or "Deporte"
    mins = dep.get("minutos") or 90
    # Red de seguridad: si se cambia de split (p. ej. a PPL, que ocupa 6 dias),
    # el deporte puede caer encima de un dia de pesas sin que nadie avise.
    aviso = (" OJO: este dia el plan TAMBIEN trae sesion de gym. Si es dia de "
             "pierna, muevela: saltar con dolor muscular de sentadilla es riesgo de "
             "rodilla y tobillo." if choca_con_pesas else "")
    return [Fila(dia_sem, nombre, "Deporte", 1, nombre, None, 0, None, None, None, None,
                 f"{mins} min. Cuenta como tu acondicionamiento (no hace falta "
                 "cardio extra). Carga pierna: pantorrillas, cuadriceps y aductores, mas "
                 "los aterrizajes. Calienta tobillo y cadera antes." + aviso)]


def _dia_descanso(dia_sem: int) -> list[Fila]:
    return [Fila(dia_sem, "Descanso Activo", "Descanso", 1, "Descanso Activo", None, 0,
                 None, None, None, None,
                 "Camina 10-12k pasos. 2.5-3 L agua. Proteina. Dormir 7-9h.")]


def generar_plan(config: dict | None = None, ciclo: int | None = None) -> list[Fila]:
    """Construye el plan semanal completo a partir de la config del usuario.

    ciclo = numero de mesociclo (rota la seleccion de ejercicios entre ciclos
    de 5 semanas). None = calcularlo automaticamente desde MES_INICIO."""
    cfg = config or cargar_config()
    if ciclo is None:
        ciclo = ciclo_mesociclo()
    enf = ENFOQUES.get(cfg["enfoque"], ENFOQUES["recomposicion"])
    split = SPLITS.get(cfg["split"], SPLITS["upper_lower"])
    prioridades = cfg.get("prioridades", [])
    excluidos = frozenset(cfg.get("equipo_excluido", []))
    layout = LAYOUTS[split.clave]
    antebrazo_dias = ANTEBRAZO_EN_DIAS.get(split.clave, [])

    filas: list[Fila] = []

    # Aislamientos ya usados en la semana: el Bloque C no repite el mismo
    # ejercicio entre dias (variedad real de angulos/cabezas dentro de la semana)
    usados_c_semana: set[str] = set()
    # cuantas veces aparecio cada ejercicio de A/B en la semana (tope: MAX_REPES_SEMANA)
    usados_ab_semana: dict[str, int] = {}

    # Dias de pesas (variante = cuantas veces ya aparecio ese foco -> variedad de ejercicio)
    foco_visto: dict[str, int] = {}
    for i, (dia_plan, dia_sem) in enumerate(zip(split.dias_pesas, layout["pesas"])):
        variante = foco_visto.get(dia_plan.foco, 0)
        foco_visto[dia_plan.foco] = variante + 1
        filas += _dia_pesas(dia_plan, dia_sem, enf, prioridades,
                            con_antebrazo=i in antebrazo_dias, variante=variante,
                            excluidos=excluidos, ciclo=ciclo,
                            usados_c_semana=usados_c_semana,
                            usados_ab_semana=usados_ab_semana)

    # DEPORTE fuera del gym (basquet, futbol...): se pinta como dia propio.
    deporte = cfg.get("deporte") or {}
    dias_deporte = {d for d in (deporte.get("dias") or [])}
    for dia_sem in sorted(dias_deporte):
        filas += _dia_deporte(dia_sem, deporte,
                              choca_con_pesas=dia_sem in set(layout["pesas"]))

    # Dias libres -> cardio (hasta enf.cardio_dias) y luego descanso.
    # Los dias de deporte se descuentan: el deporte YA es el acondicionamiento y
    # mandarle 40 min de eliptica encima a hora y media de basquet es sumar
    # fatiga sin estimulo nuevo.
    # SIEMPRE se reserva al menos un dia de descanso real: el cardio no puede
    # ocupar todos los dias libres. Con PPL (6 dias de pesas -> 1 solo libre) y
    # un enfoque que pide 2 dias de cardio, la semana se quedaba con CERO dias
    # de descanso: 7 dias seguidos de actividad. La recuperacion es parte del
    # estimulo, no el hueco que sobra.
    libres = [d for d in layout["libres"] if d not in dias_deporte]
    n_cardio = min(enf.cardio_dias, max(0, len(libres) - 1))
    usados_core: set[str] = set()  # el core no repite entre dias de cardio
    for j, dia_sem in enumerate(libres):
        if j < n_cardio:
            filas += _dia_cardio(dia_sem, enf, ciclo=ciclo, excluidos=excluidos,
                                 usados_core=usados_core)
        else:
            filas += _dia_descanso(dia_sem)

    # Ordenar por dia de la semana y luego por orden
    filas.sort(key=lambda f: (f.dia, f.orden))
    return filas


def obtener_plan(fecha=None) -> list[Fila]:
    """Plan actual segun la config guardada. Punto de entrada para planificar.py.
    fecha = fecha de la semana objetivo (define que mesociclo toca)."""
    return generar_plan(cargar_config(), ciclo=ciclo_mesociclo(fecha))


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

"""El "entrenador": modelo de fuerza por ejercicio y prescripcion de cargas.

Lo que hace un entrenador personal con tus registros, y que el motor anterior no
hacia (miraba SOLO la ultima sesion y subia de 2.5 en 2.5 pasara lo que pasara):

1. Estima tu 1RM en cada ejercicio con CADA serie, usando el RPE: 60 kg x 8 a
   RPE 8 son 10 reps hasta el fallo -> ~78% del 1RM -> e1RM ~77 kg (tabla RTS de
   Tuchscherer; escala RIR de Zourdos/Helms et al. 2016). Un solo modelo por
   ejercicio: el Top Set, el Back-off y las series de volumen se informan entre si.
2. Suaviza con una media movil exponencial (un mal dia no hunde el plan, un buen
   dia no lo dispara) y descuenta el desentrenamiento tras 4 semanas sin hacer el
   ejercicio (Bosquet et al. 2013: la fuerza maxima apenas cae antes de 28 dias).
3. Corrige el sesgo de RPE: la gente infravalora las reps que le quedan en ~1
   (Halperin et al. 2022); se asume 0.5 (conservador). Se probo calibrarlo con
   las series al fallo del mismo dia y se descarto: esas series llegan con la
   fatiga de las anteriores y el sesgo "medido" salia al reves (simulador).
   Las series muy lejos del fallo (RPE < 6) dan una COTA INFERIOR: el RPE ahi es
   poco fiable (Zourdos 2016), pero "me sobraron 5 o mas" si dice que el peso se
   queda corto. Descartarlas dejaba al modelo pegado a una estimacion vieja
   mientras el usuario hacia series con 10+ reps de sobra (simulador).
4. Detecta si el RPE no informa (siempre el mismo numero, p. ej. el 8 que la app
   trae por defecto): entonces no se usa para estimar y se vuelve a la doble
   progresion clasica.
5. Prescribe la carga EXACTA para llegar al tope del rango al RPE objetivo, con
   limites de seguridad por sesion (+10% normal, +20% si la ultima fue clarisimamente
   facil; -15% como mucho hacia abajo) y redondeo a pesos que se pueden cargar.
6. Mide el rendimiento contra la tendencia: varios ejercicios por debajo a la vez
   = fatiga acumulada (deload anticipado); ninguna mejora en 3 semanas =
   estancamiento real (no "tonelaje", que cambia con solo cambiar las series).

La autorregulacion por RPE supera a la carga fija en fuerza maxima (Zhang et al.
2021, meta-analisis, ES 0.64; Larsen et al. 2021).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

# %1RM para N repeticiones al fallo (RPE 10), tabla RTS. Indice 0 = 1 rep.
RTS_FALLO = [1.000, 0.955, 0.922, 0.892, 0.863, 0.837, 0.811, 0.786, 0.762, 0.739, 0.707, 0.680]

SESGO_POR_DEFECTO = 0.5     # RIR que la gente se deja sin saberlo (Halperin 2022: ~1; conservador)
ALFA_EWMA = 0.5             # peso de la sesion nueva en la tendencia
REPS_MAX_FIABLES = 60       # tope de cordura; la curva (RTS + Epley) es continua. Truncar en 20
                            # tiraba la senal clave de una calibracion: 50 reps con 42.5 kg
                            # "valian" un 1RM de 75 cuando el real era 130 (simulador)
NOTA_CALIBRAR = "CALIBRAR:"
DESENTRENO_SEMANAS = 4      # sin perdida hasta aqui (Bosquet 2013)
DESENTRENO_POR_SEMANA = 0.01
SUBIDA_MAX = 0.10           # +10% por sesion como mucho...
SUBIDA_MAX_FACIL = 0.15     # ...+15% si la ultima vez sobraron 5+ reps (~5 reps en la tabla RTS)
RIR_FACIL = 5.0
SUBIDA_MAX_FIABLE = 0.30    # ...y hasta +30% si el dato es FIABLE: serie a 3 o menos del fallo
RIR_FIABLE = 3.0
BAJADA_MAX = 0.15
BAJADA_MAX_FALLO = 0.30     # sin llegar ni a la mitad del minimo: el peso estaba muy mal estimado


def pct_1rm(reps_al_fallo: float) -> float:
    """Fraccion del 1RM con la que se llega al fallo en `reps_al_fallo` reps.
    Tabla RTS de 1 a 12 (interpolada); a partir de 12, Epley escalado para empalmar."""
    n = max(1.0, float(reps_al_fallo))
    if n <= 12:
        lo = int(math.floor(n))
        hi = min(12, lo + 1)
        a, b = RTS_FALLO[lo - 1], RTS_FALLO[hi - 1]
        return a + (b - a) * (n - lo)
    return RTS_FALLO[11] * (1 + 12 / 30) / (1 + n / 30)


def reps_al_fallo(fraccion: float) -> float:
    """Inversa de pct_1rm: reps hasta el fallo a esa fraccion del 1RM."""
    if fraccion >= 1.0:
        return max(0.0, 1.0 - (fraccion - 1.0) * 10)
    lo, hi = 1.0, 80.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if pct_1rm(mid) > fraccion:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def e1rm(peso: float, reps: float, rpe: float | None, sesgo: float = SESGO_POR_DEFECTO) -> float | None:
    """1RM estimado de una serie. sesgo = reps que el usuario se deja SIN contar."""
    if not peso or peso <= 0 or not reps or reps <= 0:
        return None
    rir = (10 - rpe) if rpe is not None and not pd.isna(rpe) else 2.0
    rir = max(0.0, rir) + (sesgo if rir > 0 else 0.0)   # al fallo no hay sesgo posible
    return peso / pct_1rm(reps + rir)


def carga_para(e1rm_: float, reps: float, rpe: float, sesgo: float = SESGO_POR_DEFECTO) -> float:
    """Carga con la que, segun el modelo, se llega a `reps` al RPE `rpe`
    (lo que el usuario PERCIBE: su sesgo se suma a las reps reales que le quedan)."""
    rir = max(0.0, 10 - rpe) + (sesgo if rpe < 10 else 0.0)
    return e1rm_ * pct_1rm(reps + rir)


@dataclass
class Estado:
    """Lo que el modelo sabe de un ejercicio."""
    tendencia: float            # e1RM suavizado (con desentrenamiento aplicado)
    ultima: float               # e1RM de la ultima sesion
    sesiones: int
    ultima_fecha: date
    residuos: list[float]       # rendimiento de cada sesion vs la tendencia previa (0.97 = -3%)
    rir_ultima: float | None    # reps que sobraron en la ultima sesion (estimado)
    estancado: bool
    ultima_exigente: bool = True  # la ultima sesion tuvo series a RPE >= 8


def _rpe_informativo(df: pd.DataFrame) -> bool:
    """False si casi todas las series tienen el MISMO RPE (no se esta registrando)."""
    rpe = pd.to_numeric(df.get("rpe"), errors="coerce").dropna().tail(80)
    if len(rpe) < 12:
        return True
    return float(rpe.value_counts(normalize=True).iloc[0]) < 0.85


def _es_al_fallo(tecnica) -> bool:
    t = str(tecnica or "").lower()
    return any(k in t for k in ("amrap", "rest", "drop"))


class ModeloFuerza:
    """Estado de fuerza por ejercicio a partir del historial."""

    def __init__(self, df: pd.DataFrame, hoy: date):
        from ejercicios_db import nombre_canonico
        self.hoy = hoy
        self.estados: dict[str, Estado] = {}
        self.sesgo = SESGO_POR_DEFECTO
        self.rpe_ok = True
        if df is None or df.empty or "ejercicio" not in df:
            return
        from planificar import sanear_historial   # typos, pseudo-ejercicios, RPE fuera de rango
        d = sanear_historial(df).copy()
        if d.empty:
            return
        d["peso_kg"] = pd.to_numeric(d["peso_kg"], errors="coerce")
        d["reps_hechas"] = pd.to_numeric(d["reps_hechas"], errors="coerce")
        d["rpe"] = pd.to_numeric(d.get("rpe"), errors="coerce")
        d = d[(d["peso_kg"] > 0) & (d["reps_hechas"] > 0) & d["fecha_entreno"].notna()]
        d = d[d["fecha_entreno"] < pd.Timestamp(hoy)]
        if d.empty:
            return
        d["k"] = d["ejercicio"].map(lambda x: str(nombre_canonico(x)).strip().lower())
        self.rpe_ok = _rpe_informativo(d)
        self.sesgo = SESGO_POR_DEFECTO
        for k, g in d.groupby("k"):
            est = self._estado(g)
            if est:
                self.estados[k] = est

    # ── estado por ejercicio ──────────────────────────────────────────────────
    def _estado(self, g: pd.DataFrame) -> Estado | None:
        sesiones = []
        for fecha, s in g.groupby("fecha_entreno"):
            vals = []
            rirs = []
            exigente = False      # alguna serie a RPE >= 8: la sesion SI mide rendimiento
            for _, r in s.iterrows():
                reps = min(float(r["reps_hechas"]), REPS_MAX_FIABLES)
                if _es_al_fallo(r.get("tecnica")) and s["numero_serie"].max() == r.get("numero_serie") \
                        and len(s) > 1:
                    rpe = 10.0                    # la ultima serie al fallo: RIR 0 por definicion
                elif self.rpe_ok:
                    rpe = r["rpe"] if not pd.isna(r["rpe"]) else None
                else:
                    rpe = None                    # RPE que no informa: se asume RIR 2
                # RPE < 6: se estima como RPE 6 (al menos 4 en reserva) -> cota inferior
                v = e1rm(float(r["peso_kg"]), reps, max(6.0, rpe) if rpe is not None else None, self.sesgo)
                if v:
                    vals.append(v)
                    exigente = exigente or (rpe is not None and rpe >= 8)
                    if rpe is not None and rpe < 10:
                        rirs.append(10 - rpe + self.sesgo)
            if vals:
                # la MEJOR serie: la mas cercana al fallo es la que mejor estima el
                # 1RM; las demas llevan fatiga encima. El ruido lo suaviza la EWMA.
                sesiones.append((fecha.date(), max(vals), min(rirs) if rirs else None, exigente))
        if not sesiones:
            return None
        tendencia = sesiones[0][1]
        residuos = []
        for _, v, _, exigente in sesiones[1:]:
            # solo una sesion EXIGENTE mide el rendimiento: en un deload (o una
            # sesion suave) las series lejos del fallo dan una cota inferior y
            # parecerian una "caida" -> deload encadenado tras deload (simulador)
            if exigente:
                residuos.append(v / tendencia)
            # la tendencia no baja por una sesion suave (solo cota inferior)
            if exigente or v > tendencia:
                tendencia = ALFA_EWMA * v + (1 - ALFA_EWMA) * tendencia
        ultima_fecha = sesiones[-1][0]
        semanas_sin = (self.hoy - ultima_fecha).days / 7
        if semanas_sin > DESENTRENO_SEMANAS:
            tendencia *= max(0.85, 1 - DESENTRENO_POR_SEMANA * (semanas_sin - DESENTRENO_SEMANAS))
        # estancamiento real: lo mejor de las sesiones de las ultimas 3 semanas no
        # supera en 1% lo mejor de antes (con al menos 3 sesiones en ese tramo)
        corte = self.hoy - timedelta(days=21)
        recientes = [v for f, v, _, _ in sesiones if f >= corte]
        previas = [v for f, v, _, _ in sesiones if f < corte]
        estancado = len(recientes) >= 3 and bool(previas) and max(recientes) <= max(previas) * 1.01
        return Estado(tendencia=tendencia, ultima=sesiones[-1][1], sesiones=len(sesiones),
                      ultima_fecha=ultima_fecha, residuos=residuos,
                      rir_ultima=sesiones[-1][2], estancado=estancado,
                      ultima_exigente=sesiones[-1][3])

    def necesita_calibrar(self, ejercicio: str) -> bool:
        """El modelo no sabe bien tu fuerza aqui: nunca lo hiciste, o la ultima
        vez te sobraban 5+ reps (el RPE solo dio una cota inferior)."""
        if not self.rpe_ok:
            return False
        est = self.estado(ejercicio)
        return est is None or (est.rir_ultima is not None and est.rir_ultima >= RIR_FACIL)

    def estado(self, ejercicio: str) -> Estado | None:
        from ejercicios_db import nombre_canonico
        return self.estados.get(str(nombre_canonico(ejercicio)).strip().lower())

    # ── prescripcion ─────────────────────────────────────────────────────────
    def carga(self, ejercicio: str, reps_obj: int, rpe_obj: float, ultimo_peso: float | None,
              paso: float, minimo: float = 0.0, bajada_max: float = BAJADA_MAX,
              abajo=None) -> tuple[float, str] | None:
        """Carga sugerida para hacer `reps_obj` al RPE `rpe_obj`, limitada respecto
        a la ultima carga usada. None si el modelo no tiene datos (o el RPE no
        informa): entonces manda la doble progresion clasica."""
        est = self.estado(ejercicio)
        if est is None or not self.rpe_ok:
            return None
        objetivo = carga_para(est.tendencia, reps_obj, rpe_obj, self.sesgo)
        motivo = f"e1RM ~{est.tendencia:.0f} kg"
        if ultimo_peso and ultimo_peso > 0:
            facil = est.rir_ultima is not None and est.rir_ultima >= RIR_FACIL
            if facil:
                # SONDEO: con 5+ reps de sobra el RPE solo da una cota inferior (la
                # misma cada semana si siempre hace las mismas reps faciles) y el
                # modelo no puede saber cuanto mas aguanta. Un entrenador sube un
                # escalon grande y mira que pasa.
                objetivo = max(objetivo, ultimo_peso * (1 + SUBIDA_MAX_FACIL))
                motivo += ", te sobraban 5+ reps"
            # cuanto se puede subir depende de lo FIABLE que sea el dato: una serie
            # cerca del fallo (p. ej. la de calibracion) dice la verdad (Zourdos
            # 2016: el RPE es mas preciso cerca del fallo) -> se salta al peso
            # correcto; una cota inferior solo permite sondear
            fiable = est.rir_ultima is not None and est.rir_ultima <= RIR_FIABLE
            techo = ultimo_peso * (1 + (SUBIDA_MAX_FIABLE if fiable else
                                        SUBIDA_MAX_FACIL if facil else SUBIDA_MAX))
            suelo = ultimo_peso * (1 - bajada_max)
            if objetivo > techo:
                objetivo, motivo = techo, motivo + (", subida grande limitada" if facil else ", subida limitada")
            elif objetivo < suelo:
                objetivo, motivo = suelo, motivo + ", bajada limitada"
        # redondeo a lo cargable: hacia abajo (mejor quedarse corto que fallar).
        # `abajo` sabe que pesos existen (p. ej. la lista de mancuernas del gym,
        # que no va a saltos iguales); sin el, multiplos de `paso`.
        def _abajo(x: float) -> float:
            return abajo(x) if abajo else max(minimo, math.floor(x / paso + 1e-9) * paso)
        peso = max(minimo, _abajo(objetivo))
        # ...salvo que el redondeo rompa el limite de bajada (60 -> 50 es -17%):
        # entonces el siguiente cargable por debajo del ultimo, que siempre se
        # permite (con escalones grandes el limite dejaba el peso clavado para
        # siempre en uno imposible: simulador, 30 kg y 2 reps semana tras semana)
        if ultimo_peso and ultimo_peso > 0 and peso < ultimo_peso * (1 - bajada_max) - 1e-9:
            suelo = ultimo_peso * (1 - bajada_max)
            # el cargable mas bajo que respeta el limite (bajando de uno en uno)...
            x = ultimo_peso
            for _ in range(50):
                y = _abajo(x - 1e-3)
                if y >= x - 1e-9 or y < suelo - 1e-9:
                    break
                x = y
            # ...y si ni uno cabe en el limite, un escalon por debajo del ultimo
            peso = x if x < ultimo_peso - 1e-9 else max(minimo, _abajo(ultimo_peso - 1e-3))
        return (round(peso, 2), motivo) if peso > 0 else None

    # ── fatiga y estancamiento ───────────────────────────────────────────────
    def fatiga_por_rendimiento(self, dias: int = 8, umbral: float = 0.96, min_ejercicios: int = 4) -> bool:
        """Mitad o mas de los ejercicios de la ULTIMA semana rindiendo 4%+ por
        debajo de su tendencia = fatiga acumulada, no un mal dia suelto. Solo la
        ultima semana: si fue un deload, no hay evidencia nueva y no se encadena
        otro con los mismos datos (simulador: 2 deloads seguidos)."""
        corte = self.hoy - timedelta(days=dias)
        rec = [e for e in self.estados.values()
               if e.ultima_fecha >= corte and e.residuos and e.ultima_exigente]
        if len(rec) < min_ejercicios:
            return False
        abajo = sum(1 for e in rec if e.residuos[-1] < umbral)
        return abajo / len(rec) >= 0.5

    def estancados(self) -> set[str]:
        return {k for k, e in self.estados.items() if e.estancado}

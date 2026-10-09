"""Atleta virtual ("gemelo digital") para evaluar al motor COMO ENTRENADOR.

Las pruebas unitarias comprueban reglas sueltas; esto comprueba el resultado:
se le da al motor un atleta simulado, el motor le prescribe semana a semana, el
atleta "entrena" lo prescrito (con su fuerza real, su fatiga y su forma de
reportar el RPE) y el historial resultante vuelve al motor. Despues de N semanas
se mide lo que mediria un entrenador: si progreso, si las cargas eran posibles,
si eran demasiado faciles, si los saltos eran seguros y si supo reaccionar a la
fatiga y a las pausas.

Modelo del atleta (simple a proposito, cada pieza con su porque):
  - Fuerza real (1RM) por ejercicio. Repeticiones posibles a una carga: curva
    %1RM-reps de la tabla RTS (Tuchscherer; Helms et al. 2016), la misma que
    usa el motor: el modelo no le da ventaja al motor porque lo que el motor ve
    es el RPE REPORTADO, con ruido y sesgo, no la fuerza real.
  - Reporte de RPE: RIR real + sesgo + ruido. Halperin et al. (2022): la gente
    infravalora las reps que le quedan en ~1 rep (sesgo +1 en RPE).
  - Ganancia semanal con rendimientos decrecientes hacia un techo y dosis-
    respuesta por series duras (RIR <= 4; Refalo 2023, Robinson 2024).
  - Fatiga global que se acumula con las series duras y se disipa (~0.6/semana).
  - Desentrenamiento: sin perdida hasta 4 semanas, luego ~1%/semana (Bosquet 2013).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

import ejercicios_db as db

# %1RM para N repeticiones al fallo (RPE 10), tabla RTS. Indice 0 = 1 rep.
RTS_FALLO = [1.000, 0.955, 0.922, 0.892, 0.863, 0.837, 0.811, 0.786, 0.762, 0.739, 0.707, 0.680]


def pct_1rm(reps_al_fallo: float) -> float:
    """Fraccion del 1RM con la que se llega al fallo en `reps_al_fallo` reps.
    Tabla RTS de 1 a 12; de ahi en adelante, Epley escalado para empalmar."""
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
        return 1.0 if fraccion <= 1.0 else max(0.0, 1.0 - (fraccion - 1.0) * 10)
    lo, hi = 1.0, 60.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if pct_1rm(mid) > fraccion:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass
class Perfil:
    nombre: str
    nivel: float = 1.0               # fuerza relativa (0.7 principiante, 1.0 intermedio)
    ganancia: float = 0.006          # ganancia semanal maxima (fraccion del 1RM)
    techo: float = 1.30              # techo de fuerza respecto al inicial
    ruido_rpe: float = 0.5           # desviacion del RPE reportado
    sesgo_rpe: float = 1.0           # +1 = reporta 1 punto MAS de lo real (Halperin 2022)
    rpe_fijo: int | None = None      # siempre reporta este RPE (deja el 8 por defecto de la app)
    pausas: tuple = ()               # (semana_inicio, semanas) sin entrenar
    estres: dict = field(default_factory=dict)  # semana -> factor de rendimiento (0.9 = -10%)
    adherencia: float = 1.0          # probabilidad de ir a cada dia de gym
    arranque: float = 0.65           # sin peso sugerido, elige esta fraccion de su 1RM


def _fuerza_inicial(e: db.Ejercicio, rng: random.Random, nivel: float) -> float:
    """1RM verosimil de un intermedio de ~73 kg (peso TOTAL en mancuernas)."""
    comp = any(b in e.bloques for b in ("A", "B"))
    if e.equipo == "peso_corporal":
        return 0.0
    if e.equipo == "barra":
        if "EZ" in e.nombre or not comp:
            base = 40
        else:
            base = {db.DOMINANTE_CADERA: 120, db.DOMINANTE_RODILLA: 95, db.EMPUJE_HORIZONTAL: 75,
                    db.EMPUJE_VERTICAL: 50, db.TIRON_HORIZONTAL: 75}.get(e.patron, 70)
    elif e.equipo == "mancuerna":
        una = "1 mano" in e.nombre.lower()
        base = (32 if una else 55) if comp else (14 if una else 22)
    elif e.equipo == "maquina":
        base = (180 if "prensa" in e.nombre.lower() else 100) if comp else 55
    else:  # polea
        base = 70 if comp else 32
    return base * nivel * math.exp(rng.gauss(0, 0.12))


class Atleta:
    def __init__(self, perfil: Perfil, semilla: int = 1):
        self.p = perfil
        self.rng = random.Random(semilla)
        self.fuerza: dict[str, float] = {}       # 1RM real por ejercicio (canonico)
        self.max_reps: dict[str, float] = {}     # peso corporal: reps maximas reales
        self.inicial: dict[str, float] = {}
        self.ultimo_entreno: dict[str, int] = {}  # ejercicio -> semana
        self.fuerza_al_dejarlo: dict[str, float] = {}  # 1RM la ultima vez que se entreno
        self.fatiga = 0.0
        self.registros: list[dict] = []          # metricas por serie (para evaluar)

    def _alta(self, nombre: str) -> None:
        if nombre in self.fuerza or nombre in self.max_reps:
            return
        e = {x.nombre: x for x in db.EJERCICIOS}.get(nombre)
        if e is None or e.equipo == "peso_corporal":
            self.max_reps[nombre] = 12 * self.p.nivel * math.exp(self.rng.gauss(0, 0.15))
            return
        f = _fuerza_inicial(e, self.rng, self.p.nivel)
        self.fuerza[nombre] = f
        self.inicial[nombre] = f

    def _paso(self, nombre: str, peso: float | None = None) -> float:
        import planificar as pl
        return pl.paso_carga(nombre, peso)

    def entrenar_semana(self, filas: list[dict], lunes: date, semana_idx: int, adaptar: bool = True) -> list[dict]:
        """Hace la semana prescrita. Devuelve filas de historial (formato del CSV).
        adaptar=False: acumula y espera a cerrar_semana (modo dia a dia)."""
        en_pausa = any(ini <= semana_idx < ini + n for ini, n in self.p.pausas)
        factor_dia = self.p.estres.get(semana_idx, 1.0)
        historial: list[dict] = []
        duras = self._duras = getattr(self, "_duras", None) or {}
        total_duras = 0
        por_dia: dict[int, list[dict]] = {}
        for f in filas:
            if f.get("tecnica") and (f.get("bloque") or "")[:4] in ("A - ", "B - ", "C - "):
                por_dia.setdefault(int(f["dia_semana"]), []).append(f)
        for dia, fd in sorted(por_dia.items()):
            if en_pausa or self.rng.random() > self.p.adherencia:
                continue
            fecha = lunes + timedelta(days=dia - 1)
            for f in fd:
                nombre = db.nombre_canonico(f["ejercicio"])
                self._alta(nombre)
                n_series = max(1, int(round(float(f["series_objetivo"] or 1))))
                rmin = int(f["reps_min"] or 8)
                rmax = int(f["reps_max"] or rmin)
                tec = (f["tecnica"] or "").lower()
                al_fallo_ult = any(k in tec for k in ("amrap", "rest", "drop"))
                calibrar = "CALIBRAR" in (f.get("notas") or "")
                rpe_obj = 8.5 if "top set" in tec else 8.0
                for i in range(n_series):
                    ult = i == n_series - 1
                    perf = (1 - self.fatiga) * factor_dia
                    if nombre in self.max_reps:      # peso corporal: reps
                        rtf = self.max_reps[nombre] * perf - 0.8 * i
                        carga = 0.0
                    else:
                        carga = f.get("peso_sugerido")
                        if not carga:
                            # sin sugerencia el atleta elige conservador y redondea
                            objetivo = self.fuerza[nombre] * self.p.arranque
                            paso = self._paso(nombre, objetivo)
                            carga = max(paso, math.floor(objetivo / paso) * paso)
                        carga = float(carga)
                        rtf = reps_al_fallo(carga / (self.fuerza[nombre] * perf)) - 0.7 * i
                    rtf = max(0.0, rtf)
                    if al_fallo_ult and ult:
                        reps = int(math.floor(rtf))
                    elif calibrar and ult:
                        # todas las reps que pueda dejando 1-2 (con su sesgo, deja algo mas)
                        reps = int(math.floor(rtf - 1.5 - max(0.0, self.p.sesgo_rpe)))
                    else:
                        # para donde CREE que le quedan rir_obj reps; con el sesgo de
                        # Halperin (cree tener menos de las que tiene) para antes
                        rir_obj = 10 - rpe_obj
                        reps = min(rmax, int(math.floor(rtf - rir_obj - max(0.0, self.p.sesgo_rpe))))
                        if reps < rmin:      # aprieta hasta el minimo si le da
                            reps = min(rmin, int(math.floor(rtf)))
                    reps = max(1, reps) if rtf >= 1 else 0
                    rir_real = rtf - reps
                    rpe_rep = None
                    if self.p.rpe_fijo is not None:
                        rpe = self.p.rpe_fijo
                    else:
                        # RIR percibido = real - sesgo -> RPE reportado
                        rpe = int(round(10 - (rir_real - self.p.sesgo_rpe) + self.rng.gauss(0, self.p.ruido_rpe)))
                        rpe = max(5, min(10, rpe))
                    # la APP corrige las series siguientes segun el RPE (ajusteIntraSesion)
                    if carga > 0 and not (al_fallo_ult and ult) and not any(k in tec for k in ("amrap", "drop", "rest")):
                        rpe_max = 9 if "top set" in tec else 8
                        paso = self._paso(nombre, carga)
                        n_saltos = lambda fr: max(1, round(carga * fr / paso))
                        if rpe <= rpe_max - 2 and reps >= rmax:
                            f = dict(f, peso_sugerido=carga + n_saltos(0.05) * paso)
                        elif (rpe >= 10 and reps < rmin) or rpe >= rpe_max + 2:
                            f = dict(f, peso_sugerido=max(paso, carga - n_saltos(0.1 if reps < rmin else 0.05) * paso))
                    historial.append({
                        "fecha_entreno": pd.Timestamp(fecha), "ejercicio": f["ejercicio"],
                        "tecnica": f["tecnica"], "numero_serie": i + 1, "peso_kg": carga,
                        "reps_hechas": reps, "rpe": rpe, "tonelaje_serie": carga * reps,
                        "bloque": f["bloque"],
                    })
                    self.registros.append({
                        "semana": semana_idx, "ejercicio": nombre, "carga": carga, "reps": reps,
                        "rmin": rmin, "rmax": rmax, "rtf": rtf, "rir": rir_real,
                        "al_fallo": al_fallo_ult and ult, "corporal": nombre in self.max_reps,
                        "tecnica": tec,
                    })
                    if rir_real <= 4 and reps > 0:
                        duras[nombre] = duras.get(nombre, 0) + 1
                        total_duras += 1
                        self._total_duras = getattr(self, "_total_duras", 0) + 1
                self.ultimo_entreno[nombre] = semana_idx
        if adaptar:
            self.cerrar_semana(semana_idx)
        return historial

    def cerrar_semana(self, semana_idx: int) -> None:
        self._adaptar(getattr(self, "_duras", None) or {}, getattr(self, "_total_duras", 0), semana_idx)
        self._duras, self._total_duras = {}, 0

    def _adaptar(self, duras: dict[str, int], total_duras: int, semana_idx: int) -> None:
        g = self.p.ganancia
        for nombre, h in duras.items():
            dosis = 1 - math.exp(-h / 3)
            if nombre in self.fuerza:
                # 1 al empezar, 0 al llegar al techo (rendimientos decrecientes)
                margen = max(0.0, 1 - (self.fuerza[nombre] / self.inicial[nombre] - 1) / (self.p.techo - 1))
                self.fuerza[nombre] *= 1 + g * dosis * margen
            else:
                self.max_reps[nombre] *= 1 + g * 1.5 * dosis
        for nombre in duras:
            if nombre in self.fuerza:
                self.fuerza_al_dejarlo[nombre] = self.fuerza[nombre]
        # desentrenamiento: nada hasta 4 semanas sin hacerlo, luego ~1%/semana
        for nombre in self.fuerza:
            sin = semana_idx - self.ultimo_entreno.get(nombre, semana_idx)
            if sin > 4:
                self.fuerza[nombre] *= 0.99
        # fatiga global: se acumula con las series duras y se disipa
        self.fatiga = max(0.0, min(0.25, 0.6 * self.fatiga + 0.00027 * total_duras))


def simular(perfil: Perfil, semanas: int = 20, semilla: int = 1, config: dict | None = None,
            inicio: date = date(2026, 1, 5), diario: bool = False) -> dict:
    """Corre el motor contra el atleta. Devuelve metricas de entrenador."""
    import planificar as pl
    from generador import generar_plan

    cfg = config or {"enfoque": "hipertrofia", "split": "upper_lower", "prioridades": [],
                     "duracion_min": 90}
    atleta = Atleta(perfil, semilla)
    hist = pd.DataFrame()
    semanas_info = []
    prescripciones: dict[str, list[tuple[int, float]]] = {}
    saltos_reales: list[float] = []
    for w in range(semanas):
        lunes = inicio + timedelta(weeks=w)
        semana, reingreso, avisos = pl.decidir_semana(hist, lunes, inicio)
        plan = generar_plan(cfg, ciclo=w // 5)
        filas = pl.generar_filas(hist, lunes.isoformat(), semana, plan=plan, reingreso=reingreso,
                                 duracion_min=cfg.get("duracion_min", 90))
        # lo que se LEVANTO la ultima vez por ejercicio y tecnica (la app puede
        # haberlo subido o bajado dentro de la sesion)
        levantado = {}
        if not hist.empty:
            for (ej, tec), g in hist.groupby(["ejercicio", "tecnica"]):
                ult = g[g["fecha_entreno"] == g["fecha_entreno"].max()]
                levantado[(ej, tec)] = float(ult["peso_kg"].max())
        for f in filas:
            k = (f["ejercicio"], f["tecnica"])
            if f.get("peso_sugerido") and k in levantado and levantado[k] > 0 and semana != 5 and not reingreso:
                antes, ahora = levantado[k], float(f["peso_sugerido"])
                escalon = pl.paso_carga(f["ejercicio"], antes)
                if ahora - antes > escalon + 1e-6:      # mas de UN escalon minimo
                    saltos_reales.append(ahora / antes - 1)
                else:
                    saltos_reales.append(0.0)
        if diario:
            # el entrenador re-prescribe CADA dia con lo que paso en los anteriores
            nuevas = []
            for dia in sorted({int(f["dia_semana"]) for f in filas}):
                hoy = lunes + timedelta(days=dia - 1)
                h = hist if not nuevas else (pd.DataFrame(nuevas) if hist.empty else
                                             pd.concat([hist, pd.DataFrame(nuevas)], ignore_index=True))
                del_dia = [f for f in pl.generar_filas(h, lunes.isoformat(), semana, plan=plan,
                                                       reingreso=reingreso, duracion_min=cfg.get("duracion_min", 90),
                                                       hoy=hoy) if int(f["dia_semana"]) == dia]
                nuevas += atleta.entrenar_semana(del_dia, lunes, w, adaptar=False)
            atleta.cerrar_semana(w)
        else:
            nuevas = atleta.entrenar_semana(filas, lunes, w)
        semanas_info.append({"semana": w, "meso": semana, "reingreso": reingreso,
                             "avisos": avisos, "fatiga": atleta.fatiga, "sesiones": len({r["fecha_entreno"] for r in nuevas})})
        if nuevas:
            hist = pd.DataFrame(nuevas) if hist.empty else pd.concat([hist, pd.DataFrame(nuevas)], ignore_index=True)
    return evaluar(atleta, semanas_info, saltos_reales)


def evaluar(atleta: Atleta, semanas_info: list[dict], saltos: list[float]) -> dict:
    reg = pd.DataFrame(atleta.registros)
    con_carga = reg[(~reg["corporal"]) & (~reg["al_fallo"]) & (reg["carga"] > 0)] if not reg.empty else reg
    # imposible: ni yendo al fallo llega al minimo del rango
    imposible = float((con_carga["rtf"] < con_carga["rmin"]).mean()) if len(con_carga) else 0.0
    # demasiado facil: completa el rango y le quedan 5+ reps (RIR >= 5 en el tope)
    facil = float(((con_carga["reps"] >= con_carga["rmax"]) & (con_carga["rir"] >= 5)).mean()) if len(con_carga) else 0.0
    # en zona: dentro del rango y con 0-4 reps en reserva (estimulo efectivo)
    zona = float(((con_carga["reps"] >= con_carga["rmin"]) & (con_carga["rir"] <= 4)).mean()) if len(con_carga) else 0.0
    # ganancia de fuerza real media (ejercicios con carga que se entrenaron)
    # ganancia de los ejercicios que se entrenaron de verdad (8+ semanas): lo que
    # el plan roto tras unas pocas semanas mide la rotacion, no al entrenador
    sem_por_ej = reg.groupby("ejercicio")["semana"].nunique() if not reg.empty else {}
    gan = [atleta.fuerza_al_dejarlo.get(n, atleta.fuerza[n]) / atleta.inicial[n] - 1 for n in atleta.fuerza
           if n in sem_por_ej and sem_por_ej[n] >= 8]
    # saltos: carga prescrita vs la que SE LEVANTO la ultima vez (sin deload ni
    # reingreso); subir un solo escalon minimo no cuenta (de 8 a 10 kg en unas
    # laterales es +25% y no hay forma mas fina de subir)
    # estimulo: series EFECTIVAS por semana (dentro del rango y a 0-4 del fallo)
    n_sem = max(1, len(semanas_info))
    efectivas = float(((con_carga["reps"] >= con_carga["rmin"]) & (con_carga["rir"] <= 4)).sum()) / n_sem         if len(con_carga) else 0.0
    return {
        "ganancia_fuerza": sum(gan) / len(gan) if gan else 0.0,
        "efectivas_semana": efectivas,
        "series_imposibles": imposible,
        "series_demasiado_faciles": facil,
        "series_en_zona": zona,
        "salto_max": max(saltos) if saltos else 0.0,
        "saltos_mayores_10": float(sum(s > 0.10 for s in saltos) / len(saltos)) if saltos else 0.0,
        # >20% de una semana a otra no lo haria ningun entrenador (el sondeo es +15%)
        "saltos_mayores_20": float(sum(s > 0.20 for s in saltos) / len(saltos)) if saltos else 0.0,
        "semanas": semanas_info,
        "fatiga_final": atleta.fatiga,
    }


# Perfiles de prueba: cada uno es una forma tipica de que un plan falle
PERFILES = {
    "intermedio":       Perfil("intermedio"),
    "principiante":     Perfil("principiante", nivel=0.7, ganancia=0.015, techo=1.6),
    "rpe_ruidoso":      Perfil("rpe_ruidoso", ruido_rpe=1.5),
    "sin_sesgo":        Perfil("sin_sesgo", sesgo_rpe=0.0),
    "rpe_siempre_8":    Perfil("rpe_siempre_8", rpe_fijo=8),
    "subestimado":      Perfil("subestimado", arranque=0.45),          # empieza MUY por debajo
    "vacaciones":       Perfil("vacaciones", pausas=((8, 3),)),
    "estres":           Perfil("estres", estres={w: 0.88 for w in range(6, 10)}),
    "irregular":        Perfil("irregular", adherencia=0.6),
}


if __name__ == "__main__":
    import sys
    nombres = sys.argv[1:] or list(PERFILES)
    for n in nombres:
        r = simular(PERFILES[n], semanas=20)
        print(f"{n:15} fuerza {r['ganancia_fuerza']:+6.1%} | efect/sem {r['efectivas_semana']:4.1f} | imposibles {r['series_imposibles']:5.1%} | "
              f"faciles {r['series_demasiado_faciles']:5.1%} | en zona {r['series_en_zona']:5.1%} | "
              f"salto max {r['salto_max']:5.1%} (>20%: {r['saltos_mayores_20']:4.1%})")

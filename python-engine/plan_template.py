"""La unidad del plan: una `Fila` = un ejercicio con su tecnica en un dia.

El plan lo construye generador.py a partir de config_usuario.json (enfoque +
split + prioridades) y planificar.py le pone pesos. Aqui vivia ademas `PLAN`, la
plantilla fija del enfoque Recomposicion original; nadie la usaba desde el
generador dinamico y se elimino (sigue en el historial de git).

Campo semanas: tuple con los numeros de semana en que aparece la fila
(None = todas las semanas del ciclo S1-S4; el deload se maneja en el motor).
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

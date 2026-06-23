"""Punto de entrada semanal: exporta el historial y recalcula la rutina.
Pensado para el Programador de tareas de Windows. Registra en motor.log.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys

import exportar_local
import planificar

LOG = pathlib.Path(__file__).resolve().parent / "motor.log"


def registrar(mensaje: str) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(mensaje + "\n")


def main() -> None:
    registrar(f"===== {dt.datetime.now():%Y-%m-%d %H:%M:%S} =====")
    try:
        exportar_local.main()
        planificar.main()
        registrar("OK")
    except Exception as e:  # noqa: BLE001
        registrar(f"ERROR: {e!r}")
        sys.exit(1)


if __name__ == "__main__":
    main()

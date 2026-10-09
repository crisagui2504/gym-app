"""Configuracion del usuario, persistida en config_usuario.json.

Esto es lo que hace la app "permanente": el enfoque elegido desde el dashboard
se guarda en disco y tanto el dashboard como planificar.py lo leen al arrancar.
"""
from __future__ import annotations

import json
import pathlib

CONFIG_PATH = pathlib.Path(__file__).resolve().parent / "config_usuario.json"

DEFAULT_CONFIG: dict = {
    "enfoque": "recomposicion",
    "split": "upper_lower",
    "prioridades": ["hombros", "cuadriceps"],
    "peso_corporal": 75,
    "duracion_min": 90,  # 60 | 75 | 90 | 120 -> ajusta cuantos ejercicios por dia
    "tema": "oscuro",    # "oscuro" | "claro"
    "equipo_excluido": [],  # equipo que tu gym NO tiene: "barra" | "mancuerna" | "polea" | "maquina"
    # Deporte fuera del gym (basquet, futbol...). Es un dato de tu semana, no del
    # split, asi que vive aqui. El generador lo pinta como dia propio y NO manda
    # cardio encima: el deporte ya es el acondicionamiento. dias: 1=Lun..7=Dom.
    "deporte": None,     # p.ej. {"nombre": "Basquetbol", "dias": [2, 4], "minutos": 90}
    # Mancuernas que HAY en tu gym (kg de UNA). El motor solo prescribe pesos de
    # esta lista (registrados como la SUMA de las dos). None = de 1 en 1 kg hasta
    # 10 y de 2.5 en 2.5 despues.
    "mancuernas_kg": None,
    # Ejercicios que haces en MAQUINA ASISTIDA: lo que registras es la AYUDA
    # (mas kg = mas facil). El motor trabaja con la carga real (peso corporal -
    # ayuda) y te devuelve la ayuda. p.ej. ["Dominadas", "Fondos en Paralelas"]
    "asistidas": [],
    "paso_asistencia_kg": 5,   # salto de la placa de la maquina asistida
}


def cargar_config() -> dict:
    """Lee la config del disco; completa con defaults los campos faltantes."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass  # config corrupta -> usa defaults
    return cfg


def guardar_config(cfg: dict) -> None:
    """Persiste la config (mezclada con la existente)."""
    actual = cargar_config()
    actual.update(cfg)
    CONFIG_PATH.write_text(json.dumps(actual, indent=2, ensure_ascii=False), encoding="utf-8")

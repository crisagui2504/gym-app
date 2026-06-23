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

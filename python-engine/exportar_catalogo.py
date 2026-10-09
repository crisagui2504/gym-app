"""Genera app/src/app/catalogo.generado.ts con el catalogo de ejercicios del motor.

La app tenia su PROPIA lista de alternativas ("Maquina ocupada") y se habia
desviado del motor: de 214 alternativas, solo 38 existian en ejercicios_db. Lo
que se elegia en el gym se registraba con un nombre que el motor no conoce: sin
progresion, sin estimacion de peso, sin contar volumen. Ahora la app sale de
aqui; test_motor comprueba que el archivo generado este al dia.

Uso:  python exportar_catalogo.py   (tras tocar ejercicios_db.py)
"""
from __future__ import annotations

import json
import pathlib

import ejercicios_db as db

DESTINO = pathlib.Path(__file__).resolve().parents[1] / "app" / "src" / "app" / "catalogo.generado.ts"


def contenido() -> str:
    items = [{"nombre": e.nombre, "patron": e.patron, "musculo": e.musculo, "equipo": e.equipo,
              "bloques": "".join(e.bloques), "pref": e.pref} for e in db.EJERCICIOS]
    filas = ",\n".join("  " + json.dumps(i, ensure_ascii=False) for i in items)
    return ("// GENERADO por python-engine/exportar_catalogo.py desde ejercicios_db.py.\n"
            "// NO editar a mano: cambia ejercicios_db.py y vuelve a correr el script.\n"
            "export interface EjercicioMotor {\n"
            "  nombre: string;\n  patron: string;\n  musculo: string;\n  equipo: string;\n"
            "  bloques: string;\n  pref: number;\n}\n\n"
            f"export const CATALOGO_MOTOR: EjercicioMotor[] = [\n{filas}\n];\n")


if __name__ == "__main__":
    DESTINO.write_text(contenido(), encoding="utf-8")
    print(f"{DESTINO.name}: {len(db.EJERCICIOS)} ejercicios")

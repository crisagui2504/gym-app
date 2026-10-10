"""Respaldo de la demo que la app lleva DENTRO (por si la VM no responde).

La demo normal pide sus datos a la API publica del dashboard
(/demo/api/escenario), que genera con demo_motor.py cualquier tipo de entreno.
Si la VM esta apagada, la app usa este escenario fijo (la config por defecto
de la demo): las 5 semanas del mesociclo y el ultimo mes de historial, mas la
lista de enfoques/splits para los selectores.

Las fechas van como "dias antes del lunes de la semana de demo": la app las
coloca relativas a HOY, asi la demo nunca envejece.

Genera:  app/src/app/demo.generado.ts
Uso:     python exportar_demo.py
"""
from __future__ import annotations

import json
import pathlib

import demo_motor

AQUI = pathlib.Path(__file__).resolve().parent
DESTINO_TS = AQUI.parent / "app" / "src" / "app" / "demo.generado.ts"


def generar() -> str:
    esc = demo_motor.para_app({})
    return ("// GENERADO por python-engine/exportar_demo.py (demo_motor.py, atleta virtual).\n"
            "// Datos de DEMOSTRACION: nada de esto es tuyo. NO editar a mano.\n"
            f"export const DEMO_OPCIONES: any = {json.dumps(demo_motor.opciones(), ensure_ascii=False)};\n\n"
            f"export const DEMO_ESCENARIO: any = {json.dumps(esc, ensure_ascii=False)};\n\n"
            f"export const DEMO_MENU: any = {json.dumps(menu_demo(), ensure_ascii=False)};\n")


def menu_demo() -> dict:
    """Menu del atleta virtual (75 kg, recomposicion) con precios de REFERENCIA:
    tus precios propios nunca entran a la demo."""
    import alimentos_mx as alx
    import menu
    from datetime import date
    return menu.generar_menu({"enfoque": "recomposicion", "peso_corporal": 75}, date(2026, 1, 5), semilla=1,
                             precios={a.id: a.precio_kg for a in alx.ALIMENTOS.values()})


if __name__ == "__main__":
    ts = generar()
    DESTINO_TS.write_text(ts, encoding="utf-8")
    viejo = AQUI / "demo_historial.csv"          # ya no se usa (el dashboard genera al vuelo)
    if viejo.exists():
        viejo.unlink()
    print(f"{DESTINO_TS.name}: {len(ts.encode()) // 1024} KB")

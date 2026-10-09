"""Recordatorio diario: si hoy toca gym y todavia no registraste el entreno.

Corre cada hora en la VM (gymtracker-recordatorio.timer) y solo actua a la hora
de config_usuario.json -> "recordatorio_hora" (por defecto 18 = 6 pm, hora de
Mexico). Asi la hora se cambia en la config sin volver a desplegar nada.
No avisa en descanso ni en dias de deporte, ni dos veces el mismo dia.

Limite conocido: si moviste el descanso desde la app (📅), ese cambio vive en
el telefono y aqui no se ve: el aviso sigue el plan original.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date, datetime

AQUI = pathlib.Path(__file__).resolve().parent
ESTADO = AQUI / ".recordatorio_enviado"


def main(ahora: datetime | None = None, forzar: bool = False) -> int:
    from dotenv import load_dotenv
    load_dotenv(AQUI / ".env", override=True)
    from config_usuario import cargar_config

    ahora = ahora or datetime.now()
    hoy = ahora.date()
    hora = int(cargar_config().get("recordatorio_hora", 18) or 18)
    if not forzar and ahora.hour != hora:
        return 0
    if not forzar and ESTADO.exists() and ESTADO.read_text().strip() == hoy.isoformat():
        return 0

    import avisos
    import planificar as pl
    base, token = pl.api_config()
    sesion = pl.sesion_infinityfree(base)
    rutina = sesion.get(f"{base}/get_rutina_hoy.php", params={"fecha": hoy.isoformat()},
                        headers={"X-API-Token": token}, timeout=30).json().get("rutina") or []
    if not debe_avisar(rutina, _series_de_hoy(sesion, base, token, hoy)):
        print("recordatorio: hoy no toca o ya entrenaste")
        return 0
    nombre = rutina[0]["nombre_dia"]
    n = len({f["ejercicio"] for f in rutina})
    avisos.enviar(f"💪 Hoy toca {nombre}", f"{n} ejercicios esperando. Si ya entrenaste, guarda el entreno en la app.",
                  etiqueta="recordatorio")
    ESTADO.write_text(hoy.isoformat())
    return 0


def _series_de_hoy(sesion, base: str, token: str, hoy: date) -> int:
    r = sesion.get(f"{base}/get_historial.php", params={"dias": 1},
                   headers={"X-API-Token": token}, timeout=30)
    return sum(1 for s in r.json().get("series") or [] if str(s.get("fecha_entreno", ""))[:10] == hoy.isoformat())


def debe_avisar(rutina: list[dict], series_hoy: int) -> bool:
    """Solo si hoy hay pesas en el plan y no hay ninguna serie registrada hoy."""
    if not rutina or series_hoy > 0:
        return False
    nombre = str(rutina[0].get("nombre_dia", ""))
    bloques = " ".join(str(f.get("bloque") or "") for f in rutina).lower()
    return "descanso" not in nombre.lower() and "deporte" not in bloques


if __name__ == "__main__":
    sys.exit(main(forzar="--forzar" in sys.argv))

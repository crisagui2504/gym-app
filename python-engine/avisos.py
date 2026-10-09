"""Notificaciones push a la app (Web Push con VAPID).

InfinityFree solo GUARDA las suscripciones (guardar_suscripcion.php); quien
envia es la VM o el PC, que si tienen tareas programadas. Los avisos van por los
servidores de push de Google / Apple / Mozilla, no por InfinityFree.

Claves en .env:  VAPID_PRIVADA (secreta)  y  VAPID_PUBLICA (va en la app).
En iPhone solo llegan con la app INSTALADA en la pantalla de inicio (iOS 16.4+).

Uso manual (prueba):  python avisos.py "Titulo" "Texto"
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlparse


def _claims(base_url: str) -> dict:
    # "sub" es el contacto que ven los servicios de push: la URL del sitio,
    # no un correo personal.
    u = urlparse(base_url)
    return {"sub": f"{u.scheme}://{u.netloc}"}


def enviar(titulo: str, cuerpo: str, url: str = "/", etiqueta: str = "gymtracker") -> int:
    """Envia a todas las suscripciones. Devuelve cuantas llegaron. Nunca lanza:
    un aviso que falla no debe tumbar la generacion de la rutina."""
    try:
        from pywebpush import WebPushException, webpush

        import planificar as pl
    except ImportError as e:
        print(f"avisos: falta una dependencia ({e}); pip install pywebpush")
        return 0
    privada = os.getenv("VAPID_PRIVADA")
    if not privada:
        print("avisos: sin VAPID_PRIVADA en .env, no se envia nada")
        return 0
    try:
        base, token = pl.api_config()
        sesion = pl.sesion_infinityfree(base)
        r = sesion.get(f"{base}/get_suscripciones.php", headers={"X-API-Token": token}, timeout=30)
        r.raise_for_status()
        subs = r.json().get("suscripciones") or []
    except Exception as e:  # noqa: BLE001
        print(f"avisos: no se pudieron leer las suscripciones ({e.__class__.__name__})")
        return 0

    datos = json.dumps({"title": titulo, "body": cuerpo, "url": url, "tag": etiqueta},
                       ensure_ascii=False)
    ok = 0
    for s in subs:
        info = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
        try:
            webpush(subscription_info=info, data=datos, vapid_private_key=privada,
                    vapid_claims=_claims(base), ttl=12 * 3600, timeout=20)
            ok += 1
        except WebPushException as e:
            estado = getattr(e.response, "status_code", None)
            if estado in (404, 410):
                # la suscripcion caduco (se desinstalo la app, se borraron datos...)
                try:
                    sesion.post(f"{base}/guardar_suscripcion.php", headers={"X-API-Token": token},
                                json={"endpoint": s["endpoint"], "baja": True}, timeout=30)
                except Exception:  # noqa: BLE001
                    pass
                print("avisos: suscripcion caducada, dada de baja")
            else:
                print(f"avisos: fallo el envio ({estado})")
        except Exception as e:  # noqa: BLE001
            print(f"avisos: fallo el envio ({e.__class__.__name__})")
    print(f"avisos: {ok}/{len(subs)} enviados")
    return ok


def rutina_lista(lunes) -> int:
    """Aviso de que la rutina de la semana ya esta subida."""
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    cuerpo = f"Semana del {lunes.day} {meses[lunes.month - 1]}. Ábrela para ver qué toca el lunes."
    try:
        import planificar as pl
        base, token = pl.api_config()
        r = pl.sesion_infinityfree(base).get(f"{base}/get_rutina_hoy.php", params={"fecha": lunes.isoformat()},
                                             headers={"X-API-Token": token}, timeout=30)
        filas = r.json().get("rutina") or []
        if filas:
            cuerpo = f"Semana del {lunes.day} {meses[lunes.month - 1]}. Lunes: {filas[0]['nombre_dia']}."
    except Exception:  # noqa: BLE001
        pass
    return enviar("🏋️ Tu rutina de la semana está lista", cuerpo, etiqueta="rutina-semana")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
    titulo = sys.argv[1] if len(sys.argv) > 1 else "GymTracker"
    texto = sys.argv[2] if len(sys.argv) > 2 else "Aviso de prueba: las notificaciones funcionan."
    sys.exit(0 if enviar(titulo, texto, etiqueta="prueba") else 1)

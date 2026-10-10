"""Genera la rutina de la semana SOLO si todavia no esta subida.

Lo usan los tres caminos, en este orden:
  - VM de Azure (principal): domingo 22:00 (gymtracker-motor.timer).
  - Este PC (respaldo): domingo 23:30, o al encenderse si estaba apagado.
  - A mano: generar_rutina_manual.bat, si ninguno de los dos estaba encendido.
En domingo se genera la semana que empieza el lunes; cualquier otro dia, la
semana en curso (planificar.lunes_objetivo). Si la rutina ya esta, no hace nada.

InfinityFree es la unica fuente de la verdad Y el punto de coordinacion: el
respaldo no necesita hablar con la VM para decidir, que es justo lo que hace
falta cuando la VM esta caida. Comprobar antes de generar tambien evita que un
arranque tardio (p.ej. la VM encendida el miercoles) rehaga a media semana una
rutina ya subida con el historial de esos dias.

Registro en respaldo.log. Uso:  python respaldo_semanal.py [--forzar]
"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import subprocess
import sys
from datetime import date, timedelta

AQUI = pathlib.Path(__file__).resolve().parent
LOG = AQUI / "respaldo.log"

# VM principal: desde ella se trae la config mas reciente (el dashboard publico
# vive alli, asi que los cambios de enfoque/split se hacen alli).
VM_HOST = os.getenv("GYM_VM_HOST", "azureuser@20.150.209.104")
VM_CLAVE = pathlib.Path.home() / ".ssh" / "id_gymvm"
VM_CONFIG = "~/gym/python-engine/config_usuario.json"


def registrar(msg: str) -> None:
    linea = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def plan_de_la_semana_subido(lunes: date) -> bool:
    """True si InfinityFree ya tiene la rutina de la semana que empieza en `lunes`.

    Ojo: get_rutina_hoy.php NO filtra por la semana pedida, devuelve el plan
    mas reciente con semana_inicio <= esa semana. Si la VM fallo, devolveria el
    plan de la SEMANA PASADA, y mirar solo "hay filas" diria que todo fue bien.
    Por eso se compara el semana_inicio de cada fila con el lunes buscado."""
    import planificar as pl
    base, token = pl.api_config()
    sesion = pl.sesion_infinityfree(base)
    for i in range(7):
        fecha = lunes + timedelta(days=i)
        r = sesion.get(f"{base}/get_rutina_hoy.php", params={"fecha": fecha.isoformat()},
                       headers={"X-API-Token": token}, timeout=60)
        r.raise_for_status()
        for fila in r.json().get("rutina") or []:
            if str(fila.get("semana_inicio", ""))[:10] == lunes.isoformat():
                return True
    return False


def traer_config_de_la_vm() -> None:
    """Copia la config_usuario.json de la VM (si responde). Si la VM esta caida
    —el caso en que este respaldo importa— se usa la ultima copia local."""
    if os.getenv("GYM_INSTANCIA"):
        # copia de OTRA persona en la VM: su config es la suya, nunca la tuya
        registrar("instancia de otra persona: se usa su config local")
        return
    if not VM_CLAVE.exists():
        registrar("sin clave SSH de la VM (o esto ES la VM): se usa la config local")
        return
    destino = AQUI / "config_usuario.json"
    tmp = AQUI / "config_usuario.vm.json"
    cmd = ["scp", "-q", "-i", str(VM_CLAVE), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
           "-o", "StrictHostKeyChecking=accept-new", f"{VM_HOST}:{VM_CONFIG}", str(tmp)]
    try:
        ok = subprocess.run(cmd, capture_output=True, timeout=40).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    if ok and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(destino)
        registrar("config traida de la VM")
    else:
        tmp.unlink(missing_ok=True)
        registrar("la VM no responde: se usa la ultima config local")


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(AQUI / ".env", override=True)
    import planificar as pl

    lunes = pl.lunes_objetivo()
    forzar = "--forzar" in sys.argv
    try:
        if not forzar and plan_de_la_semana_subido(lunes):
            registrar(f"semana {lunes}: la rutina ya esta subida, no hago nada")
            return 0
    except Exception as e:  # noqa: BLE001
        # si ni siquiera se puede consultar InfinityFree, generar tampoco servira
        registrar(f"no se pudo consultar InfinityFree: {e!r}")
        return 1

    registrar(f"semana {lunes}: " + ("regenerando a peticion (--forzar)" if forzar
                                     else "la rutina NO esta subida -> la genero aqui"))
    traer_config_de_la_vm()
    import motor_semanal
    try:
        motor_semanal.main()
    except SystemExit as e:
        registrar(f"motor_semanal termino con codigo {e.code}")
        return int(e.code or 0)
    ok = plan_de_la_semana_subido(lunes)
    registrar("OK: rutina subida" if ok else "FALLO: la rutina sigue sin estar")
    if ok:
        # aviso al telefono; si falla, la rutina ya esta subida igual
        import avisos
        registrar(f"aviso push: {avisos.rutina_lista(lunes)} enviado(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""El motor COMO ENTRENADOR: 20 semanas contra atletas virtuales (simulador.py).

Las pruebas de test_motor comprueban reglas; esta comprueba el resultado. Los
umbrales salen de medir el motor (2026-10-09, 3 semillas por perfil) y dejan
margen: si un cambio futuro empeora la forma de entrenar, se cae aqui aunque
cada regla por separado siga "bien".

Referencia, motor anterior -> motor con el entrenador (intermedio):
  series en zona 67% -> 82%, imposibles 7% -> 3%, demasiado faciles 21% -> 12%.

Uso:  python tests/test_simulacion.py   (~2-3 min)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import simulador as s
# config neutra para los helpers de planificar (sin TU lista de mancuernas ni
# tus asistidas): se prueba el motor para un usuario generico
import planificar as _pl
_pl._cfg = lambda: {"peso_corporal": 75}

FALLOS = []


def check(nombre, cond, detalle=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {nombre}" + (f" -> {detalle}" if detalle and not cond else ""))
    if not cond:
        FALLOS.append(nombre)


def fmt(r):
    return (f"zona {r['series_en_zona']:.0%}, imposibles {r['series_imposibles']:.0%}, "
            f"faciles {r['series_demasiado_faciles']:.0%}, saltos>20% {r['saltos_mayores_20']:.0%}")


R = {n: s.simular(p, semanas=20, semilla=1) for n, p in s.PERFILES.items()}

print("== Calidad de la prescripcion (todos los perfiles) ==")
for n, r in R.items():
    # con el RPE siempre igual el modelo no tiene informacion y manda la doble
    # progresion clasica: se le exige menos (el motor anterior daba 12% imposibles)
    piso, techo = (0.50, 0.10) if n == "rpe_siempre_8" else (0.60, 0.08)
    check(f"{n}: {piso:.0%}+ de series en zona y <={techo:.0%} imposibles",
          r["series_en_zona"] >= piso and r["series_imposibles"] <= techo, fmt(r))
    check(f"{n}: saltos de mas de un escalon por encima del 20% en <=5% de los casos",
          r["saltos_mayores_20"] <= 0.05, fmt(r))

print("\n== El atleta tipico ==")
r = R["intermedio"]
check("intermedio: 75%+ en zona, <=5% imposibles, <=18% demasiado faciles",
      r["series_en_zona"] >= 0.75 and r["series_imposibles"] <= 0.05
      and r["series_demasiado_faciles"] <= 0.18, fmt(r))
check("intermedio: sin deloads de mas (solo los del calendario)",
      [x["semana"] for x in r["semanas"] if x["meso"] == 5] == [4, 9, 14, 19])
check("principiante: gana fuerza (>3% en 20 semanas)", R["principiante"]["ganancia_fuerza"] > 0.03,
      f"{R['principiante']['ganancia_fuerza']:+.1%}")

print("\n== Situaciones que un entrenador tiene que saber manejar ==")
check("empezar MUY ligero: converge (60%+ en zona pese a arrancar al 45%)",
      R["subestimado"]["series_en_zona"] >= 0.60, fmt(R["subestimado"]))
check("estres fuera del gym: detecta la caida de rendimiento y adelanta el deload",
      any("RENDIMIENTO" in a for x in R["estres"]["semanas"] for a in x["avisos"]))
check("vacaciones de 3 semanas: vuelta en rampa (reingreso)",
      any("REINGRESO" in a for x in R["vacaciones"]["semanas"] for a in x["avisos"]))
check("RPE siempre en 8: el motor lo detecta y lo avisa",
      any(a.startswith("RPE:") for x in R["rpe_siempre_8"]["semanas"] for a in x["avisos"]))

print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} pruebas FALLARON: {FALLOS}")
    sys.exit(1)
print("RESULTADO: todas las pruebas pasaron.")

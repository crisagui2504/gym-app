# `python-scripts/` — Scripts auxiliares (legacy / offline)

Scripts simples, **anteriores al motor completo** (`python-engine/`). Se conservan como
referencia y para cálculos rápidos sin conexión. El motor de planificación real es
`python-engine/planificar.py` + `generador.py`.

> Documentación técnica completa del proyecto: [`../DOCUMENTACION.md`](../DOCUMENTACION.md)

## Contenido

| Archivo | Qué hace |
|---|---|
| `optimizar_rutina.py` | Lee un CSV local, calcula el tonelaje por ejercicio y aplica una regla simple: si RPE < 8 sube 2.5 kg, si RPE ≥ 9.5 baja 2.5 kg. Genera `rutina_optimizada.json`. |
| `rutina_base.json` | Plan de entrenamiento base en JSON, usado como referencia por el script anterior. |
| `requirements.txt` | Dependencias mínimas de estos scripts. |

## Uso

```bash
cd python-scripts
pip install -r requirements.txt
python optimizar_rutina.py
```

## Relación con el resto del proyecto

Estos scripts **no** participan del flujo de producción (app ↔ servidor ↔ motor).
La lógica de sobrecarga progresiva "buena" (mesociclo de 5 semanas, reglas por bloque,
recorte por duración, antibot) vive en `python-engine/`. Mantené estos como histórico
o para experimentar offline.

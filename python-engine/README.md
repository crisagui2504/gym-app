# Motor Algorítmico Local (capa Local)

Corre en tu PC, **no** se sube a InfinityFree. Es el "cerebro": genera los planes,
aplica la sobrecarga progresiva basada en evidencia y sirve el dashboard.

> Fundamento científico de cada regla: [`../docs/CAMBIOS_EVIDENCIA.md`](../docs/CAMBIOS_EVIDENCIA.md)
> · Documentación técnica: [`../DOCUMENTACION.md`](../DOCUMENTACION.md)

## Setup

```powershell
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # editá API_BASE_URL, API_TOKEN y MES_INICIO
```

## Módulos

| Archivo | Qué hace |
|---|---|
| `ejercicios_db.py` | Base de ejercicios por patrón de movimiento + **ponderación de estímulo por submúsculo** (`ESTIMULOS`) + bisagras axiales |
| `enfoques.py` | 5 enfoques (reps, técnicas, macros en g/kg, cardio) y 3 splits (U/L, PPL en orden Push/Piernas/Pull, Full Body) |
| `generador.py` | Construye el plan: selección por **ganancia marginal de submúsculo**, topes por región, protección lumbar, rotación por mesociclo |
| `config_usuario.py` | Persiste enfoque/split/prioridades/peso/duración/equipo excluido en `config_usuario.json` |
| `plan_template.py` | Dataclass `Fila` (unidad del plan) + plantilla de referencia |
| `planificar.py` | Sobrecarga progresiva: doble progresión estricta, RPE de trabajo, deload reactivo, marca anterior. Descarga historial, calcula y sube el plan |
| `exportar_local.py` | Descarga `historial.csv` + **backup fechado** en `backups/` |
| `motor_semanal.py` / `.bat` | Orquestador para el Programador de tareas de Windows (log en `motor.log`) |
| `dashboard.py` | Dashboard Dash/Plotly (progresión, e1RM, PRs, fatiga, peso+cintura, config, plan, mesociclo) |
| `tests/test_motor.py` | Suite de pruebas + **simulaciones** de cobertura/sobrecarga (45 combos) |

## Correr el motor

```powershell
python planificar.py           # calcula y sube la semana objetivo
DRY_RUN=1 python planificar.py # solo imprime, no envía  (PowerShell: $env:DRY_RUN=1)
python dashboard.py            # dashboard en http://127.0.0.1:8050
python tests/test_motor.py     # corre la suite (debe decir "todas las pruebas pasaron")
```

Flujo de `planificar.py`:

1. Resuelve el antibot de InfinityFree (reto AES-128/CBC con `pycryptodome`).
2. Descarga `exportar_csv.php` (historial real).
3. Calcula la semana objetivo según la posición en el mesociclo de 5 semanas y las
   reglas de progresión por bloque (basadas en evidencia).
4. Envía el plan a `actualizar_plan.php`.

## Variables de `.env`

```env
API_BASE_URL=https://tu-dominio.infinityfreeapp.com/api
API_TOKEN=el-mismo-token-que-config.php
MES_INICIO=2026-06-22          # lunes de la S1 del mesociclo (define semana y rotación)
# SEMANA_SIGUIENTE=2026-06-29  # opcional: forzar semana destino
# DRY_RUN=1                    # opcional: no envía nada
```

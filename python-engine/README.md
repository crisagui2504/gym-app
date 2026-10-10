# Motor, nutrición y dashboard (Python)

Corre en la VM de Azure (principal) y en el PC (respaldo). No se sube a InfinityFree. Es el "cerebro":

- arma y ajusta la rutina semanal;
- calcula las metas de nutrición y el menú barato;
- sirve el dashboard.

Más información:

- Fundamento de cada regla: [`../docs/CAMBIOS_EVIDENCIA.md`](../docs/CAMBIOS_EVIDENCIA.md).
- Documentación técnica completa: [`../DOCUMENTACION.md`](../DOCUMENTACION.md#7-módulos-del-motor-y-del-dashboard-python).

## Setup

```powershell
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # API_BASE_URL, API_TOKEN, MES_INICIO, VAPID_PRIVADA, VAPID_PUBLICA
```

## Módulos

| Área | Módulos |
|---|---|
| Plan de entreno | `ejercicios_db.py` (98 ejercicios) · `enfoques.py` (5 enfoques, 4 splits) · `generador.py` · `planificar.py` (motor semanal) · `entrenador.py` (modelo de fuerza) · `feedback.py` (encuesta, dolor, bienestar, preferencias) · `volumen.py` · `config_usuario.py` |
| Nutrición | `nutricion.py` (metas, calorías adaptativas, kcal por tipo de día, revisión semanal) · `alimentos_mx.py` (35 alimentos, precios) · `recetas_mx.py` (48 recetas) · `menu.py` (menú semanal barato) |
| Servidor y datos | `respaldo_semanal.py` / `motor_semanal.py` (la semana sin pisar lo ya subido) · `exportar_local.py` (CSV + respaldos) · `avisos.py` / `recordatorio.py` (push) · `dashboard.py` (11 pestañas + modo demo) |
| Demo y app | `simulador.py` (atleta virtual) · `demo_motor.py` · `exportar_demo.py` · `exportar_catalogo.py` |

## Comandos

```powershell
python dashboard.py            # http://127.0.0.1:8050 (o GymTracker.bat en la raíz)
python planificar.py           # calcula y sube la semana   ($env:DRY_RUN=1 para no subir)
python menu.py                 # imprime el menú de la semana y la lista del súper
python exportar_local.py       # baja historial, encuesta, preferencias y nutrición
python exportar_catalogo.py    # app/src/app/catalogo.generado.ts (si cambias ejercicios)
python exportar_demo.py        # app/src/app/demo.generado.ts (si cambias la demo o el menú)
```

## Pruebas

```powershell
python tests/test_motor.py        # reglas del motor, nutrición y menú
python tests/test_funcional.py    # dashboard, modo demo, estilos de la app
python tests/test_plan_qa.py      # calidad del plan (35 criterios)
python tests/test_barrido.py      # 13 440 semanas sin violar topes
python tests/test_simulacion.py   # el motor como entrenador (9 atletas virtuales)
```

Las cinco corren en GitHub Actions antes de cada despliegue.

## Archivos locales (no se versionan)

- **Configuración:** `.env` y `config_usuario.json`.
- **Datos:** `historial.csv`, `feedback.csv`, `preferencias.csv`, `nutricion.csv` y `peso_corporal.csv`.
- **Menú:** `menu_semana.json` y `precios_alimentos.json` (tus precios).
- **Otros:** `backups/` y `motor.log`.

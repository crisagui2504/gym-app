# Gym App — Rutinas Inteligentes con Sobrecarga Progresiva

Sistema completo de seguimiento de entrenamiento con planificación automática basada en tu historial real. Conecta una app Angular (interfaz de entrenamiento), una API PHP en la nube, un motor Python de inteligencia de progresión, y Power BI para análisis visual.

---

## Arquitectura general

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TU PC (local)                               │
│                                                                     │
│  ┌─────────────────┐        ┌───────────────────────────────────┐   │
│  │  python-engine/ │        │  app/ o angular-app/              │   │
│  │  Motor Python   │        │  Angular (interfaz de entreno)    │   │
│  │  planificar.py  │        │  Tarjetas, series, RPE, timer     │   │
│  └────────┬────────┘        └───────────────┬───────────────────┘   │
│           │ POST /actualizar_plan.php        │ GET /get_rutina_hoy  │
│           │ (subir plan semana)              │ POST /guardar_entreno│
└───────────┼──────────────────────────────────┼─────────────────────┘
            │                                  │
            ▼                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                   InfinityFree (nube gratuita)                    │
│                                                                   │
│  infinityfree/api/                                                │
│  ├── get_rutina_hoy.php   → devuelve los ejercicios del día      │
│  ├── guardar_entreno.php  → graba series, peso, RPE              │
│  ├── actualizar_plan.php  → recibe el plan calculado por Python  │
│  └── exportar_csv.php     → descarga el historial completo       │
│                                                                   │
│  Base de datos MySQL                                              │
│  ├── plan_rutina          → plan semanal generado                │
│  └── registro_series      → historial de cada serie hecha       │
└───────────────────────────────────────────────────────────────────┘
            │
            │ exportar_csv.php (historial en CSV)
            ▼
┌───────────────────────┐
│   Power BI Desktop    │
│   Dashboards DAX      │
│   Tonelaje / RPE / PR │
└───────────────────────┘
```

---

## Estructura de carpetas

```
gym/
├── app/                  → App Angular principal (interfaz de entrenamiento)
├── angular-app/          → Versión alternativa / experimental de la app Angular
├── infinityfree/         → Backend PHP + SQL para alojar en InfinityFree
│   └── api/              → Endpoints REST
├── python-engine/        → Motor de planificación semanal (corre local)
├── python-scripts/       → Scripts auxiliares (optimización básica)
├── docs/                 → Roadmap por sprints
└── powerbi_guide.md      → Guía para armar el dashboard en Power BI
```

---

## Módulo 1 — App Angular (`app/`)

La interfaz móvil con la que entrenas en el gimnasio. Se conecta a la API PHP cada día y te muestra qué hacer.

### Qué hace
- Descarga la rutina del día al abrirse (`GET /get_rutina_hoy.php`).
- Muestra cada ejercicio como una tarjeta con: técnica, rango de reps, peso sugerido, imagen del movimiento y músculos involucrados.
- Permite registrar cada serie: ajustás el **peso** (en pasos de 1.25 kg) y las **repeticiones**, y le ponés un **RPE del 6 al 10**.
- Al terminar una serie, arranca automáticamente un **cronómetro de descanso** (el tiempo viene del plan; si no hay, se calcula según la técnica). Suena una alarma (Web Audio API) y vibra el teléfono cuando termina.
- Botón **Guardar entreno**: manda todas las series al servidor (`POST /guardar_entreno.php`).
- **Racha de días**: cuenta cuántos días seguidos entrenas y lo muestra. Se guarda en `localStorage`.
- **Tema oscuro/claro**: se recuerda entre sesiones.
- **Calentamiento específico** por día de entrenamiento con movilidad y activación.
- **Series de aproximación**: si hay un ejercicio con peso ≥ 10 kg, genera automáticamente calentamientos progresivos (50% → 70% → 85%).
- **Mapa de músculos SVG**: resalta los grupos musculares del ejercicio activo.
- **Alternativas de ejercicio**: si un ejercicio no te va, podés reemplazarlo por otro del mismo grupo muscular sin salir de la app.
- Modal de **explicación de técnica**: descripción de Top Set, Back-off, AMRAP, Rest-Pause, etc.

### Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/app/app.component.ts` | Componente principal: toda la lógica (cargar, guardar, timer, racha, tema) |
| `src/app/app.component.html` | Template: tarjetas, series, controles, modal de técnica |
| `src/app/rutina-api.service.ts` | Servicio HTTP: `getRutinaHoy()` y `guardarEntreno()` |
| `src/app/entreno-data.ts` | Base de datos local: músculos por ejercicio, imágenes (wger.de), técnicas, alternativas, calentamientos, descansos por técnica |
| `src/app/muscle-map.component.ts` | SVG del cuerpo humano con músculos en highlight |
| `src/environments/environment.ts` | URL base de la API y token de autenticación |

### Cómo correrla localmente

```powershell
cd app
npm install       # o pnpm install
npm start         # abre en localhost:4200
```

### Cómo compilarla para producción

```powershell
cd app
npm run build
# El resultado queda en dist/
# Subí el contenido de dist/ a htdocs/ en InfinityFree
```

---

## Módulo 2 — Backend PHP (`infinityfree/`)

API REST para alojar en [InfinityFree](https://infinityfree.net/) (hosting gratuito con MySQL). Es el único servidor del sistema.

### Base de datos

Dos tablas principales (definidas en `schema.sql`):

**`plan_rutina`** — el plan de la semana (lo escribe el motor Python):
- `semana_inicio`, `dia_semana` (1=Lun…7=Dom), `nombre_dia`, `bloque`, `orden`
- `ejercicio`, `tecnica`, `series_objetivo`, `reps_min`, `reps_max`, `descanso_seg`
- `peso_sugerido` — el peso calculado por el motor según tu historial

**`registro_series`** — cada serie que hacés:
- `fecha_entreno`, `ejercicio`, `tecnica`, `numero_serie`
- `peso_kg`, `repeticiones`, `rpe`
- `tonelaje_serie` — columna calculada automáticamente: `peso_kg × repeticiones`

### Endpoints

| Método | Endpoint | Qué hace |
|---|---|---|
| `GET` | `/api/get_rutina_hoy.php?token=...&fecha=YYYY-MM-DD` | Devuelve los ejercicios del día como JSON |
| `POST` | `/api/guardar_entreno.php` | Graba las series del entreno (body JSON con `fecha_entreno` e `items[]`) |
| `GET` | `/api/exportar_csv.php?token=...` | Descarga todo el historial en CSV (para Python y Power BI) |
| `POST` | `/api/actualizar_plan.php` | Recibe el nuevo plan semanal desde Python y lo inserta en la BD |

Todos los endpoints requieren autenticación: `?token=TU_TOKEN` (GET) o header `X-API-Token: TU_TOKEN` (POST).

### Instalación en InfinityFree

1. Creá la base de datos MySQL desde el panel de InfinityFree.
2. En phpMyAdmin, ejecutá `schema.sql` (crea las tablas y carga un plan semilla).
3. Copiá `api/config.example.php` como `api/config.php` y completá:
   ```php
   define('DB_HOST', '...');
   define('DB_NAME', '...');
   define('DB_USER', '...');
   define('DB_PASS', '...');
   define('API_TOKEN', 'pon-aqui-un-token-secreto');
   ```
4. Subí la carpeta `api/` a `htdocs/api/` vía FTP.
5. Subí el build de Angular a `htdocs/`.

---

## Módulo 3 — Motor Python (`python-engine/`)

El cerebro del sistema. Corre en tu PC (no en el servidor) cada domingo o cuando quieras planificar la semana siguiente.

### Qué hace

1. **Descarga el historial** completo desde `exportar_csv.php`.
2. **Analiza** el último rendimiento de cada ejercicio: peso, reps y RPE de la última sesión, el mejor peso del mes, y si hay estancamiento (3 semanas sin subir tonelaje).
3. **Calcula el plan** de la semana siguiente según la posición en el mesociclo de 4 semanas:
   - **S1** — establecer base, no al máximo.
   - **S2 y S3** — sobrecarga progresiva (+1.25 kg o +1 rep según RPE).
   - **S4** — semana pico: superar todos los Top Sets del mes.
4. **Aplica reglas distintas por bloque**:
   - **Top Set**: si completaste el rango de reps con RPE ≤ 9, subís. Si el RPE fue ≥ 9 y estás estancado, deload reactivo al 90%.
   - **Back-off**: siempre el 80% del Top Set calculado.
   - **Volumen / AMRAP / Drop Set / Rest-Pause / Superserie**: sube si llegaste al tope de reps con RPE ≤ 8.
   - **Cardio y core**: peso base fijo.
5. **Sube el plan** calculado al servidor vía `actualizar_plan.php`.

> InfinityFree bloquea bots con un reto AES-128/CBC. El motor lo resuelve automáticamente con `pycryptodome` sin que tengas que hacer nada.

### Setup

```powershell
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Editá .env con tu URL y token
```

Variables en `.env`:

```env
API_BASE_URL=https://tu-dominio.infinityfreeapp.com/api
API_TOKEN=el-mismo-token-que-config.php
MES_INICIO=2026-06-23   # lunes de inicio del mesociclo actual
# SEMANA_SIGUIENTE=2026-06-30  # opcional: forzar una semana específica
# DRY_RUN=1                    # opcional: solo imprime, no envía al servidor
```

### Correrlo

```powershell
python planificar.py
```

Salida de ejemplo:
```
Semana objetivo 2026-06-30 | Mesociclo: semana 2/4 | 42 filas
{'ok': True, 'inserted': 42, 'updated': 0}
Plan de la semana 2026-06-30 (mesociclo S2) sincronizado.
```

### Plantilla del plan (`plan_template.py`)

Define la estructura semanal fija: qué ejercicios, en qué días, con qué técnica, cuántas series y el rango de reps. El motor lee esta plantilla y le aplica los pesos calculados del historial. Si es la primera semana (sin historial), usa los `peso_base` definidos en la plantilla.

**Estructura semanal (Upper/Lower, 4 sesiones de pesas + cardio):**

| Día | Sesión |
|---|---|
| Lunes | Torso A — Fuerza (Top Set + Back-off + Volumen + Aislamiento) |
| Martes | Pierna A — Fuerza |
| Miércoles | Descanso |
| Jueves | Descanso |
| Viernes | Torso Bombeo (Press Arnold, remos, face pull) |
| Sábado | Pierna Bombeo (Hip Thrust, Peso Muerto, Drop Sets) |
| Domingo | Cardio LISS + Core |

---

## Módulo 4 — Power BI (`powerbi_guide.md`)

Dashboard para analizar tu progreso de hipertrofia conectando directamente al CSV exportado.

### Cómo conectarlo

1. Power BI Desktop → **Obtener datos** → **Web** (URL directa) o **Texto/CSV** (archivo local).
2. URL para conexión en vivo: `https://TU-DOMINIO.infinityfreeapp.com/api/exportar_csv.php?token=TU_TOKEN`

### Medidas DAX incluidas

```dax
-- Tonelaje total movido (la métrica principal de hipertrofia)
Tonelaje Total = SUMX('historial', 'historial'[repeticiones] * 'historial'[peso])

-- RPE promedio (para detectar sobreentrenamiento)
RPE Promedio = AVERAGE('historial'[rpe])

-- Peso máximo histórico (PR)
Peso Máximo (PR) = MAX('historial'[peso])
```

### Visualizaciones recomendadas

- **Curva de sobrecarga progresiva**: línea de Tonelaje Total por semana, filtrada por ejercicio. Si la línea sube semana a semana, el sistema está funcionando.
- **Termómetro del SNC**: RPE Promedio semanal. Si supera 9.5 sostenidamente → deload.
- **Tabla/matriz de logbook**: fecha × ejercicio, con peso, reps y RPE.

---

## Módulo 5 — Scripts auxiliares (`python-scripts/`)

Scripts más simples, anteriores al motor completo. Útiles como referencia o para cálculos rápidos offline.

- **`optimizar_rutina.py`**: lee un CSV local, calcula tonelaje por ejercicio y aplica una regla simple: si RPE < 8 sube 2.5 kg, si RPE ≥ 9.5 baja 2.5 kg. Genera `rutina_optimizada.json`.
- **`rutina_base.json`**: plan de entrenamiento base en JSON, usado como referencia por el script anterior.

---

## Herramientas del repositorio

### Repomix

Empaqueta todo el repo en un único archivo de texto para pegarlo en un LLM (ChatGPT, Claude, etc.) y pedir análisis o mejoras.

```powershell
npm run pack        # genera repomix-output.xml en la raíz
```

El archivo resultante está ignorado por git (`.gitignore`).

---

## Flujo completo de un ciclo semanal

```
Domingo por la noche
  └── python planificar.py
        ├── Descarga historial del servidor
        ├── Calcula pesos para la semana siguiente (S1–S4 del mesociclo)
        └── Sube el plan a InfinityFree

Lunes a Sábado (en el gimnasio)
  └── Abrís la app Angular en el celular
        ├── Carga automáticamente los ejercicios del día
        ├── Hacés cada serie → ajustás peso/reps → ponés RPE → marcás como hecho
        ├── El timer de descanso corre automáticamente
        └── Al terminar: "Guardar entreno" → se sube al servidor

Cuando querés analizar tu progreso
  └── Power BI → conecta al CSV → dashboards de tonelaje, RPE, PRs
```

---

## Requisitos

| Componente | Tecnología |
|---|---|
| App Angular | Node.js 18+, Angular 17+ |
| Backend | PHP 8+, MySQL 5.7+ |
| Hosting | InfinityFree (gratuito) o cualquier hosting PHP/MySQL |
| Motor Python | Python 3.10+, pandas, requests, pycryptodome, python-dotenv |
| Análisis | Power BI Desktop (gratuito) |

---

## Roadmap (sprints)

Ver [`docs/SPRINTS.md`](docs/SPRINTS.md) para el detalle. Resumen:

- **Sprint 1** ✅ Infraestructura y API PHP
- **Sprint 2** ✅ App Angular con tarjetas y registro de series
- **Sprint 3** — Despliegue en dominio propio
- **Sprint 4** ✅ Motor Python local con mesociclo de 4 semanas
- **Sprint 5** — Dashboard Power BI conectado en vivo

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
            │ exportar_csv.php → historial.csv local
            ▼
┌───────────────────────────────────┐
│   Dashboard Python (Dash/Plotly)  │
│   localhost:8050                   │
│   Tonelaje · RPE · PRs · Logbook  │
│   (Power BI queda como alternativa)│
└───────────────────────────────────┘
```

---

## Estructura de carpetas

```
gym/
├── app/                  → App Angular principal (interfaz de entrenamiento)
├── angular-app/          → Versión alternativa / experimental de la app Angular
├── infinityfree/         → Backend PHP + SQL para alojar en InfinityFree
│   └── api/              → Endpoints REST
├── GymTracker.bat        → ▶ Ejecutable de un clic (abre el dashboard)
├── GymTracker (sin consola).vbs → Igual pero sin ventana de consola
├── Crear acceso directo en escritorio.bat → Pone el icono en el escritorio
├── python-engine/        → Motor + generador + dashboard (corre local)
│   ├── ejercicios_db.py → Base de datos de ejercicios (por patrón de movimiento)
│   ├── enfoques.py      → Enfoques (recomp/volumen/etc.) y splits (U-L/PPL/FB)
│   ├── generador.py     → Genera el plan dinámicamente según tu config
│   ├── config_usuario.py → Guarda tu enfoque elegido (lo hace permanente)
│   ├── planificar.py    → Motor de sobrecarga progresiva (mesociclo 5 semanas)
│   ├── plan_template.py → Dataclass Fila + plantilla de referencia
│   ├── dashboard.py     → Dashboard Dash/Plotly + configuración interactiva
│   └── assets/         → CSS del dashboard (tema oscuro, lo carga Dash solo)
├── python-scripts/       → Scripts auxiliares (optimización básica)
├── docs/                 → Roadmap por sprints
└── powerbi_guide.md      → Guía alternativa para Power BI
```

---

## Módulo 1 — App Angular (`app/`)

La interfaz móvil con la que entrenas en el gimnasio. Se conecta a la API PHP cada día y te muestra qué hacer.

### Qué hace
- Descarga la rutina del día al abrirse (`GET /get_rutina_hoy.php`).
- **Una tarjeta por ejercicio con todas sus series juntas**: el Top Set, el Back-off y las series de volumen del mismo ejercicio van en la misma tarjeta. Cada serie se etiqueta (Top Set / Back-off / Serie N), y la serie AMRAP se marca **"Al fallo (AMRAP)"** resaltada.
- Permite registrar cada serie: ajustás el **peso** (en pasos de 1.25 kg) y las **repeticiones**, y le ponés un **RPE del 6 al 10**.
- **Botón "⟳ repetir"**: copia el peso y las reps de una serie a todas las siguientes del ejercicio (la mayoría de las veces repetís el mismo peso → ahorra tiempo).
- Al terminar una serie, arranca automáticamente un **cronómetro de descanso basado en timestamp**: sigue contando bien aunque salgas de la app o bloquees el teléfono, y se reanuda si recargás (se persiste en `localStorage`). Suena una alarma (Web Audio API) y vibra al terminar.
- Botón **Guardar entreno**: manda todas las series al servidor (`POST /guardar_entreno.php`).
- **Racha de días**, **tema oscuro/claro**, **calentamiento específico** por día y **series de aproximación** automáticas.
- **Mapa de músculos SVG** (el "mapa de calor" de la esquina de cada tarjeta) resalta los grupos trabajados. *(Se quitaron las imágenes externas de wger.)*
- **Alternativas de ejercicio**: si una máquina está ocupada, reemplazás el ejercicio (toda su tarjeta) por otro del mismo grupo muscular.
- **Diseño adaptado a cada ejercicio**: la tarjeta muestra solo los campos que el ejercicio necesita — fuerza (peso + reps + RPE), cardio (minutos, Zona 2), plancha (segundos), Farmer's carry (peso + metros), pinzamiento (peso + segundos), rodillo (rondas), core (reps, sin RPE). Lo decide `medidaDe()` en `entreno-data.ts`.
- **Reprogramar la semana** (botón 📅): movés el **día de descanso** sin tocar el servidor. Tocás "Descansar acá" en cualquier día y su entreno se intercambia con el día de descanso actual (p. ej. descansás el sábado y hacés su entreno el jueves). El cambio se guarda en `localStorage` para esa semana y vuelve solo al default la semana siguiente.
- Modal de **explicación de técnica**: Top Set, Back-off, AMRAP, Rest-Pause, etc.

### Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/app/app.component.ts` | Componente principal: toda la lógica (cargar, guardar, timer, racha, tema) |
| `src/app/app.component.html` | Template: tarjetas, series, controles, modal de técnica |
| `src/app/rutina-api.service.ts` | Servicio HTTP: `getRutinaHoy()` y `guardarEntreno()` |
| `src/app/entreno-data.ts` | Base de datos local: músculos por ejercicio, técnicas, alternativas, calentamientos, descansos por técnica |
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
3. **Calcula el plan** de la semana siguiente según la posición en el mesociclo de **5 semanas** (metodología del Plan v3):
   - **S1** — establecer línea base, no al máximo absoluto.
   - **S2** — rota los ejercicios del Bloque B para atacar el músculo desde otro ángulo + primer intento de progresión.
   - **S3** — superar los registros de la Semana 1 (sobrecarga progresiva).
   - **S4 (Pico)** — superar todos los Top Sets del mes.
   - **S5 (Deload)** — recuperación: mismo peso que la última sesión, volumen reducido al 50% (1 serie en Bloque A y B, sin Bloque C).
4. **Aplica reglas distintas por bloque**:
   - **Top Set**: si completaste el rango de reps con RPE ≤ 9, subís. Si el RPE fue ≥ 9 y estás estancado, deload reactivo al 90%.
   - **Back-off**: siempre el 80% del Top Set calculado.
   - **Volumen / AMRAP / Drop Set / Rest-Pause / Superserie**: sube si llegaste al tope de reps con RPE ≤ 8.
   - **Cardio y core**: peso base fijo.
5. **Rota ejercicios según la semana** (campo `semanas` en cada fila de la plantilla): por ejemplo el Bloque B de Torso pasa de Press de Banca (S1/S3/S4) a Press Inclinado (S2), y los ejercicios de antebrazo (Farmer's Carry, Pinzamiento de Disco, Rodillo de Muñeca, Curl de Muñeca) aparecen en semanas específicas, siempre al final de la sesión.
6. **Sube el plan** calculado al servidor vía `actualizar_plan.php`.

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
Semana objetivo 2026-06-30 | Mesociclo: S2/4 | 48 filas
{'ok': True, 'inserted': 48, 'updated': 0}
Plan de la semana 2026-06-30 (S2/4) sincronizado.
```

### De dónde sale el plan base

El plan que el motor rellena con pesos lo construye **`generador.py`** según tu `config_usuario.json` (ver Módulo 4). El motor toma ese plan, le aplica los pesos calculados del historial y, si es la primera semana, usa los `peso_base` de la base de datos de ejercicios.

Cada fila tiene un campo `semanas` que controla en qué semanas del mesociclo aparece (`None` = todas). Así se implementa la rotación del Bloque B en S2 y los antebrazos por semana, fieles a la metodología del Plan v3. (`plan_template.py` conserva la plantilla fija original como referencia.)

**Estructura semanal de ejemplo (enfoque Recomposición, split Upper/Lower):**

| Día | Sesión | Prioridad |
|---|---|---|
| Lunes | Torso A — Fuerza | Hombro (Press Militar primero) |
| Martes | Pierna A — Fuerza | Cuádriceps (Sentadilla primero) |
| Miércoles | Cardio LISS + Core | Zona 2, 35–45 min |
| Jueves | Descanso Activo | 10–12k pasos |
| Viernes | Torso Bombeo | Hombro (Press Arnold primero) |
| Sábado | Pierna Bombeo | Cadena posterior (Hip Thrust + PDR) |
| Domingo | Cardio LISS + Core | Zona 2, 35–45 min |

**Descansos por técnica** (tabla del Plan v3): Top Set 180s · Back-off 120s · AMRAP/Volumen 90s · Rest-Pause 90s (10s intra) · Drop Set 90s (0s entre drops) · Aislamiento 90s · Superserie 60s.

---

## Módulo 4 — Dashboard Python + Generador autónomo (`python-engine/dashboard.py`)

Panel de Inteligencia Deportiva local (**reemplaza a Power BI**). App web hecha con **Dash + Plotly** que corre en tu PC, lee tu `historial.csv` y te deja **cambiar el enfoque de entrenamiento sin tocar código**.

### Cómo lanzarlo — un clic, sin terminal

Doble clic en **`GymTracker.bat`** (en la raíz del proyecto). La primera vez crea el entorno e instala dependencias solo; después abre el navegador en `http://127.0.0.1:8050` automáticamente.

- **`GymTracker (sin consola).vbs`** — igual, pero sin ninguna ventana de consola.
- **`Crear acceso directo en escritorio.bat`** — corrélo una vez y te deja el icono **"Gym Tracker"** en el escritorio para abrirlo cuando quieras.

### Datos reales y botón "Actualizar datos"

El dashboard muestra tus **datos reales** del backend. El botón **🔄 Actualizar datos** (arriba a la derecha) descarga el historial del servidor sin salir del dashboard — corre el mismo pipeline que `exportar_local.py` (Angular → PHP → MySQL → `historial.csv`) y recarga la vista. El chip de estado indica **● EN VIVO** (hay datos), **● SIN DATOS** o **● DEMO**.

Si todavía no registraste entrenos, ves un estado vacío con instrucciones (no datos falsos). Para una demo con datos de ejemplo, arrancá con la variable de entorno `GYM_DEMO=1`.

### Autonomía: cambiar el enfoque desde el dashboard

En la pestaña **⚙ Configuración** elegís:

- **Enfoque (objetivo):** Recomposición · Volumen (Bulk) · Definición (Cut) · Powerbuilding · Fuerza Pura. Cada uno ajusta rangos de reps, técnicas, volumen de los bloques, cardio y guía de macros según la teoría.
- **Split:** Upper/Lower (4 días) · Push/Pull/Legs (6 días) · Full Body (3 días).
- **Músculos prioritarios:** los que marques reciben el estímulo máximo (van **primero en el Bloque A**) y frecuencia extra al final de otros días.
- **Duración por sesión:** ~60 / 75 / 90 / 120 min. Limita cuántos ejercicios tiene cada día (recorta el Bloque C de menor prioridad) para que la sesión entre en tu tiempo y no llegues fundido a los últimos ejercicios.

Al presionar **"Generar y guardar plan"**, el `generador.py` reconstruye el plan completo aplicando las reglas del informe (patrones de movimiento, bloques A/B/C, técnicas, descansos, prioridad de orden, rotación del Bloque B y antebrazos por semana). La elección se guarda en `config_usuario.json` (por eso es **permanente**) y el motor `planificar.py` la usa en su próxima corrida.

### El generador (`generador.py` + `ejercicios_db.py` + `enfoques.py`)

- **`ejercicios_db.py`** — base de datos de ejercicios **comunes** etiquetados por patrón de movimiento (empuje/tirón horizontal y vertical, dominante de rodilla/cadera), músculo, equipo y bloque.
- **`enfoques.py`** — define cada enfoque (reps, técnicas, volumen, macros) y cada split (qué patrón se entrena cada día, respetando frecuencia 2×/semana).
- **`generador.py`** — combina lo anterior con tus prioridades para producir un plan válido. Nada de ejercicios raros: todo común y replicable en cualquier gimnasio.

### Qué muestra (7 pestañas)

| Pestaña | Contenido |
|---|---|
| **Resumen** | Tonelaje semanal, frecuencia de sesiones, volumen por bloque y RPE semanal |
| **Progresión** | Curva de peso máximo + tonelaje por ejercicio (selector) |
| **Records (PRs)** | Peso máximo histórico de cada ejercicio |
| **Estado SNC** | RPE promedio semanal con zona óptima (7.5–9) y zona de deload (≥9) |
| **Logbook** | Tabla completa, filtrable y ordenable, de todas las series |
| **⚙ Configuración** | Cambiar enfoque / split / prioridades y regenerar el plan |
| **Plan semana** | El plan calculado para la próxima semana según tu config |

Interfaz moderna (fuente Inter, tarjetas con gradiente, dropdowns de alto contraste). Incluye **tema oscuro y tema claro** conmutables con el botón **☀️ Vista clara / 🌙 Vista oscura** del header; la preferencia se guarda en `config_usuario.json`. Los estilos están en `python-engine/assets/dashboard.css` (Dash los carga solo).

> Power BI (`powerbi_guide.md`) queda como alternativa, pero el dashboard Python es la herramienta principal.

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
  └── python planificar.py   (o motor_semanal.py para automatizar)
        ├── Descarga historial del servidor
        ├── Calcula pesos para la semana siguiente (S1–S5 del mesociclo)
        │   → S2 rota Bloque B, S5 es semana de deload
        └── Sube el plan a InfinityFree

Lunes a Sábado (en el gimnasio)
  └── Abrís la app Angular en el celular
        ├── Carga automáticamente los ejercicios del día
        ├── Hacés cada serie → ajustás peso/reps → ponés RPE → marcás como hecho
        ├── El timer de descanso corre automáticamente
        └── Al terminar: "Guardar entreno" → se sube al servidor

Cuando querés analizar tu progreso
  └── .\run_dashboard.ps1 → dashboard en localhost:8050
        (tonelaje, RPE, PRs, logbook y plan de la semana)
```

---

## Requisitos

| Componente | Tecnología |
|---|---|
| App Angular | Node.js 18+, Angular 17+ |
| Backend | PHP 8+, MySQL 5.7+ |
| Hosting | InfinityFree (gratuito) o cualquier hosting PHP/MySQL |
| Motor Python | Python 3.10+, pandas, requests, pycryptodome, python-dotenv |
| Dashboard | Python 3.10+, dash, plotly (Power BI Desktop opcional) |

---

## Roadmap (sprints)

Ver [`docs/SPRINTS.md`](docs/SPRINTS.md) para el detalle. Resumen:

- **Sprint 1** ✅ Infraestructura y API PHP
- **Sprint 2** ✅ App Angular con tarjetas y registro de series
- **Sprint 3** — Despliegue en dominio propio
- **Sprint 4** ✅ Motor Python local con mesociclo de 5 semanas (deload + rotación)
- **Sprint 5** ✅ Dashboard Python (Dash/Plotly) — reemplaza Power BI
- **Sprint 6** ✅ App autónoma: generador dinámico de planes + enfoque configurable desde el dashboard + ejecutable de un clic

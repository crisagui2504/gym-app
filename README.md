# Gym App — Rutinas Inteligentes con Sobrecarga Progresiva

Sistema completo de seguimiento de entrenamiento con planificación automática basada en tu historial real. Conecta una app Angular (interfaz de entrenamiento, instalable como PWA), una API PHP en la nube, un motor Python de inteligencia de progresión **basado en evidencia científica**, y un dashboard local Dash/Plotly para análisis visual.

> **📚 Documentación clave**
> - [`DOCUMENTACION.md`](DOCUMENTACION.md) — documentación técnica completa (arquitectura, módulos, API).
> - [`docs/CAMBIOS_EVIDENCIA.md`](docs/CAMBIOS_EVIDENCIA.md) — **el fundamento científico de cada regla del motor**, con el detalle de todas las mejoras aplicadas (fallo/RIR, volumen, descansos, submúsculos, topes anti-sobrecarga, protección lumbar, etc.) y sus citas.
> - [`docs/Informe_Cientifico_GymTracker.docx`](docs/Informe_Cientifico_GymTracker.docx) / [`.pdf`](docs/Informe_Cientifico_GymTracker.pdf) — informe formal con 27 referencias revisadas por pares.

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
│  ├── get_historial.php    → últimas sesiones (panel Historial)   │
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
│   ├── exportar_local.py→ Descarga historial.csv + backups fechados
│   ├── motor_semanal.py/.bat → Orquestador para el Programador de tareas
│   ├── tests/test_motor.py → Suite de pruebas + simulaciones de cobertura
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

### Funciones avanzadas (tandas de mejora)

- **PWA instalable**: `manifest.webmanifest` + service worker + ícono. Se agrega a la pantalla de inicio del iPhone y abre al instante; cachea el shell y el plan del día para funcionar sin conexión.
- **Rediseño mobile-first (iPhone)**: barra de acciones fija al fondo (zona del pulgar) con Guardar grande (52 px) + toggles, barra de progreso de la sesión (N/M series), `safe-area-inset` respetado, sin zoom por doble toque.
- **Guardado blindado**: cola offline (si falla, el entreno queda en el teléfono y se reenvía solo al volver internet), anti doble-envío, y caché del plan para entrenar aunque el servidor esté caído.
- **Check-in de readiness** (😃/😐/😫): en día de baja energía baja el objetivo de RPE a 7-8 sin fallo, solo por ese día.
- **Objetivo de RPE por serie**: muestra el RPE objetivo antes de registrar (RIR 1-2, o "al fallo" en la última serie de S3-S4).
- **Historial** (botón 📓): tus últimas sesiones con la mejor serie de cada ejercicio (por e1RM).
- **Confeti de PR** 🎉: al guardar, si rompés un récord de 1RM estimado, celebración + vibración.
- **Filtro de equipo**: si tu gym no tiene cierto equipo, el motor sustituye por alternativas del mismo patrón (se configura en el dashboard).

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
4. **Aplica reglas distintas por bloque** (doble progresión estricta):
   - **Top Set**: primero completás el rango de reps, luego sube la carga. El PR de la S4 solo se intenta si la última sesión cumplió el rango con RPE ≤ 8 (progresión ganada, no forzada). Deload reactivo al 90% si estás estancado con RPE alto.
   - **Back-off**: siempre el 80% del Top Set calculado.
   - **Volumen / AMRAP / Drop Set / Rest-Pause / Superserie**: sube si llegaste al tope de reps con RPE ≤ 8. El **RPE de trabajo excluye la serie al fallo** (si no, el AMRAP bloqueaba la progresión).
   - **Peso corporal / core**: progresa por reps (sube el rango objetivo) hasta gatillar lastre.
5. **Dosifica el fallo por semana**: S1-S2 a RIR 1-2; las técnicas de intensidad (AMRAP/Rest-Pause/Drop) solo en S3-S4 y solo en la última serie. Deload (S5) 100% libre de fallo.
6. **Marca a superar visible**: cada tarjeta trae "Anterior: X kg × Y @RPE Z".
7. **Deload reactivo global**: si el RPE medio semanal ≥ 9 dos semanas seguidas, adelanta la descarga.
8. **Sube el plan** calculado al servidor vía `actualizar_plan.php`.

> InfinityFree bloquea bots con un reto AES-128/CBC. El motor lo resuelve automáticamente con `pycryptodome` sin que tengas que hacer nada.

### Selección inteligente por submúsculos (anti-sobrecarga)

El generador no elige ejercicios "por categoría amplia" ni al azar. Cada ejercicio declara **cuánto estimula cada submúsculo** (dorsal / espalda alta / deltoides anterior-lateral-posterior / pecho superior-inferior / cuádriceps / isquios / glúteo…) en `ESTIMULOS` (`ejercicios_db.py`), y la selección aplica:

- **Ganancia marginal con retornos decrecientes**: tras unas dominadas (dorsal), elige un remo (espalda alta) en vez de otro jalón — no repite el mismo estímulo.
- **Tope de compuestos por región/sesión**: pecho 2, press de hombro 1, espalda 3, cuádriceps 2, cadera 3 (no 3 presses de pecho el mismo día).
- **Techo de saturación**: ningún submúsculo pasa de ~10-12 series efectivas por sesión (dosis-respuesta con techo).
- **Protección lumbar**: máximo 2 bisagras axiales (peso muerto/RDL) por sesión; la 3ª pasa a hip thrust / curl femoral (cadena posterior sin carga espinal).
- **Rotación por mesociclo**: cada 5 semanas rota al siguiente ejercicio preferido de cada patrón (variedad con intención; la progresión no se pierde porque el historial es por ejercicio).

Todo esto se valida con **simulaciones automáticas** (45 combinaciones enfoque × split × ciclo) en `python-engine/tests/test_motor.py`. Detalle y citas en [`docs/CAMBIOS_EVIDENCIA.md`](docs/CAMBIOS_EVIDENCIA.md).

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

### Qué muestra (pestañas)

| Pestaña | Contenido |
|---|---|
| **Resumen** | Tonelaje semanal, frecuencia de sesiones, volumen por bloque y RPE semanal |
| **Progresión** | Peso máximo + **1RM estimado (Epley)** + tonelaje por ejercicio (selector) |
| **Records (PRs)** | Récords por **e1RM** (fuerza real), con la serie que lo produjo — detecta PRs "invisibles" (mismos kg, más reps) |
| **Fatiga (RPE)** | RPE promedio semanal con zona óptima (7.5–9) y zona de deload (≥9) |
| **Peso corporal** | Registro de peso + **cintura**, media móvil de 7 días y **semáforo calórico** que compara tu tendencia con el objetivo del enfoque (detecta recomposición) |
| **Logbook** | Tabla completa, filtrable y ordenable, de todas las series |
| **⚙ Configuración** | Cambiar enfoque / split / prioridades / **equipo excluido** y regenerar el plan; **macros en gramos** según tu peso |
| **Plan semana** | El plan de la próxima semana + botones **⬆ Recalcular y subir plan** y **📋 Copiar tabla** |
| **Mesociclo (5 sem)** | Las 5 semanas del mesociclo de un vistazo (estructura exacta, pesos proyectados), filtrable y copiable |

Interfaz moderna con **tema oscuro y claro** (botón del header, se guarda en `config_usuario.json`). Los estilos están en `python-engine/assets/dashboard.css`.

**Nutrición**: la pestaña Configuración convierte las guías de macros del enfoque a **gramos diarios** según tu peso, con distribución de proteína y recordatorio de creatina.

> Power BI (`powerbi_guide.md`) queda como alternativa legacy; el dashboard Python es la herramienta principal.

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

## Automatización semanal (opcional)

- **`motor_semanal.bat`** + **tarea programada de Windows** «GymTracker Semanal» (creada para correr **domingos 20:00**): descarga historial → recalcula → sube el plan, sin que toques nada. Se cambia/quita con `schtasks /Change` / `schtasks /Delete`.
- **`exportar_local.py`** guarda un **backup fechado** del historial en `python-engine/backups/` cada vez que descarga (las últimas 30 copias) — tu respaldo real ante un hosting gratuito.

## Flujo completo de un ciclo semanal

```
Domingo por la noche  (automático con la tarea programada, o manual)
  └── python planificar.py   (o motor_semanal.bat / botón del dashboard)
        ├── Descarga historial del servidor (+ backup fechado)
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
| App Angular | Node.js 18+ (probado en 24), Angular 20 (standalone + signals), PWA |
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
- **Sprint 7** ✅ **Motor basado en evidencia científica**: dosificación del fallo (RIR), descansos, volumen dosis-respuesta, doble progresión, deload reactivo, e1RM, nutrición en gramos, peso corporal + cintura, PWA, rediseño mobile-first, backups, automatización semanal.
- **Sprint 8** ✅ **Ponderación por submúsculos y anti-sobrecarga**: selección por ganancia marginal, topes por región, protección lumbar (bisagras axiales), rotación por mesociclo, vista del mesociclo completo — todo verificado con simulaciones. Ver [`docs/CAMBIOS_EVIDENCIA.md`](docs/CAMBIOS_EVIDENCIA.md).

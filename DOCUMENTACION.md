# Gym Tracker — Documentación Técnica

> Sistema de seguimiento y planificación inteligente de entrenamiento de fuerza,
> con arquitectura **Edge-to-Local** de tres capas (nube gratuita + cliente móvil +
> motor local en la laptop).

**Versión del documento:** 1.2 · **Última actualización:** Julio 2026
**Repositorio:** https://github.com/crisagui2504/gym-app

> **v1.2 (Julio 2026)**: el motor de rutinas y progresión se ajustó a la
> evidencia científica 2016–2025 y se sumó una capa de **inteligencia por
> submúsculos** que evita la sobrecarga y la redundancia. Lo esencial:
> - **Progresión**: doble progresión estricta, RPE de trabajo (excluye la serie al
>   fallo), fallo dosificado por semana (RIR 1-2 en S1-S2), deload reactivo global,
>   marca "Anterior" visible, progresión por reps en peso corporal.
> - **Selección**: ponderación de estímulo por submúsculo, elección por ganancia
>   marginal (anti-redundancia), topes de compuestos por región, protección lumbar
>   (máx. 2 bisagras axiales), rotación de ejercicios por mesociclo.
> - **Nutrición**: macros en gramos, peso corporal + cintura con semáforo calórico,
>   creatina; **app**: PWA, cola offline, readiness, historial, e1RM, confeti de PR,
>   rediseño mobile-first; **dashboard**: pestañas nuevas (Peso corporal, Mesociclo),
>   copiar tablas, subir plan; **automatización** semanal + backups fechados.
>
> Detalle completo, fundamento y **27 referencias** en
> [`docs/CAMBIOS_EVIDENCIA.md`](docs/CAMBIOS_EVIDENCIA.md) y el informe formal
> [`docs/Informe_Cientifico_GymTracker.docx`](docs/Informe_Cientifico_GymTracker.docx).

---

## Índice

1. [Visión General](#1-visión-general-overview)
2. [Alcances del Proyecto](#2-alcances-del-proyecto-scope)
3. [Limitaciones](#3-limitaciones-limitations)
4. [Arquitectura y Tecnologías](#4-arquitectura-y-tecnologías)
5. [Prerrequisitos](#5-prerrequisitos)
6. [Instalación y Configuración](#6-instalación-y-configuración-setup)
7. [Estructura del Proyecto y Documentación Interna](#7-estructura-del-proyecto-y-documentación-interna)
8. [Diccionario de Módulos y Clases](#8-diccionario-de-módulos-y-clases)
9. [Documentación de la API](#9-documentación-de-la-api)

---

## 1. Visión General (Overview)

**Gym Tracker** es una aplicación personal de entrenamiento que registra cada serie
de cada sesión y **recalcula automáticamente** la rutina de la semana siguiente
aplicando los principios de hipertrofia y sobrecarga progresiva (Top Set + Back-off,
AMRAP, Rest-Pause, Drop Set, mesociclos con deload).

El proyecto nació de una restricción concreta: alojar todo en un hosting **gratuito**
(InfinityFree), que bloquea peticiones automatizadas y limita base de datos, número
de archivos (inodes) y tiempo de ejecución. La solución es una arquitectura híbrida
donde el navegador valida las cookies anti-bot y un motor en Python corre en la
laptop del usuario, comunicándose con el servidor por HTTP.

### Características principales

- **App de gimnasio (Angular)**: interfaz táctil para registrar series con peso, reps
  y RPE; cronómetro de descanso que sobrevive el segundo plano; mapa muscular; cambio
  de ejercicio por alternativas; reprogramación del día de descanso.
- **Diseño adaptativo por ejercicio**: cada tarjeta muestra **solo los campos que el
  ejercicio necesita** (fuerza → peso+reps+RPE, cardio → minutos, plancha → segundos,
  carry → metros, etc.).
- **Motor de planificación (Python)**: genera el plan dinámicamente desde una base de
  datos de ejercicios y un enfoque configurable, y aplica la sobrecarga progresiva
  leyendo el historial real.
- **Dashboard local (Dash/Plotly)**: panel de inteligencia deportiva (reemplaza Power
  BI) con KPIs, progresión, records, estado del SNC y configuración del enfoque.
- **Backend PHP + MySQL**: API REST mínima alojada en InfinityFree.
- **Ejecutable de un clic** y scripts de build para no depender de la terminal.

---

## 2. Alcances del Proyecto (Scope)

### Metas que cumple

| Meta | Cómo la cumple |
|---|---|
| Registrar entrenamientos serie por serie | App Angular → `guardar_entreno.php` → MySQL |
| Aplicar sobrecarga progresiva automática | `planificar.py` analiza el historial y sube/baja peso por ejercicio |
| Generar rutinas según un objetivo | `generador.py` arma el plan desde `ejercicios_db.py` + `enfoques.py` |
| Cambiar el enfoque sin tocar código | Pestaña **Configuración** del dashboard → `config_usuario.json` |
| Analizar el progreso | Dashboard Dash/Plotly local sobre `historial.csv` |
| Operar dentro de un hosting gratuito | Antibot resuelto en cliente; motor corre local |

### Procesos que abarca (flujo completo)

```
1. ENTRENAR   → App Angular registra series (peso/reps/RPE) → MySQL
2. EXTRAER    → exportar_local.py descarga el historial a historial.csv
3. ANALIZAR   → dashboard.py muestra progreso; planificar.py calcula la semana siguiente
4. SINCRONIZAR→ planificar.py sube el plan nuevo a MySQL (actualizar_plan.php)
5. REPETIR    → la app trae el plan recalculado el siguiente día
```

### Hasta dónde llegan las funcionalidades actuales

- **Mesociclo de 5 semanas**: S1 base, S2 rotación del Bloque B, S3 superar S1,
  S4 pico, S5 deload (volumen reducido). Las técnicas de intensidad
  (AMRAP/Rest-Pause/Drop) solo se prescriben en S3–S4 y solo en la última
  serie; S1–S2 se trabaja a RIR 1–2 y el deload es 100% libre de fallo.
- **PR condicionado**: en S4 el motor solo propone superar el mejor peso del
  mes si la última sesión completó el rango de reps con RPE ≤ 8.
- **5 enfoques**: Recomposición, Volumen, Definición, Powerbuilding, Fuerza Pura.
- **3 splits**: Upper/Lower (4 días), Push/Pull/Legs (6 días), Full Body (3 días).
- **Duración objetivo por sesión** (60/75/90/120 min): recorta el Bloque C para
  ajustar el tiempo.
- **Prioridad muscular**: el músculo rezagado abre el día (Bloque A) y recibe
  frecuencia extra.
- **Reprogramación semanal**: mover el día de descanso (client-side, por semana).

---

## 3. Limitaciones (Limitations)

### Restricciones del hosting gratuito (InfinityFree)

- **Antibot**: el servidor inyecta una cookie `__test` con un reto AES-128/CBC.
  Cualquier cliente automatizado (Python) debe resolverlo. El motor lo hace con
  `pycryptodome`; si InfinityFree cambia el esquema del reto, el motor deja de
  conectar hasta adaptarlo.
- **Base de datos ≤ 50 MB**: el diseño usa `VARCHAR` limitados y `DECIMAL` precisos.
  El historial crece de a kilobytes por sesión, pero es un techo a tener presente.
- **Inodes (nº de archivos)**: la app se sirve como **4 archivos** compilados; se evita
  agregar assets externos. Por eso se quitaron las imágenes de wger.
- **Tiempo de ejecución ~20 s**: las queries son simples y la conexión PDO se cierra
  rápido. No hay procesos PHP largos.
- **Enrutamiento SPA**: requiere un `.htaccess` que redirija los 404 al `index.html`.

### Decisiones de diseño (cosas que el sistema NO hace, a propósito)

- **No hay autenticación de usuarios**: es una app personal monousuario, protegida solo
  por un **token de API** compartido. No está pensada para multiusuario.
- **El motor no corre en la nube**: `planificar.py` / `dashboard.py` se ejecutan en la
  laptop. El servidor solo guarda y sirve datos.
- **El plan no se regenera solo en el servidor**: hay que correr `planificar.py`
  (manual o vía Programador de tareas con `motor_semanal.py`).
- **El dashboard es local**: no está expuesto en internet; corre en `localhost:8050`.
- **La reprogramación del descanso es del lado del cliente** (`localStorage`): no cambia
  el plan en el servidor, solo qué sesión generada se muestra cada día; se reinicia
  cada semana.

### Cuellos de botella / dependencias externas

- **Conexión a internet** para sincronizar (la app y el motor dependen de la API).
- **El token viaja en el front** (`environment.ts`) y en `.env`: si se filtra, hay que
  rotarlo en los tres lugares (PHP, Angular, Python).
- **Calidad de los datos**: si en la app no se cargan pesos reales, el motor no puede
  calcular progresiones útiles (sugerirá valores mínimos).

---

## 4. Arquitectura y Tecnologías

### Diagrama de capas

```
┌──────────────────────── CAPA LOCAL (laptop del usuario) ────────────────────────┐
│  python-engine/                                                                  │
│   ├─ generador.py     → arma el plan (DB de ejercicios + enfoque + prioridades)  │
│   ├─ planificar.py    → sobrecarga progresiva; descarga historial; sube el plan  │
│   ├─ dashboard.py     → panel Dash/Plotly (localhost:8050)                       │
│   └─ exportar_local.py→ baja el historial a historial.csv                        │
└───────────────┬─────────────────────────────────────────────────────────────────┘
                │  HTTP (token X-API-Token) — resuelve el antibot __test (AES)
                ▼
┌──────────────────────── CAPA EDGE (InfinityFree, nube gratis) ──────────────────┐
│  infinityfree/api/ (PHP 8 + PDO)                                                 │
│   ├─ get_rutina_hoy.php   → devuelve la sesión del día                           │
│   ├─ get_historial.php    → últimas sesiones (panel Historial de la app)        │
│   ├─ guardar_entreno.php  → graba las series del entreno                         │
│   ├─ actualizar_plan.php  → reemplaza el plan de la semana (DELETE + INSERT)     │
│   └─ exportar_csv.php     → exporta todo el historial como CSV                   │
│  MySQL: plan_rutina · registro_series · sincronizaciones_plan                    │
└───────────────▲─────────────────────────────────────────────────────────────────┘
                │  HTTP (el navegador ya valida la cookie antibot de forma natural)
                ▼
┌──────────────────────── CAPA CLIENTE (móvil / navegador) ───────────────────────┐
│  app/ (Angular 20, SPA compilada y subida a htdocs)                              │
│   └─ AppComponent → registra series, cronómetro, alternativas, reprogramar semana│
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Cómo interactúan los componentes

1. **El navegador** carga la SPA Angular desde InfinityFree. Al hacerlo, el servidor
   le entrega la cookie antibot `__test`, que el navegador valida automáticamente
   (por eso el cliente no tiene problemas con el antibot).
2. **La app** llama a `get_rutina_hoy.php` para mostrar la sesión del día y a
   `guardar_entreno.php` al terminar. Todas las llamadas llevan el header
   `X-API-Token`.
3. **El motor local** (Python) **sí** debe resolver el reto antibot: `planificar.py`
   abre una sesión `requests`, descifra el reto AES y setea la cookie `__test` a mano.
4. **`planificar.py`** descarga el historial (`exportar_csv.php`), calcula la semana
   siguiente con `generador.py` + las reglas de progresión, y la sube
   (`actualizar_plan.php`).
5. **El dashboard** lee el `historial.csv` local (generado por `exportar_local.py`) y
   permite cambiar el enfoque, que se guarda en `config_usuario.json` y consume el
   propio `generador.py`.

### Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Cliente | Angular 20, TypeScript 5.8, RxJS 7.8, Standalone Components + Signals |
| Edge / Backend | PHP 8, PDO, MySQL/MariaDB, `.htaccess` (Apache) |
| Local / Motor | Python 3.10+, pandas, requests, pycryptodome, python-dotenv |
| Dashboard | Dash, Plotly (Flask por debajo) |
| Tooling | Node.js 24 + npm (build Angular), Repomix (empaquetado para LLMs) |

---

## 5. Prerrequisitos

| Componente | Herramienta | Versión recomendada |
|---|---|---|
| App Angular | Node.js | 18+ (probado en 24.15) |
| | npm | 9+ (probado en 11.12) |
| | Angular CLI | 20.x (vía `npx`, no requiere global) |
| Motor + Dashboard | Python | 3.10 o superior |
| | pip | incluido con Python |
| Backend | PHP | 8.0+ |
| | MySQL / MariaDB | 5.7+ / 10.4+ |
| | Hosting | InfinityFree (o cualquier hosting PHP/MySQL) |
| Control de versiones | Git | 2.x |

**Dependencias de Python** (`python-engine/requirements.txt`):
`pandas`, `requests`, `python-dotenv`, `pycryptodome`, `dash`, `plotly`.

---

## 6. Instalación y Configuración (Setup)

### 6.1. Clonar el repositorio

```bash
git clone https://github.com/crisagui2504/gym-app.git
cd gym-app
```

### 6.2. Backend (InfinityFree / MySQL)

1. Crear la base de datos en el panel de InfinityFree (phpMyAdmin) y ejecutar
   `infinityfree/schema.sql`.
2. Copiar la configuración:
   ```bash
   cp infinityfree/api/config.example.php infinityfree/api/config.php
   ```
3. Editar `config.php` con tus credenciales y un token largo:
   ```php
   const DB_HOST = 'sqlXXX.infinityfree.com';
   const DB_NAME = 'if0_XXXXXXX_gym';
   const DB_USER = 'if0_XXXXXXX';
   const DB_PASS = 'TU_PASSWORD';
   const API_TOKEN = 'CAMBIA_ESTE_TOKEN_LARGO';
   const ALLOWED_ORIGIN = '*'; // o tu dominio
   ```
4. Subir por FTP el contenido de `infinityfree/` a `htdocs/` (incluida la carpeta
   `api/` y el `.htaccess`).

### 6.3. App Angular

```bash
cd app
npm install
# Editar app/src/environments/environment.ts con tu apiBaseUrl y el MISMO apiToken
npx ng build           # genera dist/gym-rutinas/browser/
```
Subir el contenido de `dist/gym-rutinas/browser/` a `htdocs/` (junto a `api/`).
> Atajo: desde la raíz, doble clic en **`Construir app para subir.bat`** deja la
> carpeta `deploy/` lista para arrastrar al FTP.

### 6.4. Motor y Dashboard (laptop local)

```bash
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env                 # y editarlo
```

Variables de `python-engine/.env`:
```env
API_BASE_URL=https://TU-DOMINIO.infinityfreeapp.com/api
API_TOKEN=el-mismo-token-que-config.php
MES_INICIO=2026-06-22                # lunes de la Semana 1 del mesociclo
# SEMANA_SIGUIENTE=2026-06-29        # opcional: forzar semana destino
# DRY_RUN=1                          # opcional: solo imprime, no envía
```

### 6.5. Levantar el entorno local

```bash
# Dashboard (un clic): doble clic en GymTracker.bat (raíz del proyecto)
# o manualmente:
python dashboard.py        # → http://127.0.0.1:8050

# Recalcular y subir el plan de la semana:
python planificar.py
```

---

## 7. Estructura del Proyecto y Documentación Interna

Cada carpeta principal incluye su propio `README.md` con el detalle de ese módulo.
La documentación central es este archivo (`DOCUMENTACION.md`).

```
gym-app/
├── DOCUMENTACION.md          → este documento (visión técnica completa)
├── README.md                 → guía general del proyecto
├── powerbi_guide.md          → guía alternativa de Power BI (legacy)
├── GymTracker.bat            → ejecutable de un clic (abre el dashboard)
├── GymTracker (sin consola).vbs
├── Construir app para subir.bat → compila la app y prepara deploy/
│
├── app/                      → ★ App Angular de producción (la que se sube)
│   ├── README.md
│   └── src/app/
│       ├── app.component.ts/html  → AppComponent (vista de entrenamiento)
│       ├── entreno-data.ts        → datos y clasificadores (medidaDe, etc.)
│       ├── rutina-api.service.ts  → RutinaApiService (cliente HTTP)
│       └── muscle-map.component.ts→ MuscleMapComponent (mapa muscular SVG)
│
├── angular-app/              → Versión experimental/alternativa de la app
│   └── README.md
│
├── infinityfree/             → ★ Backend PHP + SQL (capa Edge)
│   ├── README.md
│   ├── schema.sql            → tablas (plan_rutina, registro_series, ...)
│   ├── conexion.php
│   └── api/
│       ├── bootstrap.php          → helpers (token, CORS, PDO, JSON)
│       ├── get_rutina_hoy.php     → GET sesión del día
│       ├── guardar_entreno.php    → POST series del entreno
│       ├── actualizar_plan.php    → POST plan de la semana (DELETE+INSERT)
│       ├── exportar_csv.php       → GET historial en CSV
│       └── config.example.php     → plantilla de credenciales
│
├── python-engine/            → ★ Motor + Generador + Dashboard (capa Local)
│   ├── README.md
│   ├── generador.py          → arma el plan dinámico
│   ├── enfoques.py           → enfoques + splits + descansos
│   ├── ejercicios_db.py      → base de datos de ejercicios
│   ├── plan_template.py      → dataclass Fila + plantilla de referencia
│   ├── config_usuario.py     → persistencia del enfoque elegido
│   ├── planificar.py         → sobrecarga progresiva + sincronización
│   ├── exportar_local.py     → descarga historial.csv
│   ├── motor_semanal.py      → orquestador (Programador de tareas)
│   ├── dashboard.py          → panel Dash/Plotly
│   ├── requirements.txt
│   └── assets/dashboard.css  → estilos del dashboard
│
├── python-scripts/           → Scripts auxiliares (legacy / cálculos offline)
│   └── README.md
│
└── docs/
    └── SPRINTS.md            → roadmap por sprints
```

> **Nota sobre archivos ignorados (`.gitignore`)**: `config_usuario.json`,
> `historial.csv`, `motor.log`, `registrar_sesion.py`, `deploy/`, `node_modules/`,
> `.venv/` y los `.env`/`config.php` con secretos **no** se versionan.

---

## 8. Diccionario de Módulos y Clases

### 8.1. Capa Cliente (Angular — `app/src/app/`)

#### `AppComponent` (`app.component.ts`)
- **Qué es / qué hace**: el componente raíz y único de la SPA. Orquesta toda la
  sesión de entrenamiento: carga la rutina del día, arma las tarjetas de ejercicio,
  gestiona el cronómetro de descanso, el cambio de tema, la racha, las alternativas
  y la reprogramación de la semana.
- **Para qué sirve en el sistema**: es la cara visible para el usuario en el gimnasio.
  Convierte las filas del plan (que vienen del backend) en tarjetas interactivas y, al
  terminar, empaqueta las series y las envía a guardar.
- **Cómo interactúa**:
  - Usa `RutinaApiService` para `getRutinaHoy()` y `guardarEntreno()`.
  - Usa los helpers de `entreno-data.ts` (`medidaDe`, `musculosDe`, `alternativasDe`,
    `nSeriesDe`, `descansoPorTecnica`, `calentamientoDe`, etc.).
  - Renderiza `MuscleMapComponent` dentro de cada tarjeta.
- **Conceptos internos clave**:
  - `agrupar()`: une filas consecutivas del mismo ejercicio en **una sola tarjeta**
    (Top Set + Back-off juntos).
  - `agregarSegmento()`: crea las series según la **medida** del ejercicio.
  - Cronómetro basado en **timestamp** (`finAt`), persistido en `localStorage`, que
    sobrevive el segundo plano y la recarga.
  - Reprogramación de la semana mediante un mapa de override en `localStorage`.

#### `RutinaApiService` (`rutina-api.service.ts`)
- **Qué es / qué hace**: servicio inyectable que encapsula las llamadas HTTP al backend
  (con el header `X-API-Token`).
- **Para qué sirve**: aísla a `AppComponent` de los detalles de la red. Define las
  interfaces `EjercicioPlan`, `RutinaHoyResponse` y `SeriePayload`.
- **Cómo interactúa**: lee `environment.apiBaseUrl` / `apiToken`; lo consume
  `AppComponent`.

#### `MuscleMapComponent` (`muscle-map.component.ts`)
- **Qué es / qué hace**: componente standalone que dibuja un **mapa muscular en SVG
  inline** y resalta los músculos trabajados por el ejercicio.
- **Para qué sirve**: feedback visual del músculo objetivo sin imágenes externas
  (clave para no gastar inodes/hits del hosting).
- **Cómo interactúa**: recibe `@Input() muscles: MuscleId[]` desde `AppComponent`.

#### `entreno-data.ts` (módulo de datos y clasificadores)
- **Qué es / qué hace**: módulo sin estado con tipos, catálogos y funciones puras:
  - `medidaDe(nombre, bloque)` → **clasifica cada ejercicio** y decide qué campos
    mostrar (peso/reps/minutos/segundos/metros/rondas y si lleva RPE). Es el corazón
    del diseño adaptativo.
  - `musculosDe(nombre)` → músculos trabajados (para el mapa).
  - `alternativasDe(nombre)` → ejercicios sustitutos del mismo grupo.
  - `nSeriesDe`, `descansoPorTecnica`, `explicacionTecnica`, `calentamientoDe`,
    `seriesAproximacion`, `rpeSignificado`.
- **Para qué sirve**: centraliza el "conocimiento de dominio" del front, de forma que
  la vista solo renderiza.
- **Cómo interactúa**: lo consume `AppComponent`.

### 8.2. Capa Local (Python — `python-engine/`)

#### `ejercicios_db.py`
- **Qué es / qué hace**: base de datos en código de ejercicios **comunes**, cada uno
  etiquetado por patrón de movimiento, músculo, equipo y bloque (A/B/C). Define la
  dataclass `Ejercicio` y helpers de consulta (`por_patron`, `MUSCULO_A_PATRON`).
- **Para qué sirve**: es el "vocabulario" del generador. Nada de ejercicios raros.
- **Cómo interactúa**: lo consume `generador.py` y `enfoques.py`.

#### `enfoques.py`
- **Qué es / qué hace**: define los **enfoques** (Recomposición, Volumen, Definición,
  Powerbuilding, Fuerza) con sus parámetros (reps, técnicas, volumen, macros, cardio)
  y los **splits** (Upper/Lower, PPL, Full Body) con la distribución de patrones por
  día. También la tabla de descansos por técnica.
- **Para qué sirve**: traduce un objetivo abstracto a parámetros concretos.
- **Cómo interactúa**: lo consume `generador.py`.

#### `generador.py`
- **Qué es / qué hace**: **construye el plan semanal** (`list[Fila]`) combinando el
  split, el enfoque, las prioridades del usuario y la base de ejercicios. Aplica
  prioridad de orden, frecuencia extra, rotación del Bloque B en S2 y antebrazos por
  semana.
- **Para qué sirve**: es **el motor que genera todas las rutinas**. Punto de entrada
  `obtener_plan()`.
- **Cómo interactúa**: lee `config_usuario.py`; usa `ejercicios_db`, `enfoques` y la
  dataclass `Fila` de `plan_template`. Lo consume `planificar.py` y `dashboard.py`.

#### `plan_template.py`
- **Qué es / qué hace**: define la dataclass **`Fila`** (la unidad atómica de un plan)
  y conserva una plantilla fija de referencia (`PLAN`) del enfoque Recomposición.
- **Para qué sirve**: `Fila` es el contrato común entre el generador, el motor y el
  backend.
- **Cómo interactúa**: `generador.py` y `planificar.py` importan `Fila`.

#### `config_usuario.py`
- **Qué es / qué hace**: lee/escribe `config_usuario.json` (enfoque, split,
  prioridades, peso corporal, duración, tema). `DEFAULT_CONFIG`, `cargar_config()`,
  `guardar_config()`.
- **Para qué sirve**: hace la app "permanente" — la elección sobrevive entre corridas.
- **Cómo interactúa**: lo consumen `generador.py` y `dashboard.py`.

#### `planificar.py`
- **Qué es / qué hace**: el **cerebro de la sobrecarga progresiva**. Resuelve el
  antibot, descarga el historial, calcula la posición en el mesociclo (S1–S5), aplica
  las reglas de progresión por bloque (Top Set, Back-off, Volumen) y recorta por
  duración; finalmente **sube el plan** al servidor.
- **Para qué sirve**: cierra el ciclo semanal. Punto de entrada `main()`.
- **Cómo interactúa**: usa `generador.obtener_plan()`; llama a `exportar_csv.php` y
  `actualizar_plan.php`. Provee `api_config()` y `sesion_infinityfree()` que reutilizan
  `exportar_local.py` y `registrar_sesion.py`.

#### `exportar_local.py`
- **Qué es / qué hace**: descarga el historial completo y lo guarda como
  `historial.csv` (fuente del dashboard).
- **Cómo interactúa**: reutiliza el solucionador antibot de `planificar.py`.

#### `motor_semanal.py`
- **Qué es / qué hace**: orquestador para el Programador de tareas de Windows; corre
  `exportar_local` + `planificar` y registra en `motor.log`.

#### `dashboard.py`
- **Qué es / qué hace**: app **Dash/Plotly** (panel de inteligencia deportiva).
  Construye el layout, las figuras (tonelaje, RPE, records, frecuencia, progresión),
  la pestaña de **Configuración** (cambiar enfoque) y el botón "Actualizar datos".
  Soporta tema claro/oscuro.
- **Para qué sirve**: análisis del progreso y control del enfoque sin tocar código.
- **Cómo interactúa**: lee `historial.csv`; usa `enfoques`, `generador` y
  `config_usuario`; dispara `exportar_local.main()` desde el navegador.

### 8.3. Capa Edge (PHP — `infinityfree/api/`)

#### `bootstrap.php`
- **Qué es / qué hace**: prólogo común de todos los endpoints. Configura **CORS**,
  responde a `OPTIONS`, y expone los helpers: `db()` (PDO singleton), `require_token()`
  (valida `X-API-Token` o `?token`), `json_input()`, `json_response()` y
  `monday_for_date()`.
- **Para qué sirve**: evita repetir boilerplate y centraliza la seguridad mínima.
- **Cómo interactúa**: lo incluye cada endpoint con `require_once`.

#### Endpoints (ver detalle en la sección 9)
- `get_rutina_hoy.php`, `guardar_entreno.php`, `actualizar_plan.php`,
  `exportar_csv.php`. Todos validan el token y usan el `db()` de `bootstrap.php`.

---

## 9. Documentación de la API

**Base URL**: `https://TU-DOMINIO/api`
**Autenticación**: header `X-API-Token: <token>` (o `?token=<token>` en los GET).
**Formato**: JSON (salvo `exportar_csv.php`, que devuelve CSV).

### 9.1. `GET /get_rutina_hoy.php`

Devuelve la sesión que corresponde a una fecha (según su día de la semana y la última
semana de plan disponible).

**Query params**
| Param | Tipo | Descripción |
|---|---|---|
| `fecha` | `YYYY-MM-DD` | Opcional. Por defecto, hoy. |
| `token` | string | Token (si no va en el header). |

**Respuesta `200`**
```json
{
  "ok": true,
  "fecha": "2026-06-22",
  "semana_inicio": "2026-06-22",
  "dia_semana": 1,
  "rutina": [
    {
      "id": 101, "dia_semana": 1, "nombre_dia": "Torso A - Fuerza",
      "bloque": "A - Fuerza maxima", "orden": 1,
      "ejercicio": "Press Militar Mancuernas (Sentado)", "tecnica": "Top Set",
      "series_objetivo": "1.0", "reps_min": 6, "reps_max": 8,
      "descanso_seg": 180, "peso_sugerido": "25.00", "notas": null
    }
  ]
}
```

### 9.1b. `GET /get_historial.php`

Devuelve las series de los últimos `dias` días (por defecto 30, tope 90), más
recientes primero. Lo consume el panel **Historial** de la app (botón 📓).

**Query params**
| Param | Tipo | Descripción |
|---|---|---|
| `dias` | int | Opcional (1–90). Por defecto 30. |
| `token` | string | Token (si no va en el header). |

**Respuesta `200`**: `{ "ok": true, "dias": 30, "series": [ { "fecha_entreno",
"ejercicio", "tecnica", "numero_serie", "peso_kg", "repeticiones", "rpe" }, … ] }`

### 9.2. `POST /guardar_entreno.php`

Graba las series de un entreno. `plan_id` es opcional (nullable).

**Body**
```json
{
  "fecha_entreno": "2026-06-22",
  "items": [
    {
      "plan_id": 101, "ejercicio": "Press Militar Mancuernas (Sentado)",
      "tecnica": "Top Set", "numero_serie": 1,
      "peso_kg": 25, "repeticiones": 8, "rpe": 9, "notas": null
    }
  ]
}
```
> `rpe` es obligatorio y debe estar entre 1 y 10 (el endpoint lo valida).

**Respuesta `200`**
```json
{ "ok": true, "inserted": 16 }
```

### 9.3. `POST /actualizar_plan.php`

Reemplaza **por completo** el plan de la(s) semana(s) del payload (DELETE + INSERT),
evitando duplicados y huérfanos.

**Body**
```json
{
  "semana_inicio": "2026-06-22",
  "rutina": [
    {
      "semana_inicio": "2026-06-22", "dia_semana": 1,
      "nombre_dia": "Torso A - Fuerza", "bloque": "A - Fuerza maxima", "orden": 1,
      "ejercicio": "Press Militar Mancuernas (Sentado)", "tecnica": "Top Set",
      "series_objetivo": 1, "reps_min": 6, "reps_max": 8,
      "descanso_seg": 180, "peso_sugerido": 25.0, "notas": "..."
    }
  ]
}
```

**Respuesta `200`**
```json
{ "ok": true, "procesados": 41, "semana_inicio": "2026-06-22" }
```

### 9.4. `GET /exportar_csv.php`

Exporta todo el historial (`registro_series` con LEFT JOIN a `plan_rutina`) como CSV
descargable. Lo consume el motor local.

**Cabeceras de respuesta**: `Content-Type: text/csv`, `Content-Disposition: attachment`.

**Columnas**: `id, fecha_entreno, ejercicio, tecnica, numero_serie, peso_kg,
reps_hechas, rpe, tonelaje_serie, semana_inicio, dia_semana, nombre_dia, bloque,
series_objetivo, reps_min, reps_max, peso_sugerido`.

### 9.5. Errores comunes

| Código | Significado |
|---|---|
| `401` | `{ "ok": false, "error": "Token invalido" }` |
| `400` | JSON inválido, payload sin rutina/series, o RPE fuera de 1–10 |
| `204` | Respuesta a `OPTIONS` (preflight CORS) |

---

## Modelo de datos (MySQL)

| Tabla | Propósito |
|---|---|
| `plan_rutina` | Plan semanal generado (una fila por ejercicio/técnica/orden por día). |
| `registro_series` | Historial real: cada serie con peso, reps, RPE y `tonelaje_serie` (columna generada). FK a `plan_rutina` con `ON DELETE SET NULL`. |
| `sincronizaciones_plan` | Bitácora de cada push de plan (auditoría). |

---

## Apéndice — Glosario de técnicas

- **Top Set**: la serie más pesada del día (1 serie), busca superar la semana anterior
  (doble progresión: primero completar el rango de reps, luego subir carga).
- **Back-off**: 2 series al ~80% del Top Set, más repeticiones.
- **RIR (reps en reserva)**: cuántas reps quedaban antes del fallo. S1–S2 se
  entrena a RIR 1–2; el RPE de la app es su inverso (RPE 8 = RIR 2).
- **AMRAP**: la última serie al fallo (tantas reps como se pueda). Solo en S3–S4.
- **Rest-Pause**: en la última serie, fallo → 10 s → fallo con el mismo peso. Solo en S3–S4.
- **Drop Set**: en la última serie, fallo → −20% de peso sin descanso → fallo. Solo en S3–S4.
- **Deload (S5)**: semana de recuperación: misma intensidad (peso), volumen al
  50%, sin Bloque C y sin ninguna serie al fallo.

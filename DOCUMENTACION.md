# GymTracker — Documentación técnica

> Entrenador personal de fuerza y nutrición: una app móvil (PWA) registra cada
> serie, un motor en Python estima tu fuerza y arma la semana siguiente, y un
> dashboard muestra el progreso. Todo sobre infraestructura gratuita o mínima.

**Versión del documento:** 2.0 · **Última actualización:** octubre 2026
**Repositorio:** https://github.com/crisagui2504/gym-app

Documentos relacionados:

| Documento | Para qué |
|---|---|
| [`README.md`](README.md) | Visión general, cómo funciona una semana, cómo desarrollar |
| [`docs/CAMBIOS_EVIDENCIA.md`](docs/CAMBIOS_EVIDENCIA.md) | Cada cambio del motor y de la app, con su fundamento científico y referencias |
| [`docs/NUEVO_USUARIO.md`](docs/NUEVO_USUARIO.md) | Darle una copia propia a otra persona, paso a paso |
| [`python-engine/README.md`](python-engine/README.md) · [`infinityfree/README.md`](infinityfree/README.md) | Detalle de cada carpeta |

---

## Índice

1. [Visión general](#1-visión-general)
2. [Arquitectura](#2-arquitectura)
3. [Limitaciones y decisiones de diseño](#3-limitaciones-y-decisiones-de-diseño)
4. [Instalación y configuración](#4-instalación-y-configuración)
5. [Estructura del repositorio](#5-estructura-del-repositorio)
6. [Módulos de la app (Angular)](#6-módulos-de-la-app-angular)
7. [Módulos del motor y del dashboard (Python)](#7-módulos-del-motor-y-del-dashboard-python)
8. [API (PHP)](#8-api-php)
9. [Modelo de datos (MySQL)](#9-modelo-de-datos-mysql)
10. [Pruebas y despliegue](#10-pruebas-y-despliegue)
11. [Glosario](#11-glosario)

---

## 1. Visión general

| Pieza | Qué hace |
|---|---|
| **App** (Angular 20 PWA) | Muestra la rutina del día y registra cada serie (peso, reps, RPE). Funciona sin conexión. Además: encuesta por músculo, bienestar, proteína del día, menú semanal y avisos push. |
| **API** (PHP 8 + MySQL, InfinityFree) | Guarda y sirve los datos. Es lo único que vive en el hosting gratuito. |
| **Motor** (Python) | Lee el historial, estima el 1RM de cada ejercicio con el RPE y arma la semana siguiente dentro de un mesociclo de 5 semanas. También calcula las metas de nutrición y el menú barato. |
| **Dashboard** (Dash/Plotly) | Progresión, récords, fatiga, volumen, peso, menú, configuración, plan y mesociclo. Es público en la VM y funciona en celular. |
| **VM de Azure** | Corre el motor cada domingo, refresca los datos del dashboard, manda los avisos push y sirve el dashboard por HTTPS. |
| **PC** | Respaldo del motor por si la VM no generó la semana. |
| **GitHub Actions** | Prueba todo y publica la app en InfinityFree en cada push a `main`. |

### Lo que hace el motor (resumen)

- **Mesociclo de 5 semanas:** S1 base, S2 rotación, S3 superar S1, S4 pico y S5 descarga. El RPE objetivo sube de 8 a 9 y el fallo solo aparece en S3–S4.
- **Modelo de fuerza por ejercicio** (`entrenador.py`): e1RM con la tabla RTS y Epley, suavizado en el tiempo, con desentrenamiento y topes de salto.
- **Autorregulación:**
  - la encuesta por músculo ajusta series (−2 a +3);
  - el dolor articular cambia el ejercicio;
  - con 3 o más días malos de energía o sueño se adelanta la descarga.
- **Selección de ejercicios** por estímulo de submúsculo, con topes por región, protección lumbar y rotación.
- **Configuración:**
  - 5 enfoques: Recomposición, Volumen, Definición, Powerbuilding y Fuerza;
  - 4 splits: Upper/Lower de 4 y 5 días, Push/Piernas/Pull y Full Body;
  - duración de 60–120 min, deporte (por ejemplo básquetbol) y equipo disponible.
- **Pesos realistas:** discos de 1.25 kg, tu lista de mancuernas y el paso de la máquina asistida.

### Lo que hace la parte de nutrición

- **Metas:** proteína en g/kg según el enfoque (1.6–2.5 g/kg) y kcal desde los macros del enfoque más los ajustes que aceptaste.
- **Calorías adaptativas:** se ajustan según la pendiente del peso de 21 días, de ±100 a ±300 kcal, con 14 días de espera entre ajustes. Se reparten por tipo de día (pesas, deporte, cardio, descanso) con el mismo total semanal.
- **Menú semanal más barato** con comida mexicana (~50 opciones por tiempo), con:
  - tipo de dieta: mexicana (Plato del Bien Comer), **DASH** (sodio ≤ 2,300 o 1,500 mg) o **mediterránea**;
  - énfasis: equilibrado, más proteína o más carbohidratos;
  - alternativas por comida;
  - cocina por adelantado;
  - lista del súper;
  - presupuesto y porciones para la familia;
  - fibra, hierro y calcio.

---

## 2. Arquitectura

```
                         ┌────────────────────────────┐
                         │  Celular: app (PWA)         │
                         │  IndexedDB + cola offline   │
                         └─────────────┬──────────────┘
                     rutina, historial │ entreno, encuesta, proteína, preferencias,
                     meta, menú        │ suscripción push            (X-API-Token)
                                       ▼
┌──────────────────────────────── InfinityFree ─────────────────────────────────┐
│  htdocs/            app compilada + .htaccess (SPA, no-cache de index.html)   │
│  htdocs/api/        endpoints PHP (sección 8) · config.php solo en el servidor │
│  MySQL              plan, series, encuesta, preferencias, push, nutrición, menú│
└───────────────▲───────────────────────────────────────────▲───────────────────┘
                │ el motor resuelve el antibot __test (AES)  │ FTPS en cada push
┌───────────────┴────────────── VM de Azure ──────┐   ┌──────┴────────────────────┐
│ gymtracker-motor   domingo 22:00 (México)       │   │ GitHub Actions            │
│ gymtracker-datos   cada 3 h (historial, etc.)   │   │ 6 suites de pruebas →     │
│ gymtracker-recordatorio  cada hora (push 6 pm)  │   │ ng build → deploy/ → FTPS │
│ gymtracker-dashboard  gunicorn + Caddy (HTTPS)  │   └───────────────────────────┘
│   + API pública de la demo (/demo/api/…)        │
└──────────────────────────────▲──────────────────┘
                               │ si la VM no generó la semana
                        ┌──────┴──────┐
                        │ PC: respaldo │ domingo 23:30 o al encender
                        └─────────────┘
```

### Flujo de una semana

1. **Domingo 22:00:** `respaldo_semanal.py` en la VM comprueba si la rutina de la semana ya está subida. Si no está:
   1. `motor_semanal.py` exporta el historial;
   2. `planificar.main()` calcula la semana y la sube (`actualizar_plan.php`);
   3. sube la meta de nutrición y el menú;
   4. manda los avisos push "rutina lista" y "tu semana de nutrición".
2. **Si la VM no pudo:** el PC lo intenta a las 23:30 o al encender. También existe `generar_rutina_manual.bat`.
3. **Durante la semana:** la app trae la rutina del día, registra series, la encuesta y la proteína. Sin red, todo queda en cola y se reenvía.
4. **Cada 3 h:** `exportar_local.py` refresca en la VM el historial, la encuesta, las preferencias y la nutrición que lee el dashboard.

### Autenticación y antibot

- **Token compartido:** todas las llamadas llevan `X-API-Token` (o `?token=` en GET). Es una app personal, sin cuentas de usuario.
- **Antibot de InfinityFree:** responde a clientes automatizados con un reto AES (cookie `__test`). El navegador lo resuelve solo; Python lo resuelve con `pycryptodome` en `planificar.sesion_infinityfree()`.

### Stack

| Capa | Tecnologías |
|---|---|
| App | Angular 20 (standalone + signals), TypeScript, RxJS, service worker propio, IndexedDB, Web Push |
| API | PHP 8, PDO, MySQL/MariaDB, `.htaccess` (Apache) |
| Motor y dashboard | Python 3.11+ (VM: 3.12), pandas, numpy, requests, pycryptodome, Dash, Plotly, pywebpush |
| Servidor | Azure VM Ubuntu 24.04, systemd, gunicorn, Caddy (HTTPS con sslip.io), 1 GB de swap |
| CI | GitHub Actions + SamKirkland/FTP-Deploy-Action (FTPS) |

---

## 3. Limitaciones y decisiones de diseño

### Hosting gratuito (InfinityFree)

- **Antibot:** si InfinityFree cambia el reto, el motor deja de conectar hasta adaptarlo.
- **Base de datos pequeña** y procesos PHP cortos: queries simples y tablas que se crean solas con `CREATE TABLE IF NOT EXISTS`.
- **No manda `Cache-Control` por defecto:** el `.htaccess` marca `index.html`, `sw.js` y el manifiesto como `no-cache`. Sin esto, la app seguía cargando la versión anterior tras cada despliegue.
- **SPA:** el `.htaccess` manda todo lo que no es archivo a `index.html`. Así se evitan los 404, que InfinityFree castiga.

### Seguridad (estado actual)

- **Un solo token, sin cuentas.** El token va dentro de la app (`environment.ts`), así que cualquiera que abra la app puede verlo. Sirve para una app personal, no para datos de terceros.
- **`config.php` (credenciales de MySQL y token) se dejó de versionar.** Vive solo en el servidor y nunca lo sube el CI. Sus valores anteriores quedaron en el historial de git, así que **hay que rotarlos**: nueva contraseña de MySQL en el panel y nuevo token en `config.php`, `environment.ts` y los `.env`.
- **El dashboard público es de solo lectura para la demo,** pero tus datos reales se ven sin contraseña: decisión del usuario.

### Decisiones a propósito

- **Proteína por porciones, no conteo de calorías al gramo:** es lo que la gente sostiene. Las calorías se ajustan con la báscula.
- **Valores nutrimentales y precios aproximados:** USDA y tablas mexicanas para nutrimentos; Profeco 2026 donde hay dato y estimado (editable) donde no.
- **Sin escáner de código de barras:** Safari en iOS no tiene `BarcodeDetector` en apps web.
- **Sin precios automáticos de Profeco:** sus datos abiertos se quedaron en 2018.
- **Sin Apple Health, Apple Watch ni Live Activities:** requieren app nativa.
- **Mover el día de descanso desde la app** es local (por semana). El recordatorio push de la VM no lo ve.
- **Otra persona = otra copia completa** (`docs/NUEVO_USUARIO.md`), no multiusuario.

---

## 4. Instalación y configuración

### 4.1 Backend (InfinityFree)

1. Crea la base MySQL e importa `infinityfree/schema.sql` en phpMyAdmin. Las tablas nuevas también se crean solas.
2. Copia `infinityfree/api/config.example.php` como `config.php` en `htdocs/api/` **del servidor**, nunca en git:

   ```php
   const DB_HOST = 'sqlXXX.infinityfree.com';
   const DB_NAME = 'if0_XXXXXXX_gym';
   const DB_USER = 'if0_XXXXXXX';
   const DB_PASS = '…';
   const API_TOKEN = 'token-largo';
   const ALLOWED_ORIGIN = '*';
   ```

3. La app y la API las publica el CI (sección 10). A mano: `Construir app para subir.bat` deja `deploy/` listo para FTP.

### 4.2 App

```powershell
cd app
npm ci
npm start                  # http://localhost:4200   (modo demo: ?demo=1)
npx ng build               # dist/gym-rutinas/browser/
```

`src/environments/environment.ts` define:

| Variable | Contenido |
|---|---|
| `apiBaseUrl` | La API |
| `apiToken` | El mismo token de `config.php` |
| `vapidPublica` | La clave pública de los avisos push |
| `demoApi` | La API de la demo en la VM |

### 4.3 Motor y dashboard

```powershell
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env`:

```env
API_BASE_URL=https://TU-SITIO/api
API_TOKEN=el-mismo-de-config.php
MES_INICIO=2026-09-28            # lunes de la S1 del mesociclo
VAPID_PRIVADA=…                  # avisos push (la pública va en la app)
VAPID_PUBLICA=…
# SEMANA_SIGUIENTE=2026-10-12    # opcional: forzar la semana destino
# DRY_RUN=1                      # opcional: calcula sin subir
```

`config_usuario.json` lo escribe el dashboard (pestaña Configuración). Contiene:

- **Entreno:** enfoque, split, prioridades, peso, duración, equipo excluido, deporte, mancuernas, máquinas asistidas y tema.
- **Nutrición:** ajuste de kcal y su fecha, alimentos excluidos, suplementos en el menú, presupuesto, adultos y niños.

Comandos:

```powershell
python dashboard.py               # http://127.0.0.1:8050  (o GymTracker.bat)
python planificar.py              # calcula y sube la semana
python menu.py                    # imprime el menú de la semana
python exportar_local.py          # baja historial y demás CSV
```

### 4.4 VM

Instalación o actualización (idempotente; también actualiza las copias de otras personas):

```bash
ssh azureuser@20.150.209.104
cd ~/gym && git pull && bash servidor/instalar_vm.sh
```

La primera vez, `servidor/desplegar.sh` (desde el PC) copia el `.env` y la config por SSH.

---

## 5. Estructura del repositorio

```
gym/
├── app/                         App Angular (PWA)
│   ├── public/sw.js             service worker (red primero para index.html, sin caché HTTP)
│   └── src/app/                 sección 6
├── infinityfree/
│   ├── .htaccess                SPA + no-cache de index.html y sw.js
│   ├── schema.sql               todas las tablas (sección 9)
│   └── api/                     endpoints (sección 8); config.php NO se versiona
├── python-engine/               motor, nutrición, menú, dashboard (sección 7)
│   ├── assets/dashboard.css     estilos (incluye la vista de celular)
│   └── tests/                   6 suites (sección 10)
├── servidor/                    instalación de la VM (systemd, Caddy), copias de otras personas, armar_deploy.sh
├── instancias/instancias.json   personas con su propia copia (docs/NUEVO_USUARIO.md)
├── docs/                        evidencia científica, informe, tesis, guía de nuevo usuario
├── .github/workflows/desplegar.yml
├── GymTracker.bat / .vbs        dashboard local en un clic
├── Construir app para subir.bat build manual a deploy/
└── Nuevo usuario.bat            asistente para la copia de otra persona
```

No se versionan:

- `.env`, `config_usuario.json` y `infinityfree/api/config.php`;
- `historial.csv`, `feedback.csv`, `preferencias.csv`, `nutricion.csv`, `peso_corporal.csv`;
- `menu_semana.json`, `precios_alimentos.json` e `instancias/*/`;
- `deploy/`, `node_modules/` y `.venv/`.

---

## 6. Módulos de la app (Angular)

| Archivo | Qué hace |
|---|---|
| `app.component.ts/.html` | Pantalla principal. Incluye: rutina del día por tarjetas, series, RPE objetivo, cronómetro, "¿Cómo te sientes hoy?" y encuesta, cambio de ejercicio ("Máquina ocupada" / "Usar siempre"), mover el descanso, historial, resumen al guardar, racha, tema, avisos push y la banda del modo demo. Guarda el entreno en curso y lo restaura si la app se cierra. |
| `rutina-api.service.ts` | Cliente HTTP de la API (sección 8). Interfaces de rutina, historial, encuesta, nutrición y menú. |
| `almacen.ts` | Almacén durable en IndexedDB, con localStorage como respaldo y memoria en demo: entreno en curso, colas de envío, proteína del día. |
| `entreno-data.ts` | Conocimiento del front: qué campos lleva cada ejercicio (`medidaDe`), músculos, alternativas, descansos y calentamiento. |
| `catalogo.generado.ts` | Catálogo de ejercicios del motor (lo genera `exportar_catalogo.py`; una prueba exige que esté al día). |
| `muscle-map.component.ts` | Mapa muscular en SVG. |
| `acentos.ts` | Pipe que pone acentos a los nombres que vienen del motor. |
| `nutricion.ts` | `NutricionService`. Proteína del día por porciones (17 de casa y 20 de "Comí fuera"), meta del motor, creatina con racha, "Lo comí" del menú, menú de la semana, elección de comidas y "ya tengo en casa", peso de hoy (y cintura) con su tendencia. Guardado offline con reenvío. |
| `menu-semana.ts` | Funciones puras que rehacen en el teléfono la lista del súper (por hogar) y la cocina por adelantado según las comidas elegidas, y el texto para compartir la lista. |
| `proteina.component.ts` | Panel **Comida** con dos vistas: Proteína (barra, porciones, creatina, comí fuera) y Menú (resumen, días, cambiar, lo comí, cocina, lista). |
| `demo.ts` / `demo.generado.ts` | Modo demo (5 toques al logo o `?demo=1`). Usa una API falsa que pide escenarios al motor de la VM y tiene un respaldo empaquetado. Almacén en memoria: nada real se lee ni se escribe. |

---

## 7. Módulos del motor y del dashboard (Python)

### Entreno

| Módulo | Qué hace |
|---|---|
| `ejercicios_db.py` | 98 ejercicios con patrón, músculo, equipo, bloque y estímulo por submúsculo. |
| `enfoques.py` | 5 enfoques (reps, técnicas, macros en g/kg, tendencia de peso objetivo) y 4 splits. |
| `generador.py` | Arma el plan: ganancia marginal por submúsculo, topes por región, bisagras axiales, rotación, deporte y duración. |
| `planificar.py` | Motor semanal: semana del mesociclo, descargas (rendimiento, bienestar, reingreso), progresión por ejercicio, redondeo a pesos reales, preferencias y encuesta. Sube el plan, la meta de nutrición y el menú. Incluye helpers de API y antibot. |
| `entrenador.py` | `ModeloFuerza`: e1RM por ejercicio con RPE, tendencia, desentrenamiento y calibración. |
| `feedback.py` | Encuesta por músculo, dolor, días malos y preferencias "Usar siempre". |
| `volumen.py` | Series efectivas por músculo (las indirectas cuentan la mitad) contra MEV/MAV/MRV. |
| `simulador.py` | Atleta virtual: 9 perfiles para medir al motor como entrenador. |
| `config_usuario.py` | `config_usuario.json` con sus valores por defecto. |

### Nutrición

| Módulo | Qué hace |
|---|---|
| `nutricion.py` | Metas (proteína y kcal), tendencia de peso, calorías adaptativas (`evaluar`), kcal por tipo de día (MET del Compendium), adherencia de 7 días, resumen semanal para el push, y subida y descarga con la API. |
| `alimentos_mx.py` | 69 alimentos: nutrimentos, fibra, hierro, calcio, grasa saturada, sodio, precios (Profeco o estimado), unidades legibles. Tus precios van en `precios_alimentos.json`. |
| `recetas_mx.py` | 174 recetas mexicanas: 50 desayunos, 51 comidas, 50 cenas y 23 colaciones, con porciones base. |
| `menu.py` | Generador del menú semanal (sección 7.1). |

### Servidor, datos y demo

| Módulo | Qué hace |
|---|---|
| `dashboard.py` | Dash/Plotly con 11 pestañas: Resumen, Progresión, Récords, Fatiga, Volumen, Peso corporal, Menú, Logbook, Configuración, Plan semana, Mesociclo. Modo demo por cookie y API pública de la demo (`/demo`, `/demo/salir`, `/demo/api/opciones`, `/demo/api/escenario`). |
| `exportar_local.py` | Baja historial, encuesta, preferencias y nutrición a CSV, con respaldos fechados en `backups/`. |
| `motor_semanal.py` / `respaldo_semanal.py` | Orquestan la semana (sección 2) sin pisar una rutina ya subida. |
| `avisos.py` / `recordatorio.py` | Web Push (VAPID): rutina lista, revisión semanal de nutrición, recordatorio de las 6 pm si no has entrenado. |
| `demo_motor.py` / `exportar_demo.py` / `exportar_catalogo.py` | Escenarios de la demo (cualquier enfoque y split), respaldo de demo para la app y catálogo para la app. |

### 7.1 Cómo se arma el menú (`menu.py`)

1. **Combinaciones:** de las ~50 recetas de cada tiempo, cada día entran 18: las 5 más baratas por kcal, las 3 con más kcal y las 2 con más proteína, las 4 que mejor cumplen la dieta, las 4 con más proteína o carbos si hay énfasis, y el resto al azar. Prueba desayuno × comida × cena × porción (0.75–2.5×) × colación, ~1.1 millones, con numpy (~1 s el menú).
   - **Dieta:** cambia ingredientes (DASH: leche descremada, arroz y pasta integrales, res magra, pechuga, panela; mediterránea: aceite de oliva, res magra) y pone reglas. DASH: sodio ≤ 2,300/1,500 mg al día, grasa saturada ≤ 7 % de las kcal, ≥ 600 g de verdura y fruta, 2-3 lácteos y carne roja ≤ 2/semana. Mediterránea: saturada ≤ 9 %, ≥ 500 g de verdura y fruta, pescado ≥ 2/semana y carne roja ≤ 1/semana. `menu["dieta"]["cumple"]` compara cada regla con lo que trae el menú.
   - **Énfasis:** "más proteína" pide el tope del rango de proteína del enfoque; "más carbohidratos" el tope del rango de carbos (g/kg × peso). Las kcal no cambian.
2. **Elección:** se queda con la **más barata** que queda a ±5 % de las kcal del día y llega a la proteína mínima. Revisa los 600 mejores candidatos con las cantidades ya redondeadas (huevos y tortillas enteros).
3. **Variedad:**
   - $9 virtuales por cada repetición;
   - tope de usos por receta;
   - comida y cena sin la misma proteína;
   - como máximo 4 huevos al día.
4. **Etapas de respaldo:** dieta completa con énfasis → más holgura → dieta básica (sodio, saturada, verdura mínima) → sin énfasis → sin dieta → sin proteína → sin variedad; nunca el huevo. Cada cosa que se suelta se avisa. Con exclusiones fuertes hay menú en vez de error.
5. **Presupuesto (`menu_presupuesto`):** si no cabe, baja la variedad en 3 pasos. Si aun así no cabe, avisa lo mínimo posible.
6. **Hogar:** la lista y la cocina se multiplican por adultos + 0.6 × niños.
7. **El JSON resultante** (~70 KB) incluye:
   - días con comidas y sus alternativas;
   - lista del súper;
   - cocina por adelantado (domingo y miércoles);
   - ficha de cada alimento, para que la app rehaga las cuentas;
   - promedios de fibra, hierro, calcio, sodio, % de grasa saturada y verdura/fruta;
   - la dieta, el énfasis y el cumplimiento de cada regla;
   - avisos.

---

## 8. API (PHP)

**Base:** `https://TU-SITIO/api`.

- **Autenticación:** `X-API-Token: <token>`, o `?token=` en GET.
- **Formato:** JSON, salvo `exportar_csv.php`.
- **Errores:**
  - `401` token inválido;
  - `400` datos inválidos, con `{"ok": false, "error": "…"}`;
  - `500` error al guardar;
  - `204` preflight CORS.
- **Tablas:** las marcadas con *(auto)* se crean solas la primera vez.

### Entreno

| Endpoint | Método | Entrada | Respuesta |
|---|---|---|---|
| `get_rutina_hoy.php` | GET | `fecha` (YYYY-MM-DD, opcional; hoy) | `{ok, fecha, semana_inicio, dia_semana, rutina: [{id, nombre_dia, bloque, orden, ejercicio, tecnica, series_objetivo, reps_min, reps_max, descanso_seg, peso_sugerido, notas}]}`. Es el plan más reciente con `semana_inicio` ≤ esa semana. |
| `get_historial.php` | GET | `dias` (1–90, defecto 30) | `{ok, dias, series: [{fecha_entreno, ejercicio, tecnica, numero_serie, peso_kg, repeticiones, rpe}]}`, más recientes primero. |
| `guardar_entreno.php` | POST | `{fecha_entreno, items: [{plan_id?, ejercicio, tecnica, numero_serie, peso_kg, repeticiones, rpe (1–10), notas?}]}` | `{ok, inserted}` |
| `actualizar_plan.php` | POST | `{semana_inicio, rutina: [filas del plan]}` | Reemplaza la semana completa (DELETE + INSERT): `{ok, procesados, semana_inicio}` |
| `exportar_csv.php` | GET | — | CSV del historial unido al plan: `id, fecha_entreno, ejercicio, tecnica, numero_serie, peso_kg, reps_hechas, rpe, tonelaje_serie, semana_inicio, dia_semana, nombre_dia, bloque, series_objetivo, reps_min, reps_max, peso_sugerido` |
| `get_notas.php` | GET | — | `{ok, notas: [{ejercicio, notas, fecha_entreno}]}`: la última nota por ejercicio de los últimos 180 días |

### Encuesta, preferencias y avisos

| Endpoint | Método | Entrada | Respuesta |
|---|---|---|---|
| `guardar_feedback.php` | POST | `{fecha, items: [{tipo, clave, bombeo?, carga?, agujetas?, dolor?}]}`, ver la tabla de abajo | `{ok, guardadas}`. Upsert por (fecha, tipo, clave): completar la misma fila en dos momentos no pisa lo previo. |
| `get_feedback.php` | GET | `dias` (1–120, defecto 42) | `{ok, dias, feedback: [...]}` |
| `guardar_preferencia.php` | POST | `{original, reemplazo}` o `{original, baja: true}` | `{ok}`. "Usar siempre" un reemplazo; con `baja` se vuelve al original. |
| `get_preferencias.php` | GET | — | `{ok, preferencias: [{original, reemplazo}]}` |
| `guardar_suscripcion.php` | POST | PushSubscription `{endpoint, keys: {p256dh, auth}}`, o `{endpoint, baja: true}` | `{ok}` |
| `get_suscripciones.php` | GET | — | `{ok, suscripciones: [{endpoint, p256dh, auth}]}` (lo usa `avisos.py`) |

Valores de `guardar_feedback.php`:

| `tipo` | `clave` | Campos (escala) |
|---|---|---|
| `musculo` | el músculo | `bombeo` y `carga` (1–3), `agujetas` (1–3) |
| `ejercicio` | el ejercicio | `dolor` (0/1) |
| `dia` | `energia` o `sueno` | el valor 1–3 va en `carga` |

### Nutrición

| Endpoint | Método | Entrada | Respuesta |
|---|---|---|---|
| `guardar_proteina.php` | POST | `{fecha, proteina_g (0–600), porciones: {id: cantidad}}`, ver la nota de abajo | `{ok}`. Guarda el **total** del día; reenviarlo no duplica. |
| `get_nutricion.php` | GET | `dias` (1–180, defecto 14) | `{ok, meta: {proteina_min, proteina_max, kcal, peso, enfoque, actualizado_en} \| null, dias: [{fecha, proteina_g, porciones}]}` |
| `guardar_meta_nutricion.php` | POST | `{proteina_min, proteina_max (20–500), kcal? (800–6000), peso?, enfoque?}` | `{ok}` (lo sube el motor) |
| `guardar_menu.php` | POST | `{semana_inicio, menu: {dias: [...], …}}`, hasta 400 KB | `{ok}` (lo sube el motor) |
| `get_menu.php` | GET | `fecha` (opcional; hoy) | `{ok, menu \| null}`: el menú más reciente que empezó en las 2 semanas previas a `fecha` |
| `guardar_peso.php` | POST | `{fecha, peso (30–250), cintura? (40–200)}` | `{ok}`. Un pesaje por día (upsert); sin `cintura` conserva la que ya hubiera ese día. Lo usan la app y el dashboard. |
| `get_peso.php` | GET | `dias` (1–3650, defecto 60) | `{ok, pesos: [{fecha, peso, cintura \| null}]}`, del más viejo al más nuevo (la app y `exportar_local.py`) |

Reglas de `porciones` en `guardar_proteina.php`:

- **Ids:** `[a-z0-9_]{1,24}`, hasta 40 por día.
- **Cantidades:** 0–50 en las porciones normales.
- **Claves `menu_<tiempo>`** ("Lo comí"): guardan gramos, hasta 300.
- **`creatina`:** vale 1 cuando la tomaste.

---

## 9. Modelo de datos (MySQL)

| Tabla | Contenido |
|---|---|
| `plan_rutina` | Plan semanal: una fila por ejercicio, técnica y orden de cada día. |
| `registro_series` | Cada serie real (peso, reps, RPE, notas). `tonelaje_serie` es una columna generada. Llave foránea al plan con `ON DELETE SET NULL`. |
| `sincronizaciones_plan` | Bitácora de cada subida de plan. |
| `feedback_sesion` *(auto)* | Encuesta: músculo, ejercicio, energía y sueño, únicos por (fecha, tipo, clave). |
| `preferencia_ejercicio` *(auto)* | "Usar siempre": `original` → `reemplazo`. |
| `push_suscripciones` *(auto)* | Suscripciones Web Push, únicas por hash del endpoint. |
| `nutricion_dia` *(auto)* | Proteína del día: `fecha` es la llave, con `proteina_g` y `porciones` (JSON). |
| `nutricion_meta` *(auto)* | Una sola fila (`id = 1`) con el rango de proteína, kcal, peso y enfoque. |
| `menu_semana` *(auto)* | Un menú por semana (`semana_inicio`, `datos` en JSON). |
| `peso_corporal` *(auto)* | Un pesaje por día: `fecha` es la llave, con `peso` y `cintura` (opcional). Fuente de las calorías adaptativas; el motor lo baja a `peso_corporal.csv`. |

Todas están también en `infinityfree/schema.sql`.

---

## 10. Pruebas y despliegue

Cada push a `main` que toque `app/`, `infinityfree/`, `python-engine/` o `instancias/instancias.json` sigue estos pasos:

1. **Pruebas (6 suites).** Si una falla, no se sube nada.

   | Suite | Qué comprueba |
   |---|---|
   | `test_motor.py` | Reglas del motor, nutrición, menú, calorías por día, presupuesto, peso corporal (54 secciones). |
   | `test_menu.py` | Menú de 50 opciones: reglas DASH y mediterránea, énfasis, variedad, barrido de 108 perfiles. |
   | `test_funcional.py` | Dashboard y helpers, aislamiento del modo demo y su API, menú en demo, **selectores CSS duplicados** en `app/src/styles.css`. |
   | `test_plan_qa.py` | 35 criterios de calidad del plan. |
   | `test_barrido.py` | 13 440 semanas sin violar topes. |
   | `test_simulacion.py` | 9 atletas virtuales progresan con cargas realistas. |

2. **Build y armado:** `ng build` y `servidor/armar_deploy.sh`, que arma `deploy/` sin `config.php`.
3. **Subida por FTPS** a `htdocs/` de InfinityFree.
4. **Copias de otras personas:** para cada entrada de `instancias/instancias.json`, la misma app compilada con su API y su token, a su InfinityFree.

Secretos de GitHub:

- `FTP_USUARIO` y `FTP_PASSWORD`, opcionalmente `FTP_SERVIDOR`;
- por persona: `TOKEN_<CLAVE>`, `FTP_USUARIO_<CLAVE>` y `FTP_PASSWORD_<CLAVE>`.

La VM no la actualiza el CI: `cd ~/gym && git pull && bash servidor/instalar_vm.sh`.

**Revisión tras cada cambio:**

- las 6 suites en verde;
- el despliegue en verde;
- la página en vivo carga el bundle nuevo (comparar `main-*.js` con `index.html` del servidor);
- revisar en el navegador a 375 px la rutina, la barra de progreso, Guardar, Historial, Semana y Comida, y el dashboard.

---

## 11. Glosario

| Término | Significado |
|---|---|
| **Top Set** | La serie más pesada del día. Doble progresión: primero completar el rango de reps, luego subir carga. |
| **Back-off** | Series al ~80 % del Top Set, con más repeticiones. |
| **RPE / RIR** | Esfuerzo de 1 a 10 / repeticiones en reserva (RPE 8 = RIR 2). |
| **e1RM** | 1RM estimado con el peso, las reps y el RPE de una serie. |
| **AMRAP, Rest-Pause, Drop Set** | Técnicas al fallo, solo en la última serie de S3–S4. |
| **Deload (S5)** | Misma intensidad, mitad de volumen, sin fallo. |
| **MEV / MAV / MRV** | Volumen mínimo efectivo / adaptativo / máximo recuperable, en series por músculo y semana. |
| **MET** | Gasto de una actividad en múltiplos del reposo. Calorías netas = (MET − 1) × kg × horas. |
| **Calorías adaptativas** | Ajuste de kcal según la tendencia real del peso, no por fórmula. |

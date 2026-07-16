# `app/` — App Angular de producción (capa Cliente)

La aplicación con la que entrenás en el gimnasio. Es una **SPA en Angular 20**
(standalone components + signals) que se compila y se sube a InfinityFree (`htdocs/`).
Es la versión **oficial/de producción** (la carpeta `angular-app/` es experimental).

> Documentación técnica completa del proyecto: [`../DOCUMENTACION.md`](../DOCUMENTACION.md)

## Qué hace

- Carga la sesión del día desde la API (`get_rutina_hoy.php`).
- Muestra **una tarjeta por ejercicio** con sus series (Top Set + Back-off juntos).
- **Diseño adaptado a cada ejercicio** (`medidaDe`): fuerza → peso+reps+RPE,
  cardio → minutos, plancha → segundos, carry → metros, etc.
- Cronómetro de descanso basado en timestamp (sobrevive el segundo plano).
- Cambio de ejercicio por **alternativas por función de movimiento** (un press se sustituye por otro press, no por cualquier ejercicio del mismo músculo).
- **Reprogramar la semana** (mover el día de descanso, client-side).
- Mapa muscular en SVG inline, racha, tema claro/oscuro.
- Al terminar: "Guardar" → `guardar_entreno.php`.

### Funciones avanzadas

- **PWA instalable** (manifest + service worker + ícono) con caché offline del shell y del plan del día.
- **Rediseño mobile-first (iPhone)**: barra de acciones fija abajo (Guardar 52 px + toggles), barra de progreso de la sesión, `safe-area` respetado.
- **Guardado blindado**: cola offline con reenvío automático, anti doble-envío, caché del plan.
- **Readiness** pre-sesión (😃/😐/😫) que modula el RPE objetivo del día.
- **Objetivo de RPE por serie**, **Historial** (📓, mejor serie por e1RM) y **confeti de PR** 🎉 al romper un récord de 1RM estimado.

## Estructura

```
public/                      → assets PWA (manifest.webmanifest, sw.js, icon.svg)
src/
├── main.ts                  → bootstrap de Angular
├── index.html               → registra el service worker + manifest
├── styles.css               → estilos globales (tema claro/oscuro, barra inferior, progreso)
├── environments/
│   └── environment.ts       → apiBaseUrl + apiToken (¡el MISMO de config.php!)
└── app/
    ├── app.component.ts      → AppComponent (sesión, cola offline, readiness, historial, PRs)
    ├── app.component.html    → template de la vista
    ├── entreno-data.ts       → tipos, clasificadores (medidaDe, alternativas por función, RPE objetivo)
    ├── rutina-api.service.ts → RutinaApiService (getRutinaHoy, getHistorial, guardarEntreno)
    └── muscle-map.component.ts → MuscleMapComponent (mapa muscular SVG)
```

## Desarrollo

```bash
npm install
npm start            # ng serve (dev, http://localhost:4200)
npx ng build         # producción → dist/gym-rutinas/browser/
```

## Despliegue

Subir el contenido de `dist/gym-rutinas/browser/` a `htdocs/`, sobrescribiendo y
borrando los `main-*`/`styles-*` viejos. Incluye los assets PWA (`manifest.webmanifest`,
`icon.svg`, `sw.js`). **No tocar `api/`** (salvo subir `get_historial.php` una vez).

> Atajo: `Construir app para subir.bat` (en la raíz) compila y deja `deploy/` listo.

## Configuración

Editar `src/environments/environment.ts`:
```ts
export const environment = {
  apiBaseUrl: 'https://TU-DOMINIO/api',
  apiToken: 'EL_MISMO_TOKEN_QUE_config.php'
};
```

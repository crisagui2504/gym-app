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
- Cambio de ejercicio por **alternativas** del mismo grupo muscular.
- **Reprogramar la semana** (mover el día de descanso, client-side).
- Mapa muscular en SVG inline, racha, tema claro/oscuro.
- Al terminar: "Guardar" → `guardar_entreno.php`.

## Estructura

```
src/
├── main.ts                  → bootstrap de Angular
├── index.html
├── styles.css               → estilos globales (incluye tema claro/oscuro)
├── environments/
│   └── environment.ts       → apiBaseUrl + apiToken (¡el MISMO de config.php!)
└── app/
    ├── app.component.ts      → AppComponent (toda la lógica de la sesión)
    ├── app.component.html    → template de la vista
    ├── entreno-data.ts       → tipos, catálogos y clasificadores (medidaDe, etc.)
    ├── rutina-api.service.ts → RutinaApiService (cliente HTTP con X-API-Token)
    └── muscle-map.component.ts → MuscleMapComponent (mapa muscular SVG)
```

## Desarrollo

```bash
npm install
npm start            # ng serve (dev, http://localhost:4200)
npx ng build         # producción → dist/gym-rutinas/browser/
```

## Despliegue

Subir el contenido de `dist/gym-rutinas/browser/` (4 archivos) a `htdocs/`,
sobrescribiendo y borrando los `main-*`/`styles-*` viejos. **No tocar `api/`**.

> Atajo: `Construir app para subir.bat` (en la raíz) compila y deja `deploy/` listo.

## Configuración

Editar `src/environments/environment.ts`:
```ts
export const environment = {
  apiBaseUrl: 'https://TU-DOMINIO/api',
  apiToken: 'EL_MISMO_TOKEN_QUE_config.php'
};
```

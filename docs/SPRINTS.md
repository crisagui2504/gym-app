# Roadmap

## Sprint 1 - Infraestructura y API

Listo en esta base:

- `infinityfree/schema.sql`
- `infinityfree/api/get_rutina_hoy.php`
- `infinityfree/api/guardar_entreno.php`
- `infinityfree/api/exportar_csv.php`
- `infinityfree/api/actualizar_plan.php`

## Sprint 2 - App Angular

Base creada en `app/`:

- Tarjetas por ejercicio.
- Botones grandes para peso y repeticiones.
- Selector RPE 1-10.
- Texto tactico `Sugerido hoy`.
- Servicio HTTP conectado a los endpoints.

## Sprint 3 - Despliegue

Pendiente cuando tengas dominio y credenciales:

```powershell
cd app
pnpm install
pnpm build
```

Sube el build de Angular a `htdocs/` y `infinityfree/api/` a `htdocs/api/`.

## Sprint 4 - Cerebro local

Base creada en `python-engine/planificar.py`.

## Sprint 5 - Dashboard local (reemplaza Power BI)

Dashboard Dash/Plotly en `python-engine/dashboard.py` (localhost:8050). Power BI
queda como alternativa legacy (`powerbi_guide.md`).

## Sprint 6 - App autónoma

Generador dinámico de planes (`generador.py`) + enfoque configurable desde el
dashboard + ejecutable de un clic (`GymTracker.bat`).

## Sprint 7 - Motor basado en evidencia científica

Ajuste de todas las reglas de programación a la literatura 2016–2025: fallo
dosificado (RIR), descansos, volumen dosis-respuesta, doble progresión, deload
reactivo, e1RM, nutrición en gramos, peso + cintura, PWA, rediseño mobile-first,
backups y automatización semanal.

## Sprint 8 - Inteligencia por submúsculos y anti-sobrecarga

Ponderación de estímulo por submúsculo, selección por ganancia marginal
(anti-redundancia), topes de compuestos por región, protección lumbar (bisagras
axiales), rotación por mesociclo y vista del mesociclo completo — todo validado
con simulaciones automáticas (`tests/test_motor.py`).

> El fundamento científico y el detalle de los Sprints 7–8 están en
> [`CAMBIOS_EVIDENCIA.md`](CAMBIOS_EVIDENCIA.md).

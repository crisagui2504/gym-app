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

## Sprint 5 - Power BI

Conecta Power BI a la URL:

```text
https://TU-DOMINIO.infinityfreeapp.com/api/exportar_csv.php?token=TU_TOKEN
```

Medida DAX inicial:

```DAX
Tonelaje Total = SUMX(registro_series, registro_series[reps_hechas] * registro_series[peso_kg])
```

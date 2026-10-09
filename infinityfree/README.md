# InfinityFree

Esta carpeta contiene solo lo que pertenece al servidor InfinityFree.

## Instalacion

1. Crea la base de datos MySQL en InfinityFree.
2. En phpMyAdmin, ejecuta `schema.sql`.
3. Copia `api/config.example.php` como `api/config.php`.
4. Llena `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` y cambia `API_TOKEN`.
5. Doble clic en `Construir app para subir.bat` (raiz del repo) y sube TODO el
   contenido de `deploy/` a `htdocs/`: app + `.htaccess` + `api/` (sin
   `config.php`, que solo vive en el servidor y nunca se pisa).
   Las tablas nuevas (encuesta, avisos) se crean solas la primera vez.

## Endpoints

- `GET /api/get_rutina_hoy.php?token=...&fecha=2026-06-22`
- `GET /api/get_historial.php?token=...&dias=30` — últimas sesiones (panel Historial de la app)
- `POST /api/guardar_entreno.php`
- `GET /api/exportar_csv.php?token=...`
- `POST /api/actualizar_plan.php`

Para `POST`, manda el token en el header `X-API-Token`.

> Al actualizar: vuelve a correr el `.bat` y sube `deploy/` entero. Borra del
> servidor los `main-*.js` / `styles-*.css` viejos.

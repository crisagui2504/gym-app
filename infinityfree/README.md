# InfinityFree

Esta carpeta contiene solo lo que pertenece al servidor InfinityFree.

## Instalacion

1. Crea la base de datos MySQL en InfinityFree.
2. En phpMyAdmin, ejecuta `schema.sql`.
3. Copia `api/config.example.php` como `api/config.php`.
4. Llena `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` y cambia `API_TOKEN`.
5. Sube la carpeta `api/` a `htdocs/api/`.
6. Cuando compiles Angular, sube el contenido de `app/dist/gym-rutinas/browser/` o `app/dist/gym-rutinas/` a `htdocs/`.

## Endpoints

- `GET /api/get_rutina_hoy.php?token=...&fecha=2026-06-22`
- `POST /api/guardar_entreno.php`
- `GET /api/exportar_csv.php?token=...`
- `POST /api/actualizar_plan.php`

Para `POST`, manda el token en el header `X-API-Token`.

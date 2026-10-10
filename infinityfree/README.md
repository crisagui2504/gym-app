# InfinityFree (API y app publicada)

Esta carpeta tiene solo lo que vive en InfinityFree: la API PHP, el esquema de la base de datos y el `.htaccess`. El detalle de cada endpoint está en [`../DOCUMENTACION.md`](../DOCUMENTACION.md#8-api-php).

## Instalación

1. Crea la base MySQL en InfinityFree y, en phpMyAdmin, importa `schema.sql`. Las tablas marcadas como *(auto)* abajo también se crean solas la primera vez.
2. Copia `api/config.example.php` como `config.php` **directo en el servidor** (`htdocs/api/`) y llena `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` y un `API_TOKEN` largo. `config.php` no se versiona y nadie lo sube por ti: ni el CI ni `deploy/` lo tocan.
3. La app y la API las publica GitHub Actions en cada push a `main` (por FTPS). A mano: `Construir app para subir.bat` en la raíz arma `deploy/` para subirlo a `htdocs/`.

## Endpoints

Todos piden `X-API-Token` (o `?token=` en GET).

| Grupo | Endpoints |
|---|---|
| Entreno | `get_rutina_hoy.php`, `get_historial.php`, `guardar_entreno.php`, `actualizar_plan.php`, `exportar_csv.php`, `get_notas.php` |
| Encuesta y preferencias | `guardar_feedback.php`, `get_feedback.php`, `guardar_preferencia.php`, `get_preferencias.php` |
| Avisos push | `guardar_suscripcion.php`, `get_suscripciones.php` |
| Nutrición | `guardar_proteina.php`, `get_nutricion.php`, `guardar_meta_nutricion.php`, `guardar_menu.php`, `get_menu.php` |
| Peso corporal | `guardar_peso.php`, `get_peso.php` |

Archivos de apoyo: `bootstrap.php` (CORS, PDO, token, JSON) y `*_tabla.php` (crean las tablas automáticas).

## Tablas

`plan_rutina`, `registro_series`, `sincronizaciones_plan`, y las automáticas:

- `feedback_sesion`
- `preferencia_ejercicio`
- `push_suscripciones`
- `nutricion_dia`
- `nutricion_meta`
- `menu_semana`
- `peso_corporal`

## `.htaccess`

- Lo que no es un archivo va a `index.html` (SPA), lo que evita los 404 que InfinityFree castiga.
- `index.html`, `sw.js` y el manifiesto van con `Cache-Control: no-cache`, para que el teléfono cargue la versión nueva después de cada despliegue.

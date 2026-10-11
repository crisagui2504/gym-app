<?php
declare(strict_types=1);

// "No me gusta" del menu: recetas o alimentos que no quieres volver a ver.
// Lo marcan la app (boton en cada comida) o el dashboard; el generador del menu
// (python-engine/menu.py) los excluye la proxima vez que arma la semana.
// La tabla se crea sola la primera vez: no hace falta pasar por phpMyAdmin.
function asegurar_tabla_no_me_gusta(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS menu_no_me_gusta (
            tipo VARCHAR(10) NOT NULL,
            id VARCHAR(60) NOT NULL,
            creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (tipo, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

<?php
declare(strict_types=1);

// Menu semanal barato que genera el motor (python-engine/menu.py): una fila por
// semana con todo el menu en JSON (dias, comidas, lista del super, costo).
// La tabla se crea sola la primera vez.
function asegurar_tabla_menu(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS menu_semana (
            semana_inicio DATE NOT NULL PRIMARY KEY,
            datos MEDIUMTEXT NOT NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

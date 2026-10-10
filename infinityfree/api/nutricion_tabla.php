<?php
declare(strict_types=1);

// Nutricion: proteina del dia (la registra la app) y la meta (la sube el motor).
//   nutricion_dia   una fila por dia: total de proteina y las porciones tocadas
//                   en la app ({"huevo": 3, "frijol": 1}); se sobrescribe entera.
//   nutricion_meta  una sola fila (id = 1): rango de proteina y kcal objetivo,
//                   calculados por el motor con tu peso y tu enfoque.
// Las tablas se crean solas la primera vez: no hace falta pasar por phpMyAdmin.
function asegurar_tablas_nutricion(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS nutricion_dia (
            fecha DATE NOT NULL PRIMARY KEY,
            proteina_g DECIMAL(6,1) NOT NULL DEFAULT 0,
            porciones VARCHAR(2000) NOT NULL DEFAULT '{}',
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS nutricion_meta (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            proteina_min SMALLINT UNSIGNED NOT NULL,
            proteina_max SMALLINT UNSIGNED NOT NULL,
            kcal SMALLINT UNSIGNED NULL,
            peso DECIMAL(5,1) NULL,
            enfoque VARCHAR(40) NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

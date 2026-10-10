<?php
declare(strict_types=1);

// Peso corporal: un pesaje por dia (lo registran la app o el dashboard).
// Es la fuente de las calorias adaptativas del motor (python-engine/nutricion.py),
// que lo baja a peso_corporal.csv con exportar_local.py.
// La tabla se crea sola la primera vez: no hace falta pasar por phpMyAdmin.
function asegurar_tabla_peso(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS peso_corporal (
            fecha DATE NOT NULL PRIMARY KEY,
            peso DECIMAL(5,1) NOT NULL,
            cintura DECIMAL(5,1) NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

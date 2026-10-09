<?php
declare(strict_types=1);

// "Usar siempre": ejercicio del plan -> el que prefieres (tu gym no tiene la
// maquina, no te gusta...). El motor aplica el cambio cada semana. La tabla se
// crea sola la primera vez.
function asegurar_tabla_preferencias(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS preferencia_ejercicio (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            original VARCHAR(160) NOT NULL,
            reemplazo VARCHAR(160) NOT NULL,
            creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_preferencia_original (original)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

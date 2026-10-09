<?php
declare(strict_types=1);

// Suscripciones a notificaciones push (Web Push). Las ENVIA la VM / el PC con
// pywebpush (InfinityFree no puede: no tiene tareas programadas). Aqui solo se
// guardan. La tabla se crea sola la primera vez.
function asegurar_tabla_push(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS push_suscripciones (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            endpoint VARCHAR(500) NOT NULL,
            endpoint_hash CHAR(64) NOT NULL,
            p256dh VARCHAR(200) NOT NULL,
            auth VARCHAR(100) NOT NULL,
            creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_push_endpoint (endpoint_hash)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

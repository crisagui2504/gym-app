<?php
declare(strict_types=1);

// Check-in semanal de nutricion (una sola fila, id = 1):
//   evaluacion     JSON que sube el motor (python-engine/nutricion.py checkin):
//                  tendencia del peso, objetivo, estado y kcal sugeridas.
//   aplicar_delta  el ajuste que tocaste en la app ("Aplicar"); el motor lo pasa
//                  a tu config en su siguiente corrida y lo vuelve a NULL.
// La tabla se crea sola la primera vez: no hace falta pasar por phpMyAdmin.
function asegurar_tabla_checkin(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS nutricion_checkin (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            evaluacion MEDIUMTEXT NULL,
            aplicar_delta SMALLINT NULL,
            aplicar_pedido TIMESTAMP NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

<?php
declare(strict_types=1);

// Datos del reloj (Amazfit -> Zepp -> Apple Salud), ya resumidos por dia en el
// telefono (app/src/app/salud.ts): el pulso minuto a minuto nunca llega aqui.
// Los usa el motor (python-engine/reloj.py): sueno y pulso nocturno para la
// recuperacion, entrenos para la duracion real de la sesion y los pasos para el
// check-in de nutricion. Las tablas se crean solas la primera vez.
function asegurar_tablas_reloj(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS reloj_dias (
            fecha DATE NOT NULL PRIMARY KEY,
            sueno_min SMALLINT UNSIGNED NULL,
            pulso_noche TINYINT UNSIGNED NULL,
            pulso_reposo TINYINT UNSIGNED NULL,
            hrv DECIMAL(5,1) NULL,
            pasos MEDIUMINT UNSIGNED NULL,
            peso DECIMAL(5,1) NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS reloj_entrenos (
            inicio DATETIME NOT NULL,
            tipo VARCHAR(60) NOT NULL,
            fin DATETIME NOT NULL,
            minutos DECIMAL(5,1) NOT NULL,
            pulso_prom TINYINT UNSIGNED NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (inicio, tipo)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

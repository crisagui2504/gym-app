<?php
declare(strict_types=1);

// Encuesta de la sesion (estilo RP Hypertrophy): lo que la app pregunta al
// terminar y al empezar, para que el motor ajuste el volumen de cada musculo.
//   tipo='musculo'   clave=id del musculo (pecho, dorsales...)
//       bombeo   1 poco | 2 bueno | 3 brutal              (al terminar)
//       carga    1 facil | 2 justa | 3 demasiado          (al terminar)
//       agujetas 1 nada | 2 sanaron justo | 3 aun duelen  (al empezar: de la vez anterior)
//   tipo='ejercicio' clave=nombre del ejercicio
//       dolor    1 = molestia ARTICULAR (no muscular) en ese ejercicio
//   tipo='dia'       clave='energia' | 'sueno'  (como llegas hoy; el valor va en `carga`)
//       energia  1 bien | 2 normal | 3 sin energia
//       sueno    1 bien | 2 regular | 3 mal
// La tabla se crea sola la primera vez: no hace falta pasar por phpMyAdmin.
function asegurar_tabla_feedback(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS feedback_sesion (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            tipo VARCHAR(16) NOT NULL,
            clave VARCHAR(160) NOT NULL,
            bombeo TINYINT UNSIGNED NULL,
            carga TINYINT UNSIGNED NULL,
            agujetas TINYINT UNSIGNED NULL,
            dolor TINYINT UNSIGNED NULL,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_feedback (fecha, tipo, clave),
            INDEX idx_feedback_fecha (fecha)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

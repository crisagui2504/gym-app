<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

// Ultima nota del usuario por ejercicio ("asiento en 4", "agarre neutro"...),
// para mostrarla la proxima vez que toque. Ultimos 180 dias.
// Sin funciones de ventana: compatible con MySQL 5.7 / MariaDB de InfinityFree.
$sql = <<<SQL
SELECT r.ejercicio, r.notas, r.fecha_entreno
FROM registro_series r
JOIN (
    SELECT ejercicio, MAX(id) AS id
    FROM registro_series
    WHERE notas IS NOT NULL AND notas <> ''
      AND fecha_entreno >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
    GROUP BY ejercicio
) u ON u.id = r.id
SQL;

json_response(['ok' => true, 'notas' => db()->query($sql)->fetchAll()]);

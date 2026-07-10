<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

// Historial reciente para la app (panel "Historial"): series de los ultimos
// N dias (por defecto 30, tope 90), mas recientes primero.
$dias = (int) ($_GET['dias'] ?? 30);
$dias = max(1, min(90, $dias));

$sql = <<<SQL
SELECT fecha_entreno, ejercicio, tecnica, numero_serie, peso_kg, repeticiones, rpe
FROM registro_series
WHERE fecha_entreno >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
ORDER BY fecha_entreno DESC, id ASC
SQL;

$stmt = db()->prepare($sql);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();

json_response([
    'ok' => true,
    'dias' => $dias,
    'series' => $stmt->fetchAll(),
]);

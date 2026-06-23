<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

$data = json_input();
$fecha = $data['fecha_entreno'] ?? date('Y-m-d');
$items = $data['items'] ?? [];

if (!is_array($items) || count($items) === 0) {
    json_response(['ok' => false, 'error' => 'No hay series para guardar'], 400);
}

$pdo = db();
$pdo->beginTransaction();

try {
    $stmt = $pdo->prepare(
        'INSERT INTO registro_series
        (plan_id, fecha_entreno, ejercicio, tecnica, numero_serie, peso_kg, repeticiones, rpe, notas)
        VALUES
        (:plan_id, :fecha_entreno, :ejercicio, :tecnica, :numero_serie, :peso_kg, :repeticiones, :rpe, :notas)'
    );

    $inserted = 0;
    foreach ($items as $item) {
        $rpe = (int) ($item['rpe'] ?? 0);
        if ($rpe < 1 || $rpe > 10) {
            throw new InvalidArgumentException('RPE debe estar entre 1 y 10');
        }

        $stmt->execute([
            ':plan_id' => isset($item['plan_id']) ? (int) $item['plan_id'] : null,
            ':fecha_entreno' => $fecha,
            ':ejercicio' => trim((string) ($item['ejercicio'] ?? '')),
            ':tecnica' => $item['tecnica'] ?? null,
            ':numero_serie' => (int) ($item['numero_serie'] ?? 1),
            ':peso_kg' => (float) ($item['peso_kg'] ?? 0),
            ':repeticiones' => (int) ($item['repeticiones'] ?? 0),
            ':rpe' => $rpe,
            ':notas' => $item['notas'] ?? null,
        ]);
        $inserted++;
    }

    $pdo->commit();
    json_response(['ok' => true, 'inserted' => $inserted]);
} catch (Throwable $e) {
    $pdo->rollBack();
    json_response(['ok' => false, 'error' => $e->getMessage()], 400);
}

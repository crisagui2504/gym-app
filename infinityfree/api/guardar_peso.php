<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/peso_tabla.php';
require_token();

// POST {fecha: 'YYYY-MM-DD', peso: 74.6, cintura: 83.0 (opcional)}
// Un pesaje por dia: volver a mandarlo lo sobrescribe (reenviarlo es seguro).
// Sin cintura se conserva la que ya hubiera ese dia.
$data = json_input();
$fecha = (string) ($data['fecha'] ?? '');
$dt = DateTimeImmutable::createFromFormat('Y-m-d', $fecha);
if (!$dt || $dt->format('Y-m-d') !== $fecha) {
    json_response(['ok' => false, 'error' => 'Fecha invalida'], 400);
}

$peso = filter_var($data['peso'] ?? null, FILTER_VALIDATE_FLOAT);
if ($peso === false || $peso < 30 || $peso > 250) {
    json_response(['ok' => false, 'error' => 'Peso fuera de rango (30-250 kg)'], 400);
}

$cintura = null;
if (isset($data['cintura']) && $data['cintura'] !== '') {
    $cintura = filter_var($data['cintura'], FILTER_VALIDATE_FLOAT);
    if ($cintura === false || $cintura < 40 || $cintura > 200) {
        json_response(['ok' => false, 'error' => 'Cintura fuera de rango (40-200 cm)'], 400);
    }
}

try {
    $pdo = db();
    asegurar_tabla_peso($pdo);
    $stmt = $pdo->prepare(
        'INSERT INTO peso_corporal (fecha, peso, cintura) VALUES (:fecha, :peso, :cintura)
         ON DUPLICATE KEY UPDATE peso = VALUES(peso), cintura = COALESCE(VALUES(cintura), cintura)'
    );
    $stmt->execute([
        ':fecha' => $fecha,
        ':peso' => round((float) $peso, 1),
        ':cintura' => $cintura === null ? null : round((float) $cintura, 1),
    ]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

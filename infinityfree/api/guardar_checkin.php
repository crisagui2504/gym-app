<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/checkin_tabla.php';
require_token();

// POST {evaluacion: {...}, aplicado?: true}   (lo sube el motor)
// Guarda la evaluacion de la semana. Con aplicado: true, borra el ajuste que se
// pidio desde la app (el motor ya lo paso a tu config).
$data = json_input();
$evaluacion = $data['evaluacion'] ?? null;
if (!is_array($evaluacion)) {
    json_response(['ok' => false, 'error' => 'Evaluacion invalida'], 400);
}
$json = json_encode($evaluacion, JSON_UNESCAPED_UNICODE);
if ($json === false || strlen($json) > 20000) {
    json_response(['ok' => false, 'error' => 'Evaluacion demasiado grande'], 400);
}

try {
    $pdo = db();
    asegurar_tabla_checkin($pdo);
    $limpiar = !empty($data['aplicado']);
    $stmt = $pdo->prepare(
        'INSERT INTO nutricion_checkin (id, evaluacion) VALUES (1, :e)
         ON DUPLICATE KEY UPDATE evaluacion = VALUES(evaluacion)'
         . ($limpiar ? ', aplicar_delta = NULL, aplicar_pedido = NULL' : '')
    );
    $stmt->execute([':e' => $json]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

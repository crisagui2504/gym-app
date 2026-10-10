<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/nutricion_tabla.php';
require_token();

// POST {fecha: 'YYYY-MM-DD', proteina_g: 128.5, porciones: {"huevo": 3, "frijol": 1}}
// Guarda el TOTAL del dia (la app manda siempre el estado completo): reenviarlo
// es seguro, no duplica.
$data = json_input();
$fecha = (string) ($data['fecha'] ?? '');
$dt = DateTimeImmutable::createFromFormat('Y-m-d', $fecha);
if (!$dt || $dt->format('Y-m-d') !== $fecha) {
    json_response(['ok' => false, 'error' => 'Fecha invalida'], 400);
}

$gramos = filter_var($data['proteina_g'] ?? null, FILTER_VALIDATE_FLOAT);
if ($gramos === false || $gramos < 0 || $gramos > 600) {
    json_response(['ok' => false, 'error' => 'Proteina fuera de rango'], 400);
}

$porciones = $data['porciones'] ?? [];
if (!is_array($porciones) || count($porciones) > 40) {
    json_response(['ok' => false, 'error' => 'Porciones invalidas'], 400);
}
$limpias = [];
foreach ($porciones as $id => $n) {
    $cant = filter_var($n, FILTER_VALIDATE_INT);
    if (!is_string($id) || !preg_match('/^[a-z0-9_]{1,24}$/', $id) || $cant === false || $cant < 0 || $cant > 50) {
        json_response(['ok' => false, 'error' => 'Porciones invalidas'], 400);
    }
    if ($cant > 0) {
        $limpias[$id] = $cant;
    }
}

try {
    $pdo = db();
    asegurar_tablas_nutricion($pdo);
    $stmt = $pdo->prepare(
        'INSERT INTO nutricion_dia (fecha, proteina_g, porciones) VALUES (:fecha, :g, :p)
         ON DUPLICATE KEY UPDATE proteina_g = VALUES(proteina_g), porciones = VALUES(porciones)'
    );
    $stmt->execute([
        ':fecha' => $fecha,
        ':g' => round((float) $gramos, 1),
        ':p' => json_encode((object) $limpias, JSON_UNESCAPED_UNICODE),
    ]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

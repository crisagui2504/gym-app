<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/checkin_tabla.php';
require_token();

// POST {kcal_delta: 150}   (el boton "Aplicar" del check-in en la app)
// Solo se acepta el ajuste que sugirio el motor en su ultima evaluacion: la app no
// puede inventar otro. Con {cancelar: true} se retira el pedido. El motor lo pasa
// a tu config en su siguiente corrida (cada 3 horas en la VM).
$data = json_input();

try {
    $pdo = db();
    asegurar_tabla_checkin($pdo);
    if (!empty($data['cancelar'])) {
        $pdo->exec('UPDATE nutricion_checkin SET aplicar_delta = NULL, aplicar_pedido = NULL WHERE id = 1');
        json_response(['ok' => true, 'cancelado' => true]);
    }
    $delta = filter_var($data['kcal_delta'] ?? null, FILTER_VALIDATE_INT);
    if ($delta === false || $delta === 0 || abs($delta) > 300) {
        json_response(['ok' => false, 'error' => 'Ajuste fuera de rango'], 400);
    }
    $fila = $pdo->query('SELECT evaluacion FROM nutricion_checkin WHERE id = 1')->fetch();
    $e = $fila ? json_decode((string) $fila['evaluacion'], true) : null;
    if (!is_array($e) || (int) ($e['kcal_delta'] ?? 0) !== $delta) {
        json_response(['ok' => false, 'error' => 'El ajuste ya no coincide con la sugerencia'], 409);
    }
    $pdo->prepare('UPDATE nutricion_checkin SET aplicar_delta = ?, aplicar_pedido = NOW() WHERE id = 1')->execute([$delta]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

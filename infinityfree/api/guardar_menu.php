<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/menu_tabla.php';
require_token();

// POST {semana_inicio: 'YYYY-MM-DD', menu: {...}}  (lo sube el motor)
$data = json_input();
$semana = (string) ($data['semana_inicio'] ?? '');
$dt = DateTimeImmutable::createFromFormat('Y-m-d', $semana);
if (!$dt || $dt->format('Y-m-d') !== $semana) {
    json_response(['ok' => false, 'error' => 'Fecha invalida'], 400);
}
$menu = $data['menu'] ?? null;
if (!is_array($menu) || !isset($menu['dias']) || !is_array($menu['dias'])) {
    json_response(['ok' => false, 'error' => 'Menu invalido'], 400);
}
$json = json_encode($menu, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
if ($json === false || strlen($json) > 400000) {
    json_response(['ok' => false, 'error' => 'Menu demasiado grande'], 400);
}

try {
    $pdo = db();
    asegurar_tabla_menu($pdo);
    $stmt = $pdo->prepare(
        'INSERT INTO menu_semana (semana_inicio, datos) VALUES (:s, :d)
         ON DUPLICATE KEY UPDATE datos = VALUES(datos)'
    );
    $stmt->execute([':s' => $semana, ':d' => $json]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

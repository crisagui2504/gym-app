<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/no_me_gusta_tabla.php';
require_token();

// POST {tipo: 'receta' | 'alimento', id: 'tacos_lentejas'}          -> lo marca
// POST {tipo: 'receta' | 'alimento', id: 'tacos_lentejas', baja: true} -> lo quita
// Marcarlo dos veces es seguro (no duplica).
$data = json_input();
$tipo = (string) ($data['tipo'] ?? '');
$id = trim((string) ($data['id'] ?? ''));
if (!in_array($tipo, ['receta', 'alimento'], true)) {
    json_response(['ok' => false, 'error' => 'Tipo invalido'], 400);
}
if (!preg_match('/^[a-z0-9_]{1,60}$/', $id)) {
    json_response(['ok' => false, 'error' => 'Id invalido'], 400);
}

try {
    $pdo = db();
    asegurar_tabla_no_me_gusta($pdo);
    if (!empty($data['baja'])) {
        $pdo->prepare('DELETE FROM menu_no_me_gusta WHERE tipo = ? AND id = ?')->execute([$tipo, $id]);
        json_response(['ok' => true, 'baja' => true]);
    }
    $pdo->prepare('INSERT IGNORE INTO menu_no_me_gusta (tipo, id) VALUES (?, ?)')->execute([$tipo, $id]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'No se pudo guardar'], 500);
}

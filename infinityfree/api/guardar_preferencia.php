<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/preferencias_tabla.php';
require_token();

// POST {original, reemplazo}  -> guarda (o cambia) la preferencia
// POST {original, baja: true} -> la quita (vuelve el ejercicio del plan)
$data = json_input();
$original = trim((string) ($data['original'] ?? ''));
$reemplazo = trim((string) ($data['reemplazo'] ?? ''));
if ($original === '' || strlen($original) > 480) {
    json_response(['ok' => false, 'error' => 'Ejercicio invalido'], 400);
}
$pdo = db();
asegurar_tabla_preferencias($pdo);

if (!empty($data['baja'])) {
    $pdo->prepare('DELETE FROM preferencia_ejercicio WHERE original = ?')->execute([$original]);
    json_response(['ok' => true, 'baja' => true]);
}
if ($reemplazo === '' || strlen($reemplazo) > 480 || strcasecmp($reemplazo, $original) === 0) {
    json_response(['ok' => false, 'error' => 'Reemplazo invalido'], 400);
}
$pdo->prepare(
    'INSERT INTO preferencia_ejercicio (original, reemplazo) VALUES (?, ?)
     ON DUPLICATE KEY UPDATE reemplazo = VALUES(reemplazo)'
)->execute([$original, $reemplazo]);
json_response(['ok' => true]);

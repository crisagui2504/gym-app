<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/push_tabla.php';
require_token();

// POST la PushSubscription del navegador: {endpoint, keys: {p256dh, auth}}.
// Con {"baja": true} se borra (el usuario apago los avisos o la VM vio que caduco).
$data = json_input();
$endpoint = trim((string) ($data['endpoint'] ?? ''));
if (!preg_match('#^https://[^\s]{10,490}$#', $endpoint)) {
    json_response(['ok' => false, 'error' => 'Suscripcion invalida'], 400);
}
$hash = hash('sha256', $endpoint);
$pdo = db();
asegurar_tabla_push($pdo);

if (!empty($data['baja'])) {
    $pdo->prepare('DELETE FROM push_suscripciones WHERE endpoint_hash = ?')->execute([$hash]);
    json_response(['ok' => true, 'baja' => true]);
}

$p256dh = (string) ($data['keys']['p256dh'] ?? '');
$auth = (string) ($data['keys']['auth'] ?? '');
if (!preg_match('/^[A-Za-z0-9_-]{40,200}$/', $p256dh) || !preg_match('/^[A-Za-z0-9_-]{10,100}$/', $auth)) {
    json_response(['ok' => false, 'error' => 'Claves invalidas'], 400);
}
$pdo->prepare(
    'INSERT INTO push_suscripciones (endpoint, endpoint_hash, p256dh, auth) VALUES (?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE p256dh = VALUES(p256dh), auth = VALUES(auth)'
)->execute([$endpoint, $hash, $p256dh, $auth]);
json_response(['ok' => true]);

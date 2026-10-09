<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/push_tabla.php';
require_token();

// Para avisos.py (VM / PC): a quien mandar las notificaciones.
$pdo = db();
asegurar_tabla_push($pdo);
json_response([
    'ok' => true,
    'suscripciones' => $pdo->query('SELECT endpoint, p256dh, auth FROM push_suscripciones')->fetchAll(),
]);

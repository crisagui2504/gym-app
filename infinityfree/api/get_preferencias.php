<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/preferencias_tabla.php';
require_token();

// Para la app (boton "volver al original") y el motor (aplica los cambios).
$pdo = db();
asegurar_tabla_preferencias($pdo);
json_response([
    'ok' => true,
    'preferencias' => $pdo->query('SELECT original, reemplazo FROM preferencia_ejercicio ORDER BY id')->fetchAll(),
]);

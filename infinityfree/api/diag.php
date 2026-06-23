<?php
// === ARCHIVO TEMPORAL DE DIAGNOSTICO ===
// Subir a htdocs/api/diag.php, abrir en el navegador con ?token=TU_TOKEN
// y BORRARLO despues. Reporta el estado real de la base de datos.
declare(strict_types=1);
require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

if (($_GET['token'] ?? '') !== API_TOKEN) {
    http_response_code(401);
    echo json_encode(['ok' => false, 'error' => 'Token invalido']);
    exit;
}

$out = ['ok' => true, 'pasos' => []];
try {
    $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $out['pasos']['conexion'] = 'OK';
    $out['version_mysql'] = $pdo->query('SELECT VERSION()')->fetchColumn();

    $tablas = $pdo->query('SHOW TABLES')->fetchAll(PDO::FETCH_COLUMN);
    $out['tablas'] = $tablas;

    foreach (['plan_rutina', 'registro_series', 'sincronizaciones_plan'] as $t) {
        if (in_array($t, $tablas, true)) {
            $out['conteos'][$t] = (int) $pdo->query("SELECT COUNT(*) FROM `$t`")->fetchColumn();
        } else {
            $out['conteos'][$t] = 'NO EXISTE';
        }
    }
} catch (Throwable $e) {
    http_response_code(200);
    $out['ok'] = false;
    $out['error'] = $e->getMessage();
}

echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);

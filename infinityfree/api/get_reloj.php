<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/reloj_tabla.php';
require_token();

// Datos del reloj de los ultimos N dias (por defecto 90, tope 400), del mas viejo
// al mas nuevo. Lo lee el motor (python-engine/reloj.py).
$dias = max(1, min(400, (int) ($_GET['dias'] ?? 90)));

$pdo = db();
asegurar_tablas_reloj($pdo);

$stmt = $pdo->prepare(
    'SELECT fecha, sueno_min, pulso_noche, pulso_reposo, hrv, pasos, peso FROM reloj_dias
     WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL :dias DAY) ORDER BY fecha ASC'
);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();
$num = static fn($v) => $v === null ? null : (float) $v;
$filas = [];
foreach ($stmt->fetchAll() as $f) {
    $filas[] = [
        'fecha' => $f['fecha'],
        'sueno_min' => $num($f['sueno_min']),
        'pulso_noche' => $num($f['pulso_noche']),
        'pulso_reposo' => $num($f['pulso_reposo']),
        'hrv' => $num($f['hrv']),
        'pasos' => $num($f['pasos']),
        'peso' => $num($f['peso']),
    ];
}

$stmt = $pdo->prepare(
    'SELECT inicio, fin, tipo, minutos, pulso_prom FROM reloj_entrenos
     WHERE inicio >= DATE_SUB(CURDATE(), INTERVAL :dias DAY) ORDER BY inicio ASC'
);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();
$entrenos = [];
foreach ($stmt->fetchAll() as $e) {
    $entrenos[] = [
        'inicio' => $e['inicio'],
        'fin' => $e['fin'],
        'tipo' => $e['tipo'],
        'minutos' => (float) $e['minutos'],
        'pulso_prom' => $num($e['pulso_prom']),
    ];
}

json_response(['ok' => true, 'dias' => $filas, 'entrenos' => $entrenos]);

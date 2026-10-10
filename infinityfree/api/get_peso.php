<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/peso_tabla.php';
require_token();

// Pesajes de los ultimos N dias (por defecto 60, tope 3650), del mas viejo al
// mas nuevo. Lo leen la app (tendencia) y el motor (exportar_local.py).
$dias = max(1, min(3650, (int) ($_GET['dias'] ?? 60)));

$pdo = db();
asegurar_tabla_peso($pdo);

$stmt = $pdo->prepare(
    'SELECT fecha, peso, cintura FROM peso_corporal
     WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
     ORDER BY fecha ASC'
);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();
$filas = [];
foreach ($stmt->fetchAll() as $f) {
    $filas[] = [
        'fecha' => $f['fecha'],
        'peso' => (float) $f['peso'],
        'cintura' => $f['cintura'] === null ? null : (float) $f['cintura'],
    ];
}

json_response(['ok' => true, 'pesos' => $filas]);

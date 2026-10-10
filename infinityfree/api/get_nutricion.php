<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/nutricion_tabla.php';
require_token();

// Meta de nutricion (la sube el motor) + proteina registrada de los ultimos N
// dias (por defecto 14, tope 180). Lo leen la app y el motor/dashboard.
$dias = max(1, min(180, (int) ($_GET['dias'] ?? 14)));

$pdo = db();
asegurar_tablas_nutricion($pdo);

$meta = $pdo->query(
    'SELECT proteina_min, proteina_max, kcal, peso, enfoque, actualizado_en FROM nutricion_meta WHERE id = 1'
)->fetch();

$stmt = $pdo->prepare(
    'SELECT fecha, proteina_g, porciones FROM nutricion_dia
     WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
     ORDER BY fecha ASC'
);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();
$filas = [];
foreach ($stmt->fetchAll() as $f) {
    $p = json_decode((string) $f['porciones'], true);
    $filas[] = [
        'fecha' => $f['fecha'],
        'proteina_g' => (float) $f['proteina_g'],
        'porciones' => is_array($p) ? (object) $p : new stdClass(),
    ];
}

json_response(['ok' => true, 'meta' => $meta ?: null, 'dias' => $filas]);

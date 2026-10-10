<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/menu_tabla.php';
require_token();

// El menu de la semana de `fecha` (por defecto hoy): el mas reciente que haya
// empezado en las ultimas 2 semanas. Sin menu: {menu: null}.
$fecha = (string) ($_GET['fecha'] ?? date('Y-m-d'));
$dt = DateTimeImmutable::createFromFormat('Y-m-d', $fecha);
if (!$dt || $dt->format('Y-m-d') !== $fecha) {
    json_response(['ok' => false, 'error' => 'Fecha invalida'], 400);
}

$pdo = db();
asegurar_tabla_menu($pdo);
$stmt = $pdo->prepare(
    'SELECT semana_inicio, datos FROM menu_semana
     WHERE semana_inicio <= :f AND semana_inicio > DATE_SUB(:f2, INTERVAL 14 DAY)
     ORDER BY semana_inicio DESC LIMIT 1'
);
$stmt->execute([':f' => $fecha, ':f2' => $fecha]);
$fila = $stmt->fetch();
$menu = $fila ? json_decode((string) $fila['datos'], true) : null;

json_response(['ok' => true, 'menu' => is_array($menu) ? $menu : null]);

<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/checkin_tabla.php';
require_token();

// La evaluacion de la semana que subio el motor y el ajuste pedido desde la app
// (si aun no lo aplica). Lo leen la app (pestana Check-in) y el motor.
$pdo = db();
asegurar_tabla_checkin($pdo);
$fila = $pdo->query(
    'SELECT evaluacion, aplicar_delta, aplicar_pedido, actualizado_en FROM nutricion_checkin WHERE id = 1'
)->fetch();

$evaluacion = null;
if ($fila && $fila['evaluacion'] !== null) {
    $e = json_decode((string) $fila['evaluacion'], true);
    $evaluacion = is_array($e) ? $e : null;
}
$pendiente = ($fila && $fila['aplicar_delta'] !== null)
    ? ['delta' => (int) $fila['aplicar_delta'], 'pedido' => $fila['aplicar_pedido']]
    : null;

json_response(['ok' => true, 'evaluacion' => $evaluacion, 'pendiente' => $pendiente,
               'actualizado_en' => $fila ? $fila['actualizado_en'] : null]);

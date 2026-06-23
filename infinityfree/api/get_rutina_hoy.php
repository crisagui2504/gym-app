<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

$fecha = $_GET['fecha'] ?? date('Y-m-d');
$diaSemana = (int) (new DateTimeImmutable($fecha))->format('N');
$semanaInicio = monday_for_date($fecha);

$sql = <<<SQL
SELECT id, semana_inicio, dia_semana, nombre_dia, bloque, orden, ejercicio, tecnica,
       series_objetivo, reps_min, reps_max, descanso_seg, peso_sugerido, notas
FROM plan_rutina
WHERE activo = 1
  AND dia_semana = :dia_semana
  AND semana_inicio = (
    SELECT MAX(semana_inicio)
    FROM plan_rutina
    WHERE activo = 1 AND semana_inicio <= :semana_inicio
  )
ORDER BY orden ASC, id ASC
SQL;

$stmt = db()->prepare($sql);
$stmt->execute([
    ':dia_semana' => $diaSemana,
    ':semana_inicio' => $semanaInicio,
]);

json_response([
    'ok' => true,
    'fecha' => $fecha,
    'semana_inicio' => $semanaInicio,
    'dia_semana' => $diaSemana,
    'rutina' => $stmt->fetchAll(),
]);

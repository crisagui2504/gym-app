<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

$data = json_input();
$semanaInicio = $data['semana_inicio'] ?? monday_for_date(date('Y-m-d'));
$rutina = $data['rutina'] ?? $data;

if (!is_array($rutina) || count($rutina) === 0) {
    json_response(['ok' => false, 'error' => 'Payload sin rutina'], 400);
}

$pdo = db();
$pdo->beginTransaction();

try {
    // Reemplazo total por semana: borrar el plan anterior e insertar el nuevo.
    // Asi se eliminan duplicados y ejercicios huerfanos de una sola vez, sin
    // depender de rowCount() (que en MySQL cuenta filas CAMBIADAS y generaba
    // inserts duplicados al re-empujar un plan identico).
    // El historial (registro_series) no se pierde: el FK es ON DELETE SET NULL.
    $semanas = [];
    foreach ($rutina as $item) {
        $semanas[$item['semana_inicio'] ?? $semanaInicio] = true;
    }
    $del = $pdo->prepare('DELETE FROM plan_rutina WHERE semana_inicio = :s');
    foreach (array_keys($semanas) as $s) {
        $del->execute([':s' => $s]);
    }

    $insert = $pdo->prepare(
        'INSERT INTO plan_rutina
        (semana_inicio, dia_semana, nombre_dia, bloque, orden, ejercicio, tecnica,
         series_objetivo, reps_min, reps_max, descanso_seg, peso_sugerido, notas, activo)
        VALUES
        (:semana_inicio, :dia_semana, :nombre_dia, :bloque, :orden, :ejercicio, :tecnica,
         :series_objetivo, :reps_min, :reps_max, :descanso_seg, :peso_sugerido, :notas, 1)'
    );

    $procesados = 0;
    foreach ($rutina as $item) {
        $ejercicio = trim((string) ($item['ejercicio'] ?? ''));
        if ($ejercicio === '' || !isset($item['dia_semana'], $item['orden'])) {
            continue;
        }

        $insert->execute([
            ':semana_inicio' => $item['semana_inicio'] ?? $semanaInicio,
            ':dia_semana' => (int) $item['dia_semana'],
            ':orden' => (int) $item['orden'],
            ':nombre_dia' => $item['nombre_dia'] ?? 'Rutina',
            ':bloque' => $item['bloque'] ?? null,
            ':ejercicio' => $ejercicio,
            ':tecnica' => $item['tecnica'] ?? null,
            ':series_objetivo' => (float) ($item['series_objetivo'] ?? 1),
            ':reps_min' => isset($item['reps_min']) ? (int) $item['reps_min'] : null,
            ':reps_max' => isset($item['reps_max']) ? (int) $item['reps_max'] : null,
            ':descanso_seg' => isset($item['descanso_seg']) ? (int) $item['descanso_seg'] : null,
            ':peso_sugerido' => isset($item['peso_sugerido']) && $item['peso_sugerido'] !== null ? (float) $item['peso_sugerido'] : null,
            ':notas' => $item['notas'] ?? null,
        ]);
        $procesados++;
    }

    $log = $pdo->prepare('INSERT INTO sincronizaciones_plan (semana_inicio, payload_json) VALUES (:semana_inicio, :payload_json)');
    $log->execute([
        ':semana_inicio' => $semanaInicio,
        ':payload_json' => json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
    ]);

    $pdo->commit();
    json_response(['ok' => true, 'procesados' => $procesados, 'semana_inicio' => $semanaInicio]);
} catch (Throwable $e) {
    $pdo->rollBack();
    json_response(['ok' => false, 'error' => $e->getMessage()], 400);
}

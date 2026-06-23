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
    // Upsert por casilla unica: (semana_inicio, dia_semana, orden).
    $update = $pdo->prepare(
        'UPDATE plan_rutina SET
            nombre_dia = :nombre_dia,
            bloque = :bloque,
            ejercicio = :ejercicio,
            tecnica = :tecnica,
            series_objetivo = :series_objetivo,
            reps_min = :reps_min,
            reps_max = :reps_max,
            descanso_seg = :descanso_seg,
            peso_sugerido = :peso_sugerido,
            notas = :notas,
            activo = 1
         WHERE semana_inicio = :semana_inicio
           AND dia_semana = :dia_semana
           AND orden = :orden'
    );

    $insert = $pdo->prepare(
        'INSERT INTO plan_rutina
        (semana_inicio, dia_semana, nombre_dia, bloque, orden, ejercicio, tecnica,
         series_objetivo, reps_min, reps_max, descanso_seg, peso_sugerido, notas)
        VALUES
        (:semana_inicio, :dia_semana, :nombre_dia, :bloque, :orden, :ejercicio, :tecnica,
         :series_objetivo, :reps_min, :reps_max, :descanso_seg, :peso_sugerido, :notas)'
    );

    $procesados = 0;
    foreach ($rutina as $item) {
        $ejercicio = trim((string) ($item['ejercicio'] ?? ''));
        if ($ejercicio === '' || !isset($item['dia_semana'], $item['orden'])) {
            continue;
        }

        $params = [
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
        ];

        $update->execute($params);
        if ($update->rowCount() === 0) {
            $insert->execute($params);
        }
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

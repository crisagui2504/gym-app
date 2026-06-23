<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_token();

$stmt = db()->query(
    'SELECT r.id, r.fecha_entreno, r.ejercicio, r.tecnica, r.numero_serie,
            r.peso_kg, r.repeticiones AS reps_hechas, r.rpe, r.tonelaje_serie,
            p.semana_inicio, p.dia_semana, p.nombre_dia, p.bloque,
            p.series_objetivo, p.reps_min, p.reps_max, p.peso_sugerido
     FROM registro_series r
     LEFT JOIN plan_rutina p ON p.id = r.plan_id
     ORDER BY r.fecha_entreno ASC, r.ejercicio ASC, r.numero_serie ASC'
);

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="base_gimnasio.csv"');

$out = fopen('php://output', 'w');
$first = true;
while ($row = $stmt->fetch()) {
    if ($first) {
        fputcsv($out, array_keys($row));
        $first = false;
    }
    fputcsv($out, $row);
}
fclose($out);

<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/nutricion_tabla.php';
require_token();

// POST {proteina_min, proteina_max, kcal?, peso?, enfoque?}
// La sube el motor (python-engine/nutricion.py) al generar la semana y cuando
// cambias tu peso o tu enfoque en el dashboard. La app la lee para la meta del dia.
$data = json_input();

function entero($v, int $min, int $max, bool $opcional = false): ?int
{
    if ($opcional && ($v === null || $v === '')) {
        return null;
    }
    $n = filter_var($v, FILTER_VALIDATE_INT);
    if ($n === false || $n < $min || $n > $max) {
        json_response(['ok' => false, 'error' => 'Valor fuera de rango'], 400);
    }
    return $n;
}

$pmin = entero($data['proteina_min'] ?? null, 20, 500);
$pmax = entero($data['proteina_max'] ?? null, 20, 500);
if ($pmax < $pmin) {
    json_response(['ok' => false, 'error' => 'Rango invalido'], 400);
}
$kcal = entero($data['kcal'] ?? null, 800, 6000, true);
$peso = filter_var($data['peso'] ?? null, FILTER_VALIDATE_FLOAT);
$peso = ($peso !== false && $peso >= 30 && $peso <= 250) ? round((float) $peso, 1) : null;
$enfoque = preg_replace('/[^a-z_]/', '', (string) ($data['enfoque'] ?? ''));

try {
    $pdo = db();
    asegurar_tablas_nutricion($pdo);
    $stmt = $pdo->prepare(
        'INSERT INTO nutricion_meta (id, proteina_min, proteina_max, kcal, peso, enfoque)
         VALUES (1, :pmin, :pmax, :kcal, :peso, :enf)
         ON DUPLICATE KEY UPDATE proteina_min = VALUES(proteina_min), proteina_max = VALUES(proteina_max),
            kcal = VALUES(kcal), peso = VALUES(peso), enfoque = VALUES(enfoque)'
    );
    $stmt->execute([':pmin' => $pmin, ':pmax' => $pmax, ':kcal' => $kcal, ':peso' => $peso,
                    ':enf' => substr($enfoque, 0, 40) ?: null]);
    json_response(['ok' => true]);
} catch (Throwable $e) {
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

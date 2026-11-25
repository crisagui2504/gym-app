<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/reloj_tabla.php';
require_token();

// POST {dias: [{fecha, sueno_min, pulso_noche, pulso_reposo, hrv, pasos, peso}],
//       entrenos: [{inicio, fin, tipo, minutos, pulso_prom}]}
// Lo manda la app al importar la exportacion de Salud. Reimportar es seguro:
// cada dia y cada entreno se sobrescriben, y un dato que falte en el envio nuevo
// conserva el que ya habia (COALESCE).
$data = json_input();
$dias = is_array($data['dias'] ?? null) ? $data['dias'] : [];
$entrenos = is_array($data['entrenos'] ?? null) ? $data['entrenos'] : [];
if (count($dias) > 400 || count($entrenos) > 400) {
    json_response(['ok' => false, 'error' => 'Demasiados datos (maximo 400 dias y 400 entrenos)'], 400);
}

function fecha_valida(string $f, string $formato): bool
{
    $dt = DateTimeImmutable::createFromFormat($formato, $f);
    return $dt !== false && $dt->format($formato) === $f;
}

/** Numero dentro de [min, max] o null (fuera de rango = dato malo del sensor). */
function numero($v, float $min, float $max): ?float
{
    if ($v === null || $v === '') {
        return null;
    }
    $n = filter_var($v, FILTER_VALIDATE_FLOAT);
    return ($n === false || $n < $min || $n > $max) ? null : (float) $n;
}

try {
    $pdo = db();
    asegurar_tablas_reloj($pdo);
    $pdo->beginTransaction();
    $sd = $pdo->prepare(
        'INSERT INTO reloj_dias (fecha, sueno_min, pulso_noche, pulso_reposo, hrv, pasos, peso)
         VALUES (:fecha, :sueno, :pnoche, :preposo, :hrv, :pasos, :peso)
         ON DUPLICATE KEY UPDATE
            sueno_min = COALESCE(VALUES(sueno_min), sueno_min),
            pulso_noche = COALESCE(VALUES(pulso_noche), pulso_noche),
            pulso_reposo = COALESCE(VALUES(pulso_reposo), pulso_reposo),
            hrv = COALESCE(VALUES(hrv), hrv),
            pasos = COALESCE(VALUES(pasos), pasos),
            peso = COALESCE(VALUES(peso), peso)'
    );
    $nd = 0;
    foreach ($dias as $d) {
        $fecha = (string) ($d['fecha'] ?? '');
        if (!fecha_valida($fecha, 'Y-m-d')) {
            continue;
        }
        $sueno = numero($d['sueno_min'] ?? null, 0, 1440);
        $pasos = numero($d['pasos'] ?? null, 0, 150000);
        $pn = numero($d['pulso_noche'] ?? null, 25, 200);
        $pr = numero($d['pulso_reposo'] ?? null, 25, 200);
        $hrv = numero($d['hrv'] ?? null, 0, 999);
        $peso = numero($d['peso'] ?? null, 30, 250);
        $sd->execute([
            ':fecha' => $fecha,
            ':sueno' => $sueno === null ? null : (int) round($sueno),
            ':pnoche' => $pn === null ? null : (int) round($pn),
            ':preposo' => $pr === null ? null : (int) round($pr),
            ':hrv' => $hrv === null ? null : round($hrv, 1),
            ':pasos' => $pasos === null ? null : (int) round($pasos),
            ':peso' => $peso === null ? null : round($peso, 1),
        ]);
        $nd++;
    }
    $se = $pdo->prepare(
        'INSERT INTO reloj_entrenos (inicio, tipo, fin, minutos, pulso_prom)
         VALUES (:inicio, :tipo, :fin, :minutos, :pulso)
         ON DUPLICATE KEY UPDATE fin = VALUES(fin), minutos = VALUES(minutos),
            pulso_prom = COALESCE(VALUES(pulso_prom), pulso_prom)'
    );
    $ne = 0;
    foreach ($entrenos as $e) {
        $inicio = (string) ($e['inicio'] ?? '');
        $fin = (string) ($e['fin'] ?? '');
        $tipo = preg_replace('/[^A-Za-z0-9]/', '', (string) ($e['tipo'] ?? ''));
        $min = numero($e['minutos'] ?? null, 1, 720);
        if (!fecha_valida($inicio, 'Y-m-d H:i:s') || !fecha_valida($fin, 'Y-m-d H:i:s') || $tipo === '' || $min === null) {
            continue;
        }
        $pulso = numero($e['pulso_prom'] ?? null, 30, 230);
        $se->execute([
            ':inicio' => $inicio,
            ':tipo' => substr($tipo, 0, 60),
            ':fin' => $fin,
            ':minutos' => round($min, 1),
            ':pulso' => $pulso === null ? null : (int) round($pulso),
        ]);
        $ne++;
    }
    $pdo->commit();
    json_response(['ok' => true, 'dias' => $nd, 'entrenos' => $ne]);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

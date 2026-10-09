<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/feedback_tabla.php';
require_token();

// POST {fecha: 'YYYY-MM-DD', items: [{tipo, clave, bombeo?, carga?, agujetas?, dolor?}]}
// Upsert por (fecha, tipo, clave): responder en dos momentos (agujetas al
// empezar, bombeo/carga al terminar) completa la misma fila sin pisar lo previo.
$data = json_input();
$fecha = (string) ($data['fecha'] ?? '');
$items = $data['items'] ?? [];

$dt = DateTimeImmutable::createFromFormat('Y-m-d', $fecha);
if (!$dt || $dt->format('Y-m-d') !== $fecha) {
    json_response(['ok' => false, 'error' => 'Fecha invalida'], 400);
}
if (!is_array($items) || count($items) === 0 || count($items) > 60) {
    json_response(['ok' => false, 'error' => 'Sin respuestas que guardar'], 400);
}

/** null si no viene; si viene, entero dentro del rango o error. */
function escala($v, int $min, int $max): ?int
{
    if ($v === null || $v === '') {
        return null;
    }
    $n = filter_var($v, FILTER_VALIDATE_INT);
    if ($n === false || $n < $min || $n > $max) {
        throw new InvalidArgumentException('Valor fuera de rango');
    }
    return $n;
}

$pdo = db();
asegurar_tabla_feedback($pdo);
$pdo->beginTransaction();
try {
    $stmt = $pdo->prepare(
        'INSERT INTO feedback_sesion (fecha, tipo, clave, bombeo, carga, agujetas, dolor)
         VALUES (:fecha, :tipo, :clave, :bombeo, :carga, :agujetas, :dolor)
         ON DUPLICATE KEY UPDATE
            bombeo   = COALESCE(VALUES(bombeo), bombeo),
            carga    = COALESCE(VALUES(carga), carga),
            agujetas = COALESCE(VALUES(agujetas), agujetas),
            dolor    = COALESCE(VALUES(dolor), dolor)'
    );
    $n = 0;
    foreach ($items as $it) {
        $tipo = (string) ($it['tipo'] ?? '');
        $clave = trim((string) ($it['clave'] ?? ''));
        if (!in_array($tipo, ['musculo', 'ejercicio'], true) || $clave === '' || strlen($clave) > 480) {  // 160 caracteres utf8mb4 (sin depender de mbstring)
            throw new InvalidArgumentException('Respuesta invalida');
        }
        $stmt->execute([
            ':fecha' => $fecha,
            ':tipo' => $tipo,
            ':clave' => $clave,
            ':bombeo' => escala($it['bombeo'] ?? null, 1, 3),
            ':carga' => escala($it['carga'] ?? null, 1, 3),
            ':agujetas' => escala($it['agujetas'] ?? null, 1, 3),
            ':dolor' => escala($it['dolor'] ?? null, 0, 1),
        ]);
        $n++;
    }
    $pdo->commit();
    json_response(['ok' => true, 'guardadas' => $n]);
} catch (InvalidArgumentException $e) {
    $pdo->rollBack();
    json_response(['ok' => false, 'error' => $e->getMessage()], 400);
} catch (Throwable $e) {
    $pdo->rollBack();
    json_response(['ok' => false, 'error' => 'Error al guardar'], 500);
}

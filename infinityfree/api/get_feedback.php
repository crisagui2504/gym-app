<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/feedback_tabla.php';
require_token();

// Respuestas de la encuesta de los ultimos N dias (por defecto 42, tope 120).
// Lo lee el motor (planificar.py) para ajustar el volumen de la semana siguiente.
$dias = max(1, min(120, (int) ($_GET['dias'] ?? 42)));

$pdo = db();
asegurar_tabla_feedback($pdo);
$stmt = $pdo->prepare(
    'SELECT fecha, tipo, clave, bombeo, carga, agujetas, dolor
     FROM feedback_sesion
     WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
     ORDER BY fecha ASC, id ASC'
);
$stmt->bindValue(':dias', $dias, PDO::PARAM_INT);
$stmt->execute();

json_response(['ok' => true, 'dias' => $dias, 'feedback' => $stmt->fetchAll()]);

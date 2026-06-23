<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require 'conexion.php';

$input = json_decode(file_get_contents('php://input'), true);

if (!$input || !isset($input['series']) || !is_array($input['series'])) {
    echo json_encode(['status' => 'error', 'message' => 'JSON inválido o sin series']);
    exit;
}

try {
    $pdo->beginTransaction();

    $fecha = date('Y-m-d');
    
    // 1. Obtener o crear el registro de día
    $stmt = $pdo->prepare('SELECT id FROM registro_dias WHERE fecha = ?');
    $stmt->execute([$fecha]);
    $dia = $stmt->fetch();

    if (!$dia) {
        $stmt = $pdo->prepare('INSERT INTO registro_dias (fecha) VALUES (?)');
        $stmt->execute([$fecha]);
        $dia_id = $pdo->lastInsertId();
    } else {
        $dia_id = $dia['id'];
    }

    // 2. Insertar las series del entrenamiento
    $stmt = $pdo->prepare('INSERT INTO registro_series (registro_dia_id, ejercicio, serie_num, repeticiones, rpe, peso) VALUES (?, ?, ?, ?, ?, ?)');
    
    foreach ($input['series'] as $serie) {
        // Validación básica
        if (!isset($serie['ejercicio'], $serie['serie_num'], $serie['repeticiones'], $serie['rpe'], $serie['peso'])) {
            throw new Exception("Faltan datos en una de las series");
        }

        $stmt->execute([
            $dia_id,
            $serie['ejercicio'],
            $serie['serie_num'],
            $serie['repeticiones'],
            $serie['rpe'],
            $serie['peso']
        ]);
    }

    $pdo->commit();
    echo json_encode(['status' => 'success', 'message' => 'Entrenamiento guardado correctamente']);

} catch (Exception $e) {
    $pdo->rollBack();
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}
?>

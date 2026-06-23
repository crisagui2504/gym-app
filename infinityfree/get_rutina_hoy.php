<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *'); // Si hay problemas de CORS con Angular, cambiar a dominio específico
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require 'conexion.php';

try {
    $dia_semana = date('N'); // 1 (Lunes) a 7 (Domingo)

    $stmt = $pdo->prepare('SELECT * FROM plan_rutina WHERE dia_semana = ? ORDER BY id ASC');
    $stmt->execute([$dia_semana]);
    $rutina = $stmt->fetchAll();

    echo json_encode(['status' => 'success', 'data' => $rutina]);

} catch (Exception $e) {
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
}
?>

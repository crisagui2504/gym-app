<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require 'conexion.php';

// Este script espera recibir un archivo en un FormData llamado 'json_file'
if (isset($_FILES['json_file']) && $_FILES['json_file']['error'] === UPLOAD_ERR_OK) {
    
    $jsonContent = file_get_contents($_FILES['json_file']['tmp_name']);
    $plan = json_decode($jsonContent, true);

    if (!$plan) {
        echo json_encode(['status' => 'error', 'message' => 'El archivo no contiene un JSON válido']);
        exit;
    }

    try {
        $pdo->beginTransaction();

        // Limpiar la rutina anterior
        $pdo->exec('TRUNCATE TABLE plan_rutina');

        // Insertar la nueva rutina optimizada
        $stmt = $pdo->prepare('INSERT INTO plan_rutina (ejercicio, dia_semana, series_objetivo, reps_objetivo, rpe_objetivo, peso_objetivo) VALUES (?, ?, ?, ?, ?, ?)');
        
        foreach ($plan as $item) {
            // Validar que vengan todos los campos necesarios
            if (!isset($item['ejercicio'], $item['dia_semana'], $item['series_objetivo'], $item['reps_objetivo'], $item['rpe_objetivo'], $item['peso_objetivo'])) {
                throw new Exception("Formato JSON incorrecto. Faltan propiedades en algún ejercicio.");
            }

            $stmt->execute([
                $item['ejercicio'],
                $item['dia_semana'],
                $item['series_objetivo'],
                $item['reps_objetivo'],
                $item['rpe_objetivo'],
                $item['peso_objetivo']
            ]);
        }

        $pdo->commit();
        echo json_encode(['status' => 'success', 'message' => 'Plan de rutina actualizado con éxito en InfinityFree']);

    } catch (Exception $e) {
        $pdo->rollBack();
        echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
    }

} else {
    echo json_encode(['status' => 'error', 'message' => 'No se recibió ningún archivo o hubo un error al subirlo']);
}
?>

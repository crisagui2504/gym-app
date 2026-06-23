<?php
header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="historial_entrenamiento.csv"');

require 'conexion.php';

// Abrir la salida estándar como un archivo para escribir el CSV directamente
$output = fopen('php://output', 'w');

// Añadir BOM para que Excel detecte UTF-8 correctamente
fputs($output, $bom = (chr(0xEF) . chr(0xBB) . chr(0xBF)));

// Escribir las cabeceras del CSV
fputcsv($output, ['fecha', 'ejercicio', 'serie_num', 'repeticiones', 'rpe', 'peso']);

try {
    // Consulta para extraer todo el historial ordenado cronológicamente
    $query = "
        SELECT d.fecha, s.ejercicio, s.serie_num, s.repeticiones, s.rpe, s.peso 
        FROM registro_series s
        JOIN registro_dias d ON s.registro_dia_id = d.id
        ORDER BY d.fecha ASC, s.ejercicio ASC, s.serie_num ASC
    ";

    $stmt = $pdo->query($query);

    // Escribir fila por fila para no saturar memoria
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        fputcsv($output, $row);
    }

} catch (Exception $e) {
    // Si hay error, lo inyectamos como texto plano en vez de romper el CSV con HTML
    fputcsv($output, ['ERROR', $e->getMessage()]);
}

fclose($output);
?>

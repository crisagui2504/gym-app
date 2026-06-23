<?php
// conexion.php - Configuración de conexión optimizada para InfinityFree
// REEMPLAZA LOS SIGUIENTES VALORES EN EL PANEL DE INFINITYFREE
$host = 'sql308.infinityfree.com';
$db   = 'if0_41476828_gym_app'; 
$user = 'if0_41476828';
$pass = '2002Rodrigo';
$charset = 'utf8mb4';

$dsn = "mysql:host=$host;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
    PDO::ATTR_PERSISTENT         => false // Vital para cerrar la conexión rápidamente y no consumir límite de 20s
];

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
} catch (\PDOException $e) {
    // Si falla, se envía un status de error JSON para que Angular no se cuelgue
    header('Content-Type: application/json');
    echo json_encode(['status' => 'error', 'message' => 'Error de conexion a DB']);
    exit;
}
?>

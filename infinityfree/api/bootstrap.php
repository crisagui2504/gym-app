<?php
declare(strict_types=1);

require_once __DIR__ . '/config.php';

header('Access-Control-Allow-Origin: ' . ALLOWED_ORIGIN);
header('Access-Control-Allow-Headers: Content-Type, X-API-Token');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    return $pdo;
}

function require_token(): void
{
    $headerToken = $_SERVER['HTTP_X_API_TOKEN'] ?? '';
    $queryToken = $_GET['token'] ?? '';
    $token = $headerToken !== '' ? $headerToken : $queryToken;

    if (!hash_equals(API_TOKEN, (string) $token)) {
        json_response(['ok' => false, 'error' => 'Token invalido'], 401);
    }
}

function json_input(): array
{
    $raw = file_get_contents('php://input');
    $data = json_decode($raw ?: '[]', true);

    if (!is_array($data)) {
        json_response(['ok' => false, 'error' => 'JSON invalido'], 400);
    }

    return $data;
}

function json_response(array $payload, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function monday_for_date(string $date): string
{
    $dt = new DateTimeImmutable($date);
    return $dt->modify('monday this week')->format('Y-m-d');
}

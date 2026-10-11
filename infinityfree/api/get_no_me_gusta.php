<?php
declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/no_me_gusta_tabla.php';
require_token();

// Lo que no quieres en el menu: {ok, recetas: [...], alimentos: [...]}.
// Lo leen la app (para no ofrecerlo en "Cambiar") y el motor (menu.py).
$pdo = db();
asegurar_tabla_no_me_gusta($pdo);
$recetas = [];
$alimentos = [];
foreach ($pdo->query('SELECT tipo, id FROM menu_no_me_gusta ORDER BY creado_en ASC')->fetchAll() as $f) {
    if ($f['tipo'] === 'receta') {
        $recetas[] = $f['id'];
    } else {
        $alimentos[] = $f['id'];
    }
}

json_response(['ok' => true, 'recetas' => $recetas, 'alimentos' => $alimentos]);

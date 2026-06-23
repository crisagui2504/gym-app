-- Base de datos para Rutinas Inteligentes en InfinityFree/MySQL.
-- Ejecuta este archivo en phpMyAdmin antes de subir los endpoints PHP.

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS plan_rutina (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  semana_inicio DATE NOT NULL,
  dia_semana TINYINT UNSIGNED NOT NULL COMMENT '1=Lunes, 7=Domingo',
  nombre_dia VARCHAR(80) NOT NULL,
  bloque VARCHAR(80) NULL,
  orden INT UNSIGNED NOT NULL DEFAULT 1,
  ejercicio VARCHAR(160) NOT NULL,
  tecnica VARCHAR(120) NULL,
  series_objetivo DECIMAL(4,1) NOT NULL DEFAULT 1,
  reps_min INT UNSIGNED NULL,
  reps_max INT UNSIGNED NULL,
  descanso_seg INT UNSIGNED NULL,
  peso_sugerido DECIMAL(6,2) NULL,
  notas VARCHAR(255) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_plan_fecha_dia (semana_inicio, dia_semana, activo),
  INDEX idx_plan_ejercicio (ejercicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS registro_series (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  plan_id INT UNSIGNED NULL,
  fecha_entreno DATE NOT NULL,
  ejercicio VARCHAR(160) NOT NULL,
  tecnica VARCHAR(120) NULL,
  numero_serie INT UNSIGNED NOT NULL DEFAULT 1,
  peso_kg DECIMAL(6,2) NOT NULL DEFAULT 0,
  repeticiones INT UNSIGNED NOT NULL DEFAULT 0,
  rpe TINYINT UNSIGNED NOT NULL,
  tonelaje_serie DECIMAL(9,2) GENERATED ALWAYS AS (peso_kg * repeticiones) STORED,
  notas VARCHAR(255) NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_rpe CHECK (rpe BETWEEN 1 AND 10),
  CONSTRAINT fk_registro_plan FOREIGN KEY (plan_id) REFERENCES plan_rutina(id) ON DELETE SET NULL,
  INDEX idx_registro_fecha (fecha_entreno),
  INDEX idx_registro_ejercicio_fecha (ejercicio, fecha_entreno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sincronizaciones_plan (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  semana_inicio DATE NOT NULL,
  origen VARCHAR(40) NOT NULL DEFAULT 'python',
  payload_json JSON NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Semana semilla. Cambia semana_inicio si quieres arrancar otra semana.
INSERT INTO plan_rutina
(semana_inicio, dia_semana, nombre_dia, bloque, orden, ejercicio, tecnica, series_objetivo, reps_min, reps_max, descanso_seg, peso_sugerido, notas)
VALUES
('2026-06-22', 1, 'Torso A - Fuerza', 'Fuerza maxima', 1, 'Press Militar Mancuernas (Sentado)', 'TOP SET', 1, 6, 8, 180, 25.00, 'Hombro prioritario'),
('2026-06-22', 1, 'Torso A - Fuerza', 'Fuerza maxima', 2, 'Press Militar Mancuernas (Sentado)', 'Back-off', 2, 8, 12, 180, 20.00, '-20% del top set'),
('2026-06-22', 1, 'Torso A - Fuerza', 'Fuerza maxima', 3, 'Remo con Mancuerna a 1 Mano', 'TOP SET', 1, 6, 8, 180, 15.00, 'Por brazo'),
('2026-06-22', 1, 'Torso A - Fuerza', 'Volumen', 4, 'Press de Banca con Barra', 'Tradicional', 2, 8, 12, 90, 36.00, NULL),
('2026-06-22', 1, 'Torso A - Fuerza', 'Volumen', 5, 'Jalon al Pecho Agarre Amplio', 'AMRAP', 1, NULL, NULL, 90, NULL, 'Ultima serie al fallo'),
('2026-06-22', 2, 'Pierna A - Fuerza', 'Fuerza maxima', 1, 'Sentadilla Libre con Barra', 'Top Set', 1, 5, 8, 180, NULL, NULL),
('2026-06-22', 2, 'Pierna A - Fuerza', 'Fuerza maxima', 2, 'Peso Muerto Rumano con Mancuernas', 'Tradicional', 3, 10, 12, 90, NULL, NULL),
('2026-06-22', 2, 'Pierna A - Fuerza', 'Volumen', 3, 'Prensa de Piernas 45 grados', 'Tradicional + AMRAP', 3, 10, 15, 90, NULL, NULL),
('2026-06-22', 2, 'Pierna A - Fuerza', 'Aislamiento', 4, 'Extensiones de Cuadriceps (Maquina)', 'Rest-Pause', 2, 12, 15, 60, NULL, NULL),
('2026-06-22', 5, 'Torso Bombeo', 'Fuerza maxima', 1, 'Press Arnold con Mancuernas', 'TOP SET', 1, 6, 8, 180, NULL, 'Registrar top set'),
('2026-06-22', 5, 'Torso Bombeo', 'Fuerza maxima', 2, 'Press Arnold con Mancuernas', 'Back-off', 2, 10, 12, 180, NULL, '-20%'),
('2026-06-22', 5, 'Torso Bombeo', 'Volumen', 3, 'Remo en Polea Baja Agarre Neutro', 'AMRAP', 3, 10, 12, 90, NULL, NULL),
('2026-06-22', 5, 'Torso Bombeo', 'Bombeo', 4, 'Face Pull Polea Alta', 'Tradicional', 3, 15, 15, 60, NULL, NULL),
('2026-06-22', 6, 'Pierna Bombeo', 'Fuerza maxima', 1, 'Hip Thrust con Barra', 'TOP SET', 1, 6, 8, 180, NULL, NULL),
('2026-06-22', 6, 'Pierna Bombeo', 'Fuerza maxima', 2, 'Peso Muerto Rumano con Barra', 'TOP SET', 1, 5, 8, 180, NULL, NULL),
('2026-06-22', 6, 'Pierna Bombeo', 'Volumen', 3, 'Prensa de Piernas 45 grados', 'Drop Set', 3, 10, 15, 90, NULL, NULL),
('2026-06-22', 6, 'Pierna Bombeo', 'Bombeo', 4, 'Curl de Isquios Tumbado (Maquina)', 'Drop Set', 2, 12, 15, 60, NULL, NULL),
('2026-06-22', 7, 'Cardio LISS + Core', 'Cardio', 1, 'Eliptica', 'Zona 2', 1, 35, 45, NULL, NULL, 'Minutos en lugar de repeticiones'),
('2026-06-22', 7, 'Cardio LISS + Core', 'Core', 2, 'Plancha Frontal', 'Tradicional', 3, NULL, NULL, 60, NULL, 'Al fallo');

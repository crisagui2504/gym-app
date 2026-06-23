-- --------------------------------------------------------
-- Tracker de Gimnasio: Esquema de Base de Datos
-- Optimizado para no exceder los límites de InfinityFree
-- --------------------------------------------------------

-- Tabla para el plan de rutinas
CREATE TABLE IF NOT EXISTS plan_rutina (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ejercicio VARCHAR(50) NOT NULL,
    dia_semana TINYINT NOT NULL COMMENT '1=Lunes, 7=Domingo',
    series_objetivo TINYINT NOT NULL,
    reps_objetivo TINYINT NOT NULL,
    rpe_objetivo DECIMAL(3,1) NOT NULL,
    peso_objetivo DECIMAL(5,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla para registrar los días en que hubo entrenamiento
CREATE TABLE IF NOT EXISTS registro_dias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    notas VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla para el registro granular de cada serie (ahorra inodos y datos)
CREATE TABLE IF NOT EXISTS registro_series (
    id INT AUTO_INCREMENT PRIMARY KEY,
    registro_dia_id INT NOT NULL,
    ejercicio VARCHAR(50) NOT NULL,
    serie_num TINYINT NOT NULL,
    repeticiones TINYINT NOT NULL,
    rpe DECIMAL(3,1) NOT NULL,
    peso DECIMAL(5,2) NOT NULL,
    FOREIGN KEY (registro_dia_id) REFERENCES registro_dias(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

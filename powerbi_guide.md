# Guía de Power BI para Gym Tracker

Esta guía te ayudará a conectar los datos generados por tu aplicación de Angular e InfinityFree directamente en Power BI para obtener dashboards interactivos y profesionales sobre tu progreso de hipertrofia.

## 1. Importar los Datos

1. Abre **Power BI Desktop**.
2. En la cinta de opciones superior, haz clic en **Obtener datos** > **Texto/CSV**.
3. Selecciona el archivo `historial_entrenamiento.csv` que descargaste previamente desde tu Panel de Administrador en la App Web.
4. Haz clic en **Cargar**.

## 2. Fórmulas DAX Esenciales (El Motor de Análisis)

Para sacarle el máximo provecho a tu historial y poder medir tu sobrecarga progresiva real, crea las siguientes **Medidas**. (En el panel de la derecha, haz clic derecho sobre el nombre de tu tabla de datos y selecciona **"Nueva medida"**).

### A. Tonelaje Total
El tonelaje es la métrica reina de la hipertrofia. Te indica la cantidad exacta de kilogramos totales movidos (Series × Reps × Peso).

```dax
Tonelaje Total = 
SUMX(
    'historial_entrenamiento', 
    'historial_entrenamiento'[repeticiones] * 'historial_entrenamiento'[peso]
)
```

### B. Esfuerzo Percibido (RPE Promedio)
Crucial para saber si te estás sobreentrenando o si estás dejando demasiadas repeticiones en reserva (RIR).

```dax
RPE Promedio = 
AVERAGE('historial_entrenamiento'[rpe])
```

### C. Progresión de Fuerza (Peso Máximo Movido)
Para hacer un seguimiento a tus "Top Sets" o PRs (Personal Records) en ejercicios compuestos.

```dax
Peso Máximo (PR) = 
MAX('historial_entrenamiento'[peso])
```

## 3. Visualizaciones Recomendadas para el Dashboard

Una vez tengas las medidas listas, arrastra estos elementos al lienzo:

1. **Curva de Sobrecarga Progresiva (Gráfico de Líneas):**
   * **Eje X:** `fecha`
   * **Eje Y:** Medida `Tonelaje Total`
   * **Leyenda / Filtro:** `ejercicio` (Ej. Selecciona solo "Press Militar Manc. (Top Set)" para ver cómo sube la línea a lo largo de las semanas).

2. **Termómetro del SNC (Gráfico de Barras o Medidor):**
   * **Valor:** Medida `RPE Promedio`
   * Si el promedio semanal supera 9.5 constantemente, Power BI te avisará visualmente que necesitas una semana de descarga (Deload).

3. **Tabla de Matriz de Entrenamientos:**
   * **Filas:** `fecha` y `ejercicio`
   * **Valores:** `repeticiones`, `peso`, y `RPE Promedio`
   * Esto funciona como un log book digital idéntico al que llevarías en un cuaderno, pero filtrable por mes.

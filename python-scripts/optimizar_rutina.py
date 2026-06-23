import os
import pandas as pd
import json
from datetime import datetime

# Rutas de archivos (usamos el directorio local suponiendo que el CSV se descargó aquí)
CSV_FILE = "historial_entrenamiento.csv"
OUTPUT_JSON = "rutina_optimizada.json"

def calcular_tonelaje(df):
    """Calcula el tonelaje total (series * reps * peso) por ejercicio."""
    df['tonelaje'] = df['repeticiones'] * df['peso']
    return df.groupby('ejercicio')['tonelaje'].sum().reset_index()

def auditar_progreso(df):
    """
    Evalúa si hubo estancamiento basándose en RPE.
    Si el RPE promedio en la última sesión para un ejercicio fue menor a 8,
    se permite aplicar sobrecarga progresiva.
    """
    # Obtener el día más reciente para cada ejercicio
    idx_max_fecha = df.groupby('ejercicio')['fecha'].transform(max) == df['fecha']
    ultimo_entrenamiento = df[idx_max_fecha]
    
    promedio_rpe = ultimo_entrenamiento.groupby('ejercicio')['rpe'].mean().reset_index()
    promedio_peso = ultimo_entrenamiento.groupby('ejercicio')['peso'].max().reset_index()
    
    progreso = pd.merge(promedio_rpe, promedio_peso, on='ejercicio')
    
    # Motor de reglas de hipertrofia
    # Si RPE < 8, aumentamos 2.5kg. Si RPE >= 9, mantenemos.
    def calcular_nuevo_peso(row):
        peso_actual = row['peso']
        if pd.isna(peso_actual) or peso_actual == 0:
            return 0
            
        if row['rpe'] < 8.0:
            return peso_actual + 2.5 # Microcarga positiva
        elif row['rpe'] >= 9.5:
            return max(peso_actual - 2.5, 0) # Descarga si el RPE es crítico
        return peso_actual # Mantenimiento
        
    progreso['nuevo_peso_objetivo'] = progreso.apply(calcular_nuevo_peso, axis=1)
    return progreso

def generar_rutina_optimizada(progreso_df):
    """Genera la estructura JSON que espera Angular/PHP basándose en rutina_base.json."""
    
    rutina_base_path = "rutina_base.json"
    if not os.path.exists(rutina_base_path):
        print(f"Error: No se encontró la plantilla {rutina_base_path}")
        return []
        
    with open(rutina_base_path, 'r', encoding='utf-8') as f:
        plantilla = json.load(f)
    
    rutina_final = []
    
    for item in plantilla:
        ejercicio = item['ejercicio']
        # Buscar el peso calculado
        match = progreso_df[progreso_df['ejercicio'] == ejercicio]
        if not match.empty:
            peso_calc = float(match.iloc[0]['nuevo_peso_objetivo'])
            item['peso_objetivo'] = peso_calc
        # Si no hay historial, se queda con el peso_objetivo inicial de la plantilla
            
        rutina_final.append(item)
        
    return rutina_final

def main():
    print(f"--- Iniciando Algoritmo de Sobrecarga Progresiva ---")
    if not os.path.exists(CSV_FILE):
        print(f"Error: No se encontró el archivo {CSV_FILE}. Por favor descárgalo desde la app Angular.")
        return
        
    # 1. Adaptación a Datos Locales (Pandas + OS)
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"Historial cargado: {len(df)} registros.")
    except Exception as e:
        print(f"Error al leer el CSV: {e}")
        return

    # 2. Análisis y Reglas
    tonelaje_df = calcular_tonelaje(df)
    progreso_df = auditar_progreso(df)
    
    # 3. Generar JSON
    rutina_json = generar_rutina_optimizada(progreso_df)
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(rutina_json, f, ensure_ascii=False, indent=4)
        
    print(f"Éxito: Archivo '{OUTPUT_JSON}' generado correctamente.")
    print("Siguiente paso: Sube este archivo en la vista de Ajustes de la App Angular.")

if __name__ == "__main__":
    main()

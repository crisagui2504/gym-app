import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';
import { fechaLocal } from './entreno-data';

export interface EjercicioPlan {
  id: number;
  nombre_dia: string;
  bloque: string | null;
  orden: number;
  ejercicio: string;
  tecnica: string | null;
  series_objetivo: string;
  reps_min: number | null;
  reps_max: number | null;
  descanso_seg: number | null;
  peso_sugerido: string | null;
  notas: string | null;
}

export interface RutinaHoyResponse {
  ok: boolean;
  fecha: string;
  semana_inicio: string;
  dia_semana: number;
  rutina: EjercicioPlan[];
}

export interface SeriePayload {
  plan_id: number;
  ejercicio: string;
  tecnica: string | null;
  numero_serie: number;
  peso_kg: number;
  repeticiones: number;
  rpe: number;
  notas?: string | null;
}

@Injectable({ providedIn: 'root' })
export class RutinaApiService {
  private readonly http = inject(HttpClient);
  private readonly headers = new HttpHeaders({ 'X-API-Token': environment.apiToken });

  getRutinaHoy(fecha = new Date()): Observable<RutinaHoyResponse> {
    const iso = fechaLocal(fecha);
    return this.http.get<RutinaHoyResponse>(
      `${environment.apiBaseUrl}/get_rutina_hoy.php?fecha=${iso}`,
      { headers: this.headers }
    );
  }

  guardarEntreno(fecha: string, items: SeriePayload[]): Observable<{ ok: boolean; inserted: number }> {
    return this.http.post<{ ok: boolean; inserted: number }>(
      `${environment.apiBaseUrl}/guardar_entreno.php`,
      { fecha_entreno: fecha, items },
      { headers: this.headers }
    );
  }
}

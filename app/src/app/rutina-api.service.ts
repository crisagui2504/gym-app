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

export interface SerieHistorial {
  fecha_entreno: string;
  ejercicio: string;
  tecnica: string | null;
  numero_serie: number | string;
  peso_kg: number | string;
  repeticiones: number | string;
  rpe: number | string;
}

export interface HistorialResponse {
  ok: boolean;
  dias: number;
  series: SerieHistorial[];
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

/** Respuesta de la encuesta de la sesion (ver infinityfree/api/feedback_tabla.php). */
export interface FeedbackItem {
  tipo: 'musculo' | 'ejercicio' | 'dia';
  clave: string;               // id del musculo o nombre del ejercicio
  bombeo?: number | null;      // 1 poco | 2 bueno | 3 brutal
  carga?: number | null;       // 1 facil | 2 justa | 3 demasiado (tipo 'dia': energia / sueno, 1 bien .. 3 mal)
  agujetas?: number | null;    // 1 nada | 2 sanaron justo | 3 aun duelen
  dolor?: number | null;       // 1 = molestia articular
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

  getHistorial(dias = 30): Observable<HistorialResponse> {
    return this.http.get<HistorialResponse>(
      `${environment.apiBaseUrl}/get_historial.php?dias=${dias}`,
      { headers: this.headers }
    );
  }

  /** Ultima nota del usuario por ejercicio (get_notas.php). */
  getNotas(): Observable<{ ok: boolean; notas: Array<{ ejercicio: string; notas: string; fecha_entreno: string }> }> {
    return this.http.get<{ ok: boolean; notas: Array<{ ejercicio: string; notas: string; fecha_entreno: string }> }>(
      `${environment.apiBaseUrl}/get_notas.php`,
      { headers: this.headers }
    );
  }

  /** "Usar siempre": {original, reemplazo} guarda; {original, baja: true} la quita. */
  guardarPreferencia(body: { original: string; reemplazo?: string; baja?: boolean }): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${environment.apiBaseUrl}/guardar_preferencia.php`, body, { headers: this.headers });
  }

  getPreferencias(): Observable<{ ok: boolean; preferencias: Array<{ original: string; reemplazo: string }> }> {
    return this.http.get<{ ok: boolean; preferencias: Array<{ original: string; reemplazo: string }> }>(
      `${environment.apiBaseUrl}/get_preferencias.php`,
      { headers: this.headers }
    );
  }

  /** Alta o baja ({endpoint, baja: true}) de la suscripcion a avisos push. */
  guardarSuscripcion(sub: unknown): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(
      `${environment.apiBaseUrl}/guardar_suscripcion.php`,
      sub,
      { headers: this.headers }
    );
  }

  guardarFeedback(fecha: string, items: FeedbackItem[]): Observable<{ ok: boolean; guardadas: number }> {
    return this.http.post<{ ok: boolean; guardadas: number }>(
      `${environment.apiBaseUrl}/guardar_feedback.php`,
      { fecha, items },
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

import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { DEMO_HISTORIAL, DEMO_PLAN } from './demo.generado';
import { fechaLocal } from './entreno-data';
import type { EjercicioPlan, FeedbackItem, HistorialResponse, RutinaHoyResponse, SeriePayload } from './rutina-api.service';

/**
 * MODO DEMO (oculto): para ensenar la app sin tocar NADA real.
 * - Se entra con 5 toques al logo (o abriendo la app con ?demo=1).
 * - Los datos salen de un atleta virtual (python-engine/exportar_demo.py).
 * - No hay red: esta "API" responde desde memoria y lo que se "guarda" se olvida.
 * - localStorage e IndexedDB se sustituyen por memoria (ver activarAlmacenDemo):
 *   tus colas, records, racha y entreno en curso no se leen ni se escriben.
 */
export const ES_DEMO = typeof location !== 'undefined' && new URLSearchParams(location.search).has('demo');

/** localStorage de mentira (memoria): la demo no ve ni pisa el almacen real. */
export function activarAlmacenDemo(): void {
  const datos = new Map<string, string>();
  const falso: Storage = {
    get length() {
      return datos.size;
    },
    clear: () => datos.clear(),
    getItem: (k: string) => (datos.has(k) ? datos.get(k)! : null),
    key: (i: number) => Array.from(datos.keys())[i] ?? null,
    removeItem: (k: string) => void datos.delete(k),
    setItem: (k: string, v: string) => void datos.set(k, String(v))
  };
  Object.defineProperty(window, 'localStorage', { value: falso, configurable: true });
  (globalThis as unknown as { __GYM_DEMO__: boolean }).__GYM_DEMO__ = true;
}

export function entrarDemo(): void {
  location.href = location.pathname + '?demo=1';
}

export function salirDemo(): void {
  location.href = location.pathname;
}

/** Misma forma que RutinaApiService, pero todo local y sin red. */
@Injectable()
export class DemoApiService {
  private readonly espera = 250; // como si hubiera red: se ven los "Cargando..."

  private lunes(): Date {
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return d;
  }

  getRutinaHoy(fecha = new Date()): Observable<RutinaHoyResponse> {
    const dia = ((fecha.getDay() + 6) % 7) + 1;
    const rutina = (DEMO_PLAN[dia] ?? []).map((f) => ({ ...f, semana_inicio: fechaLocal(this.lunes()) })) as EjercicioPlan[];
    return of({ ok: true, fecha: fechaLocal(fecha), semana_inicio: fechaLocal(this.lunes()), dia_semana: dia, rutina })
      .pipe(delay(this.espera));
  }

  getHistorial(dias = 30): Observable<HistorialResponse> {
    const lunes = this.lunes();
    const series = DEMO_HISTORIAL.filter((s) => s.dias_atras <= dias + 7).map((s) => {
      const f = new Date(lunes);
      f.setDate(f.getDate() - s.dias_atras);
      return { fecha_entreno: fechaLocal(f), ejercicio: s.ejercicio, tecnica: s.tecnica, numero_serie: s.numero_serie,
        peso_kg: s.peso_kg, repeticiones: s.repeticiones, rpe: s.rpe };
    }).sort((a, b) => (a.fecha_entreno < b.fecha_entreno ? 1 : -1));
    return of({ ok: true, dias, series }).pipe(delay(this.espera));
  }

  guardarEntreno(_fecha: string, items: SeriePayload[]): Observable<{ ok: boolean; inserted: number }> {
    return of({ ok: true, inserted: items.length }).pipe(delay(this.espera));
  }

  getNotas(): Observable<{ ok: boolean; notas: Array<{ ejercicio: string; notas: string; fecha_entreno: string }> }> {
    return of({ ok: true, notas: [] });
  }

  guardarFeedback(_fecha: string, items: FeedbackItem[]): Observable<{ ok: boolean; guardadas: number }> {
    return of({ ok: true, guardadas: items.length });
  }

  guardarPreferencia(_body: unknown): Observable<{ ok: boolean }> {
    return of({ ok: true });
  }

  getPreferencias(): Observable<{ ok: boolean; preferencias: Array<{ original: string; reemplazo: string }> }> {
    return of({ ok: true, preferencias: [] });
  }

  guardarSuscripcion(_sub: unknown): Observable<{ ok: boolean }> {
    return of({ ok: true });
  }
}

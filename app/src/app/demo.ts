import { Injectable, signal } from '@angular/core';
import { Observable, from, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';
import { environment } from '../environments/environment';
import { fechaLocal } from './entreno-data';
import type { EjercicioPlan, FeedbackItem, HistorialResponse, MenuSemana, NutricionResponse, RutinaHoyResponse, SeriePayload } from './rutina-api.service';

/**
 * MODO DEMO (oculto): para ensenar la app sin tocar NADA real.
 * - Se entra con 5 toques al logo (o abriendo la app con ?demo=1).
 * - Los planes los genera el motor (VM, /demo/api) para el tipo de entreno que
 *   elijas, con las 5 semanas del mesociclo; si no hay servidor, usa el
 *   escenario de respaldo que viene dentro (python-engine/exportar_demo.py).
 * - Solo LEE de la API publica de la demo: lo que se "guarda" se olvida.
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

/** Tipo de entreno de la demo (lo que el motor puede generar). */
export interface DemoConfig {
  enfoque: string;
  split: string;
  duracion: number;
}
export interface DemoOpciones {
  enfoques: Array<{ id: string; nombre: string }>;
  splits: Array<{ id: string; nombre: string }>;
  duraciones: number[];
  semanas: Array<{ n: number; nombre: string }>;
}
interface DemoEscenario {
  semanas: Record<string, Record<string, EjercicioPlan[]>>;
  historial: Array<{ dias_atras: number; ejercicio: string; tecnica: string; numero_serie: number;
    peso_kg: number; repeticiones: number; rpe: number }>;
}
interface DemoRespaldo {
  DEMO_OPCIONES: DemoOpciones;
  DEMO_ESCENARIO: DemoEscenario;
  DEMO_MENU: MenuSemana;
}

const POR_DEFECTO: DemoConfig = { enfoque: 'recomposicion', split: 'upper_lower', duracion: 75 };

/** Misma forma que RutinaApiService, pero sin tocar nada real. */
@Injectable()
export class DemoApiService {
  private readonly espera = 250; // como si hubiera red: se ven los "Cargando..."

  readonly opciones = signal<DemoOpciones | null>(null);
  readonly config = signal<DemoConfig>(this.leerUrl());
  readonly semana = signal(Math.min(5, Math.max(1, Number(new URLSearchParams(location.search).get('sem')) || 1)));
  readonly generando = signal(false);
  readonly aviso = signal('');
  private escenario: Promise<DemoEscenario> | null = null;
  private respaldo: Promise<DemoRespaldo> | null = null;

  constructor() {
    this.cargarRespaldo().then((r) => this.opciones() ?? this.opciones.set(r.DEMO_OPCIONES));
    this.pedir<DemoOpciones>('/opciones').then((o) => this.opciones.set(o)).catch(() => undefined);
  }

  /** Cambia el tipo de entreno y/o la semana del mesociclo (S1..S5). */
  cambiar(cambio: Partial<DemoConfig> & { semana?: number }): void {
    const { semana, ...cfg } = cambio;
    if (semana) this.semana.set(semana);
    if (Object.keys(cfg).length) {
      this.config.set({ ...this.config(), ...cfg });
      this.escenario = null;
    }
    const c = this.config();
    const q = new URLSearchParams({ demo: '1', enfoque: c.enfoque, split: c.split, duracion: String(c.duracion),
      sem: String(this.semana()) });
    history.replaceState(null, '', location.pathname + '?' + q.toString()); // recargar conserva lo elegido
  }

  private leerUrl(): DemoConfig {
    const q = new URLSearchParams(location.search);
    return { enfoque: q.get('enfoque') || POR_DEFECTO.enfoque, split: q.get('split') || POR_DEFECTO.split,
      duracion: Number(q.get('duracion')) || POR_DEFECTO.duracion };
  }

  /** Import dinamico: el respaldo no engorda la app normal (va en su propio archivo). */
  private cargarRespaldo(): Promise<DemoRespaldo> {
    return (this.respaldo ??= import('./demo.generado') as Promise<DemoRespaldo>);
  }

  private async pedir<T>(ruta: string, ms = 30000): Promise<T> {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), ms);
    try {
      const r = await fetch(environment.demoApi + ruta, { signal: ctl.signal });
      if (!r.ok) throw new Error(String(r.status));
      return (await r.json()) as T;
    } finally {
      clearTimeout(t);
    }
  }

  /** El escenario del tipo de entreno elegido: lo genera el motor (unos segundos la 1a vez). */
  private datos(): Promise<DemoEscenario> {
    if (this.escenario) return this.escenario;
    const c = this.config();
    const q = new URLSearchParams({ enfoque: c.enfoque, split: c.split, duracion: String(c.duracion) });
    this.generando.set(true);
    this.aviso.set('');
    this.escenario = this.pedir<DemoEscenario>('/escenario?' + q.toString())
      .catch(async () => {
        const r = await this.cargarRespaldo();
        const igual = c.enfoque === POR_DEFECTO.enfoque && c.split === POR_DEFECTO.split && c.duracion === POR_DEFECTO.duracion;
        this.aviso.set(igual ? '' : 'El motor (servidor) no respondió: se muestra el ejemplo guardado en la app.');
        return r.DEMO_ESCENARIO;
      })
      .finally(() => this.generando.set(false));
    return this.escenario;
  }

  private lunes(): Date {
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return d;
  }

  getRutinaHoy(fecha = new Date()): Observable<RutinaHoyResponse> {
    const dia = ((fecha.getDay() + 6) % 7) + 1;
    const lunes = fechaLocal(this.lunes());
    return from(this.datos()).pipe(
      map((e): RutinaHoyResponse => {
        const rutina = ((e.semanas[this.semana()] ?? {})[dia] ?? []).map((f) => ({ ...f, semana_inicio: lunes }));
        return { ok: true, fecha: fechaLocal(fecha), semana_inicio: lunes, dia_semana: dia, rutina };
      }),
      delay(this.espera)
    );
  }

  getHistorial(dias = 30): Observable<HistorialResponse> {
    const lunes = this.lunes();
    return from(this.datos()).pipe(
      map((e): HistorialResponse => {
        const series = e.historial.filter((s) => s.dias_atras <= dias + 7).map((s) => {
          const f = new Date(lunes);
          f.setDate(f.getDate() - s.dias_atras);
          return { fecha_entreno: fechaLocal(f), ejercicio: s.ejercicio, tecnica: s.tecnica, numero_serie: s.numero_serie,
            peso_kg: s.peso_kg, repeticiones: s.repeticiones, rpe: s.rpe };
        }).sort((a, b) => (a.fecha_entreno < b.fecha_entreno ? 1 : -1));
        return { ok: true, dias, series };
      }),
      delay(this.espera)
    );
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

  /** Nutricion del atleta virtual (75 kg, recomposicion: 1.8-2.2 g/kg). Nada se guarda. */
  getNutricion(dias = 14): Observable<NutricionResponse> {
    const lunes = this.lunes();
    const historial = Array.from({ length: Math.min(dias, 6) }, (_, i) => {
      const f = new Date(lunes);
      f.setDate(f.getDate() - (i + 1));
      return { fecha: fechaLocal(f), proteina_g: [128, 141, 150, 119, 137, 146][i], porciones: {} };
    }).reverse();
    return of({ ok: true, meta: { proteina_min: 135, proteina_max: 165, kcal: 2480, peso: 75, enfoque: 'recomposicion' },
                dias: historial }).pipe(delay(this.espera));
  }

  /** Menu del atleta virtual (generado con precios de referencia, viene dentro de la app). */
  getMenu(_fecha = new Date()): Observable<{ ok: boolean; menu: MenuSemana | null }> {
    return from(this.cargarRespaldo()).pipe(map((r) => ({ ok: true, menu: r.DEMO_MENU })), delay(this.espera));
  }

  guardarProteina(_fecha: string, _g: number, _porciones: Record<string, number>): Observable<{ ok: boolean }> {
    return of({ ok: true });
  }
}

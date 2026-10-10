import { Injectable, computed, inject, signal } from '@angular/core';
import * as almacen from './almacen';
import { fechaLocal } from './entreno-data';
import { MenuSemana, RutinaApiService } from './rutina-api.service';

/**
 * Proteina del dia por PORCIONES (sin pesar comida ni contar calorias): lo que
 * mas importa para el musculo es llegar a la proteina diaria (~1.6 g/kg o mas
 * segun el enfoque; Morton 2018, ISSN 2017) y anotar por porciones es lo que
 * la gente sostiene. La meta la calcula el motor con tu peso y tu enfoque
 * (python-engine/nutricion.py) y llega por get_nutricion.php.
 *
 * Gramos por porcion: valores APROXIMADOS (USDA FoodData Central / SMAE).
 */
export interface Porcion {
  id: string;
  nombre: string;
  porcion: string;
  g: number;
  barato?: boolean;   // de lo mas barato por gramo de proteina en Mexico (Profeco 2026)
}

export const PORCIONES: Porcion[] = [
  { id: 'huevo', nombre: 'Huevo', porcion: '1 pieza', g: 6, barato: true },
  { id: 'frijol', nombre: 'Frijoles', porcion: '1 taza cocidos', g: 15, barato: true },
  { id: 'lentejas', nombre: 'Lentejas', porcion: '1 taza cocidas', g: 18, barato: true },
  { id: 'soya', nombre: 'Soya texturizada', porcion: '½ taza seca', g: 12, barato: true },
  { id: 'atun', nombre: 'Atún', porcion: '1 lata escurrida', g: 24, barato: true },
  { id: 'sardina', nombre: 'Sardina', porcion: '100 g', g: 21, barato: true },
  { id: 'pollo', nombre: 'Pollo', porcion: '100 g cocido (una palma)', g: 28 },
  { id: 'res', nombre: 'Res o cerdo', porcion: '100 g cocido', g: 26 },
  { id: 'pescado', nombre: 'Pescado', porcion: '100 g cocido', g: 22 },
  { id: 'leche', nombre: 'Leche', porcion: '1 vaso (250 ml)', g: 8, barato: true },
  { id: 'yogur_griego', nombre: 'Yogur griego', porcion: '1 taza', g: 18 },
  { id: 'queso', nombre: 'Queso panela o fresco', porcion: '60 g (2 rebanadas)', g: 11 },
  { id: 'tortilla', nombre: 'Tortillas de maíz', porcion: '3 piezas', g: 5, barato: true },
  { id: 'avena', nombre: 'Avena', porcion: '½ taza cruda', g: 5, barato: true },
  { id: 'cacahuate', nombre: 'Cacahuates', porcion: '1 puño (30 g)', g: 7 },
  { id: 'scoop', nombre: 'Proteína en polvo', porcion: '1 scoop', g: 24 },
  { id: 'otro', nombre: 'Otro', porcion: 'algo más', g: 5 }
];

const POR_ID = new Map(PORCIONES.map((p) => [p.id, p]));

export interface MetaNutricion {
  proteina_min: number;
  proteina_max: number;
  kcal: number | null;
  peso: number | null;
  enfoque: string | null;
}

/** Sin meta del servidor todavia: 1.6 g/kg de 75 kg (lo minimo que respalda la evidencia). */
const META_POR_DEFECTO: MetaNutricion = { proteina_min: 120, proteina_max: 150, kcal: null, peso: null, enfoque: null };

interface Pendiente {
  fecha: string;
  proteina_g: number;
  porciones: Record<string, number>;
}

export function gramosDe(porciones: Record<string, number>): number {
  let total = 0;
  for (const [id, n] of Object.entries(porciones)) total += (POR_ID.get(id)?.g ?? 0) * (n || 0);
  return Math.round(total * 10) / 10;
}

@Injectable({ providedIn: 'root' })
export class NutricionService {
  private readonly api = inject(RutinaApiService);
  private fecha = fechaLocal(new Date());
  private temporizador: ReturnType<typeof setTimeout> | null = null;
  private cargado = false;

  readonly porciones = signal<Record<string, number>>({});
  readonly meta = signal<MetaNutricion | null>(this.metaGuardada());
  readonly promedio7 = signal<number | null>(null);
  readonly sinConexion = signal(false);
  readonly menu = signal<MenuSemana | null>(this.menuGuardado());
  readonly cargandoMenu = signal(false);
  private menuPedido = false;

  readonly total = computed(() => gramosDe(this.porciones()));
  readonly metaEfectiva = computed(() => this.meta() ?? META_POR_DEFECTO);
  readonly pct = computed(() => Math.min(100, Math.round((this.total() / this.metaEfectiva().proteina_min) * 100)));

  /** Hoy desde el telefono; meta y semana desde el servidor (si responde). */
  async cargar(): Promise<void> {
    const hoy = fechaLocal(new Date());
    if (this.cargado && hoy === this.fecha) return;
    this.fecha = hoy;
    this.cargado = true;
    const local = await almacen.leer<Record<string, number>>('proteina-' + hoy);
    this.porciones.set(local ?? {});
    this.api.getNutricion(14).subscribe({
      next: (res) => {
        this.sinConexion.set(false);
        if (res.meta) {
          const m: MetaNutricion = {
            proteina_min: Number(res.meta.proteina_min),
            proteina_max: Number(res.meta.proteina_max),
            kcal: res.meta.kcal == null ? null : Number(res.meta.kcal),
            peso: res.meta.peso == null ? null : Number(res.meta.peso),
            enfoque: res.meta.enfoque ?? null
          };
          this.meta.set(m);
          try {
            localStorage.setItem('nut-meta', JSON.stringify(m));
          } catch {
            /* sin espacio: se usa la meta en memoria */
          }
        }
        const dias = res.dias ?? [];
        // otro dispositivo ya registro hoy y este telefono no: se adopta lo del servidor
        const deHoy = dias.find((d) => String(d.fecha).slice(0, 10) === hoy);
        if (!local && deHoy && deHoy.porciones && Object.keys(deHoy.porciones).length) {
          this.porciones.set({ ...deHoy.porciones });
        }
        const recientes = dias.filter((d) => String(d.fecha).slice(0, 10) !== hoy && Number(d.proteina_g) > 0).slice(-7);
        this.promedio7.set(recientes.length ? recientes.reduce((s, d) => s + Number(d.proteina_g), 0) / recientes.length : null);
      },
      error: () => this.sinConexion.set(true)
    });
  }

  /** Menu de la semana (lo genera el motor); se guarda en el telefono para verlo sin red. */
  cargarMenu(): void {
    if (this.menuPedido) return;
    this.menuPedido = true;
    this.cargandoMenu.set(true);
    this.api.getMenu(new Date()).subscribe({
      next: (res) => {
        this.cargandoMenu.set(false);
        if (res.menu) {
          this.menu.set(res.menu);
          try {
            localStorage.setItem('menu-semana', JSON.stringify(res.menu));
          } catch {
            /* sin espacio: queda en memoria */
          }
        }
      },
      error: () => {
        this.cargandoMenu.set(false);
        this.menuPedido = false;     // se reintenta la proxima vez que se abra
      }
    });
  }

  cantidad(id: string): number {
    return this.porciones()[id] ?? 0;
  }

  sumar(id: string, delta: number): void {
    if (!POR_ID.has(id)) return;
    const hoy = fechaLocal(new Date());
    if (hoy !== this.fecha) {
      // paso la medianoche con la app abierta: el dia nuevo empieza en cero
      this.fecha = hoy;
      this.porciones.set({});
    }
    const actual = { ...this.porciones() };
    const n = Math.max(0, Math.min(50, (actual[id] ?? 0) + delta));
    if (n === 0) delete actual[id];
    else actual[id] = n;
    this.porciones.set(actual);
    void almacen.guardar('proteina-' + this.fecha, actual);
    // se manda el total del dia un momento despues (varios toques = un solo envio)
    if (this.temporizador) clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.enviar({ fecha: this.fecha, proteina_g: this.total(), porciones: actual }), 1500);
  }

  /** Lo que no se pudo mandar (sin red) se reintenta al volver internet o al abrir la app. */
  async reenviarPendiente(): Promise<void> {
    const p = await almacen.leer<Pendiente>('proteina-pendiente');
    if (p) this.enviar(p);
  }

  private enviar(p: Pendiente): void {
    void almacen.guardar('proteina-pendiente', p);
    this.api.guardarProteina(p.fecha, p.proteina_g, p.porciones).subscribe({
      next: () => {
        this.sinConexion.set(false);
        // solo se borra si no hubo un cambio posterior mientras viajaba
        void almacen.leer<Pendiente>('proteina-pendiente').then((actual) => {
          if (actual && actual.fecha === p.fecha && actual.proteina_g === p.proteina_g) {
            void almacen.borrar('proteina-pendiente');
          }
        });
      },
      error: () => this.sinConexion.set(true)
    });
  }

  private menuGuardado(): MenuSemana | null {
    try {
      const v = localStorage.getItem('menu-semana');
      return v ? (JSON.parse(v) as MenuSemana) : null;
    } catch {
      return null;
    }
  }

  private metaGuardada(): MetaNutricion | null {
    try {
      const v = localStorage.getItem('nut-meta');
      return v ? (JSON.parse(v) as MetaNutricion) : null;
    } catch {
      return null;
    }
  }
}

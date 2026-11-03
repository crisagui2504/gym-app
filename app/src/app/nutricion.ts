import { Injectable, computed, inject, signal } from '@angular/core';
import * as almacen from './almacen';
import { fechaLocal } from './entreno-data';
import { CheckinResponse, MenuComida, MenuDia, MenuSemana, Pesaje, RutinaApiService } from './rutina-api.service';
import { FilaLista, ORDEN_TIENDAS, claveEleccion, cocina, comidasDelDia, elegida, listaSuper, textoLista } from './menu-semana';

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
  kcal?: number;      // aproximadas (USDA / SMAE), por porcion
  carb?: number;      // g de carbohidratos por porcion (aprox.)
  grasa?: number;     // g de grasa por porcion (aprox.)
  fuera?: boolean;    // platillo de la calle / fonda
}

export const PORCIONES: Porcion[] = [
  { id: 'huevo', nombre: 'Huevo', porcion: '1 pieza', g: 6, barato: true, kcal: 72, carb: 0.4, grasa: 5 },
  { id: 'frijol', nombre: 'Frijoles', porcion: '1 taza cocidos', g: 15, barato: true, kcal: 225, carb: 40, grasa: 1 },
  { id: 'lentejas', nombre: 'Lentejas', porcion: '1 taza cocidas', g: 18, barato: true, kcal: 230, carb: 40, grasa: 1 },
  { id: 'soya', nombre: 'Soya texturizada', porcion: '½ taza seca', g: 12, barato: true, kcal: 85, carb: 8, grasa: 0.3 },
  { id: 'atun', nombre: 'Atún', porcion: '1 lata escurrida', g: 24, barato: true, kcal: 130, carb: 0, grasa: 3 },
  { id: 'sardina', nombre: 'Sardina', porcion: '100 g', g: 21, barato: true, kcal: 190, carb: 1, grasa: 11 },
  { id: 'pollo', nombre: 'Pollo', porcion: '100 g cocido (una palma)', g: 28, kcal: 165, carb: 0, grasa: 4 },
  { id: 'res', nombre: 'Res o cerdo', porcion: '100 g cocido', g: 26, kcal: 250, carb: 0, grasa: 15 },
  { id: 'pescado', nombre: 'Pescado', porcion: '100 g cocido', g: 22, kcal: 130, carb: 0, grasa: 4 },
  { id: 'leche', nombre: 'Leche', porcion: '1 vaso (250 ml)', g: 8, barato: true, kcal: 150, carb: 12, grasa: 8 },
  { id: 'yogur_griego', nombre: 'Yogur griego', porcion: '1 taza', g: 18, kcal: 150, carb: 8, grasa: 4 },
  { id: 'queso', nombre: 'Queso panela o fresco', porcion: '60 g (2 rebanadas)', g: 11, kcal: 150, carb: 2, grasa: 11 },
  { id: 'tortilla', nombre: 'Tortillas de maíz', porcion: '3 piezas', g: 5, barato: true, kcal: 160, carb: 33, grasa: 2 },
  { id: 'avena', nombre: 'Avena', porcion: '½ taza cruda', g: 5, barato: true, kcal: 150, carb: 27, grasa: 3 },
  { id: 'cacahuate', nombre: 'Cacahuates', porcion: '1 puño (30 g)', g: 7, kcal: 170, carb: 5, grasa: 14 },
  { id: 'scoop', nombre: 'Proteína en polvo', porcion: '1 scoop', g: 24, kcal: 120, carb: 3, grasa: 1.5 },
  { id: 'otro', nombre: 'Otro', porcion: 'algo más', g: 5, kcal: 50, carb: 3, grasa: 2 },
  // ── Comí fuera: platillos comunes de calle y fonda (APROXIMADOS: USDA y recetas típicas) ──
  { id: 'f_pastor', nombre: 'Tacos al pastor', porcion: '3 tacos', g: 24, kcal: 560, carb: 50, grasa: 28, fuera: true },
  { id: 'f_asada', nombre: 'Tacos de asada', porcion: '3 tacos', g: 30, kcal: 540, carb: 45, grasa: 26, fuera: true },
  { id: 'f_canasta', nombre: 'Tacos de canasta', porcion: '4 tacos', g: 14, kcal: 620, carb: 70, grasa: 31, fuera: true },
  { id: 'f_quesadilla', nombre: 'Quesadillas de comal', porcion: '2 con queso', g: 22, kcal: 600, carb: 50, grasa: 34, fuera: true },
  { id: 'f_torta', nombre: 'Torta de milanesa o pierna', porcion: '1 torta', g: 32, kcal: 750, carb: 80, grasa: 33, fuera: true },
  { id: 'f_corrida', nombre: 'Comida corrida', porcion: 'sopa, arroz, guisado', g: 35, kcal: 900, carb: 110, grasa: 35, fuera: true },
  { id: 'f_pozole', nombre: 'Pozole', porcion: '1 plato grande', g: 30, kcal: 550, carb: 55, grasa: 22, fuera: true },
  { id: 'f_enchiladas', nombre: 'Enchiladas de pollo', porcion: '3 piezas', g: 28, kcal: 650, carb: 60, grasa: 33, fuera: true },
  { id: 'f_chilaquiles', nombre: 'Chilaquiles con pollo', porcion: '1 plato', g: 25, kcal: 700, carb: 70, grasa: 36, fuera: true },
  { id: 'f_tamal', nombre: 'Tamal', porcion: '1 pieza', g: 8, kcal: 300, carb: 35, grasa: 15, fuera: true },
  { id: 'f_rostizado', nombre: 'Pollo rostizado', porcion: '¼ de pollo', g: 38, kcal: 550, carb: 5, grasa: 42, fuera: true },
  { id: 'f_hamburguesa', nombre: 'Hamburguesa sencilla', porcion: '1 pieza', g: 25, kcal: 550, carb: 45, grasa: 30, fuera: true },
  { id: 'f_pizza', nombre: 'Pizza', porcion: '2 rebanadas', g: 24, kcal: 560, carb: 65, grasa: 22, fuera: true },
  { id: 'f_sushi', nombre: 'Sushi empanizado', porcion: '1 rollo', g: 15, kcal: 650, carb: 80, grasa: 30, fuera: true },
  { id: 'f_burrito', nombre: 'Burrito de carne', porcion: '1 pieza', g: 30, kcal: 700, carb: 75, grasa: 30, fuera: true },
  { id: 'f_gorditas', nombre: 'Gorditas de chicharrón', porcion: '2 piezas', g: 14, kcal: 650, carb: 60, grasa: 39, fuera: true },
  { id: 'f_caldo', nombre: 'Caldo de res o de pollo', porcion: '1 plato', g: 30, kcal: 400, carb: 30, grasa: 17, fuera: true },
  { id: 'f_coctel', nombre: 'Cóctel de camarón', porcion: '1 mediano', g: 25, kcal: 250, carb: 25, grasa: 5, fuera: true },
  { id: 'f_esquite', nombre: 'Esquite', porcion: '1 vaso mediano', g: 6, kcal: 350, carb: 45, grasa: 16, fuera: true },
  { id: 'f_licuado', nombre: 'Licuado de plátano (fonda)', porcion: '1 vaso grande', g: 12, kcal: 350, carb: 55, grasa: 9, fuera: true }
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

/** Pesajes que aun no llegan al servidor (sin red), por fecha. */
type PesosPendientes = Record<string, { peso: number; cintura: number | null }>;

export const PESAJES_TENDENCIA = 8;       // como python-engine/nutricion.py tendencia_pct_sem
const VENTANA_TENDENCIA = 21;

const mediodia = (fecha: string) => new Date(fecha + 'T12:00:00').getTime();

/** Pesajes de los ultimos 21 dias (inclusive), ordenados. */
export function pesajesRecientes(pesos: Pesaje[], hoy = new Date()): Pesaje[] {
  const desde = new Date(hoy);
  desde.setHours(12, 0, 0, 0);
  desde.setDate(desde.getDate() - VENTANA_TENDENCIA);
  const lim = fechaLocal(desde);
  return pesos.filter((p) => p.fecha >= lim && p.peso > 0).sort((a, b) => (a.fecha < b.fecha ? -1 : 1));
}

/** Cambio de peso por semana: recta sobre los pesajes de los ultimos 21 dias, la
 *  misma cuenta que hace el motor para ajustar las calorias (nutricion.py):
 *  hacen falta 8 pesajes y 10 dias de rango; con menos, la bascula solo mide agua. */
export function tendenciaPeso(pesos: Pesaje[], hoy = new Date()): { pct: number; kg: number } | null {
  const d = pesajesRecientes(pesos, hoy);
  if (d.length < PESAJES_TENDENCIA) return null;
  const x = d.map((p) => Math.round((mediodia(p.fecha) - mediodia(d[0].fecha)) / 864e5));
  if (x[x.length - 1] < 10) return null;
  const y = d.map((p) => Number(p.peso));
  const mx = x.reduce((s, v) => s + v, 0) / x.length;
  const my = y.reduce((s, v) => s + v, 0) / y.length;
  let num = 0;
  let den = 0;
  x.forEach((v, i) => {
    num += (v - mx) * (y[i] - my);
    den += (v - mx) ** 2;
  });
  const kg = (num / den) * 7;
  return { kg, pct: (kg / my) * 100 };
}

/** "menu_<tiempo>": comida del menu marcada como "Lo comi"; su valor ya son gramos. */
export const esDelMenu = (id: string) => id.startsWith('menu_');

/** Las 4 comidas del dia. En porciones, "<pre>_<id>" = esa porcion en esa comida
 *  ("de_huevo": 2). Sin prefijo (registros viejos o GymTracker) cuenta igual, sin comida. */
export interface Tiempo {
  id: string;
  pre: string;
  nombre: string;
  ico: string;
  parte: number;      // parte de las kcal del dia si no hay menu (aprox. 25/35/15/25 %)
}
export const TIEMPOS: Tiempo[] = [
  { id: 'desayuno', pre: 'de', nombre: 'Desayuno', ico: '🍳', parte: 0.25 },
  { id: 'comida', pre: 'co', nombre: 'Comida', ico: '🍲', parte: 0.35 },
  { id: 'colacion', pre: 'cl', nombre: 'Colación', ico: '🍎', parte: 0.15 },
  { id: 'cena', pre: 'ce', nombre: 'Cena', ico: '🌮', parte: 0.25 }
];
const POR_PRE = new Map(TIEMPOS.map((t) => [t.pre, t]));

/** "de_huevo" -> {tiempo: desayuno, id: huevo}; "huevo" -> {tiempo: null, id: huevo}. */
export function partirClave(clave: string): { tiempo: Tiempo | null; id: string } {
  const t = POR_PRE.get(clave.slice(0, 2));
  return t && clave[2] === '_' ? { tiempo: t, id: clave.slice(3) } : { tiempo: null, id: clave };
}

export interface Macros {
  kcal: number;
  prot: number;
  carb: number;
  grasa: number;
}
const CERO: Macros = { kcal: 0, prot: 0, carb: 0, grasa: 0 };
const sumarMacros = (a: Macros, b: Macros): Macros =>
  ({ kcal: a.kcal + b.kcal, prot: a.prot + b.prot, carb: a.carb + b.carb, grasa: a.grasa + b.grasa });

export interface Anotado extends Macros {
  clave: string;      // la llave en porciones ("de_huevo" o "menu_desayuno")
  nombre: string;
  n: number;          // porciones (en las del menu, 1)
  menu: boolean;
}
export interface ComidaDelDia extends Macros {
  tiempo: Tiempo;
  items: Anotado[];
}

/** Lo anotado en un dia, por comida, con sus kcal y macros (aproximados). Las del
 *  menu ("Lo comi") guardan proteina en menu_<t> y kcal/carb/grasa en mk_/mc_/mg_<t>. */
export function desglosar(porciones: Record<string, number>, nombreMenu: (tiempo: string) => string = () => ''): {
  comidas: ComidaDelDia[]; sinComida: Anotado[]; total: Macros;
} {
  const comidas: ComidaDelDia[] = TIEMPOS.map((t) => ({ tiempo: t, items: [], ...CERO }));
  const sinComida: Anotado[] = [];
  for (const [clave, n] of Object.entries(porciones)) {
    if (!n) continue;
    let item: Anotado;
    let destino: ComidaDelDia | undefined;
    if (esDelMenu(clave)) {
      const t = clave.slice(5);
      destino = comidas.find((c) => c.tiempo.id === t);
      item = { clave, nombre: nombreMenu(t) || 'Del menú', n: 1, menu: true, prot: n,
               kcal: porciones['mk_' + t] ?? 0, carb: porciones['mc_' + t] ?? 0, grasa: porciones['mg_' + t] ?? 0 };
    } else {
      const { tiempo, id } = partirClave(clave);
      const p = POR_ID.get(id);
      if (!p) continue;                                    // creatina, mk_/mc_/mg_...
      item = { clave, nombre: p.nombre, n, menu: false, prot: p.g * n, kcal: (p.kcal ?? 0) * n,
               carb: (p.carb ?? 0) * n, grasa: (p.grasa ?? 0) * n };
      destino = tiempo ? comidas.find((c) => c.tiempo === tiempo) : undefined;
    }
    if (destino) {
      destino.items.push(item);
      Object.assign(destino, sumarMacros(destino, item));
    } else {
      sinComida.push(item);
    }
  }
  const total = [...comidas, ...sinComida].reduce((a, b) => sumarMacros(a, b), CERO);
  return { comidas, sinComida, total };
}

export function gramosDe(porciones: Record<string, number>): number {
  let total = 0;
  for (const [id, n] of Object.entries(porciones)) {
    total += esDelMenu(id) ? n || 0 : (POR_ID.get(partirClave(id).id)?.g ?? 0) * (n || 0);
  }
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
  /** Comidas que cambiaste: "fecha|tiempo" -> 0 (la del menu) o 1.. (alternativa). */
  readonly eleccion = signal<Record<string, number>>(this.leerJson('menu-eleccion', {}));
  /** Recetas que marcaste 👎: no se ofrecen en "Cambiar" y el motor ya no las pone. */
  readonly noMeGusta = signal<string[]>(this.leerJson('no-me-gusta', []));
  /** Lo que el telefono aun no pudo mandar: id -> alta (true) o baja (false). */
  private noGustaPend: Record<string, boolean> = this.leerJson('no-me-gusta-pend', {});
  /** Lo que ya tienes en casa (ids), por semana del menu. */
  readonly tengo = signal<string[]>(this.leerJson('despensa-' + (this.menu()?.semana_inicio ?? ''), []));
  /** Pesajes (servidor + los que aun no suben), del mas viejo al mas nuevo. */
  readonly pesos = signal<Pesaje[]>(this.leerJson('pesos-cache', []));
  readonly pesoPendiente = signal(false);
  readonly pesoHoy = computed(() => this.pesos().find((p) => p.fecha === fechaLocal(new Date())) ?? null);
  readonly tendencia = computed(() => tendenciaPeso(this.pesos()));
  readonly pesajes21 = computed(() => pesajesRecientes(this.pesos()).length);
  /** Dias recientes del servidor (para la racha de creatina). */
  private readonly diasServidor = signal<Array<{ fecha: string; proteina_g?: number; porciones: Record<string, number> }>>([]);
  /** Proteina registrada por dia (servidor; hoy, lo del telefono), para graficas. */
  readonly proteinaDias = computed(() => {
    const hoy = fechaLocal(new Date());
    const m = new Map(this.diasServidor().map((d) => [String(d.fecha).slice(0, 10), Number(d.proteina_g) || 0]));
    m.set(hoy, this.total());
    return [...m.entries()].map(([fecha, g]) => ({ fecha, g })).sort((a, b) => (a.fecha < b.fecha ? -1 : 1));
  });

  /** Tiendas donde compras (null = todas): la lista elige el producto de esas. */
  readonly tiendas = signal<string[] | null>(this.leerJson('menu-tiendas', null));
  readonly lista = computed<FilaLista[]>(() => {
    const m = this.menu();
    return m ? listaSuper(m, this.eleccion(), this.tiendas()) : [];
  });
  readonly cocina = computed(() => {
    const m = this.menu();
    return m ? cocina(m, this.eleccion()) : [];
  });
  readonly costoPendiente = computed(() =>
    this.lista().filter((f) => !this.tengo().includes(f.id)).reduce((s, f) => s + f.costo, 0)
  );
  /** De lo que pagas, lo que sobra y rinde para otras semanas (frijol, aceite, arroz...). */
  readonly despensaPendiente = computed(() =>
    this.lista().filter((f) => !this.tengo().includes(f.id)).reduce((s, f) => s + f.queda, 0)
  );
  readonly creatinaHoy = computed(() => !!this.porciones()['creatina']);
  /** Dias seguidos con creatina, contando hoy si ya la tomaste. */
  readonly rachaCreatina = computed(() => {
    const con = new Set(this.diasServidor().filter((d) => d.porciones?.['creatina']).map((d) => String(d.fecha).slice(0, 10)));
    const hoy = fechaLocal(new Date());
    if (this.creatinaHoy()) con.add(hoy);
    else con.delete(hoy);
    const dia = new Date();
    if (!con.has(hoy)) dia.setDate(dia.getDate() - 1);       // aun no la tomas hoy: la racha viene de ayer
    let n = 0;
    while (con.has(fechaLocal(dia))) {
      n++;
      dia.setDate(dia.getDate() - 1);
    }
    return n;
  });

  readonly total = computed(() => gramosDe(this.porciones()));

  /** El dia de hoy en el menu de la semana (si el menu lo cubre). */
  readonly menuHoy = computed(() => this.menu()?.dias.find((d) => d.fecha === fechaLocal(new Date())) ?? null);
  /** Lo de hoy por comida, con kcal y macros (aprox.). */
  readonly desglose = computed(() => {
    const d = this.menuHoy();
    return desglosar(this.porciones(), (t) => {
      const c = d?.comidas.find((x) => x.tiempo === t);
      return d && c ? this.comidaDe(d, c).nombre : '';
    });
  });
  /** Metas de HOY: kcal del dia (mas si entrenas: kcal_por_dia del motor, via el menu),
   *  proteina del motor y carb/grasa del menu; sin menu, del promedio (grasa ~27 %). */
  readonly metaHoy = computed(() => {
    const m = this.metaEfectiva();
    const d = this.menuHoy();
    const kcal = d?.kcal_meta ?? m.kcal ?? 2200;
    const prot = m.proteina_min;
    const grasa = d?.grasa ?? Math.round((kcal * 0.27) / 9);
    const carb = d?.carb ?? Math.max(0, Math.round((kcal - prot * 4 - grasa * 9) / 4));
    const porTiempo: Record<string, number> = {};
    for (const t of TIEMPOS) {
      const c = d?.comidas.find((x) => x.tiempo === t.id);
      porTiempo[t.id] = Math.round(d && c ? this.comidaDe(d, c).kcal : kcal * t.parte);
    }
    return { kcal, prot, carb, grasa, porTiempo, conMenu: !!d };
  });
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
        this.diasServidor.set(dias);
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
    this.cargarPesos();
  }

  // ----- Peso corporal: lo que pilota las calorias (el motor lo lee de MySQL) -----
  private cargarPesos(): void {
    this.api.getPeso(60).subscribe({
      next: async (res) => {
        const pend = (await almacen.leer<PesosPendientes>('peso-pendiente')) ?? {};
        // lo que aun no sube manda: es mas nuevo que lo del servidor
        const todos = new Map((res.pesos ?? []).map((p) => [String(p.fecha).slice(0, 10), {
          fecha: String(p.fecha).slice(0, 10), peso: Number(p.peso), cintura: p.cintura == null ? null : Number(p.cintura)
        }]));
        for (const [fecha, p] of Object.entries(pend)) todos.set(fecha, { fecha, ...p });
        this.fijarPesos([...todos.values()]);
        this.pesoPendiente.set(Object.keys(pend).length > 0);
      },
      error: () => undefined         // sin red: se queda lo guardado en el telefono
    });
  }

  /** Anota (o corrige) el peso de hoy. Devuelve un error para mostrar, o ''. */
  async anotarPeso(peso: number, cintura: number | null): Promise<string> {
    if (!(peso >= 30 && peso <= 250)) return 'El peso va de 30 a 250 kg.';
    if (cintura != null && !(cintura >= 40 && cintura <= 200)) return 'La cintura va de 40 a 200 cm.';
    const fecha = fechaLocal(new Date());
    const previa = this.pesos().find((p) => p.fecha === fecha);
    const nuevo: Pesaje = {
      fecha,
      peso: Math.round(peso * 10) / 10,
      cintura: cintura != null ? Math.round(cintura * 10) / 10 : previa?.cintura ?? null   // sin cintura: conserva la de hoy
    };
    this.fijarPesos([...this.pesos().filter((p) => p.fecha !== fecha), nuevo]);
    const pend = (await almacen.leer<PesosPendientes>('peso-pendiente')) ?? {};
    pend[fecha] = { peso: nuevo.peso, cintura: nuevo.cintura };
    await almacen.guardar('peso-pendiente', pend);
    this.enviarPesos(pend);
    return '';
  }

  private fijarPesos(pesos: Pesaje[]): void {
    const orden = [...pesos].sort((a, b) => (a.fecha < b.fecha ? -1 : 1)).slice(-90);
    this.pesos.set(orden);
    this.guardarJson('pesos-cache', orden);
  }

  /** Upsert por fecha: reenviar es seguro. Solo se borra de la cola si no cambio mientras viajaba. */
  private enviarPesos(pend: PesosPendientes): void {
    const fechas = Object.keys(pend);
    this.pesoPendiente.set(fechas.length > 0);
    for (const fecha of fechas) {
      const p = pend[fecha];
      this.api.guardarPeso(fecha, p.peso, p.cintura).subscribe({
        next: async () => {
          const actual = (await almacen.leer<PesosPendientes>('peso-pendiente')) ?? {};
          if (actual[fecha] && actual[fecha].peso === p.peso && actual[fecha].cintura === p.cintura) {
            delete actual[fecha];
            await almacen.guardar('peso-pendiente', actual);
          }
          this.pesoPendiente.set(Object.keys(actual).length > 0);
        },
        error: () => this.pesoPendiente.set(true)
      });
    }
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
          // lo marcado en el dashboard (o en otro telefono) + lo de aqui que aun no sube
          const servidor = res.menu.no_me_gusta?.recetas ?? [];
          const juntos = new Set([...this.noMeGusta(), ...servidor]);
          for (const [id, alta] of Object.entries(this.noGustaPend)) {
            if (alta) juntos.add(id); else juntos.delete(id);
          }
          this.noMeGusta.set([...juntos]);
          this.guardarJson('no-me-gusta', [...juntos]);
          this.tengo.set(this.leerJson('despensa-' + res.menu.semana_inicio, []));
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

  // ----- Menu: cambiar una comida, ya tengo en casa, compartir -----
  comidaDe(d: MenuDia, c: MenuComida): MenuComida {
    return comidasDelDia({ ...d, comidas: [c] }, this.eleccion())[0];
  }

  comidasDe(d: MenuDia): MenuComida[] {
    return comidasDelDia(d, this.eleccion());
  }

  totalesDe(d: MenuDia): { kcal: number; prot: number; costo: number } {
    return this.comidasDe(d).reduce(
      (s, c) => ({ kcal: s.kcal + c.kcal, prot: s.prot + c.prot, costo: s.costo + c.costo }),
      { kcal: 0, prot: 0, costo: 0 }
    );
  }

  opcionDe(d: MenuDia, c: MenuComida): number {
    return this.eleccion()[claveEleccion(d, c)] ?? 0;
  }

  /** Pasa a la siguiente opcion de esa comida (la del menu y sus alternativas, en circulo),
   *  saltando las que marcaste 👎. */
  cambiarComida(d: MenuDia, c: MenuComida): void {
    const n = 1 + (c.alternativas?.length ?? 0);
    if (n < 2) return;
    const actual = this.eleccion()[claveEleccion(d, c)] ?? 0;
    let sig = (actual + 1) % n;
    for (let i = 0; i < n - 1 && this.noGusta(elegida(c, sig).receta); i++) sig = (sig + 1) % n;
    if (sig !== actual) this.elegirOpcion(d, c, sig);
  }

  /** Pone la opcion `idx` de esa comida (0 = la del menu); las sobras cambian con su dia de cocina. */
  elegirOpcion(d: MenuDia, c: MenuComida, idx: number): void {
    const clave = claveEleccion(d, c);
    if ((this.eleccion()[clave] ?? 0) === idx || idx < 0 || idx > (c.alternativas?.length ?? 0)) return;
    const nueva = { ...this.eleccion(), [clave]: idx };
    this.eleccion.set(nueva);
    this.guardarJson('menu-eleccion', nueva);
    // si ya la habias marcado como comida, se actualiza con la proteina de la nueva
    if (d.fecha === fechaLocal(new Date()) && this.comioMenu(c.tiempo)) {
      this.alternarMenu(c.tiempo, 0);
      const nueva = this.comidaDe(d, c);
      this.alternarMenu(c.tiempo, nueva.prot, nueva);
    }
  }

  noGusta(receta: string): boolean {
    return this.noMeGusta().includes(receta);
  }

  /** 👎 en una comida: se marca (o se desmarca) y, si es la que tocaba, se cambia por otra. */
  marcarNoMeGusta(d: MenuDia, c: MenuComida): void {
    const receta = this.comidaDe(d, c).receta;
    const alta = !this.noGusta(receta);
    const lista = alta ? [...this.noMeGusta(), receta] : this.noMeGusta().filter((x) => x !== receta);
    this.noMeGusta.set(lista);
    this.guardarJson('no-me-gusta', lista);
    this.noGustaPend = { ...this.noGustaPend, [receta]: alta };
    this.guardarJson('no-me-gusta-pend', this.noGustaPend);
    this.enviarNoMeGusta();
    if (alta) this.cambiarComida(d, c);
  }

  private enviarNoMeGusta(): void {
    for (const [id, alta] of Object.entries(this.noGustaPend)) {
      this.api.guardarNoMeGusta('receta', id, !alta).subscribe({
        next: () => {
          // solo se borra si no lo volviste a tocar mientras viajaba
          if (this.noGustaPend[id] === alta) {
            const { [id]: _, ...resto } = this.noGustaPend;
            this.noGustaPend = resto;
            this.guardarJson('no-me-gusta-pend', resto);
          }
        },
        error: () => this.sinConexion.set(true)
      });
    }
  }

  usaTienda(t: string): boolean {
    return !this.tiendas() || this.tiendas()!.includes(t);
  }

  /** Prende o apaga una tienda en la lista (siempre queda al menos una). */
  alternarTienda(t: string): void {
    const actuales = this.tiendas() ?? ORDEN_TIENDAS;
    const nuevas = actuales.includes(t) ? actuales.filter((x) => x !== t) : ORDEN_TIENDAS.filter((x) => x === t || actuales.includes(x));
    if (!nuevas.length) return;
    const valor = nuevas.length === ORDEN_TIENDAS.length ? null : nuevas;
    this.tiendas.set(valor);
    this.guardarJson('menu-tiendas', valor);
  }

  alternarTengo(id: string): void {
    const m = this.menu();
    if (!m) return;
    const t = this.tengo().includes(id) ? this.tengo().filter((x) => x !== id) : [...this.tengo(), id];
    this.tengo.set(t);
    this.guardarJson('despensa-' + m.semana_inicio, t);
  }

  /** Comparte la lista (sin lo que ya tienes); si el telefono no puede, la copia. */
  async compartirLista(): Promise<string> {
    const m = this.menu();
    if (!m) return '';
    const texto = textoLista(m, this.lista(), this.tengo());
    try {
      if (navigator.share) {
        await navigator.share({ title: 'Lista del súper', text: texto });
        return '';
      }
      await navigator.clipboard.writeText(texto);
      return 'Lista copiada: pégala en WhatsApp o en tus notas.';
    } catch {
      return '';
    }
  }

  // ----- Creatina: un toque al dia -----
  alternarCreatina(): void {
    const actual = this.deHoy();
    if (actual['creatina']) delete actual['creatina'];
    else actual['creatina'] = 1;
    this.aplicar(actual);
  }

  cantidad(id: string): number {
    return this.porciones()[id] ?? 0;
  }

  sumar(id: string, delta: number): void {
    if (!POR_ID.has(id)) return;
    const actual = this.deHoy();
    const n = Math.max(0, Math.min(50, (actual[id] ?? 0) + delta));
    if (n === 0) delete actual[id];
    else actual[id] = n;
    this.aplicar(actual);
  }

  // ----- Check-in semanal (lo evalua el motor; "Aplicar" se pide desde aqui) -----
  readonly checkin = signal<CheckinResponse | null>(this.leerJson('checkin', null));
  readonly cargandoCheckin = signal(false);

  cargarCheckin(): void {
    this.cargandoCheckin.set(true);
    this.api.getCheckin().subscribe({
      next: (r) => {
        this.cargandoCheckin.set(false);
        this.checkin.set(r);
        this.guardarJson('checkin', r);
      },
      error: () => this.cargandoCheckin.set(false)
    });
  }

  /** Pide el ajuste sugerido (null: lo cancela). Devuelve un error para mostrar, o ''. */
  ajustarKcal(delta: number | null): Promise<string> {
    return new Promise((listo) => {
      this.api.aplicarAjuste(delta === null ? { cancelar: true } : { kcal_delta: delta }).subscribe({
        next: () => {
          this.cargarCheckin();
          listo('');
        },
        error: (e: { status?: number }) =>
          listo(e?.status === 409 ? 'La sugerencia cambió: vuelve a abrir el check-in.' : 'Sin conexión: inténtalo de nuevo.')
      });
    });
  }

  /** kcal y proteina promedio de los ultimos 7 dias con algo anotado en la app. */
  readonly semana7 = computed(() => {
    const dias = Array.from({ length: 7 }, (_, i) => {
      const f = new Date();
      f.setDate(f.getDate() - i);
      return desglosar(this.porcionesDe(fechaLocal(f))).total;
    }).filter((t) => t.kcal > 0 || t.prot > 0);
    const prom = (k: 'kcal' | 'prot') => (dias.length ? dias.reduce((s, t) => s + t[k], 0) / dias.length : null);
    return { dias: dias.length, kcal: prom('kcal'), prot: prom('prot') };
  });

  /** Lo anotado en una fecha: hoy, lo del telefono; otro dia reciente, lo del servidor. */
  porcionesDe(fecha: string): Record<string, number> {
    if (fecha === fechaLocal(new Date())) return this.porciones();
    return this.diasServidor().find((d) => String(d.fecha).slice(0, 10) === fecha)?.porciones ?? {};
  }

  /** Una porcion en una comida del dia ("de_huevo"). */
  cantidadEn(tiempo: Tiempo, id: string): number {
    return this.porciones()[tiempo.pre + '_' + id] ?? 0;
  }

  sumarEn(tiempo: Tiempo, id: string, delta: number): void {
    if (!POR_ID.has(id)) return;
    const clave = tiempo.pre + '_' + id;
    const actual = this.deHoy();
    const n = Math.max(0, Math.min(50, (actual[clave] ?? 0) + delta));
    if (n === 0) delete actual[clave];
    else actual[clave] = n;
    this.aplicar(actual);
  }

  /** Quita algo anotado (una porcion o una comida del menu) de un solo toque. */
  quitarAnotado(clave: string): void {
    if (esDelMenu(clave)) {
      if (this.porciones()[clave]) this.alternarMenu(clave.slice(5), 0);
      return;
    }
    const actual = this.deHoy();
    delete actual[clave];
    this.aplicar(actual);
  }

  /** "Lo comi" en una comida del menu de hoy: suma su proteina (y sus kcal y macros,
   *  si vienen); otra vez la quita. */
  alternarMenu(tiempo: string, gramos: number, macros?: { kcal?: number; carb?: number; grasa?: number }): void {
    const t = tiempo.replace(/[^a-z]/g, '').slice(0, 19);
    const id = 'menu_' + t;
    const actual = this.deHoy();
    if (actual[id]) {
      for (const k of [id, 'mk_' + t, 'mc_' + t, 'mg_' + t]) delete actual[k];
    } else {
      actual[id] = Math.max(1, Math.min(300, Math.round(gramos)));
      if (macros?.kcal) actual['mk_' + t] = Math.min(3000, Math.round(macros.kcal));
      if (macros?.carb) actual['mc_' + t] = Math.min(300, Math.round(macros.carb));
      if (macros?.grasa) actual['mg_' + t] = Math.min(300, Math.round(macros.grasa));
    }
    this.aplicar(actual);
  }

  comioMenu(tiempo: string): boolean {
    return !!this.porciones()['menu_' + tiempo.replace(/[^a-z]/g, '').slice(0, 19)];
  }

  /** Copia de las porciones de HOY (si paso la medianoche con la app abierta, empieza en cero). */
  private deHoy(): Record<string, number> {
    const hoy = fechaLocal(new Date());
    if (hoy !== this.fecha) {
      this.fecha = hoy;
      this.porciones.set({});
    }
    return { ...this.porciones() };
  }

  private aplicar(actual: Record<string, number>): void {
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
    const pesos = await almacen.leer<PesosPendientes>('peso-pendiente');
    if (pesos && Object.keys(pesos).length) this.enviarPesos(pesos);
    if (Object.keys(this.noGustaPend).length) this.enviarNoMeGusta();
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

  private leerJson<T>(clave: string, defecto: T): T {
    try {
      const v = localStorage.getItem(clave);
      return v ? (JSON.parse(v) as T) : defecto;
    } catch {
      return defecto;
    }
  }

  private guardarJson(clave: string, valor: unknown): void {
    try {
      localStorage.setItem(clave, JSON.stringify(valor));
    } catch {
      /* sin espacio: queda en memoria */
    }
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

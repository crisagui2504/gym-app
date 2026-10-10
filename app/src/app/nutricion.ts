import { Injectable, computed, inject, signal } from '@angular/core';
import * as almacen from './almacen';
import { fechaLocal } from './entreno-data';
import { MenuComida, MenuDia, MenuSemana, Pesaje, RutinaApiService } from './rutina-api.service';
import { FilaLista, claveEleccion, cocina, comidasDelDia, listaSuper, textoLista } from './menu-semana';

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
  kcal?: number;      // solo los platillos de "Comí fuera" (aproximado)
  fuera?: boolean;    // platillo de la calle / fonda
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
  { id: 'otro', nombre: 'Otro', porcion: 'algo más', g: 5 },
  // ── Comí fuera: platillos comunes de calle y fonda (APROXIMADOS: USDA y recetas típicas) ──
  { id: 'f_pastor', nombre: 'Tacos al pastor', porcion: '3 tacos', g: 24, kcal: 560, fuera: true },
  { id: 'f_asada', nombre: 'Tacos de asada', porcion: '3 tacos', g: 30, kcal: 540, fuera: true },
  { id: 'f_canasta', nombre: 'Tacos de canasta', porcion: '4 tacos', g: 14, kcal: 620, fuera: true },
  { id: 'f_quesadilla', nombre: 'Quesadillas de comal', porcion: '2 con queso', g: 22, kcal: 600, fuera: true },
  { id: 'f_torta', nombre: 'Torta de milanesa o pierna', porcion: '1 torta', g: 32, kcal: 750, fuera: true },
  { id: 'f_corrida', nombre: 'Comida corrida', porcion: 'sopa, arroz, guisado', g: 35, kcal: 900, fuera: true },
  { id: 'f_pozole', nombre: 'Pozole', porcion: '1 plato grande', g: 30, kcal: 550, fuera: true },
  { id: 'f_enchiladas', nombre: 'Enchiladas de pollo', porcion: '3 piezas', g: 28, kcal: 650, fuera: true },
  { id: 'f_chilaquiles', nombre: 'Chilaquiles con pollo', porcion: '1 plato', g: 25, kcal: 700, fuera: true },
  { id: 'f_tamal', nombre: 'Tamal', porcion: '1 pieza', g: 8, kcal: 300, fuera: true },
  { id: 'f_rostizado', nombre: 'Pollo rostizado', porcion: '¼ de pollo', g: 38, kcal: 550, fuera: true },
  { id: 'f_hamburguesa', nombre: 'Hamburguesa sencilla', porcion: '1 pieza', g: 25, kcal: 550, fuera: true },
  { id: 'f_pizza', nombre: 'Pizza', porcion: '2 rebanadas', g: 24, kcal: 560, fuera: true },
  { id: 'f_sushi', nombre: 'Sushi empanizado', porcion: '1 rollo', g: 15, kcal: 650, fuera: true },
  { id: 'f_burrito', nombre: 'Burrito de carne', porcion: '1 pieza', g: 30, kcal: 700, fuera: true },
  { id: 'f_gorditas', nombre: 'Gorditas de chicharrón', porcion: '2 piezas', g: 14, kcal: 650, fuera: true },
  { id: 'f_caldo', nombre: 'Caldo de res o de pollo', porcion: '1 plato', g: 30, kcal: 400, fuera: true },
  { id: 'f_coctel', nombre: 'Cóctel de camarón', porcion: '1 mediano', g: 25, kcal: 250, fuera: true },
  { id: 'f_esquite', nombre: 'Esquite', porcion: '1 vaso mediano', g: 6, kcal: 350, fuera: true },
  { id: 'f_licuado', nombre: 'Licuado de plátano (fonda)', porcion: '1 vaso grande', g: 12, kcal: 350, fuera: true }
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

export function gramosDe(porciones: Record<string, number>): number {
  let total = 0;
  for (const [id, n] of Object.entries(porciones)) {
    total += esDelMenu(id) ? n || 0 : (POR_ID.get(id)?.g ?? 0) * (n || 0);
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
  /** Lo que ya tienes en casa (ids), por semana del menu. */
  readonly tengo = signal<string[]>(this.leerJson('despensa-' + (this.menu()?.semana_inicio ?? ''), []));
  /** Pesajes (servidor + los que aun no suben), del mas viejo al mas nuevo. */
  readonly pesos = signal<Pesaje[]>(this.leerJson('pesos-cache', []));
  readonly pesoPendiente = signal(false);
  readonly pesoHoy = computed(() => this.pesos().find((p) => p.fecha === fechaLocal(new Date())) ?? null);
  readonly tendencia = computed(() => tendenciaPeso(this.pesos()));
  readonly pesajes21 = computed(() => pesajesRecientes(this.pesos()).length);
  /** Dias recientes del servidor (para la racha de creatina). */
  private readonly diasServidor = signal<Array<{ fecha: string; porciones: Record<string, number> }>>([]);

  readonly lista = computed<FilaLista[]>(() => {
    const m = this.menu();
    return m ? listaSuper(m, this.eleccion()) : [];
  });
  readonly cocina = computed(() => {
    const m = this.menu();
    return m ? cocina(m, this.eleccion()) : [];
  });
  readonly costoPendiente = computed(() =>
    this.lista().filter((f) => !this.tengo().includes(f.id)).reduce((s, f) => s + f.costo, 0)
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

  /** Pasa a la siguiente opcion de esa comida (la del menu y sus alternativas, en circulo). */
  cambiarComida(d: MenuDia, c: MenuComida): void {
    const n = 1 + (c.alternativas?.length ?? 0);
    if (n < 2) return;
    const clave = claveEleccion(d, c);
    const nueva = { ...this.eleccion(), [clave]: ((this.eleccion()[clave] ?? 0) + 1) % n };
    this.eleccion.set(nueva);
    this.guardarJson('menu-eleccion', nueva);
    // si ya la habias marcado como comida, se actualiza con la proteina de la nueva
    if (d.fecha === fechaLocal(new Date()) && this.comioMenu(c.tiempo)) {
      this.alternarMenu(c.tiempo, 0);
      this.alternarMenu(c.tiempo, this.comidaDe(d, c).prot);
    }
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

  /** "Lo comi" en una comida del menu de hoy: suma su proteina; otra vez la quita. */
  alternarMenu(tiempo: string, gramos: number): void {
    const id = 'menu_' + tiempo.replace(/[^a-z]/g, '').slice(0, 19);
    const actual = this.deHoy();
    if (actual[id]) delete actual[id];
    else actual[id] = Math.max(1, Math.min(300, Math.round(gramos)));
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

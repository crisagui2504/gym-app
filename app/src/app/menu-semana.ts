import type { FilaListaMenu, MenuComida, MenuDia, MenuSemana, ProductoMenu } from './rutina-api.service';

/**
 * Cuentas del menu en el TELEFONO: si cambias una comida o las tiendas donde
 * compras, la lista del super y la cocina se rehacen con lo que de verdad vas a
 * comer. Mismas reglas que python-engine/menu.py (lista_super, cocina_por_adelantado)
 * y productos_mx.py (elegir: paquetes enteros de la tienda que sale mas a cuenta).
 */
export interface FilaLista {
  id: string;
  nombre: string;
  g: number;
  compra: string;
  costo: number;
  tienda: string;          // 'otra' = sin producto real (tu precio, o ninguna de tus tiendas lo tiene)
  producto: string;
  sobra: string;
  queda: number;           // $ de lo que sobra y rinde para otras semanas (despensa)
  otras: Array<{ tienda: string; producto: string; costo: number }>;
  sinPrecio: string[];
}

export interface TandaCocina {
  cuando: string;
  para: string;
  tareas: Array<{ id: string; texto: string }>;
}

export const TIENDAS: Record<string, string> = {
  mercado: 'Mercado o tianguis', tortilleria: 'Tortillería', '3b': 'Tiendas 3B', walmart: 'Walmart',
  chedraui: 'Chedraui', sams: "Sam's Club"
};
export const ORDEN_TIENDAS = Object.keys(TIENDAS);

/** Lo que se cocina en olla grande dos veces por semana (lo cocido dura 3-4 dias en el refri, USDA). */
const PARA_COCINAR: Record<string, string> = {
  frijol: 'en olla (2 h, o 40 min en olla exprés)', lentejas: 'en olla (30-40 min)',
  garbanzo: 'remojo la noche anterior y olla (1½ h)', habas: 'en olla (1 h)'
};
const TANDAS: Array<[string, string, number[]]> = [
  ['Domingo', 'para lunes a miércoles', [1, 2, 3]],
  ['Miércoles en la noche', 'para jueves a domingo', [4, 5, 6, 7]]
];
const ORDEN_GRUPO: Record<string, number> = { origen_animal: 0, leguminosas: 1, cereales: 2, verduras_frutas: 3, grasas: 4 };

type Ficha = NonNullable<MenuSemana['alimentos']>[string];

/** Gramos de sal en medidas de cocina (1 cucharadita rasa ~ 6 g); igual que menu.py. */
export function cucharadita(g: number): string {
  const tabla: Array<[number, string]> = [[0.5, 'una pizca'], [1.25, '≈ ⅛ de cucharadita'], [1.75, '≈ ¼ de cucharadita'],
    [2.5, '≈ ⅓ de cucharadita'], [4, '≈ ½ cucharadita'], [5.25, '≈ ¾ de cucharadita']];
  for (const [limite, txt] of tabla) if (g < limite) return txt;
  return '≈ 1 cucharadita';
}

/** La comida que elegiste (0 = la del menu, 1.. = sus alternativas). */
export function elegida(c: MenuComida, idx: number): MenuComida {
  const alts = c.alternativas ?? [];
  return idx > 0 && idx <= alts.length ? alts[idx - 1] : c;
}

/** Las sobras se cambian junto con el dia en que se cocinaron (misma clave). */
export function claveEleccion(d: MenuDia, c: MenuComida): string {
  return `${c.sobras?.de ?? d.fecha}|${c.tiempo}`;
}

export function comidasDelDia(d: MenuDia, eleccion: Record<string, number>): MenuComida[] {
  return d.comidas.map((c) => elegida(c, eleccion[claveEleccion(d, c)] ?? 0));
}

function fraccion(n: number): string {
  const entero = Math.floor(n);
  const medio = n - entero >= 0.5;
  if (entero === 0) return '½';
  return medio ? `${entero}½` : `${entero}`;
}

/** '3 huevos', '½ jitomate', '60 g de frijol en seco (≈ 1 taza cocida)' (como alimentos_mx.cantidad_legible). */
function cantidadLegible(a: Ficha | undefined, g: number, id: string): string {
  const nombre = (a?.nombre ?? id).toLowerCase();
  const gu = a?.g_unidad ?? 1;
  if (a && ['pieza', 'lata', 'scoop', 'taza'].includes(a.unidad ?? '') && gu > 1) {
    const n = Math.round((g / gu) * 2) / 2;
    if (n === 0) return `${Math.round(g)} g de ${nombre}`;
    if (a.unidad === 'pieza' && a.piezas?.[0]) return `${fraccion(n)} ${n <= 1 ? a.piezas[0] : a.piezas[1]}`;
    const plural: Record<string, string> = { pieza: 'piezas', lata: 'latas', scoop: 'scoops', taza: 'tazas' };
    return `${fraccion(n)} ${n <= 1 ? a.unidad : plural[a.unidad!]} de ${nombre}`;
  }
  if (a?.unidad === 'ml') return `${Math.round(g)} ml de ${nombre}`;
  if (a?.seco_por_taza) {
    const tazas = Math.round((g / a.seco_por_taza) * 2) / 2;
    const extra = tazas ? ` (≈ ${fraccion(tazas)} taza${tazas > 1 ? 's' : ''} cocida${tazas > 1 ? 's' : ''})` : '';
    return `${Math.round(g)} g de ${nombre} en seco${extra}`;
  }
  return `${Math.round(g)} g de ${nombre}`;
}

function compraLegible(m: MenuSemana, id: string, g: number): string {
  const a = m.alimentos?.[id];
  if (!a) return `${Math.round(g)} g`;
  if (a.compra === 'pieza' || a.compra === 'lata') {
    const n = Math.ceil(g / a.g_compra - 0.05);
    if (a.compra === 'pieza' && a.piezas?.[0]) return `${n} ${n === 1 ? a.piezas[0] : a.piezas[1]}`;
    return `${n} ${a.compra}${n !== 1 ? 's' : ''}`;
  }
  if (a.compra === 'L') return `${(g / 1000).toFixed(1).replace('.0', '')} L`;
  const kg = g / 1000;
  return kg < 1 ? `${kg.toFixed(2)} kg` : `${kg.toFixed(1)} kg`;
}

/** 750 g · 1.25 kg · 2 kg */
function peso(g: number): string {
  if (g < 1000) return `${Math.round(g)} g`;
  return `${(g / 1000).toFixed(2).replace(/0+$/, '').replace(/\.$/, '')} kg`;
}

interface Opcion {
  p: ProductoMenu;
  n: number;
  gCompra: number;
  pagas: number;
  sobra: number;
  merma: number;
  queda: number;
  efectivo: number;
}

function precioKg(p: ProductoMenu): number {
  return (p.p ?? 0) / (p.g / 1000) / p.r;
}

/** Cuanto comprar de un producto: paquetes enteros (o kilos en pasos), lo que pagas y lo que sobra. */
function comprar(p: ProductoMenu, gComer: number, gSemana: number, dura: number): Opcion {
  const gBruto = gComer / p.r;
  let n = 0;
  let gCompra: number;
  let pagas: number;
  if (p.gr) {
    gCompra = Math.max(p.paso, Math.ceil(gBruto / p.paso - 0.02) * p.paso);
    pagas = ((p.p ?? 0) * gCompra) / 1000;
  } else {
    n = Math.max(1, Math.ceil(gBruto / p.g - 0.02));
    gCompra = n * p.g;
    pagas = n * (p.p ?? 0);
  }
  const sobra = Math.max(0, gCompra * p.r - gComer);
  const usable = Math.min(sobra, gSemana * Math.max(0, dura - 1));    // lo que alcanzas a comer antes de que se eche a perder
  const queda = (usable / 1000) * precioKg(p);
  return { p, n, gCompra, pagas, sobra, merma: sobra - usable, queda, efectivo: pagas - queda + 0.02 * pagas };
}

/** Opciones de compra de la que mas conviene a la que menos (solo productos con precio de tus tiendas). */
function opciones(a: Ficha, gComer: number, tiendas: string[] | null): Opcion[] {
  return (a.productos ?? [])
    .filter((p) => p.p && (!tiendas || tiendas.includes(p.t)))
    .map((p) => comprar(p, gComer, gComer, a.dura ?? 1))
    .sort((x, y) => x.efectivo - y.efectivo || x.pagas - y.pagas);
}

function textoCompra(a: Ficha, o: Opcion, gComer: number): string {
  if (o.p.gr) {
    let txt = peso(o.gCompra);
    const gu = a.g_unidad ?? 1;
    if (a.piezas?.[0] && gu > 1) {
      const n = Math.max(1, Math.round(gComer / gu));
      txt += ` (≈ ${n} ${n === 1 ? a.piezas[0] : a.piezas[1]})`;
    }
    return txt;
  }
  if (o.p.n.includes('(pieza')) return `${o.n} pieza${o.n !== 1 ? 's' : ''}`;
  return o.n > 1 ? `${o.n} × ${o.p.n}` : o.p.n;
}

function textoSobra(a: Ficha, o: Opcion, gComer: number, id: string): string {
  if (o.sobra < Math.max(40, 0.12 * gComer)) return '';
  const cuanto = ['pieza', 'lata'].includes(a.unidad ?? '') && (a.g_unidad ?? 1) > 1 ? cantidadLegible(a, o.sobra, id) : peso(o.sobra);
  if ((a.dura ?? 1) >= 4 || o.merma <= o.sobra * 0.25) return `te sobran ≈ ${cuanto} para otras semanas`;
  return `sobran ≈ ${cuanto}: úsalo pronto o congélalo`;
}

function fila(m: MenuSemana, id: string, g: number, tiendas: string[] | null): FilaLista {
  const a = m.alimentos?.[id];
  const base = { id, nombre: a?.nombre ?? id, g };
  const ops = a && !a.propio ? opciones(a, g, tiendas) : [];
  if (!a || !ops.length) {      // tu precio, o ninguna de tus tiendas lo tiene: por kilo
    return { ...base, compra: compraLegible(m, id, g), costo: ((a?.precio_kg ?? 0) * g) / 1000, tienda: 'otra',
             producto: '', sobra: '', queda: 0, otras: [], sinPrecio: [] };
  }
  const o = ops[0];
  const vistas = new Set([o.p.t]);
  const otras: FilaLista['otras'] = [];
  for (const x of ops.slice(1)) {
    if (vistas.has(x.p.t)) continue;
    vistas.add(x.p.t);
    otras.push({ tienda: x.p.t, producto: x.p.n, costo: x.pagas });
  }
  const sinPrecio = (a.productos ?? []).filter((p) => !p.p && (!tiendas || tiendas.includes(p.t))).map((p) => p.n);
  return { ...base, compra: textoCompra(a, o, g), costo: o.pagas, tienda: o.p.t, producto: o.p.n,
           sobra: textoSobra(a, o, g, id), queda: o.queda, otras: otras.slice(0, 2), sinPrecio };
}

/** Lista del super de lo que vas a comer de verdad (con tus cambios), en productos reales
 *  de las tiendas donde compras (null = todas), ordenada por tienda. */
export function listaSuper(m: MenuSemana, eleccion: Record<string, number>, tiendas: string[] | null = null): FilaLista[] {
  if (!m.alimentos) {
    return m.lista.map((f: FilaListaMenu) => ({
      id: f.id, nombre: f.nombre, g: f.g ?? 0, compra: f.compra, costo: f.costo, tienda: f.tienda ?? 'otra',
      producto: f.producto ?? '', sobra: f.sobra ?? '', queda: f.queda ?? 0, otras: f.otras ?? [], sinPrecio: f.sin_precio ?? []
    }));
  }
  const total: Record<string, number> = {};
  const f = m.hogar?.factor ?? 1;          // para todos en casa (un nino ~60 %)
  for (const d of m.dias) {
    for (const c of comidasDelDia(d, eleccion)) {
      for (const i of c.ingredientes) total[i.id] = (total[i.id] ?? 0) + i.g * f;
    }
  }
  const ordenT = (t: string) => { const i = ORDEN_TIENDAS.indexOf(t); return i < 0 ? 9 : i; };
  const grupo = (id: string) => ORDEN_GRUPO[m.alimentos![id]?.grupo ?? ''] ?? 9;
  return Object.entries(total)
    .map(([id, g]) => fila(m, id, g, tiendas))
    .sort((x, y) => ordenT(x.tienda) - ordenT(y.tienda) || grupo(x.id) - grupo(y.id) || y.costo - x.costo);
}

/** Que pedir, en una linea: '2 × Frijol negro Chedraui 900 g' o 'Plátano: 1.25 kg (≈ 7 plátanos)'. */
export function queComprar(f: FilaLista): string {
  return f.producto && f.compra.includes(f.producto) ? f.compra : `${f.nombre}: ${f.compra}`;
}

/** Que cocinar y cuando: la comida de cada dia de cocina (para hoy y manana) y las ollas de frijol. */
export function cocina(m: MenuSemana, eleccion: Record<string, number>): TandaCocina[] {
  if (!m.alimentos) return m.cocina ?? [];
  const salida: TandaCocina[] = [];
  const f = m.hogar?.factor ?? 1;
  for (const d of m.dias) {
    const c0 = d.comidas.find((x) => x.tiempo === 'comida');
    if (!c0 || (c0.rinde ?? 1) < 2) continue;
    const c = elegida(c0, eleccion[claveEleccion(d, c0)] ?? 0);
    const otro = m.dias.find((dd) => dd.comidas.some((x) => x.tiempo === 'comida' && x.sobras?.de === d.fecha));
    const veces = otro ? 2 : 1;
    const texto = `${c.nombre} × ${veces} porciones: ` +
      c.ingredientes.map((i) => cantidadLegible(m.alimentos![i.id], i.g * veces * f, i.id)).join(', ');
    salida.push({ cuando: d.nombre, para: otro ? `comida de hoy y de mañana (${otro.nombre.toLowerCase()})` : 'comida de hoy',
                  tareas: [{ id: c.receta, texto }] });
  }
  for (const [cuando, para, nums] of TANDAS) {
    const total: Record<string, number> = {};
    for (const d of m.dias.filter((x) => nums.includes(x.dia))) {
      for (const c of comidasDelDia(d, eleccion)) {
        for (const i of c.ingredientes) if (i.id in PARA_COCINAR) total[i.id] = (total[i.id] ?? 0) + i.g * f;
      }
    }
    const tareas = Object.keys(PARA_COCINAR)
      .filter((id) => total[id])
      .map((id) => {
        const texto = `${cantidadLegible(m.alimentos![id], total[id], id)} — ${PARA_COCINAR[id]}`;
        return { id, texto: texto[0].toUpperCase() + texto.slice(1) };
      });
    if (tareas.length) salida.push({ cuando, para, tareas });
  }
  return salida;
}

/** Texto para compartir la lista (WhatsApp, notas…), por tienda y sin lo que ya tienes. */
export function textoLista(m: MenuSemana, filas: FilaLista[], tengo: string[]): string {
  const pendientes = filas.filter((f) => !tengo.includes(f.id));
  const costo = pendientes.reduce((s, f) => s + f.costo, 0);
  const h = m.hogar && m.hogar.factor !== 1
    ? ` · para ${m.hogar.adultos} adulto${m.hogar.adultos !== 1 ? 's' : ''}${m.hogar.ninos ? ` y ${m.hogar.ninos} niño${m.hogar.ninos !== 1 ? 's' : ''}` : ''}`
    : '';
  const lineas = [`🛒 Lista del súper (semana del ${m.semana_inicio})${h} · ≈ $${Math.round(costo)}`];
  let tienda = '';
  for (const f of pendientes) {
    if (f.tienda !== tienda) {
      tienda = f.tienda;
      lineas.push('', `📍 ${TIENDAS[tienda] ?? 'Otros'}`);
    }
    lineas.push(`• ${queComprar(f)}${f.costo ? ` — $${Math.round(f.costo)}` : ''}`);
  }
  return lineas.join('\n');
}

import type { MenuComida, MenuDia, MenuSemana } from './rutina-api.service';

/**
 * Cuentas del menu en el TELEFONO: si cambias una comida, la lista del super y
 * la cocina por adelantado se rehacen con lo que de verdad vas a comer. Mismas
 * reglas que python-engine/menu.py (lista_super / cocina_por_adelantado).
 */
export interface FilaLista {
  id: string;
  nombre: string;
  g: number;
  compra: string;
  costo: number;
}

export interface TandaCocina {
  cuando: string;
  para: string;
  tareas: Array<{ id: string; texto: string }>;
}

/** Lo que conviene cocinar por adelantado (lo cocido dura 3-4 dias en el refri, USDA). */
const PARA_COCINAR: Record<string, string> = {
  frijol: 'en olla', lentejas: 'en olla', arroz: '', pollo: 'cocer y deshebrar', pechuga: 'cocer y deshebrar'
};
const TANDAS: Array<[string, string, number[]]> = [
  ['Domingo', 'para lunes a miércoles', [1, 2, 3]],
  ['Miércoles en la noche', 'para jueves a domingo', [4, 5, 6, 7]]
];
const ORDEN_GRUPO: Record<string, number> = { leguminosas: 0, origen_animal: 1, cereales: 2, verduras_frutas: 3, grasas: 4 };

/** La comida que elegiste (0 = la del menu, 1.. = sus alternativas). */
export function elegida(c: MenuComida, idx: number): MenuComida {
  const alts = c.alternativas ?? [];
  return idx > 0 && idx <= alts.length ? alts[idx - 1] : c;
}

export function claveEleccion(d: MenuDia, c: MenuComida): string {
  return `${d.fecha}|${c.tiempo}`;
}

export function comidasDelDia(d: MenuDia, eleccion: Record<string, number>): MenuComida[] {
  return d.comidas.map((c) => elegida(c, eleccion[claveEleccion(d, c)] ?? 0));
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

/** Lista del super de lo que vas a comer de verdad (con tus cambios). */
export function listaSuper(m: MenuSemana, eleccion: Record<string, number>): FilaLista[] {
  if (!m.alimentos) {
    return m.lista.map((f) => ({ id: f.id, nombre: f.nombre, g: 0, compra: f.compra, costo: f.costo }));
  }
  const total: Record<string, number> = {};
  const f = m.hogar?.factor ?? 1;          // para todos en casa (un nino ~60 %)
  for (const d of m.dias) {
    for (const c of comidasDelDia(d, eleccion)) {
      for (const i of c.ingredientes) total[i.id] = (total[i.id] ?? 0) + i.g * f;
    }
  }
  return Object.entries(total)
    .map(([id, g]) => {
      const a = m.alimentos![id];
      return { id, nombre: a?.nombre ?? id, g, compra: compraLegible(m, id, g), costo: ((a?.precio_kg ?? 0) * g) / 1000 };
    })
    .sort((x, y) =>
      (ORDEN_GRUPO[m.alimentos![x.id]?.grupo ?? ''] ?? 9) - (ORDEN_GRUPO[m.alimentos![y.id]?.grupo ?? ''] ?? 9) || y.costo - x.costo
    );
}

function fraccion(n: number): string {
  const entero = Math.floor(n);
  const medio = n - entero >= 0.5;
  if (entero === 0) return '½';
  return medio ? `${entero}½` : `${entero}`;
}

/** Que cocinar el domingo y el miercoles para lo que vas a comer. */
export function cocina(m: MenuSemana, eleccion: Record<string, number>): TandaCocina[] {
  if (!m.alimentos) return m.cocina ?? [];
  const salida: TandaCocina[] = [];
  for (const [cuando, para, nums] of TANDAS) {
    const total: Record<string, number> = {};
    const f = m.hogar?.factor ?? 1;
    for (const d of m.dias.filter((x) => nums.includes(x.dia))) {
      for (const c of comidasDelDia(d, eleccion)) {
        for (const i of c.ingredientes) if (i.id in PARA_COCINAR) total[i.id] = (total[i.id] ?? 0) + i.g * f;
      }
    }
    const tareas = Object.keys(PARA_COCINAR)
      .filter((id) => total[id])
      .map((id) => {
        const a = m.alimentos![id];
        const g = Math.round(total[id]);
        let texto = `${g} g de ${(a?.nombre ?? id).toLowerCase()}`;
        if (a?.seco_por_taza) {
          const tazas = Math.round((g / a.seco_por_taza) * 2) / 2;
          texto += ` en seco${tazas ? ` (≈ ${fraccion(tazas)} taza${tazas > 1 ? 's' : ''} cocida${tazas > 1 ? 's' : ''})` : ''}`;
        }
        if (PARA_COCINAR[id]) texto += ` — ${PARA_COCINAR[id]}`;
        return { id, texto: texto[0].toUpperCase() + texto.slice(1) };
      });
    if (tareas.length) salida.push({ cuando, para, tareas });
  }
  return salida;
}

/** Texto para compartir la lista (WhatsApp, notas…), sin lo que ya tienes. */
export function textoLista(m: MenuSemana, filas: FilaLista[], tengo: string[]): string {
  const pendientes = filas.filter((f) => !tengo.includes(f.id));
  const costo = pendientes.reduce((s, f) => s + f.costo, 0);
  const h = m.hogar && m.hogar.factor !== 1
    ? ` · para ${m.hogar.adultos} adulto${m.hogar.adultos !== 1 ? 's' : ''}${m.hogar.ninos ? ` y ${m.hogar.ninos} niño${m.hogar.ninos !== 1 ? 's' : ''}` : ''}`
    : '';
  return [
    `🛒 Lista del súper (semana del ${m.semana_inicio})${h} · ≈ $${Math.round(costo)}`,
    ...pendientes.map((f) => `• ${f.nombre}: ${f.compra}`)
  ].join('\n');
}

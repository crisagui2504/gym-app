import { GRANDES, MUSCLE_LABEL, MuscleId, musculosDe } from './entreno-data';

// ── Acomodar la semana para que cada musculo se recupere ─────────────────────
// Cuando mueves un dia, lo demas se reacomoda solo: se prueban TODOS los ordenes
// posibles de los dias de gym que siguen (como mucho 5! = 120) y se queda el que
// menos vuelve a cargar un musculo antes de recuperarse: ~72 h los grandes
// (pecho, dorsales, cuadriceps, isquios, gluteos, lumbar) y ~48 h los demas, la
// misma regla del mapa de recuperacion (fatigaMuscular). El basquet cuenta como
// carga de pierna (gemelos, cuadriceps, gluteos).

/** Series por musculo de una sesion: el principal cuenta 1 y los secundarios 0.5. */
export type Carga = Partial<Record<MuscleId, number>>;

/** Carga de un dia de basquet, igual que en fatigaMuscular. */
export const CARGA_DEPORTE: Carga = { gemelos: 4, cuadriceps: 3, gluteos: 2 };

/** Carga de una sesion a partir de su rutina (filas con ejercicio y series). */
export function cargaDeSesion(filas: Array<{ ejercicio: string; series_objetivo?: string | number | null }>,
                              deporte = false): Carga {
  if (deporte) return { ...CARGA_DEPORTE };
  const c: Carga = {};
  for (const f of filas) {
    const n = Number(f.series_objetivo) || 3;
    musculosDe(f.ejercicio).forEach((m, i) => {
      c[m] = (c[m] ?? 0) + n * (i === 0 ? 1 : 0.5);
    });
  }
  return c;
}

/** Cuanto se vuelve a cargar un musculo que aun no se recupera (`dias` dias despues). */
export function choque(antes: Carga, despues: Carga, dias: number): number {
  let s = 0;
  const horas = dias * 24;
  for (const [m, a] of Object.entries(antes) as [MuscleId, number][]) {
    const T = GRANDES.includes(m) ? 72 : 48;
    const b = despues[m];
    if (!b || horas >= T) continue;
    s += Math.min(a, b) * (1 - horas / T);
  }
  return s;
}

/** Repetir musculo al dia siguiente (< 48 h) pesa el doble que entre 48 y 72 h. */
const peso = (dias: number) => (dias === 1 ? 2 : 1);

/** Choque total de una semana (`orden[i]` = carga del dia i+1). El lunes que viene
 *  cuenta a la mitad: ese plan aun puede cambiar. */
export function costoSemana(orden: Carga[], siguienteLunes?: Carga): number {
  let s = 0;
  for (let i = 0; i < orden.length; i++) {
    for (let j = i + 1; j <= i + 2 && j < orden.length; j++) s += peso(j - i) * choque(orden[i], orden[j], j - i);
  }
  if (siguienteLunes) {
    for (let i = Math.max(0, orden.length - 2); i < orden.length; i++) {
      s += 0.5 * peso(orden.length - i) * choque(orden[i], siguienteLunes, orden.length - i);
    }
  }
  return s;
}

function permutaciones<T>(xs: T[]): T[][] {
  if (xs.length <= 1) return [xs.slice()];
  const out: T[][] = [];
  xs.forEach((x, i) => {
    for (const resto of permutaciones([...xs.slice(0, i), ...xs.slice(i + 1)])) out.push([x, ...resto]);
  });
  return out;
}

/** Lo que "cuesta" mover una sesion de su dia: solo se mueve si la recuperacion
 *  mejora de verdad (p. ej. torso dos dias seguidos), no por detalles. */
const MOVER = 2.0;

export interface Movimiento {
  sesion: number;
  de: number;      // dia calendario (1 = lunes)
  a: number;
}

/**
 * Reacomoda los dias libres. `orden[cal - 1]` = sesion de ese dia; `cargas[sesion - 1]`
 * = su carga; `fijos` = dias que no se tocan (pasados, hoy, los que moviste tu y los
 * de deporte). Cada sesion que cambia de dia cuesta un poco: si da casi igual, se
 * queda donde estaba.
 */
export function acomodar(orden: number[], cargas: Carga[], fijos: Set<number>,
                         siguienteLunes?: Carga): { orden: number[]; movidos: Movimiento[] } {
  const libres = orden.map((_, i) => i + 1).filter((cal) => !fijos.has(cal));
  if (libres.length < 2) return { orden: orden.slice(), movidos: [] };
  const sesionesLibres = libres.map((cal) => orden[cal - 1]);
  let mejor = orden.slice();
  let mejorCosto = Infinity;
  for (const p of permutaciones(sesionesLibres)) {
    const cand = orden.slice();
    libres.forEach((cal, k) => (cand[cal - 1] = p[k]));
    const cambios = libres.filter((cal) => cand[cal - 1] !== orden[cal - 1]).length;
    const costo = costoSemana(cand.map((s) => cargas[s - 1] ?? {}), siguienteLunes) + MOVER * cambios;
    if (costo < mejorCosto - 1e-9) {
      mejor = cand;
      mejorCosto = costo;
    }
  }
  const movidos: Movimiento[] = [];
  for (const cal of libres) {
    const s = mejor[cal - 1];
    if (s !== orden[cal - 1]) movidos.push({ sesion: s, de: orden.indexOf(s) + 1, a: cal });
  }
  return { orden: mejor, movidos };
}

/** Musculos que ese dia se vuelven a cargar con menos de 48 h de descanso (el dia
 *  anterior los trabajo), de mas a menos. Entre 48 y 72 h no se avisa: con 3 dias de
 *  torso en una semana a veces no se puede mas, y el acomodo ya lo evita si puede. */
export function sinRecuperar(orden: number[], cargas: Carga[], cal: number, umbral = 1.5): MuscleId[] {
  if (cal < 2) return [];
  const hoy = cargas[orden[cal - 1] - 1] ?? {};
  const antes = cargas[orden[cal - 2] - 1] ?? {};
  const porMusculo: Partial<Record<MuscleId, number>> = {};
  for (const m of Object.keys(antes) as MuscleId[]) {
    const v = choque({ [m]: antes[m] } as Carga, hoy, 1);
    if (v) porMusculo[m] = v;
  }
  return (Object.entries(porMusculo) as [MuscleId, number][])
    .filter(([, v]) => v >= umbral)
    .sort((a, b) => b[1] - a[1])
    .map(([m]) => m);
}

/** "Pecho y Dorsales" (los 2 que mas pesan). */
export function nombresMusculos(ms: MuscleId[]): string {
  const n = ms.slice(0, 2).map((m) => MUSCLE_LABEL[m]);
  return n.length === 2 ? `${n[0]} y ${n[1]}` : (n[0] ?? '');
}

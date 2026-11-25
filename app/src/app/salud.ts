// Lee la exportacion de Apple Salud ("Exportar todos los datos de salud": un .zip
// con exportar.xml / export.xml) EN EL TELEFONO y la resume por dia. Al servidor
// solo suben los totales (sueno, pulso nocturno, pasos, peso y entrenos); el
// archivo, con el pulso minuto a minuto, nunca sale del telefono.
//
// Asi entra el Amazfit (Zepp -> Salud) al motor: iPhone no deja que un servidor
// lea Salud solo, por eso la exportacion es manual (cada 1-2 semanas).
//
// El XML pesa cientos de MB: se lee en streaming (DecompressionStream + linea a
// linea) sin cargarlo entero en memoria. Cada registro viene en su propia linea:
//   <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Zepp" ... startDate="2026-11-16 03:12:00 -0600" ... value="54"/>
// Las horas se usan tal cual (hora local de cuando se midio).
// Pruebas: app/tests/salud.test.ts

export interface DiaReloj {
  /** YYYY-MM-DD. La noche cuenta para el dia en que despiertas. */
  fecha: string;
  sueno_min: number | null;
  /** Percentil 10 del pulso mientras dormias (lpm): tu "pulso en reposo" de esa noche. */
  pulso_noche: number | null;
  /** RestingHeartRate de Salud, si el reloj lo manda (lpm). */
  pulso_reposo: number | null;
  /** HRV (SDNN, ms), promedio del dia. */
  hrv: number | null;
  pasos: number | null;
  /** kg */
  peso: number | null;
}

export interface EntrenoReloj {
  /** 'YYYY-MM-DD HH:MM:SS', hora local */
  inicio: string;
  fin: string;
  /** HKWorkoutActivityType sin el prefijo: TraditionalStrengthTraining, Elliptical, Basketball... */
  tipo: string;
  minutos: number;
  pulso_prom: number | null;
}

export interface ResumenReloj {
  dias: DiaReloj[];
  entrenos: EntrenoReloj[];
  desde: string;
  /** Registros de los tipos que interesan dentro del rango (para saber si trajo algo). */
  registros: number;
}

const H = 3600e3;
/** Una noche se asigna al dia de (fin del sueno + 6 h): despertar a las 7:00 -> ese dia;
 *  un tramo que acaba a las 23:30 -> el dia siguiente (es la misma noche). */
const CORTE_NOCHE = 6 * H;

/** Hora local de Salud ('2026-11-16 03:12:00 -0600') a ms "de pared" (sin zona). */
function pared(s: string): number {
  return Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10), +s.slice(11, 13), +s.slice(14, 16), +s.slice(17, 19));
}

function fechaDePared(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

function attr(l: string, nombre: string): string | null {
  const k = ' ' + nombre + '="';
  const i = l.indexOf(k);
  if (i < 0) return null;
  const j = l.indexOf('"', i + k.length);
  return j < 0 ? null : l.slice(i + k.length, j);
}

function percentil(v: number[], p: number): number {
  const s = [...v].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.max(0, Math.floor((s.length - 1) * p)))];
}

const TIPOS: Record<string, 'pulso' | 'sueno' | 'pasos' | 'reposo' | 'hrv' | 'peso'> = {
  HKQuantityTypeIdentifierHeartRate: 'pulso',
  HKCategoryTypeIdentifierSleepAnalysis: 'sueno',
  HKQuantityTypeIdentifierStepCount: 'pasos',
  HKQuantityTypeIdentifierRestingHeartRate: 'reposo',
  HKQuantityTypeIdentifierHeartRateVariabilitySDNN: 'hrv',
  HKQuantityTypeIdentifierBodyMass: 'peso',
};

/** Junta los registros linea a linea; resultado() arma el resumen por dia. */
export class ResumidorSalud {
  registros = 0;
  private readonly sueno = new Map<string, Array<[number, number]>>(); // fuente -> tramos dormido
  private readonly pulsoT: number[] = [];
  private readonly pulsoV: number[] = [];
  private readonly pasos = new Map<string, Map<string, number>>();     // fecha -> fuente -> suma
  private readonly reposo = new Map<string, number>();
  private readonly hrv = new Map<string, number[]>();
  private readonly peso = new Map<string, [string, number]>();         // fecha -> [hora, kg]
  private readonly entrenos: EntrenoReloj[] = [];
  private enEntreno: EntrenoReloj | null = null;

  constructor(readonly desde: string) {}

  linea(l: string): void {
    if (this.enEntreno) {
      if (l.includes('</Workout>')) {
        this.entrenos.push(this.enEntreno);
        this.enEntreno = null;
      } else if (l.includes('<WorkoutStatistics') && l.includes('"HKQuantityTypeIdentifierHeartRate"')) {
        const prom = Number(attr(l, 'average'));
        if (prom > 0) this.enEntreno.pulso_prom = Math.round(prom);
      }
      return;
    }
    const r = l.indexOf('<Record type="');
    if (r >= 0) {
      const t0 = r + 14;
      const clase = TIPOS[l.slice(t0, l.indexOf('"', t0))];
      if (clase) this.registro(clase, l);
      return;
    }
    if (l.includes('<Workout ')) this.entreno(l);
  }

  private registro(clase: string, l: string): void {
    const ini = attr(l, 'startDate');
    if (!ini || ini.length < 19 || ini.slice(0, 10) < this.desde) return;
    const valor = attr(l, 'value') ?? '';
    const fecha = ini.slice(0, 10);
    this.registros++;
    switch (clase) {
      case 'pulso': {
        const h = +ini.slice(11, 13);
        if (h >= 13 && h < 18) return;       // solo sirve el de la noche (y siestas de la manana)
        const v = Number(valor);
        if (v >= 25 && v <= 230) {
          this.pulsoT.push(pared(ini));
          this.pulsoV.push(v);
        }
        return;
      }
      case 'sueno': {
        if (!valor.includes('Asleep')) return;          // InBed y Awake no son dormir
        const fin = attr(l, 'endDate');
        if (!fin) return;
        const fuente = attr(l, 'sourceName') ?? '';
        const a = pared(ini);
        const b = pared(fin);
        if (b > a && b - a < 16 * H) (this.sueno.get(fuente) ?? this.sueno.set(fuente, []).get(fuente)!).push([a, b]);
        return;
      }
      case 'pasos': {
        const v = Number(valor);
        if (!(v > 0)) return;
        const fuente = attr(l, 'sourceName') ?? '';
        const dia = this.pasos.get(fecha) ?? this.pasos.set(fecha, new Map()).get(fecha)!;
        dia.set(fuente, (dia.get(fuente) ?? 0) + v);
        return;
      }
      case 'reposo': {
        const v = Number(valor);
        if (v >= 25 && v <= 150) this.reposo.set(fecha, v);
        return;
      }
      case 'hrv': {
        const v = Number(valor);
        if (v > 0 && v < 400) (this.hrv.get(fecha) ?? this.hrv.set(fecha, []).get(fecha)!).push(v);
        return;
      }
      case 'peso': {
        const u = (attr(l, 'unit') ?? 'kg').toLowerCase();
        const kg = Number(valor) * (u === 'lb' ? 0.45359237 : u === 'g' ? 0.001 : 1);
        const prev = this.peso.get(fecha);
        if (kg >= 30 && kg <= 250 && (!prev || ini >= prev[0])) this.peso.set(fecha, [ini, kg]);
        return;
      }
    }
  }

  private entreno(l: string): void {
    const ini = attr(l, 'startDate');
    const fin = attr(l, 'endDate');
    if (!ini || !fin || ini.slice(0, 10) < this.desde) return;
    const dur = Number(attr(l, 'duration'));
    const u = attr(l, 'durationUnit') ?? 'min';
    let minutos = u === 'min' ? dur : u === 's' ? dur / 60 : u === 'hr' ? dur * 60 : NaN;
    if (!(minutos > 0)) minutos = (pared(fin) - pared(ini)) / 60000;
    const e: EntrenoReloj = {
      inicio: ini.slice(0, 19), fin: fin.slice(0, 19),
      tipo: (attr(l, 'workoutActivityType') ?? '').replace('HKWorkoutActivityType', '') || 'Other',
      minutos: Math.round(minutos * 10) / 10, pulso_prom: null,
    };
    this.registros++;
    if (l.trimEnd().endsWith('/>')) this.entrenos.push(e);
    else this.enEntreno = e;
  }

  resultado(): ResumenReloj {
    // sueno: por fuente se unen los tramos (etapas ligero/profundo/REM) y se
    // reparten por noche; si dos fuentes registran la misma noche (reloj y
    // telefono) gana la que tiene mas minutos: sumarlas lo contaria doble
    type Noche = { min: number; tramos: Array<[number, number]> };
    const noches = new Map<string, Noche>();
    for (const tramos of this.sueno.values()) {
      tramos.sort((a, b) => a[0] - b[0]);
      const unidos: Array<[number, number]> = [];
      for (const [a, b] of tramos) {
        const u = unidos[unidos.length - 1];
        if (u && a <= u[1]) u[1] = Math.max(u[1], b);
        else unidos.push([a, b]);
      }
      const porNoche = new Map<string, Noche>();
      for (const [a, b] of unidos) {
        const k = fechaDePared(b + CORTE_NOCHE);
        const n = porNoche.get(k) ?? { min: 0, tramos: [] };
        n.min += (b - a) / 60000;
        n.tramos.push([a, b]);
        porNoche.set(k, n);
      }
      for (const [k, n] of porNoche) {
        const prev = noches.get(k);
        if (!prev || n.min > prev.min) noches.set(k, n);
      }
    }

    // pulso de cada noche: percentil 10 de lo medido MIENTRAS dormias (solo dentro
    // de los tramos dormido: una siesta no mete el pulso de la manana despierto;
    // el minimo suelto es ruido del sensor)
    const orden = this.pulsoT.map((_, i) => i).sort((a, b) => this.pulsoT[a] - this.pulsoT[b]);
    const t = orden.map((i) => this.pulsoT[i]);
    const v = orden.map((i) => this.pulsoV[i]);
    const desdeT = (x: number) => {
      let lo = 0, hi = t.length;
      while (lo < hi) {
        const m = (lo + hi) >> 1;
        if (t[m] < x) lo = m + 1;
        else hi = m;
      }
      return lo;
    };
    const pulsoNoche = new Map<string, number>();
    for (const [k, n] of noches) {
      const muestras: number[] = [];
      for (const [a, b] of n.tramos) {
        for (let i = desdeT(a); i < t.length && t[i] <= b; i++) muestras.push(v[i]);
      }
      if (muestras.length >= 20) pulsoNoche.set(k, Math.round(percentil(muestras, 0.1)));
    }

    const fechas = new Set<string>([...noches.keys(), ...this.pasos.keys(), ...this.reposo.keys(),
                                    ...this.hrv.keys(), ...this.peso.keys()]);
    const dias: DiaReloj[] = [...fechas].filter((f) => f >= this.desde).sort().map((fecha) => {
      const n = noches.get(fecha);
      const p = this.pasos.get(fecha);
      const h = this.hrv.get(fecha);
      const kg = this.peso.get(fecha);
      return {
        fecha,
        sueno_min: n ? Math.round(n.min) : null,
        pulso_noche: pulsoNoche.get(fecha) ?? null,
        pulso_reposo: this.reposo.has(fecha) ? Math.round(this.reposo.get(fecha)!) : null,
        hrv: h ? Math.round((h.reduce((a, b) => a + b, 0) / h.length) * 10) / 10 : null,
        // varias fuentes (telefono y reloj) cuentan los mismos pasos: la mayor, no la suma
        pasos: p ? Math.round(Math.max(...p.values())) : null,
        peso: kg ? Math.round(kg[1] * 10) / 10 : null,
      };
    });
    const entrenos = [...this.entrenos].sort((a, b) => (a.inicio < b.inicio ? -1 : 1));
    return { dias, entrenos, desde: this.desde, registros: this.registros };
  }
}

interface EntradaZip { nombre: string; metodo: number; comprimido: number; original: number; offset: number }

/** Busca en el directorio central del .zip el XML de la exportacion (no el _cda). */
async function entradaXml(z: Blob): Promise<EntradaZip> {
  const cola = Math.min(z.size, 65557 + 20);
  const fin = new DataView(await z.slice(z.size - cola).arrayBuffer());
  let p = -1;
  for (let i = fin.byteLength - 22; i >= 0; i--) {
    if (fin.getUint32(i, true) === 0x06054b50) {
      p = i;
      break;
    }
  }
  if (p < 0) throw new Error('El archivo no es un .zip válido.');
  let n = fin.getUint16(p + 10, true);
  let tam = fin.getUint32(p + 12, true);
  let off = fin.getUint32(p + 16, true);
  if (n === 0xffff || tam === 0xffffffff || off === 0xffffffff) {
    const loc = p - 20; // zip64: el localizador va justo antes
    if (loc >= 0 && fin.getUint32(loc, true) === 0x07064b50) {
      const pos = Number(fin.getBigUint64(loc + 8, true));
      const r = new DataView(await z.slice(pos, pos + 56).arrayBuffer());
      n = Number(r.getBigUint64(32, true));
      tam = Number(r.getBigUint64(40, true));
      off = Number(r.getBigUint64(48, true));
    }
  }
  const cd = new DataView(await z.slice(off, off + tam).arrayBuffer());
  const dec = new TextDecoder();
  let mejor: EntradaZip | null = null;
  for (let i = 0, k = 0; k < n && i + 46 <= cd.byteLength; k++) {
    if (cd.getUint32(i, true) !== 0x02014b50) break;
    const metodo = cd.getUint16(i + 10, true);
    let comprimido = cd.getUint32(i + 20, true);
    let original = cd.getUint32(i + 24, true);
    const ln = cd.getUint16(i + 28, true);
    const le = cd.getUint16(i + 30, true);
    const lc = cd.getUint16(i + 32, true);
    let offset = cd.getUint32(i + 42, true);
    const nombre = dec.decode(new Uint8Array(cd.buffer, cd.byteOffset + i + 46, ln));
    for (let e = i + 46 + ln; e + 4 <= i + 46 + ln + le;) {
      const id = cd.getUint16(e, true);
      const sz = cd.getUint16(e + 2, true);
      if (id === 0x0001) { // zip64: los campos que no cupieron en 32 bits, en orden
        let q = e + 4;
        if (original === 0xffffffff) { original = Number(cd.getBigUint64(q, true)); q += 8; }
        if (comprimido === 0xffffffff) { comprimido = Number(cd.getBigUint64(q, true)); q += 8; }
        if (offset === 0xffffffff) offset = Number(cd.getBigUint64(q, true));
      }
      e += 4 + sz;
    }
    if (/^(?:[^/]+\/)?[^/]+\.xml$/i.test(nombre) && !/cda/i.test(nombre) && (!mejor || original > mejor.original)) {
      mejor = { nombre, metodo, comprimido, original, offset };
    }
    i += 46 + ln + le + lc;
  }
  if (!mejor) throw new Error('El .zip no trae la exportación de Salud (exportar.xml).');
  if (mejor.metodo !== 0 && mejor.metodo !== 8) throw new Error('El .zip usa una compresión que no se puede leer aquí.');
  return mejor;
}

/** Recorre el XML de la exportacion linea a linea (del .zip o del .xml suelto). */
export async function leerLineas(archivo: Blob, alLinea: (l: string) => void,
                                 progreso?: (fraccion: number) => void): Promise<void> {
  const nombre = (archivo as File).name ?? '';
  let crudo: ReadableStream<Uint8Array>;
  let total: number;
  let metodo = 0;
  if (/\.xml$/i.test(nombre)) {
    crudo = archivo.stream();
    total = archivo.size;
  } else {
    const e = await entradaXml(archivo);
    const local = new DataView(await archivo.slice(e.offset, e.offset + 30).arrayBuffer());
    if (local.getUint32(0, true) !== 0x04034b50) throw new Error('El .zip está dañado.');
    const ini = e.offset + 30 + local.getUint16(26, true) + local.getUint16(28, true);
    crudo = archivo.slice(ini, ini + e.comprimido).stream();
    total = e.comprimido;
    metodo = e.metodo;
  }
  let leidos = 0;
  let ultimo = -1;
  const contador = new TransformStream<Uint8Array, Uint8Array>({
    transform(trozo, ctl) {
      leidos += trozo.byteLength;
      const pct = Math.floor((leidos / Math.max(1, total)) * 100);
      if (pct !== ultimo) {
        ultimo = pct;
        progreso?.(Math.min(1, leidos / Math.max(1, total)));
      }
      ctl.enqueue(trozo);
    },
  });
  let datos = crudo.pipeThrough(contador);
  if (metodo === 8) datos = datos.pipeThrough(new DecompressionStream('deflate-raw') as unknown as TransformStream<Uint8Array, Uint8Array>);
  const lector = datos.pipeThrough(new TextDecoderStream()).getReader();
  let resto = '';
  for (;;) {
    const { value, done } = await lector.read();
    if (done) break;
    const trozo = resto + value;
    let i = 0;
    for (let j = trozo.indexOf('\n'); j >= 0; j = trozo.indexOf('\n', i)) {
      alLinea(trozo.slice(i, j));
      i = j + 1;
    }
    resto = trozo.slice(i);
  }
  if (resto) alLinea(resto);
}

/** Lee la exportacion y la resume (los ultimos `dias` dias). */
export async function leerExportSalud(archivo: Blob, opciones: { dias?: number; hoy?: Date;
                                      progreso?: (fraccion: number) => void } = {}): Promise<ResumenReloj> {
  const hoy = opciones.hoy ?? new Date();
  const d = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - (opciones.dias ?? 120));
  const desde = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const r = new ResumidorSalud(desde);
  await leerLineas(archivo, (l) => r.linea(l), opciones.progreso);
  return r.resultado();
}

/** Lo que la app recuerda de la ultima importacion (para mostrarlo en el panel). */
export interface UltimaImportacion {
  fecha: string;
  noches: number;
  sueno_prom_h: number | null;
  pulso_noche: number | null;
  pasos_prom: number | null;
  entrenos: number;
  hasta: string | null;
}

/** Resumen de los ultimos 7 dias con dato, para el panel. Noches de menos de 3 h
 *  no cuentan: casi siempre es el reloj que no se uso toda la noche. */
export function resumenCorto(r: ResumenReloj, hoy = new Date()): UltimaImportacion {
  const conSueno = r.dias.filter((d) => (d.sueno_min ?? 0) >= 180).slice(-7);
  const conPasos = r.dias.filter((d) => d.pasos !== null).slice(-7);
  const pulsos = conSueno.filter((d) => d.pulso_noche !== null);   // en 1-2 h el pulso no es representativo
  const prom = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  const s = prom(conSueno.map((d) => d.sueno_min! / 60));
  const p = prom(pulsos.map((d) => d.pulso_noche!));
  const pa = prom(conPasos.map((d) => d.pasos!));
  const f = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
  return {
    fecha: f,
    noches: r.dias.filter((d) => (d.sueno_min ?? 0) >= 180).length,
    sueno_prom_h: s === null ? null : Math.round(s * 10) / 10,
    pulso_noche: p === null ? null : Math.round(p),
    pasos_prom: pa === null ? null : Math.round(pa / 100) * 100,
    entrenos: r.entrenos.length,
    hasta: r.dias.length ? r.dias[r.dias.length - 1].fecha : null,
  };
}

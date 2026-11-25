// Pruebas del lector de la exportacion de Apple Salud (app/src/app/salud.ts).
//   cd app && npx esbuild tests/salud.test.ts --bundle --platform=node --outfile=tests/.salud.js && node tests/.salud.js
// Todo es SINTETICO: el XML y el .zip se arman aqui mismo (nunca datos reales).
import { deflateRawSync } from 'node:zlib';
import { ResumidorSalud, leerExportSalud, resumenCorto } from '../src/app/salud';

const fallas: string[] = [];
function check(nombre: string, ok: boolean, detalle = ''): void {
  console.log(`[${ok ? 'OK ' : 'X  '}] ${nombre}${!ok && detalle ? '  -> ' + detalle : ''}`);
  if (!ok) fallas.push(nombre);
}

const TZ = ' -0600';
const rec = (tipo: string, fuente: string, ini: string, fin: string, valor: string | number, unidad = '') =>
  ` <Record type="${tipo}" sourceName="${fuente}" sourceVersion="1"${unidad ? ` unit="${unidad}"` : ''} creationDate="${fin}${TZ}" startDate="${ini}${TZ}" endDate="${fin}${TZ}" value="${valor}"/>`;
const sueno = (fuente: string, ini: string, fin: string, etapa: string) =>
  rec('HKCategoryTypeIdentifierSleepAnalysis', fuente, ini, fin, `HKCategoryValueSleepAnalysis${etapa}`);
const pulso = (t: string, v: number) => rec('HKQuantityTypeIdentifierHeartRate', 'Zepp', t, t, v, 'count/min');

function hhmm(base: Date, min: number): string {
  const d = new Date(base.getTime() + min * 60000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:00`;
}

const lineas: string[] = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<!DOCTYPE HealthData [',
  '<!ELEMENT Workout ((MetadataEntry|WorkoutEvent|WorkoutRoute|WorkoutStatistics)*)>',
  ']>',
  '<HealthData locale="es_MX">',
  ' <ExportDate value="2026-11-25 14:00:00 -0600"/>',
  // ── noche del 19 al 20: Zepp 6.5 h dormido en etapas (con un despertar y "en cama") ──
  sueno('Zepp', '2026-11-19 23:00:00', '2026-11-20 07:00:00', 'InBed'),
  sueno('Zepp', '2026-11-19 23:30:00', '2026-11-20 01:00:00', 'AsleepCore'),
  sueno('Zepp', '2026-11-20 01:00:00', '2026-11-20 02:30:00', 'AsleepDeep'),
  sueno('Zepp', '2026-11-20 02:30:00', '2026-11-20 03:00:00', 'Awake'),
  sueno('Zepp', '2026-11-20 03:00:00', '2026-11-20 05:00:00', 'AsleepREM'),
  sueno('Zepp', '2026-11-20 04:50:00', '2026-11-20 06:30:00', 'AsleepCore'),   // se encima: no cuenta doble
  // el telefono registra 5 h de la misma noche: gana el reloj, no se suman
  sueno('iPhone', '2026-11-20 00:00:00', '2026-11-20 05:00:00', 'AsleepUnspecified'),
  // ── noche del 20 al 21: el reloj solo 1.5 h (no se uso toda la noche) ──
  sueno('Zepp', '2026-11-21 04:00:00', '2026-11-21 05:30:00', 'AsleepCore'),
];
// pulso de la noche 1 cada 5 min: 55 lpm, con 3 lecturas basura de 30 (el minimo
// suelto miente; el percentil 10 no)
const base1 = new Date(Date.UTC(2026, 10, 19, 23, 30));
for (let m = 0; m <= 420; m += 5) lineas.push(pulso(hhmm(base1, m), m === 60 || m === 200 || m === 300 ? 30 : 55));
// despierto en el hueco de las 2:30-3:00 con pulso alto: fuera de los tramos dormido
lineas.push(pulso('2026-11-20 02:40:00', 95), pulso('2026-11-20 02:45:00', 98));
for (let m = 0; m < 10; m++) lineas.push(pulso(hhmm(new Date(Date.UTC(2026, 10, 21, 4, 0)), m * 5), 58));
lineas.push(pulso('2026-11-20 15:00:00', 120));                                  // tarde: ignorado
lineas.push(
  // pasos del 20: telefono 3,500 y reloj 4,300 (los mismos pasos): cuenta la mayor
  rec('HKQuantityTypeIdentifierStepCount', 'iPhone', '2026-11-20 09:00:00', '2026-11-20 09:10:00', 1000, 'count'),
  rec('HKQuantityTypeIdentifierStepCount', 'iPhone', '2026-11-20 12:00:00', '2026-11-20 12:10:00', 2000, 'count'),
  rec('HKQuantityTypeIdentifierStepCount', 'iPhone', '2026-11-20 18:00:00', '2026-11-20 18:10:00', 500, 'count'),
  rec('HKQuantityTypeIdentifierStepCount', 'Zepp', '2026-11-20 09:00:00', '2026-11-20 13:00:00', 2500, 'count'),
  rec('HKQuantityTypeIdentifierStepCount', 'Zepp', '2026-11-20 13:00:00', '2026-11-20 20:00:00', 1800, 'count'),
  rec('HKQuantityTypeIdentifierRestingHeartRate', 'Zepp', '2026-11-20 08:00:00', '2026-11-20 08:00:00', 54, 'count/min'),
  rec('HKQuantityTypeIdentifierHeartRateVariabilitySDNN', 'Zepp', '2026-11-20 03:00:00', '2026-11-20 03:01:00', 40, 'ms'),
  rec('HKQuantityTypeIdentifierHeartRateVariabilitySDNN', 'Zepp', '2026-11-20 05:00:00', '2026-11-20 05:01:00', 50, 'ms'),
  // dos pesajes el mismo dia: gana el ultimo (8:00, en libras)
  rec('HKQuantityTypeIdentifierBodyMass', 'Zepp', '2026-11-20 07:00:00', '2026-11-20 07:00:00', 80, 'kg'),
  rec('HKQuantityTypeIdentifierBodyMass', 'Zepp', '2026-11-20 08:00:00', '2026-11-20 08:00:00', 170, 'lb'),
  // viejo (antes del rango): ignorado
  rec('HKQuantityTypeIdentifierStepCount', 'iPhone', '2026-09-01 09:00:00', '2026-09-01 09:10:00', 9999, 'count'),
  // tipo que no interesa
  rec('HKQuantityTypeIdentifierOxygenSaturation', 'Zepp', '2026-11-20 03:00:00', '2026-11-20 03:00:00', 0.97, '%'),
  // entreno de fuerza con hijos (varias lineas) y eliptica en una sola linea
  ` <Workout workoutActivityType="HKWorkoutActivityTypeTraditionalStrengthTraining" duration="85" durationUnit="min" sourceName="Zepp" sourceVersion="1" device="&lt;&lt;HKDevice: 0x1&gt;, name:Amazfit&gt;" creationDate="2026-11-20 19:26:00${TZ}" startDate="2026-11-20 18:00:00${TZ}" endDate="2026-11-20 19:25:00${TZ}">`,
  '  <MetadataEntry key="HKIndoorWorkout" value="1"/>',
  `  <WorkoutEvent type="HKWorkoutEventTypeMarker" date="2026-11-20 18:30:00${TZ}"/>`,
  `  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2026-11-20 18:00:00${TZ}" endDate="2026-11-20 19:25:00${TZ}" sum="400" unit="kcal"/>`,
  `  <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="2026-11-20 18:00:00${TZ}" endDate="2026-11-20 19:25:00${TZ}" average="118.4" minimum="80" maximum="160" unit="count/min"/>`,
  ' </Workout>',
  ` <Workout workoutActivityType="HKWorkoutActivityTypeElliptical" duration="17.3" durationUnit="min" sourceName="Zepp" sourceVersion="1" creationDate="2026-11-20 19:48:00${TZ}" startDate="2026-11-20 19:30:00${TZ}" endDate="2026-11-20 19:47:18${TZ}"/>`,
  ` <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="30" durationUnit="min" sourceName="Apple Watch" sourceVersion="1" creationDate="2024-02-01 08:00:00${TZ}" startDate="2024-02-01 07:30:00${TZ}" endDate="2024-02-01 08:00:00${TZ}">`,
  ' </Workout>',
  '</HealthData>',
);
const xml = lineas.join('\n') + '\n';

/** Zip minimo (deflate), con un campo extra en la cabecera local para probar el offset. */
function armarZip(archivos: Array<[string, string]>): Uint8Array {
  const partes: Buffer[] = [];
  const central: Buffer[] = [];
  let off = 0;
  for (const [nombre, texto] of archivos) {
    const datos = Buffer.from(texto, 'utf8');
    const comp = deflateRawSync(datos);
    const n = Buffer.from(nombre, 'utf8');
    const extra = Buffer.from([0x55, 0x54, 0x01, 0x00, 0x00]);         // "UT" con 1 byte
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(8, 6); lh.writeUInt16LE(8, 8);
    lh.writeUInt32LE(0, 18); lh.writeUInt32LE(0, 22);                     // tamanos en el descriptor (como iOS)
    lh.writeUInt16LE(n.length, 26); lh.writeUInt16LE(extra.length, 28);
    const desc = Buffer.alloc(16);
    desc.writeUInt32LE(0x08074b50, 0); desc.writeUInt32LE(comp.length, 8); desc.writeUInt32LE(datos.length, 12);
    partes.push(lh, n, extra, comp, desc);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 4); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(8, 8); ch.writeUInt16LE(8, 10);
    ch.writeUInt32LE(comp.length, 20); ch.writeUInt32LE(datos.length, 24); ch.writeUInt16LE(n.length, 28); ch.writeUInt32LE(off, 42);
    central.push(ch, n);
    off += 30 + n.length + extra.length + comp.length + desc.length;
  }
  const cd = Buffer.concat(central);
  const fin = Buffer.alloc(22);
  fin.writeUInt32LE(0x06054b50, 0); fin.writeUInt16LE(archivos.length, 8); fin.writeUInt16LE(archivos.length, 10);
  fin.writeUInt32LE(cd.length, 12); fin.writeUInt32LE(off, 16);
  return new Uint8Array(Buffer.concat([...partes, cd, fin]));
}

async function main(): Promise<void> {
  const hoy = new Date(2026, 10, 25);
  // el _cda es otro formato y a veces mas grande: nunca se lee
  const cda = lineas.map((l) => l.replace('value="55"', 'value="99"')).join('\n').repeat(2);
  const zip = armarZip([
    ['apple_health_export/exportar.xml', xml],
    ['apple_health_export/workout-routes/route_2026-11-20.gpx', '<gpx/>'],
    ['apple_health_export/export_cda.xml', cda],
  ]);
  const avances: number[] = [];
  const r = await leerExportSalud(new Blob([zip]), { dias: 30, hoy, progreso: (f) => avances.push(f) });
  const d20 = r.dias.find((d) => d.fecha === '2026-11-20');
  const d21 = r.dias.find((d) => d.fecha === '2026-11-21');

  console.log('== Sueno y pulso ==');
  check('desde = hoy - 30 dias', r.desde === '2026-10-26', r.desde);
  check('la noche del 19 al 20 cuenta para el 20 (dia en que despiertas)', !!d20 && d20.sueno_min !== null);
  check('6.5 h: etapas unidas, sin "en cama" ni "despierto", sin contar doble lo encimado',
        d20?.sueno_min === 390, String(d20?.sueno_min));
  check('si reloj y telefono registran la misma noche, gana el reloj (no se suman)', d20?.sueno_min === 390);
  check('pulso de la noche: percentil 10 (las 3 lecturas basura de 30 no cuentan)', d20?.pulso_noche === 55, String(d20?.pulso_noche));
  check('noche incompleta (1.5 h) se guarda tal cual; sin pulso con <20 lecturas',
        d21?.sueno_min === 90 && d21?.pulso_noche === null, JSON.stringify(d21));
  check('pulso en reposo y HRV del dia', d20?.pulso_reposo === 54 && d20?.hrv === 45, JSON.stringify(d20));

  console.log('== Pasos, peso y entrenos ==');
  check('pasos: la fuente con mas pasos, no la suma de telefono + reloj', d20?.pasos === 4300, String(d20?.pasos));
  check('peso: el ultimo pesaje del dia, de libras a kg', d20?.peso === 77.1, String(d20?.peso));
  check('lo anterior al rango no entra', !r.dias.some((d) => d.fecha < r.desde) && !r.entrenos.some((e) => e.inicio < r.desde));
  check('2 entrenos (el de 2024 queda fuera)', r.entrenos.length === 2, String(r.entrenos.length));
  const f = r.entrenos[0];
  check('fuerza: tipo, inicio/fin en hora local, 85 min y pulso promedio de sus estadisticas',
        f?.tipo === 'TraditionalStrengthTraining' && f.inicio === '2026-11-20 18:00:00' && f.fin === '2026-11-20 19:25:00'
        && f.minutos === 85 && f.pulso_prom === 118, JSON.stringify(f));
  const el = r.entrenos[1];
  check('eliptica en una sola linea: 17.3 min, sin pulso', el?.tipo === 'Elliptical' && el.minutos === 17.3 && el.pulso_prom === null,
        JSON.stringify(el));
  check('el export_cda.xml no se lee', !r.dias.some((d) => d.pulso_noche === 99));
  check('avisa el avance hasta 100 %', avances.length > 0 && avances[avances.length - 1] === 1, String(avances.slice(-1)));

  console.log('== .xml suelto, resumen y errores ==');
  const r2 = await leerExportSalud(new File([xml], 'exportar.xml'), { dias: 30, hoy });
  check('el .xml suelto (descomprimido en Archivos) da lo mismo', JSON.stringify(r2.dias) === JSON.stringify(r.dias)
        && JSON.stringify(r2.entrenos) === JSON.stringify(r.entrenos));
  const c = resumenCorto(r, hoy);
  check('resumen corto: 1 noche completa de 6.5 h, 4,300 pasos, 2 entrenos',
        c.noches === 1 && c.sueno_prom_h === 6.5 && c.pasos_prom === 4300 && c.entrenos === 2 && c.hasta === '2026-11-21',
        JSON.stringify(c));
  let msg = '';
  try {
    await leerExportSalud(new Blob([new Uint8Array(200)]), { hoy });
  } catch (e) {
    msg = (e as Error).message;
  }
  check('un archivo que no es zip da un error claro', /no es un \.zip/i.test(msg), msg);
  msg = '';
  try {
    await leerExportSalud(new Blob([armarZip([['otra/cosa.txt', 'hola']])]), { hoy });
  } catch (e) {
    msg = (e as Error).message;
  }
  check('un zip sin la exportacion de Salud da un error claro', /no trae la exportaci/i.test(msg), msg);
  const vacio = new ResumidorSalud('2026-11-01');
  vacio.linea('<HealthData>');
  check('sin registros: resumen vacio', vacio.resultado().dias.length === 0 && vacio.registros === 0);

  console.log(fallas.length ? `\n${fallas.length} FALLA(S): ${fallas.join(' | ')}` : '\nTodo OK.');
  if (fallas.length) process.exit(1);
}

void main();

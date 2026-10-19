// Pruebas del acomodo de la semana (app/src/app/semana-plan.ts).
//   cd app && npx esbuild tests/semana-plan.test.ts --bundle --platform=node --outfile=tests/.semana.js && node tests/.semana.js
// semana-real.json = la semana del 19 de octubre de 2026 tal como la genero el motor
// (Torso A, Basquet, Torso Bombeo, Basquet, Pierna A, Torso C, Pierna Bombeo).
import semana from './semana-real.json';
import { acomodar, cargaDeSesion, choque, costoSemana, sinRecuperar } from '../src/app/semana-plan';

const fallas: string[] = [];
function check(nombre: string, ok: boolean, detalle = ''): void {
  console.log(`[${ok ? 'OK ' : 'X  '}] ${nombre}${!ok && detalle ? '  -> ' + detalle : ''}`);
  if (!ok) fallas.push(nombre);
}

const deporte = semana.map((s) => /deporte/i.test(s.bloque ?? ''));
const cargas = semana.map((s, i) => cargaDeSesion(s.filas, deporte[i]));
const nombre = (orden: number[]) => orden.map((s) => semana[s - 1].nombre);
const esTorso = (s: number) => /torso/i.test(semana[s - 1].nombre);
const esPierna = (s: number) => /pierna/i.test(semana[s - 1].nombre);
const fijosDe = (orden: number[], hoy: number, movidos: number[]) =>
  new Set([1, 2, 3, 4, 5, 6, 7].filter((cal) => cal <= hoy || movidos.includes(cal) || deporte[orden[cal - 1] - 1]));

console.log('== Cargas ==');
check('torso carga pecho y dorsales; pierna, cuadriceps', (cargas[0].pecho ?? 0) > 0 && (cargas[0].dorsales ?? 0) > 0
      && (cargas[4].cuadriceps ?? 0) > 0 && !cargas[4].pecho);
check('el basquet carga gemelos, cuadriceps y gluteos', cargas[1].gemelos === 4 && cargas[1].cuadriceps === 3);
check('torso al dia siguiente de torso choca mucho; a los 3 dias, nada',
      choque(cargas[0], cargas[2], 1) > 5 && choque(cargas[0], cargas[2], 3) === 0,
      `${choque(cargas[0], cargas[2], 1).toFixed(1)} / ${choque(cargas[0], cargas[2], 3)}`);
check('torso y pierna casi no chocan', choque(cargas[0], cargas[4], 1) < 1.5, choque(cargas[0], cargas[4], 1).toFixed(2));

console.log('\n== Tu caso: lunes, cambias el basquet de manana a hoy ==');
const original = [1, 2, 3, 4, 5, 6, 7];
const cambiado = original.slice();
[cambiado[0], cambiado[1]] = [cambiado[1], cambiado[0]];            // Lun basquet, Mar Torso A
const r = acomodar(cambiado, cargas, fijosDe(cambiado, 1, [1, 2]), cargas[0]);
console.log('   ', nombre(r.orden).join(' | '));
check('lunes basquet y martes Torso A (lo que pediste) no se tocan',
      r.orden[0] === 2 && r.orden[1] === 1);
check('el jueves sigue siendo basquet (no se mueve solo)', r.orden[3] === 4);
check('nunca torso dos dias seguidos',
      r.orden.every((s, i) => i === 0 || !(esTorso(s) && esTorso(r.orden[i - 1]))), nombre(r.orden).join(', '));
check('nunca pierna dos dias seguidos',
      r.orden.every((s, i) => i === 0 || !(esPierna(s) && esPierna(r.orden[i - 1]))));
check('ningun dia queda con pecho o dorsales sin 48 h',
      [1, 2, 3, 4, 5, 6, 7].every((cal) => !sinRecuperar(r.orden, cargas, cal).some((m) => m === 'pecho' || m === 'dorsales')),
      [1, 2, 3, 4, 5, 6, 7].map((cal) => sinRecuperar(r.orden, cargas, cal).join('+')).join(' | '));
check('es la misma semana, solo reordenada', [...r.orden].sort().join() === original.join());
check('dice que movio', r.movidos.length > 0 && r.movidos.every((m) => r.orden[m.a - 1] === m.sesion));
const sinAcomodar = costoSemana(cambiado.map((s) => cargas[s - 1]), cargas[0]);
const conAcomodo = costoSemana(r.orden.map((s) => cargas[s - 1]), cargas[0]);
check('acomodado choca menos que solo intercambiar', conAcomodo < sinAcomodar,
      `${conAcomodo.toFixed(1)} vs ${sinAcomodar.toFixed(1)}`);

console.log('\n== Lo que te paso con el boton viejo (captura del 19 oct) ==');
const viejo = [4, 2, 1, 6, 5, 3, 7];         // Lun Basq, Mar Basq, Mie Torso A, Jue Torso C, Vie Pierna A, Sab Torso B, Dom Pierna B
const avisoJue = sinRecuperar(viejo, cargas, 4);
check('el jueves (Torso C despues de Torso A) avisa pecho/dorsales sin recuperar',
      avisoJue.includes('pecho') || avisoJue.includes('dorsales'), avisoJue.join(', '));
const arreglo = acomodar(viejo, cargas, fijosDe(viejo, 1, []), cargas[0]);
console.log('   ', nombre(arreglo.orden).join(' | '));
check('acomodar arregla esa semana: sin torso seguido',
      arreglo.orden.every((s, i) => i === 0 || !(esTorso(s) && esTorso(arreglo.orden[i - 1]))));

console.log('\n== Estabilidad ==');
const igual = acomodar(original, cargas, fijosDe(original, 1, []), cargas[0]);
check('el plan del motor ya estaba bien: no se mueve nada', igual.movidos.length === 0, nombre(igual.orden).join(', '));
const tarde = acomodar(cambiado, cargas, fijosDe(cambiado, 6, [1, 2]), cargas[0]);
check('el sabado ya no hay nada que acomodar (solo queda el domingo)', tarde.movidos.length === 0);
const fijos = fijosDe(cambiado, 3, [1, 2]);
const parcial = acomodar(cambiado, cargas, fijos, cargas[0]);
check('nunca toca dias pasados, hoy ni los fijos', [...fijos].every((cal) => parcial.orden[cal - 1] === cambiado[cal - 1]));

console.log(`\nRESULTADO: ${fallas.length ? fallas.length + ' pruebas FALLARON: ' + fallas.join('; ') : 'todas las pruebas pasaron.'}`);
if (fallas.length) process.exit(1);

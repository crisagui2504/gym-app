import { Pipe, PipeTransform } from '@angular/core';

/**
 * Acentos para MOSTRAR. Los nombres de ejercicio y las notas que manda el motor
 * van sin tildes ("Jalon al Pecho", "rotacion de angulo") porque son claves del
 * historial y de los clasificadores (norm() las compara sin acentos). Cambiarlos
 * en los datos romperia el historial; aqui solo se corrigen al pintarlos.
 * Solo palabras SIN ambiguedad ("mas" en estos textos es siempre "más"; "esta"
 * o "si" no se tocan porque pueden ir con o sin tilde).
 */
const MAPA: Record<string, string> = {
  abduccion: 'abducción', activacion: 'activación', aduccion: 'aducción', angulo: 'ángulo',
  aproximacion: 'aproximación', aqui: 'aquí', atras: 'atrás', basquet: 'básquet', basquetbol: 'básquetbol',
  bascula: 'báscula', biceps: 'bíceps', bulgara: 'búlgara', cajon: 'cajón', calorias: 'calorías',
  comodo: 'cómodo', conexion: 'conexión', cuadriceps: 'cuádriceps', cuantas: 'cuántas', despues: 'después',
  dia: 'día', dias: 'días', dificil: 'difícil', elevacion: 'elevación', eliptica: 'elíptica',
  energia: 'energía', estatica: 'estática', estres: 'estrés', excentrica: 'excéntrica', excentrico: 'excéntrico',
  extension: 'extensión', facil: 'fácil', faciles: 'fáciles', frances: 'francés', gluteo: 'glúteo',
  gluteos: 'glúteos', hiperextension: 'hiperextensión', isometrica: 'isométrica', isometrico: 'isométrico',
  jalon: 'jalón', limite: 'límite', manten: 'mantén', maquina: 'máquina', maquinas: 'máquinas',
  marcalo: 'márcalo', mas: 'más', maxima: 'máxima', maximo: 'máximo', metabolico: 'metabólico',
  metodo: 'método', minimo: 'mínimo', muevela: 'muévela', muneca: 'muñeca', munecas: 'muñecas',
  musculo: 'músculo', musculos: 'músculos', nordico: 'nórdico', numero: 'número', omoplatos: 'omóplatos',
  pajaro: 'pájaro', pajaros: 'pájaros', podes: 'puedes', podrias: 'podrías', posicion: 'posición',
  proteina: 'proteína', proxima: 'próxima', proximo: 'próximo', quedo: 'quedó', rapida: 'rápida',
  rapido: 'rápido', recuperacion: 'recuperación', reenviara: 'reenviará', retraccion: 'retracción',
  rotacion: 'rotación', segun: 'según', sesion: 'sesión', sincronizara: 'sincronizará', soleo: 'sóleo',
  sosten: 'sostén', talon: 'talón', tambien: 'también', tecnica: 'técnica', tecnicas: 'técnicas',
  tecnico: 'técnico', telefono: 'teléfono', triceps: 'tríceps', ultima: 'última', ultimas: 'últimas',
  ultimo: 'último', util: 'útil', vacia: 'vacía'
};

const PALABRA = new RegExp(`(?<![\\p{L}])(${Object.keys(MAPA).join('|')})(?![\\p{L}])`, 'giu');

/** Pone las tildes que faltan respetando mayusculas ("MAS" -> "MÁS", "Jalon" -> "Jalón"). */
export function acentuar(texto: string | null | undefined): string {
  if (!texto) return texto ?? '';
  return texto.replace(PALABRA, (m) => {
    const r = MAPA[m.toLowerCase()];
    if (!r) return m;
    if (m === m.toUpperCase() && m.length > 1) return r.toUpperCase();
    if (m[0] === m[0].toUpperCase()) return r[0].toUpperCase() + r.slice(1);
    return r;
  });
}

@Pipe({ name: 'acentos', standalone: true })
export class AcentosPipe implements PipeTransform {
  transform(texto: string | null | undefined): string {
    return acentuar(texto);
  }
}

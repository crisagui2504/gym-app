// Datos de entrenamiento: musculos, imagenes (wger.de externas), tecnicas,
// catalogo de alternativas, series y descansos. Todo local / sin coste de hosting.

export type MuscleId =
  | 'hombros'
  | 'pecho'
  | 'biceps'
  | 'antebrazos'
  | 'abdomen'
  | 'cuadriceps'
  | 'trapecios'
  | 'dorsales'
  | 'triceps'
  | 'lumbar'
  | 'gluteos'
  | 'isquios'
  | 'gemelos';

export const MUSCLE_LABEL: Record<MuscleId, string> = {
  hombros: 'Hombros',
  pecho: 'Pecho',
  biceps: 'Biceps',
  antebrazos: 'Antebrazos',
  abdomen: 'Core',
  cuadriceps: 'Cuadriceps',
  trapecios: 'Trapecios',
  dorsales: 'Dorsales',
  triceps: 'Triceps',
  lumbar: 'Lumbar',
  gluteos: 'Gluteos',
  isquios: 'Isquios',
  gemelos: 'Gemelos'
};

/** Fecha local en formato YYYY-MM-DD (evita el desfase de toISOString que usa UTC). */
export function fechaLocal(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dia}`;
}

export function norm(texto: string): string {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

/** Musculos principales de un ejercicio segun su nombre. El primero es el primario. */
export function musculosDe(nombre: string): MuscleId[] {
  const n = norm(nombre);
  const s: MuscleId[] = [];
  const add = (m: MuscleId) => {
    if (!s.includes(m)) s.push(m);
  };
  const tiene = (...claves: string[]) => claves.some((k) => n.includes(k));

  if (tiene('curl de isquios', 'curl femoral')) {
    add('isquios');
    add('gluteos');
  } else if (tiene('peso muerto rumano', 'rumano', 'pdr', 'buenos dias', 'peso muerto', 'isquios', 'femoral')) {
    add('isquios');
    add('gluteos');
    add('lumbar');
  }
  if (tiene('hip thrust', 'puente de gluteo', 'patada de gluteo')) {
    add('gluteos');
    add('isquios');
  }
  if (tiene('press militar', 'press arnold', 'arnold', 'militar', 'press de hombro')) {
    add('hombros');
    add('triceps');
  }
  if (tiene('elevacion', 'elevaciones', 'lateral')) add('hombros');
  if (tiene('face pull', 'pec deck invertido', 'pajaro', 'posterior')) {
    add('hombros');
    add('trapecios');
  }
  if (tiene('press de banca', 'banca', 'press inclinado', 'press plano', 'pec deck', 'apertura', 'peck', 'aperturas')) {
    add('pecho');
    add('triceps');
    add('hombros');
  }
  if (tiene('fondos', 'dips')) {
    add('pecho');
    add('triceps');
  }
  if (tiene('remo', 'jalon', 'dominada', 'gironda', 'pull over', 'pullover', 'pull-up')) {
    add('dorsales');
    add('trapecios');
    add('biceps');
  }
  if (tiene('encogimiento', 'shrug', 'trapecio')) add('trapecios');
  if (tiene('curl invertido', 'martillo', 'muneca', 'antebrazo')) add('antebrazos');
  if (tiene('curl') && !tiene('isquios', 'femoral')) add('biceps');
  if (tiene('triceps', 'press frances', 'frances', 'copa', 'patada', 'press cerrado', 'close grip')) add('triceps');
  if (tiene('sentadilla', 'prensa', 'hack', 'zancada', 'bulgara', 'split', 'extension de cuadriceps', 'extensiones de cuadriceps', 'cuadriceps')) {
    add('cuadriceps');
    add('gluteos');
  }
  if (tiene('lumbar', 'hiperextension', 'extensiones lumbares', 'extension lumbar')) add('lumbar');
  if (tiene('pantorrilla', 'gemelo', 'soleo', 'talon', 'calf')) add('gemelos');
  if (tiene('plancha', 'crunch', 'abdominal', 'rueda', 'ab wheel', 'elevaciones de piernas', 'elevacion de piernas', 'oblicuo', 'core')) {
    add('abdomen');
  }
  if (tiene('farmer', 'pinzamiento', 'agarre')) add('antebrazos');

  return s;
}

// ===== Catalogo de ejercicios comunes por musculo primario (sin imagenes) =====
interface CatItem {
  nombre: string;
  muscle: MuscleId;
  claves: string[];
}

// Ordenado de mas especifico a mas generico.
const CATALOGO: CatItem[] = [
  // Pecho
  { nombre: 'Press Inclinado con Mancuernas', muscle: 'pecho', claves: ['press inclinado', 'inclinado'] },
  { nombre: 'Aperturas en Maquina (Pec Deck)', muscle: 'pecho', claves: ['pec deck', 'apertura', 'aperturas', 'peck'] },
  { nombre: 'Press de Banca con Barra', muscle: 'pecho', claves: ['press de banca', 'banca'] },
  { nombre: 'Press con Mancuernas', muscle: 'pecho', claves: ['press con mancuernas', 'press plano'] },
  // Hombros
  { nombre: 'Face Pull / Pajaros', muscle: 'hombros', claves: ['face pull', 'pajaro', 'pec deck invertido', 'posterior'] },
  { nombre: 'Press Militar con Mancuernas', muscle: 'hombros', claves: ['press militar', 'militar', 'arnold', 'press de hombro'] },
  { nombre: 'Elevaciones Laterales', muscle: 'hombros', claves: ['elevacion', 'elevaciones', 'lateral'] },
  { nombre: 'Press de Hombro en Maquina', muscle: 'hombros', claves: ['hombro en maquina'] },
  // Dorsales
  { nombre: 'Remo Sentado en Polea', muscle: 'dorsales', claves: ['remo en polea', 'remo sentado', 'gironda', 'polea baja'] },
  { nombre: 'Jalon al Pecho / Dominadas', muscle: 'dorsales', claves: ['jalon', 'dominada'] },
  { nombre: 'Remo con Barra', muscle: 'dorsales', claves: ['remo'] },
  { nombre: 'Remo en Maquina (T-Bar)', muscle: 'dorsales', claves: ['t-bar', 'remo t'] },
  // Triceps
  { nombre: 'Extension de Triceps en Polea', muscle: 'triceps', claves: ['extension triceps', 'extension de triceps', 'triceps', 'frances', 'patada'] },
  { nombre: 'Fondos en Banco', muscle: 'triceps', claves: ['fondos', 'dips'] },
  { nombre: 'Press Cerrado', muscle: 'triceps', claves: ['press cerrado', 'close grip'] },
  // Biceps
  { nombre: 'Curl Martillo', muscle: 'biceps', claves: ['martillo'] },
  { nombre: 'Curl con Barra', muscle: 'biceps', claves: ['curl con barra', 'curl ez', 'barra ez', 'curl de biceps'] },
  { nombre: 'Curl con Mancuernas', muscle: 'biceps', claves: ['curl con mancuernas', 'curl alterno'] },
  { nombre: 'Curl Predicador', muscle: 'biceps', claves: ['predicador', 'preacher'] },
  // Cuadriceps
  { nombre: 'Zancadas Caminando', muscle: 'cuadriceps', claves: ['zancada', 'bulgara', 'split'] },
  { nombre: 'Sentadilla Hack en Maquina', muscle: 'cuadriceps', claves: ['hack'] },
  { nombre: 'Prensa de Piernas', muscle: 'cuadriceps', claves: ['prensa'] },
  { nombre: 'Extension de Cuadriceps', muscle: 'cuadriceps', claves: ['extension de cuadriceps', 'extensiones de cuadriceps'] },
  { nombre: 'Sentadilla con Barra', muscle: 'cuadriceps', claves: ['sentadilla', 'frontal', 'cuadriceps'] },
  // Isquios
  { nombre: 'Curl de Isquios en Maquina', muscle: 'isquios', claves: ['curl de isquios', 'curl femoral', 'isquios', 'femoral'] },
  { nombre: 'Peso Muerto Rumano', muscle: 'isquios', claves: ['rumano', 'pdr', 'buenos dias', 'peso muerto'] },
  // Gluteos
  { nombre: 'Hip Thrust', muscle: 'gluteos', claves: ['hip thrust', 'puente'] },
  // Trapecios
  { nombre: 'Encogimientos', muscle: 'trapecios', claves: ['encogimiento', 'shrug', 'trapecio'] },
  // Abdomen
  { nombre: 'Elevaciones de Piernas', muscle: 'abdomen', claves: ['elevaciones de piernas', 'elevacion de piernas', 'colgado'] },
  { nombre: 'Crunch / Plancha', muscle: 'abdomen', claves: ['crunch', 'abdominal', 'plancha', 'rueda', 'oblicuo'] },
  // Lumbar
  { nombre: 'Hiperextensiones', muscle: 'lumbar', claves: ['lumbar', 'hiperextension', 'extensiones lumbares'] },
  // Antebrazos
  { nombre: 'Curl con Cuerda', muscle: 'antebrazos', claves: ['antebrazo', 'muneca', 'curl invertido', 'farmer'] }
];

export interface Alternativa {
  nombre: string;
  musculos: MuscleId[];
}

/** Alternativas que entrenan el mismo grupo muscular primario. */
export function alternativasDe(nombre: string): Alternativa[] {
  const primario = musculosDe(nombre)[0];
  if (!primario) return [];
  const objetivo = norm(nombre);
  return CATALOGO.filter((c) => c.muscle === primario && norm(c.nombre) !== objetivo).map((c) => ({
    nombre: c.nombre,
    musculos: musculosDe(c.nombre)
  }));
}

// ===== Tecnicas (explicaciones) =====
export interface Tecnica {
  titulo: string;
  texto: string;
}

const TECNICAS: Array<{ clave: string; data: Tecnica }> = [
  { clave: 'top set', data: { titulo: 'Top Set', texto: 'Tu serie mas pesada del dia (1 serie). Intenta superar el peso o las reps de la semana pasada. Hazla bien descansado (~3 min) tras tus series de aproximacion.' } },
  { clave: 'back-off', data: { titulo: 'Back-off', texto: 'Despues del Top Set baja el peso ~20% y haz 2 series con mas repeticiones. Sirve para acumular volumen de forma mas segura.' } },
  { clave: 'back off', data: { titulo: 'Back-off', texto: 'Despues del Top Set baja el peso ~20% y haz 2 series con mas repeticiones para acumular volumen.' } },
  { clave: 'amrap', data: { titulo: 'AMRAP', texto: 'As Many Reps As Possible: la ultima serie se lleva al fallo muscular. Tantas repeticiones como puedas con buena tecnica.' } },
  { clave: 'rest-pause', data: { titulo: 'Rest-Pause', texto: 'Llega al fallo (~12-15 reps), suelta el peso 10 segundos sin moverte, y vuelve con el MISMO peso al fallo (~4-6 reps). Repite 1-2 veces. Todo eso = 1 serie.' } },
  { clave: 'rest pause', data: { titulo: 'Rest-Pause', texto: 'Fallo (~12-15) -> 10 seg de pausa -> mismo peso al fallo otra vez. Repite 1-2 veces = 1 serie. Estres metabolico maximo.' } },
  { clave: 'drop set', data: { titulo: 'Drop Set', texto: 'Serie al fallo, baja el peso 20-30% sin descansar y vuelve al fallo. 1-2 bajadas. Agota todas las fibras del musculo.' } },
  { clave: 'superserie', data: { titulo: 'Superserie', texto: 'Dos ejercicios seguidos SIN descanso entre ellos. Descansas solo al terminar la ronda (~60-90 seg).' } },
  { clave: 'tradicional', data: { titulo: 'Tradicional', texto: 'Series y repeticiones normales, con descanso completo entre cada serie.' } }
];

export const RPE_INFO: Tecnica = {
  titulo: 'RPE · Esfuerzo percibido',
  texto:
    'Mide que tan cerca del fallo terminaste la serie: cuantas repeticiones MAS podrias haber hecho. ' +
    '6 = facil (te sobraban ~4) · 8 = exigente (2 en reserva) · 10 = al fallo total. ' +
    'El motor lo usa para tu progreso: si cumples las reps con RPE 8 o menos, la proxima semana sube el peso; ' +
    'si te estancas con RPE 9-10, baja la carga (deload). Marcalo honesto.'
};

/** Significado corto del numero de RPE elegido. */
export function rpeSignificado(rpe: number): string {
  if (rpe <= 6) return 'facil · ~4 reps en reserva';
  if (rpe === 7) return 'comodo · 3 en reserva';
  if (rpe === 8) return 'exigente · 2 en reserva';
  if (rpe === 9) return 'casi al limite · 1 en reserva';
  return 'al fallo · 0 en reserva';
}

/** Devuelve la explicacion de una tecnica, o null. */
export function explicacionTecnica(tecnica: string | null): Tecnica | null {
  if (!tecnica) return null;
  const n = norm(tecnica);
  for (const t of TECNICAS) {
    if (n.includes(t.clave)) return t.data;
  }
  return null;
}

/** Cuantas series mostrar segun series_objetivo (acepta "2", "2.0", "2-5"). */
export function nSeriesDe(seriesObjetivo: string | number | null): number {
  if (seriesObjetivo == null) return 3;
  const nums = String(seriesObjetivo).match(/\d+/g);
  if (!nums || !nums.length) return 3;
  const n = Math.max(...nums.map((x) => parseInt(x, 10)));
  return Math.min(6, Math.max(1, n));
}

/** Descanso en segundos por tecnica si la base no lo trae. */
export function descansoPorTecnica(tecnica: string | null): number {
  const t = explicacionTecnica(tecnica);
  if (!t) return 90;
  switch (t.titulo) {
    case 'Top Set':
      return 180;
    case 'Back-off':
      return 120;
    case 'Drop Set':
    case 'Superserie':
    case 'AMRAP':
      return 90;
    case 'Rest-Pause':
      return 90;
    default:
      return 90;
  }
}

// ===== Calentamiento =====
export interface PasoCalentamiento {
  nombre: string;
  detalle: string;
  meta: string;
}

export interface Calentamiento {
  movilidad: PasoCalentamiento[];
  activacion: PasoCalentamiento[];
}

const CAL_TORSO: Calentamiento = {
  movilidad: [
    { nombre: 'Rotaciones de hombro', detalle: '10 hacia adelante y 10 atras en cada brazo.', meta: '40 seg' },
    { nombre: 'Retraccion escapular', detalle: 'Brazos al frente, junta los omoplatos con fuerza. 15 reps.', meta: '30 seg' },
    { nombre: 'Apertura de pecho', detalle: 'Abre y cierra los brazos a la altura del pecho. 10 reps.', meta: '30 seg' }
  ],
  activacion: [
    { nombre: 'Empuje con barra vacia', detalle: 'Press de banca o militar con barra vacia, enfoca la tecnica.', meta: '2 x 15' },
    { nombre: 'Jalon ligero', detalle: 'Jalon o remo con peso muy ligero para activar la espalda.', meta: '2 x 15' }
  ]
};

const CAL_PIERNA: Calentamiento = {
  movilidad: [
    { nombre: 'Sentadilla profunda con pausa', detalle: 'Baja al fondo y manten 2 seg. 10 reps.', meta: '40 seg' },
    { nombre: 'Apertura de cadera (mariposa)', detalle: 'Junta las plantas y empuja las rodillas hacia abajo.', meta: '30 seg' },
    { nombre: 'Estocada con rotacion', detalle: 'Paso al frente y rota el torso. 8 reps por lado.', meta: '40 seg' }
  ],
  activacion: [
    { nombre: 'Sentadilla con barra vacia', detalle: 'Baja a paralelo, rodillas siguiendo los pies.', meta: '2 x 15' },
    { nombre: 'Buenos dias con barra vacia', detalle: 'Activa isquios y protege la espalda baja.', meta: '1 x 10' }
  ]
};

const CAL_GENERAL: Calentamiento = {
  movilidad: [
    { nombre: 'Cardio suave', detalle: 'Eliptica o cinta a ritmo comodo para subir pulsaciones.', meta: '5 min' },
    { nombre: 'Movilidad articular', detalle: 'Cuello, hombros, caderas, rodillas y tobillos.', meta: '2 min' }
  ],
  activacion: [{ nombre: 'Activacion de core', detalle: 'Plancha 2 x 20 seg + gato-camello 10 reps.', meta: '2 series' }]
};

/** Rutina de calentamiento adaptada al enfoque del dia. */
export function calentamientoDe(nombreDia: string): Calentamiento {
  const n = norm(nombreDia);
  if (['pierna', 'cuadriceps', 'isquios', 'gluteo'].some((k) => n.includes(k))) return CAL_PIERNA;
  if (['torso', 'hombro', 'pecho', 'espalda', 'bombeo'].some((k) => n.includes(k))) return CAL_TORSO;
  return CAL_GENERAL;
}

function redondear(valor: number, paso = 2.5): number {
  return Math.max(paso, Math.round(valor / paso) * paso);
}

/** Series de aproximacion progresivas a partir del peso objetivo. */
export function seriesAproximacion(peso: number): Array<{ label: string; peso: number; reps: number }> {
  if (!peso || peso < 10) return [];
  return [
    { porcentaje: 0.5, reps: 10, label: '50%' },
    { porcentaje: 0.7, reps: 5, label: '70%' },
    { porcentaje: 0.9, reps: 1, label: '90%' }
  ].map((s) => ({ label: s.label, reps: s.reps, peso: redondear(peso * s.porcentaje) }));
}

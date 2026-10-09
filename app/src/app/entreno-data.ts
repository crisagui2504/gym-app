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
  | 'gemelos'
  | 'aductores';

export const MUSCLE_LABEL: Record<MuscleId, string> = {
  hombros: 'Hombros',
  pecho: 'Pecho',
  biceps: 'Bíceps',
  antebrazos: 'Antebrazos',
  abdomen: 'Core',
  cuadriceps: 'Cuádriceps',
  trapecios: 'Trapecios',
  dorsales: 'Dorsales',
  triceps: 'Tríceps',
  lumbar: 'Lumbar',
  gluteos: 'Glúteos',
  isquios: 'Isquios',
  gemelos: 'Pantorrillas',
  aductores: 'Aductores'
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

/** Matching de clave con limite de palabra: evita falsos positivos como
 *  'lateral' dentro de 'unilateral' (que clasificaba un jalon como hombro
 *  y ofrecia elevaciones laterales de alternativa). La clave puede ser
 *  multi-palabra; se exige que empiece y termine en frontera de palabra. */
export function contieneClave(texto: string, clave: string): boolean {
  const esc = clave.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // (e?s)? admite el plural de la clave: 'dominada' casa con "Dominadas" y
  // 'encogimiento' con "Encogimientos". Sin esto la frontera de palabra final
  // rechazaba toda forma plural y el ejercicio quedaba sin clasificar.
  return new RegExp(`(^|[^a-z0-9])${esc}(e?s)?([^a-z0-9]|$)`).test(texto);
}

/** Musculos principales de un ejercicio segun su nombre. El primero es el primario. */
export function musculosDe(nombre: string): MuscleId[] {
  const n = norm(nombre);
  const s: MuscleId[] = [];
  const add = (m: MuscleId) => {
    if (!s.includes(m)) s.push(m);
  };
  const tiene = (...claves: string[]) => claves.some((k) => contieneClave(n, k));

  // ===== Casos que DEBEN resolverse antes que las reglas genericas =========
  // Sus nombres contienen una palabra que otra regla reclamaria y acabarian
  // con el musculo primario equivocado (y con alternativas absurdas: unas
  // elevaciones laterales sustituyendo a unas elevaciones de pantorrilla).
  if (tiene('pantorrilla', 'gemelo', 'soleo', 'talon', 'calf')) {
    add('gemelos'); // "Elevacion de Pantorrilla en Prensa": ni hombro ni cuadriceps
    return s;
  }
  if (tiene('nordico')) {
    add('isquios'); // "Curl Nordico" no es un curl de biceps
    add('gluteos');
    return s;
  }
  if (tiene('zancada lateral', 'cossack')) {
    add('aductores'); // aductor en posicion elongada, no hombro
    add('gluteos');
    add('cuadriceps');
    return s;
  }
  if (tiene('sentadilla sumo')) {
    add('aductores');
    add('cuadriceps');
    add('gluteos');
    return s;
  }
  if (tiene('caminata lateral')) {
    add('gluteos'); // gluteo medio, no hombro
    return s;
  }
  if (tiene('fondos en banco')) {
    add('triceps'); // primario el triceps, no el pecho
    add('pecho');
    return s;
  }
  if (tiene('pallof')) {
    add('abdomen'); // anti-rotacion: core, aunque se llame "press"
    return s;
  }

  if (tiene('curl de isquios', 'curl femoral')) {
    add('isquios');
    add('gluteos');
  } else if (tiene('peso muerto sumo')) {
    add('gluteos');
    add('aductores');
    add('isquios');
    add('lumbar');
  } else if (tiene('peso muerto rumano', 'rumano', 'pdr', 'buenos dias', 'isquios', 'femoral')) {
    add('isquios'); // el rumano SI es isquio-primario (cadera, rodilla fija)
    add('gluteos');
    add('lumbar');
  } else if (tiene('peso muerto')) {
    add('gluteos'); // el convencional es gluteo-primario
    add('isquios');
    add('lumbar');
  }
  if (tiene('hip thrust', 'puente de gluteo', 'patada de gluteo')) {
    add('gluteos');
    add('isquios');
  }
  if (tiene('press militar', 'press arnold', 'arnold', 'militar', 'press de hombro', 'press hombro')) {
    add('hombros');
    add('triceps');
  }
  // Acotado a los vuelos de hombro reales: 'elevacion' y 'lateral' a secas
  // capturaban "Elevaciones de Pantorrilla" y "Caminata Lateral".
  if (tiene('elevacion lateral', 'elevaciones laterales', 'elevacion frontal',
            'elevaciones frontales', 'vuelo lateral')) add('hombros');
  if (tiene('face pull', 'pec deck invertido', 'pajaro', 'posterior')) {
    add('hombros');
    add('trapecios');
  }
  if (tiene('press de banca', 'banca', 'press inclinado', 'press plano', 'press pecho',
            'pec deck', 'apertura', 'peck', 'cruce de poleas', 'cruce')) {
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
  // zottman / invertido / muneca = antebrazo de motor (braquiorradial y
  // extensores), aunque el nombre lleve la palabra "curl"
  if (tiene('curl invertido', 'zottman', 'muneca', 'antebrazo')) add('antebrazos');
  if (tiene('martillo')) {
    add('biceps'); // el martillo es braquial/biceps primario; antebrazo secundario
    add('antebrazos');
  }
  if (tiene('curl') && !tiene('isquios', 'femoral')) add('biceps');
  if (tiene('triceps', 'press frances', 'frances', 'copa', 'patada de triceps', 'press cerrado', 'close grip')) add('triceps');
  if (tiene('sentadilla', 'prensa', 'hack', 'zancada', 'bulgara', 'split', 'step up', 'subida al cajon',
            'extension de cuadriceps', 'extensiones de cuadriceps', 'cuadriceps')) {
    add('cuadriceps');
    add('gluteos');
  }
  if (tiene('lumbar', 'hiperextension', 'extensiones lumbares', 'extension lumbar')) add('lumbar');
  if (tiene('pantorrilla', 'gemelo', 'soleo', 'talon', 'calf')) add('gemelos');
  if (tiene('plancha', 'crunch', 'abdominal', 'rueda', 'ab wheel', 'elevaciones de piernas', 'elevacion de piernas', 'oblicuo', 'core')) {
    add('abdomen');
  }
  if (tiene('abduccion', 'abductor', 'caminata lateral')) add('gluteos');
  if (tiene('aduccion', 'aductor')) add('aductores');
  if (tiene('patada de gluteo', 'kickback', 'puente de gluteo')) {
    add('gluteos');
    add('isquios');
  }
  if (tiene('rotacion externa', 'cubanos', 'manguito')) add('hombros');
  if (tiene('farmer', 'pinzamiento', 'agarre')) add('antebrazos');

  return s;
}

// ===== Catalogo de ejercicios comunes por musculo primario (sin imagenes) =====
// `grupo` = funcion del ejercicio (patron de movimiento / rol). Las alternativas
// se buscan por grupo, NO por musculo: unas elevaciones laterales no sustituyen
// a un press militar aunque ambos sean "hombro".
type GrupoFn =
  | 'empuje_h' | 'empuje_v' | 'tiron_h' | 'tiron_v'
  | 'rodilla' | 'cadera' | 'aisl_cuadriceps' | 'aisl_isquios'
  | 'hombro_lat' | 'hombro_post' | 'aisl_pecho'
  | 'biceps' | 'triceps' | 'trapecio' | 'core' | 'antebrazo'
  | 'abductor' | 'aductor' | 'gluteo' | 'rotadores';

interface CatItem {
  nombre: string;
  muscle: MuscleId;
  grupo: GrupoFn;
  claves: string[];
}

// Ordenado de mas especifico a mas generico.
const CATALOGO: CatItem[] = [
  // Pecho
  { nombre: 'Press Inclinado con Mancuernas', muscle: 'pecho', grupo: 'empuje_h', claves: ['press inclinado', 'inclinado'] },
  { nombre: 'Aperturas en Maquina (Pec Deck)', muscle: 'pecho', grupo: 'aisl_pecho', claves: ['pec deck', 'apertura', 'aperturas', 'peck'] },
  { nombre: 'Cruce de Poleas', muscle: 'pecho', grupo: 'aisl_pecho', claves: ['cruce de poleas', 'crossover'] },
  { nombre: 'Press de Banca con Barra', muscle: 'pecho', grupo: 'empuje_h', claves: ['press de banca', 'banca'] },
  { nombre: 'Press con Mancuernas', muscle: 'pecho', grupo: 'empuje_h', claves: ['press con mancuernas', 'press plano', 'fondos en paralelas', 'press pecho'] },
  // Hombros
  { nombre: 'Face Pull / Pajaros', muscle: 'hombros', grupo: 'hombro_post', claves: ['face pull', 'pajaro', 'pec deck invertido', 'posterior'] },
  { nombre: 'Press Militar con Mancuernas', muscle: 'hombros', grupo: 'empuje_v', claves: ['press militar', 'militar', 'arnold', 'press de hombro'] },
  { nombre: 'Elevaciones Laterales', muscle: 'hombros', grupo: 'hombro_lat', claves: ['elevacion', 'elevaciones', 'lateral'] },
  { nombre: 'Press de Hombro en Maquina', muscle: 'hombros', grupo: 'empuje_v', claves: ['hombro en maquina'] },
  // Dorsales
  { nombre: 'Remo Sentado en Polea', muscle: 'dorsales', grupo: 'tiron_h', claves: ['remo en polea', 'remo sentado', 'gironda', 'polea baja'] },
  { nombre: 'Jalon al Pecho / Dominadas', muscle: 'dorsales', grupo: 'tiron_v', claves: ['jalon', 'dominada'] },
  { nombre: 'Remo con Barra', muscle: 'dorsales', grupo: 'tiron_h', claves: ['remo'] },
  { nombre: 'Remo en Maquina (T-Bar)', muscle: 'dorsales', grupo: 'tiron_h', claves: ['t-bar', 'remo t', 'remo en punta'] },
  // Triceps
  { nombre: 'Extension de Triceps en Polea', muscle: 'triceps', grupo: 'triceps', claves: ['extension triceps', 'extension de triceps', 'triceps', 'frances', 'patada de triceps'] },
  { nombre: 'Fondos en Banco', muscle: 'triceps', grupo: 'triceps', claves: ['fondos', 'dips'] },
  { nombre: 'Press Cerrado', muscle: 'triceps', grupo: 'triceps', claves: ['press cerrado', 'close grip'] },
  // Biceps
  { nombre: 'Curl Martillo', muscle: 'biceps', grupo: 'biceps', claves: ['martillo'] },
  { nombre: 'Curl con Barra', muscle: 'biceps', grupo: 'biceps', claves: ['curl con barra', 'curl ez', 'barra ez', 'curl de biceps'] },
  { nombre: 'Curl con Mancuernas', muscle: 'biceps', grupo: 'biceps', claves: ['curl con mancuernas', 'curl alterno', 'curl polea', 'curl concentrado'] },
  { nombre: 'Curl Predicador', muscle: 'biceps', grupo: 'biceps', claves: ['predicador', 'preacher'] },
  // Cuadriceps
  { nombre: 'Zancadas Caminando', muscle: 'cuadriceps', grupo: 'rodilla', claves: ['zancada', 'bulgara', 'split', 'step up'] },
  { nombre: 'Sentadilla Hack en Maquina', muscle: 'cuadriceps', grupo: 'rodilla', claves: ['hack'] },
  { nombre: 'Prensa de Piernas', muscle: 'cuadriceps', grupo: 'rodilla', claves: ['prensa'] },
  { nombre: 'Extension de Cuadriceps', muscle: 'cuadriceps', grupo: 'aisl_cuadriceps', claves: ['extension de cuadriceps', 'extensiones de cuadriceps'] },
  { nombre: 'Sentadilla con Barra', muscle: 'cuadriceps', grupo: 'rodilla', claves: ['sentadilla', 'frontal', 'cuadriceps', 'goblet'] },
  // Isquios
  { nombre: 'Curl de Isquios en Maquina', muscle: 'isquios', grupo: 'aisl_isquios', claves: ['curl de isquios', 'curl femoral', 'isquios', 'femoral'] },
  { nombre: 'Peso Muerto Rumano', muscle: 'isquios', grupo: 'cadera', claves: ['rumano', 'pdr', 'buenos dias', 'peso muerto'] },
  // Gluteos
  { nombre: 'Hip Thrust', muscle: 'gluteos', grupo: 'cadera', claves: ['hip thrust', 'puente'] },
  // Abductor / gluteo medio
  { nombre: 'Abduccion de Cadera en Maquina', muscle: 'gluteos', grupo: 'abductor', claves: ['abduccion', 'abductor'] },
  { nombre: 'Caminata Lateral con Banda', muscle: 'gluteos', grupo: 'abductor', claves: ['caminata lateral', 'monster walk'] },
  // Aductor
  { nombre: 'Aduccion de Cadera en Maquina', muscle: 'aductores', grupo: 'aductor', claves: ['aduccion', 'aductor'] },
  // Gluteo aislado
  { nombre: 'Patada de Gluteo en Polea', muscle: 'gluteos', grupo: 'gluteo', claves: ['patada de gluteo', 'kickback'] },
  { nombre: 'Puente de Gluteo a 1 Pierna', muscle: 'gluteos', grupo: 'gluteo', claves: ['puente de gluteo'] },
  // Rotadores / manguito
  { nombre: 'Rotacion Externa en Polea', muscle: 'hombros', grupo: 'rotadores', claves: ['rotacion externa'] },
  { nombre: 'Cubanos con Mancuernas', muscle: 'hombros', grupo: 'rotadores', claves: ['cubanos', 'manguito'] },
  // Trapecios
  { nombre: 'Encogimientos', muscle: 'trapecios', grupo: 'trapecio', claves: ['encogimiento', 'shrug', 'trapecio'] },
  // Abdomen
  { nombre: 'Elevaciones de Piernas', muscle: 'abdomen', grupo: 'core', claves: ['elevaciones de piernas', 'elevacion de piernas', 'colgado'] },
  { nombre: 'Crunch / Plancha', muscle: 'abdomen', grupo: 'core', claves: ['crunch', 'abdominal', 'plancha', 'rueda', 'oblicuo'] },
  // Lumbar
  { nombre: 'Hiperextensiones', muscle: 'lumbar', grupo: 'cadera', claves: ['lumbar', 'hiperextension', 'extensiones lumbares'] },
  // Antebrazos
  { nombre: 'Curl con Cuerda', muscle: 'antebrazos', grupo: 'antebrazo', claves: ['antebrazo', 'muneca', 'curl invertido', 'farmer'] }
];

export interface Alternativa {
  nombre: string;
  musculos: MuscleId[];
}

/** Grupo funcional de un ejercicio del plan (por sus claves). */
function grupoDe(nombre: string): GrupoFn | null {
  const n = norm(nombre);
  for (const c of CATALOGO) {
    if (c.claves.some((k) => contieneClave(n, k))) return c.grupo;
  }
  return null;
}

/** Alternativas REALES: mismo patron de movimiento / misma funcion.
 *  Solo si no hay ninguna del mismo patron, cae al mismo musculo primario. */
export function alternativasDe(nombre: string): Alternativa[] {
  const objetivo = norm(nombre);
  const grupo = grupoDe(nombre);
  const map = (items: CatItem[]) =>
    items.map((c) => ({ nombre: c.nombre, musculos: musculosDe(c.nombre) }));

  if (grupo) {
    const filtradas = CATALOGO.filter((c) => c.grupo === grupo && norm(c.nombre) !== objetivo);
    if (filtradas.length) return map(filtradas);
  }
  const primario = musculosDe(nombre)[0];
  if (!primario) return [];
  return map(CATALOGO.filter((c) => c.muscle === primario && norm(c.nombre) !== objetivo));
}

// ===== Medida del ejercicio (que campos mostrar y con que unidad) =====
export interface Medida {
  peso: boolean;                                          // mostrar campo de peso
  cuenta: { label: string; unidad: string; paso: number; def: number } | null; // campo de conteo
  rpe: boolean;                                           // mostrar RPE
  nota: string;                                           // ayuda contextual
  objetivo: string;                                       // texto de objetivo si el plan no trae rango
  cardio: boolean;                                        // para ocultar musculos/alternativas
}

/**
 * Clasifica un ejercicio por lo que realmente se mide.
 * El diseno de la tarjeta se adapta a esto (no al reves).
 */
export function medidaDe(nombre: string, bloque: string | null): Medida {
  const n = norm(nombre);
  const b = norm(bloque || '');

  // --- Deporte (basquet, futbol...): minutos, sin peso ni RPE. Red de
  // seguridad: si alguna vista llega a dibujarlo como tarjeta, que no pida
  // registrar kilos ni RPE de una serie de basquet.
  if (b.startsWith('deporte')) {
    return {
      peso: false, rpe: false, cardio: true,
      cuenta: { label: 'Minutos', unidad: 'min', paso: 15, def: 90 },
      nota: '🏀 Tu deporte ya es el acondicionamiento: no hace falta cardio extra.',
      objetivo: '90 min'
    };
  }

  // --- Cardio: minutos en Zona 2 ---
  if (b.startsWith('cardio') || /(eliptica|bicicleta|bici|caminata|cinta|trotadora|remo ergometro|escaladora|spinning)/.test(n)) {
    return {
      peso: false, rpe: false, cardio: true,
      cuenta: { label: 'Minutos', unidad: 'min', paso: 5, def: 40 },
      nota: '🫀 Zona 2 · ritmo conversacional: puedes hablar sin ahogarte.',
      objetivo: '35-45 min'
    };
  }

  // --- Plancha / isometricos: tiempo (segundos), sin peso ni RPE ---
  if (/(plancha|hollow|isometric|vacio abdominal|hueco)/.test(n)) {
    return {
      peso: false, rpe: false, cardio: false,
      cuenta: { label: 'Segundos', unidad: 'seg', paso: 5, def: 30 },
      nota: 'Manten la posicion firme. Al fallo (minimo 30 seg).',
      objetivo: 'al fallo'
    };
  }

  // --- Paseos / carries: distancia (metros) con peso ---
  if (/(farmer|paseo del granjero|carry|caminata del granjero|sentadilla en copa caminando)/.test(n)) {
    return {
      peso: true, rpe: false, cardio: false,
      cuenta: { label: 'Metros', unidad: 'm', paso: 5, def: 30 },
      nota: 'Camina con el peso, agarre firme y core apretado.',
      objetivo: '30-40 m'
    };
  }

  // --- Pinzamiento de disco: tiempo de sosten con peso ---
  if (/(pinzamiento|pinch|sosten de disco|agarre de disco)/.test(n)) {
    return {
      peso: true, rpe: false, cardio: false,
      cuenta: { label: 'Segundos', unidad: 'seg', paso: 5, def: 20 },
      nota: 'Sosten el disco con los dedos (4 + pulgar).',
      objetivo: '20-30 seg'
    };
  }

  // --- Rodillo de muneca: rondas, sin peso ni RPE ---
  if (/(rodillo|wrist roller|enrollar)/.test(n)) {
    return {
      peso: false, rpe: false, cardio: false,
      cuenta: { label: 'Rondas', unidad: 'rondas', paso: 1, def: 3 },
      nota: 'Sube y baja el peso enrollando la cuerda. Sin parar.',
      objetivo: '3 series'
    };
  }

  // --- Core / abdominales: reps (peso solo si lleva carga), sin RPE ---
  const esCore = b.startsWith('core') ||
    /(crunch|abdominal|elevaciones de piernas|elevacion de piernas|rueda|ab wheel|oblicuo|encogimiento abdominal|colgado)/.test(n);
  if (esCore) {
    return {
      peso: /(polea|cable|disco|con peso|mancuern|lastrad)/.test(n),
      rpe: false, cardio: false,
      cuenta: { label: 'Reps', unidad: 'reps', paso: 1, def: 15 },
      nota: '',
      objetivo: 'al fallo'
    };
  }

  // --- Por defecto: fuerza (peso + reps + RPE) ---
  return {
    peso: true, rpe: true, cardio: false,
    cuenta: { label: 'Reps', unidad: 'reps', paso: 1, def: 10 },
    nota: '',
    objetivo: 'al fallo'
  };
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
  // RPE 5 = "me sobraban 5 o mas": el motor sube un escalon grande (+15%) y
  // pide una serie de calibracion. Sin esta opcion, una carga ridicula se
  // marcaba como 6 y el motor subia de 2.5 en 2.5 durante semanas.
  if (rpe <= 5) return 'muy facil · 5+ reps en reserva';
  if (rpe === 6) return 'facil · ~4 reps en reserva';
  if (rpe === 7) return 'comodo · 3 en reserva';
  if (rpe === 8) return 'exigente · 2 en reserva';
  if (rpe === 9) return 'casi al limite · 1 en reserva';
  return 'al fallo · 0 en reserva';
}

/** RPE objetivo de una serie segun su tecnica. Tiene que decir LO MISMO que el
 *  motor: el peso de las series de trabajo (bloques B y C) solo sube si se
 *  cierran a RPE <= 8, asi que se pide RIR 2-3 (RPE 7-8). Antes este texto decia
 *  "RPE 8-9 · deja 1-2 reps": el motor se corrigio en la tanda BJ pero el movil
 *  seguia empujando a la zona que bloquea la progresion. El Top Set admite
 *  RPE <= 9 en el motor, por eso conserva su objetivo. El fallo solo va en la
 *  ultima serie de las tecnicas de intensidad (AMRAP / Rest-Pause / Drop, S3-S4). */
export function rpeObjetivoDe(tecnica: string | null, ultimaSerie: boolean): string {
  const t = norm(tecnica ?? '');
  if (ultimaSerie && (t.includes('amrap') || t.includes('rest') || t.includes('drop'))) {
    return 'al fallo (RPE 10)';
  }
  if (t.includes('top set')) return 'RPE 8-9';
  if (t.includes('back')) return 'RPE 7-8';
  return 'RPE 7-8 · deja 2-3 reps';
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
    case 'AMRAP': // compuestos del Bloque B: >= 2 min entre series
      return 120;
    case 'Drop Set':
    case 'Rest-Pause':
      return 90;
    case 'Superserie':
      return 60;
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
  // Los dias de PPL se llaman en ingles ("Legs A", "Push B", "Pull A"): sin estas
  // claves los seis caian en el calentamiento GENERICO, y un "Legs A" con sentadilla
  // pesada no proponia movilidad de tobillo ni cadera. Pierna va antes que torso
  // ("Pierna Bombeo" contiene "bombeo", que es clave de torso).
  if (['pierna', 'legs', 'cuadriceps', 'isquios', 'gluteo'].some((k) => n.includes(k))) return CAL_PIERNA;
  if (['torso', 'push', 'pull', 'hombro', 'pecho', 'espalda', 'bombeo'].some((k) => n.includes(k))) return CAL_TORSO;
  return CAL_GENERAL;
}

function redondear(valor: number, paso = 2.5): number {
  return Math.max(paso, Math.round(valor / paso) * paso);
}

/** Series de aproximacion progresivas a partir del peso objetivo.
 *  En cargas altas (>80 kg) inserta escalones extra para que ningun salto
 *  supere ~15 kg: acercarse al maximo debe ser gradual, no un salto brusco
 *  que asuste al sistema nervioso antes del Top Set. */
export function seriesAproximacion(peso: number): Array<{ label: string; peso: number; reps: number }> {
  if (!peso || peso < 10) return [];
  // Cargas moderadas: rampa clasica 50 / 70 / 90 %.
  if (peso <= 80) {
    return [
      { frac: 0.5, reps: 10 },
      { frac: 0.7, reps: 5 },
      { frac: 0.9, reps: 2 }
    ].map((s) => ({ label: Math.round(s.frac * 100) + '%', reps: s.reps, peso: redondear(peso * s.frac) }));
  }
  // Cargas altas: tantos escalones como haga falta para que el salto entre
  // series (incluido el ultimo hacia el peso objetivo) no pase de ~15 kg.
  // Tope de 8 escalones (cubre saltos <=15 kg hasta ~240 kg objetivo).
  const saltoMax = 15;
  const n = Math.min(8, Math.max(3, Math.ceil((peso * 0.5) / saltoMax)));
  const reps = [12, 10, 8, 5, 4, 3, 2, 2];
  const sets: Array<{ label: string; peso: number; reps: number }> = [];
  for (let i = 0; i < n; i++) {
    const frac = 0.5 + (0.5 * i) / n; // 50 % .. justo por debajo de 100 %
    sets.push({ label: Math.round(frac * 100) + '%', reps: reps[i], peso: redondear(peso * frac) });
  }
  return sets;
}

// ── Calculadora de discos ────────────────────────────────────────────────────
// El peso de un ejercicio con barra es el TOTAL cargado (barra incluida), igual
// que lo sugiere el motor (estimar_peso nunca baja de la barra vacia). Discos
// estandar de gimnasio; con 1.25 como el mas chico, el salto minimo real de una
// barra es 2.5 kg (1.25 por lado).
export const DISCOS_KG = [25, 20, 15, 10, 5, 2.5, 1.25];

/** Peso de la barra si el ejercicio se carga con discos en una barra; null si no.
 *  "Extension Triceps Polea Barra" es una polea (agarre de barra), no se carga. */
export function barraDe(nombre: string): number | null {
  const n = norm(nombre);
  if (contieneClave(n, 'polea') || contieneClave(n, 'maquina') || contieneClave(n, 'smith')) return null;
  if (contieneClave(n, 't-bar') || contieneClave(n, 'en punta')) return null; // landmine: solo discos
  // curls de muneca: barra ligera o mancuerna (extensores = epicondilitis, carga ligera)
  if (n.includes('muneca')) return null;
  if (contieneClave(n, 'ez')) return 10;
  if (contieneClave(n, 'barra') || contieneClave(n, 'peso muerto convencional')) return 20;
  return null;
}

export interface Carga {
  porLado: number[];   // discos de UN lado, de mayor a menor
  total: number;       // lo que realmente queda cargado
  exacto: boolean;     // false: el objetivo no es cargable y se muestra el mas cercano por debajo
}

/** Discos por lado para llegar a `objetivo` (total con barra). Voraz: con este
 *  juego de discos siempre llega al multiplo de 2.5 inferior mas cercano. */
export function discosPorLado(objetivo: number, barra: number): Carga | null {
  if (!objetivo || objetivo <= barra) return null;
  let lado = Math.floor(((objetivo - barra) / 2) * 100 + 1e-6) / 100;
  const porLado: number[] = [];
  for (const d of DISCOS_KG) {
    while (lado + 1e-6 >= d) {
      porLado.push(d);
      lado = Math.round((lado - d) * 100) / 100;
    }
  }
  const total = Math.round((barra + 2 * porLado.reduce((a, b) => a + b, 0)) * 100) / 100;
  return { porLado, total, exacto: Math.abs(total - objetivo) < 0.01 };
}

/** "20 + 5 + 1.25" (cada disco, un lado). */
export function textoDiscos(c: Carga): string {
  return c.porLado.map((d) => String(d)).join(' + ');
}

// ── Mapa de recuperacion muscular (estilo Fitbod) ────────────────────────────
// Estimacion simple y explicable, no una medicion: cada serie reciente suma
// fatiga al musculo (principal 1, secundarios 0.5; mas cerca del fallo, mas
// fatiga) y esa fatiga se desvanece en linea recta en 48 h (musculos chicos) o
// 72 h (grandes), que es el rango en que la sintesis proteica y el dano vuelven
// a la base tras una sesion dura. ~6 series duras = musculo "agotado".
const GRANDES: MuscleId[] = ['pecho', 'dorsales', 'cuadriceps', 'isquios', 'gluteos', 'lumbar'];
const SERIES_AGOTADO = 6;

export interface SerieReciente {
  fecha: string;      // YYYY-MM-DD
  ejercicio: string;
  rpe: number;
}

function horasDesde(fecha: string, ahora: Date): number {
  // sin hora en el registro: se asume que entrenaste a las 18:00 de ese dia
  const [y, m, d] = fecha.slice(0, 10).split('-').map(Number);
  return (ahora.getTime() - new Date(y, m - 1, d, 18).getTime()) / 3600000;
}

function factorEsfuerzo(rpe: number): number {
  return rpe >= 9 ? 1.2 : rpe >= 8 ? 1 : rpe >= 7 ? 0.8 : 0.5;
}

/** Fatiga 0..1 por musculo. `deporte`: fechas de partidos (basquet, futbol):
 *  cargan gemelos, cuadriceps y gluteos como ~4/3/2 series duras. */
export function fatigaMuscular(series: SerieReciente[], ahora: Date, deporte: string[] = []): Partial<Record<MuscleId, number>> {
  const total: Partial<Record<MuscleId, number>> = {};
  const sumar = (m: MuscleId, carga: number, horas: number) => {
    const T = GRANDES.includes(m) ? 72 : 48;
    if (horas < 0 || horas >= T) return;
    total[m] = (total[m] ?? 0) + carga * (1 - horas / T);
  };
  for (const s of series) {
    const h = horasDesde(s.fecha, ahora);
    const f = factorEsfuerzo(Number(s.rpe) || 0);
    musculosDe(s.ejercicio).forEach((m, i) => sumar(m, (i === 0 ? 1 : 0.5) * f, h));
  }
  for (const fecha of deporte) {
    const h = horasDesde(fecha, ahora);
    sumar('gemelos', 4, h);
    sumar('cuadriceps', 3, h);
    sumar('gluteos', 2, h);
  }
  const out: Partial<Record<MuscleId, number>> = {};
  for (const [m, v] of Object.entries(total) as [MuscleId, number][]) {
    out[m] = Math.min(1, v / SERIES_AGOTADO);
  }
  return out;
}

// ── Autorregulacion dentro de la sesion (estilo Juggernaut AI) ───────────────
// Tras completar una serie, si el RPE real se aleja del objetivo, se corrige el
// peso de las SIGUIENTES series del ejercicio en lugar de esperar a la semana
// que viene. Conservador: solo con desvios claros (2+ puntos de RPE, o fallo
// antes del minimo del rango) y nunca en series al fallo / drop / rest-pause.
export interface AjusteIntra {
  peso: number;
  motivo: string;
  sube: boolean;
}

/** Numero maximo del objetivo de RPE ("RPE 7-8 · deja 2-3 reps" -> 8). */
export function rpeMaxDe(objetivo: string): number | null {
  const m = objetivo.match(/RPE (\d+)(?:-(\d+))?/);
  return m ? Number(m[2] ?? m[1]) : null;
}

/** Salto de carga REAL que se puede hacer con ese equipo (kg del valor registrado).
 *  Igual que paso_carga() del motor: barra 2.5 (1.25 por lado); maquina / polea
 *  2.5; mancuernas (peso TOTAL de las dos) de 1 en 1 kg por mano hasta 10 kg y de
 *  2.5 por mano despues; a una mano se registra una sola. */
export function pasoCarga(nombre: string, peso = 0): number {
  const n = norm(nombre);
  if (barraDe(nombre)) return 2.5;
  if (contieneClave(n, 'mancuerna')) {
    const manos = /1 mano|una mano|unilateral/.test(n) ? 1 : 2;
    return manos * (peso > 0 && peso / manos < 10 ? 1 : 2.5);
  }
  return 2.5;
}

export function ajusteIntraSesion(o: {
  peso: number; reps: number; rpe: number; repsMin: number | null; repsMax: number | null;
  rpeObjetivoMax: number | null; tecnica: string | null; alFallo: boolean; barra: number | null; paso: number;
}): AjusteIntra | null {
  const t = norm(o.tecnica ?? '');
  if (o.alFallo || !o.peso || o.peso <= 0 || !o.rpe || o.rpeObjetivoMax == null) return null;
  if (t.includes('amrap') || t.includes('drop') || t.includes('rest')) return null;
  const paso = o.paso;
  // se mueve en saltos ENTEROS desde el peso real (no se redondea a una rejilla:
  // 22.5 + un salto de 5 es 27.5, no 30); ~5% o ~10%, minimo un salto
  const saltos = (frac: number) => Math.max(1, Math.round((o.peso * frac) / paso));
  const r2 = (v: number) => Math.round(v * 100) / 100;
  const facil = o.rpe <= o.rpeObjetivoMax - 2 && o.repsMax != null && o.reps >= o.repsMax;
  const muyDuro = (o.rpe >= 10 && o.repsMin != null && o.reps < o.repsMin) || o.rpe >= o.rpeObjetivoMax + 2;
  if (facil) {
    const nuevo = r2(o.peso + saltos(0.05) * paso);
    return nuevo > o.peso ? { peso: nuevo, sube: true, motivo: `RPE ${o.rpe} con el rango completo: sobraba` } : null;
  }
  if (muyDuro) {
    const frac = o.rpe >= 10 && o.repsMin != null && o.reps < o.repsMin ? 0.1 : 0.05;
    const nuevo = r2(Math.max(o.barra ?? paso, o.peso - saltos(frac) * paso));
    return nuevo < o.peso ? { peso: nuevo, sube: false, motivo: `RPE ${o.rpe}${o.repsMin != null && o.reps < o.repsMin ? ' sin llegar al minimo' : ''}: demasiado` } : null;
  }
  return null;
}

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { EjercicioPlan, FeedbackItem, RutinaApiService, SerieHistorial, SeriePayload } from './rutina-api.service';
import { MuscleMapComponent } from './muscle-map.component';
import { AcentosPipe } from './acentos';
import * as almacen from './almacen';
import { environment } from '../environments/environment';
import {
  ajusteIntraSesion,
  Alternativa,
  barraDe,
  Calentamiento,
  Carga,
  discosPorLado,
  MUSCLE_LABEL,
  MuscleId,
  Tecnica,
  alternativasDe,
  calentamientoDe,
  descansoPorTecnica,
  explicacionTecnica,
  fatigaMuscular,
  fechaLocal,
  Medida,
  medidaDe,
  musculosDe,
  norm,
  nSeriesDe,
  pasoCarga,
  RPE_INFO,
  rpeMaxDe,
  rpeObjetivoDe,
  rpeSignificado,
  seriesAproximacion,
  textoDiscos
} from './entreno-data';

interface SerieVM {
  planId: number;        // fila del plan a la que pertenece esta serie
  numeroSerie: number;   // indice dentro de su fila (1-based)
  tecnica: string | null;
  etiqueta: string;      // "Top Set", "Back-off", "Al fallo (AMRAP)", "Serie N"
  alFallo: boolean;
  descanso: number;      // segundos de descanso de esta serie
  repsObjetivo: string;  // "6-8" para mostrar de guia
  reps: number;
  peso: number;
  rpe: number;
  hecho: boolean;
  abierta: boolean;      // desplegada a mano para editarla (si no, solo la activa lo esta)
  repsMin: number | null;
  repsMax: number | null;
  manual: boolean;       // el usuario toco el peso: la autorregulacion ya no lo cambia
}

type EntrenoPendiente = { fecha: string; items: SeriePayload[] };
type FeedbackPendiente = { fecha: string; items: FeedbackItem[] };

/** Foto del entreno EN CURSO (lo que ya marcaste antes de pulsar Guardar). */
interface EnCurso {
  fecha: string;
  sesion: number;
  cards: Array<{
    plan: number;            // planId de la primera serie: identifica la tarjeta
    ejercicio: string;       // puede ser una alternativa elegida en el gym
    miNota: string;
    series: Array<{ planId: number; numeroSerie: number; peso: number; reps: number; rpe: number; hecho: boolean; manual: boolean }>;
  }>;
}

/** Resumen que se muestra al guardar el entreno. */
interface Resumen {
  series: number;
  volumen: number;              // kg x reps de las series hechas (sin las asistidas)
  minutos: number | null;
  prs: string[];
  cambioVolumen: number | null; // vs la ultima vez de ESOS ejercicios (fraccion: 0.08 = +8%)
  comparando: boolean;          // esperando el historial del servidor
  sinConexion: boolean;
  ejercicios: Array<{ nombre: string; volumen: number; e1rm: number; cambioE1rm: number | null; cambioVolumen: number | null }>;
}

interface EjercicioVM {
  ejercicio: string;
  nombre_dia: string;
  bloque: string | null;
  medida: Medida;        // que campos/unidades mostrar (se adapta al ejercicio)
  musculos: MuscleId[];
  tecnicas: string[];    // tecnicas distintas (para los chips)
  series: SerieVM[];     // todas las series del ejercicio, juntas
  mostrarAlt: boolean;
  alternativas: Alternativa[];
  barra: number | null;  // kg de la barra si se carga con discos (calculadora); null si no
  notasMotor: string[];  // lo que explica el motor (de donde sale el peso, por que no subio...)
  verNotas: boolean;     // notas del motor desplegadas
  miNota: string;        // nota propia ("asiento en 4"): se guarda y reaparece la proxima vez
  aviso: { texto: string; sube: boolean } | null; // ajuste automatico de las series siguientes
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, MuscleMapComponent, AcentosPipe],
  templateUrl: './app.component.html'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly api = inject(RutinaApiService);

  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly mensaje = signal('');
  // Blindaje del guardado: cola offline + no duplicar el envio del dia
  readonly pendientes = signal(0);
  readonly reintentando = signal(false);
  readonly yaGuardadoHoy = signal(false);
  readonly modoOffline = signal(false);
  private readonly onOnline = () => {
    this.reenviarPendientes();
    this.reenviarFeedback();
  };
  readonly fecha = fechaLocal();
  readonly nombreDia = signal('Rutina de hoy');
  readonly ejercicios = signal<EjercicioVM[]>([]);
  readonly rpeValores = [5, 6, 7, 8, 9, 10];
  readonly etiquetas = MUSCLE_LABEL;

  readonly tema = signal<'light' | 'dark'>('dark');
  // Avisos push: 'on' suscrito, 'off' no, 'instalar' = iPhone sin instalar la app
  // (Safari solo da push a apps en la pantalla de inicio), 'no' = sin soporte.
  readonly avisos = signal<'on' | 'off' | 'instalar' | 'no'>('off');
  readonly cambiandoAvisos = signal(false);
  readonly racha = signal(0);
  readonly mostrarCalentamiento = signal(false);

  // Readiness: como llegas hoy -> modula el objetivo de RPE del dia
  readonly readiness = signal<'bien' | 'normal' | 'baja' | null>(null);
  readonly sueno = signal<1 | 2 | 3 | null>(null);   // 1 bien | 2 regular | 3 mal

  // ----- Encuesta de la sesion (el motor ajusta el volumen con esto) -----
  /** Musculos PRINCIPALES de hoy (el primero de cada ejercicio de pesas). */
  readonly musculosHoy = computed<MuscleId[]>(() => {
    const out: MuscleId[] = [];
    for (const e of this.ejercicios()) {
      const m = e.musculos[0];
      if (!e.medida.cardio && e.medida.rpe && m && !out.includes(m)) out.push(m);
    }
    return out;
  });
  readonly agujetas = signal<Partial<Record<MuscleId, number>>>({});
  readonly mostrarEncuesta = signal(false);
  readonly resumen = signal<Resumen | null>(null);
  readonly encBombeo = signal<Partial<Record<MuscleId, number>>>({});
  readonly encCarga = signal<Partial<Record<MuscleId, number>>>({});
  readonly encDolor = signal<string[]>([]);
  readonly opcionesAgujetas = [
    { v: 1, t: 'Nada' }, { v: 2, t: 'Un poco' }, { v: 3, t: 'Todavía duele' }
  ];
  readonly opcionesBombeo = [{ v: 1, t: 'Poco' }, { v: 2, t: 'Bueno' }, { v: 3, t: 'Brutal' }];
  readonly opcionesCarga = [{ v: 1, t: 'Fácil' }, { v: 2, t: 'Justa' }, { v: 3, t: 'Demasiado' }];

  // Mapa de recuperacion (dias de descanso y de deporte)
  readonly recuperacion = signal<{
    niveles: Partial<Record<MuscleId, number>>;
    cargados: string[];
    medios: string[];
    listos: string[];
  } | null>(null);

  // "Usar siempre": reemplazo (normalizado) -> ejercicio original del plan
  readonly preferencias = signal<Record<string, string>>({});

  // Ultima nota propia por ejercicio (clave normalizada). Cacheada en el
  // telefono para que aparezca tambien sin conexion.
  private notasUsuario: Record<string, string> = {};

  // Historial (ultimas sesiones, desde el servidor)
  readonly mostrarHistorial = signal(false);
  readonly cargandoHistorial = signal(false);
  readonly historial = signal<Array<{ fecha: string; items: Array<{ ejercicio: string; mejor: string }> }>>([]);

  // ----- Reprogramar la semana (mover el dia de descanso) -----
  readonly diasLabel = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'];
  readonly mostrarSemana = signal(false);
  readonly cargandoSemana = signal(false);
  readonly semana = signal<{ cal: number; sesion: number; nombre: string; descanso: boolean; deporte: boolean; hoy: boolean }[]>([]);
  private nombresSesion: string[] = [];
  private bloquesSesion: string[] = [];
  readonly esDiaDescanso = computed(() => /descanso/i.test(this.nombreDia()));
  /** Dia de DEPORTE (basquet, futbol...): no es gym ni descanso. Se detecta por
   *  el bloque, no por el nombre — el nombre lo pone el usuario en su config.
   *  Sin esto se dibujaba una tarjeta de ejercicio con 1 serie a 0 kg y slider
   *  de RPE pidiendo registrar una serie de basquet (nSeriesDe(0) devuelve 1). */
  readonly esDiaDeporte = computed(() => {
    const e = this.ejercicios();
    return e.length > 0 && e.every((x) => /deporte/i.test(x.bloque || ''));
  });
  readonly calentamiento = computed<Calentamiento>(() => calentamientoDe(this.nombreDia()));
  readonly aproximacion = computed<{ ejercicio: string; barra: number | null; series: ReturnType<typeof seriesAproximacion> } | null>(() => {
    let mejor: EjercicioVM | null = null;
    let maxPeso = 0;
    for (const e of this.ejercicios()) {
      const p = e.series[0]?.peso ?? 0;
      if (p > maxPeso) {
        maxPeso = p;
        mejor = e;
      }
    }
    if (!mejor || maxPeso < 10) return null;
    const series = seriesAproximacion(maxPeso);
    return series.length ? { ejercicio: mejor.ejercicio, barra: mejor.barra, series } : null;
  });

  readonly tecnicaActiva = signal<Tecnica | null>(null);

  // Progreso de la sesion (series completadas / totales) para la barra superior
  readonly progreso = signal<{ hechas: number; total: number; pct: number }>({ hechas: 0, total: 0, pct: 0 });

  private recalcularProgreso(): void {
    let hechas = 0;
    let total = 0;
    for (const e of this.ejercicios()) {
      for (const s of e.series) {
        total++;
        if (s.hecho) hechas++;
      }
    }
    this.progreso.set({ hechas, total, pct: total ? Math.round((hechas / total) * 100) : 0 });
  }

  // Cronometro de descanso
  readonly tmrActivo = signal(false);
  readonly tmrSeg = signal(0);
  readonly tmrTotal = signal(0);
  readonly tmrNombre = signal('');
  readonly tmrTexto = computed(() => {
    const s = this.tmrSeg();
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2, '0')}`;
  });
  readonly tmrPct = computed(() => (this.tmrTotal() ? (this.tmrSeg() / this.tmrTotal()) * 100 : 0));
  private intervalo: ReturnType<typeof setInterval> | null = null;

  // Pantalla siempre encendida mientras hay un entreno en curso (Screen Wake
  // Lock). Sin esto el telefono se bloquea entre series y hay que desbloquearlo
  // para marcar cada una. iPhone: funciona con la app instalada desde iOS 18.4+.
  private wakeLock: WakeLockSentinel | null = null;
  readonly pantallaFija = signal(false);
  private finAt = 0;            // timestamp (ms) en que termina el descanso
  private alarmaSonada = false;
  // recalcula al volver a la app (el setInterval se frena en segundo plano)
  // Colas de envio pendiente: en memoria y persistidas en IndexedDB (almacen.ts)
  private cola: EntrenoPendiente[] = [];
  private colaFb: FeedbackPendiente[] = [];
  private sesionMostrada = 0;
  private guardadoEnCursoProgramado: ReturnType<typeof setTimeout> | null = null;
  private readonly onSalir = () => this.guardarEnCurso(true);

  // ----- iPhone (iOS 26): barra inferior "flotando" tras cerrar el teclado -----
  // Regresion de WebKit: al cerrar el teclado (al escribir un peso) iOS deja el
  // viewport encogido / desplazado y los position:fixed de abajo (barra de
  // acciones, cronometro) quedan a media pantalla. Apple no lo ha arreglado
  // (developer.apple.com/forums/thread/800125). Remedio documentado: forzar que
  // WebKit vuelva a medir el viewport ocultando y mostrando la raiz de la app.
  private alturaMax = window.innerHeight;
  private reparoProgramado: ReturnType<typeof setTimeout> | null = null;
  private readonly onResizeVentana = () => {
    if (window.innerHeight > this.alturaMax) this.alturaMax = window.innerHeight;
  };
  private readonly onFocoEntra = (e: FocusEvent) => {
    if (this.esCampo(e.target)) document.body.classList.add('teclado');
  };
  private readonly onFocoSale = (e: FocusEvent) => {
    if (!this.esCampo(e.target)) return;
    setTimeout(() => {
      if (this.esCampo(document.activeElement)) return; // paso a otro campo: el teclado sigue
      document.body.classList.remove('teclado');
      this.repararViewport();
    }, 150);
  };
  /** El visual viewport quedo corrido sin un campo con foco: tambien se repara. */
  private readonly onViewport = () => {
    if (this.esCampo(document.activeElement)) return;
    if (this.reparoProgramado) clearTimeout(this.reparoProgramado);
    this.reparoProgramado = setTimeout(() => this.repararViewport(), 250);
  };

  private esCampo(t: EventTarget | null): boolean {
    return t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement;
  }

  private repararViewport(): void {
    const vv = window.visualViewport;
    const encogido = this.alturaMax - window.innerHeight > 4;
    const corrido = !!vv && vv.offsetTop > 1;
    if (!encogido && !corrido) return;
    const raiz = document.querySelector('app-root') as HTMLElement | null;
    const x = window.scrollX;
    const y = window.scrollY;
    if (raiz) {
      raiz.style.display = 'none';
      void raiz.offsetHeight; // reflujo sincrono: WebKit vuelve a medir el viewport
      raiz.style.display = '';
    }
    window.scrollTo(x, y);
  }

  private readonly onVisibilidad = () => {
    if (document.hidden) {
      // el sistema puede matar la app en segundo plano: se guarda YA
      this.guardarEnCurso(true);
      return;
    }
    if (this.finAt > 0) this.tick();
    // el sistema suelta el wake lock al salir de la app: se vuelve a pedir
    if (this.entrenoEnCurso()) this.fijarPantalla();
  };

  ngOnInit(): void {
    const guardado = localStorage.getItem('tema');
    this.aplicarTema(guardado === 'light' ? 'light' : 'dark');
    this.cargarRacha();

    this.restaurarTimer();
    document.addEventListener('visibilitychange', this.onVisibilidad);

    // readiness del dia (persiste si recargas la app en el gym)
    const r = localStorage.getItem('readiness-' + this.fecha);
    if (r === 'bien' || r === 'normal' || r === 'baja') this.readiness.set(r);
    const sn = Number(localStorage.getItem('sueno-' + this.fecha));
    if (sn === 1 || sn === 2 || sn === 3) this.sueno.set(sn);
    try {
      this.agujetas.set(JSON.parse(localStorage.getItem('agujetas-' + this.fecha) ?? '{}'));
    } catch {
      /* noop */
    }

    // guardado blindado: colas en IndexedDB y reintento automatico
    this.yaGuardadoHoy.set(localStorage.getItem('ultimoGuardado') === this.fecha);
    window.addEventListener('online', this.onOnline);
    window.addEventListener('pagehide', this.onSalir);
    window.addEventListener('resize', this.onResizeVentana);
    document.addEventListener('focusin', this.onFocoEntra);
    document.addEventListener('focusout', this.onFocoSale);
    window.visualViewport?.addEventListener('resize', this.onViewport);
    this.cargarColas().then(() => {
      this.reenviarPendientes();
      this.reenviarFeedback();
    });

    this.cargarNotas();
    this.cargarPreferencias();
    this.cargarSesion(this.sesionDe(this.weekdayHoy()));
    this.estadoAvisos();
    if (localStorage.getItem('inicio-' + this.fecha)) this.arrancarReloj();
  }

  // ----- Mapa de recuperacion -----
  /** En descanso / deporte: que musculos siguen cargados segun las series de los
   *  ultimos dias (y el partido de hoy o de ayer). Estimacion, no medicion. */
  private cargarRecuperacion(): void {
    this.recuperacion.set(null);
    if (!this.esDiaDescanso() && !this.esDiaDeporte()) return;
    const ayer = new Date();
    ayer.setDate(ayer.getDate() - 1);
    forkJoin([this.api.getHistorial(4), this.api.getRutinaHoy(ayer)]).subscribe({
      next: ([hist, rutAyer]) => {
        const series = (hist.series ?? []).map((s) => ({
          fecha: String(s.fecha_entreno).slice(0, 10),
          ejercicio: s.ejercicio,
          rpe: Number(s.rpe) || 0
        }));
        const deporte: string[] = [];
        if (this.esDiaDeporte()) deporte.push(this.fecha);
        if ((rutAyer.rutina ?? []).some((f) => /deporte/i.test(f.bloque ?? ''))) deporte.push(fechaLocal(ayer));
        const niveles = fatigaMuscular(series, new Date(), deporte);
        const todos = Object.keys(MUSCLE_LABEL) as MuscleId[];
        const de = (min: number, max: number) =>
          todos.filter((m) => (niveles[m] ?? 0) >= min && (niveles[m] ?? 0) < max).map((m) => MUSCLE_LABEL[m]);
        this.recuperacion.set({ niveles, cargados: de(0.6, 2), medios: de(0.25, 0.6), listos: de(0, 0.25) });
      },
      error: () => undefined // sin conexion: simplemente no se muestra
    });
  }

  // ----- Avisos push -----
  private esIosSinInstalar(): boolean {
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const instalada = window.matchMedia?.('(display-mode: standalone)').matches
      || (navigator as unknown as { standalone?: boolean }).standalone === true;
    return ios && !instalada;
  }

  private async estadoAvisos(): Promise<void> {
    if (this.esIosSinInstalar()) return this.avisos.set('instalar');
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      return this.avisos.set('no');
    }
    try {
      const reg = await navigator.serviceWorker.getRegistration();
      const sub = await reg?.pushManager.getSubscription();
      this.avisos.set(sub && Notification.permission === 'granted' ? 'on' : 'off');
    } catch {
      this.avisos.set('off');
    }
  }

  async toggleAvisos(): Promise<void> {
    const estado = this.avisos();
    if (estado === 'instalar') {
      this.mensaje.set('🔔 En iPhone los avisos solo llegan con la app instalada: Compartir → «Agregar a inicio», y actívalos desde ahí.');
      return;
    }
    if (estado === 'no') {
      this.mensaje.set('Este navegador no admite avisos push.');
      return;
    }
    if (this.cambiandoAvisos()) return;
    this.cambiandoAvisos.set(true);
    try {
      const reg = await navigator.serviceWorker.ready;
      if (estado === 'on') {
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          this.api.guardarSuscripcion({ endpoint: sub.endpoint, baja: true }).subscribe({ error: () => undefined });
          await sub.unsubscribe();
        }
        this.avisos.set('off');
        this.mensaje.set('🔕 Avisos desactivados.');
        return;
      }
      const permiso = await Notification.requestPermission();
      if (permiso !== 'granted') {
        this.mensaje.set('Sin permiso de notificaciones: actívalo en los ajustes del navegador para recibir avisos.');
        return;
      }
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.claveVapid(environment.vapidPublica)
      });
      this.api.guardarSuscripcion(sub.toJSON()).subscribe({
        next: () => {
          this.avisos.set('on');
          this.mensaje.set('🔔 Avisos activados: rutina lista el domingo y recordatorio si un día de gym no has registrado.');
        },
        error: () => {
          sub.unsubscribe().catch(() => undefined);
          this.mensaje.set('No se pudo activar los avisos (sin conexión con el servidor). Inténtalo de nuevo.');
        }
      });
    } catch {
      this.mensaje.set('No se pudo activar los avisos en este dispositivo.');
    } finally {
      this.cambiandoAvisos.set(false);
    }
  }

  /** Clave VAPID base64url -> bytes (lo que pide pushManager.subscribe). */
  private claveVapid(b64: string): Uint8Array<ArrayBuffer> {
    const pad = '='.repeat((4 - (b64.length % 4)) % 4);
    const bin = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
    const out = new Uint8Array(new ArrayBuffer(bin.length));
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  /** Notas propias por ejercicio: primero la copia del telefono, luego el servidor. */
  private cargarNotas(): void {
    try {
      this.notasUsuario = JSON.parse(localStorage.getItem('notasEjercicio') ?? '{}');
    } catch {
      this.notasUsuario = {};
    }
    this.api.getNotas().subscribe({
      next: (res) => {
        const m: Record<string, string> = {};
        for (const n of res.notas ?? []) if (n.notas) m[norm(n.ejercicio)] = n.notas;
        this.notasUsuario = m;
        try {
          localStorage.setItem('notasEjercicio', JSON.stringify(m));
        } catch {
          /* noop */
        }
        // si las tarjetas ya estaban pintadas, rellena las notas que falten
        for (const e of this.ejercicios()) if (!e.miNota) e.miNota = m[norm(e.ejercicio)] ?? '';
      },
      error: () => undefined // sin conexion: vale la copia local
    });
  }

  /** Carga la sesion (dia del plan) que corresponde mostrar hoy.
   *  El plan se cachea en el telefono: si el servidor no responde (InfinityFree
   *  caido o sin datos en el gym), se usa la ultima copia descargada. */
  private cargarSesion(sessionWeekday: number): void {
    this.cargando.set(true);
    this.mensaje.set('');
    this.modoOffline.set(false);
    const cacheKey = 'plan-' + fechaLocal(this.fechaDeSesion(sessionWeekday));
    this.api.getRutinaHoy(this.fechaDeSesion(sessionWeekday)).subscribe({
      next: (res) => {
        this.nombreDia.set(res.rutina.length ? res.rutina[0].nombre_dia : 'Descanso');
        this.ejercicios.set(this.agrupar(res.rutina));
        this.sesionMostrada = sessionWeekday;
        this.restaurarEnCurso();
        this.recalcularProgreso();
        this.cargando.set(false);
        this.cargarRecuperacion();
        try {
          localStorage.setItem(cacheKey, JSON.stringify(res.rutina));
        } catch {
          /* almacenamiento lleno: seguimos sin cache */
        }
      },
      error: () => {
        const cache = localStorage.getItem(cacheKey);
        if (cache) {
          try {
            const rutina = JSON.parse(cache) as EjercicioPlan[];
            this.nombreDia.set(rutina.length ? rutina[0].nombre_dia : 'Descanso');
            this.ejercicios.set(this.agrupar(rutina));
            this.sesionMostrada = sessionWeekday;
            this.restaurarEnCurso();
            this.recalcularProgreso();
            this.modoOffline.set(true);
            this.mensaje.set('📡 Sin conexion: mostrando la rutina guardada en el telefono. Puedes entrenar normal; el entreno se sincronizara despues.');
            this.cargando.set(false);
            return;
          } catch {
            /* cache corrupta: cae al mensaje de error */
          }
        }
        this.mensaje.set('No se pudo cargar la rutina. Revisa tu conexion.');
        this.cargando.set(false);
      }
    });
  }

  // ----- Helpers de fechas / semana -----
  private weekdayHoy(): number {
    return ((new Date().getDay() + 6) % 7) + 1; // 1=Lun .. 7=Dom
  }

  private mondayActual(): Date {
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return d;
  }

  private fechaDeSesion(sessionWeekday: number): Date {
    const d = this.mondayActual();
    d.setDate(d.getDate() + (sessionWeekday - 1));
    return d;
  }

  private overrideKey(): string {
    return 'horario-' + fechaLocal(this.mondayActual());
  }

  private cargarOverrideMap(): Record<number, number> {
    try {
      return JSON.parse(localStorage.getItem(this.overrideKey()) || '{}');
    } catch {
      return {};
    }
  }

  /** Sesion del plan (1-7) que se muestra en un dia calendario, con override. */
  sesionDe(cal: number): number {
    const m = this.cargarOverrideMap();
    return m[cal] ?? cal;
  }

  // ----- Panel "Mi semana" -----
  toggleSemana(): void {
    this.mostrarSemana.update((v) => !v);
    if (this.mostrarSemana() && this.nombresSesion.length === 0) {
      this.cargandoSemana.set(true);
      const reqs = [1, 2, 3, 4, 5, 6, 7].map((s) => this.api.getRutinaHoy(this.fechaDeSesion(s)));
      forkJoin(reqs).subscribe({
        next: (arr) => {
          this.nombresSesion = arr.map((r) => (r.rutina[0]?.nombre_dia ?? '—'));
          this.bloquesSesion = arr.map((r) => (r.rutina[0]?.bloque ?? ''));
          this.reconstruirSemana();
          this.cargandoSemana.set(false);
        },
        error: () => {
          this.mensaje.set('No se pudo cargar la semana.');
          this.cargandoSemana.set(false);
        }
      });
    } else if (this.mostrarSemana()) {
      this.reconstruirSemana();
    }
  }

  private reconstruirSemana(): void {
    const hoy = this.weekdayHoy();
    this.semana.set(
      [1, 2, 3, 4, 5, 6, 7].map((cal) => {
        const s = this.sesionDe(cal);
        const nombre = this.nombresSesion[s - 1] ?? '—';
        return {
          cal, sesion: s, nombre,
          descanso: /descanso/i.test(nombre),
          // los dias de deporte son un compromiso fijo (basquet a una hora), no
          // una sesion movible: no se pueden intercambiar con el descanso
          deporte: /deporte/i.test(this.bloquesSesion[s - 1] ?? ''),
          hoy: cal === hoy
        };
      })
    );
  }

  private sesionDescanso(): number {
    const i = this.nombresSesion.findIndex((n) => /descanso/i.test(n));
    return i >= 0 ? i + 1 : 4;
  }

  /** Pone el descanso en este dia calendario, intercambiando con el dia de descanso actual. */
  descansarEn(cal: number): void {
    // Un dia de deporte no se intercambia: el basquet es a una hora fija en el
    // mundo real, no una sesion que se pueda correr de dia.
    if (this.semana().find((d) => d.cal === cal)?.deporte) {
      this.mensaje.set('Ese día es de deporte, no se puede mover. Elige un día de gym.');
      return;
    }
    const m = this.cargarOverrideMap();
    const full: Record<number, number> = {};
    for (let d = 1; d <= 7; d++) full[d] = m[d] ?? d;

    const rest = this.sesionDescanso();
    let oldRestCal = 0;
    for (let d = 1; d <= 7; d++) {
      if (full[d] === rest) {
        oldRestCal = d;
        break;
      }
    }
    if (!oldRestCal || oldRestCal === cal) return;

    const tmp = full[cal];
    full[cal] = full[oldRestCal];
    full[oldRestCal] = tmp;

    localStorage.setItem(this.overrideKey(), JSON.stringify(full));
    this.reconstruirSemana();
    this.cargarSesion(this.sesionDe(this.weekdayHoy())); // recarga hoy si cambio

    // feedback claro de lo que paso
    const diaDesc = this.diasLabel[cal - 1];
    const sesionMovida = this.nombresSesion[tmp - 1] ?? 'su entreno';
    const diaQueRecibe = this.diasLabel[oldRestCal - 1];
    this.mensaje.set(`Descanso movido al ${diaDesc}. ${sesionMovida} pasa al ${diaQueRecibe}.`);
  }

  restaurarSemana(): void {
    localStorage.removeItem(this.overrideKey());
    this.reconstruirSemana();
    this.cargarSesion(this.sesionDe(this.weekdayHoy()));
    this.mensaje.set('Semana restaurada al horario original.');
  }

  ngOnDestroy(): void {
    window.removeEventListener('pagehide', this.onSalir);
    window.removeEventListener('resize', this.onResizeVentana);
    document.removeEventListener('focusin', this.onFocoEntra);
    document.removeEventListener('focusout', this.onFocoSale);
    window.visualViewport?.removeEventListener('resize', this.onViewport);
    this.soltarPantalla();
    if (this.relojSesion) clearInterval(this.relojSesion);
    if (this.intervalo) clearInterval(this.intervalo);
    document.removeEventListener('visibilitychange', this.onVisibilidad);
    window.removeEventListener('online', this.onOnline);
  }

  /** Une filas consecutivas del mismo ejercicio en una sola tarjeta. */
  private agrupar(rutina: EjercicioPlan[]): EjercicioVM[] {
    const cards: EjercicioVM[] = [];
    for (const ej of rutina) {
      const ultima = cards[cards.length - 1];
      const mismaCarta =
        ultima && norm(ultima.ejercicio) === norm(ej.ejercicio) && ultima.bloque === ej.bloque;
      if (!mismaCarta) {
        cards.push({
          ejercicio: ej.ejercicio,
          nombre_dia: ej.nombre_dia,
          bloque: ej.bloque,
          medida: medidaDe(ej.ejercicio, ej.bloque),
          musculos: musculosDe(ej.ejercicio),
          tecnicas: [],
          series: [],
          mostrarAlt: false,
          alternativas: [],
          barra: barraDe(ej.ejercicio),
          notasMotor: [],
          verNotas: false,
          miNota: this.notasUsuario[norm(ej.ejercicio)] ?? '',
          aviso: null
        });
      }
      this.agregarSegmento(cards[cards.length - 1], ej);
    }
    return cards;
  }

  /** Agrega las series de una fila del plan a su tarjeta, segun su medida. */
  private agregarSegmento(card: EjercicioVM, ej: EjercicioPlan): void {
    if (ej.tecnica && !card.tecnicas.includes(ej.tecnica)) card.tecnicas.push(ej.tecnica);
    const nota = (ej.notas ?? '').trim();
    if (nota && !card.notasMotor.includes(nota)) card.notasMotor.push(nota);

    const med = card.medida;
    const unidad = med.cuenta?.unidad ?? '';
    const peso = Number(ej.peso_sugerido ?? 0);
    const n = med.cardio ? 1 : nSeriesDe(ej.series_objetivo);
    const esAmrap = /amrap/i.test(ej.tecnica ?? '');
    const hayReps = ej.reps_min != null || ej.reps_max != null;
    const valor = hayReps ? (ej.reps_max ?? ej.reps_min ?? 0) : (med.cuenta?.def ?? 0);
    const rango = ej.reps_min ? `${ej.reps_min}${ej.reps_max ? '-' + ej.reps_max : ''}` : '';

    for (let i = 0; i < n; i++) {
      const ultima = i === n - 1;
      const alFallo = esAmrap && ultima;
      const repsObjetivo = alFallo
        ? 'al fallo'
        : med.cardio && hayReps
        ? `${rango} ${unidad} continuos`
        : hayReps && rango
        ? `${rango} ${unidad}`
        : med.objetivo;
      card.series.push({
        planId: ej.id,
        numeroSerie: i + 1,
        tecnica: ej.tecnica,
        etiqueta: med.cardio ? 'Sesión continua' : this.etiquetaSerie(ej.tecnica, i, n, alFallo, card.series.length),
        alFallo,
        descanso: med.cardio ? 0 : (ej.descanso_seg && ej.descanso_seg > 0 ? ej.descanso_seg : descansoPorTecnica(ej.tecnica)),
        repsObjetivo,
        reps: valor,        // "reps" = el conteo (reps / min / seg / metros / rondas)
        peso,
        rpe: med.rpe ? 8 : (med.cardio ? 6 : 8),
        hecho: false,
        abierta: false,
        repsMin: ej.reps_min,
        repsMax: ej.reps_max,
        manual: false
      });
    }
  }

  private etiquetaSerie(tec: string | null, i: number, n: number, alFallo: boolean, yaHay: number): string {
    const t = (tec ?? '').toLowerCase();
    if (t.includes('top set')) return 'Top Set';
    if (t.includes('back')) return 'Back-off';
    if (alFallo) return 'Al fallo (AMRAP)';
    if (t.includes('drop') && i === n - 1) return 'Drop set';
    if (t.includes('rest')) return 'Rest-Pause';
    if (t.includes('super')) return 'Superserie';
    return `Serie ${yaHay + 1}`;
  }

  // ----- Tema -----
  private aplicarTema(t: 'light' | 'dark'): void {
    this.tema.set(t);
    document.documentElement.classList.toggle('theme-dark', t === 'dark');
    localStorage.setItem('tema', t);
  }

  toggleTema(): void {
    this.aplicarTema(this.tema() === 'dark' ? 'light' : 'dark');
  }

  // ----- Racha -----
  private cargarRacha(): void {
    try {
      const r = localStorage.getItem('racha');
      if (r) this.racha.set(JSON.parse(r).count ?? 0);
    } catch {
      /* noop */
    }
  }

  private registrarRacha(): void {
    let count = 1;
    let last = '';
    try {
      const r = localStorage.getItem('racha');
      if (r) {
        const o = JSON.parse(r);
        count = o.count ?? 0;
        last = o.last ?? '';
      }
    } catch {
      /* noop */
    }
    const hoy = this.fecha;
    if (last !== hoy) {
      const ayer = fechaLocal(new Date(Date.now() - 86400000));
      count = last === ayer ? count + 1 : 1;
      localStorage.setItem('racha', JSON.stringify({ count, last: hoy }));
      this.racha.set(count);
    }
  }

  // ----- Calentamiento / tecnicas -----
  toggleCalentamiento(): void {
    this.mostrarCalentamiento.update((v) => !v);
  }

  abrirTecnica(tecnica: string | null): void {
    this.tecnicaActiva.set(explicacionTecnica(tecnica));
  }

  abrirRpe(): void {
    this.tecnicaActiva.set(RPE_INFO);
  }

  rpeTexto(rpe: number): string {
    return rpeSignificado(rpe);
  }

  /** RPE objetivo de la serie (guia antes de registrar el real).
   *  En dia de baja energia (readiness) se entrena igual pero lejos del fallo:
   *  la autorregulacion diaria protege la recuperacion sin perder la sesion. */
  rpeObjetivo(s: SerieVM, ultima: boolean): string {
    if (this.diaSuave()) return 'RPE 7-8 · hoy sin fallo (RIR 3-4)';
    if (s.alFallo) return 'al fallo (RPE 10)';
    return rpeObjetivoDe(s.tecnica, ultima);
  }

  // ----- Readiness (como llegas hoy) -----
  setReadiness(v: 'bien' | 'normal' | 'baja'): void {
    this.readiness.set(v);
    try {
      localStorage.setItem('readiness-' + this.fecha, v);
    } catch {
      /* noop */
    }
    // al motor: varios dias "sin energia" en una semana adelantan la descarga
    this.enviarFeedback([{ tipo: 'dia', clave: 'energia', carga: v === 'bien' ? 1 : v === 'normal' ? 2 : 3 }]);
  }

  setSueno(v: 1 | 2 | 3): void {
    this.sueno.set(v);
    try {
      localStorage.setItem('sueno-' + this.fecha, String(v));
    } catch {
      /* noop */
    }
    this.enviarFeedback([{ tipo: 'dia', clave: 'sueno', carga: v }]);
  }

  /** Dia suave: sin energia o habiendo dormido mal -> nada al fallo. */
  diaSuave(): boolean {
    return this.readiness() === 'baja' || this.sueno() === 3;
  }

  // ----- Resumen al guardar -----
  /** e1RM de una serie (misma formula que los records de la app: Epley, reps <= 15). */
  private e1rmSerie(peso: number, reps: number): number {
    return peso > 0 && reps > 0 ? peso * (1 + Math.min(reps, 15) / 30) : 0;
  }

  /** Lo hecho hoy por ejercicio: volumen y mejor e1RM (solo series marcadas; si no
   *  se marco ninguna, todas las que se guardan). Las asistidas no suman volumen:
   *  su "peso" es la ayuda de la maquina. */
  private hechoHoy(): Resumen['ejercicios'] {
    const cards = this.ejercicios();
    const algunaMarcada = cards.some((e) => e.series.some((s) => s.hecho));
    return cards
      .filter((e) => !e.medida.cardio && !this.esAsistida(e))
      .map((e) => {
        const ss = e.series.filter((s) => s.hecho || !algunaMarcada);
        return {
          nombre: e.ejercicio,
          volumen: ss.reduce((a, s) => a + (s.peso > 0 ? s.peso * s.reps : 0), 0),
          e1rm: Math.max(0, ...ss.map((s) => this.e1rmSerie(s.peso, s.reps))),
          cambioE1rm: null,
          cambioVolumen: null
        };
      })
      .filter((x) => x.volumen > 0);
  }

  private abrirResumen(prs: string[], sinConexion: boolean): void {
    const ej = this.hechoHoy();
    const cards = this.ejercicios();
    const algunaMarcada = cards.some((e) => e.series.some((s) => s.hecho));
    this.resumen.set({
      series: cards.reduce((a, e) => a + e.series.filter((s) => s.hecho || !algunaMarcada).length, 0),
      volumen: Math.round(ej.reduce((a, x) => a + x.volumen, 0)),
      minutos: this.minutosSesion(),
      prs,
      cambioVolumen: null,
      comparando: !sinConexion,
      sinConexion,
      ejercicios: ej
    });
    if (sinConexion) return;
    // comparacion: la ULTIMA vez que hiciste cada uno de estos ejercicios
    this.api.getHistorial(60).subscribe({
      next: (res) => {
        const r = this.resumen();
        if (!r) return;
        const previas = (res.series ?? []).filter((s) => String(s.fecha_entreno).slice(0, 10) < this.fecha);
        let antes = 0;
        let ahora = 0;
        const ejercicios = r.ejercicios.map((x) => {
          const del = previas.filter((s) => norm(s.ejercicio) === norm(x.nombre));
          if (!del.length) return x;
          const ultima = del.reduce((m, s) => (String(s.fecha_entreno) > m ? String(s.fecha_entreno) : m), '');
          const sesion = del.filter((s) => String(s.fecha_entreno) === ultima);
          const vol = sesion.reduce((a, s) => a + (Number(s.peso_kg) || 0) * (Number(s.repeticiones) || 0), 0);
          const e1 = Math.max(0, ...sesion.map((s) => this.e1rmSerie(Number(s.peso_kg) || 0, Number(s.repeticiones) || 0)));
          if (vol > 0) {
            antes += vol;
            ahora += x.volumen;
          }
          return {
            ...x,
            cambioE1rm: e1 > 0 && x.e1rm > 0 ? x.e1rm / e1 - 1 : null,
            cambioVolumen: vol > 0 ? x.volumen / vol - 1 : null
          };
        });
        this.resumen.set({ ...r, ejercicios, comparando: false, cambioVolumen: antes > 0 ? ahora / antes - 1 : null });
      },
      error: () => {
        const r = this.resumen();
        if (r) this.resumen.set({ ...r, comparando: false });
      }
    });
  }

  cerrarResumen(): void {
    this.resumen.set(null);
    this.abrirEncuesta();
  }

  /** "+8%" / "-3%" / "=" para el resumen. */
  pct(x: number | null): string {
    if (x === null || !isFinite(x)) return '';
    const v = Math.round(x * 100);
    return v === 0 ? '=' : `${v > 0 ? '+' : ''}${v}%`;
  }

  // ----- Encuesta: agujetas al empezar, bombeo/carga/dolor al terminar -----
  setAgujetas(m: MuscleId, v: number): void {
    this.agujetas.update((a) => ({ ...a, [m]: v }));
    try {
      localStorage.setItem('agujetas-' + this.fecha, JSON.stringify(this.agujetas()));
    } catch {
      /* noop */
    }
    this.enviarFeedback([{ tipo: 'musculo', clave: m, agujetas: v }]);
  }

  setEnc(campo: 'bombeo' | 'carga', m: MuscleId, v: number): void {
    (campo === 'bombeo' ? this.encBombeo : this.encCarga).update((a) => ({ ...a, [m]: v }));
  }

  toggleDolor(ejercicio: string): void {
    this.encDolor.update((d) => (d.includes(ejercicio) ? d.filter((x) => x !== ejercicio) : [...d, ejercicio]));
  }

  /** Ejercicios de pesas de hoy (para marcar dolor articular). */
  ejerciciosPesas(): string[] {
    return this.ejercicios().filter((e) => !e.medida.cardio && e.medida.rpe).map((e) => e.ejercicio);
  }

  private abrirEncuesta(): void {
    if (localStorage.getItem('encuesta-' + this.fecha) || !this.musculosHoy().length) return;
    this.encBombeo.set({});
    this.encCarga.set({});
    this.encDolor.set([]);
    this.mostrarEncuesta.set(true);
  }

  enviarEncuesta(): void {
    const items: FeedbackItem[] = [];
    for (const m of this.musculosHoy()) {
      const bombeo = this.encBombeo()[m] ?? null;
      const carga = this.encCarga()[m] ?? null;
      if (bombeo || carga) items.push({ tipo: 'musculo', clave: m, bombeo, carga });
    }
    for (const e of this.encDolor()) items.push({ tipo: 'ejercicio', clave: e, dolor: 1 });
    if (items.length) this.enviarFeedback(items);
    this.cerrarEncuesta();
    if (items.length) this.mensaje.set('✓ Gracias: con esto el motor ajusta tus series de la próxima semana.');
  }

  cerrarEncuesta(): void {
    this.mostrarEncuesta.set(false);
    try {
      localStorage.setItem('encuesta-' + this.fecha, '1');
    } catch {
      /* noop */
    }
  }

  /** Envia respuestas; si no hay conexion quedan en cola y se reenvian solas. */
  private enviarFeedback(items: FeedbackItem[], fecha = this.fecha): void {
    this.api.guardarFeedback(fecha, items).subscribe({
      error: () => {
        const cola = this.leerColaFeedback();
        cola.push({ fecha, items });
        this.escribirColaFeedback(cola);
      }
    });
  }

  private leerColaFeedback(): FeedbackPendiente[] {
    return [...this.colaFb];
  }

  private escribirColaFeedback(cola: FeedbackPendiente[]): void {
    this.colaFb = cola.slice(-40);
    almacen.guardar('colaFeedback', this.colaFb);
  }

  /** Reenvia la cola de encuestas (es un upsert: reenviar no duplica nada). */
  private reenviarFeedback(): void {
    const cola = this.leerColaFeedback();
    if (!cola.length) return;
    this.escribirColaFeedback([]);
    for (const e of cola) this.enviarFeedback(e.items, e.fecha);
  }

  // ----- Historial (ultimas sesiones) -----
  toggleHistorial(): void {
    this.mostrarHistorial.update((v) => !v);
    if (this.mostrarHistorial() && this.historial().length === 0) {
      this.cargandoHistorial.set(true);
      this.api.getHistorial(30).subscribe({
        next: (res) => {
          this.historial.set(this.agruparHistorial(res.series ?? []));
          this.cargandoHistorial.set(false);
        },
        error: () => {
          this.mensaje.set('No se pudo cargar el historial. Revisa tu conexion.');
          this.cargandoHistorial.set(false);
          this.mostrarHistorial.set(false);
        }
      });
    }
  }

  /** Agrupa las series por fecha y muestra la mejor serie de cada ejercicio. */
  private agruparHistorial(series: SerieHistorial[]): Array<{ fecha: string; items: Array<{ ejercicio: string; mejor: string }> }> {
    const porFecha = new Map<string, Map<string, { e1rm: number; label: string }>>();
    for (const s of series) {
      const fecha = String(s.fecha_entreno).slice(0, 10);
      const peso = Number(s.peso_kg) || 0;
      const reps = Number(s.repeticiones) || 0;
      const e1rm = peso > 0 ? peso * (1 + Math.min(reps, 15) / 30) : reps;
      const label = peso > 0 ? `${peso} kg × ${reps} @RPE ${Number(s.rpe) || '—'}` : `${reps} reps @RPE ${Number(s.rpe) || '—'}`;
      if (!porFecha.has(fecha)) porFecha.set(fecha, new Map());
      const dia = porFecha.get(fecha)!;
      const prev = dia.get(s.ejercicio);
      if (!prev || e1rm > prev.e1rm) dia.set(s.ejercicio, { e1rm, label });
    }
    return Array.from(porFecha.entries()).map(([fecha, dia]) => ({
      fecha,
      items: Array.from(dia.entries()).map(([ejercicio, v]) => ({ ejercicio, mejor: v.label }))
    }));
  }

  // ----- Records personales (e1RM) + celebracion -----
  /** Detecta PRs comparando el e1RM de hoy contra el record guardado. */
  private detectarPrs(items: SeriePayload[]): string[] {
    let prs: Record<string, number> = {};
    try {
      prs = JSON.parse(localStorage.getItem('prs') ?? '{}');
    } catch {
      prs = {};
    }
    const hoy = new Map<string, number>();
    for (const it of items) {
      const peso = Number(it.peso_kg) || 0;
      const reps = Number(it.repeticiones) || 0;
      if (peso <= 0 || reps <= 0) continue;
      const e1rm = peso * (1 + Math.min(reps, 15) / 30);
      if (e1rm > (hoy.get(it.ejercicio) ?? 0)) hoy.set(it.ejercicio, e1rm);
    }
    const nuevos: string[] = [];
    for (const [ej, e1rm] of hoy) {
      const record = prs[ej] ?? 0;
      if (record > 0 && e1rm > record + 0.01) nuevos.push(ej);
      if (e1rm > record) prs[ej] = Math.round(e1rm * 100) / 100;
    }
    try {
      localStorage.setItem('prs', JSON.stringify(prs));
    } catch {
      /* noop */
    }
    return nuevos;
  }

  /** Lluvia de confeti (sin librerias): piezas CSS que caen y se autodestruyen. */
  private celebrar(): void {
    const cont = document.createElement('div');
    cont.className = 'confetti';
    const colores = ['#aaff00', '#7d51fe', '#5920ff', '#ffffff', '#7ab800']; // paleta violeta + lima
    for (let i = 0; i < 28; i++) {
      const p = document.createElement('span');
      p.className = 'confetti-piece';
      p.style.left = Math.random() * 100 + 'vw';
      p.style.background = colores[i % colores.length];
      p.style.animationDelay = Math.random() * 0.6 + 's';
      p.style.animationDuration = 1.8 + Math.random() * 1.2 + 's';
      cont.appendChild(p);
    }
    document.body.appendChild(cont);
    setTimeout(() => cont.remove(), 3600);
    if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
  }

  cerrarTecnica(): void {
    this.tecnicaActiva.set(null);
  }

  // ----- Alternativas -----
  toggleAlternativas(ej: EjercicioVM): void {
    ej.mostrarAlt = !ej.mostrarAlt;
    if (ej.mostrarAlt) {
      // excluye solo los OTROS ejercicios de la rutina, no el actual
      const otros = new Set(
        this.ejercicios().filter((e) => e !== ej).map((e) => norm(e.ejercicio))
      );
      ej.alternativas = alternativasDe(ej.ejercicio).filter((a) => !otros.has(norm(a.nombre)));
    }
  }

  // ----- "Usar siempre" -----
  private cargarPreferencias(): void {
    try {
      this.preferencias.set(JSON.parse(localStorage.getItem('preferencias') ?? '{}'));
    } catch {
      /* noop */
    }
    this.api.getPreferencias().subscribe({
      next: (res) => {
        const m: Record<string, string> = {};
        for (const p of res.preferencias ?? []) m[norm(p.reemplazo)] = p.original;
        this.guardarPreferenciasLocal(m);
      },
      error: () => undefined // sin conexion: vale la copia local
    });
  }

  private guardarPreferenciasLocal(m: Record<string, string>): void {
    this.preferencias.set(m);
    try {
      localStorage.setItem('preferencias', JSON.stringify(m));
    } catch {
      /* noop */
    }
  }

  /** Ejercicio ORIGINAL del plan para esta tarjeta (si ya es un reemplazo tuyo). */
  originalDe(ej: EjercicioVM): string | null {
    return this.preferencias()[norm(ej.ejercicio)] ?? null;
  }

  /** Cambia el ejercicio hoy Y en los planes siguientes (el motor lo respeta). */
  usarSiempre(ej: EjercicioVM, alt: Alternativa): void {
    const original = this.originalDe(ej) ?? ej.ejercicio;
    this.elegirAlternativa(ej, alt);
    this.guardarEnCurso();
    this.api.guardarPreferencia({ original, reemplazo: alt.nombre }).subscribe({
      next: () => {
        const m = { ...this.preferencias() };
        for (const k of Object.keys(m)) if (m[k] === original) delete m[k];
        m[norm(alt.nombre)] = original;
        this.guardarPreferenciasLocal(m);
        this.mensaje.set(`✓ Desde el próximo plan usarás ${alt.nombre} en lugar de ${original}.`);
      },
      error: () => this.mensaje.set('Hoy se cambió, pero no se pudo guardar para siempre (sin conexión). Inténtalo de nuevo.')
    });
  }

  /** Quita la preferencia: vuelve el ejercicio original del plan (hoy y despues). */
  volverAlOriginal(ej: EjercicioVM): void {
    const original = this.originalDe(ej);
    if (!original) return;
    this.api.guardarPreferencia({ original, baja: true }).subscribe({
      next: () => {
        const m = { ...this.preferencias() };
        delete m[norm(ej.ejercicio)];
        this.guardarPreferenciasLocal(m);
        this.elegirAlternativa(ej, { nombre: original, musculos: musculosDe(original) });
        this.guardarEnCurso();
        this.mensaje.set(`✓ Vuelve ${original} a tu plan.`);
      },
      error: () => this.mensaje.set('No se pudo quitar la preferencia (sin conexión). Inténtalo de nuevo.')
    });
  }

  elegirAlternativa(ej: EjercicioVM, alt: Alternativa): void {
    ej.ejercicio = alt.nombre;            // cambia TODA la tarjeta (todas sus series)
    ej.musculos = alt.musculos;
    ej.barra = barraDe(alt.nombre);
    ej.miNota = this.notasUsuario[norm(alt.nombre)] ?? '';
    // las notas del motor hablaban del ejercicio original (su peso anterior...)
    ej.notasMotor = [];
    ej.mostrarAlt = false;
  }

  // ----- Series -----
  ajustar(serie: SerieVM, campo: 'peso' | 'reps', delta: number, ej?: EjercicioVM): void {
    // con barra el salto minimo real es 2.5 kg (el disco mas chico, 1.25, por lado)
    const paso = campo === 'peso' ? (ej?.barra ? 2.5 : 1.25) : 1;
    serie[campo] = Math.max(0, Number((serie[campo] + delta * paso).toFixed(2)));
    if (campo === 'peso') serie.manual = true;
    this.guardarEnCurso();
  }

  // ----- Autorregulacion dentro de la sesion -----
  /** Al completar una serie: corrige el peso de las SIGUIENTES si el RPE real se
   *  alejo claramente del objetivo, y recalcula el back-off desde el Top Set REAL.
   *  No toca series que el usuario ya edito a mano. */
  private autorregular(ej: EjercicioVM, s: SerieVM): void {
    const i = ej.series.indexOf(s);
    const libres = (x: SerieVM) => !x.hecho && !x.manual && x.peso > 0;
    const paso = pasoCarga(ej.ejercicio, s.peso);
    const r2 = (v: number) => Math.round(v * 100) / 100;

    if (/top set/i.test(s.tecnica ?? '') && s.peso > 0 && !this.esAsistida(ej)) {
      const backs = ej.series.filter((x) => /back/i.test(x.tecnica ?? '') && libres(x));
      const nuevo = r2(Math.max(ej.barra ?? paso, Math.round((s.peso * 0.8) / paso) * paso));
      if (backs.length && backs.some((b) => b.peso !== nuevo)) {
        backs.forEach((b) => (b.peso = nuevo));
        ej.aviso = { texto: `Back-off = 80% de tu Top Set real (${s.peso} kg) → ${nuevo} kg`, sube: nuevo >= s.peso * 0.8 };
      }
    }

    const siguientes = ej.series.slice(i + 1).filter((x) => libres(x) && x.tecnica === s.tecnica);
    if (!siguientes.length) return;
    const aj = ajusteIntraSesion({
      peso: s.peso, reps: s.reps, rpe: s.rpe, repsMin: s.repsMin, repsMax: s.repsMax,
      rpeObjetivoMax: rpeMaxDe(this.rpeObjetivo(s, i === ej.series.length - 1)),
      tecnica: s.tecnica, alFallo: s.alFallo, barra: ej.barra, paso
    });
    if (!aj) return;
    if (this.esAsistida(ej)) {
      // asistida: "subir la carga" es QUITAR ayuda (y al reves), de 5 en 5
      const ayuda = Math.max(0, s.peso + (aj.sube ? -5 : 5));
      siguientes.forEach((x) => (x.peso = ayuda));
      ej.aviso = { texto: `${aj.sube ? '↑' : '↓'} Siguientes series con ayuda ${ayuda} kg · ${aj.motivo}`, sube: aj.sube };
      return;
    }
    siguientes.forEach((x) => (x.peso = aj.peso));
    ej.aviso = { texto: `${aj.sube ? '↑' : '↓'} Siguientes series a ${aj.peso} kg · ${aj.motivo}`, sube: aj.sube };
  }

  // ----- Reloj de la sesion -----
  readonly minutosSesion = signal<number | null>(null);
  private relojSesion: ReturnType<typeof setInterval> | null = null;

  private marcarInicioSesion(): void {
    if (!localStorage.getItem('inicio-' + this.fecha)) {
      try {
        localStorage.setItem('inicio-' + this.fecha, String(Date.now()));
      } catch {
        /* noop */
      }
    }
    this.arrancarReloj();
  }

  private arrancarReloj(): void {
    this.tickReloj();
    if (!this.relojSesion && !this.yaGuardadoHoy()) this.relojSesion = setInterval(() => this.tickReloj(), 30000);
  }

  private tickReloj(): void {
    const ini = Number(localStorage.getItem('inicio-' + this.fecha) || 0);
    if (!ini) return this.minutosSesion.set(null);
    const fin = Number(localStorage.getItem('fin-' + this.fecha) || 0) || Date.now();
    this.minutosSesion.set(Math.max(0, Math.round((fin - ini) / 60000)));
  }

  private pararReloj(): void {
    try {
      if (!localStorage.getItem('fin-' + this.fecha)) localStorage.setItem('fin-' + this.fecha, String(Date.now()));
    } catch {
      /* noop */
    }
    this.tickReloj();
    if (this.relojSesion) clearInterval(this.relojSesion);
    this.relojSesion = null;
  }

  // ----- Calculadora de discos -----
  /** Discos por lado para el peso de la serie; null si no es de barra o no hace falta. */
  cargaDe(ej: EjercicioVM, peso: number): Carga | null {
    return ej.barra ? discosPorLado(peso, ej.barra) : null;
  }

  discosRampa(peso: number, barra: number): Carga | null {
    return discosPorLado(peso, barra);
  }

  textoCarga(c: Carga): string {
    return textoDiscos(c);
  }

  /** Mancuernas (peso TOTAL de las dos): "2 × 12.5 kg" para saber que agarrar. */
  porMancuerna(ej: EjercicioVM, peso: number): string | null {
    if (!peso || !ej.ejercicio.toLowerCase().includes('mancuerna')) return null;
    const m = Math.round((peso / 2) * 100) / 100;
    return `2 × ${m} kg`;
  }

  // ----- Pantalla siempre encendida -----
  /** Hay un entreno empezado y sin guardar: es cuando la pantalla no debe apagarse. */
  private entrenoEnCurso(): boolean {
    return !this.yaGuardadoHoy() && this.progreso().hechas > 0;
  }

  private async fijarPantalla(): Promise<void> {
    if (this.wakeLock || document.hidden || !('wakeLock' in navigator)) return;
    try {
      const wl = await navigator.wakeLock.request('screen');
      this.wakeLock = wl;
      this.pantallaFija.set(true);
      wl.addEventListener('release', () => {
        if (this.wakeLock === wl) this.wakeLock = null;
        this.pantallaFija.set(false);
      });
    } catch {
      /* bateria baja o el sistema lo niega: se sigue sin el */
    }
  }

  private soltarPantalla(): void {
    const wl = this.wakeLock;
    this.wakeLock = null;
    this.pantallaFija.set(false);
    wl?.release().catch(() => undefined);
  }

  setRpe(serie: SerieVM, rpe: number): void {
    serie.rpe = rpe;
  }

  /** Repite el peso y las reps de esta serie en todas las siguientes del ejercicio. */
  repetir(ej: EjercicioVM, index: number): void {
    const base = ej.series[index];
    for (let j = index + 1; j < ej.series.length; j++) {
      ej.series[j].peso = base.peso;
      ej.series[j].reps = base.reps;
      ej.series[j].rpe = base.rpe;
    }
  }

  hayPosteriores(ej: EjercicioVM, index: number): boolean {
    return index < ej.series.length - 1;
  }

  toggleSerie(ej: EjercicioVM, serie: SerieVM): void {
    serie.hecho = !serie.hecho;
    if (serie.hecho) serie.abierta = false; // al completarla se pliega y pasa la siguiente
    this.recalcularProgreso();
    if (serie.hecho) {
      this.iniciarDescanso(serie, ej.ejercicio);
      this.fijarPantalla();
      this.marcarInicioSesion();
      this.autorregular(ej, serie);
      almacen.pedirPersistencia();
    }
    this.guardarEnCurso();
  }

  // ----- Estructura "Atleta": una serie a la vez -----
  /** Primera serie pendiente del ejercicio: la que se muestra en grande. */
  serieActiva(ej: EjercicioVM): SerieVM | null {
    return ej.series.find((s) => !s.hecho) ?? null;
  }

  /** La activa siempre esta desplegada; las demas, solo si se abrieron a mano. */
  serieAbierta(ej: EjercicioVM, s: SerieVM): boolean {
    return s.abierta || s === this.serieActiva(ej);
  }

  alternarSerie(s: SerieVM): void {
    s.abierta = !s.abierta;
  }

  /** "A - Fuerza maxima" -> "Fuerza": la pastilla del bloque, corta. */
  bloqueCorto(b: string | null): string {
    const t = (b || '').replace(/^[ABC]\s*-\s*/, '');
    return /fuerza/i.test(t) ? 'Fuerza' : /volumen/i.test(t) ? 'Volumen' : /aislam/i.test(t) ? 'Aislamiento' : t || 'Bloque';
  }

  /** Convencion del usuario: las mancuernas se registran como PESO TOTAL de las dos. */
  unidadPeso(ej: EjercicioVM): string {
    if (this.esAsistida(ej)) return 'kg ayuda';
    return ej.ejercicio.toLowerCase().includes('mancuerna') ? 'kg total' : 'kg';
  }

  /** Maquina asistida (el motor la marca "(Asistida)"): el peso es la AYUDA,
   *  asi que menos kg = mas dificil y todo ajuste va al reves. */
  esAsistida(ej: EjercicioVM): boolean {
    return /\(asistida\)/i.test(ej.ejercicio);
  }

  /** Anillo de progreso de la cabecera (r = 20 -> circunferencia 2*pi*20). */
  readonly ringC = 2 * Math.PI * 20;
  readonly ringOffset = computed(() => this.ringC * (1 - this.progreso().pct / 100));

  ejercicioHecho(ej: EjercicioVM): boolean {
    return ej.series.every((s) => s.hecho);
  }

  // ----- Cronometro (basado en timestamp: sobrevive el segundo plano) -----
  iniciarDescanso(serie: SerieVM, nombre: string): void {
    const seg = serie.descanso > 0 ? serie.descanso : 90;
    this.arrancarTimer(seg, nombre);
  }

  private arrancarTimer(seg: number, nombre: string): void {
    this.finAt = Date.now() + seg * 1000;
    this.alarmaSonada = false;
    this.tmrTotal.set(seg);
    this.tmrSeg.set(seg);
    this.tmrNombre.set(nombre);
    this.tmrActivo.set(true);
    this.persistirTimer();
    if (this.intervalo) clearInterval(this.intervalo);
    this.intervalo = setInterval(() => this.tick(), 500);
  }

  private tick(): void {
    const restante = Math.max(0, Math.round((this.finAt - Date.now()) / 1000));
    this.tmrSeg.set(restante);
    if (restante <= 0) {
      if (this.intervalo) clearInterval(this.intervalo);
      this.intervalo = null;
      this.tmrActivo.set(false);
      if (!this.alarmaSonada) {
        this.alarmaSonada = true;
        this.alarma();
      }
      localStorage.removeItem('timer');
    }
  }

  sumarTiempo(s: number): void {
    this.finAt += s * 1000;
    this.tmrSeg.set(Math.max(0, Math.round((this.finAt - Date.now()) / 1000)));
    this.tmrTotal.update((v) => Math.max(v, this.tmrSeg()));
    if (!this.tmrActivo()) {
      this.tmrActivo.set(true);
      this.alarmaSonada = false;
      if (!this.intervalo) this.intervalo = setInterval(() => this.tick(), 500);
    }
    this.persistirTimer();
  }

  cancelarTimer(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    this.intervalo = null;
    this.finAt = 0;
    this.tmrActivo.set(false);
    this.tmrSeg.set(0);
    localStorage.removeItem('timer');
  }

  private persistirTimer(): void {
    localStorage.setItem(
      'timer',
      JSON.stringify({ finAt: this.finAt, total: this.tmrTotal(), nombre: this.tmrNombre() })
    );
  }

  /** Reanuda el cronometro si quedo uno corriendo (ej. recarga o segundo plano). */
  private restaurarTimer(): void {
    try {
      const raw = localStorage.getItem('timer');
      if (!raw) return;
      const o = JSON.parse(raw) as { finAt: number; total: number; nombre: string };
      if (!o.finAt) return;
      if (o.finAt - Date.now() > 1000) {
        this.finAt = o.finAt;
        this.tmrTotal.set(o.total || 0);
        this.tmrNombre.set(o.nombre || '');
        this.alarmaSonada = false;
        this.tmrActivo.set(true);
        this.tmrSeg.set(Math.round((o.finAt - Date.now()) / 1000));
        this.intervalo = setInterval(() => this.tick(), 500);
      } else {
        localStorage.removeItem('timer');
      }
    } catch {
      /* noop */
    }
  }

  private alarma(): void {
    try {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g);
      g.connect(ctx.destination);
      o.type = 'sine';
      o.frequency.value = 880;
      g.gain.setValueAtTime(0.0001, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5);
      o.start();
      o.stop(ctx.currentTime + 0.55);
    } catch {
      /* noop */
    }
    if (navigator.vibrate) navigator.vibrate([200, 90, 200]);
  }

  // ----- Guardar (blindado: sin duplicados y sin perder entrenos) -----
  guardar(): void {
    if (this.guardando()) return; // anti doble-tap
    // Un dia de descanso o de deporte no tiene series que registrar. Antes el
    // boton seguia activo y guardaba el pseudo-ejercicio como sesion: en el
    // historial real aparecian "Descanso Activo" x4 y "Basquetbol" x1, que
    // contaban como dias entrenados para la deteccion de pausas.
    if (this.esDiaDescanso() || this.esDiaDeporte()) return;
    if (this.yaGuardadoHoy() &&
        !window.confirm('Ya guardaste este entreno hoy. ¿Enviarlo OTRA VEZ? Puede duplicar series en el historial.')) {
      return;
    }
    const items: SeriePayload[] = [];
    for (const ej of this.ejercicios()) {
      const nota = ej.miNota.trim().slice(0, 200) || null;
      ej.series.forEach((s, i) => {
        items.push({
          plan_id: s.planId,
          ejercicio: ej.ejercicio,
          tecnica: s.tecnica,
          numero_serie: s.numeroSerie,
          peso_kg: s.peso,
          repeticiones: s.reps,
          rpe: s.rpe,
          notas: i === 0 ? nota : null   // la nota va una vez por ejercicio
        });
      });
      if (nota) this.notasUsuario[norm(ej.ejercicio)] = nota;
    }
    try {
      localStorage.setItem('notasEjercicio', JSON.stringify(this.notasUsuario));
    } catch {
      /* noop */
    }

    this.guardando.set(true);
    this.mensaje.set('');
    this.api.guardarEntreno(this.fecha, items).subscribe({
      next: (res) => {
        this.registrarRacha();
        this.marcarGuardadoHoy();
        this.soltarPantalla();
        this.pararReloj();
        almacen.borrar('enCurso');
        const prs = this.detectarPrs(items);
        if (prs.length) {
          this.celebrar();
          this.mensaje.set(`🎉 ¡PR en ${prs.join(', ')}! Entreno guardado: ${res.inserted} series. Racha: ${this.racha()} dias.`);
        } else {
          this.mensaje.set(`✓ Entreno guardado: ${res.inserted} series. Racha: ${this.racha()} dias.`);
        }
        this.guardando.set(false);
        this.reenviarPendientes();
        this.abrirResumen(prs, false);
      },
      error: () => {
        // No se pierde nada: queda en el telefono y se reenvia solo
        this.encolar(this.fecha, items);
        almacen.borrar('enCurso');
        this.mensaje.set(`📥 Sin conexion: tu entreno (${items.length} series) quedo guardado en el telefono. Se reenviara solo al volver internet, o toca "Reintentar".`);
        this.guardando.set(false);
        this.abrirResumen(this.detectarPrs(items), true);
      }
    });
  }

  private marcarGuardadoHoy(): void {
    this.yaGuardadoHoy.set(true);
    try {
      localStorage.setItem('ultimoGuardado', this.fecha);
    } catch {
      /* noop */
    }
  }

  // ----- Colas offline (IndexedDB, ver almacen.ts) -----
  /** Carga las colas del almacen durable. Migra (una vez) lo que hubiera en
   *  localStorage de versiones anteriores de la app, sin perder nada. */
  private async cargarColas(): Promise<void> {
    const migrar = async <T>(clave: string): Promise<T[]> => {
      let datos = (await almacen.leer<T[]>(clave)) ?? [];
      try {
        const viejo = JSON.parse(localStorage.getItem(clave) ?? '[]');
        if (Array.isArray(viejo) && viejo.length) {
          datos = [...datos, ...viejo];
          await almacen.guardar(clave, datos);
        }
        localStorage.removeItem(clave);
      } catch {
        /* noop */
      }
      return Array.isArray(datos) ? datos : [];
    };
    this.cola = await migrar<EntrenoPendiente>('colaEntrenos');
    this.colaFb = await migrar<FeedbackPendiente>('colaFeedback');
    this.pendientes.set(this.cola.length);
  }

  private leerCola(): EntrenoPendiente[] {
    return [...this.cola];
  }

  private escribirCola(cola: EntrenoPendiente[]): void {
    this.cola = cola;
    almacen.guardar('colaEntrenos', cola);
    this.pendientes.set(cola.length);
  }

  /** Guarda la foto del entreno en curso (series, pesos, marcas, alternativas,
   *  nota). Sin esto, si el sistema cerraba la app a mitad del entreno (iPhone
   *  al cambiar de app), se perdia todo lo marcado hasta pulsar Guardar.
   *  ya=true: sin esperar (al salir de la app); si no, se agrupan los cambios. */
  guardarEnCurso(ya = false): void {
    if (this.guardadoEnCursoProgramado) clearTimeout(this.guardadoEnCursoProgramado);
    const hacer = () => {
      this.guardadoEnCursoProgramado = null;
      const cards = this.ejercicios();
      if (!cards.length || this.yaGuardadoHoy() || !cards.some((e) => e.series.some((s) => s.hecho))) return;
      const foto: EnCurso = {
        fecha: this.fecha,
        sesion: this.sesionMostrada,
        cards: cards.map((e) => ({
          plan: e.series[0]?.planId ?? 0,
          ejercicio: e.ejercicio,
          miNota: e.miNota,
          series: e.series.map((s) => ({ planId: s.planId, numeroSerie: s.numeroSerie, peso: s.peso,
            reps: s.reps, rpe: s.rpe, hecho: s.hecho, manual: s.manual }))
        }))
      };
      almacen.guardar('enCurso', foto);
    };
    if (ya) hacer();
    else this.guardadoEnCursoProgramado = setTimeout(hacer, 400);
  }

  /** Si la app se cerro a mitad del entreno de HOY, lo deja como estaba. */
  private async restaurarEnCurso(): Promise<void> {
    const foto = await almacen.leer<EnCurso>('enCurso');
    if (!foto) return;
    if (foto.fecha !== this.fecha) {
      almacen.borrar('enCurso');          // de otro dia: ya no sirve
      return;
    }
    if (foto.sesion !== this.sesionMostrada || this.yaGuardadoHoy()) return;
    let restauradas = 0;
    for (const ej of this.ejercicios()) {
      const c = foto.cards.find((x) => x.plan === (ej.series[0]?.planId ?? -1));
      if (!c) continue;
      if (c.ejercicio !== ej.ejercicio) {
        // alternativa elegida en el gym: misma logica que elegirAlternativa
        ej.ejercicio = c.ejercicio;
        ej.musculos = musculosDe(c.ejercicio);
        ej.barra = barraDe(c.ejercicio);
        ej.notasMotor = [];
      }
      ej.miNota = c.miNota ?? ej.miNota;
      for (const s of ej.series) {
        const g = c.series.find((x) => x.planId === s.planId && x.numeroSerie === s.numeroSerie);
        if (!g) continue;
        Object.assign(s, { peso: g.peso, reps: g.reps, rpe: g.rpe, hecho: g.hecho, manual: g.manual });
        if (g.hecho) restauradas++;
      }
    }
    if (restauradas) {
      this.ejercicios.set([...this.ejercicios()]);
      this.recalcularProgreso();
      this.mensaje.set(`↩ Recuperé tu entreno en curso: ${restauradas} series ya marcadas.`);
    }
  }

  private encolar(fecha: string, items: SeriePayload[]): void {
    // un solo pendiente por fecha: reenviar el mismo dia reemplaza, no duplica
    const cola = this.leerCola().filter((e) => e.fecha !== fecha);
    cola.push({ fecha, items });
    this.escribirCola(cola);
  }

  /** Reenvia los entrenos pendientes, uno por uno y en orden. */
  reenviarPendientes(): void {
    const cola = this.leerCola();
    this.pendientes.set(cola.length);
    if (!cola.length || this.reintentando()) return;
    this.reintentando.set(true);
    const e = cola[0];
    this.api.guardarEntreno(e.fecha, e.items).subscribe({
      next: (res) => {
        this.escribirCola(this.leerCola().filter((x) => x.fecha !== e.fecha));
        if (e.fecha === this.fecha) this.marcarGuardadoHoy();
        this.mensaje.set(`✓ Entreno pendiente del ${e.fecha} sincronizado (${res.inserted} series).`);
        this.reintentando.set(false);
        if (this.leerCola().length) this.reenviarPendientes();
      },
      error: () => {
        this.reintentando.set(false); // se reintenta al volver online o manualmente
      }
    });
  }
}

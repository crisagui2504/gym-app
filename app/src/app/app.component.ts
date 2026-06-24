import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EjercicioPlan, RutinaApiService, SeriePayload } from './rutina-api.service';
import { MuscleMapComponent } from './muscle-map.component';
import {
  Alternativa,
  Calentamiento,
  MUSCLE_LABEL,
  MuscleId,
  Tecnica,
  alternativasDe,
  calentamientoDe,
  descansoPorTecnica,
  explicacionTecnica,
  fechaLocal,
  musculosDe,
  norm,
  nSeriesDe,
  RPE_INFO,
  rpeSignificado,
  seriesAproximacion
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
}

interface EjercicioVM {
  ejercicio: string;
  nombre_dia: string;
  bloque: string | null;
  musculos: MuscleId[];
  tecnicas: string[];    // tecnicas distintas (para los chips)
  series: SerieVM[];     // todas las series del ejercicio, juntas
  mostrarAlt: boolean;
  alternativas: Alternativa[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, MuscleMapComponent],
  templateUrl: './app.component.html'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly api = inject(RutinaApiService);

  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly mensaje = signal('');
  readonly fecha = fechaLocal();
  readonly nombreDia = signal('Rutina de hoy');
  readonly ejercicios = signal<EjercicioVM[]>([]);
  readonly rpeValores = [6, 7, 8, 9, 10];
  readonly etiquetas = MUSCLE_LABEL;

  readonly tema = signal<'light' | 'dark'>('dark');
  readonly racha = signal(0);
  readonly mostrarCalentamiento = signal(false);
  readonly calentamiento = computed<Calentamiento>(() => calentamientoDe(this.nombreDia()));
  readonly aproximacion = computed<{ ejercicio: string; series: ReturnType<typeof seriesAproximacion> } | null>(() => {
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
    return series.length ? { ejercicio: mejor.ejercicio, series } : null;
  });

  readonly tecnicaActiva = signal<Tecnica | null>(null);

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
  private finAt = 0;            // timestamp (ms) en que termina el descanso
  private alarmaSonada = false;
  // recalcula al volver a la app (el setInterval se frena en segundo plano)
  private readonly onVisibilidad = () => {
    if (!document.hidden && this.finAt > 0) this.tick();
  };

  ngOnInit(): void {
    const guardado = localStorage.getItem('tema');
    this.aplicarTema(guardado === 'light' ? 'light' : 'dark');
    this.cargarRacha();

    this.restaurarTimer();
    document.addEventListener('visibilitychange', this.onVisibilidad);

    this.api.getRutinaHoy().subscribe({
      next: (res) => {
        if (res.rutina.length > 0) {
          this.nombreDia.set(res.rutina[0].nombre_dia);
        }
        this.ejercicios.set(this.agrupar(res.rutina));
        this.cargando.set(false);
      },
      error: () => {
        this.mensaje.set('No se pudo cargar la rutina. Revisa tu conexion.');
        this.cargando.set(false);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    document.removeEventListener('visibilitychange', this.onVisibilidad);
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
          musculos: musculosDe(ej.ejercicio),
          tecnicas: [],
          series: [],
          mostrarAlt: false,
          alternativas: []
        });
      }
      this.agregarSegmento(cards[cards.length - 1], ej);
    }
    return cards;
  }

  /** Agrega las series de una fila del plan a su tarjeta. */
  private agregarSegmento(card: EjercicioVM, ej: EjercicioPlan): void {
    const peso = Number(ej.peso_sugerido ?? 0);
    const reps = ej.reps_max ?? ej.reps_min ?? 10;
    const n = nSeriesDe(ej.series_objetivo);
    const esAmrap = /amrap/i.test(ej.tecnica ?? '');
    const rango = ej.reps_min ? `${ej.reps_min}${ej.reps_max ? '-' + ej.reps_max : ''}` : '';
    if (ej.tecnica && !card.tecnicas.includes(ej.tecnica)) card.tecnicas.push(ej.tecnica);

    for (let i = 0; i < n; i++) {
      const ultima = i === n - 1;
      const alFallo = esAmrap && ultima;
      card.series.push({
        planId: ej.id,
        numeroSerie: i + 1,
        tecnica: ej.tecnica,
        etiqueta: this.etiquetaSerie(ej.tecnica, i, n, alFallo, card.series.length),
        alFallo,
        descanso: ej.descanso_seg && ej.descanso_seg > 0 ? ej.descanso_seg : descansoPorTecnica(ej.tecnica),
        repsObjetivo: alFallo ? 'al fallo' : rango,
        reps,
        peso,
        rpe: 8,
        hecho: false
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

  elegirAlternativa(ej: EjercicioVM, alt: Alternativa): void {
    ej.ejercicio = alt.nombre;            // cambia TODA la tarjeta (todas sus series)
    ej.musculos = alt.musculos;
    ej.mostrarAlt = false;
  }

  // ----- Series -----
  ajustar(serie: SerieVM, campo: 'peso' | 'reps', delta: number): void {
    const paso = campo === 'peso' ? 1.25 : 1;
    serie[campo] = Math.max(0, Number((serie[campo] + delta * paso).toFixed(2)));
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
    if (serie.hecho) this.iniciarDescanso(serie, ej.ejercicio);
  }

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

  // ----- Guardar -----
  guardar(): void {
    const items: SeriePayload[] = [];
    for (const ej of this.ejercicios()) {
      for (const s of ej.series) {
        items.push({
          plan_id: s.planId,
          ejercicio: ej.ejercicio,
          tecnica: s.tecnica,
          numero_serie: s.numeroSerie,
          peso_kg: s.peso,
          repeticiones: s.reps,
          rpe: s.rpe
        });
      }
    }

    this.guardando.set(true);
    this.mensaje.set('');
    this.api.guardarEntreno(this.fecha, items).subscribe({
      next: (res) => {
        this.registrarRacha();
        this.mensaje.set(`Entreno guardado: ${res.inserted} series. Racha: ${this.racha()} dias.`);
        this.guardando.set(false);
      },
      error: () => {
        this.mensaje.set('No se pudo guardar. Revisa tu conexion e intenta de nuevo.');
        this.guardando.set(false);
      }
    });
  }
}

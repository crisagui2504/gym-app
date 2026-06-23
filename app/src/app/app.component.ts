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
  imagenDe,
  musculosDe,
  nSeriesDe,
  RPE_INFO,
  rpeSignificado,
  seriesAproximacion
} from './entreno-data';

interface SerieVM {
  reps: number;
  peso: number;
  rpe: number;
  hecho: boolean;
}

interface EjercicioVM {
  id: number;
  nombre_dia: string;
  bloque: string | null;
  ejercicio: string;
  tecnica: string | null;
  reps_min: number | null;
  reps_max: number | null;
  descanso_seg: number | null;
  peso_sugerido: string | null;
  musculos: MuscleId[];
  imagen: string | null;
  sinImagen: boolean;
  series: SerieVM[];
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
    const pesado = this.ejercicios().find((e) => Number(e.peso_sugerido) >= 10);
    if (!pesado) return null;
    const series = seriesAproximacion(Number(pesado.peso_sugerido));
    return series.length ? { ejercicio: pesado.ejercicio, series } : null;
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

  ngOnInit(): void {
    const guardado = localStorage.getItem('tema');
    this.aplicarTema(guardado === 'light' ? 'light' : 'dark');
    this.cargarRacha();

    this.api.getRutinaHoy().subscribe({
      next: (res) => {
        if (res.rutina.length > 0) {
          this.nombreDia.set(res.rutina[0].nombre_dia);
        }
        this.ejercicios.set(res.rutina.map((ej) => this.crearVM(ej)));
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
  }

  private crearVM(ej: EjercicioPlan): EjercicioVM {
    const peso = Number(ej.peso_sugerido ?? 0);
    const reps = ej.reps_max ?? ej.reps_min ?? 10;
    const n = nSeriesDe(ej.series_objetivo);
    const series: SerieVM[] = Array.from({ length: n }, () => ({ reps, peso, rpe: 8, hecho: false }));
    return {
      id: ej.id,
      nombre_dia: ej.nombre_dia,
      bloque: ej.bloque,
      ejercicio: ej.ejercicio,
      tecnica: ej.tecnica,
      reps_min: ej.reps_min,
      reps_max: ej.reps_max,
      descanso_seg: ej.descanso_seg,
      peso_sugerido: ej.peso_sugerido,
      musculos: musculosDe(ej.ejercicio),
      imagen: imagenDe(ej.ejercicio),
      sinImagen: false,
      series,
      mostrarAlt: false,
      alternativas: []
    };
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

  // ----- Imagen / alternativas -----
  imagenFallo(ej: EjercicioVM): void {
    ej.sinImagen = true;
  }

  toggleAlternativas(ej: EjercicioVM): void {
    ej.mostrarAlt = !ej.mostrarAlt;
    if (ej.mostrarAlt) {
      const enRutina = new Set(this.ejercicios().map((e) => e.ejercicio.toLowerCase()));
      ej.alternativas = alternativasDe(ej.ejercicio).filter((a) => !enRutina.has(a.nombre.toLowerCase()));
    }
  }

  elegirAlternativa(ej: EjercicioVM, alt: Alternativa): void {
    ej.ejercicio = alt.nombre;
    ej.musculos = alt.musculos;
    ej.imagen = alt.imagen;
    ej.sinImagen = false;
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

  toggleSerie(ej: EjercicioVM, serie: SerieVM): void {
    serie.hecho = !serie.hecho;
    if (serie.hecho) this.iniciarDescanso(ej);
  }

  ejercicioHecho(ej: EjercicioVM): boolean {
    return ej.series.every((s) => s.hecho);
  }

  // ----- Cronometro -----
  iniciarDescanso(ej: EjercicioVM): void {
    const seg = ej.descanso_seg && ej.descanso_seg > 0 ? ej.descanso_seg : descansoPorTecnica(ej.tecnica);
    this.tmrTotal.set(seg);
    this.tmrSeg.set(seg);
    this.tmrNombre.set(ej.ejercicio);
    this.tmrActivo.set(true);
    if (this.intervalo) clearInterval(this.intervalo);
    this.intervalo = setInterval(() => this.tick(), 1000);
  }

  private tick(): void {
    const v = this.tmrSeg() - 1;
    if (v <= 0) {
      this.tmrSeg.set(0);
      if (this.intervalo) clearInterval(this.intervalo);
      this.tmrActivo.set(false);
      this.alarma();
    } else {
      this.tmrSeg.set(v);
    }
  }

  sumarTiempo(s: number): void {
    this.tmrSeg.update((v) => v + s);
    this.tmrTotal.update((v) => Math.max(v, this.tmrSeg()));
  }

  cancelarTimer(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    this.tmrActivo.set(false);
    this.tmrSeg.set(0);
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
      ej.series.forEach((s, i) => {
        items.push({
          plan_id: ej.id,
          ejercicio: ej.ejercicio,
          tecnica: ej.tecnica,
          numero_serie: i + 1,
          peso_kg: s.peso,
          repeticiones: s.reps,
          rpe: s.rpe
        });
      });
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

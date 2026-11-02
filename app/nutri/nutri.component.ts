import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit, computed, inject, signal } from '@angular/core';
import { NutricionService } from '../src/app/nutricion';
import { ProteinaComponent } from '../src/app/proteina.component';
import { ES_DEMO, entrarDemo, salirDemo } from '../src/app/demo';
import { ProgresoComponent } from './progreso.component';

type Pestana = 'hoy' | 'menu' | 'progreso';

/** App de nutricion (crisrodrigo.infinityfree.io): Hoy, Menu y Progreso. */
@Component({
  selector: 'app-nutri',
  standalone: true,
  imports: [CommonModule, ProteinaComponent, ProgresoComponent],
  template: `
    <div class="nu-app">
      <header class="nu-top">
        <div class="nu-top-txt">
          <button type="button" class="nu-marca" (click)="toqueMarca()" aria-label="Nutri">nutri<i>.</i></button>
          <h1>{{ titulos[tab()] }}</h1>
          <p class="nu-fecha">{{ fechaTexto }}</p>
        </div>
        <div class="nu-anillo" [class.ok]="nut.pct() >= 100" [class.cero]="nut.pct() === 0" role="img"
             [attr.aria-label]="'Proteína de hoy: ' + nut.pct() + ' % de la meta'">
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle class="nu-anillo-fondo" cx="32" cy="32" r="27"/>
            <circle class="nu-anillo-valor" cx="32" cy="32" r="27" [attr.stroke-dasharray]="arco()"/>
          </svg>
          <span><b>{{ nut.total() | number: '1.0-0' }}</b>g</span>
        </div>
      </header>

      <div class="nu-demo" *ngIf="esDemo">
        <span><b>Demo</b> · datos simulados, nada se guarda</span>
        <button type="button" (click)="salir()">Salir</button>
      </div>

      <main class="nu-main">
        <app-proteina *ngIf="tab() === 'hoy'" fija="prot"></app-proteina>
        <app-proteina *ngIf="tab() === 'menu'" fija="menu"></app-proteina>
        <app-progreso *ngIf="tab() === 'progreso'"></app-progreso>
      </main>

      <nav class="nu-nav" aria-label="Secciones">
        <button type="button" *ngFor="let p of pestanas" [class.on]="tab() === p.id" (click)="ir(p.id)"
                [attr.aria-current]="tab() === p.id ? 'page' : null">
          <span class="nu-nav-ico" aria-hidden="true">{{ p.ico }}</span>{{ p.nombre }}
        </button>
      </nav>
    </div>
  `
})
export class NutriComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly esDemo = ES_DEMO;
  readonly pestanas: Array<{ id: Pestana; nombre: string; ico: string }> = [
    { id: 'hoy', nombre: 'Hoy', ico: '🥑' },
    { id: 'menu', nombre: 'Menú', ico: '🍲' },
    { id: 'progreso', nombre: 'Progreso', ico: '📈' }
  ];
  readonly titulos: Record<Pestana, string> = { hoy: 'Tu comida de hoy', menu: 'Menú de la semana', progreso: 'Cómo vas' };
  readonly tab = signal<Pestana>(this.tabGuardada());
  readonly fechaTexto = new Date().toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
  /** Anillo de proteina: largo del arco sobre la circunferencia (r = 27). */
  readonly arco = computed(() => {
    const c = 2 * Math.PI * 27;
    return `${(c * this.nut.pct()) / 100} ${c}`;
  });
  private toques = 0;
  private reloj: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    void this.nut.cargar();
    void this.nut.reenviarPendiente();
  }

  /** Lo que no se pudo subir sin red se manda al volver internet. */
  @HostListener('window:online')
  alVolverLaRed(): void {
    void this.nut.reenviarPendiente();
  }

  ir(p: Pestana): void {
    this.tab.set(p);
    window.scrollTo({ top: 0 });
    try {
      localStorage.setItem('nu-tab', p);
    } catch {
      /* sin espacio: no pasa nada */
    }
  }

  /** 5 toques al logo: modo demo (como en GymTracker). */
  toqueMarca(): void {
    this.toques++;
    if (this.reloj) clearTimeout(this.reloj);
    this.reloj = setTimeout(() => (this.toques = 0), 1500);
    if (this.toques >= 5 && !ES_DEMO) entrarDemo();
  }

  salir(): void {
    salirDemo();
  }

  private tabGuardada(): Pestana {
    try {
      const t = localStorage.getItem('nu-tab');
      return t === 'menu' || t === 'progreso' ? t : 'hoy';
    } catch {
      return 'hoy';
    }
  }
}

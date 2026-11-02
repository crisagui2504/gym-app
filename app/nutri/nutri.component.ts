import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit, inject, signal } from '@angular/core';
import { NutricionService } from '../src/app/nutricion';
import { ProteinaComponent } from '../src/app/proteina.component';
import { ES_DEMO, entrarDemo, salirDemo } from '../src/app/demo';
import { AgregarComponent } from './agregar.component';
import { BienvenidaComponent } from './bienvenida.component';
import { HoyComponent } from './hoy.component';
import { ProgresoComponent } from './progreso.component';
import { CheckinComponent } from './checkin.component';
import { tiempoPorHora } from './iconos';

type Pestana = 'hoy' | 'menu' | 'progreso' | 'checkin';

/** App de nutricion (crisrodrigo.infinityfree.io): Hoy, Menu y Progreso, con el + al centro. */
@Component({
  selector: 'app-nutri',
  standalone: true,
  imports: [CommonModule, ProteinaComponent, ProgresoComponent, HoyComponent, AgregarComponent, BienvenidaComponent, CheckinComponent],
  template: `
    <app-bienvenida *ngIf="bienvenida()" (listo)="cerrarBienvenida()"></app-bienvenida>

    <div class="nu-app" *ngIf="!bienvenida()">
      <header class="nu-top">
        <button type="button" class="nu-avatar" (click)="toqueMarca()" aria-label="Nutri">🥑</button>
        <div class="nu-top-txt">
          <small>{{ saludo }} 👋</small>
          <h1>{{ titulos[tab()] }}</h1>
        </div>
        <span class="nu-fecha">{{ fechaCorta }}</span>
      </header>

      <div class="nu-demo" *ngIf="esDemo">
        <span><b>Demo</b> · datos simulados, nada se guarda</span>
        <button type="button" (click)="salir()">Salir</button>
      </div>

      <main class="nu-main">
        <app-hoy *ngIf="tab() === 'hoy'" (agregar)="abrirAgregar($event)"></app-hoy>
        <app-proteina *ngIf="tab() === 'menu'" fija="menu"></app-proteina>
        <app-progreso *ngIf="tab() === 'progreso'"></app-progreso>
        <app-checkin *ngIf="tab() === 'checkin'"></app-checkin>
      </main>

      <nav class="nu-nav" aria-label="Secciones">
        <button type="button" [class.on]="tab() === 'hoy'" (click)="ir('hoy')" [attr.aria-current]="tab() === 'hoy' ? 'page' : null">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z"/></svg>
          <span>Hoy</span>
        </button>
        <button type="button" [class.on]="tab() === 'menu'" (click)="ir('menu')" [attr.aria-current]="tab() === 'menu' ? 'page' : null">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3v8M5 3v5a2 2 0 0 0 4 0V3M7 11v10M17 3c-2 2-3 5-3 8h3v10"/></svg>
          <span>Menú</span>
        </button>
        <button type="button" class="nu-nav-mas" (click)="abrirAgregar(null)" aria-label="Anotar comida">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        </button>
        <button type="button" [class.on]="tab() === 'progreso'" (click)="ir('progreso')" [attr.aria-current]="tab() === 'progreso' ? 'page' : null">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
          <span>Progreso</span>
        </button>
        <button type="button" [class.on]="tab() === 'checkin'" (click)="ir('checkin')" [attr.aria-current]="tab() === 'checkin' ? 'page' : null">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4h6v3H9zM7 5H5v16h14V5h-2M8.5 14l2.5 2.5 5-5"/></svg>
          <span>Check-in</span>
        </button>
      </nav>

      <app-agregar *ngIf="agregarEn() as t" [inicial]="t" (cerrar)="agregarEn.set(null)"></app-agregar>
    </div>
  `
})
export class NutriComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly esDemo = ES_DEMO;
  readonly titulos: Record<Pestana, string> = { hoy: 'Tu día', menu: 'Menú de la semana', progreso: 'Cómo vas', checkin: 'Check-in' };
  readonly tab = signal<Pestana>(this.tabGuardada());
  readonly agregarEn = signal<string | null>(null);
  readonly bienvenida = signal(!this.leer('nu-bienvenida') && !ES_DEMO);
  readonly saludo = ((h) => (h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'))(new Date().getHours());
  readonly fechaCorta = new Date().toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric', month: 'short' });
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
    this.escribir('nu-tab', p);
  }

  /** El + del centro abre la comida que toca por la hora; el de cada comida, esa. */
  abrirAgregar(tiempo: string | null): void {
    this.nut.cargarMenu();
    this.agregarEn.set(tiempo ?? tiempoPorHora());
  }

  cerrarBienvenida(): void {
    this.escribir('nu-bienvenida', '1');
    this.bienvenida.set(false);
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
    const t = this.leer('nu-tab');
    return t === 'menu' || t === 'progreso' || t === 'checkin' ? t : 'hoy';
  }

  private leer(k: string): string | null {
    try {
      return localStorage.getItem(k);
    } catch {
      return null;
    }
  }

  private escribir(k: string, v: string): void {
    try {
      localStorage.setItem(k, v);
    } catch {
      /* sin espacio: no pasa nada */
    }
  }
}

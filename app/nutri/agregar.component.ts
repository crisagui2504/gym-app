import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, computed, inject, signal } from '@angular/core';
import { NutricionService, PORCIONES, Porcion, TIEMPOS, Tiempo } from '../src/app/nutricion';
import { emojiDe } from './iconos';

/** Hoja de abajo para anotar en una comida: lo del menu de hoy, porciones de casa y "Comi fuera". */
@Component({
  selector: 'app-agregar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ag-fondo" (click)="cerrar.emit()"></div>
    <section class="ag-hoja" role="dialog" aria-modal="true" [attr.aria-label]="'Agregar a ' + tiempo().nombre">
      <div class="ag-asa" aria-hidden="true"></div>
      <div class="ag-top">
        <h2>Agregar a {{ tiempo().nombre }}</h2>
        <button type="button" class="ag-cerrar" (click)="cerrar.emit()" aria-label="Cerrar">✕</button>
      </div>
      <div class="ag-tiempos">
        <button type="button" *ngFor="let t of tiempos" [class.on]="t.id === tiempo().id" (click)="tiempoId.set(t.id)">
          {{ t.ico }} {{ t.nombre }}
        </button>
      </div>
      <input class="ag-buscar" type="search" placeholder="Buscar: huevo, tacos, pollo…" aria-label="Buscar alimento"
             [value]="busqueda()" (input)="busqueda.set($any($event.target).value)">

      <ng-container *ngIf="delMenu() as c">
        <h3>Del menú de hoy</h3>
        <button type="button" class="ag-menu" [class.on]="nut.comioMenu(c.tiempo)"
                (click)="nut.alternarMenu(c.tiempo, c.prot, c)">
          <span class="ag-ico">🍽️</span>
          <span class="ag-txt"><b>{{ c.nombre }}</b>
            <small>{{ c.kcal | number: '1.0-0' }} kcal · P {{ c.prot | number: '1.0-0' }} · C {{ (c.carb ?? 0) | number: '1.0-0' }} · G {{ (c.grasa ?? 0) | number: '1.0-0' }}</small>
          </span>
          <span class="ag-check">{{ nut.comioMenu(c.tiempo) ? '✓' : '+' }}</span>
        </button>
      </ng-container>

      <h3>Porciones de casa</h3>
      <div class="ag-lista">
        <div class="ag-fila" *ngFor="let p of enCasa()" [class.on]="nut.cantidadEn(tiempo(), p.id) > 0">
          <span class="ag-ico">{{ emoji(p.id) }}</span>
          <span class="ag-txt"><b>{{ p.nombre }}<i *ngIf="p.barato">$</i></b><small>{{ p.porcion }} · {{ p.kcal }} kcal · P {{ p.g }} g</small></span>
          <span class="ag-paso">
            <button type="button" *ngIf="nut.cantidadEn(tiempo(), p.id) > 0" (click)="nut.sumarEn(tiempo(), p.id, -1)"
                    [attr.aria-label]="'Quitar ' + p.nombre">−</button>
            <b *ngIf="nut.cantidadEn(tiempo(), p.id) > 0">{{ nut.cantidadEn(tiempo(), p.id) }}</b>
            <button type="button" class="mas" (click)="nut.sumarEn(tiempo(), p.id, 1)" [attr.aria-label]="'Agregar ' + p.nombre">+</button>
          </span>
        </div>
      </div>

      <h3>Comí fuera</h3>
      <div class="ag-lista">
        <div class="ag-fila" *ngFor="let p of fuera()" [class.on]="nut.cantidadEn(tiempo(), p.id) > 0">
          <span class="ag-ico">{{ emoji(p.id) }}</span>
          <span class="ag-txt"><b>{{ p.nombre }}</b><small>{{ p.porcion }} · ~{{ p.kcal }} kcal · P {{ p.g }} g</small></span>
          <span class="ag-paso">
            <button type="button" *ngIf="nut.cantidadEn(tiempo(), p.id) > 0" (click)="nut.sumarEn(tiempo(), p.id, -1)"
                    [attr.aria-label]="'Quitar ' + p.nombre">−</button>
            <b *ngIf="nut.cantidadEn(tiempo(), p.id) > 0">{{ nut.cantidadEn(tiempo(), p.id) }}</b>
            <button type="button" class="mas" (click)="nut.sumarEn(tiempo(), p.id, 1)" [attr.aria-label]="'Agregar ' + p.nombre">+</button>
          </span>
        </div>
      </div>
      <p class="ag-vacio" *ngIf="!enCasa().length && !fuera().length">Nada con "{{ busqueda() }}". Prueba con "Otro" (algo más).</p>
      <p class="ag-nota">Valores aproximados por porción (USDA / SMAE). <b>$</b> = de lo más barato por gramo de proteína.</p>
      <button type="button" class="ag-listo" (click)="cerrar.emit()">Listo</button>
    </section>
  `
})
export class AgregarComponent {
  readonly nut = inject(NutricionService);
  readonly tiempos = TIEMPOS;
  readonly tiempoId = signal('desayuno');
  readonly busqueda = signal('');
  @Input() set inicial(id: string) {
    this.tiempoId.set(id);
  }
  @Output() readonly cerrar = new EventEmitter<void>();

  readonly tiempo = computed<Tiempo>(() => TIEMPOS.find((t) => t.id === this.tiempoId()) ?? TIEMPOS[0]);
  private readonly filtradas = computed(() => {
    const q = this.normal(this.busqueda().trim());
    return q ? PORCIONES.filter((p) => this.normal(p.nombre + ' ' + p.porcion).includes(q)) : PORCIONES;
  });
  readonly enCasa = computed<Porcion[]>(() => this.filtradas().filter((p) => !p.fuera));
  readonly fuera = computed<Porcion[]>(() => this.filtradas().filter((p) => p.fuera));
  /** La comida del menu de hoy para este tiempo (con la opcion que elegiste en "Cambiar"). */
  readonly delMenu = computed(() => {
    const d = this.nut.menuHoy();
    const c = d?.comidas.find((x) => x.tiempo === this.tiempoId());
    return d && c ? this.nut.comidaDe(d, c) : null;
  });

  emoji(id: string): string {
    return emojiDe(id);
  }

  private normal(t: string): string {
    return t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
}

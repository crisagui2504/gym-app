import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject } from '@angular/core';
import { NutricionService, PORCIONES } from './nutricion';

/** Panel "Proteína de hoy": se toca una porción y suma; tocar lo anotado lo resta. */
@Component({
  selector: 'app-proteina',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="panel prot">
      <div class="prot-head">
        <strong>🍗 Proteína de hoy</strong>
        <span class="prot-total"><b>{{ nut.total() | number: '1.0-0' }}</b> / {{ meta().proteina_min }} g</span>
      </div>
      <div class="prot-barra" [class.ok]="nut.pct() >= 100"><div [style.width.%]="nut.pct()"></div></div>
      <p class="prot-hint">
        <ng-container *ngIf="faltan() > 0; else listo">Te faltan <b>{{ faltan() | number: '1.0-0' }} g</b>.</ng-container>
        <ng-template #listo><b>Meta cumplida.</b></ng-template>
        Meta {{ meta().proteina_min }}–{{ meta().proteina_max }} g/día<ng-container *ngIf="meta().peso"> para {{ meta().peso }} kg</ng-container>.
        <ng-container *ngIf="nut.promedio7() !== null"> Promedio de tus últimos días: {{ nut.promedio7() | number: '1.0-0' }} g.</ng-container>
      </p>
      <p class="prot-hint aviso" *ngIf="!nut.meta()">Meta provisional: registra tu peso en el dashboard para calcular la tuya.</p>

      <div class="prot-hoy" *ngIf="anotadas().length">
        <button type="button" *ngFor="let a of anotadas()" (click)="nut.sumar(a.id, -1)" [attr.aria-label]="'Quitar ' + a.nombre">
          {{ a.nombre }} ×{{ a.n }} <span>−</span>
        </button>
      </div>

      <div class="prot-grid">
        <button type="button" class="prot-item" *ngFor="let p of porciones" (click)="nut.sumar(p.id, 1)"
                [class.on]="nut.cantidad(p.id) > 0">
          <span class="prot-nom">{{ p.nombre }}<i *ngIf="p.barato" title="Barato por gramo de proteína">$</i></span>
          <span class="prot-por">{{ p.porcion }}</span>
          <span class="prot-g">+{{ p.g }} g</span>
        </button>
      </div>
      <p class="prot-nota">
        Valores aproximados por porción. <b>$</b> = de lo más barato por gramo de proteína: frijol + tortilla
        se complementan, y huevo, atún y soya rinden mucho. Cuenta el total del día, no la hora.
        <ng-container *ngIf="nut.sinConexion()"> Sin conexión: se guarda en el teléfono y se sube después.</ng-container>
      </p>
    </section>
  `
})
export class ProteinaComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly porciones = PORCIONES;
  readonly meta = this.nut.metaEfectiva;
  readonly faltan = computed(() => Math.max(0, this.meta().proteina_min - this.nut.total()));
  readonly anotadas = computed(() => {
    const p = this.nut.porciones();
    return PORCIONES.filter((x) => (p[x.id] ?? 0) > 0).map((x) => ({ id: x.id, nombre: x.nombre, n: p[x.id] }));
  });

  ngOnInit(): void {
    void this.nut.cargar();
  }
}

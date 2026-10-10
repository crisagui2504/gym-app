import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NutricionService, PORCIONES } from './nutricion';
import type { MenuComida } from './rutina-api.service';

/** Panel "Comida": proteína del día por porciones y el menú barato de la semana. */
@Component({
  selector: 'app-proteina',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="panel prot">
      <div class="seg">
        <button type="button" [class.on]="vista() === 'prot'" (click)="vista.set('prot')">🍗 Proteína</button>
        <button type="button" [class.on]="vista() === 'menu'" (click)="verMenu()">🍽️ Menú</button>
      </div>

      <ng-container *ngIf="vista() === 'prot'">
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
      </ng-container>

      <ng-container *ngIf="vista() === 'menu'">
        <p class="prot-hint" *ngIf="!nut.menu() && nut.cargandoMenu()">Cargando el menú…</p>
        <p class="prot-hint" *ngIf="!nut.menu() && !nut.cargandoMenu()">
          Todavía no hay menú. Se genera con tu rutina el domingo, o en el dashboard, pestaña Menú.
        </p>
        <ng-container *ngIf="nut.menu() as m">
          <p class="menu-res">
            <b>\${{ m.costo_semana | number: '1.0-0' }}</b> a la semana · ~\${{ m.costo_dia | number: '1.0-0' }} al día<br>
            {{ m.kcal_prom | number: '1.0-0' }} kcal y {{ m.prot_prom }} g de proteína al día en promedio
          </p>
          <div class="menu-sel">
            <button type="button" *ngFor="let d of m.dias" [class.on]="diaSel() === d.dia" (click)="diaSel.set(d.dia)">
              {{ d.nombre.slice(0, 3) }}
            </button>
          </div>
          <ng-container *ngIf="dia() as d">
            <p class="menu-dia-tot">{{ d.nombre }} · {{ d.kcal | number: '1.0-0' }} kcal · {{ d.prot }} g · \${{ d.costo | number: '1.0-0' }}</p>
            <div class="menu-comida" *ngFor="let c of d.comidas">
              <span class="menu-t">{{ etiqueta[c.tiempo] || c.tiempo }}</span>
              <div class="menu-nom"><strong>{{ c.nombre }}</strong><small>{{ c.kcal }} kcal · {{ c.prot | number: '1.0-0' }} g</small></div>
              <p class="menu-ing">{{ ingredientes(c) }}</p>
              <p class="menu-como" *ngIf="c.como">{{ c.como }}</p>
            </div>
          </ng-container>
          <p class="prot-hint aviso" *ngFor="let a of m.avisos">{{ a }}</p>
          <details class="menu-lista">
            <summary>🛒 Lista del súper (≈ \${{ m.costo_semana | number: '1.0-0' }})</summary>
            <div class="menu-li" *ngFor="let f of m.lista">
              <span>{{ f.nombre }}</span><span>{{ f.compra }}</span><span>\${{ f.costo | number: '1.0-0' }}</span>
            </div>
          </details>
          <p class="prot-nota">{{ m.nota }} Para cambiar recetas, quitar alimentos o poner tus precios: dashboard, pestaña Menú.</p>
        </ng-container>
      </ng-container>
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

  readonly vista = signal<'prot' | 'menu'>('prot');
  readonly diaSel = signal(((new Date().getDay() + 6) % 7) + 1);     // hoy (1 = lunes)
  readonly dia = computed(() => this.nut.menu()?.dias.find((d) => d.dia === this.diaSel()) ?? null);
  readonly etiqueta: Record<string, string> = { desayuno: 'Desayuno', comida: 'Comida', colacion: 'Colación', cena: 'Cena' };

  ngOnInit(): void {
    void this.nut.cargar();
  }

  verMenu(): void {
    this.vista.set('menu');
    this.nut.cargarMenu();
  }

  ingredientes(c: MenuComida): string {
    return c.ingredientes.map((i) => i.texto).join(', ');
  }
}

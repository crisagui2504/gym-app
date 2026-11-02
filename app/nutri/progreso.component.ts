import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject } from '@angular/core';
import { NutricionService, PESAJES_TENDENCIA } from '../src/app/nutricion';
import { fechaLocal } from '../src/app/entreno-data';

const ANCHO = 320;
const ALTO = 140;
const MARGEN = 14;

/** Progreso: peso (pesajes + media de 7 dias), proteina de 2 semanas y tu meta. */
@Component({
  selector: 'app-progreso',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="nu-card">
      <div class="nu-card-top">
        <h2>⚖️ Peso</h2>
        <span *ngIf="ultimo() as u">{{ u.peso | number: '1.1-1' }} kg</span>
      </div>
      <ng-container *ngIf="grafPeso() as g; else sinPeso">
        <svg class="nu-graf" [attr.viewBox]="'0 0 ' + ancho + ' ' + alto" role="img"
             [attr.aria-label]="'Peso de ' + g.min + ' a ' + g.max + ' kg en los últimos 60 días'">
          <line class="nu-graf-eje" [attr.x1]="margen" [attr.x2]="ancho - margen" [attr.y1]="alto - margen" [attr.y2]="alto - margen"/>
          <polyline class="nu-graf-media" [attr.points]="g.media"/>
          <circle class="nu-graf-punto" *ngFor="let p of g.puntos" [attr.cx]="p.x" [attr.cy]="p.y" r="3"/>
          <text class="nu-graf-txt" [attr.x]="margen" y="10">{{ g.max | number: '1.1-1' }}</text>
          <text class="nu-graf-txt" [attr.x]="margen" [attr.y]="alto - margen - 4">{{ g.min | number: '1.1-1' }}</text>
        </svg>
        <p class="nu-leyenda"><i class="nu-l-punto"></i> pesajes <i class="nu-l-linea"></i> media de 7 días</p>
      </ng-container>
      <ng-template #sinPeso>
        <p class="nu-vacio">Todavía no hay pesajes. Anótalo en <b>Hoy</b>, en ayunas: con unos días aquí aparece tu gráfica.</p>
      </ng-template>
      <p class="nu-dato" *ngIf="nut.tendencia() as t; else sinTend">
        Tendencia <b>{{ conSigno(t.pct, 2) }} %/sem</b> · {{ conSigno(t.kg, 2) }} kg por semana (últimos 21 días)
      </p>
      <ng-template #sinTend>
        <p class="nu-dato" *ngIf="faltan() > 0">Faltan {{ faltan() }} pesaje{{ faltan() !== 1 ? 's' : '' }} para calcular tu tendencia.</p>
      </ng-template>
    </section>

    <section class="nu-card">
      <div class="nu-card-top">
        <h2>🍗 Proteína, 2 semanas</h2>
        <span *ngIf="nut.promedio7() !== null">~{{ nut.promedio7() | number: '1.0-0' }} g/día</span>
      </div>
      <svg class="nu-graf" [attr.viewBox]="'0 0 ' + ancho + ' ' + alto" role="img"
           [attr.aria-label]="'Proteína por día; meta ' + meta().proteina_min + ' g'">
        <rect *ngFor="let b of grafProt().barras" class="nu-graf-barra" [class.ok]="b.ok" [class.hoy]="b.hoy"
              [attr.x]="b.x" [attr.y]="b.y" [attr.width]="b.w" [attr.height]="b.h" rx="3"/>
        <line class="nu-graf-meta" [attr.x1]="margen" [attr.x2]="ancho - margen" [attr.y1]="grafProt().meta" [attr.y2]="grafProt().meta"/>
        <text class="nu-graf-txt nu-graf-txt-meta" [attr.x]="margen" [attr.y]="grafProt().meta - 5">meta {{ meta().proteina_min }} g</text>
      </svg>
      <p class="nu-dato">{{ grafProt().enMeta }} de {{ grafProt().conDato }} días registrados llegaron a la meta.</p>
    </section>

    <section class="nu-card">
      <div class="nu-card-top"><h2>🎯 Tu meta</h2></div>
      <div class="nu-metas">
        <div><b>{{ meta().proteina_min }}–{{ meta().proteina_max }}</b><span>g de proteína al día</span></div>
        <div><b>{{ meta().kcal ? (meta().kcal | number: '1.0-0') : '—' }}</b><span>kcal al día (promedio)</span></div>
        <div><b>{{ nut.rachaCreatina() }}</b><span>día{{ nut.rachaCreatina() !== 1 ? 's' : '' }} seguidos de creatina</span></div>
      </div>
      <p class="nu-nota" *ngIf="nut.meta(); else provisional">
        Calculada por el motor para {{ meta().peso }} kg<ng-container *ngIf="meta().enfoque"> y tu enfoque ({{ meta().enfoque }})</ng-container>.
        Se ajusta sola con tu peso.
      </p>
      <ng-template #provisional>
        <p class="nu-nota">Meta provisional: anota tu peso y el motor calcula la tuya en unas horas.</p>
      </ng-template>
    </section>
  `
})
export class ProgresoComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly ancho = ANCHO;
  readonly alto = ALTO;
  readonly margen = MARGEN;
  readonly meta = this.nut.metaEfectiva;
  readonly faltan = computed(() => Math.max(0, PESAJES_TENDENCIA - this.nut.pesajes21()));
  readonly ultimo = computed(() => this.nut.pesos().at(-1) ?? null);

  /** Pesajes de los ultimos 60 dias como puntos, y la media de 7 dias como linea. */
  readonly grafPeso = computed(() => {
    const desde = new Date();
    desde.setDate(desde.getDate() - 60);
    const d = this.nut.pesos().filter((p) => p.fecha >= fechaLocal(desde));
    if (d.length < 2) return null;
    const t = (f: string) => new Date(f + 'T12:00:00').getTime() / 864e5;
    const t0 = t(d[0].fecha);
    const rango = Math.max(1, t(d[d.length - 1].fecha) - t0);
    const pesos = d.map((p) => p.peso);
    const min = Math.floor((Math.min(...pesos) - 0.3) * 2) / 2;
    const max = Math.ceil((Math.max(...pesos) + 0.3) * 2) / 2;
    const x = (f: string) => MARGEN + ((t(f) - t0) / rango) * (ANCHO - 2 * MARGEN);
    const y = (kg: number) => MARGEN + ((max - kg) / (max - min)) * (ALTO - 2 * MARGEN);
    const media = d.map((p) => {
      const vent = d.filter((q) => t(q.fecha) <= t(p.fecha) && t(q.fecha) > t(p.fecha) - 7);
      return `${x(p.fecha).toFixed(1)},${y(vent.reduce((s, q) => s + q.peso, 0) / vent.length).toFixed(1)}`;
    });
    return { puntos: d.map((p) => ({ x: x(p.fecha), y: y(p.peso) })), media: media.join(' '), min, max };
  });

  /** Barras de los ultimos 14 dias (los dias sin registro quedan en cero) contra la meta. */
  readonly grafProt = computed(() => {
    const porDia = new Map(this.nut.proteinaDias().map((d) => [d.fecha, d.g]));
    const metaG = this.meta().proteina_min;
    const dias = Array.from({ length: 14 }, (_, i) => {
      const f = new Date();
      f.setDate(f.getDate() - (13 - i));
      return fechaLocal(f);
    });
    const tope = Math.max(metaG * 1.25, ...dias.map((f) => porDia.get(f) ?? 0));
    const paso = (ANCHO - 2 * MARGEN) / 14;
    const alto = ALTO - 2 * MARGEN;
    const hoy = fechaLocal(new Date());
    const barras = dias.map((f, i) => {
      const g = porDia.get(f) ?? 0;
      const h = Math.max(2, (g / tope) * alto);
      return { x: MARGEN + i * paso + 2, w: paso - 4, h, y: ALTO - MARGEN - h, ok: g >= metaG, hoy: f === hoy };
    });
    const conDato = dias.filter((f) => (porDia.get(f) ?? 0) > 0).length;
    const enMeta = dias.filter((f) => (porDia.get(f) ?? 0) >= metaG).length;
    return { barras, meta: ALTO - MARGEN - (metaG / tope) * alto, conDato, enMeta };
  });

  ngOnInit(): void {
    void this.nut.cargar();
  }

  /** +0.25 / −0.10 / ±0.00 (nunca "-0.00"). */
  conSigno(v: number, dec: number): string {
    const r = Math.round(v * 10 ** dec) / 10 ** dec + 0;
    return (r > 0 ? '+' : r < 0 ? '−' : '±') + Math.abs(r).toFixed(dec);
  }
}

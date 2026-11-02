import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NutricionService, PESAJES_TENDENCIA } from '../src/app/nutricion';

/** Check-in semanal (como MacroFactor): tendencia del peso contra tu objetivo, tu
 *  adherencia de 7 dias y la sugerencia de kcal con "Aplicar". La evaluacion la
 *  hace el motor (python-engine/nutricion.py checkin) y la aplica en la VM. */
@Component({
  selector: 'app-checkin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <p class="nu-vacio" *ngIf="!ev() && !nut.cargandoCheckin()">
      El motor aún no hace tu primer check-in: se calcula en el servidor cada 3 horas. Mientras, anota tu peso y tu comida.
    </p>
    <p class="nu-vacio" *ngIf="!ev() && nut.cargandoCheckin()">Cargando tu check-in…</p>

    <ng-container *ngIf="ev() as e">
      <section class="ci-hero" [class]="'ci-hero e-' + e.estado">
        <small>Check-in del {{ fechaLarga(e.fecha) }}</small>
        <h2>{{ titulo[e.estado] }}</h2>
        <p>{{ e.consejo.charAt(0).toUpperCase() + e.consejo.slice(1) }}.</p>
      </section>

      <section class="nu-card">
        <div class="nu-card-top"><h2>⚖️ Tu peso</h2><span *ngIf="e.tendencia !== null">{{ conSigno(e.tendencia) }} %/sem</span></div>
        <div class="ci-rango" *ngIf="e.tendencia !== null; else faltanPeso" role="img"
             [attr.aria-label]="'Tendencia ' + conSigno(e.tendencia) + ' por semana; objetivo de ' + conSigno(e.objetivo[0]) + ' a ' + conSigno(e.objetivo[1])">
          <span class="ci-rango-meta" [style.left.%]="pos(e.objetivo[0])" [style.width.%]="pos(e.objetivo[1]) - pos(e.objetivo[0])"></span>
          <span class="ci-rango-tu" [style.left.%]="pos(e.tendencia)"></span>
        </div>
        <ng-template #faltanPeso>
          <p class="nu-dato">Faltan {{ faltan() }} pesaje{{ faltan() !== 1 ? 's' : '' }} (en 2-3 semanas) para ver tu tendencia.</p>
        </ng-template>
        <p class="nu-dato">
          Objetivo de tu enfoque ({{ e.enfoque }}): <b>{{ conSigno(e.objetivo[0]) }} a {{ conSigno(e.objetivo[1]) }} %</b> de tu peso por semana.
          <ng-container *ngIf="e.cintura_sem !== null"> Cintura: {{ conSigno(e.cintura_sem) }} cm/semana.</ng-container>
        </p>
      </section>

      <section class="nu-card">
        <div class="nu-card-top"><h2>📋 Tu semana</h2><span>{{ e.proteina.dias }}/7 días</span></div>
        <div class="ci-adh">
          <div class="m-prot"><b>{{ e.proteina.promedio !== null ? (e.proteina.promedio | number: '1.0-0') : '—' }}</b><span>g de proteína / día (meta {{ e.proteina.meta }})</span></div>
          <div class="m-kcal"><b>{{ nut.semana7().kcal !== null ? (nut.semana7().kcal! | number: '1.0-0') : '—' }}</b><span>kcal / día anotadas (meta {{ e.kcal | number: '1.0-0' }})</span></div>
          <div class="m-carb"><b>{{ e.proteina.en_meta }}</b><span>días con la proteína cumplida</span></div>
          <div class="m-grasa"><b>{{ e.creatina_dias }}</b><span>días con creatina</span></div>
        </div>
      </section>

      <section class="nu-card ci-accion" *ngIf="e.estado === 'subir' || e.estado === 'bajar'">
        <div class="nu-card-top"><h2>🎯 Ajuste sugerido</h2></div>
        <b class="ci-delta">{{ e.kcal_delta > 0 ? '+' : '−' }}{{ abs(e.kcal_delta) }} kcal/día</b>
        <p class="nu-dato">≈ {{ abs(e.kcal_delta) / 4 | number: '1.0-0' }} g de carbohidratos {{ e.kcal_delta > 0 ? 'más' : 'menos' }} al día
          (100 kcal ≈ 1½ tortillas o ½ taza de arroz). Tu meta pasaría de {{ e.kcal | number: '1.0-0' }} a {{ e.kcal + e.kcal_delta | number: '1.0-0' }} kcal.</p>
        <ng-container *ngIf="pendiente() as p; else botonAplicar">
          <p class="ci-pendiente">✓ Pedido. El motor lo aplica en las próximas horas (revisa cada 3 h) y tu menú y tus metas se ajustan solos.</p>
          <button type="button" class="ci-cancelar" (click)="ajustar(null)" [disabled]="enviando()">Cancelar</button>
        </ng-container>
        <ng-template #botonAplicar>
          <button type="button" class="ci-aplicar" (click)="ajustar(e.kcal_delta)" [disabled]="enviando()">
            Aplicar {{ e.kcal_delta > 0 ? '+' : '−' }}{{ abs(e.kcal_delta) }} kcal
          </button>
        </ng-template>
        <p class="ci-error" *ngIf="error()">{{ error() }}</p>
      </section>

      <p class="nu-nota" *ngIf="e.aplicado as a">✓ Ajuste de {{ a.delta > 0 ? '+' : '−' }}{{ abs(a.delta) }} kcal aplicado el {{ fechaLarga(a.fecha) }}.</p>
      <p class="nu-nota">
        Cómo funciona: la báscula diaria cambia 1-2 kg por agua y comida; lo que cuenta es la tendencia de 3 semanas.
        Los ajustes son chicos (100-300 kcal) y se reevalúan a las 2 semanas, que es lo que tarda en verse un cambio.
        Tu meta actual: {{ e.kcal | number: '1.0-0' }} kcal ({{ e.kcal_base | number: '1.0-0' }} de partida
        {{ e.kcal_ajuste >= 0 ? '+' : '−' }} {{ abs(e.kcal_ajuste) }} de ajustes).
      </p>
    </ng-container>
  `
})
export class CheckinComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly ev = computed(() => this.nut.checkin()?.evaluacion ?? null);
  readonly pendiente = computed(() => this.nut.checkin()?.pendiente ?? null);
  readonly faltan = computed(() => Math.max(0, PESAJES_TENDENCIA - this.nut.pesajes21()));
  readonly enviando = signal(false);
  readonly error = signal('');
  readonly titulo: Record<string, string> = {
    subir: 'Te conviene comer un poco más', bajar: 'Te conviene comer un poco menos', en_rango: 'Vas justo donde quieres',
    recomposicion: 'Recomposición en marcha', esperando: 'Dale tiempo a tu último ajuste', pocos_datos: 'Faltan pesajes'
  };

  ngOnInit(): void {
    void this.nut.cargar();
    this.nut.cargarCheckin();
  }

  async ajustar(delta: number | null): Promise<void> {
    this.enviando.set(true);
    this.error.set(await this.nut.ajustarKcal(delta));
    this.enviando.set(false);
  }

  /** Posicion en la barra de -1.5 a +1.5 %/semana. */
  pos(v: number): number {
    return Math.max(0, Math.min(100, ((v + 1.5) / 3) * 100));
  }

  abs(v: number): number {
    return Math.abs(v);
  }

  conSigno(v: number): string {
    const r = Math.round(v * 100) / 100 + 0;
    return (r > 0 ? '+' : r < 0 ? '−' : '±') + Math.abs(r).toFixed(2);
  }

  fechaLarga(f: string): string {
    return new Date(f.slice(0, 10) + 'T12:00:00').toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
  }
}

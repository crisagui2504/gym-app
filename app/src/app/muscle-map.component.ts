import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MuscleId } from './entreno-data';

@Component({
  selector: 'app-muscle-map',
  standalone: true,
  imports: [CommonModule],
  template: `
    <svg viewBox="0 0 210 160" xmlns="http://www.w3.org/2000/svg" class="bodymap" role="img"
         [attr.aria-label]="'Musculos trabajados'">
      <!-- ===== FIGURA FRONTAL ===== -->
      <g class="base">
        <circle cx="50" cy="16" r="8" />
        <rect x="46" y="22" width="8" height="6" rx="2" />
        <rect x="36" y="29" width="28" height="38" rx="7" />
        <rect x="26" y="31" width="8" height="40" rx="4" />
        <rect x="66" y="31" width="8" height="40" rx="4" />
        <rect x="38" y="65" width="24" height="9" rx="3" />
        <rect x="40" y="72" width="10" height="62" rx="4" />
        <rect x="50" y="72" width="10" height="62" rx="4" />
      </g>
      <g class="muscles">
        <ellipse cx="38" cy="34" rx="5" ry="4" [class.on]="on('hombros')" [style.fill]="tono('hombros')" />
        <ellipse cx="62" cy="34" rx="5" ry="4" [class.on]="on('hombros')" [style.fill]="tono('hombros')" />
        <rect x="40" y="38" width="9" height="9" rx="3" [class.on]="on('pecho')" [style.fill]="tono('pecho')" />
        <rect x="51" y="38" width="9" height="9" rx="3" [class.on]="on('pecho')" [style.fill]="tono('pecho')" />
        <rect x="46" y="48" width="8" height="16" rx="3" [class.on]="on('abdomen')" [style.fill]="tono('abdomen')" />
        <ellipse cx="30" cy="44" rx="3.6" ry="7" [class.on]="on('biceps')" [style.fill]="tono('biceps')" />
        <ellipse cx="70" cy="44" rx="3.6" ry="7" [class.on]="on('biceps')" [style.fill]="tono('biceps')" />
        <ellipse cx="30" cy="62" rx="3.4" ry="7" [class.on]="on('antebrazos')" [style.fill]="tono('antebrazos')" />
        <ellipse cx="70" cy="62" rx="3.4" ry="7" [class.on]="on('antebrazos')" [style.fill]="tono('antebrazos')" />
        <rect x="41" y="78" width="8" height="26" rx="3" [class.on]="on('cuadriceps')" [style.fill]="tono('cuadriceps')" />
        <rect x="51" y="78" width="8" height="26" rx="3" [class.on]="on('cuadriceps')" [style.fill]="tono('cuadriceps')" />
      </g>

      <!-- ===== FIGURA POSTERIOR ===== -->
      <g class="base">
        <circle cx="160" cy="16" r="8" />
        <rect x="156" y="22" width="8" height="6" rx="2" />
        <rect x="146" y="29" width="28" height="38" rx="7" />
        <rect x="136" y="31" width="8" height="40" rx="4" />
        <rect x="174" y="31" width="8" height="40" rx="4" />
        <rect x="148" y="65" width="24" height="9" rx="3" />
        <rect x="150" y="72" width="10" height="62" rx="4" />
        <rect x="160" y="72" width="10" height="62" rx="4" />
      </g>
      <g class="muscles">
        <rect x="152" y="31" width="16" height="8" rx="3" [class.on]="on('trapecios')" [style.fill]="tono('trapecios')" />
        <rect x="147" y="41" width="11" height="14" rx="3" [class.on]="on('dorsales')" [style.fill]="tono('dorsales')" />
        <rect x="162" y="41" width="11" height="14" rx="3" [class.on]="on('dorsales')" [style.fill]="tono('dorsales')" />
        <ellipse cx="140" cy="44" rx="3.6" ry="7" [class.on]="on('triceps')" [style.fill]="tono('triceps')" />
        <ellipse cx="180" cy="44" rx="3.6" ry="7" [class.on]="on('triceps')" [style.fill]="tono('triceps')" />
        <rect x="154" y="56" width="12" height="9" rx="2" [class.on]="on('lumbar')" [style.fill]="tono('lumbar')" />
        <rect x="150" y="66" width="9" height="9" rx="3" [class.on]="on('gluteos')" [style.fill]="tono('gluteos')" />
        <rect x="161" y="66" width="9" height="9" rx="3" [class.on]="on('gluteos')" [style.fill]="tono('gluteos')" />
        <rect x="151" y="78" width="8" height="24" rx="3" [class.on]="on('isquios')" [style.fill]="tono('isquios')" />
        <rect x="161" y="78" width="8" height="24" rx="3" [class.on]="on('isquios')" [style.fill]="tono('isquios')" />
        <rect x="151" y="106" width="8" height="22" rx="3" [class.on]="on('gemelos')" [style.fill]="tono('gemelos')" />
        <rect x="161" y="106" width="8" height="22" rx="3" [class.on]="on('gemelos')" [style.fill]="tono('gemelos')" />
      </g>

      <text x="50" y="150" class="cap">Frente</text>
      <text x="160" y="150" class="cap">Espalda</text>
    </svg>
  `,
  styles: [
    `
      .bodymap {
        width: 100%;
        height: auto;
        display: block;
      }
      .base rect,
      .base circle {
        fill: var(--map-base, #2a3340);
      }
      .muscles rect,
      .muscles ellipse {
        fill: var(--map-off, #3d4858);
        transition: fill 0.2s ease;
      }
      .muscles .on {
        fill: var(--map-on, #f59e0b);
      }
      .cap {
        fill: var(--map-cap, #94a3b8);
        font-size: 9px;
        font-weight: 700;
        text-anchor: middle;
        font-family: inherit;
      }
    `
  ]
})
export class MuscleMapComponent {
  @Input() muscles: MuscleId[] = [];
  /** Modo recuperacion: fatiga 0..1 por musculo. Si viene, colorea TODOS los
   *  musculos (lima = listo, ambar = a medias, rojo = todavia cargado). */
  @Input() niveles: Partial<Record<MuscleId, number>> | null = null;

  on(id: MuscleId): boolean {
    return this.muscles.includes(id);
  }

  tono(id: MuscleId): string | null {
    if (!this.niveles) return null;
    const f = this.niveles[id] ?? 0;
    return f >= 0.6 ? '#ff6b6b' : f >= 0.25 ? '#ffc043' : '#aaff00';
  }
}

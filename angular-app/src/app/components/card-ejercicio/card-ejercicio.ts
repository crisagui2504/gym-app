import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RpeSliderComponent } from '../rpe-slider/rpe-slider';

@Component({
  selector: 'app-card-ejercicio',
  standalone: true,
  imports: [CommonModule, FormsModule, RpeSliderComponent],
  template: `
    <div class="glass-panel card">
      <div class="card-header">
        <div class="exercise-info">
          <h3>{{ ejercicio.ejercicio }}</h3>
          <p class="target">Objetivo: {{ ejercicio.series_objetivo }}x{{ ejercicio.reps_objetivo }} &#64; {{ ejercicio.peso_objetivo }}kg</p>
        </div>
      </div>
      
      <div class="series-list">
        <div class="serie-row" *ngFor="let s of seriesRegistradas; let i = index">
          <span class="serie-num">Serie {{ i + 1 }}</span>
          <div class="inputs">
            <input type="number" [(ngModel)]="s.repeticiones" class="input-glass" placeholder="Reps">
            <input type="number" [(ngModel)]="s.peso" step="1.25" class="input-glass" placeholder="Peso (kg)">
          </div>
          <app-rpe-slider [(rpe)]="s.rpe"></app-rpe-slider>
        </div>
      </div>

      <div class="actions">
        <button class="btn-neon-cyan add-serie" (click)="agregarSerie()" *ngIf="seriesRegistradas.length < ejercicio.series_objetivo">
          + Añadir Serie
        </button>
        <button class="btn-neon-emerald complete-btn" (click)="completarEjercicio()" *ngIf="seriesRegistradas.length > 0">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 6px;">
            <path d="M20 6L9 17l-5-5"></path>
          </svg>
          Completar
        </button>
      </div>
    </div>
  `,
  styles: [`
    .card {
      padding: 20px;
      margin-bottom: 24px;
      transition: transform 0.3s ease;
    }
    .card:hover {
      transform: translateY(-2px);
    }
    .card-header {
      border-bottom: 1px solid var(--border-glass);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }
    .card-header h3 {
      margin-bottom: 4px;
      font-size: 1.25rem;
    }
    .target {
      color: var(--accent-emerald);
      font-weight: 600;
      font-size: 0.9rem;
    }
    .serie-row {
      background: rgba(0,0,0,0.2);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
    }
    .serie-num {
      display: block;
      color: var(--text-muted);
      margin-bottom: 8px;
      font-weight: 600;
    }
    .inputs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .input-glass {
      background: var(--bg-glass);
      border: 1px solid var(--border-glass);
      color: var(--text-main);
      padding: 12px;
      border-radius: 8px;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.3s;
    }
    .input-glass:focus {
      border-color: var(--accent-cyan);
    }
    .actions {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 16px;
    }
    .add-serie, .complete-btn {
      width: 100%;
    }
  `]
})
export class CardEjercicioComponent {
  @Input() ejercicio: any;
  @Output() ejercicioCompletado = new EventEmitter<any[]>();

  seriesRegistradas: any[] = [];

  ngOnInit() {
    this.agregarSerie(); // Serie inicial
  }

  agregarSerie() {
    this.seriesRegistradas.push({
      ejercicio: this.ejercicio.ejercicio,
      serie_num: this.seriesRegistradas.length + 1,
      repeticiones: this.ejercicio.reps_objetivo,
      peso: this.ejercicio.peso_objetivo,
      rpe: this.ejercicio.rpe_objetivo
    });
  }

  completarEjercicio() {
    this.ejercicioCompletado.emit(this.seriesRegistradas);
  }
}

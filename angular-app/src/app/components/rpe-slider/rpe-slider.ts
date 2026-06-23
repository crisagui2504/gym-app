import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-rpe-slider',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="slider-container">
      <div class="slider-header">
        <span class="label">RPE</span>
        <span class="value" [class.high-rpe]="rpe >= 9">{{ rpe | number:'1.1-1' }}</span>
      </div>
      <input 
        type="range" 
        min="5" max="10" step="0.5" 
        [(ngModel)]="rpe" 
        (ngModelChange)="rpeChange.emit(rpe)"
        class="neon-slider"
      >
      <div class="slider-marks">
        <span>5</span>
        <span>7.5</span>
        <span>10</span>
      </div>
    </div>
  `,
  styles: [`
    .slider-container {
      margin-top: 16px;
    }
    .slider-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
    }
    .label {
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.9rem;
    }
    .value {
      font-weight: 800;
      color: var(--accent-cyan);
      font-size: 1.1rem;
    }
    .value.high-rpe {
      color: var(--accent-danger);
    }
    .neon-slider {
      width: 100%;
      -webkit-appearance: none;
      background: transparent;
    }
    .neon-slider::-webkit-slider-runnable-track {
      width: 100%;
      height: 6px;
      background: var(--bg-glass);
      border-radius: 4px;
      border: 1px solid var(--border-glass);
    }
    .neon-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      height: 20px;
      width: 20px;
      border-radius: 50%;
      background: var(--accent-cyan);
      box-shadow: 0 0 10px var(--accent-cyan-glow);
      cursor: pointer;
      margin-top: -8px;
      transition: transform 0.1s;
    }
    .neon-slider::-webkit-slider-thumb:active {
      transform: scale(1.2);
    }
    .slider-marks {
      display: flex;
      justify-content: space-between;
      margin-top: 4px;
      font-size: 0.75rem;
      color: var(--text-muted);
    }
  `]
})
export class RpeSliderComponent {
  @Input() rpe: number = 8.0;
  @Output() rpeChange = new EventEmitter<number>();
}

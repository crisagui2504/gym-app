import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CardEjercicioComponent } from '../../components/card-ejercicio/card-ejercicio';
import { Router } from '@angular/router';

@Component({
  selector: 'app-vista-gimnasio',
  standalone: true,
  imports: [CommonModule, HttpClientModule, CardEjercicioComponent],
  template: `
    <div class="header">
      <h1>Rutina de Hoy</h1>
      <button class="btn-neon-cyan icon-btn" (click)="irAdmin()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </button>
    </div>

    <div *ngIf="cargando()" class="loading">
      <div class="spinner"></div>
      <p>Cargando rutina...</p>
    </div>

    <div *ngIf="!cargando() && rutina().length === 0" class="empty-state glass-panel">
      <h3>Día de Descanso</h3>
      <p>No hay rutina programada para hoy. ¡Recupera energías!</p>
    </div>

    <div class="rutina-list" *ngIf="!cargando() && rutina().length > 0">
      <app-card-ejercicio 
        *ngFor="let ej of rutina(); let i = index" 
        [ejercicio]="ej"
        (ejercicioCompletado)="guardarSeries($event, i)"
        [class.hidden]="i !== ejercicioActualIndex()"
      ></app-card-ejercicio>

      <div *ngIf="ejercicioActualIndex() >= rutina().length" class="empty-state glass-panel success-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <h3>¡Entrenamiento Completado!</h3>
        <p>Has terminado todos los ejercicios de hoy.</p>
        <button class="btn-neon-emerald" style="margin-top: 16px;" (click)="enviarEntrenamiento()" [disabled]="enviando()">
          {{ enviando() ? 'Guardando...' : 'Sincronizar Entrenamiento' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .icon-btn {
      padding: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
    }
    .hidden {
      display: none;
    }
    .loading {
      text-align: center;
      padding: 40px;
      color: var(--text-muted);
    }
    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid var(--border-glass);
      border-top-color: var(--accent-cyan);
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 16px;
    }
    @keyframes spin { 100% { transform: rotate(360deg); } }
    .empty-state {
      padding: 40px 20px;
      text-align: center;
    }
    .empty-state h3 {
      color: var(--accent-cyan);
    }
    .success-state h3 {
      color: var(--accent-emerald);
      margin-top: 16px;
    }
  `]
})
export class VistaGimnasioComponent {
  private http = inject(HttpClient);
  private router = inject(Router);

  rutina = signal<any[]>([]);
  cargando = signal(true);
  enviando = signal(false);
  ejercicioActualIndex = signal(0);
  
  todasLasSeries: any[] = [];

  // API_BASE es relativo asumiendo que están en la misma carpeta o usamos path absoluto si es dev
  // En producción (InfinityFree) estarán en la misma raíz, en desarrollo podemos poner la ruta local si queremos, pero lo dejamos genérico.
  API_BASE = '/infinityfree'; // Modifica según tu entorno local vs prod

  ngOnInit() {
    this.cargarRutina();
  }

  cargarRutina() {
    // Si usas ng serve, esto dará 404 a menos que configures un proxy, 
    // pero para InfinityFree en producción funcionará si compilas a la raíz.
    // Usaremos una ruta relativa simple asumiendo despliegue unificado.
    const url = 'get_rutina_hoy.php'; 
    
    this.http.get<any>(url).subscribe({
      next: (res) => {
        if(res.status === 'success') {
          this.rutina.set(res.data);
        }
        this.cargando.set(false);
      },
      error: (err) => {
        console.error('Error cargando rutina, simulando datos de prueba', err);
        // Fallback de prueba para que puedas ver el UI en tu local si no tienes PHP corriendo
        this.rutina.set([
          { ejercicio: 'Press de Banca', series_objetivo: 4, reps_objetivo: 10, peso_objetivo: 60, rpe_objetivo: 8 },
          { ejercicio: 'Remo con Barra', series_objetivo: 3, reps_objetivo: 12, peso_objetivo: 50, rpe_objetivo: 7.5 }
        ]);
        this.cargando.set(false);
      }
    });
  }

  guardarSeries(series: any[], index: number) {
    this.todasLasSeries.push(...series);
    this.ejercicioActualIndex.update(v => v + 1);
  }

  enviarEntrenamiento() {
    this.enviando.set(true);
    this.http.post<any>('guardar_entreno.php', { series: this.todasLasSeries }).subscribe({
      next: (res) => {
        alert('Entrenamiento guardado con éxito!');
        this.enviando.set(false);
      },
      error: (err) => {
        console.error('Error al guardar', err);
        alert('Modo Dev: Simulación de guardado exitoso.');
        this.enviando.set(false);
      }
    });
  }

  irAdmin() {
    this.router.navigate(['/sync']);
  }
}

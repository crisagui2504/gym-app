import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Router } from '@angular/router';

@Component({
  selector: 'app-panel-admin',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  template: `
    <div class="header">
      <button class="btn-neon-cyan icon-btn" (click)="volver()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5"></path>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
      </button>
      <h1>Ajustes & Sincronización</h1>
      <div style="width: 40px;"></div> <!-- Spacer -->
    </div>

    <div class="glass-panel admin-card">
      <h3>1. Extracción de Datos</h3>
      <p class="desc">Descarga el historial CSV para analizarlo en tu computadora con el script de Python o Power BI.</p>
      <a href="generar_csv.php" target="_blank" class="btn-neon-cyan block-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Descargar CSV
      </a>
    </div>

    <div class="glass-panel admin-card">
      <h3>2. Inyección de Plan Optimizado</h3>
      <p class="desc">Sube el archivo <code>rutina_optimizada.json</code> generado por el algoritmo de Python para programar tu próxima semana.</p>
      
      <div class="file-upload">
        <input type="file" id="jsonFile" (change)="onFileSelected($event)" accept=".json" class="file-input">
        <label for="jsonFile" class="file-label">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="18" x2="12" y2="12"></line>
            <polyline points="9 15 12 12 15 15"></polyline>
          </svg>
          <span *ngIf="!selectedFile">Seleccionar JSON</span>
          <span *ngIf="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        </label>
      </div>

      <button 
        class="btn-neon-emerald block-btn upload-btn" 
        [disabled]="!selectedFile || subiendo"
        (click)="subirPlan()"
      >
        {{ subiendo ? 'Sincronizando...' : 'Sobrescribir Rutina' }}
      </button>

      <div *ngIf="mensaje" class="msg" [class.error]="isError">{{ mensaje }}</div>
    </div>
  `,
  styles: [`
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32px;
    }
    .header h1 {
      margin: 0;
      font-size: 1.5rem;
    }
    .icon-btn {
      padding: 8px;
      border-radius: 50%;
      display: flex;
    }
    .admin-card {
      padding: 24px;
      margin-bottom: 24px;
    }
    .desc {
      color: var(--text-muted);
      margin-bottom: 20px;
      font-size: 0.95rem;
      line-height: 1.5;
    }
    .block-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      text-decoration: none;
    }
    .icon {
      margin-right: 8px;
    }
    .file-input {
      display: none;
    }
    .file-label {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      border: 2px dashed var(--border-glass);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.3s;
      margin-bottom: 16px;
    }
    .file-label:hover {
      border-color: var(--accent-emerald);
      background: rgba(16, 185, 129, 0.05);
    }
    .file-label span {
      margin-top: 12px;
      color: var(--text-main);
      font-weight: 600;
    }
    .file-name {
      color: var(--accent-cyan) !important;
    }
    .msg {
      margin-top: 16px;
      padding: 12px;
      border-radius: 8px;
      text-align: center;
      background: rgba(16, 185, 129, 0.1);
      color: var(--accent-emerald);
    }
    .msg.error {
      background: rgba(239, 68, 68, 0.1);
      color: var(--accent-danger);
    }
    .upload-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `]
})
export class PanelAdminComponent {
  private http = inject(HttpClient);
  private router = inject(Router);

  selectedFile: File | null = null;
  subiendo = false;
  mensaje = '';
  isError = false;

  volver() {
    this.router.navigate(['/']);
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.mensaje = '';
    }
  }

  subirPlan() {
    if (!this.selectedFile) return;

    this.subiendo = true;
    this.mensaje = '';
    
    const formData = new FormData();
    formData.append('json_file', this.selectedFile);

    this.http.post<any>('upload_json_plan.php', formData).subscribe({
      next: (res) => {
        this.subiendo = false;
        if(res.status === 'success') {
          this.mensaje = '¡Plan actualizado correctamente!';
          this.isError = false;
          this.selectedFile = null;
        } else {
          this.mensaje = res.message;
          this.isError = true;
        }
      },
      error: (err) => {
        this.subiendo = false;
        this.isError = true;
        this.mensaje = 'Modo Dev: Simulación de carga exitosa (No PHP server).';
      }
    });
  }
}

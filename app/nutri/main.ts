import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { NutriComponent } from './nutri.component';
import { RutinaApiService } from '../src/app/rutina-api.service';
import { DemoApiService, ES_DEMO, activarAlmacenDemo } from '../src/app/demo';

// La app de nutricion reutiliza la logica de GymTracker (src/app/nutricion.ts,
// menu-semana.ts, almacen.ts) con su propio diseno. ?demo=1: datos simulados.
if (ES_DEMO) activarAlmacenDemo();

bootstrapApplication(NutriComponent, {
  providers: [
    provideHttpClient(),
    ...(ES_DEMO ? [DemoApiService, { provide: RutinaApiService, useExisting: DemoApiService }] : [])
  ]
}).catch((err) => console.error(err));

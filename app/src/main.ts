import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { AppComponent } from './app/app.component';
import { RutinaApiService } from './app/rutina-api.service';
import { DemoApiService, ES_DEMO, activarAlmacenDemo } from './app/demo';

// Modo demo (oculto): almacen en memoria y API local, ANTES de arrancar la app,
// para que nada real se lea ni se escriba. Ver app/demo.ts.
if (ES_DEMO) activarAlmacenDemo();

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(),
    ...(ES_DEMO ? [{ provide: RutinaApiService, useClass: DemoApiService }] : [])
  ]
}).catch((err) => console.error(err));

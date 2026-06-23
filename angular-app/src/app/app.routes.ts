import { Routes } from '@angular/router';
import { VistaGimnasioComponent } from './pages/vista-gimnasio/vista-gimnasio';
import { PanelAdminComponent } from './pages/panel-admin/panel-admin';

export const routes: Routes = [
  { path: '', component: VistaGimnasioComponent },
  { path: 'sync', component: PanelAdminComponent },
  { path: '**', redirectTo: '' }
];

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output, computed, inject, signal } from '@angular/core';
import { NutricionService, PESAJES_TENDENCIA, desglosar } from '../src/app/nutricion';
import { fechaLocal } from '../src/app/entreno-data';
import { emojiDe } from './iconos';

const R_FUERA = 86;      // anillo de kcal
const R_DENTRO = 68;     // anillo de proteina

/** Hoy: semana, calorias y macros contra tu meta del dia, comidas y habitos. */
@Component({
  selector: 'app-hoy',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="hy-semana" aria-label="Esta semana">
      <button type="button" *ngFor="let d of semana()" [class.on]="d.fecha === fechaSel()" [class.hoy]="d.esHoy"
              [class.futuro]="d.futuro" [disabled]="d.futuro" (click)="fechaSel.set(d.fecha)"
              [attr.aria-label]="d.largo + (d.conDatos ? ', con registro' : '')">
        <small>{{ d.letra }}</small><b>{{ d.num }}</b><i [class.si]="d.conDatos" aria-hidden="true"></i>
      </button>
    </section>

    <p class="hy-pasado" *ngIf="!esHoy()">
      Viendo el {{ fechaTexto() }} (solo lectura). <button type="button" (click)="fechaSel.set(hoy)">Volver a hoy</button>
    </p>

    <section class="hy-tracker">
      <div class="hy-tracker-top">
        <h2>Calorías</h2>
        <span class="hy-tipo" *ngIf="esHoy() && nut.menuHoy()?.tipo as tipo">día de {{ tipo }}</span>
      </div>
      <div class="hy-anillo" role="img"
           [attr.aria-label]="(dia().total.kcal | number: '1.0-0') + ' de ' + meta().kcal + ' kcal; proteína ' + (dia().total.prot | number: '1.0-0') + ' de ' + meta().prot + ' g'">
        <svg viewBox="0 0 200 200" aria-hidden="true">
          <circle class="hy-pista" cx="100" cy="100" [attr.r]="rFuera"/>
          <circle class="hy-kcal" cx="100" cy="100" [attr.r]="rFuera" [attr.stroke-dasharray]="arco(dia().total.kcal, meta().kcal, rFuera)"
                  [class.pasado]="dia().total.kcal > meta().kcal * 1.05" [class.cero]="!dia().total.kcal"/>
          <circle class="hy-pista" cx="100" cy="100" [attr.r]="rDentro"/>
          <circle class="hy-prot" cx="100" cy="100" [attr.r]="rDentro" [attr.stroke-dasharray]="arco(dia().total.prot, meta().prot, rDentro)" [class.cero]="!dia().total.prot"/>
        </svg>
        <div class="hy-anillo-txt">
          <span class="hy-flama" aria-hidden="true">🔥</span>
          <small>de {{ meta().kcal | number: '1.0-0' }} kcal</small>
          <b>{{ dia().total.kcal | number: '1.0-0' }}</b>
        </div>
      </div>
      <p class="hy-resta">
        <ng-container *ngIf="restan() > 0; else listoKcal">Te quedan <b>{{ restan() | number: '1.0-0' }} kcal</b></ng-container>
        <ng-template #listoKcal><b>Llegaste a tus calorías</b></ng-template>
        · proteína {{ dia().total.prot | number: '1.0-0' }} / {{ meta().prot }} g
      </p>
    </section>

    <section class="hy-macros">
      <div class="hy-macro m-carb">
        <span class="hy-macro-top"><i aria-hidden="true">🌾</i> Carbos</span>
        <b>{{ dia().total.carb | number: '1.0-0' }}<small> / {{ meta().carb }} g</small></b>
        <span class="hy-barra"><span [style.width.%]="pct(dia().total.carb, meta().carb)"></span></span>
      </div>
      <div class="hy-macro m-grasa">
        <span class="hy-macro-top"><i aria-hidden="true">🥑</i> Grasa</span>
        <b>{{ dia().total.grasa | number: '1.0-0' }}<small> / {{ meta().grasa }} g</small></b>
        <span class="hy-barra"><span [style.width.%]="pct(dia().total.grasa, meta().grasa)"></span></span>
      </div>
      <div class="hy-macro m-prot">
        <span class="hy-macro-top"><i aria-hidden="true">💪</i> Proteína</span>
        <b>{{ dia().total.prot | number: '1.0-0' }}<small> / {{ meta().prot }} g</small></b>
        <span class="hy-barra"><span [style.width.%]="pct(dia().total.prot, meta().prot)"></span></span>
      </div>
    </section>
    <p class="hy-aviso" *ngIf="!nut.meta()">Meta provisional: anota tu peso abajo y el motor calcula la tuya en unas horas.</p>

    <h2 class="hy-titulo">Comidas del día</h2>
    <section class="hy-comida" *ngFor="let c of dia().comidas">
      <span class="hy-comida-ico" [class]="'hy-comida-ico t-' + c.tiempo.id" aria-hidden="true">{{ c.tiempo.ico }}</span>
      <div class="hy-comida-txt">
        <b>{{ c.tiempo.nombre }}</b>
        <small><span class="hy-chip-kcal">🔥 {{ c.kcal | number: '1.0-0' }} / {{ meta().porTiempo[c.tiempo.id] | number: '1.0-0' }} kcal</span></small>
        <div class="hy-items" *ngIf="c.items.length">
          <button type="button" *ngFor="let it of c.items" [disabled]="!esHoy()" (click)="nut.quitarAnotado(it.clave)"
                  [attr.aria-label]="'Quitar ' + it.nombre">
            {{ it.menu ? '🍽️' : emoji(it.clave) }} {{ it.nombre }}<ng-container *ngIf="it.n > 1"> ×{{ it.n }}</ng-container>
            <span *ngIf="esHoy()" aria-hidden="true">×</span>
          </button>
        </div>
      </div>
      <button type="button" class="hy-mas" *ngIf="esHoy()" (click)="agregar.emit(c.tiempo.id)"
              [attr.aria-label]="'Agregar a ' + c.tiempo.nombre">+</button>
    </section>
    <section class="hy-comida" *ngIf="dia().sinComida.length">
      <span class="hy-comida-ico t-otros" aria-hidden="true">📝</span>
      <div class="hy-comida-txt">
        <b>Sin comida asignada</b>
        <small>anotado antes de las comidas del día</small>
        <div class="hy-items">
          <button type="button" *ngFor="let it of dia().sinComida" [disabled]="!esHoy()" (click)="nut.quitarAnotado(it.clave)">
            {{ it.nombre }}<ng-container *ngIf="it.n > 1"> ×{{ it.n }}</ng-container>
          </button>
        </div>
      </div>
    </section>

    <ng-container *ngIf="esHoy()">
      <h2 class="hy-titulo">Hábitos</h2>
      <div class="hy-habitos">
        <button type="button" class="hy-habito" [class.on]="nut.creatinaHoy()" (click)="nut.alternarCreatina()">
          <span class="hy-habito-ico" aria-hidden="true">💊</span>
          <b>Creatina</b>
          <small>{{ nut.creatinaHoy() ? '✓ Tomada hoy' : '3-5 g · toca para marcar' }}</small>
          <small *ngIf="nut.rachaCreatina() > 1">{{ nut.rachaCreatina() }} días seguidos</small>
        </button>
        <div class="hy-habito hy-peso">
          <span class="hy-habito-ico" aria-hidden="true">⚖️</span>
          <b>Peso de hoy</b>
          <small *ngIf="nut.pesoHoy() as p; else sinPeso">✓ {{ p.peso | number: '1.1-1' }} kg</small>
          <ng-template #sinPeso><small>en ayunas</small></ng-template>
          <div class="hy-peso-campos">
            <input #kg type="number" inputmode="decimal" step="0.1" min="30" max="250" placeholder="kg" aria-label="Peso en kg"
                   [value]="nut.pesoHoy()?.peso ?? ''" (keyup.enter)="anotarPeso(kg.value, cin.value)">
            <input #cin type="number" inputmode="decimal" step="0.5" min="40" max="200" placeholder="cintura" aria-label="Cintura en cm (opcional)"
                   [value]="nut.pesoHoy()?.cintura ?? ''" (keyup.enter)="anotarPeso(kg.value, cin.value)">
            <button type="button" (click)="anotarPeso(kg.value, cin.value)">{{ nut.pesoHoy() ? 'Corregir' : 'Anotar' }}</button>
          </div>
          <small class="hy-peso-msg" *ngIf="pesoMsg()">{{ pesoMsg() }}</small>
        </div>
      </div>
      <p class="hy-nota">
        <ng-container *ngIf="nut.tendencia() as t; else faltanTxt">Tendencia de tu peso: {{ conSigno(t.pct) }} %/semana.</ng-container>
        <ng-template #faltanTxt>Con {{ faltanPesajes() }} pesaje{{ faltanPesajes() !== 1 ? 's' : '' }} más se ve tu tendencia.</ng-template>
        <ng-container *ngIf="nut.sinConexion() || nut.pesoPendiente()"> Sin conexión: se guarda en el teléfono y se sube solo.</ng-container>
      </p>
    </ng-container>
  `
})
export class HoyComponent implements OnInit {
  readonly nut = inject(NutricionService);
  @Output() readonly agregar = new EventEmitter<string>();
  readonly rFuera = R_FUERA;
  readonly rDentro = R_DENTRO;
  readonly hoy = fechaLocal(new Date());
  readonly fechaSel = signal(this.hoy);
  readonly esHoy = computed(() => this.fechaSel() === this.hoy);
  readonly meta = this.nut.metaHoy;
  readonly pesoMsg = signal('');
  readonly faltanPesajes = computed(() => Math.max(0, PESAJES_TENDENCIA - this.nut.pesajes21()));

  /** El dia elegido: hoy (lo del telefono) o uno pasado de la semana (lo del servidor). */
  readonly dia = computed(() => {
    if (this.esHoy()) return this.nut.desglose();
    const f = this.fechaSel();
    const md = this.nut.menu()?.dias.find((d) => d.fecha === f);
    return desglosar(this.nut.porcionesDe(f), (t) => {
      const c = md?.comidas.find((x) => x.tiempo === t);
      return md && c ? this.nut.comidaDe(md, c).nombre : '';
    });
  });
  readonly restan = computed(() => this.meta().kcal - this.dia().total.kcal);

  /** Lunes a domingo de esta semana, con un punto en los dias que tienen algo anotado. */
  readonly semana = computed(() => {
    const conDatos = new Set(this.nut.proteinaDias().filter((d) => d.g > 0).map((d) => d.fecha));
    if (Object.keys(this.nut.porciones()).length) conDatos.add(this.hoy);
    const lunes = new Date();
    lunes.setHours(12, 0, 0, 0);
    lunes.setDate(lunes.getDate() - ((lunes.getDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(lunes);
      d.setDate(d.getDate() + i);
      const fecha = fechaLocal(d);
      return {
        fecha, num: d.getDate(), letra: 'LMMJVSD'[i], esHoy: fecha === this.hoy, futuro: fecha > this.hoy,
        conDatos: conDatos.has(fecha), largo: d.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric' })
      };
    });
  });
  readonly fechaTexto = computed(() =>
    new Date(this.fechaSel() + 'T12:00:00').toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' }));

  ngOnInit(): void {
    void this.nut.cargar();
    this.nut.cargarMenu();
  }

  /** Largo del arco de un anillo (se topa en la vuelta completa). */
  arco(valor: number, meta: number, r: number): string {
    const c = 2 * Math.PI * r;
    const f = meta > 0 ? Math.min(1, valor / meta) : 0;
    return `${c * f} ${c}`;
  }

  pct(valor: number, meta: number): number {
    return meta > 0 ? Math.min(100, Math.round((valor / meta) * 100)) : 0;
  }

  emoji(clave: string): string {
    return emojiDe(clave.replace(/^(de|co|cl|ce)_/, ''));
  }

  async anotarPeso(kg: string, cintura: string): Promise<void> {
    const n = (v: string) => Number(String(v).replace(',', '.'));
    const error = await this.nut.anotarPeso(n(kg), cintura.trim() ? n(cintura) : null);
    this.pesoMsg.set(error || '✓ Anotado');
    if (!error) setTimeout(() => this.pesoMsg() === '✓ Anotado' && this.pesoMsg.set(''), 2500);
  }

  conSigno(v: number): string {
    const r = Math.round(v * 100) / 100 + 0;
    return (r > 0 ? '+' : r < 0 ? '−' : '±') + Math.abs(r).toFixed(2);
  }
}

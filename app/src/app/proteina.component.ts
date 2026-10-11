import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NutricionService, PESAJES_TENDENCIA, PORCIONES, esDelMenu } from './nutricion';
import { fechaLocal } from './entreno-data';
import type { MenuComida, MenuDia } from './rutina-api.service';
import { cucharadita } from './menu-semana';

/** Panel "Comida": proteína del día por porciones y el menú barato de la semana. */
@Component({
  selector: 'app-proteina',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="panel prot">
      <div class="comida-tabs">
        <button type="button" [class.on]="vista() === 'prot'" (click)="vista.set('prot')">🍗 Proteína</button>
        <button type="button" [class.on]="vista() === 'menu'" (click)="verMenu()">🍽️ Menú</button>
      </div>

      <ng-container *ngIf="vista() === 'prot'">
      <div class="prot-head">
        <strong>🍗 Proteína de hoy</strong>
        <span class="prot-total"><b>{{ nut.total() | number: '1.0-0' }}</b> / {{ meta().proteina_min }} g</span>
      </div>
      <div class="prot-barra" [class.ok]="nut.pct() >= 100"><div [style.width.%]="nut.pct()"></div></div>
      <p class="prot-hint">
        <ng-container *ngIf="faltan() > 0; else listo">Te faltan <b>{{ faltan() | number: '1.0-0' }} g</b>.</ng-container>
        <ng-template #listo><b>Meta cumplida.</b></ng-template>
        Meta {{ meta().proteina_min }}–{{ meta().proteina_max }} g/día<ng-container *ngIf="meta().peso"> para {{ meta().peso }} kg</ng-container>.
        <ng-container *ngIf="nut.promedio7() !== null"> Promedio de tus últimos días: {{ nut.promedio7() | number: '1.0-0' }} g.</ng-container>
      </p>
      <p class="prot-hint aviso" *ngIf="!nut.meta()">Meta provisional: anota tu peso aquí abajo y el motor calcula la tuya en unas horas.</p>

      <button type="button" class="creatina-fila" [class.on]="nut.creatinaHoy()" (click)="nut.alternarCreatina()">
        <span>💊 Creatina de hoy (3-5 g)</span>
        <b>{{ nut.creatinaHoy() ? '✓ Tomada' : 'Marcar' }}</b>
        <small *ngIf="nut.rachaCreatina() > 1">{{ nut.rachaCreatina() }} días seguidos</small>
      </button>

      <div class="peso-dia">
        <div class="peso-dia-top">
          <strong>⚖️ Peso de hoy</strong>
          <span *ngIf="nut.pesoHoy() as p">✓ {{ p.peso | number: '1.1-1' }} kg<ng-container *ngIf="p.cintura"> · {{ p.cintura | number: '1.0-1' }} cm</ng-container></span>
        </div>
        <div class="peso-dia-campos">
          <input #kg type="number" inputmode="decimal" step="0.1" min="30" max="250" placeholder="kg"
                 aria-label="Peso en kg" [value]="nut.pesoHoy()?.peso ?? ''" (keyup.enter)="anotarPeso(kg.value, cin.value)">
          <input #cin type="number" inputmode="decimal" step="0.5" min="40" max="200" placeholder="cintura (opc.)"
                 aria-label="Cintura en cm (opcional)" [value]="nut.pesoHoy()?.cintura ?? ''" (keyup.enter)="anotarPeso(kg.value, cin.value)">
          <button type="button" (click)="anotarPeso(kg.value, cin.value)">{{ nut.pesoHoy() ? 'Corregir' : 'Anotar' }}</button>
        </div>
        <p class="peso-dia-msg" *ngIf="pesoMsg()">{{ pesoMsg() }}</p>
        <p class="peso-dia-tend" *ngIf="nut.tendencia() as t; else sinTendencia">
          Tendencia: <b>{{ conSigno(t.pct, 2) }} %/sem</b> ({{ conSigno(t.kg, 2) }} kg/sem, últimos 21 días).
          El motor ajusta tus calorías con esto.
        </p>
        <ng-template #sinTendencia>
          <p class="peso-dia-tend">
            Pésate en ayunas, idealmente a diario.
            <ng-container *ngIf="faltanPesajes() > 0; else casi">Con {{ faltanPesajes() }} pesaje{{ faltanPesajes() !== 1 ? 's' : '' }}
              más se ve tu tendencia y el motor ajusta tus calorías.</ng-container>
            <ng-template #casi>La tendencia necesita pesajes de al menos 10 días.</ng-template>
          </p>
        </ng-template>
        <p class="peso-dia-tend" *ngIf="nut.pesoPendiente()">Sin conexión: el peso queda en el teléfono y se sube solo.</p>
      </div>

      <div class="prot-hoy" *ngIf="anotadas().length">
        <button type="button" *ngFor="let a of anotadas()" (click)="quitar(a)" [attr.aria-label]="'Quitar ' + a.nombre">
          {{ a.nombre }} {{ a.menu ? a.n + ' g' : '×' + a.n }} <span>−</span>
        </button>
      </div>

      <div class="prot-grid">
        <button type="button" class="prot-item" *ngFor="let p of enCasa" (click)="nut.sumar(p.id, 1)"
                [class.on]="nut.cantidad(p.id) > 0">
          <span class="prot-nom">{{ p.nombre }}<i *ngIf="p.barato" title="Barato por gramo de proteína">$</i></span>
          <span class="prot-por">{{ p.porcion }}</span>
          <span class="prot-g">+{{ p.g }} g</span>
        </button>
      </div>
      <details class="prot-fuera">
        <summary>🌮 Comí fuera</summary>
        <div class="prot-grid">
          <button type="button" class="prot-item" *ngFor="let p of fuera" (click)="nut.sumar(p.id, 1)"
                  [class.on]="nut.cantidad(p.id) > 0">
            <span class="prot-nom">{{ p.nombre }}</span>
            <span class="prot-por">{{ p.porcion }} · ~{{ p.kcal }} kcal</span>
            <span class="prot-g">+{{ p.g }} g</span>
          </button>
        </div>
      </details>
      <p class="prot-nota">
        Valores aproximados por porción. <b>$</b> = de lo más barato por gramo de proteína: frijol + tortilla
        se complementan, y huevo, atún y soya rinden mucho. Cuenta el total del día, no la hora.
        <ng-container *ngIf="nut.sinConexion()"> Sin conexión: se guarda en el teléfono y se sube después.</ng-container>
      </p>
      </ng-container>

      <ng-container *ngIf="vista() === 'menu'">
        <p class="prot-hint" *ngIf="!nut.menu() && nut.cargandoMenu()">Cargando el menú…</p>
        <p class="prot-hint" *ngIf="!nut.menu() && !nut.cargandoMenu()">
          Todavía no hay menú. Se genera con tu rutina el domingo, o en el dashboard, pestaña Menú.
        </p>
        <ng-container *ngIf="nut.menu() as m">
          <p class="menu-res">
            <b>\${{ m.costo_semana | number: '1.0-0' }}</b> a la semana · ~\${{ m.costo_dia | number: '1.0-0' }} al día<br>
            {{ m.kcal_prom | number: '1.0-0' }} kcal, {{ m.prot_prom }} g de proteína<ng-container
              *ngIf="m.carb_prom"> y {{ m.carb_prom }} g de carbohidratos</ng-container> al día en promedio
          </p>
          <div class="menu-extra">
            <ng-container *ngIf="m.dieta as dt">
              <p><b>🥗 {{ dt.nombre }}</b> · {{ dt.enfasis_nombre }}<ng-container
                *ngIf="dt.estrategia_nombre"> · 💪 {{ dt.estrategia_nombre }}</ng-container></p>
              <p *ngFor="let r of dt.cumple" [class.mal]="r.ok === false">
                {{ r.ok === null ? '–' : (r.ok ? '✓' : '✗') }} {{ r.regla }}: {{ r.valor }}
                <small *ngIf="r.nota">{{ r.nota }}</small>
              </p>
              <p *ngIf="dt.id !== 'mexicana' && m.nutrientes?.sodio">
                <small>Sodio ~{{ m.nutrientes?.sodio | number: '1.0-0' }} mg/día sin la sal de mesa: cocina con poca
                  sal y sazona con limón, ajo, chile y hierbas.</small>
              </p>
            </ng-container>
            <p *ngIf="m.hogar && m.hogar.factor !== 1">
              🏠 Lista y cocina para {{ m.hogar.adultos }} adulto{{ m.hogar.adultos !== 1 ? 's' : '' }}<ng-container
                *ngIf="m.hogar.ninos"> y {{ m.hogar.ninos }} niño{{ m.hogar.ninos !== 1 ? 's' : '' }}</ng-container>
            </p>
            <p *ngIf="m.presupuesto as pr" [class.mal]="!pr.cabe">
              {{ pr.cabe ? '✓ Cabe en tu presupuesto' : '✗ No cabe en tu presupuesto' }}
              (\${{ pr.costo | number: '1.0-0' }} de \${{ pr.tope | number: '1.0-0' }})
            </p>
            <p *ngIf="m.nutrientes as n">
              Fibra {{ n.fibra | number: '1.0-0' }} g · Hierro {{ n.hierro | number: '1.0-0' }} mg ·
              Calcio {{ n.calcio | number: '1.0-0' }} mg al día
              <small *ngFor="let c of n.consejos">{{ c }}</small>
            </p>
          </div>
          <div class="menu-sel">
            <button type="button" *ngFor="let d of m.dias" [class.on]="diaSel() === d.dia" (click)="diaSel.set(d.dia)">
              {{ d.nombre.slice(0, 3) }}
            </button>
          </div>
          <ng-container *ngIf="dia() as d">
            <p class="menu-dia-tot">
              {{ d.nombre }}<ng-container *ngIf="d.tipo"> · día de {{ d.tipo }}</ng-container>
              <ng-container *ngIf="nut.totalesDe(d) as t">
                · {{ t.kcal | number: '1.0-0' }} kcal · {{ t.prot | number: '1.0-0' }} g · \${{ t.costo | number: '1.0-0' }}
              </ng-container>
            </p>
            <p class="menu-sal" *ngIf="d.sal_g != null">
              🧂 Sal para cocinar hoy: hasta {{ d.sal_g | number: '1.1-1' }} g ({{ cucharadita(d.sal_g) }}), en la olla y en la mesa
            </p>
            <ng-container *ngFor="let c0 of d.comidas">
            <div class="menu-comida" *ngIf="nut.comidaDe(d, c0) as c">
              <span class="menu-t">{{ etiqueta[c.tiempo] || c.tiempo }}</span>
              <div class="menu-nom"><strong>{{ c.nombre }}</strong><small>{{ c.kcal }} kcal · {{ c.prot | number: '1.0-0' }} g</small></div>
              <p class="menu-ing">{{ ingredientes(c) }}</p>
              <p class="menu-como" *ngIf="c.como">{{ c.como }}</p>
              <div class="menu-acciones">
                <button type="button" class="menu-comi" *ngIf="esHoy(d)" [class.on]="nut.comioMenu(c.tiempo)"
                        (click)="nut.alternarMenu(c.tiempo, c.prot)">
                  {{ nut.comioMenu(c.tiempo) ? '✓ Comido · +' + (c.prot | number: '1.0-0') + ' g' : 'Lo comí (+' + (c.prot | number: '1.0-0') + ' g)' }}
                </button>
                <button type="button" class="menu-nogusta" [class.on]="nut.noGusta(c.receta)"
                        (click)="nut.marcarNoMeGusta(d, c0)"
                        [attr.aria-label]="nut.noGusta(c.receta) ? 'Quitar no me gusta' : 'No me gusta: no volver a ponerla'">
                  👎{{ nut.noGusta(c.receta) ? ' No me gusta' : '' }}
                </button>
                <button type="button" class="menu-cambiar" *ngIf="c0.alternativas?.length" (click)="nut.cambiarComida(d, c0)">
                  ⟳ Cambiar ({{ nut.opcionDe(d, c0) + 1 }}/{{ (c0.alternativas?.length ?? 0) + 1 }})
                </button>
              </div>
            </div>
            </ng-container>
          </ng-container>
          <p class="prot-hint aviso" *ngFor="let a of m.avisos">{{ a }}</p>
          <details class="menu-lista" *ngIf="nut.cocina().length">
            <summary>🍳 Cocina por adelantado</summary>
            <p class="prot-nota">Lo cocido dura 3-4 días en el refri: por eso se cocina dos veces a la semana.</p>
            <div class="menu-cocina" *ngFor="let t of nut.cocina()">
              <b>{{ t.cuando }}</b> <small>{{ t.para }}</small>
              <ul><li *ngFor="let x of t.tareas">{{ x.texto }}</li></ul>
            </div>
          </details>
          <details class="menu-lista">
            <summary>🛒 Lista del súper (≈ \${{ nut.costoPendiente() | number: '1.0-0' }} por comprar)</summary>
            <p class="prot-nota">Toca lo que ya tienes en casa: se quita de la cuenta.</p>
            <button type="button" class="menu-li" *ngFor="let f of nut.lista()" [class.tengo]="nut.tengo().includes(f.id)"
                    (click)="nut.alternarTengo(f.id)">
              <span>{{ nut.tengo().includes(f.id) ? '✓ ' : '' }}{{ f.nombre }}</span><span>{{ f.compra }}</span>
              <span>\${{ f.costo | number: '1.0-0' }}</span>
            </button>
            <div class="lista-acciones">
              <button type="button" class="menu-cambiar" (click)="compartir()">📤 Compartir lista</button>
              <small *ngIf="aviso()">{{ aviso() }}</small>
            </div>
          </details>
          <p class="prot-nota">{{ m.nota }} Para cambiar recetas, quitar alimentos o poner tus precios: dashboard, pestaña Menú.</p>
        </ng-container>
      </ng-container>
    </section>
  `
})
export class ProteinaComponent implements OnInit {
  readonly nut = inject(NutricionService);
  readonly porciones = PORCIONES;
  readonly enCasa = PORCIONES.filter((p) => !p.fuera);
  readonly fuera = PORCIONES.filter((p) => p.fuera);
  readonly aviso = signal('');
  readonly meta = this.nut.metaEfectiva;
  readonly faltan = computed(() => Math.max(0, this.meta().proteina_min - this.nut.total()));
  readonly anotadas = computed(() => {
    const p = this.nut.porciones();
    const delMenu = Object.keys(p).filter(esDelMenu).map((id) => ({
      id, nombre: 'Menú: ' + (this.etiqueta[id.slice(5)] ?? id.slice(5)), n: p[id], menu: true, tiempo: id.slice(5)
    }));
    const sueltas = PORCIONES.filter((x) => (p[x.id] ?? 0) > 0)
      .map((x) => ({ id: x.id, nombre: x.nombre, n: p[x.id], menu: false, tiempo: '' }));
    return [...delMenu, ...sueltas];
  });

  readonly pesoMsg = signal('');
  readonly faltanPesajes = computed(() => Math.max(0, PESAJES_TENDENCIA - this.nut.pesajes21()));

  readonly vista = signal<'prot' | 'menu'>('prot');
  readonly diaSel = signal(((new Date().getDay() + 6) % 7) + 1);     // hoy (1 = lunes)
  readonly dia = computed(() => this.nut.menu()?.dias.find((d) => d.dia === this.diaSel()) ?? null);
  readonly cucharadita = cucharadita;
  readonly etiqueta: Record<string, string> = { desayuno: 'Desayuno', comida: 'Comida', colacion: 'Colación', cena: 'Cena' };

  ngOnInit(): void {
    void this.nut.cargar();
  }

  verMenu(): void {
    this.vista.set('menu');
    this.nut.cargarMenu();
  }

  esHoy(d: MenuDia): boolean {
    return d.fecha === fechaLocal(new Date());
  }

  quitar(a: { id: string; menu: boolean; tiempo: string; n: number }): void {
    if (a.menu) this.nut.alternarMenu(a.tiempo, a.n);
    else this.nut.sumar(a.id, -1);
  }

  async anotarPeso(kg: string, cintura: string): Promise<void> {
    const n = (v: string) => Number(String(v).replace(',', '.'));
    const error = await this.nut.anotarPeso(n(kg), cintura.trim() ? n(cintura) : null);
    this.pesoMsg.set(error || '✓ Anotado.');
    if (!error) setTimeout(() => this.pesoMsg() === '✓ Anotado.' && this.pesoMsg.set(''), 2500);
  }

  /** +0.25 / −0.10 / ±0.00 (nunca "-0.00"). */
  conSigno(v: number, dec: number): string {
    const r = Math.round(v * 10 ** dec) / 10 ** dec + 0;
    return (r > 0 ? '+' : r < 0 ? '−' : '±') + Math.abs(r).toFixed(dec);
  }

  async compartir(): Promise<void> {
    this.aviso.set(await this.nut.compartirLista());
  }

  ingredientes(c: MenuComida): string {
    return c.ingredientes.map((i) => i.texto).join(', ');
  }
}

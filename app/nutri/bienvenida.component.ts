import { Component, EventEmitter, Output } from '@angular/core';

/** Pantalla de bienvenida (solo la primera vez). */
@Component({
  selector: 'app-bienvenida',
  standalone: true,
  template: `
    <section class="bv">
      <div class="bv-top">
        <span class="bv-logo"><i aria-hidden="true">🥑</i> nutri</span>
        <span class="bv-puntos" aria-hidden="true"><i class="on"></i><i></i><i></i></span>
      </div>
      <h1>Tu guía diaria para comer <span class="bv-flama" aria-hidden="true">🔥</span> mejor.</h1>
      <p class="bv-sub">Proteína, calorías y un menú mexicano barato hecho para tus entrenos.</p>
      <div class="bv-arte" aria-hidden="true">
        <span class="bv-tag t1">72 kcal</span>
        <span class="bv-tag t2">225 kcal</span>
        <span class="bv-tag t3">165 kcal</span>
        <span class="bv-comida c1">🥚</span>
        <span class="bv-comida c2">🫘</span>
        <span class="bv-comida c3">🍗</span>
        <span class="bv-comida c4">🥑</span>
        <span class="bv-comida c5">🌽</span>
        <span class="bv-comida c6">🍅</span>
        <span class="bv-comida c7">🥬</span>
        <span class="bv-comida c8">🌶️</span>
      </div>
      <button type="button" class="bv-empezar" (click)="listo.emit()">
        <span class="bv-flecha" aria-hidden="true">»</span>
        Empezar
        <span class="bv-ok" aria-hidden="true">✓</span>
      </button>
    </section>
  `
})
export class BienvenidaComponent {
  @Output() readonly listo = new EventEmitter<void>();
}

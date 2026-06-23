import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <nav class="glass-panel navbar">
      <div class="nav-content">
        <h2 class="logo">Gym<span class="neon-text">Tracker</span></h2>
      </div>
    </nav>
    <main class="container">
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [`
    .navbar {
      position: sticky;
      top: 0;
      z-index: 100;
      border-radius: 0 0 16px 16px;
      margin-bottom: 24px;
      border-top: none;
      border-left: none;
      border-right: none;
    }
    .nav-content {
      padding: 16px 20px;
      max-width: 600px;
      margin: 0 auto;
    }
    .logo {
      margin: 0;
      font-size: 1.5rem;
      color: var(--text-main);
    }
    .neon-text {
      color: var(--accent-cyan);
      text-shadow: 0 0 10px var(--accent-cyan-glow);
    }
  `]
})
export class App {
  title = 'angular-app';
}

# Darle GymTracker a otra persona

Esta guía crea una **copia completa y separada** de GymTracker para otra persona: su propia app, su propia base de datos, su propio motor y su propio dashboard. **Nada de lo tuyo se toca.** Sus entrenos nunca se mezclan con los tuyos y si algo de su copia falla, la tuya sigue igual.

⏱️ **Tiempo:** unos 40 minutos la primera vez.

---

## Qué va a tener esa persona

| | Tú | La otra persona (ejemplo: `ana`) |
|---|---|---|
| App en el celular | `aguilarmunoz.infinityfree.me` | `ana-gym.infinityfreeapp.com` (la que elijas) |
| Base de datos | la tuya | una nueva, solo suya |
| Dashboard | `20-150-209-104.sslip.io` | `ana.20-150-209-104.sslip.io` |
| Rutina semanal | domingo 22:00 | domingo 22:15 |
| Recordatorio push | sí | sí |
| Configuración (enfoque, split, deporte…) | la tuya | la suya, en su dashboard |

**Comparten** el código (cuando mejoras la app, mejora para los dos), la VM de Azure y las claves de los avisos push. **No comparten** datos.

---

## Antes de empezar

Necesitas:

- ✅ Este PC, el mismo desde el que ya subes cambios a GitHub. Aquí está la llave de la VM (`.ssh\id_gymvm`).
- ✅ Tu sesión de GitHub abierta en el navegador.
- ✅ Un nombre corto para la persona: minúsculas, sin acentos ni espacios. Por ejemplo `ana`, `luis`, `carlos2`.

> **Cuántas personas caben:** la VM es pequeña (≈830 MB de memoria). Cada persona extra usa unos 150 MB. Con **1 o 2 personas extra** va bien. Más que eso requiere una VM más grande.

---

## Paso 1 — Su sitio en InfinityFree (en el navegador)

Esto se hace a mano porque InfinityFree no permite automatizarlo.

**1.1 Crear su cuenta de hosting**

1. Entra a https://dash.infinityfree.com con **tu** cuenta. Una cuenta gratis permite hasta 3 sitios.
2. Botón **Create Account**.
3. Elige un **subdominio**, por ejemplo `ana-gym`, y la terminación que quieras (`.infinityfreeapp.com`, `.infinityfree.me`…).
4. Termina el asistente. **Anota la dirección completa**, por ejemplo `ana-gym.infinityfreeapp.com`.
5. Espera a que el estado diga **Active**. A veces tarda unos minutos.

**1.2 Crear su base de datos**

1. En su cuenta nueva: **Control Panel** → **MySQL Databases**.
2. En *Create Database* escribe `gym` y presiona **Create Database**.
3. Quedan a la vista 4 datos que vas a necesitar en el Paso 2. **Déjalos abiertos en una pestaña**:
   - **MySQL Host Name** (ej. `sql123.infinityfree.com`)
   - **MySQL DB Name** (ej. `if0_12345678_gym`)
   - **MySQL User Name** (ej. `if0_12345678`)
   - **MySQL Password**: es la contraseña de esa cuenta de hosting. Se ve en *Account Details* → *Show*.

**1.3 Crear las tablas**

1. En la lista de bases de datos, junto a la nueva, presiona **Admin**. Se abre phpMyAdmin.
2. Pestaña **Importar** (*Import*).
3. **Seleccionar archivo** → elige `infinityfree\schema.sql` de la carpeta del proyecto en este PC.
4. Presiona **Continuar** (*Go*), abajo. Debe decir que se ejecutó correctamente.

**1.4 Ten a la mano sus datos de FTP**

En su cuenta: **FTP Details**. El asistente te pedirá el **FTP Username** (empieza con `if0_`). La **FTP Password** solo la vas a pegar en GitHub.

---

## Paso 2 — El asistente (doble clic)

En la carpeta del proyecto, doble clic en **`Nuevo usuario.bat`**.

Se abre una ventana que te guía en 6 partes. Cuando algo depende de ti, **se detiene y te dice exactamente qué hacer**, y sigue cuando presionas Enter.

| Parte | Qué hace el asistente | Qué haces tú |
|---|---|---|
| 1. Datos | Te pide el nombre, la dirección de su sitio y los datos de MySQL y FTP del Paso 1. Genera su `config.php` y su **token**, una clave secreta nueva. | Escribir lo que pide. La contraseña de MySQL no se ve al escribirla; es normal. |
| 2. Lista | La agrega a `instancias\instancias.json`. | Nada. |
| 3. Secretos | Abre GitHub en la página de secretos y te muestra los 3 que hay que crear. El token ya queda copiado. | Crear los 3 secretos (ver abajo). |
| 4. Publicar | Sube el cambio a GitHub, espera a que pasen las pruebas y te avisa cuando su app está publicada (≈5 min). | Esperar. |
| 5. config.php | Abre la carpeta con su `config.php` y el panel de InfinityFree. | Subir ese archivo (ver abajo). |
| 6. VM | Se conecta a la VM e instala su motor, su dashboard y su primera rutina. | Esperar (3–5 min la primera vez). |

### Los 3 secretos de GitHub (parte 3)

En la página que se abre, presiona **New repository secret** una vez por cada uno. En **Name** va exactamente el nombre que te muestra el asistente; para `ana` serían:

| Name | Secret |
|---|---|
| `TOKEN_ANA` | el token: **Ctrl+V**, ya está copiado |
| `FTP_USUARIO_ANA` | su FTP Username (`if0_…`) |
| `FTP_PASSWORD_ANA` | su FTP Password, del panel de InfinityFree |

> El nombre de la persona va **en MAYÚSCULAS** en los secretos. Un error de dedo aquí es el problema más común.

### Subir su config.php (parte 5)

1. En **su** cuenta de InfinityFree: **Online File Manager**.
2. Entra a la carpeta **htdocs** y luego a **api**. La carpeta `api` la acaba de crear la parte 4.
3. **Upload** → elige el `config.php` de la carpeta que abrió el asistente (`instancias\ana\`).

Ese archivo tiene la contraseña de su base de datos. Por eso **nunca** se sube a GitHub: vive solo en este PC (git lo ignora) y en su InfinityFree.

---

## Paso 3 — Entregárselo

El asistente termina mostrando sus dos enlaces. Mándaselos:

- **Su app:** en su iPhone, abrirla en **Safari** → botón **Compartir** → **Agregar a inicio**. Así queda como app y le llegan los avisos.
- **Su dashboard:** pestaña **⚙ Configuración** → elegir enfoque, split, duración, días de deporte y equipo → **Generar y guardar plan**.

Su primera semana arranca como **S1 (base)**, con pesos de partida estimados. El motor los ajusta en cuanto registra sus primeros entrenos.

---

## Cómo se actualiza

No hay que hacer nada por cada persona:

- **App:** cada vez que subes un cambio a GitHub, el despliegue automático publica tu app **y la de cada persona de la lista**. Lo ves en GitHub → *Actions*: hay un recuadro `desplegar (ana)` por persona.
- **VM** (motor y dashboard): el mismo comando de siempre actualiza la tuya y las de los demás:

```bash
ssh azureuser@20.150.209.104
cd ~/gym && git pull && bash servidor/instalar_vm.sh
```

---

## Quitar a una persona

1. En la VM:

   ```bash
   bash ~/gym/servidor/quitar_instancia.sh ana
   ```

   Apaga su motor y su dashboard. **No borra sus datos**: su carpeta `~/gym-ana` se queda por si acaso.
2. Borra su renglón de `instancias\instancias.json` y sube el cambio a GitHub. Así su app deja de recibir actualizaciones.
3. Opcional: borra sus 3 secretos en GitHub y su cuenta de hosting en InfinityFree.

---

## Si algo falla

| Síntoma | Qué revisar |
|---|---|
| En GitHub → Actions, `desplegar (ana)` sale en rojo con *"Falta el secreto…"* | Un secreto con el nombre mal escrito (`TOKEN_ANA`, `FTP_USUARIO_ANA`, `FTP_PASSWORD_ANA`). Corrígelo y en Actions → *Probar y desplegar* → **Run workflow**. |
| Sale en rojo al subir por FTP | La FTP Password está mal, o su cuenta de hosting todavía no está *Active*. |
| La parte 6 dice *"no pude conectar"* | 1) ¿Subiste `config.php` a `htdocs/api`? 2) ¿Importaste `schema.sql`? 3) Vuelve a ejecutar `Nuevo usuario.bat`: con el mismo nombre retoma sin duplicar nada. |
| Su dashboard no abre | Espera 1–2 minutos: la primera vez se genera su certificado HTTPS. |
| Su app abre pero sin rutina | El motor genera la rutina el domingo 22:15. Para tenerla ya: su dashboard → **Plan semana** → **Recalcular y subir plan**. |
| Algo raro y quieres empezar de cero | `quitar_instancia.sh`, borra la carpeta `instancias\ana` de este PC y repite desde el Paso 2. |

---

## Qué hay detrás (para curiosos)

| Pieza | Dónde |
|---|---|
| Lista de personas | `instancias/instancias.json` (nombre, clave y la dirección de su API; nada secreto) |
| Sus secretos | GitHub → Settings → Secrets: `TOKEN_*`, `FTP_USUARIO_*`, `FTP_PASSWORD_*` |
| Su `config.php` y su token | `instancias/<nombre>/` en este PC (ignorado por git) y en su InfinityFree |
| Despliegue de su app | `.github/workflows/desplegar.yml`, trabajo `desplegar-instancias`: compila la app apuntando a **su** API y la sube a **su** InfinityFree |
| Su copia en la VM | `~/gym-<nombre>/` con su `.env` y su `config_usuario.json` |
| Sus servicios en la VM | `gymtracker-<nombre>-{motor,datos,recordatorio,dashboard}` |
| Su dirección HTTPS | `/etc/caddy/instancias/<nombre>.caddy` |
| Scripts | `Nuevo usuario.bat` → `servidor/nuevo_usuario.ps1` (PC) · `servidor/nueva_instancia.sh` y `servidor/quitar_instancia.sh` (VM) |

**Lo que NO tiene su copia:**

- **Respaldo en tu PC:** si la VM está apagada el domingo, su rutina se genera cuando la VM vuelva. También puede generarla desde su dashboard.
- **Script de generación manual en su lado:** `generar_rutina_manual.bat` es solo tuyo.

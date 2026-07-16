# Ajustes del sistema de rutinas y cargas a la evidencia científica (Julio 2026)

> Revisión del motor de planificación como lo haría un especialista en ciencias
> del deporte: cada regla de programación se contrastó con la literatura de
> hipertrofia y fuerza de 2016–2025. Este documento explica **qué se cambió,
> por qué, y dónde en el código**.

**Alcance revisado**: los 5 enfoques (Recomposición, Volumen/Bulk, Definición,
Powerbuilding, Fuerza Pura), los 3 splits (Upper/Lower, PPL, Full Body), las
reglas de progresión por bloque, el mesociclo de 5 semanas, los descansos, y
las guías de macros.

---

## Resumen de veredicto

La arquitectura del sistema ya estaba bien fundamentada (frecuencia 2×/semana
por patrón, doble progresión regulada por RPE, deload programado + reactivo,
prioridad muscular al inicio de la sesión, macros por objetivo). Los problemas
encontrados iban casi todos en la misma dirección: **exceso de agresividad**
(demasiado fallo, PR forzado por calendario, descansos cortos) que generaba
fatiga innecesaria y, en dos casos, bloqueaba la propia sobrecarga progresiva
del sistema.

---

## 1. El fallo prescrito bloqueaba la progresión (crítico)

**Problema.** El plan ordena fallo en la última serie (AMRAP en Bloque B,
Rest-Pause/Drop en Bloque C), pero la regla de progresión de esos bloques solo
subía el peso si el **RPE promedio de la sesión** era ≤ 8. La serie al fallo
(RPE 10) arrastraba el promedio por encima de 8 → **los bloques B y C nunca
progresaban en carga, por diseño**.

**Arreglo** (`planificar.py · ultimas_y_records`):
- Se calcula el **RPE de trabajo**: si la última serie fue prescrita al fallo
  (AMRAP / Rest-Pause / Drop), se excluye del promedio. Ese RPE 10 es
  intencional y no informa sobre la carga de las series de trabajo.

**Arreglo relacionado** (`planificar.py · _familia`):
- El historial ahora se agrupa por **familia de técnica** (top set / back-off /
  volumen) en lugar del texto exacto. Antes, cuando la técnica rotaba
  (Tradicional ↔ AMRAP ↔ Drop Set), el motor "perdía" el historial del
  ejercicio y reiniciaba la progresión.

## 2. La semana pico (S4) forzaba un PR por calendario (riesgo de lesión)

**Problema.** En S4 el motor imponía `peso = max(progresión, mejor_del_mes +
microcarga)` sin condición alguna — incluso pisando el caso en que la semana
anterior no se llegó ni al mínimo de reps (donde la regla ya había bajado el
peso 5%). Un intento de PR con fatiga acumulada y rendimiento en caída es la
receta clásica de lesión, especialmente con top sets de 1–3 reps (Fuerza Pura).

**Arreglo** (`planificar.py · peso_top_set`): el intento de superar el mejor
del mes en S4 solo se prescribe si la última sesión **completó el rango de
reps con RPE ≤ 8**. La progresión se gana con rendimiento, no se impone con
fecha. La nota de S4 en la app ahora lo dice explícitamente.

## 3. Exceso de trabajo al fallo crónico

**Evidencia.** Los meta-análisis recientes (Refalo 2023; Robinson 2024; Grgic
2022) muestran que entrenar a 1–3 repeticiones en reserva (RIR) produce una
hipertrofia comparable al fallo con bastante menos fatiga y mejor recuperación
entre sesiones — más relevante aún en déficit calórico (Recomposición y
Definición).

**Arreglo** (`generador.py · _dia_pesas`): el fallo ahora está **periodizado
dentro del mesociclo**:

| Semana | Bloque B | Bloque C (aislamientos) |
|---|---|---|
| S1 | Tradicional, RIR 1–2 | Tradicional, RIR 1–2 |
| S2 (rotación) | Tradicional, RIR 1–2 (estímulo nuevo) | Tradicional, RIR 1–2 |
| S3–S4 | Técnica de intensidad (AMRAP/Drop) en la última serie | Rest-Pause/Drop **solo en la última serie** |
| S5 deload | Tradicional, RIR 3–4 (cero fallo) | (el Bloque C no se hace) |

Además el deload S5 ahora **sustituye activamente** cualquier técnica de fallo
por trabajo tradicional a RIR 3–4 (`planificar.py · generar_filas`): antes la
app mostraba "AMRAP" también en la semana de recuperación.

## 4. Descansos de 90 s en compuestos del Bloque B

**Evidencia.** Con 90 s entre series de multiarticulares se pierden reps en
las series siguientes y con ello volumen efectivo; ≥ 2 min produce más
hipertrofia (Schoenfeld 2016 y metas posteriores).

**Arreglo** (`enfoques.py · DESC`): `volumen: 90 → 120` s. Se mantienen 180 s
(Top Set), 120 s (Back-off), 90 s (aislamientos), 60 s (superserie
antagonista). Se alineó también la app (`entreno-data.ts ·
descansoPorTecnica`) y la plantilla de referencia (`plan_template.py`).

## 5. El pecho quedaba en ~6 series/semana (Upper/Lower)

**Problema.** En el split por defecto, el pecho solo aparecía en el Bloque B
(3 series × 2 días de torso) y el Bloque C de torso no incluía ningún
aislamiento de pecho. La relación dosis-respuesta (Schoenfeld 2017; Pelland
2024) sitúa el rango productivo en ~10–20 series/músculo/semana.

**Arreglo** (`enfoques.py · SPLITS`): los dos días de torso agregan un
aislamiento de empuje horizontal al Bloque C (pec deck / aperturas / cruce de
poleas) → pecho pasa a ~10 series directas/semana.

## 6. El Full Body rompía la regla de frecuencia 2×

**Problema.** El código promete "cada patrón 2×/semana", pero en el split
Full Body el empuje vertical, el tirón vertical y el dominante de cadera
quedaban 1×/semana.

**Arreglo** (`enfoques.py · full_body`): cada día pasa a 2 patrones en A + 2
en B (12 huecos), de modo que **los 6 patrones fundamentales quedan
exactamente 2×/semana**. Verificado por prueba automática.

## 7. Doble progresión estricta

**Problema.** El Top Set subía peso incluso a mitad del rango de reps (p. ej.
6 de un rango 6–8) si el RPE era ≤ 8, lo que producía "dientes de sierra"
(subir peso → caer bajo el mínimo → −5% → repetir).

**Arreglo** (`planificar.py · peso_top_set`): dentro del rango se mantiene el
peso y se progresa en reps; la carga solo sube al **completar** el rango. Es
la doble progresión canónica.

## 8. Bugs de programación con efecto en el entrenamiento

- **Superserie rota en Definición** (`generador.py`): con `n_ejercicios_c = 2`
  el tríceps se recortaba por cupo y el bíceps quedaba etiquetado "Superserie
  con tríceps" sin pareja. La pareja bíceps+tríceps ahora cuenta como **un
  solo movimiento** (comparten los 60 s de descanso) y no se puede recortar a
  medias.
- **Superserie rota por duración** (`planificar.py · _recortar_duracion`): el
  recorte por tiempo (60/75 min) podía eliminar solo un miembro de la
  superserie. Ahora se recorta como unidad (ambos o ninguno).
- **Récord mensual con NaN** (`planificar.py`): `max() or peso` no funciona
  con NaN (NaN es "truthy"); se sustituyó por `pd.notna()`.

## 9. Ajustes menores de evidencia

- **Peso corporal** (`generador.py · _nota_pc`): dominadas y fondos ahora
  llevan ruta de progresión explícita (superar el rango en todas las series →
  agregar lastre +2.5 kg). Antes no tenían forma de sobrecargar.
- **"Estado del SNC" → "Fatiga percibida"** (`dashboard.py`): un promedio de
  RPE semanal es un buen indicador de fatiga percibida, pero llamarlo estado
  del sistema nervioso central sobrevende lo que mide (la literatura actual
  le baja el tono a la "fatiga del SNC" en hipertrofia). El texto de alerta
  ahora recomienda exactamente lo que hace la S5: misma intensidad, mitad de
  volumen, cero fallo.
- **Ritmo de bulk realista** (`enfoques.py · volumen`): "+0.3–0.5 kg/semana"
  → "+0.2–0.4 kg/semana (~0.25–0.5% del peso corporal)"; más rápido es
  mayormente grasa (Iraki/Helms 2019).
- **Creatina 3–5 g/día** añadida a las guías de macros de los 5 enfoques: es
  el suplemento con mayor evidencia para fuerza e hipertrofia, seguro y
  barato.
- **Proteína en Recomposición**: límite inferior 1.6 → 1.8 g/kg (en déficit
  conviene la mitad alta del rango).
- **Fuerza Pura**: nota explícita de no pasar de RPE 9 en top sets de 1–3
  reps.

## Lo que se revisó y NO se cambió (estaba bien)

- Frecuencia 2×/semana por patrón en Upper/Lower y PPL.
- Estructura de bloques A (Top Set + Back-off 80%) / B (volumen) / C
  (aislamiento) y los rangos de reps por enfoque (6–8 / 8–12 / 12–15;
  Powerbuilding 3–5; Fuerza 1–3).
- Deload S5: misma intensidad, −50% volumen, sin Bloque C — coincide con las
  recomendaciones actuales de descarga.
- Deload reactivo por estancamiento (3 semanas sin subir tonelaje + RPE ≥ 9 →
  −10%).
- Cardio LISS Zona 2 dosificado por objetivo (1–3 días) y core separado.
- Guías de macros por enfoque (rangos de proteína/carbos/grasas y tamaño del
  déficit/superávit son consistentes con la literatura).
- Antebrazos al final y en días no consecutivos; superserie antagonista
  bíceps/tríceps; calentamiento con rampa 50/70/90%.

---

# Segunda tanda — mejoras de seguimiento y autorregulación

> Mismo criterio de evidencia; el foco pasa de "corregir la programación" a
> "cerrar los lazos de retroalimentación" (rendimiento → carga, fatiga →
> deload, báscula → kcal).

## A. "Supera tu marca" en cada tarjeta (`planificar.py · marca_anterior`)

La doble progresión vive de comparar contra la sesión anterior. Ahora las
notas del plan incluyen **"Anterior: X kg × Y @RPE Z"** en Top Sets y bloques
de volumen, así la app muestra en el gimnasio exactamente qué hay que superar.
Las notas se recortan a 255 caracteres (límite del `VARCHAR` en MySQL).

## B. Deload reactivo global (`planificar.py · fatiga_global`)

El dashboard ya avisaba "RPE ≥ 9 sostenido 2+ semanas → adelanta el deload",
pero el motor no actuaba. Ahora `planificar.py` calcula esa misma señal y, si
se dispara, genera la semana como deload (S5) sin esperar al calendario. El
mesociclo continúa normal a la semana siguiente.

## C. Progresión por repeticiones para peso corporal y core

Dominadas, fondos, crunch, elevaciones de piernas…: sin carga externa la única
sobrecarga es hacer más reps. Si el rango se completó con RPE ≤ 8, el rango
objetivo sube (p. ej. 15–20 → 18–23), con tope en 30 reps (después: lastre).
Además `peso_volumen` ya no sugiere cargas absurdas (1.25 kg) en ejercicios de
peso corporal.

## D. Objetivo de RPE visible por serie (app Angular)

Cada serie muestra ahora un chip **"Objetivo: RPE 8–9 · deja 1-2 reps"** (o
"al fallo (RPE 10)" en la última serie de AMRAP/Rest-Pause/Drop). Registrar el
RPE honesto es el combustible de todo el motor; darle el objetivo antes mejora
la calidad del dato (`entreno-data.ts · rpeObjetivoDe`).

## E. Filtro de equipo disponible (`generador.py` + Configuración)

Nueva opción "Equipo que tu gym NO tiene" (barra / mancuernas / poleas /
máquinas): el generador sustituye por alternativas del mismo patrón, con
fallback seguro (nunca deja un patrón vacío). No es fisiología: es adherencia,
la variable que más resultados predice.

## F. Macros en gramos, no en g/kg (dashboard · Configuración)

El sistema ya conocía tu peso corporal, pero te dejaba la multiplicación a ti.
La pestaña Configuración muestra ahora **gramos diarios** de proteína, carbos
y grasas para tu peso y enfoque, más la distribución recomendada de proteína
(3–5 comidas de ~0.4–0.55 g/kg, una peri-entreno; Schoenfeld & Aragon 2018).

## G. Peso corporal con tendencia y semáforo calórico (dashboard, nueva pestaña)

El hueco nutricional más grande: el sistema prescribía déficit/superávit pero
nunca verificaba si funcionaba. La nueva pestaña **"Peso corporal"**:

- registra el peso diario en `peso_corporal.csv` (local, gitignoreado);
- grafica el pesaje crudo y la **media móvil de 7 días** (la que manda);
- calcula la tendencia semanal (%) y la compara con el objetivo del enfoque
  (Recomposición −0.5 a 0 %/sem · Definición −1.0 a −0.5 · Bulk +0.25 a +0.5 ·
  Powerbuilding/Fuerza ±0.25);
- semáforo: dentro del rango → no toques nada; fuera → ajustar ±100–200
  kcal/día y reevaluar en 2 semanas.

Registrar el peso también actualiza `peso_corporal` en la config, así los
macros en gramos y el generador quedan sincronizados.

## Verificación (segunda tanda)

38 comprobaciones automáticas en verde (las 31 previas + marca anterior, cap
de 255, deload reactivo positivo/negativo, subida de rango del core, sin pesos
absurdos en peso corporal, y plan sin barra al excluir equipo). Dashboard:
smoke test del layout completo con las pestañas nuevas. App Angular: build de
producción sin errores.

---

# Tercera tanda — robustez y protección de datos (tester/dev)

## H. Guardado blindado en la app (Angular)

- **Cola offline**: si `guardar_entreno` falla (sin señal en el gym, hosting
  caído), el entreno completo queda en `localStorage` y se **reenvía solo** al
  volver la conexión (evento `online`), al abrir la app, o con el botón
  "Reintentar ahora" del banner de pendientes. Un pendiente por fecha:
  reintentar el mismo día reemplaza, nunca duplica.
- **Anti duplicados**: el botón se deshabilita durante el envío y, tras
  guardar, cambia a "Guardado ✓"; un segundo envío el mismo día pide
  confirmación explícita (protege el historial, que es el combustible del
  motor de progresión).
- **Caché del plan**: la rutina del día se guarda en el teléfono al cargarla;
  si el servidor no responde, la app muestra la última copia y avisa que está
  en modo offline — puedes entrenar normal.

## I. Backups fechados del historial (`exportar_local.py`)

Cada descarga guarda además una copia en `python-engine/backups/historial-AAAA-MM-DD.csv`
(una por día, se conservan las últimas 30). El historial vive en un hosting
gratuito: estas copias locales son el respaldo real de tus datos.

## J. Botón "Recalcular y subir plan" (dashboard · Plan semana)

Corre el motor completo (`planificar.main()`: historial → progresión → subida
a MySQL) desde el navegador, sin terminal. Muestra el resultado y avisa si se
activó el deload reactivo.

## K. Suite de pruebas en el repo

`python-engine/tests/test_motor.py` — 38 comprobaciones automáticas de toda la
lógica de rutinas y progresión. Se corre con
`python tests/test_motor.py` desde `python-engine/`.

---

# Cuarta tanda — "tope de gama": autorregulación fina, e1RM, cintura, PWA

## L. Check-in de readiness pre-sesión (app)

Antes de entrenar, un toque: 😃 Bien / 😐 Normal / 😫 Cansada. En día "Cansada"
la app mantiene el mismo entreno pero cambia todos los objetivos de RPE a
7-8 **sin series al fallo** (RIR 3-4). Es la autorregulación diaria que la
evidencia respalda como mejor modulador sesión a sesión: entrenar suave
siempre gana a no entrenar. La elección persiste el día (localStorage).

## M. e1RM estimado — la fuerza real (dashboard)

Fórmula de Epley (`peso × (1 + reps/30)`, reps limitadas a 15):
- **Progresión**: nueva línea de e1RM junto a peso máximo y tonelaje — detecta
  PRs "invisibles" (mismos kg, más reps).
- **Records**: ahora rankea por e1RM y muestra la serie que lo produjo
  (`62.5 kg (50×8)`), no solo el peso más pesado.

## N. Cintura en la pestaña de peso (dashboard)

Campo opcional de cintura (1-2 veces/semana, a la altura del ombligo). Motivo:
en recomposición la báscula puede quedarse plana mientras pierdes grasa y
ganas músculo — solo el dúo peso+cintura lo distingue de un estancamiento.
El semáforo ahora tiene un **detector de recomposición**: peso plano + cintura
bajando ⇒ "no cambies nada, estás ganando".

## O. Historial en la app + endpoint nuevo

- `infinityfree/api/get_historial.php` (**hay que subirlo por FTP a `api/`**):
  devuelve las series de los últimos N días (JSON, tope 90).
- Botón 📓 en la app: últimas sesiones agrupadas por fecha con la mejor serie
  de cada ejercicio (por e1RM) — tu logbook en el teléfono.

## P. Confeti de PR 🎉 (app)

Al guardar, la app calcula el e1RM de cada ejercicio y lo compara con tu
récord local: si lo rompes, lluvia de confeti + vibración + mensaje con los
PRs. La primera vez solo registra la línea base (sin celebrar aire). La
gamificación de PRs tiene efecto medible en adherencia.

## Q. PWA — app instalable

`manifest.webmanifest` + `icon.svg` + `sw.js` (+3 archivos en el hosting):
- Instalable como ícono en el teléfono (Chrome/Android: "Agregar a pantalla
  de inicio").
- Service worker: navegación red-primero (nunca un shell viejo), estáticos
  caché-primero con refresco en segundo plano; `/api/` jamás se cachea.

## Verificación (cuarta tanda)

Suite completa en verde, smoke del dashboard con datos reales (e1RM, récords,
panel de peso con cintura), build de producción de la app sin errores.

---

# Quinta tanda — cobertura muscular garantizada y selección con intención

> Auditoría: ¿algún músculo queda "desapercibido"? ¿la selección de ejercicios
> y las alternativas son dirigidas o genéricas? Respuesta: había 4 huecos
> reales. Todos cerrados y ahora protegidos por pruebas automáticas.

## R. Hombro posterior y manguito — patrón propio

El Face Pull y el Pec Deck Invertido vivían dentro del patrón "hombro", donde
el generador siempre elegía elevaciones laterales: **el deltoide posterior
nunca aparecía en los planes generados**. Ahora `AISL_HOMBRO_POST` es un
patrón propio, presente cada semana (2.º día de torso en Upper/Lower, días
Pull en PPL, FB B en Full Body), siempre Tradicional a RIR 2-3 — es trabajo de
salud de hombro, jamás al fallo.

## S. Curl femoral — patrón propio en ambos días de pierna

Los curls de isquios vivían en "dominante de cadera", donde perdían contra las
extensiones lumbares: **la flexión de rodilla no aparecía nunca**. El RDL no la
cubre (la cabeza corta del bíceps femoral solo trabaja flexionando la
rodilla). Ahora `AISL_ISQUIOS` va en los dos días de pierna (tumbado un día,
sentado el otro).

## T. Variedad con intención entre días repetidos (Bloque C)

El 2.º día del mismo foco ahora usa el aislamiento alternativo: curl EZ ↔ curl
con mancuernas, extensión con cuerda ↔ con barra, laterales con mancuerna ↔ en
polea, curl femoral tumbado ↔ sentado. Cobertura de cabezas/ángulos distintos
en vez de repetir el estímulo exacto.

## U. El recorte por tiempo ya no "sacrifica" músculos enteros

Dos bugs del recorte por duración:
1. La superserie bíceps+tríceps contaba como 2 ejercicios (cuesta el tiempo de
   1: rondas de 60 s) → **a 60/75 min desaparecía todo el trabajo directo de
   brazos**. Ahora cuenta como 1.
2. El orden del Bloque C ahora ES la prioridad ante el recorte: primero lo que
   nadie más cubre (brazos, curl femoral, pantorrilla), al final lo redundante
   con los compuestos del día (aislamiento de pecho, extensión de cuádriceps).

## V. Alternativas de la app por FUNCIÓN, no por músculo genérico

`alternativasDe` ofrecía "mismo músculo primario": para un press militar
sugería elevaciones laterales o face pulls (no son sustitutos). Ahora cada
ejercicio del catálogo tiene un **grupo funcional** (empuje vertical, tirón
horizontal, bisagra de cadera, curl femoral…) y las alternativas se buscan por
grupo — un press se sustituye con otro press, un remo con otro remo. Si no hay
ninguna del mismo grupo, cae al músculo primario como red de seguridad.

## Volumen resultante (config real: recomposición, U/L, 75 min)

| Día | Ejercicios | Series |
|---|---|---|
| Torso A / Torso Bombeo | 7 | 18 |
| Pierna A / Pierna Bombeo | 6 | 16 |
| Cardio + Core ×2 | 4 | 10 |

Series directas/semana: dorsales 12 · cuádriceps 12 · hombros 10 · isquios 10
· pecho 6 (+aislamiento con sesiones de 90 min) · glúteos 6 · bíceps, tríceps
y gemelos 4 c/u (+ todo el trabajo indirecto de los compuestos). Ningún grupo
en cero; por sesión ningún músculo pasa de ~9 series duras (techo productivo
~8-10/sesión).

## Verificación (quinta tanda)

47 comprobaciones en verde, incluidas las nuevas: hombro posterior y curl
femoral presentes cada semana (U/L y PPL), bíceps distinto entre los dos días
de torso, hombro posterior nunca al fallo, y brazos directos conservados
incluso con recorte a 60 y 75 minutos.

---

# Sexta tanda — orden Push/Piernas/Pull y rotación por mesociclo

## W. PPL en orden Push · Piernas · Pull

A petición del usuario, el split PPL pasa de Push/Pull/Legs a
**Push/Piernas/Pull** (×2, domingo libre): el día de pierna separa las dos
sesiones de torso, de modo que hombros, codos y agarre llegan más recuperados
a cada sesión de empuje/tirón. Los antebrazos siguen anclados a los días de
Pull (miércoles y sábado, no consecutivos).

## X. Rotación de ejercicios por mesociclo (anti-tedio con método)

Cada mesociclo de 5 semanas el generador **rota al siguiente ejercicio
preferido** de cada patrón (press militar → Arnold → militar con barra → …,
con envoltura circular). El algoritmo, los patrones, los bloques y la
progresión no cambian — solo el ejercicio concreto que ocupa cada hueco.

**Fundamento**: la variación de ejercicios produce un desarrollo más uniforme
de la musculatura que repetir siempre el mismo movimiento (Fonseca 2014,
ref. 16), y la adherencia — el mejor predictor de resultados — mejora cuando
el plan no es tedioso. La progresión no se pierde: el historial es por
ejercicio, así que al volver un ejercicio 5 semanas después el motor retoma
su última marca. Verificado con pruebas: los ciclos 0–3 generan selecciones
distintas pero **la cobertura muscular y los patrones son idénticos**.

---

# Séptima tanda — rediseño mobile-first del front (iPhone)

> Auditoría de UX móvil con referencias de las apps mejor valoradas (Hevy,
> Strong) y las guías de iOS. El diagnóstico: el header apilaba 5 controles
> —difíciles de tocar en un iPhone— y la acción más importante (Guardar) estaba
> en la esquina superior derecha, el punto más incómodo para el pulgar.

## Y. Barra de acciones inferior (zona del pulgar)

Las apps líderes ponen las acciones en la mitad inferior de la pantalla, donde
el pulgar alcanza con una mano. Ahora hay una **barra fija al fondo** con los
toggles (Historial, Semana, Tema) y un botón grande **«Guardar entreno»**
(52 px de alto, muy por encima del mínimo de 44 px recomendado por Apple).
Respeta el `safe-area-inset-bottom` del iPhone. El cronómetro de descanso
flota justo encima de ella.

## Z. Barra de progreso de la sesión

Bajo el header, una barra muestra **«N/M series»** completadas con relleno
animado — patrón directo de Hevy. Da orientación (cuánto falta) y motivación;
al llegar al 100 % muestra «¡completo! 🎉».

## AA. Header simplificado + pulido táctil

El header se reduce a marca + día + racha. Se añadió `touch-action:
manipulation` (elimina el zoom por doble toque en iOS), estados `:active` con
micro-escala en los botones, y objetivos táctiles de 52 px. Verificado en
viewport de iPhone (375 × 812) vía dev server: barra fija anclada al fondo,
progreso reactivo al completar series, y cronómetro por encima de la barra.

**Referencias de diseño**: Hevy y Strong (apps de registro mejor valoradas en
la App Store) y las guías de área segura y objetivos táctiles de iOS.

---

# Octava tanda — ponderación por submúsculos y selección anti-redundancia

> Reporte de la usuaria: "hoy me pedía dominadas y el siguiente ejercicio
> jalón al pecho" (mismo dorsal ancho, estímulo casi idéntico) y "jalón
> unilateral con alternativa elevaciones laterales" (absurdo funcional).
> Ambos confirmados en el código y corregidos de raíz.

## AB. Taxonomía de submúsculos con ponderación (`ejercicios_db.py`)

Cada nodo muscular se divide en sus subregiones funcionales (espalda →
dorsal / espalda alta / trapecio superior / lumbar; hombro → anterior /
lateral / posterior; pecho → clavicular / esternal; pierna → cuádriceps /
isquios / glúteo / aductor / gemelo…) y **cada ejercicio declara cuánto
estimula cada una** en series efectivas (1.0 primario · 0.75 fuerte ·
0.5 secundario · 0.25 accesorio), según anatomía funcional y literatura EMG.
Ya no existe "espalda y ya": las dominadas son dorsal 1.0 + espalda alta 0.5
+ bíceps 0.5; un remo es espalda alta 1.0 + dorsal 0.75.

## AC. Selección por ganancia marginal (anti-redundancia)

Los bloques B y C ya no eligen "el preferido del patrón" a ciegas: cada día
lleva un **acumulador de estímulo por submúsculo**, y el candidato elegido es
el que más estímulo aporta donde MENOS se ha acumulado (retornos decrecientes,
la forma matemática de la dosis-respuesta). El peso del músculo objetivo
manda (v²) y los casi-empates los resuelve el orden canónico + rotación del
mesociclo. El Bloque A mantiene selección estable (progresión comparable).

## AD. Tope de saturación por sesión (anti-sobrecarga)

Si añadir un ejercicio dejaría TODOS sus submúsculos primarios por encima de
~10 series efectivas en la sesión, el slot se omite: era volumen basura.
Las simulaciones lo confirmaron: los picos bajaron de 14.0 (cuádriceps y
espalda alta en los combos de Volumen y Fuerza) a ≤12.

## AE. Rediseño de los días Pull/Push del PPL

La causa raíz de "dominadas + jalón": el día Pull llevaba tirón vertical en
el Bloque A **y** en el B. Ahora el B acumula en el patrón con más variedad
interna (remos: espalda alta/dorsal según agarre; presses de pecho: ángulos),
el jalón pesado es top set del segundo día de pull, y en días de Drop Set se
excluye el peso corporal (no se puede bajar −20 % a unas dominadas). Además
los aislamientos del Bloque C **no se repiten en la semana**.

## AF. Fix del clasificador del front ("unilateral" ≠ "lateral")

Las claves se buscaban por subcadena: "jalón **unilateral**" contenía
"lateral" → la app lo clasificaba como hombro y ofrecía elevaciones laterales
como alternativa. Ahora el matching exige **límites de palabra**. Verificado
en navegador: el Jalón Unilateral ofrece "Jalón al Pecho / Dominadas" y su
mapa muscular pinta dorsales/trapecios/bíceps.

## AG. Simulaciones automáticas (el "que no vuelva a pasar")

30 combinaciones (5 enfoques × 3 splits × 2 ciclos) se simulan en cada corrida
de tests: (1) ningún submúsculo supera 12.5 series efectivas por sesión,
(2) ningún submúsculo clave queda sin estímulo semanal, (3) máximo un tirón
vertical y un empuje vertical por día, (4) ningún aislamiento se repite
idéntico en la semana. Los picos reales quedaron en: isquios 12.0,
cuádriceps 11.8, espalda alta 11.5 — dentro del techo útil.

---

# Novena tanda — tope de compuestos por región (no 3 presses el mismo día)

> Observación de la usuaria (validada): su Push B tenía **Press de Banca Barra
> + Press de Banca Mancuernas** en el Bloque B — dos press planos = estímulo
> casi idéntico ("volumen basura", como lo describió su análisis). El sistema
> de submúsculos evitaba la *sobrecarga* (pecho en 10.2, bajo el techo) pero no
> esta *redundancia de variedad*. También se detectó espalda alta en **23
> series efectivas/semana**, por encima del rango productivo (10-20).

## AH. Tope de ejercicios compuestos por región y sesión

Cada región muscular tiene ahora un máximo de compuestos (Bloque A+B) por
sesión, según su tamaño y número de subregiones:

| Región | Tope/sesión | Razón |
|---|---|---|
| Pecho | 2 | Un plano + un inclinado, no tres presses |
| Press de hombro | 1 | No hacen falta dos press verticales |
| Espalda | 3 | Jalón + 2 remos (más subregiones: dorsal / espalda alta) |
| Cuádriceps | 2 | Sentadilla + prensa |
| Cadera | 3 | Glúteo + isquios + aductor |

Si un slot del Bloque B añadiría un compuesto por encima del tope de su
región, se omite (era redundante). Resultado en el Push B real: pasó de
**3 presses de pecho** (incline + 2 flat) a **2** (incline + 1 flat) + hombro
+ laterales + tríceps — exactamente la corrección que pedía el análisis.

## AI. Efecto en el volumen semanal (todo en rango productivo)

| Submúsculo | Antes | Ahora |
|---|---|---|
| Espalda alta | 23.0 (exceso) | 17.0 ✓ |
| Dorsal | 19.5 | 15.0 ✓ |
| Pico por sesión (espalda alta) | 11.5 | 10.0 |

Ningún grande queda fuera del rango 10-20 y ningún submúsculo supera ~12
series efectivas en una sesión. La regla se verifica sobre las 45
combinaciones (5 enfoques × 3 splits × 3 ciclos) en cada corrida de tests.

## Nota sobre "¿es un día de Push o falta la espalda?"

El análisis preguntaba si faltaban los patrones de tirón. **No faltan**: en un
split Push/Piernas/Pull, el día de empuje entrena a propósito solo pecho,
hombro y tríceps; la espalda tiene sus dos días de Pull dedicados. Es la
estructura del split, no un hueco.

---

# Décima tanda — protección lumbar (tope de bisagras axiales por sesión)

> Observación de la usuaria (validada): su Legs B apilaba **3 bisagras
> axiales** — Peso Muerto Rumano barra (A) + Peso Muerto Sumo (B) + Peso
> Muerto Rumano mancuernas (B) = 9 series de peso muerto pesado en un día,
> sobrecargando los erectores espinales con riesgo de lesión lumbar.

## AJ. Por qué el tope de región no bastaba

El tope de compuestos por región (tanda 9) permite hasta 3 en "cadera", pero
trata igual un hip thrust (espalda apoyada, sin carga espinal) que un peso
muerto (carga axial máxima sobre la columna). El volumen lumbar por submúsculo
quedaba en 4.5 (bajo el techo), así que ni el techo de submúsculo ni el de
región cazaban el problema real: la **fatiga sistémica y axial** de apilar
varios pesos muertos.

## AK. Tope de bisagras axiales (`ejercicios_db.py` + `generador.py`)

Nuevo concepto **`BISAGRA_AXIAL`**: los pesos muertos y RDL (barra, mancuernas,
convencional, sumo) cargan axialmente la columna; el hip thrust y el curl
femoral NO. Límite de **2 bisagras axiales por sesión** (`MAX_AXIAL_SESION`).
Al alcanzarlo, el Bloque B excluye las bisagras del pool, y el acumulador elige
trabajo de cadena posterior sin carga espinal (hip thrust, extensión lumbar en
máquina, curl femoral).

Resultado en Legs B: de **3 pesos muertos pesados** a **2** (RDL + Sumo) + un
accesorio seguro (extensión lumbar en máquina). Verificado en los 3 ciclos y
en las 45 combinaciones de la simulación: ninguna sesión apila más de 2
bisagras axiales, sin introducir huecos ni bajar el volumen fuera de rango.

## Referencias principales

- Refalo MC et al. (2023). *Influence of resistance training proximity-to-failure on skeletal muscle hypertrophy: systematic review with meta-analysis.* Sports Med.
- Robinson ZP et al. (2024). *Exploring the dose-response relationship between estimated resistance training proximity to failure, strength gain, and muscle hypertrophy.* Meta-analysis.
- Grgic J et al. (2022). *Effects of resistance training performed to repetition failure or non-failure on muscular strength and hypertrophy.* J Sport Health Sci.
- Schoenfeld BJ et al. (2016). *Longer interset rest periods enhance muscle strength and hypertrophy in resistance-trained men.* J Strength Cond Res.
- Schoenfeld BJ, Ogborn D, Krieger JW (2017). *Dose-response relationship between weekly resistance training volume and increases in muscle mass.* J Sports Sci.
- Pelland J et al. (2024). *The resistance training dose-response: meta-regressions of volume and hypertrophy/strength.*
- Iraki J, Fitschen P, Espinar S, Helms E (2019). *Nutrition recommendations for bodybuilders in the off-season.* Sports (Basel).
- Helms ER et al. (2014). *Evidence-based recommendations for natural bodybuilding contest preparation: nutrition and supplementation.* JISSN.
- Schoenfeld BJ, Aragon AA (2018). *How much protein can the body use in a single meal for muscle-building?* JISSN (distribución de proteína por comida).

## Verificación

Suite de pruebas con historial sintético (31 comprobaciones, todas en verde):
estructura de los 3 splits × 5 enfoques × 5 semanas, frecuencia 2× en Full
Body, pecho en C, fallo solo en S3–S4, superserie íntegra en Definición y en
todos los recortes de duración, RPE de trabajo, continuidad del historial por
familia, gating del PR de S4, doble progresión estricta y deload S5 sin fallo.
La app Angular compila sin errores tras el cambio de descansos.

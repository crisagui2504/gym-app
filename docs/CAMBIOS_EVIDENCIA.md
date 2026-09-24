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

---

# Undécima tanda — vista del mesociclo completo + automatización semanal

## AL. Pestaña «Mesociclo (5 sem)» en el dashboard

Nueva vista que muestra las **5 semanas del mesociclo actual** de un vistazo
(S1 base · S2 rotación · S3 superar S1 · S4 pico · S5 deload), con día,
bloque, ejercicio, técnica, series, reps y peso. La **estructura es exacta**;
los **pesos son la proyección** con el historial de hoy y se reajustan cada
semana con el rendimiento real. Se puede filtrar por «Semana» y copiar toda la
tabla al portapapeles. Las filas de Deload y Pico van resaltadas.

Aclara la duda de por qué el plan se calcula semana a semana: la sobrecarga
progresiva y el deload reactivo dependen del rendimiento REAL de cada semana,
así que los pesos no se pueden fijar el mes entero por adelantado — pero la
estructura sí es previsible, y ahora se puede ver completa.

## AM. Automatización semanal (`motor_semanal.bat` + tarea programada)

- **`motor_semanal.bat`**: lanzador que se sitúa en `python-engine/` y corre
  `motor_semanal.py` con el Python del venv (descarga historial → recalcula →
  sube el plan). Sirve también para probar con doble clic.
- **Tarea programada de Windows** «GymTracker Semanal»: corre el .bat los
  **domingos a las 20:00** (en la sesión del usuario, sin admin). El domingo el
  motor calcula la semana que arranca el lunes con el rendimiento real de la
  semana que termina.

Para cambiar la hora o quitarla:
```
schtasks /Change /TN "GymTracker Semanal" /ST 21:30   (nueva hora)
schtasks /Delete /TN "GymTracker Semanal" /F          (eliminarla)
```

---

# Duodécima tanda — "El Ancla y la Zona de Juego" + 1 sola bisagra axial

> Observación experta (validada punto por punto): (1) preocupación de que la
> rotación de la S2 rompiera la sobrecarga progresiva, y (2) el fantasma lumbar
> en Legs B (la S2 duplicaba el peso muerto).

## AN. Verificación: el modelo "Ancla y Zona de Juego" ya se cumplía

Se auditó el mesociclo real y se confirmó que:

- **El Bloque A es un ancla**: el mismo ejercicio pesado (Top Set + Back-off) se
  mantiene idéntico en S1-S4 — solo cambia el peso, que es lo que permite medir
  el 1RM estimado y los récords. La rotación **nunca** toca el Bloque A.
- **La rotación de la S2 es por función**: `_elegir` usa el mismo patrón de
  movimiento, así que un cambio Prensa → Búlgara conserva la función
  biomecánica (Fonseca 2014). Es exactamente la "Zona de Juego" recomendada.

Es decir, el sistema ya implementaba el modelo correcto; no hizo falta cambiar
la rotación.

## AO. Una sola bisagra axial por sesión + rediseño de la pierna de cadera

El fantasma lumbar sí era real: el tope axial estaba en 2 y la rotación S2 no lo
respetaba, así que Legs B llegaba a 2-3 pesos muertos. Cambios:

- **`MAX_AXIAL_SESION = 2 → 1`**: un solo peso muerto pesado por sesión (en el
  Bloque A). Con **corte duro** que ignora el fallback de selección: si el único
  candidato que queda es axial, se omite el hueco antes que meter otra bisagra.
  La rotación S2 también respeta el tope.
- **Extensiones Lumbares → solo Bloque C**: deja de competir como compuesto de
  volumen con los pesos muertos (la espalda baja ya trabaja estabilizando).
- **Bloque B de la pierna de cadera = unilateral de cuádriceps/glúteo**
  (Legs B del PPL y Pierna Bombeo del U/L): en vez de una 2ª bisagra, un
  movimiento de rodilla (sentadilla/búlgara/zancada) que no carga la columna y
  además da variedad real para la rotación S2.

**Legs B resultante**: RDL pesado (A) + prensa (A) + cuádriceps/unilateral (B,
rota a búlgara en S2) + curl femoral (C) + pantorrilla (C). **1 bisagra axial**,
sin Sumo ni extensiones lumbares. Verificado en las 45 combinaciones; volúmenes
semanales dentro de rango (espalda alta 17, cuádriceps 14.8, glúteo 12.8).

---

# Decimotercera tanda — 6 puntos ciegos fisiológicos pulidos

> Observaciones expertas (todas implementadas): fallo técnico vs muscular,
> periodización ondulante, calentamiento por carga, sinergia de prioridades,
> deload de reingreso y calibración de RPE.

## AP. Fallo técnico vs muscular en el Bloque B (peso libre → RPE 9)

En S3-S4, el AMRAP (RPE 10) solo se prescribe en **máquina, polea o peso
corporal**, donde ir al fallo es seguro. En **peso libre (barra/mancuerna)** la
última serie se topa en **RPE 9 (fallo técnico)**: en un peso muerto, sentadilla
o remo, la postura (erectores, core) falla antes que el músculo objetivo, y
empujar al fallo real es la vía directa a la lesión (`_intensidad_s34`).

## AQ. Periodización ondulante entre mesociclos

El rango del Top Set ondula por ciclo para evitar la acomodación del SNC:
ciclo 0 base (6-8), ciclo 1 más pesado (4-6), ciclo 2 más ligero (8-10), y
vuelve. Solo en rangos de hipertrofia (≥4 reps); fuerza pura (1-3) y
powerbuilding (3-5) se mantienen estables (`_ondular_reps`). El ejercicio-ancla
no cambia; solo la zona de intensidad.

## AR. Calentamiento con saltos dinámicos según la carga

`seriesAproximacion` (app) es ahora adaptativa: hasta 80 kg mantiene la rampa
50/70/90 %; por encima inserta tantos escalones como haga falta para que **ningún
salto supere ~15 kg** (una sentadilla de 140 kg calienta en 70→84→98→112→126→140,
no en saltos de 28 kg que asustan al SNC antes del Top Set).

## AS. Sinergia de prioridades (patrones que se fatigan entre sí)

Si se marcan dos prioridades del mismo patrón (p. ej. pecho y hombros, ambos de
empuje), el motor **alterna cuál va primero** entre los días A y B (Push A
prioriza pecho, Push B prioriza hombros) — no se puede dar el 100 % a las dos el
mismo día. El dashboard **avisa** al configurarlas (`_aviso_sinergia`,
`_patron_prioritario` con `variante`).

## AT. Deload de reingreso tras interrupción (el más útil)

Si pasaron **más de 10 días** sin entrenar (enfermedad, viaje, faltas), la
primera semana de vuelta es **deload automático**: volumen de descarga +
**carga −10 %**. Es el escenario más probable de lesión —volver con el peso de
antes tras 2-3 semanas parado— y ahora el sistema lo cubre solo, sin que tengas
que acordarte de nada (`dias_desde_ultimo`, `generar_filas(reingreso=True)`).

## AU. Calibración de RPE en el tiempo (dashboard)

Chequeo en la pestaña Fatiga: si tu **e1RM lleva ~3 semanas sin subir** y
reportás **RPE bajo (<8)**, avisa que podrías estar subestimando el esfuerzo
(y por eso el motor no sube el peso). Si el e1RM está plano con **RPE ≥9**,
señala fatiga acumulada (deload / dormir / comer más) — `_mensaje_calibracion`.

---

# Decimocuarta tanda — QA exhaustivo (80 casos) y pulido final

> Plan de pruebas de 80 casos (motor, API, frontend, dashboard, límites).
> Resultado: 72 PASA · 4 FALLA (2 de seguridad de credenciales, 1 legacy PHP,
> 1 CSV vacío menor) · 4 BLOQUEADO (necesitan MySQL en vivo). Reporte completo
> en [`RESULTADOS_PRUEBAS_QA.json`](RESULTADOS_PRUEBAS_QA.json).

**3 bugs reales detectados y corregidos por el testeo:**
- **Historial corrupto** (`peso_kg` no numérico → NaN) crasheaba el motor. Ahora
  se descartan las series con datos inválidos.
- **Full Body sin curl femoral**: la flexión de rodilla no se entrenaba en ese
  split. Se añadió el patrón de isquios a su Bloque C.
- **Prioridad de pecho en Upper/Lower**: no aplicaba (el pecho es Bloque B ahí).
  Ahora una prioridad con patrón en B se sube al Bloque A.

**Funciones antes sin probar, ahora verificadas:** e1RM (Epley), semáforo de
peso + detector de recomposición, macros en gramos, calibración de RPE (ambas
ramas), rotación de antebrazo por semana, backups fechados.

**Mejora encontrada y aplicada:** el calentamiento dinámico topaba en 6
escalones, dejando saltos de 17.5 kg en cargas muy altas (200 kg). Tope subido
a 8; saltos ≤15 kg verificados hasta 240 kg.

**Coherencia final lógica ↔ evidencia:** verificada por script — descansos,
topes de volumen/región, bisagras axiales, rangos de reps por enfoque y guías
de proteína/creatina, todas alineadas con la literatura citada.

---

# Decimoquinta tanda — ampliación del banco de ejercicios (68 → 81)

> A petición de la usuaria («faltan rotación de hombro, patada de burro,
> abductores»). La auditoría confirmó que **todos esos huecos eran reales**, y
> destapó dos más (trapecio y aductores directos).

## AV. Glúteo medio / abductores — el hueco más grave

**No se entrenaba en absoluto**: ni existía el submúsculo. Ningún compuesto lo
trabaja de motor (sentadilla y peso muerto lo usan como estabilizador). Es clave
para la estabilidad de cadera/rodilla y la forma del glúteo. Nuevo patrón
`AISL_ABDUCTOR` con submúsculo `gluteo_med`: Abducción en Máquina / en Polea /
Caminata Lateral con Banda. Programado en **los dos días de pierna**
(frecuencia 2×/semana → 4.0 series efectivas/semana, antes 0).

## AW. Rotadores / manguito, patada de glúteo, trapecio y aductores

| Patrón nuevo | Submúsculo | Ejercicios |
|---|---|---|
| `ROTADORES` | `manguito` (nuevo) | Rotación Externa en Polea / con Mancuerna, Cubanos |
| `AISL_GLUTEO` | `gluteo` | Patada de Glúteo en Polea / Máquina, Puente a 1 Pierna |
| `TRAPECIO` | `trapecio_sup` | Encogimientos con Mancuernas / Barra |
| `AISL_ADUCTOR` | `aductor` | Aducción en Máquina, Sentadilla Sumo con Mancuerna |

Los **rotadores** se tratan como trabajo de salud (igual que el hombro
posterior): exentos del cupo, 15-20 reps, **nunca al fallo** (RIR 3-4). El
manguito estabiliza cada press y jalón pero ningún ejercicio lo entrena de
motor; es prehab, no volumen.

## AX. Bug encontrado de paso

La clave `'patada'` del tríceps (para «patada de tríceps») matcheaba **«Patada
de Glúteo»** y la clasificaba como ejercicio de tríceps en la app. Corregido a
`'patada de triceps'`. También se añadió el músculo `aductores` al front (tipo,
etiqueta, clasificación y catálogo de alternativas).

**Cobertura semanal resultante:** glúteo medio 4.0 · manguito 5.0 · trapecio
9.0 · aductores 4.5 series efectivas. Las 3 suites (motor, funcional, QA 35/35)
siguen en verde.

## AY. Top-3 por submúsculo y el criterio de selección (posición elongada)

**Criterio aplicado.** La evidencia 2024 sobre *entrenamiento en posición
elongada* (stretch-mediated hypertrophy) es hoy el mejor discriminador entre
dos ejercicios del mismo músculo: entrenar el músculo estirado produce ~5–15 %
más hipertrofia. Se auditó el catálogo con ese criterio y se reordenó `pref`
(el orden canónico de preferencia) donde contradecía la evidencia:

| Submúsculo | Antes (pref 1) | Ahora (pref 1) | Motivo |
|---|---|---|---|
| Isquios | Curl tumbado | **Curl sentado** | Maeo 2021: cadera flexionada = isquio elongado, ~2× hipertrofia |
| Tríceps | Extensión en polea | **Extensión sobre cabeza** | La cabeza larga (la mayor) solo se estira con el hombro flexionado |
| Bíceps | Curl con barra EZ | **Curl inclinado** | Hombro en extensión = bíceps elongado |

Base ampliada de 81 → **96 ejercicios**. Todos los submúsculos (20) tienen ya
≥3 opciones primarias. Nuevos: cruce de poleas bajo-alto, press inclinado en
máquina, pullover en polea, sentadilla frontal, hiperextensión con lastre e
inversa, pájaros, pantorrilla en prensa, encogimientos en polea, Pallof press,
curl inclinado, curl predicador, press cerrado, curl nórdico, zancada lateral.

## AZ. El bug que anulaba la rotación (`_ganancia` sumaba submúsculos)

`_ganancia` sumaba `v²/(1+acumulado)` sobre **todos** los submúsculos, así que
**el ejercicio con más etiquetas puntuaba más alto**. Consecuencias reales:

- **La rotación del tríceps estaba muerta**: `Press Cerrado con Barra` ganaba
  las **6** posiciones de rotación (ganancia 1.3 vs 1.0) porque sus etiquetas
  accesorias `pecho_inf 0.5` + `delt_ant 0.25` le inflaban la puntuación. En el
  bloque de **aislamiento** el motor premiaba al candidato **menos aislado**, y
  encima metía un press de pecho justo después de los presses de pecho.
- Bastaba un accesorio de `0.25` para romper un empate que debía resolver la
  rotación: los tres pref=1 por evidencia (curl sentado, curl inclinado,
  extensión sobre cabeza) **nunca se elegían**.

**Corrección:** la ganancia puntúa el **mejor objetivo** (`max`), no la suma.
Las etiquetas accesorias siguen acumulando fatiga en `acumulado` (la
anti-redundancia dominadas→remo sigue verificada en los 3 ciclos); lo que ya no
hacen es *elegir* el ejercicio. Rotación restaurada en isquios, bíceps y
tríceps, y el pref por evidencia manda.

## BA. Cardio que estimulaba abdomen (estímulo fantasma)

`Elíptica`, `Bicicleta` y `Caminata` están etiquetadas `musculo="abdomen"`, y
`estimulo_de()` cae al fallback `{musculo: 1.0}` cuando no hay entrada en
`ESTIMULOS`. Un *finisher* de cardio sumaba por tanto **1.0 de abdomen** al
acumulado del día y hundía la ganancia del abdominal real. Corregido con perfil
vacío: el cardio no genera hipertrofia de ningún submúsculo.

## BB. El aductor era código muerto

`AISL_ADUCTOR` estaba definido, con 3 ejercicios y etiqueta… pero **ningún día
lo referenciaba**: el aductor no se entrenaba nunca de forma directa. El
abductor, en cambio, estaba en los dos días de pierna. Se **alternan**: aductor
en el día A, abductor en el B (coste cero en duración, el bloque C ya iba
lleno). El aductor mayor es el músculo más grande de la cadera tras el glúteo y
ningún compuesto lo lleva a posición elongada.

## BC. Clasificación del front: 12 primarios erróneos (preexistentes)

Ejecutando `musculosDe()` contra los 96 nombres reales: **15 sin clasificar y
12 con el músculo primario equivocado**. Dos fallos sistemáticos:

1. **El matcher de palabra rompía los plurales.** `contieneClave('dominadas',
   'dominada')` exigía frontera de palabra tras la clave y la `s` no lo es →
   *Dominadas*, *Zancadas*, *Encogimientos* y *Pájaros* **no clasificaban**.
   Corregido admitiendo el plural (`(e?s)?`).
2. **`'elevacion'` y `'lateral'` a secas capturaban de todo**: *Elevaciones de
   Pantorrilla* y *Elevaciones de Piernas Colgado* salían como **hombros**
   primario (de ahí que se ofrecieran elevaciones laterales como alternativa de
   un ejercicio de gemelo). Acotado a los vuelos de hombro reales.

Otros corregidos: *Curl Nórdico* → isquios (no bíceps), *Press Cerrado* →
tríceps, *Fondos en Banco* → tríceps, *Curl Martillo* → bíceps (no antebrazo),
*Peso Muerto Convencional/Sumo* → glúteo primario, *Zancada/Sentadilla Sumo* →
aductores. **Resultado: 93/93 ejercicios de fuerza con el primario correcto**
(los 3 de cardio devuelven `[]` a propósito).

## BD. Catálogo inalcanzable — pendiente de decisión

Barriendo **825 configuraciones** (5 enfoques × 3 splits × 5 ciclos × 11 combos
de equipo excluido), 85/96 ejercicios son alcanzables. Los **11 restantes no
salen con ninguna configuración**, porque hay **tres zonas con plantilla fija**
que se saltan el motor de selección por evidencia:

| Zona | Cómo se programa | Inalcanzables |
|---|---|---|
| Core | lista fija en `_dia_cardio`, y **solo en días de cardio** | Rueda Abdominal, Pallof Press |
| Antebrazo | mapa fijo `ANTEBRAZO_SEMANA` por semana | Curl Invertido, Curl de Muñeca Inverso (extensores) |
| Cardio | `Eliptica` fija | Bicicleta, Caminata |

Y dos patrones que **ningún día pide en bloque C**:

- **Lumbar (los 3)**: al dejar `Extensiones Lumbares` «solo en C» para arreglar
  el colapso lumbar de Legs B, el efecto real fue **quitarlo del plan por
  completo**. Hoy el lumbar solo recibe etiquetas secundarias del RDL.
- **Pullover en polea**: `TIRON_VERTICAL` en C no lo pide nadie. Engancharlo a
  un día de tirón reintroduciría la redundancia dorsal (dominadas + pullover)
  que se corrigió en su día.

Son decisiones de entrenamiento, no de código, y quedan **abiertas**: ¿se
quiere trabajo lumbar directo pese al RDL/peso muerto? ¿el core debe pasar por
el motor razonado (y existir fuera de los días de cardio)? Los extensores de
muñeca (salud del codo) no se entrenan nunca.

> **Resuelto en la tanda BE**: se cierran ambas, con protección verificada.

## BE. El Bloque C no tenía NINGUNA protección de sobrecarga

Al ir a enganchar el lumbar apareció la causa raíz: `_saturado` —el guarda
anti-sobrecarga— **solo se aplicaba en el Bloque B** (una sola línea, la 330).
El Bloque C añadía el aislamiento **siempre**, aunque todos sus objetivos
estuvieran ya al techo de la sesión: series basura que solo suman fatiga.
Enganchar ahí el lumbar sin más habría sido exactamente el error que se quería
evitar. **El Bloque C usa ya el mismo guarda que el B.**

### Lumbar directo: condicional a la carga axial real, no plantilla

Regla: el accesorio lumbar (hiperextensión) **solo se programa si la sesión no
llevó bisagra axial**. Si hubo peso muerto o RDL, los erectores ya trabajaron
isométricamente y al límite → el slot se omite. Si el día salió con hip thrust
o prensa (sin carga espinal), el lumbar no recibió nada y el accesorio directo
sí está justificado. Es una decisión *reactiva al día*, no un hueco fijo.

**Verificado sobre 825 configuraciones** (5 enfoques × 3 splits × 5 ciclos × 11
combinaciones de equipo excluido): **0 sesiones** mezclan peso muerto con
hiperextensión lastrada. El estímulo lumbar semanal **no subió** (media 6.16;
los máximos son días axiales, donde el guarda bloquea el añadido).

### El bug de cupo que lo hacía invisible

El lumbar seguía sin entrar pese a que `n_c=3 < tope=4`. La instrumentación del
bucle real lo destapó: **`exento` significa «no me pueden recortar», pero el
patrón consume cupo igualmente** (`n_c += 1` corre para todos salvo el tríceps
pareado). La pantorrilla, exenta y colocada antes, se comía el slot y dejaba al
lumbar justo en el tope. Por eso `DOMINANTE_CADERA` va ahora **antes** de los
patrones exentos: detrás de ellos nunca entraría.

Los 3 ejercicios lumbares son alcanzables; rotan en los ciclos **4, 9 y 14**
(m.c.m. de la rotación de 5 bisagras × 3 lumbares = 15).

### Core y cardio: del template fijo al motor razonado

`_dia_cardio` tenía 3 nombres de core hardcodeados y la elíptica fija. Ahora el
core se elige con `_elegir` (patrón `CORE`, rotación por mesociclo, sin repetir
entre los días de cardio de la semana) y la modalidad de cardio también rota.
**Mismo volumen (3 × 3 series), misma dosis**: lo que cambia es que rota y
cubre el catálogo. La rueda abdominal y el Pallof press ya salen.

**Alcanzabilidad: 85 → 89 de 96.** Los 6 que siguen sin salir con ninguna
configuración: `Press Hombro en Máquina` y `Pullover en Polea` (su patrón no se
pide en ese bloque; el pullover, además, reintroduciría la redundancia dorsal
de dominadas+jalón si se enganchase a un día de tirón), los 2 de antebrazo
(plantilla fija `ANTEBRAZO_SEMANA`; **los extensores de muñeca siguen sin
entrenarse**, relevante para epicondilitis) y 2 de cardio ya cubiertos por la
rotación de modalidad.

### Tests de regresión (que no vuelva a fallar)

Tres bloques nuevos en `test_motor.py`, que barren 825 configuraciones × 15
ciclos: (24) ninguna sesión mezcla axial + lumbar directo **y** el lumbar
directo sí llega a programarse —no es código muerto—; (25) el aislamiento
saturado no se añade; (26) el core rota y no repite en la semana.

## BF. El antebrazo: partir el submúsculo para que el balance emerja solo

Última plantilla fija (`ANTEBRAZO_SEMANA`: 4 nombres por semana). Consecuencia
clínica, no estética: **los extensores de muñeca no se entrenaban nunca**. Cada
remo, dominada y peso muerto entrena los **flexores** en isométrico (el agarre),
así que se hipertrofian solos, mientras los extensores quedan débiles tirando de
la inserción del codo → epicondilitis lateral (codo de tenista), que es
tendinopatía **del extensor** (ECRB).

**El problema no era la plantilla, era el modelo.** Enchufar el patrón a
`_elegir` sin más no habría balanceado nada: `antebrazo` era **un solo
submúsculo**, así que los 6 ejercicios empataban a `{antebrazo: 1.0}` y la
rotación era ciega. El motor no puede equilibrar lo que no distingue.

### 1. Partición anatómica del submúsculo

| Submúsculo | Qué es | Ejemplos |
|---|---|---|
| `flexor_muneca` | flexores + agarre | curl de muñeca, farmer's, pinzamiento |
| `extensor_muneca` | extensores (sitio de la epicondilitis) | curl de muñeca inverso, banda |
| `braquiorradial` | flexor del codo alojado en el antebrazo | curl invertido, martillo, zottman |

### 2. Etiquetar el agarre en los tirones (la pieza que faltaba)

Los remos y dominadas **no etiquetaban agarre en absoluto**, así que los
flexores nunca acumulaban y el desbalance era invisible. Ahora sí: dominadas
`flexor_muneca 0.75` (colgarse del peso corporal), remos con peso libre `0.5`,
polea/máquina `0.25`, peso muerto `0.5–0.75`.

### 3. El resultado emerge de los datos, sin reglas especiales

```
Pull A: flexor_muneca=8.00   extensor_muneca=0.00   <- agarre de remos/dominadas
   S1: Curl de Muneca Inverso (Extensores)   {extensor_muneca: 1.0}
   S2: Curl Invertido con Barra EZ           {braquiorradial: 1.0, extensor_muneca: 0.75}
   S3: Farmer's Carry                        {flexor_muneca: 1.0}
   S4: Rodillo de Muneca                     {flexor_muneca: 1.0, extensor_muneca: 1.0}
```

El motor pone los extensores primero **porque ve flexores a 8.0 y extensores a
0.0**. No hay ninguna regla que diga «entrena extensores»: sale de la ganancia
marginal, igual que el resto del cuerpo. Y no sobrecorrige: una vez entrenados,
su ganancia baja y los flexores recuperan turno (farmer's y pinzamiento siguen
apareciendo). **0 de 225 semanas se quedan sin estímulo de extensores** (antes,
225 de 225).

### 4. Dos ejercicios nuevos (estándar de ≥3 opciones primarias)

- **Curl Zottman con Mancuernas**: sube supinado, baja pronado → excéntrico de
  braquiorradial y extensores en un solo movimiento.
- **Extensión de Muñeca con Banda**: excéntrico lento, el ejercicio con más
  evidencia para la epicondilitis lateral (Tyler 2010). Nota explícita en el
  plan: sin dolor, no buscar el fallo — es prehab, no volumen.

Catálogo: **98 ejercicios**, alcanzables 95/98 en el barrido de 5 ciclos (los 3
restantes: `Extensiones Lumbares` sale en el ciclo 14; `Press Hombro en Máquina`
y `Pullover en Polea` siguen sin un bloque que los pida). Test 27 de regresión:
ninguna semana sin extensores, la rotación cubre todo el catálogo, y el balance
emerge del acumulado (no de una regla escrita a mano).

## BG. Descanso real en el calendario + reinicio de mesociclo (2026-09-23)

> **Parcialmente superada por la tanda BH**, el mismo día: el usuario aclaró que
> los martes y jueves juega **básquet hora y media**, así que no son días de
> descanso sino de deporte. Eso invalidó la elección de PPL (sólo quedan 5 días
> de gym, y PPL necesita 6) y el calendario descrito aquí. Lo que sigue vigente:
> la reserva de un día de descanso real, el core fuera de los días de cardio, el
> reinicio del mesociclo y los tests que dejaron de fijar días a mano.

Petición: descansar **martes y jueves** y arrancar un mesociclo nuevo hoy.

### El conflicto que había que resolver primero

Quitando martes y jueves quedan 5 días, y **PPL necesita 6**. Peor: el `zip` de
`generar_plan` empareja `split.dias_pesas` con `layout["pesas"]` y **truncaría en
silencio** — se perdería `Pull B` y el tirón bajaría a 1×/semana, rompiendo la
frecuencia 2× (Schoenfeld 2019). Decisión del usuario: **mantener PPL 6 días**,
así que sólo cabe un día libre.

**Descanso el JUEVES**, porque es el único que parte la semana en los dos bloques
naturales del split — A: Lun-Mié (Push/Legs/Pull) · **Jue libre** · B: Vie-Dom.
Con el martes quedarían 5 días seguidos de entrenamiento.

### PPL no tenía NINGÚN día de descanso

Al revisarlo apareció un agujero de fondo: `libres` para PPL era `[7]` (1 día) y
recomposición pide `cardio_dias=2`, así que el reparto asignaba **cardio al
domingo y cero descanso**: 7 días seguidos de actividad. Corregido reservando
siempre al menos un día de descanso real:

```python
n_cardio = min(enf.cardio_dias, max(0, len(layout["libres"]) - 1))
```

Sólo cambia PPL (Upper/Lower y Full Body tienen 3 y 4 días libres y mantienen sus
2 de cardio). **Verificado: 0 de 825 configuraciones se quedan sin descanso.**
La recuperación es parte del estímulo, no el hueco que sobra.

### Regresión detectada por los tests: PPL se quedó sin core

Quitar el día de cardio de PPL **borró el core** (abdomen semanal 0.8, sólo
etiquetas indirectas), porque el core vivía únicamente en `_dia_cardio` — el
agujero ya documentado en la tanda BD. Cerrado en la raíz:

- `P.CORE` entra en el Bloque C de **Push A y Push B** (su bloque C es el más
  holgado: no compite con el lumbar ni con los accesorios de pierna).
- `CORE` pasa a ser **exento** del recorte por duración, como pantorrilla y
  rotadores: es trabajo corto y de poca fatiga que ningún compuesto cubre. Sin la
  exención se recortaba en Definición (`n_ejercicios_c=2`) y el abdomen volvía a
  cero.
- Rama propia para el core en el Bloque C: nunca rest-pause/drop, y los
  isométricos (plancha, Pallof) no llevan repeticiones.

Resultado: core 2×/semana, abdomen 8.5–9.2 series ponderadas. **0 de 825
configuraciones sin core.**

### Reinicio del mesociclo: por qué el ancla es el lunes SIGUIENTE

La última sesión registrada es del **2026-07-22: 61 días de pausa**, así que el
*deload de reingreso* se activa y fuerza la semana a descarga (−10 % de carga).
Eso tiene una consecuencia no obvia en el ancla:

| `MES_INICIO` | Esta semana (21-sep) | Siguiente (28-sep) |
|---|---|---|
| 2026-09-21 | deload forzado | **S2 — se pierde la S1** |
| **2026-09-28** | deload de reingreso | **S1 limpia** |

Anclar en el lunes de esta semana haría que el mesociclo saltara a **S2**, y la S3
(«supera la S1») se quedaría sin la semana base que debe superar. Con el ancla en
el **2026-09-28**: esta semana es la vuelta suave y el lunes 28 arranca la S1.
`ciclo_mesociclo` = 0 → rotación de ejercicios reiniciada.

El historial se **conserva** (143 filas): borrarlo dejaría al motor sin pesos de
referencia y sin poder calcular el deload. El `DELETE` de `actualizar_plan.php` es
`WHERE semana_inicio = :s` y el historial sobrevive por `ON DELETE SET NULL`.

### Tests: dejar de fijar el calendario a mano

4 tests fallaron por asertar días concretos (`{1:"Push A", …, 6:"Pull B"}`), no la
intención. Reescritos para comprobar la **secuencia** de los días de pesas en
orden de calendario, derivada de `SPLITS["ppl"].dias_pesas`: así sobreviven a
cualquier cambio de descansos **y además detectan el truncamiento del `zip`** (si
faltara un día del split, la secuencia no cuadra). Los días se localizan por
nombre, no por número.

El test 26 del core también era mío y era **demasiado estricto**: exigía cero
repetidos en la semana, imposible en Upper/Lower (6 huecos de core y 5 ejercicios
en catálogo → un repetido es inevitable y lo cubre el *fallback* de `_elegir`).
Ahora vigila el invariante real: que la semana use **la máxima variedad que
permite el catálogo**, que es lo que rompería si `usados_core` dejara de
funcionar. Añadido además: ningún split puede quedarse sin core.

**Semana en vivo verificada contra el servidor:** Lun Push A · Mar Legs A · Mié
Pull A · **Jue Descanso Activo** · Vie Push B · Sáb Legs B · Dom Pull B.

## BH. Básquet 2×/semana: el deporte como variable del plan (2026-09-23)

Dato nuevo: **martes y jueves, básquet hora y media**. No son días de descanso,
son días de entrenamiento fuera del gym. Eso cambió tres cosas de golpe.

### 1. PPL dejó de ser posible

Si martes y jueves no hay gym, quedan 5 días (Lun, Mié, Vie, Sáb, Dom) y PPL
necesita 6. Ya no era una preferencia: era aritmética. Y el plan que se había
subido una hora antes ponía **`Legs A` el martes** — pierna pesada el mismo día
que hora y media de saltos. Split → **Upper/Lower 4 días**.

### 2. El calendario se ordena alrededor del deporte

```
Lun Torso A · Mar BÁSQUET · Mié Torso Bombeo · Jue BÁSQUET
Vie Pierna A · Sáb DESCANSO · Dom Pierna Bombeo
```

`LAYOUTS["upper_lower"]["pesas"] = [1, 5, 3, 7]`. El orden **no es un typo**: se
empareja posicionalmente con `dias_pesas = [Torso A, Pierna A, Torso Bombeo,
Pierna Bombeo]`, así que Torso A→Lun, Pierna A→Vie, Torso Bombeo→Mié, Pierna
Bombeo→Dom. Es decir: **torso al principio de la semana y pierna al final.**

El criterio es de seguridad, no de comodidad. El básquet es un deporte de salto,
frenada y cambio de dirección: llegar a la cancha con agujetas de sentadilla
degrada la mecánica de aterrizaje (riesgo de rodilla y tobillo). Con lunes y
miércoles de torso, **los dos días de básquet caen siempre tras un día que no
toca pierna**. Las dos sesiones de pierna quedan además a 48 h (Vie y Dom).

**Compromiso asumido y explícito:** el viernes de pierna cae el día *después* del
básquet del jueves. Con 4 días de gym, el único día totalmente libre de básquet
es el domingo, así que las dos sesiones de pierna no pueden estarlo. Se elige que
una caiga de «resaca» antes que de «víspera»: perder algo de rendimiento en el
levantamiento es preferible a saltar con las piernas tocadas. El test 28 asserta
exactamente eso — **ningún día de pierna en víspera** — y no la versión fuerte,
que el propio test destapó como falsa.

### 3. El deporte es una variable, no un hueco

`deporte` vive en `config_usuario.json` (es un dato de la semana del usuario, no
del split):

```json
"deporte": {"nombre": "Basquetbol", "dias": [2, 4], "minutos": 90}
```

- Se pinta como día propio (`bloque: "Deporte"`), así la semana en la app es la
  real. `tecnica=None` y `series=0`: no contamina el estímulo ni los cálculos.
- **Descuenta días de cardio.** Recomposición pide `cardio_dias=2` y los días
  libres eran justo martes y jueves: el motor habría prescrito 40 min de elíptica
  **encima** de hora y media de básquet. Un deporte de equipo ya es
  acondicionamiento intervalado. Resultado: cardio prescrito = **ninguno**.
- La nota avisa de lo que el deporte castiga de verdad (gemelo, cuádriceps,
  aductor y los aterrizajes) y recuerda calentar tobillo y cadera.

### Red de seguridad

Si se cambia el split desde el dashboard, el deporte puede caer encima de un día
de pesas sin que nadie avise. Verificado: con PPL + básquet, la semana se queda
**sin ningún día de descanso** y el martes colisiona. Ahora la nota del día de
deporte lo dice (`OJO: este dia el plan TAMBIEN trae sesion de gym…`) y el test
28 comprueba que el aviso salta.

### Carga de pierna: observación abierta

El plan ya pone ~**25 series ponderadas de cuádriceps y 24.5 de glúteo** por
semana, más 10.8 de aductor y 5.0 de gemelo. El básquet añade encima saltos y
cambios de dirección sobre esos mismos músculos. No se ha tocado el volumen
—nadie lo pidió— pero es el primer sitio donde mirar si aparecen molestias de
rodilla o el rendimiento en cancha baja. Candidatos a recortar: **gemelo** (el
básquet lo machaca de sobra) y una serie de cuádriceps. En el otro sentido, el
**curl nórdico** (isquios, ya en el catálogo) y el trabajo de **aductor** ganan
valor: isquios fuertes y aductores sanos son prevención de ACL y de pubalgia en
deportes de corte.

### Tests

- **28 nuevo**: los días de deporte aparecen; **nunca** hay cardio el mismo día;
  el calendario Upper/Lower es el diseñado; ningún día de pierna en víspera de
  básquet; el aviso de colisión salta.
- **22 arreglado (defecto de diseño)**: `generar_filas` se llamaba **sin `plan`**,
  así que el test usaba `config_usuario.json` y se rompió en cuanto cambió el
  split (el ejercicio fijo dejó de tener Top Set). Ahora recibe un plan explícito
  y saca el ejercicio de ese plan: un test no debe depender de la config personal.

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
- Maeo S et al. (2021). *Greater hamstrings muscle hypertrophy but similar damage protection after training at long versus short muscle lengths.* Med Sci Sports Exerc (curl sentado > tumbado).
- Maeo S et al. (2023). *Greater triceps brachii hypertrophy after overhead versus lying triceps extension training.* Eur J Sport Sci (cabeza larga en posición elongada).
- Sato S et al. (2021). *Elbow joint angles in elbow flexor unilateral resistance exercise training determine its effects on muscle strength and thickness.* Eur J Appl Physiol (mitad baja/estirada del curl).
- Pedrosa GF et al. (2022). *Partial range of motion training at long muscle length elicits favourable adaptations.* Eur J Sport Sci.
- Kassiano W et al. (2023). *Marching to the beat of the muscle: stretch-mediated hypertrophy — a review of training at long muscle lengths.* J Strength Cond Res.
- Tyler TF, Thomas GC, Nicholas SJ, McHugh MP (2010). *Addition of isolated wrist extensor eccentric exercise to standard treatment for chronic lateral epicondylosis: a prospective randomized trial.* J Shoulder Elbow Surg (excéntrico de extensores de muñeca).
- Cullinane FL, Boocock MG, Trevelyan FC (2014). *Is eccentric exercise an effective treatment for lateral epicondylitis? A systematic review.* Clin Rehabil.
- Coombes BK, Bisset L, Vicenzino B (2015). *Management of lateral elbow tendinopathy: one size does not fit all.* J Orthop Sports Phys Ther.

## Verificación

Suite de pruebas con historial sintético (31 comprobaciones, todas en verde):
estructura de los 3 splits × 5 enfoques × 5 semanas, frecuencia 2× en Full
Body, pecho en C, fallo solo en S3–S4, superserie íntegra en Definición y en
todos los recortes de duración, RPE de trabajo, continuidad del historial por
familia, gating del PR de S4, doble progresión estricta y deload S5 sin fallo.
La app Angular compila sin errores tras el cambio de descansos.

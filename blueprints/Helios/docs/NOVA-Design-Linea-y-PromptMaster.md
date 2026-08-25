# NOVA Platform — Línea de diseño completa + Prompt Master

Documento listo para Claude Design / Figma AI / diseñador UI-UX.  
Idioma de UI: **Español**. Marca shell: **NOVA**. Producto activo: **Helios**. Resto: **Próximamente**.

**Ruta canónica (adjunta este archivo en el chat de Claude):**  
`c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Documents\003 - Python Dev\Nova Data Solutions\NOVA-Design-Linea-y-PromptMaster.md`

Copia espejo en Helios: `Nova Projects/blueprints/Helios/docs/NOVA-Design-Linea-y-PromptMaster.md`

---

# PARTE A — LÍNEA DE DISEÑO COMPLETA

## 1. Concepto de marca

**Nombre plataforma:** NOVA  
**Tagline:** *El impulso inteligente de tu crecimiento*  
**Empresa:** Nova Data Solutions  
**Posicionamiento:** Suite bancaria de inteligencia, automatización y operación — una sola puerta de entrada a cinco productos mitológicos.

**Metáfora visual:** constelación / órbita. NOVA es el centro gravitacional; cada producto es un astro. Helios (sol) es el único activo; los demás orbitan en “Próximamente”.

**Mensaje guía (del pitch):** *La meta no es hacer más. Es hacerlo mejor.*

---

## 2. Arquitectura de información

```
NOVA (shell)
├── Auth
│   ├── Login
│   └── Cambiar contraseña
├── Launcher / Home plataforma          ← post-login
├── Núcleo compartido
│   ├── Clientes 360
│   ├── Seguridad (usuarios, grupos, políticas)
│   └── Ambiente / pruebas (solo Super)
└── Productos
    ├── HELIOS (activo)                 ← Fábrica de Crédito
    │   ├── Home producto
    │   ├── Operación
    │   │   ├── Casos
    │   │   └── Detalle de caso
    │   ├── Captación & Ventas          (tile; puede redirigir o placeholder)
    │   ├── Preaprobaciones & Buró      (tile / parcial vía APIs)
    │   ├── Motor de decisión           (tile / próximamente interno)
    │   ├── Diseño BPM
    │   │   ├── Flujos (+ editor)
    │   │   ├── APIs
    │   │   ├── Documentos
    │   │   ├── Datos complementarios
    │   │   └── Tipos de flujo
    │   └── Analítica de originación    (próximamente)
    ├── HERMES — Próximamente           ← Programa de Fidelidad
    ├── VENUS — Próximamente            ← Motivación al uso
    ├── ZEUS — Próximamente             ← Score de cobranzas
    └── ARES — Próximamente             ← Inventario de plásticos
```

### Navegación en 3 capas

1. **Plataforma:** logo NOVA + product switcher + avatar + logout  
2. **Producto:** rail o tabs del producto activo (solo visible dentro de Helios)  
3. **Trabajo:** contenido de la pantalla

Breadcrumb siempre: `NOVA / Helios / Casos / #1842`

---

## 3. Mapa de pantallas (entregables de diseño)

Diseñar en este orden (prioridad de wire → hi-fi):

| # | Pantalla | Prioridad | Notas |
|---|----------|-----------|-------|
| 01 | Login NOVA | P0 | Brand-first, sin dashboard clutter |
| 02 | Launcher / Home NOVA | P0 | 5 astros; Helios clickable; resto “Próximamente” |
| 03 | Shell app (chrome) | P0 | Top bar + switcher + slot contenido |
| 04 | Helios Home | P0 | Submódulos en tiles; CTA a Casos |
| 05 | Casos — lista | P0 | Filtros, tabla, nuevo caso |
| 06 | Caso — detalle | P0 | Timeline, docs, datos, acciones |
| 07 | Flujos — lista + editor | P1 | Canvas BPM limpio |
| 08 | APIs — lista + detalle | P1 | |
| 09 | Catálogos (docs/datos/tipos) | P1 | |
| 10 | Clientes — lista + detalle | P1 | Compartido |
| 11 | Seguridad (usuarios/grupos) | P2 | |
| 12 | Estados vacíos + Próximamente | P0 | Modal o página producto bloqueado |
| 13 | Mobile / tablet adapt | P1 | Sidebar → drawer |

---

## 4. Sistema visual — IDENTIDAD OFICIAL NOVA (fuente: web + design system)

> **Obligatorio.** Extraído de `Nova Projects/static/css/design-system.css`, login Nova Projects, y web `datanova.com.do` / `Web Nova Dev`.  
> **NO inventar** sky `#38BDF8`, ámbar `#F59E0B` como marca plataforma, ni logos de constelación. Eso fue un error del brief preliminar.

### 4.1 Logo oficial

Composición fija (ya en producción):

```
[ icon-n.png ] | NOVA
                 DATA SOLUTIONS
```

- Asset: `icon-n.png` (`Web Nova Dev/static/images/icon-n.png` · `Nova Projects/static/img/icon-n.png`)
- Nombre **NOVA**: Varela Round / Montserrat Bold, tracking amplio
- Sub **DATA SOLUTIONS**: Montserrat Light, letter-spacing amplio
- Divisor vertical sutil entre icono y texto
- **Nunca** reemplazar por sol, órbitas inventadas u otro monograma

Web pública: https://www.datanova.com.do/

### 4.2 Principios

- Brand first con **logo oficial**, no wordmark inventado.
- Paleta única NOVA estandarizada en toda la suite (login, launcher, shell, Helios).
- Helios/Hermes/… pueden tener *tinte de producto* suave; la plataforma y CTAs de marca usan el **gradiente Nova**.
- Cards solo con interacción. Sin emoji. Sin cream+serif terracotta.
- Tipografía de marca: **Montserrat** (+ Varela Round solo en wordmark NOVA).

### 4.3 Paleta oficial (tokens)

| Token | Hex | Uso |
|-------|-----|-----|
| `--nova-primary` | `#5B52E8` | Marca / acento principal (Nova Purple) |
| `--nova-primary-hover` | `#4A41D9` | Hover primary |
| `--nova-primary-soft` | `rgba(91,82,232,0.08)` | Fondos soft, chips |
| `--nova-secondary` | `#4A9FF5` | Marca secundaria (Nova Blue) |
| `--nova-secondary-hover` | `#3A8DE3` | Hover secondary |
| `--nova-gradient` | `135deg #5B52E8 → #4A9FF5` | CTAs de marca, highlights, icon wraps |
| `--text-1` / ink | `#1a1a2e` | Texto principal |
| `--text-2` | `#2d2d44` | Texto cuerpo |
| `--text-3`–`5` | `#4b5563`…`#9ca3af` | Jerarquía muted |
| `--bg-canvas` | `#eef0f5` | Fondo app operativa |
| `--bg-elevated` | `#FFFFFF` | Cards / barras |
| `--bg-inverted` | `#1a1a2e` | Paneles marca / sidebar |
| `--border-soft` | `#e1e3e8` | Bordes |
| `--success` | `#15803d` | OK |
| `--warning` | `#a16207` | Alerta |
| `--danger` | `#d4183d` | Error / destructivo |
| `--info` | `#4A9FF5` | Info (= secondary) |

**Productos (tinte, no reemplazan la marca):** Helios puede usar un acento cálido *secundario* solo en chip de producto; CTAs globales siguen siendo `--nova-gradient` / `btn-brand`. Hermes/Venus/Zeus/Ares: tintes locked desaturados, nunca como primary de plataforma.

### 4.4 Botones y acciones (estándar Nova Projects)

| Clase | Visual | Cuándo |
|-------|--------|--------|
| `btn-brand` | Gradiente Nova + texto blanco + shadow brand | CTA principal de marca (Ingresar, Entrar a Helios, Guardar crítico) |
| `btn-primary` | Fondo `#1a1a2e` + texto blanco | Acción primaria operativa (confirmar, crear) |
| `btn-secondary` | Blanco + borde soft | Secundaria |
| `btn-ghost` | Transparente | Terciaria / toolbar |
| Danger | `#d4183d` / soft | Cancelar caso, eliminar |
| Focus ring | `rgba(91,82,232,0.18)` | Todos los controles |

Estados obligatorios en diseño: default · hover · active · disabled · focus.

### 4.5 Tipografía

- **UI / todo el producto:** Montserrat (400–700)
- **Wordmark NOVA:** Varela Round o Montserrat Bold
- **No usar** Space Grotesk / Manrope / Inter como tipografía de marca

### 4.6 Iconografía de productos (módulos)

Símbolos de Helios/Hermes/… pueden ser lineales, pero el **logo de plataforma es siempre icon-n + NOVA**. No mezclar.

| Producto | Rol | Subtítulo |
|----------|-----|-----------|
| Helios | Activo | Fábrica de Crédito |
| Hermes | Locked | Programa de Fidelidad |
| Venus | Locked | Motivación al uso |
| Zeus | Locked | Score de cobranzas |
| Ares | Locked | Inventario de plásticos |  

---

## 5. Copy clave (ES)

**Login**  
- Marca: NOVA  
- Soporte: Data Solutions · Banca inteligente  
- CTA: Ingresar  

**Launcher**  
- Título: Elige tu impulso  
- Sub: Una plataforma. Cinco soluciones.  
- Badge locked: Próximamente  
- Helios CTA: Entrar  

**Helios Home**  
- Título: Helios  
- Sub: Núcleo que energiza y orquesta la originación  
- Tiles: Captación & Ventas · Preaprobaciones & Buró · Motor de decisión · BPM operativo · Analítica  
- CTA primaria: Ir a Casos  

**Footer conceptual (opcional launcher):**  
*La meta no es hacer más. Es hacerlo mejor.*

---

## 6. Submódulos Helios (contenido de tiles)

| Tile | Descripción UI | Estado UI |
|------|----------------|-----------|
| Captación & Ventas | Prospectos y canales de originación | Disponible o soft-link |
| Preaprobaciones & Buró | Consultas y dictámenes | Disponible vía APIs/BPM |
| Motor de decisión | Políticas y ruteo de aprobación | Próximamente (interno) |
| BPM operativo | Flujos, casos, documentos, datos | **Activo** (app actual) |
| Analítica de originación | Embudo, SLA, tasas | Próximamente |

---

## 7. Criterios de calidad (aceptación diseño)

- [ ] Quitando el nav, Login y Launcher siguen siendo claramente NOVA  
- [ ] Helios es el único producto con affordance de click pleno  
- [ ] Locked products no parecen rotos: badge + copy + sin dead-end frustrante  
- [ ] Dentro de Helios, el trabajo (casos) es rápido: contraste alto, densidad útil  
- [ ] Desktop 1440 + tablet 768 + mobile 390  
- [ ] Accesible: contraste AA, focus visible, labels en formularios  
- [ ] Sin emoji, sin purple gradient cliché, sin cards decorativas vacías  

---

# PARTE B — CÓMO USARLO EN CLAUDE DESIGN

## Pasos (en este orden)

1. **Adjunta en el chat** este mismo archivo:
   - `NOVA-Design-Linea-y-PromptMaster.md`
2. **Pega en el mensaje la ruta tal cual** (para que Claude identifique el brief), por ejemplo:
   - `c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Documents\003 - Python Dev\Nova Data Solutions\NOVA-Design-Linea-y-PromptMaster.md`
3. **Debajo de la ruta, pega el Prompt Master** (bloque de abajo).
4. Si Claude pide scope: responde *Fase 1 = pantallas P0 de la Parte A del archivo adjunto*.

> La ruta es referencia; **el contenido válido es el archivo adjunto**. Si no puede abrir disco local, debe leer el attachment del chat.

---

## Prompt Master (copiar desde aquí ↓)

````
# ROLE

Eres un Director de Diseño de Producto + UI/UX Lead world-class (fintech / B2B SaaS bancario).  
Diseñas interfaces modernas, premium y operables — no landings genéricas ni dashboards “AI purple”.  
Salida lista para handoff a ingeniería (FastAPI + Jinja/Bootstrap hoy; futuro React).

# FUENTE DE VERDAD (ARCHIVO ADJUNTO) — LEE ESTO PRIMERO

En este chat te adjunto el brief oficial:

**Nombre del archivo:** `NOVA-Design-Linea-y-PromptMaster.md`  
**Ruta de referencia (el usuario la pegará tal cual debajo o arriba de este prompt):**  
`c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Documents\003 - Python Dev\Nova Data Solutions\NOVA-Design-Linea-y-PromptMaster.md`

Reglas de uso del archivo:
1. **Lee completo el attachment** antes de diseñar. Ese markdown es la especificación.
2. Prioriza **PARTE A — LÍNEA DE DISEÑO COMPLETA** (concepto, IA, pantallas, tokens, copy, tiles, criterios).
3. Usa **PARTE C** solo cuando el usuario pida refinamiento por pantalla.
4. Usa **PARTE D** como notas de handoff a ingeniería (no inventes otra arquitectura de producto).
5. Si te dan la **ruta** en el mensaje: trátala como identificador del brief (mismo documento adjunto). No digas que “no tienes acceso al disco”; trabaja con el **archivo pegado/adjunto en el chat**.
6. Si algo en este prompt choca con el attachment: **gana el attachment** en producto/IA/copy/tokens; **gana este prompt** en proceso de entrega y orden de trabajo.
7. Antes de diseñar, confirma en 3 bullets que entendiste:
   - Shell = **NOVA**
   - Único producto usable = **HELIOS**
   - HERMES / VENUS / ZEUS / ARES = **Próximamente** (no diseñar pantallas internas de esos productos)

# MISIÓN

Diseñar la experiencia de **NOVA** (Nova Data Solutions):
- Plataforma central con launcher de 5 soluciones
- **Helios** activo (Fábrica de Crédito / BPM)
- Hermes, Venus, Zeus, Ares visibles pero locked → “Próximamente”

Entregar design system + pantallas hi-fi en **español**.

# RESUMEN OPERATIVO (detalle completo = attachment Parte A)

- Flujo: Login NOVA → Launcher → Helios Home → Casos → Detalle caso  
- UX en 3 capas: Plataforma → Producto → Trabajo  
- Fase 1 = pantallas **P0** listadas en Parte A §3  
- **Identidad visual OBLIGATORIA = Parte A §4** (logo icon-n, Montserrat, purple `#5B52E8` + blue `#4A9FF5` + gradient, sistema de botones btn-brand/primary/secondary/ghost)  
- **PROHIBIDO** reinventar marca con sky `#38BDF8`, ámbar `#F59E0B` como CTA de plataforma, Space Grotesk/Manrope, o logo de órbitas/sol inventado  
- Hard rules, copy y tiles: seguir Parte A del attachment

# FORMATO DE ENTREGA (EN ESTE ORDEN)

1. Confirmación de lectura del attachment (3 bullets)  
2. Concepto (5–8 líneas)  
3. Design tokens  
4. Component library  
5. Hi-fi pantallas P0 una por una  
6. Prototype flow (incl. click locked → Próximamente)  
7. Handoff notes + símbolos SVG de los 5 productos  

# CRITERIOS DE ÉXITO

Los de **Parte A §7** del attachment.  
Brand test: sin nav, Login/Launcher siguen siendo NOVA.  
En 3 segundos se entiende que solo Helios es usable.

# EMPIEZA AHORA

1) Lee el archivo adjunto.  
2) Confirma los 3 bullets.  
3) Entrega concepto + tokens + shell.  
4) Sigue con pantallas P0.  
No pidas más contexto salvo bloqueo real.
````

---

## Mensaje modelo para pegar en Claude (plantilla)

Copia/pega esto y adjunta el `.md`:

```
Brief adjunto (fuente de verdad):
c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Documents\003 - Python Dev\Nova Data Solutions\NOVA-Design-Linea-y-PromptMaster.md

[AQUÍ PEGAS EL PROMPT MASTER COMPLETO]

Scope: Fase 1 = pantallas P0 de la Parte A del archivo adjunto.
```

---

# PARTE C — PROMPTS SATÉLITE (usar después del Master)

## C1 — Solo Launcher

```
Usa el Design System NOVA ya definido. Diseña SOLO la pantalla Launcher 1440 y 390.
5 productos en constelación; Helios activo; Hermes/Venus/Zeus/Ares con badge Próximamente.
Una composición, brand-first, sin KPIs. Entrega hi-fi + microcopy + estados hover/locked.
```

## C2 — Solo Helios Home

```
Dentro del shell NOVA (producto Helios activo en el switcher), diseña Helios Home.
Tiles: Captación & Ventas, Preaprobaciones & Buró, Motor de decisión (próximamente), BPM operativo (activo), Analítica (próximamente).
CTA primaria: Ir a Casos. Estética sol/ámbar sin volverse marketing vacío.
```

## C3 — Casos operativos

```
Diseña Casos (lista) y Caso (detalle) para banco real: filtros Activo/Cerrado/Cancelado, tabla densa, badges de etapa, timeline, docs, datos, acciones de transición.
Prioriza velocidad y claridad. Mantén chrome NOVA + contexto Helios.
```

## C4 — Critica tu propio diseño

```
Audita el diseño NOVA contra: brand test, hero budget, no-cards-in-hero, contraste AA, clutter, AI-slop blacklist.
Lista findings + fixes concretos pantalla por pantalla.
```

---

# PARTE D — Notas para implementación (equipo BI)

- No reescribir el BPM: envolver Helios actual bajo shell NOVA.  
- Launcher = nueva ruta `/` o `/nova` post-login.  
- Product switcher: Helios → `/helios/...`; otros → modal Próximamente.  
- Rebrand gradual: `helios.css` → tokens `--nova-*` + `--helios-*`.  
- Mantener perfiles 1–4 y rutas existentes bajo prefijo o layout nuevo.

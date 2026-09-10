# Nova Projects — Knowledge Map

## Changelog
- **2026-09-03**: Inframe dc1: se quitó `nova.css` del iframe (CTA morado). Catálogos/admin al kit `if-*`. Cache `?v=20260903m`.
- **2026-09-03**: Inframe dc1: se quitó `claude-nova.css` del iframe (fondo oscuro/morado). Documentos/Flujos/APIs/Clientes/Datos pasan al kit `if-*`. Lienzo único en `base.html`.
- **2026-09-03**: Réplica 1:1 del Inframe Claude (`helios-inframe.css` en px del mock): bandeja 1a (Mi bandeja + tabla + paginación), caso 1b/1c (pipeline horizontal, docs en cards, API con score 36px), home 2a (tiles).
- **2026-09-03**: Puerto visual Helios Inframe (Claude Design) a Casos/Detalle/Home: bandeja clara, header blanco, chips neutros; push pendiente/en curso.
- **2026-09-03**: Diagnóstico: CSV se había importado a BD equivocada; ahora `instance/helios.db` tiene el export; auto-import CSV al boot (`import_csv_export.py`) + push `7846981`.
- **2026-09-02**: Import CSV del .bak (`scripts/import_helios_csv.py`, copia en `blueprints/Helios/data/export`); detalle caso con API humana + modal reporte; badges neutros; `.env` con `HELIOS_SEED_DEMO=0`.
- **2026-09-02**: Docs otra vez como adjuntos; script `migrate_helios_bak.py` (.bak SQL2025 → SQLite/Postgres). Un .bak no entra directo a Railway.
- **2026-09-02**: Documentación como checklist/form (sin adjuntos) + barra guardar fija; UI caso/shell más neutra.
- **2026-09-02**: Fix seed docs BigInteger (flush) — el rollback vaciaba clientes en Railway.
- **2026-09-02**: Fix 500 Clientes 360 (Jinja `dict.items`) + catálogo/expediente Documentación dummy.
- **2026-09-02**: Flujo multi-rol 8 etapas + 12 clientes 360; fix IdLog SQLite al Ejecutar API.
- **2026-09-02**: Fix 500 Ejecutar API + identidad NOVA en caso; rail pegado a búsqueda.
- **2026-09-01**: Home público v2; login → `/nova` shell vacío.

## Stack
- Flask + Socket.IO en Railway: https://novadata-projects-production.up.railway.app/
- BD: `DATABASE_URL` (Postgres) o SQLite `instance/nova_projects.db`
- Identidad: logo `static/img/icon-n.png`, tokens `#5B52E8` / `#4A9FF5`, CSS `static/css/platform.css`

## Flujo UX
1. `/` home público v2 (constelación en movimiento, carrusel coverflow) — anónimo
2. Login → `/nova` shell vacío (sidebar siluetas, dropdown abierto)
3. Elegir solución → módulo (ej. `/helios`)
4. `/constelacion` y `/app` — legacy redirect → Helios
5. Adquirir → `/contacto?producto=...`
6. `/home` portales internos legacy

## Railway
1. Servicio con root = carpeta `Nova Projects`
2. Agregar **PostgreSQL** (Variables → `DATABASE_URL`)
3. `SECRET_KEY` fuerte
4. Deploy: Procfile corre `release: python init_db.py` luego gunicorn
5. Seed: `admin` / `admin` (cambiar tras primer login)

## Local
```powershell
cd "...\Nova Projects"
pip install -r requirements.txt
python init_db.py
python app.py
# http://127.0.0.1:5012
```

## Archivos clave
| Área | Ruta |
|------|------|
| App | `app.py` |
| BD | `database.py`, `init_db.py` |
| Soluciones | `solutions.py` |
| Catálogo UI | `templates/plataforma/marketing_home.html`, `contacto.html` |
| CSS marca | `static/css/claude-nova.css` |
| Carga NOVA | `templates/macros/nova_loader.html` (overlay `.nv-load`, variante inline para el iframe) |
| Import Helios CSV | `scripts/import_helios_csv.py` → `instance/helios.db` |
| Export dummy | `blueprints/Helios/data/export/*.csv` |
| API UI caso | `blueprints/Helios/app/services/api_result_view.py` + `templates/casos/detalle.html` |
| Inframe CSS | `blueprints/Helios/app/static/css/helios-inframe.css` (px 1:1 del mock Claude) |
| Buró 360 | `blueprints/Helios/app/templates/partials/buro_documento.html` (gauge SVG, KPIs, cuentas, leads, localización) |
| Motor crédito | `blueprints/Helios/app/templates/partials/motor_documento.html` (dictamen, montos, endeudamiento) |
| Buró Demo API | `blueprints/Helios/app/services/buro_demo.py` (data ficticia determinista por cédula) |
| Buró normalizer | `blueprints/Helios/app/services/buro_view.py` (convierte formatos buró → template unificado) |

## Local Helios (datos del .bak vía CSV)
```powershell
$env:HELIOS_SEED_DEMO="0"
python scripts/import_helios_csv.py --wipe --dir "$env:USERPROFILE\Downloads\export"
# Usuarios export: admin + analista (hashes bcrypt del bak)
```

## Changelog reciente
- **2026-09-10 CALOR TOTAL B**: Rediseño `buro_documento.html` con gauge SVG, KPI strip condicional, secciones Leads/Consultas/Localización. Referencia: `\\bvwsrvap17\...\buro_credito\templates\reporte.html`.
- **2026-09-10 CALOR TOTAL B**: Helios Home rediseñado como dashboard (KPI cards + accesos rápidos), template `plataforma/helios_home.html`.
- **2026-09-10 CALOR TOTAL B**: Breadcrumbs rediseñados (chip fondo blanco, separador ›), redundancia nombre/cédula eliminada en `cliente_detalle.html`.
- **2026-09-10 CALOR TOTAL B**: Exception handler global en `main.py` para loguear tracebacks 500 en consola.
- **2026-09-10 CALOR TOTAL B**: CSRF middleware fix: no consumir body con `request.form()`, usar `request.body()` cached.
- **2026-09-10 CALOR TOTAL B**: API demo Buró Crediticio (`services/buro_demo.py`) con datos ficticios deterministas.
- **2026-09-10 CALOR TOTAL B**: Fix 500 en caso: `motor_documento.html` usaba `r.EndeudamientoPct` (atributo) sobre dict → migrado a `r.get()`.
- **2026-09-10 CALOR TOTAL B**: Endpoint REST `GET /catalogos/api/buro-demo/{cedula}` retorna JSON completo del buró demo.
- **2026-09-10 CALOR TOTAL C**: CSRF middleware soporta `multipart/form-data` (regex en body para uploads).
- **2026-09-10 CALOR TOTAL C**: Paleta unificada: `#003CA6` → `#5B52E8` en CSS buró+dashboard (30 ocurrencias). Gauge gradient usa gradiente NOVA.
- **2026-09-10 CALOR TOTAL C**: "Ver ficha" → "Vista 360": datos personales del cliente primero, sección de casos, luego buró.
- **2026-09-10 CALOR TOTAL C**: Resumen de endeudamiento (totales aprobado/adeudado/cuota/vencido) después de cuentas en `buro_documento.html`.
- **2026-09-10 CALOR TOTAL C**: Helios Home (NOVA shell) rediseñado: hero+saludo, grid 6 tiles, sección Producto.
- **2026-09-10 CALOR TOTAL D**: Dashboard Helios Home: greeting dinámico con usuario logueado (`session.get('nombre')`), KPIs (total/activos/cerrados/cancelados), 3 gráficos Chart.js (donut estado, barras etapa, línea tendencia mensual). Botón "Ir a Casos" eliminado. Route Flask `helios_home()` ahora consulta BD Helios via `SessionLocal`.
- **2026-09-10 CALOR TOTAL D2**: Dashboard minimalista: fuera verde `#22c55e`/naranja `#f59e0b`, solo paleta NOVA (`#5B52E8` activos, `#4A9FF5` cerrados, `#888CA0` cancelados). Fix distorsión en zoom bajo (`maintainAspectRatio:false` + `.hd-plot` con alto fijo). Clases con prefijo `hd-` para no colisionar con `.hh-stats` legacy. Serie mensual se agrupa en Python y rellena los 6 meses con 0.
- **2026-09-10 CALOR TOTAL E**: Notificaciones Helios unificadas como toasts minimalistas abajo a la derecha del iframe (`base.html` + `helios-inframe.css`). Duración por severidad: éxito 30 s, información 35 s, advertencia 45 s, error 60 s; cierre manual y barra de tiempo. Los flashes del servidor, errores AJAX y avisos del editor/API usan `window.HeliosToast`.
- **2026-09-10 CALOR TOTAL E**: Fix real de “Guardar datos”: SQLite no autoincrementaba `Casos_Datos_Complementarios.IdCasoDato` por ser `BIGINT`. `guardar_datos()` ahora aplica `apply_bigint_id()` y hace `flush` por fila nueva. Verificado con guardado de tres campos y toast “Datos guardados”.
- **2026-09-10 CALOR TOTAL F**: Breadcrumbs del shell unificados como `NOVA › Helios Producto › sección`; Home usa `Inicio Helios` y Vista 360 agrega `Clientes 360 › Vista 360`.
- **2026-09-10 CALOR TOTAL F**: Home sin Accesos rápidos; la fila inferior divide tendencia mensual y nuevo gráfico `Casos por flujo`. Los cuatro canvas mantienen altura fija y no generan overflow al reducir zoom.
- **2026-09-10 CALOR TOTAL F**: Vista 360 usa `Cliente` como identidad maestra aunque el buró/demo entregue otro nombre. Primer bloque reorganizado como información personal (nombre, nacimiento, edad, nacionalidad, sexo, identificación y contacto); el buró ya no repite una identidad contradictoria.
- **2026-09-10 CALOR TOTAL F**: Referencia de buró revisada desde `blueprints/buro_credito/templates/buro_credito/reporte.html`; no existe un PDF de referencia dentro del workspace. Gauge actualizado a gradiente NOVA.
- **2026-09-10 CALOR TOTAL G**: Home público con franjas alternas (`.nv-mk__band`): barra superior → hero limpio → pilares → constelación limpia → cierre CTA + pie. El tinte (`rgba(91,82,232,.14)` → `rgba(74,159,245,.06)`) enciende con fade vía IntersectionObserver (`is-lit`); las tarjetas dentro de franja suben a `#191834` para no perder borde.
- **2026-09-10 CALOR TOTAL G**: Animación de carga NOVA reutilizable (`templates/macros/nova_loader.html` + `.nv-load` en `claude-nova.css`): overlay oscuro al pulsar Ingresar y al entrar a una solución, y velo claro inline sobre el iframe de Helios (`#wsLoad`) que se reactiva con cada cambio de `src` vía MutationObserver y se apaga en el evento `load` (corte de seguridad a 10 s).
- **2026-09-10 CALOR TOTAL G**: Se eliminó la copia duplicada `blueprints/Helios/app/static/css/claude-nova.css` (92 KB, desactualizada) que sombreaba el CSS real del shell. Cache bust `claude-nova.css?v=20260910h`.
- **2026-09-10 CALOR TOTAL H**: Franjas finales del home = barra superior, pilares y bloque de cierre; el pie (`NOVA · El impulso… © 2026`) queda sin fondo.
- **2026-09-10 CALOR TOTAL H**: La animación de carga quedó sin texto ni barra (solo anillos + marca N). Duraciones: 3 s antes del login, 5 s al enviar el login y al entrar a una solución, 5 s mínimos al abrir el módulo en el iframe y 900 ms en los cambios de pantalla internos (tope de seguridad +15 s).
- **2026-09-10 CALOR TOTAL H**: Shell anclado al viewport (`body.page-shell` con `height:100dvh` + `overflow:hidden`): topbar, ruta y rail fijos; el scroll vive dentro del iframe, en `.nv-content` de las pantallas propias y en `.nv-rail__groups` cuando los módulos pasan del alto. La carga del iframe se dibuja solo sobre `.nv-workspace`. Cache bust `?v=20260910i`.
- **2026-09-10 DEPLOY**: Runtime actualizado de Python 3.12.6 a 3.12.11 para evitar el artefacto `cpython-3.12.6+20240909` que devolvía HTTP 500 durante el build de Railpack/Railway.

## Pitfalls
- Helios (FastAPI) + Flask comparten proceso vía `wsgi.py` (`a2wsgi`). APIs demo apuntan a `{RAILWAY_PUBLIC_DOMAIN}/demo-api/*`. Con `gunicorn -w 1`, `httpx` sync desde Helios hacia ese mismo host **deadlockea** el worker (~30s timeout) → UI “frisada”. Mitigar: workers/threads>1, invocación in-process, o mock en otro servicio.
- `postgres://` se normaliza a `postgresql://` en `database.py`.
- Tras deploy, si no hay Postgres, cae a SQLite efímero (no persistente en Railway sin volumen).
- `import_helios_csv.py --wipe` borra BPM/casos/clientes/APIs antes de recargar; con `HELIOS_SEED_DEMO=0` el bridge no pisa el export.
- Jinja2 + dicts: usar `r.get('Campo')` en vez de `r.Campo` en templates; si el dict no tiene la clave, `r.Campo` lanza `AttributeError` en vez de devolver `None`.
- Chart.js: con `maintainAspectRatio: true` (default) el lienzo crece en alto al bajar el zoom, porque el ancho disponible aumenta. Usar `maintainAspectRatio: false` + wrapper con `position: relative` y alto fijo en px; el `<canvas>` sin atributos `width`/`height`.
- `claude-nova.css` ya define `.hh-stats` (flex row de otra pantalla). Al crear bloques nuevos en Helios Home usar prefijo propio (`hd-*`) o se hereda `padding`/`font` de la regla legacy.
- OneDrive puede retrasar el flush a disco de `static/css/*`: Flask sirve la versión anterior aunque el editor muestre los cambios (comparar `(Get-Item ...).Length` contra el `Content-Length` servido). Verificar con `Array.from(document.styleSheets)` en el browser antes de asumir un error de CSS.
- `wsgi.py` enruta `/static/<rel>` a Helios **si el archivo existe** en `blueprints/Helios/app/static/` (`_is_helios_static`). Si un CSS del shell Flask tiene un gemelo con el mismo nombre ahí, se sirve el de Helios y los cambios en `static/css/` parecen no aplicar: comparar `(Get-Item ...).Length` contra el `Content-Length` servido. Ya se borró el duplicado de `claude-nova.css`; `nova.css` y `helios.css` siguen duplicados (hoy solo los usa Helios).
- Si el shell vuelve a hacer scroll completo, revisar alturas mínimas en px/vh dentro del layout: `.nv-workspace__frame` tenía `min-height: calc(100vh - 104px)` y eso empujaba el documento más allá del viewport aunque el flex ya estuviera bien.
- El servidor local no recarga plantillas Jinja en caliente: tras editar un `.html` hay que reiniciar (basta con tocar `app.py`) o se sigue sirviendo el HTML cacheado, incluido el `?v=` del CSS.
- SQLite solo autoincrementa automáticamente una PK declarada exactamente como `INTEGER PRIMARY KEY`; las PK `BIGINT` requieren `app.services.sqlite_ids.apply_bigint_id()`. Si se insertan varias filas en un mismo ciclo, ejecutar `db.flush()` después de cada alta para que el siguiente `MAX(id) + 1` no repita el identificador.
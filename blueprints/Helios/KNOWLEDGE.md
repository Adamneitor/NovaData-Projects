# Helios BPM — Knowledge Map

## Changelog
- **2026-08-24**: Plataforma NOVA en Helios: `/` catálogo público → login `?next=` → `/helios` home; logo `icon-n` + tokens `#5B52E8`/`#4A9FF5`; Hermes/Venus/Zeus/Ares Próximamente.
- **2026-08-24**: Corrección identidad: paleta oficial Nova `#5B52E8`/`#4A9FF5` + logo `icon-n`; prompt fix en `NOVA-Prompt-Correccion-Identidad.md`.
- **2026-08-24**: Prompt Master guía attachment+ruta; brief canónico en `Nova Data Solutions/NOVA-Design-Linea-y-PromptMaster.md`.
- **2026-08-24**: Brief + Prompt Master NOVA en `docs/NOVA-Design-Linea-y-PromptMaster.md` (shell NOVA, Helios activo, resto Próximamente).
- **2026-08-24**: Propuesta de rediseño: plataforma Nova centralizada (Helios/Hermes/Venus/Zeus/Ares) con módulos anidados; solo ideas, sin código.
- **2026-08-24**: Ruta creación de elementos + setup BD desde cero en máquina nueva.
- **2026-08-24**: Mapa inicial. Reglas API AND/OR + AUTO/MANUAL; mock en `mock_api_evaluacion/`.

---

## Instalación desde cero (máquina nueva)

### 1. Prerrequisitos
- Python 3.12+, Git, **ODBC Driver 17 o 18** para SQL Server
- Acceso a instancia SQL Server con **Windows Authentication**
- Usuario Windows con permiso `CREATE DATABASE` (solo la primera vez)

### 2. Base de datos SQL Server

**Instancia por defecto del proyecto:** `BVNBEET0110\BIDEV`  
**Base de datos:** `Helios`

En SSMS o `sqlcmd` (ajuste servidor si es distinto):

```sql
CREATE DATABASE Helios;
-- Opcional: asignar permisos explícitos al usuario Windows del dev
-- USE Helios; CREATE USER [DOMINIO\usuario] FROM LOGIN [DOMINIO\usuario];
-- ALTER ROLE db_owner ADD MEMBER [DOMINIO\usuario];
```

**Variables de entorno** (opcional; sobrescriben `app/config.py`):

| Variable | Default |
|----------|---------|
| `HELIOS_SQL_SERVER` | `BVNBEET0110\BIDEV` |
| `HELIOS_SQL_DATABASE` | `Helios` |
| `HELIOS_SQL_DRIVER` | `ODBC Driver 17 for SQL Server` |
| `HELIOS_SECRET_KEY` | clave dev (cambiar en prod) |
| `HELIOS_AD_DOMAIN` | `BVIMENCA` |

Ejemplo PowerShell sesión:
```powershell
$env:HELIOS_SQL_SERVER = "MI-SERVIDOR\INSTANCIA"
$env:HELIOS_SQL_DATABASE = "Helios"
```

### 3. Proyecto Python

```powershell
cd "...\Helios"
pip install -r requirements.txt
python init_db.py          # CREATE TABLE + migrate + seed
python -m app.migrate      # migraciones incrementales (tras git pull)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **URL:** http://127.0.0.1:8000 → `/` catálogo NOVA (público)
- Flujo: Catálogo → click Helios → `/login?next=/helios` → `/helios` → Casos/BPM
- **Login seed:** `admin` / `admin` (perfil Super Usuario)
- **Uploads:** se crea `uploads/` automáticamente
- Logo: `app/static/img/icon-n.png` · CSS marca: `app/static/css/nova.css`

**Verificar conexión:** si `init_db.py` falla, revisar driver ODBC, nombre instancia y que la BD exista.

---

## Ruta de creación de elementos (orden obligatorio)

Dependencias: cada paso usa catálogos/config del anterior.

```
[BD + init_db]
    ↓
1. Seguridad (perfil 1 o 2)          /admin/grupos → /admin/usuarios
    ↓
2. Catálogos BPM (perfil 1 o 3)
   · /catalogos/documentos           tipos de archivo a solicitar
   · /catalogos/datos                datos complementarios (montos, flags…)
   · /catalogos/tipos-flujo          Credito / Operativo (seed trae 2)
    ↓
3. APIs (perfil 1 o 3)               /apis → crear → /apis/{id}
   · Parámetros (body/query/path/header): origen fijo | dato | campo caso
   · Outputs (nombre + JsonPath + formato)
   · Probar contra un caso (/apis/{id}/probar)
    ↓
4. Flujo (perfil 1 o 3)              /flujos → crear → /flujos/{id}/editar
   · Etapas: docs, datos, grupos, orden, flags (final/retroceso)
   · Estados: inicial, cierra etapa, API asociado
   · Mapeos input/output del estado (si hay API)
   · Reglas API (AND/OR, AUTO/MANUAL) y/o reglas por datos
   · Transiciones manuales entre estados
   · Guardar Cambios (POST guardar-completo) — obligatorio
    ↓
5. Operación
   · /catalogos/clientes             alta de clientes
   · /casos → crear                  flujo activo + cliente → caso en estado inicial
```

**Mock evaluación (local, opcional):**
```powershell
cd mock_api_evaluacion; pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 3000 --reload
```
Config manual API + mapeo en flujo: `mock_api_evaluacion/GUIA_CONFIG_HELIOS.md`  
Token: `Bearer test-token-123` · URL: `http://127.0.0.1:3000/api/evaluacion`

---

## Layout / archivos clave

| Área | Ruta |
|------|------|
| Config BD | `app/config.py` |
| Init + seed | `init_db.py`, `app/seed.py`, `app/migrate.py` |
| Motor casos | `app/services/motor.py` |
| APIs + reglas | `app/services/api_engine.py`, `api_mapeo.py` |
| Flujo JSON | `app/services/flujo_completo.py`, `static/js/flujo_builder.js` |
| UI caso | `app/templates/casos/detalle.html`, `routers/casos.py` |
| Plataforma NOVA | `app/routers/platform.py`, `app/solutions.py`, `templates/plataforma/` |
| Marca CSS / logo | `static/css/nova.css`, `static/img/icon-n.png` |
| Redesign brief | `docs/NOVA-Design-Linea-y-PromptMaster.md` (+ canónico en carpeta `Nova Data Solutions/`) |

**Perfiles:** 1 Super · 2 Admin Credenciales · 3 Soporte · 4 Operativo

---

## Reglas de negocio (no romper)

1. Caso ACTIVO: usuario en grupo de la etapa (Soporte/Super actúan en todas).
2. Obligatorios completos antes de transicionar (`motor.pendientes_etapa`).
3. Estado con API: ejecuta HTTP → mapea outputs → reglas API (AND/OR, prioridad).
   - **AUTO:** avanza sin click si no hay pendientes.
   - **MANUAL:** botón «Confirmar transición API» (`/casos/{id}/mover-por-api`).
4. Reglas por datos: prioridad + default; «Continuar según condiciones».
5. Datos mapeados desde API = solo lectura en formularios.
6. Warning API: solo si el **último** log del caso falló.

---

## Hecho / Pendiente

**Hecho:** flujos BPM completos; shell NOVA (catálogo público, login con next, Helios home, logo+paleta oficial); resto soluciones Próximamente.  
**Pendiente:** tests auto; validar `api_conclusion_id` end-to-end; submódulos Captación/Motor/Analítica.

---

## Pitfalls

- Tras `git pull`: `python -m app.migrate`.
- BD nueva: `CREATE DATABASE` antes de `init_db.py`.
- JsonPath: usar `Dictamen` no `resultado.Dictamen` si la respuesta es plana.
- Mock: `es_asalariado` boolean/1/0, no `"Si"`.
- Flujo: siempre **Guardar Cambios** en editor; no mezclar editor legacy `flujos/etapa.html`.
- Reinicio datos BPM (solo Super): `/admin/ambiente` — borra flujos/casos, conserva usuarios.
- PowerShell: `;` no `&&`.

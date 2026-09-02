# Nova Projects — Knowledge Map

## Changelog
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

## Pitfalls
- Helios (FastAPI) + Flask comparten proceso vía `wsgi.py` (`a2wsgi`). APIs demo apuntan a `{RAILWAY_PUBLIC_DOMAIN}/demo-api/*`. Con `gunicorn -w 1`, `httpx` sync desde Helios hacia ese mismo host **deadlockea** el worker (~30s timeout) → UI “frisada”. Mitigar: workers/threads>1, invocación in-process, o mock en otro servicio.
- `postgres://` se normaliza a `postgresql://` en `database.py`.
- Tras deploy, si no hay Postgres, cae a SQLite efímero (no persistente en Railway sin volumen).

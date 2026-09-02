# Nova Projects — Knowledge Map

## Changelog
- **2026-09-02**: Seed flujo BPM **Demo Originacion TDC** (`scripts/seed_demo_flujo.py`): datos + grupo + etapas Captura→Buró→Motor→finales + reglas AUTO.
- **2026-09-02**: Shell pick: Desarrollo junto al dropdown; búsqueda por cédula; APIs demo `/demo-api/*` + `seed_demo_apis.py`.
- **2026-09-01**: Home público v2 (4a): hero orbital; login → `/nova` shell vacío.

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
- Helios BPM (FastAPI + SQL Server en `blueprints/Helios`) es aparte; Railway hostea este portal Flask.
- `postgres://` se normaliza a `postgresql://` en `database.py`.
- Tras deploy, si no hay Postgres, cae a SQLite efímero (no persistente en Railway sin volumen).

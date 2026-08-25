# Nova Projects — Knowledge Map

## Changelog
- **2026-08-25**: BD persistente (SQLite local / Postgres Railway); catálogo NOVA público → login → Helios; shell alineado a marca; `init_db.py` + Procfile release.

## Stack
- Flask + Socket.IO en Railway: https://novadata-projects-production.up.railway.app/
- BD: `DATABASE_URL` (Postgres) o SQLite `instance/nova_projects.db`
- Identidad: logo `static/img/icon-n.png`, tokens `#5B52E8` / `#4A9FF5`, CSS `static/css/platform.css`

## Flujo UX
1. `/` catálogo de soluciones (público)
2. Click Helios → `/login?next=/helios` si no hay sesión
3. `/helios` home producto
4. `/home` portales internos legacy
5. Hermes/Venus/Zeus/Ares → Próximamente

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
| Catálogo UI | `templates/plataforma/` |
| Shell | `templates/shell.html` |

## Pitfalls
- Helios BPM (FastAPI + SQL Server en `blueprints/Helios`) es aparte; Railway hostea este portal Flask.
- `postgres://` se normaliza a `postgresql://` en `database.py`.
- Tras deploy, si no hay Postgres, cae a SQLite efímero (no persistente en Railway sin volumen).

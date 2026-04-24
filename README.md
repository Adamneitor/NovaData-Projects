# Nova Projects

Portal modular interno de **Nova Data Solutions**. Construido sobre Flask + Socket.IO con arquitectura de blueprints, diseñado para agrupar módulos de negocio, riesgos, análisis de crédito e inteligencia de negocios.

---

## Stack

- **Backend**: Flask 3, Flask-SocketIO, Werkzeug
- **Realtime**: Socket.IO (eventlet)
- **Frontend**: Jinja2 + design system Nova (CSS variables, Montserrat, Font Awesome 6)
- **Producción**: Gunicorn + eventlet worker

---

## Estructura

```
Nova Projects/
├── app.py                      # Entrypoint Flask (rutas core)
├── blueprints/                 # Módulos funcionales
│   └── buro_credito/           # Blueprint: Buró de Crédito
├── templates/                  # Jinja2 (base, shell, auth, admin, modules)
├── static/
│   ├── css/                    # design-system.css + components.css
│   ├── img/                    # icon-n.png, favicon.png
│   ├── manifest.json           # PWA
│   └── sw.js                   # Service Worker
├── requirements.txt
├── Procfile                    # Comando de arranque para Railway
├── runtime.txt                 # Versión de Python para Railway
├── .gitignore
└── LICENSE
```

---

## Desarrollo local

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt

python app.py
```

La app queda en `http://localhost:5012`.

**Credenciales por defecto**: `admin` / `admin` (cambiar en `USERS_DB` o conectar a una BD real antes de producción).

---

## Variables de entorno

| Variable      | Por defecto       | Descripción                          |
|---------------|-------------------|--------------------------------------|
| `SECRET_KEY`  | `dev-secret-key…` | Clave de sesión Flask. **Cambiar en prod.** |
| `PORT`        | `5012`            | Puerto HTTP (Railway la inyecta).    |
| `FLASK_DEBUG` | `0`               | `1` para activar debug local.        |

---

## Deploy a Railway

1. **Sube este folder a un repositorio** (GitHub/GitLab).
2. En Railway: **New Project → Deploy from GitHub repo** → seleccionar el repo.
3. Railway detecta `requirements.txt` automáticamente y usa el `Procfile` incluido.
4. En **Variables**, agregá al menos `SECRET_KEY` con un valor aleatorio largo.
5. En **Settings → Networking** activá "Generate Domain" y listo.

> El `Procfile` usa gunicorn con eventlet (requerido para que Socket.IO funcione detrás de gunicorn):
>
> ```
> web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
> ```

---

## Atajos de teclado

- **Ctrl/Cmd + K** — foco en búsqueda global
- **Ctrl/Cmd + B** — ocultar/mostrar barra de portales
- **Ctrl/Cmd + Q** — modo enfoque (oculta header y sidebar, iframe a pantalla completa)

---

## Cómo agregar un módulo nuevo

1. Crear carpeta `blueprints/mi_modulo/` con `__init__.py`, `routes.py` y `templates/mi_modulo/`.
2. Registrar el blueprint en `app.py`:
   ```python
   from blueprints.mi_modulo import mi_bp
   app.register_blueprint(mi_bp)
   ```
3. Añadir entrada en `MODULES_DB` dentro de `app.py` con `id`, `name`, `icon`, `route`, `portal`, `permissions`.

Los templates del blueprint deben `{% extends "shell.html" %}` para heredar el layout global.

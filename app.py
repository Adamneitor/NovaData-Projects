"""
Nova Projects - Portal de soluciones Nova Data Solutions
Flask + Socket.IO · Postgres (Railway) / SQLite (local)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _lanzar_local_si_directo() -> None:
    """Run File / F5 en app.py: venv fuera de OneDrive + wsgi (portal + Helios)."""
    if __name__ != "__main__":
        return
    if os.environ.get("NOVA_SKIP_REEXEC") == "1":
        return
    root = Path(__file__).resolve().parent
    venv_py = Path(os.environ.get("LOCALAPPDATA", "")) / "NovaProjects-venv" / "Scripts" / "python.exe"
    wsgi = root / "wsgi.py"
    if not venv_py.is_file():
        sys.stderr.write(
            "Falta el venv local. En PowerShell, desde esta carpeta:\n"
            "  .\\run_local.ps1\n"
        )
        raise SystemExit(1)
    os.execv(str(venv_py), [str(venv_py), str(wsgi)])


_lanzar_local_si_directo()

from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from database import User, create_and_seed, db, init_app as init_database
from demo_apis import demo_api_bp
from solutions import (
    SOLUTIONS,
    default_entitlements,
    enrich_solutions,
    get_solution,
    sanitize_next_path,
)

app = Flask(__name__)

# --- SECRET_KEY: obligatoria en producción, default solo en dev ---
_DEFAULT_SECRET = "dev-secret-key-change-in-production"
_IS_PRODUCTION = bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
    or os.environ.get("RAILWAY_PROJECT_ID")
    or os.environ.get("NOVA_ENV", "").lower() == "production"
)
_secret = os.environ.get("SECRET_KEY") or _DEFAULT_SECRET
if _IS_PRODUCTION and _secret == _DEFAULT_SECRET:
    raise RuntimeError(
        "SECRET_KEY no está configurada o es el default de desarrollo. "
        "Defínela en las variables de entorno antes de correr en producción."
    )
app.config["SECRET_KEY"] = _secret
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PREFERRED_URL_SCHEME"] = "https" if _IS_PRODUCTION else "http"

init_database(app)

# SocketIO: CORS restringido (no wildcard)
_ALLOWED_ORIGINS = os.environ.get("NOVA_CORS_ORIGINS", "").strip()
_socketio_cors = _ALLOWED_ORIGINS.split(",") if _ALLOWED_ORIGINS else []
socketio = SocketIO(app, cors_allowed_origins=_socketio_cors or None)

# --- Rate limit login portal (paridad con Helios) ---
from collections import defaultdict
import time as _time

_PORTAL_LOGIN_FAILS: dict[str, list[float]] = defaultdict(list)
_PORTAL_LOGIN_MAX = 5
_PORTAL_LOGIN_WINDOW = 300  # 5 minutos


def _portal_login_rate_limited(key: str) -> bool:
    ahora = _time.time()
    eventos = [t for t in _PORTAL_LOGIN_FAILS[key] if ahora - t < _PORTAL_LOGIN_WINDOW]
    _PORTAL_LOGIN_FAILS[key] = eventos
    return len(eventos) >= _PORTAL_LOGIN_MAX


def _portal_registrar_fallo(key: str) -> None:
    _PORTAL_LOGIN_FAILS[key].append(_time.time())


def _portal_limpiar_fallos(key: str) -> None:
    _PORTAL_LOGIN_FAILS.pop(key, None)

# Blueprints
from blueprints.buro_credito import buro_bp  # noqa: E402

app.register_blueprint(buro_bp)
app.register_blueprint(demo_api_bp)

# Portales legacy (herramientas internas)
PORTALS_DB = [
    {
        "id": "negocios",
        "name": "Negocios",
        "icon": "briefcase",
        "description": "Herramientas operativas, clientes, ventas y seguimiento comercial",
        "permissions": ["admin", "analyst", "user"],
    },
    {
        "id": "riesgos-financieros",
        "name": "Riesgos Financieros",
        "icon": "shield-halved",
        "description": "Límites, alertas y modelos de Machine Learning para gestión de riesgo",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": "analisis-credito",
        "name": "Análisis de Crédito",
        "icon": "file-invoice-dollar",
        "description": "Scoring de originación, buró de crédito y evaluación crediticia",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": "inteligencia-negocios",
        "name": "Inteligencia de Negocios",
        "icon": "chart-line",
        "description": "BI, dashboards ejecutivos y análisis avanzado de datos",
        "permissions": ["admin", "analyst"],
    },
]

MODULES_DB = [
    {
        "id": 1,
        "name": "Gestión de Clientes",
        "icon": "users",
        "route": "/module/clientes",
        "portal": "negocios",
        "category": "CRM",
        "description": "Directorio centralizado de clientes, contactos y segmentación comercial.",
        "permissions": ["admin", "analyst", "user"],
    },
    {
        "id": 2,
        "name": "Pipeline de Ventas",
        "icon": "filter",
        "route": "/module/pipeline",
        "portal": "negocios",
        "category": "Ventas",
        "description": "Visualiza oportunidades en cada etapa del embudo de ventas.",
        "permissions": ["admin", "analyst", "user"],
    },
    {
        "id": 3,
        "name": "Reportes Comerciales",
        "icon": "file-lines",
        "route": "/module/reportes-comerciales",
        "portal": "negocios",
        "category": "Reportes",
        "description": "Informes mensuales de ventas, metas y performance por ejecutivo.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 5,
        "name": "Límites y Alertas",
        "icon": "bell",
        "route": "/module/limites",
        "portal": "riesgos-financieros",
        "category": "Control",
        "description": "Define límites de riesgo y recibe alertas cuando se acercan a umbrales.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 15,
        "name": "ECL - Pérdida Crediticia Esperada",
        "icon": "brain",
        "route": "/module/ecl",
        "portal": "riesgos-financieros",
        "category": "Machine Learning",
        "description": "Modelo de ML para estimar la pérdida crediticia esperada (Expected Credit Loss).",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 16,
        "name": "PD - Score Predictivo de Riesgo",
        "icon": "wand-magic-sparkles",
        "route": "/module/pd-score",
        "portal": "riesgos-financieros",
        "category": "Machine Learning",
        "description": "Probabilidad de incumplimiento (PD) generada por modelo predictivo supervisado.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 7,
        "name": "Scoring de Originación",
        "icon": "chart-simple",
        "route": "/module/scoring",
        "portal": "analisis-credito",
        "category": "Scoring",
        "description": "Modelo estadístico que asigna score crediticio durante la originación.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 14,
        "name": "Buró de Crédito",
        "icon": "id-card-clip",
        "route": "/module/buro-credito/",
        "portal": "analisis-credito",
        "category": "Consulta",
        "description": "Reporte crediticio completo por cédula: cuentas, score, historial y leads.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 10,
        "name": "Dashboard Ejecutivo",
        "icon": "chart-line",
        "route": "/module/dashboard-ejecutivo",
        "portal": "inteligencia-negocios",
        "category": "Dashboards",
        "description": "KPIs consolidados del negocio en una sola vista para la alta dirección.",
        "permissions": ["admin", "analyst"],
    },
    {
        "id": 11,
        "name": "Visualización de Datos",
        "icon": "chart-pie",
        "route": "/module/viz",
        "portal": "inteligencia-negocios",
        "category": "Análisis",
        "description": "Exploración interactiva de datasets con gráficos dinámicos.",
        "permissions": ["admin", "analyst", "user"],
    },
]


def _cookie_secure() -> bool:
    if request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https":
        return True
    return bool(request.is_secure)


def _attach_sso_cookie(resp, user: User | None = None):
    """Adjunta cookie SSO Helios (misma SECRET_KEY). Evita bucle login↔/casos."""
    from helios_bridge import SSO_COOKIE_NAME, sign_sso_token

    u = user or _current_user()
    if not u:
        return resp
    resp.set_cookie(
        SSO_COOKIE_NAME,
        sign_sso_token(u.username, u.name),
        max_age=60 * 60 * 12,
        httponly=True,
        samesite="Lax",
        secure=_cookie_secure(),
        path="/",
    )
    return resp


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            nxt = quote(request.full_path if request.query_string else request.path, safe="/?=&")
            if nxt.endswith("?"):
                nxt = nxt[:-1]
            return redirect(url_for("login", next=nxt or "/"))
        return f(*args, **kwargs)

    return decorated_function


def _post_login_url() -> str:
    """Tras login: selector de solución en shell vacío."""
    if session.get("nova_solution"):
        sol = get_solution(session["nova_solution"])
        if sol and sol.get("home_endpoint"):
            return url_for(sol["home_endpoint"])
    return url_for("nova_pick")


def nova_solution_required(f):
    """Exige haber elegido solución antes del módulo operativo."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get("nova_solution"):
            return redirect(url_for("nova_pick"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next="/admin/dashboard"))
        user = _current_user()
        if not user or user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 403
        return f(*args, **kwargs)

    return decorated_function


def _current_user() -> User | None:
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.filter_by(id=uid, active=True).first()


def _user_role() -> str:
    user = _current_user()
    return user.role if user else "user"


def _accessible_portals(user_role):
    return [p for p in PORTALS_DB if user_role in p["permissions"]]


def _accessible_modules(user_role, portal_id=None):
    modules = [m for m in MODULES_DB if user_role in m["permissions"]]
    if portal_id:
        modules = [m for m in modules if m.get("portal") == portal_id]
    return modules


def _current_portal_id():
    try:
        path = request.path or ""
    except Exception:
        return None
    if request.endpoint == "portal_view":
        return (request.view_args or {}).get("portal_id")
    for m in MODULES_DB:
        route = m.get("route", "")
        if not route:
            continue
        route_stripped = route.rstrip("/")
        if path == route or path.rstrip("/") == route_stripped:
            return m.get("portal")
        if route_stripped and path.startswith(route_stripped + "/"):
            return m.get("portal")
    return None


def _active_product() -> str | None:
    path = request.path or ""
    if path.startswith("/helios"):
        return "helios"
    return None


@app.context_processor
def inject_navigation():
    base = {
        "solutions": SOLUTIONS,
        "active_product": _active_product(),
        "nova_env": os.environ.get("NOVA_ENV", "development"),
    }
    try:
        endpoint = request.endpoint
    except Exception:
        endpoint = None
    base["shell_pick_mode"] = endpoint == "nova_pick"
    if "user_id" not in session:
        return base
    user = _current_user()
    if not user:
        return base
    entitled = default_entitlements()
    return {
        **base,
        "user": user.to_session_dict(),
        "nav_portals": _accessible_portals(user.role),
        "current_portal_id": _current_portal_id(),
        "solutions_enriched": enrich_solutions(entitled),
    }


# ---------- Plataforma NOVA ----------


@app.route("/")
def launcher():
    """Anónimo → home público v2. Autenticado → shell Helios."""
    if session.get("user_id"):
        return redirect(_post_login_url())
    return render_template(
        "plataforma/marketing_home.html",
        solutions=SOLUTIONS,
    )


@app.route("/explorar")
def explorar():
    """Home marketing siempre visible (también con sesión)."""
    return render_template(
        "plataforma/marketing_home.html",
        solutions=SOLUTIONS,
    )


@app.route("/nova")
@login_required
def nova_pick():
    """Shell vacío post-login: sidebar en siluetas y selector de solución abierto."""
    return render_template("plataforma/nova_pick.html")


@app.route("/constelacion")
@login_required
def constelacion():
    """Legacy: ya no hay hub post-login."""
    return redirect(_post_login_url())


@app.route("/app")
@login_required
def hub():
    """Legacy: redirige al shell operativo."""
    return redirect(_post_login_url())


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    producto = (request.values.get("producto") or "").strip().lower()
    sol = get_solution(producto)
    form = {
        "nombre": (request.form.get("nombre") or "").strip(),
        "empresa": (request.form.get("empresa") or "").strip(),
        "correo": (request.form.get("correo") or "").strip(),
        "mensaje": (request.form.get("mensaje") or "").strip(),
    }
    if request.method == "POST":
        if not form["nombre"] or not form["empresa"] or not form["correo"]:
            return render_template(
                "plataforma/contacto.html",
                solutions=SOLUTIONS,
                producto=producto,
                producto_label=sol["name"] if sol else None,
                form=form,
                error="Completa nombre, empresa y correo.",
                sent=False,
            )
        app.logger.info(
            "Contacto NOVA: %s | %s | %s | producto=%s | %s",
            form["nombre"],
            form["empresa"],
            form["correo"],
            producto or "constelacion",
            (form["mensaje"] or "")[:200],
        )
        return render_template(
            "plataforma/contacto.html",
            solutions=SOLUTIONS,
            producto=producto,
            producto_label=sol["name"] if sol else None,
            form={},
            sent=True,
        )
    return render_template(
        "plataforma/contacto.html",
        solutions=SOLUTIONS,
        producto=producto,
        producto_label=sol["name"] if sol else None,
        form={},
        sent=False,
    )


# Alias legacy del catálogo purple
@app.route("/catalogo")
def catalogo():
    return redirect(url_for("launcher"))


@app.route("/entrar/<solution_id>")
@login_required
def entrar_solucion(solution_id):
    sol = get_solution(solution_id)
    if not sol:
        return redirect(url_for("nova_pick"))
    entitled = default_entitlements()
    if sol["id"] not in entitled:
        return redirect(url_for("contacto", producto=sol["id"]))
    if not sol.get("active"):
        return redirect(url_for("contacto", producto=sol["id"]))
    session["nova_solution"] = sol["id"]
    target = url_for(sol["home_endpoint"]) if sol.get("home_endpoint") else "/helios"
    return redirect(target)


@app.route("/helios")
@nova_solution_required
def helios_home():
    sol = get_solution("helios")
    stats = {"total": 0, "activos": 0, "cerrados": 0, "cancelados": 0,
             "por_etapa": [], "por_mes": [], "por_flujo": []}
    try:
        from app.database import SessionLocal  # type: ignore
        from app.models import Caso, Etapa, Flujo  # type: ignore
        from sqlalchemy import func
        from datetime import date

        with SessionLocal() as db:
            stats["total"] = db.query(Caso).count()
            stats["activos"] = db.query(Caso).filter(Caso.estado_general == "ACTIVO").count()
            stats["cerrados"] = db.query(Caso).filter(Caso.estado_general == "CERRADO").count()
            stats["cancelados"] = db.query(Caso).filter(Caso.estado_general == "CANCELADO").count()

            por_etapa = (
                db.query(Etapa.nombre, func.count(Caso.id))
                .join(Caso, Caso.etapa_actual_id == Etapa.id)
                .filter(Caso.estado_general == "ACTIVO")
                .group_by(Etapa.nombre)
                .order_by(func.count(Caso.id).desc())
                .all()
            )
            stats["por_etapa"] = [{"etapa": e, "count": c} for e, c in por_etapa]

            por_flujo = (
                db.query(Flujo.nombre, func.count(Caso.id))
                .join(Caso, Caso.flujo_id == Flujo.id)
                .group_by(Flujo.nombre)
                .order_by(func.count(Caso.id).desc())
                .limit(6)
                .all()
            )
            stats["por_flujo"] = [
                {"flujo": nombre, "count": cantidad}
                for nombre, cantidad in por_flujo
            ]

            # Serie de los últimos 6 meses, agrupada en Python para no depender
            # de funciones de fecha propias del motor (strftime/date_trunc).
            hoy = date.today()
            meses = []
            anio, mes = hoy.year, hoy.month
            for _ in range(6):
                meses.append((anio, mes))
                mes -= 1
                if mes == 0:
                    anio, mes = anio - 1, 12
            meses.reverse()
            conteo = {clave: 0 for clave in meses}

            desde = date(meses[0][0], meses[0][1], 1)
            for (fecha,) in db.query(Caso.fecha_creacion).filter(
                Caso.fecha_creacion >= desde
            ):
                if fecha is None:
                    continue
                clave = (fecha.year, fecha.month)
                if clave in conteo:
                    conteo[clave] += 1

            nombres_mes = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                           "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            stats["por_mes"] = [
                {"mes": f"{nombres_mes[m - 1]} {str(a)[2:]}", "count": conteo[(a, m)]}
                for a, m in meses
            ]
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Helios home: no se pudieron calcular stats: %s", exc)
    nombre_usuario = session.get("nombre", session.get("user_nombre", "Admin"))
    return render_template(
        "plataforma/helios_home.html",
        solution=sol,
        nav_active="home",
        stats=stats,
        nombre_usuario=nombre_usuario.split()[0] if nombre_usuario else "Admin",
    )


@app.route("/helios/casos")
@nova_solution_required
def helios_casos():
    """Compat: abre Casos dentro del shell NOVA."""
    return redirect(url_for("helios_workspace", to="/casos"))

_HELIOS_NAV = (
    ("/casos", "casos", "Casos"),
    ("/catalogos/clientes", "clientes", "Clientes 360"),
    ("/flujos", "flujos", "Flujos"),
    ("/apis", "apis", "APIs"),
    ("/catalogos/documentos", "documentos", "Documentos"),
    ("/catalogos/datos", "datos", "Datos complementarios"),
    ("/catalogos/tipos-flujo", "tipos", "Tipos de flujo"),
    ("/admin/usuarios", "usuarios", "Usuarios"),
    ("/admin/grupos", "grupos", "Grupos"),
    ("/admin/politicas-password", "politicas", "Politicas"),
    ("/admin/ambiente", "ambiente", "Ambiente"),
)


def _helios_nav_meta(path: str) -> tuple[str, str]:
    base = path.split("?", 1)[0]
    for prefix, nav, label in _HELIOS_NAV:
        if base == prefix or base.startswith(prefix + "/"):
            return nav, label
    return "casos", "Casos"


@app.route("/helios/w")
@nova_solution_required
def helios_workspace():
    """Shell NOVA + iframe Helios (sin chrome propio)."""
    from flask import make_response

    target = sanitize_next_path(request.args.get("to"), "/casos")
    nav, label = _helios_nav_meta(target)
    sep = "&" if "?" in target else "?"
    iframe_src = f"{target}{sep}embed=1"
    resp = make_response(
        render_template(
            "plataforma/helios_workspace.html",
            iframe_src=iframe_src,
            embed_path=target.split("?", 1)[0],
            crumb_label=label,
            nav_active=nav,
        )
    )
    resp = _attach_sso_cookie(resp)
    resp.set_cookie(
        "nova_helios_embed",
        "1",
        max_age=60 * 60 * 12,
        httponly=True,
        samesite="Lax",
        secure=_cookie_secure(),
        path="/",
    )
    return resp


@app.route("/helios/entrar")
@nova_solution_required
def helios_entrar():
    """Handoff SSO a workspace embebido (no sale del shell NOVA)."""
    target = sanitize_next_path(request.args.get("to"), "/casos")
    return redirect(url_for("helios_workspace", to=target))


# ---------- Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    default_next = "/nova"
    next_path = sanitize_next_path(request.values.get("next"), default_next)
    if next_path == "/":
        next_path = default_next

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        if "\\" in username:
            username = username.split("\\")[-1].strip()
        password = request.form.get("password") or ""
        next_path = sanitize_next_path(request.form.get("next"), default_next)
        if next_path == "/":
            next_path = default_next

        # Rate limit (paridad con Helios)
        rate_key = f"{request.remote_addr}|{username.lower()}"
        if _portal_login_rate_limited(rate_key):
            return render_template(
                "auth/login.html",
                error="Demasiados intentos fallidos. Espere 5 minutos e intente de nuevo.",
                next_path=next_path,
            )

        user = User.query.filter_by(username=username, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            _portal_limpiar_fallos(rate_key)
            session.pop("nova_solution", None)
            session["user_id"] = user.id
            session["username"] = user.username
            session["user_role"] = user.role
            session["user_name"] = user.name
            user.last_seen = datetime.utcnow()
            db.session.commit()
            from flask import make_response

            return _attach_sso_cookie(make_response(redirect(next_path)), user)

        _portal_registrar_fallo(rate_key)
        return render_template(
            "auth/login.html",
            error="Credenciales inválidas",
            next_path=next_path,
        )

    if "user_id" in session:
        # Anti-bucle: Helios ya falló SSO con cookie presente → no redirigir otra vez
        if request.args.get("sso") == "fail":
            return render_template(
                "auth/login.html",
                error="No se pudo abrir Helios (SSO). Cierra sesión, borra cookies del sitio e intenta de nuevo.",
                next_path=next_path,
            )
        from flask import make_response

        return _attach_sso_cookie(make_response(redirect(next_path)))

    return render_template("auth/login.html", next_path=next_path)


@app.route("/logout")
def logout():
    session.clear()
    from flask import make_response
    from helios_bridge import SSO_COOKIE_NAME

    resp = make_response(redirect(url_for("launcher")))
    resp.set_cookie(SSO_COOKIE_NAME, "", max_age=0, path="/")
    resp.set_cookie("nova_helios_embed", "", max_age=0, path="/")
    return resp


# ---------- Shell legacy (portales) ----------
@app.route("/home")
@login_required
def home():
    user = _current_user()
    user_role = user.role
    portals = _accessible_portals(user_role)
    modules = _accessible_modules(user_role)
    portal_stats = []
    for p in portals:
        count = len([m for m in modules if m.get("portal") == p["id"]])
        portal_stats.append({**p, "module_count": count})
    return render_template(
        "home.html",
        user=user.to_session_dict(),
        portals=portal_stats,
        modules=modules,
        total_modules=len(modules),
        total_portals=len(portals),
    )


@app.route("/portal/<portal_id>")
@login_required
def portal_view(portal_id):
    user = _current_user()
    user_role = user.role
    portal = next((p for p in PORTALS_DB if p["id"] == portal_id), None)
    if not portal:
        return render_template("error.html", error="Portal no encontrado", code=404), 404
    if user_role not in portal["permissions"]:
        return render_template("error.html", error="No tienes acceso a este portal", code=403), 403
    modules = _accessible_modules(user_role, portal_id=portal_id)
    return render_template(
        "portal.html",
        user=user.to_session_dict(),
        portal=portal,
        modules=modules,
        total_modules=len(modules),
    )


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    user = _current_user()
    users = [u.to_session_dict() for u in User.query.order_by(User.id).all()]
    return render_template(
        "admin/dashboard.html",
        user=user.to_session_dict(),
        users=users,
        modules=MODULES_DB,
        stats={
            "total_users": len(users),
            "total_modules": len(MODULES_DB),
            "active_sessions": len([u for u in users if u.get("last_seen")]),
            "system_health": "healthy",
        },
    )


@app.route("/api/search")
@login_required
def search():
    query = request.args.get("q", "").lower().strip()
    user_role = _user_role()
    results = []
    if not query:
        return jsonify(results)
    for portal in PORTALS_DB:
        if user_role in portal["permissions"]:
            if query in portal["name"].lower() or query in portal["description"].lower():
                results.append(
                    {
                        "type": "portal",
                        "name": portal["name"],
                        "description": portal["description"],
                        "icon": portal["icon"],
                        "route": f"/portal/{portal['id']}",
                    }
                )
    for module in MODULES_DB:
        if user_role in module["permissions"]:
            if query in module["name"].lower() or query in module["description"].lower():
                results.append(
                    {
                        "type": "module",
                        "name": module["name"],
                        "description": module["description"],
                        "icon": module["icon"],
                        "route": module["route"],
                    }
                )
    for sol in SOLUTIONS:
        if query in sol["name"].lower() or query in sol["subtitle"].lower():
            results.append(
                {
                    "type": "solution",
                    "name": sol["name"],
                    "description": sol["tagline"],
                    "icon": sol["icon"],
                    "route": f"/entrar/{sol['id']}",
                }
            )
    return jsonify(results)


@app.route("/api/user/photo/<username>")
def get_user_photo(username):
    user = User.query.filter_by(username=username).first()
    if user and user.photo:
        return send_file(user.photo)
    return "", 404


@app.route("/api/modules")
@login_required
def get_modules():
    user_role = _user_role()
    return jsonify([m for m in MODULES_DB if user_role in m["permissions"]])


@socketio.on("connect")
def handle_connect():
    if "user_id" in session:
        emit(
            "notification",
            {
                "type": "info",
                "title": "Connected",
                "message": "Real-time connection established",
                "timestamp": datetime.now().isoformat(),
            },
        )


@socketio.on("disconnect")
def handle_disconnect():
    pass


@app.route("/module/<module_name>")
@login_required
def module_view(module_name):
    user = _current_user()
    expected_route = f"/module/{module_name}"
    module = next((m for m in MODULES_DB if m["route"] == expected_route), None)
    if not module:
        return render_template("error.html", error="Módulo no encontrado", code=404), 404
    if user.role not in module["permissions"]:
        return render_template("error.html", error="No tienes permiso", code=403), 403
    portal = next((p for p in PORTALS_DB if p["id"] == module.get("portal")), None)
    return render_template(
        "modules/module_frame.html",
        user=user.to_session_dict(),
        module=module,
        portal=portal,
    )


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", error="Page not found", code=404), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", error="Internal server error", code=500), 500


@app.before_request
def _ensure_db():
    # Idempotente: tablas + seed en el primer request del worker
    if not getattr(app, "_db_ready", False):
        try:
            create_and_seed(app)
            app._db_ready = True
        except Exception as exc:  # noqa: BLE001
            app.logger.exception("No se pudo inicializar BD: %s", exc)


@app.after_request
def _security_headers(resp):
    """Headers de seguridad para producto B2B."""
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    # CSP: permitir iframe same-origin (Helios embebido)
    resp.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
    # HSTS solo si el request llega por HTTPS/proxy
    if request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


@app.after_request
def _ensure_helios_sso(resp):
    """En cada respuesta Flask autenticada, refresca cookie SSO (rompe el bucle Railway)."""
    if session.get("user_id") and request.endpoint not in ("static", None):
        try:
            return _attach_sso_cookie(resp)
        except Exception:
            return resp
    return resp


if __name__ == "__main__":
    # El re-exec de arriba debería haber pasado a wsgi.py. Si llega aquí, arranque Flask solo.
    create_and_seed(app)
    port = int(os.environ.get("PORT", 5012))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    socketio.run(app, debug=debug, host="0.0.0.0", port=port, allow_unsafe_werkzeug=debug)

"""
Nova Projects - Personal Tools Portal
Flask + Socket.IO multi-module application
"""
import os
from flask import Flask, render_template, redirect, url_for, request, session, jsonify, send_file
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

socketio = SocketIO(app, cors_allowed_origins="*")

# --- Blueprints de módulos ---
from blueprints.buro_credito import buro_bp  # noqa: E402
app.register_blueprint(buro_bp)

# In-memory data store (replace with SQLite/PostgreSQL in production)
USERS_DB = {
    'admin': {
        'id': 1,
        'username': 'admin',
        'password': generate_password_hash('admin'),
        'name': 'Administrator',
        'email': 'admin@novaprojects.local',
        'role': 'admin',
        'photo': None,
        'created_at': datetime.now().isoformat()
    }
}

# Portales - Áreas de negocio que agrupan módulos relacionados
PORTALS_DB = [
    {
        'id': 'negocios',
        'name': 'Negocios',
        'icon': 'briefcase',
        'description': 'Herramientas operativas, clientes, ventas y seguimiento comercial',
        'permissions': ['admin', 'analyst', 'user']
    },
    {
        'id': 'riesgos-financieros',
        'name': 'Riesgos Financieros',
        'icon': 'shield-halved',
        'description': 'Límites, alertas y modelos de Machine Learning para gestión de riesgo',
        'permissions': ['admin', 'analyst']
    },
    {
        'id': 'analisis-credito',
        'name': 'Análisis de Crédito',
        'icon': 'file-invoice-dollar',
        'description': 'Scoring de originación, buró de crédito y evaluación crediticia',
        'permissions': ['admin', 'analyst']
    },
    {
        'id': 'inteligencia-negocios',
        'name': 'Inteligencia de Negocios',
        'icon': 'chart-line',
        'description': 'BI, dashboards ejecutivos y análisis avanzado de datos',
        'permissions': ['admin', 'analyst']
    },
]

# Módulos - Cada uno pertenece a un portal (campo 'portal')
MODULES_DB = [
    # Negocios
    {'id': 1, 'name': 'Gestión de Clientes', 'icon': 'users', 'route': '/module/clientes', 'portal': 'negocios', 'category': 'CRM', 'description': 'Directorio centralizado de clientes, contactos y segmentación comercial.', 'permissions': ['admin', 'analyst', 'user']},
    {'id': 2, 'name': 'Pipeline de Ventas', 'icon': 'filter', 'route': '/module/pipeline', 'portal': 'negocios', 'category': 'Ventas', 'description': 'Visualiza oportunidades en cada etapa del embudo de ventas.', 'permissions': ['admin', 'analyst', 'user']},
    {'id': 3, 'name': 'Reportes Comerciales', 'icon': 'file-lines', 'route': '/module/reportes-comerciales', 'portal': 'negocios', 'category': 'Reportes', 'description': 'Informes mensuales de ventas, metas y performance por ejecutivo.', 'permissions': ['admin', 'analyst']},

    # Riesgos Financieros
    {'id': 5, 'name': 'Límites y Alertas', 'icon': 'bell', 'route': '/module/limites', 'portal': 'riesgos-financieros', 'category': 'Control', 'description': 'Define límites de riesgo y recibe alertas cuando se acercan a umbrales.', 'permissions': ['admin', 'analyst']},
    {'id': 15, 'name': 'ECL - Pérdida Crediticia Esperada', 'icon': 'brain', 'route': '/module/ecl', 'portal': 'riesgos-financieros', 'category': 'Machine Learning', 'description': 'Modelo de ML para estimar la pérdida crediticia esperada (Expected Credit Loss) a nivel cliente y cartera.', 'permissions': ['admin', 'analyst']},
    {'id': 16, 'name': 'PD - Score Predictivo de Riesgo', 'icon': 'wand-magic-sparkles', 'route': '/module/pd-score', 'portal': 'riesgos-financieros', 'category': 'Machine Learning', 'description': 'Probabilidad de incumplimiento (PD) generada por modelo predictivo supervisado.', 'permissions': ['admin', 'analyst']},

    # Análisis de Crédito
    {'id': 7, 'name': 'Scoring de Originación', 'icon': 'chart-simple', 'route': '/module/scoring', 'portal': 'analisis-credito', 'category': 'Scoring', 'description': 'Modelo estadístico que asigna score crediticio durante la originación de clientes nuevos.', 'permissions': ['admin', 'analyst']},
    {'id': 14, 'name': 'Buró de Crédito', 'icon': 'id-card-clip', 'route': '/module/buro-credito/', 'portal': 'analisis-credito', 'category': 'Consulta', 'description': 'Reporte crediticio completo por cédula: cuentas, score, historial y leads pre-aprobados.', 'permissions': ['admin', 'analyst']},

    # Inteligencia de Negocios
    {'id': 10, 'name': 'Dashboard Ejecutivo', 'icon': 'chart-line', 'route': '/module/dashboard-ejecutivo', 'portal': 'inteligencia-negocios', 'category': 'Dashboards', 'description': 'KPIs consolidados del negocio en una sola vista para la alta dirección.', 'permissions': ['admin', 'analyst']},
    {'id': 11, 'name': 'Visualización de Datos', 'icon': 'chart-pie', 'route': '/module/viz', 'portal': 'inteligencia-negocios', 'category': 'Análisis', 'description': 'Exploración interactiva de datasets con gráficos dinámicos.', 'permissions': ['admin', 'analyst', 'user']},
]

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = USERS_DB.get(session.get('username'))
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Routes - Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = USERS_DB.get(username)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session['user_name'] = user['name']
            return redirect(url_for('home'))

        return render_template('auth/login.html', error='Invalid credentials')

    if 'user_id' in session:
        return redirect(url_for('home'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Helpers de contexto compartido
def _user_role():
    user = USERS_DB.get(session.get('username'))
    return user['role'] if user else 'user'

def _accessible_portals(user_role):
    return [p for p in PORTALS_DB if user_role in p['permissions']]

def _accessible_modules(user_role, portal_id=None):
    modules = [m for m in MODULES_DB if user_role in m['permissions']]
    if portal_id:
        modules = [m for m in modules if m.get('portal') == portal_id]
    return modules

def _current_portal_id():
    """Determina el portal activo según la URL actual.

    - En `/portal/<id>` devuelve ese id.
    - En `/module/<name>` o en rutas de blueprints que correspondan a un
      módulo registrado, devuelve el portal al que pertenece el módulo.
    - En otras rutas devuelve None.
    """
    try:
        path = request.path or ''
    except Exception:
        return None

    if request.endpoint == 'portal_view':
        return (request.view_args or {}).get('portal_id')

    for m in MODULES_DB:
        route = m.get('route', '')
        if not route:
            continue
        route_stripped = route.rstrip('/')
        if path == route or path.rstrip('/') == route_stripped:
            return m.get('portal')
        if route_stripped and path.startswith(route_stripped + '/'):
            return m.get('portal')

    return None

@app.context_processor
def inject_navigation():
    """Inyecta usuario, portales y portal activo al sidebar en todas las vistas
    autenticadas.

    Esto permite que cualquier template (incluyendo los de blueprints) que
    extienda `shell.html` tenga acceso a `user`, `nav_portals` y
    `current_portal_id` sin tener que pasarlos manualmente en cada
    `render_template`.
    """
    if 'user_id' not in session:
        return {}
    user = USERS_DB.get(session.get('username'))
    return {
        'user': user,
        'nav_portals': _accessible_portals(_user_role()),
        'current_portal_id': _current_portal_id(),
    }

# Routes - Main Shell
@app.route('/')
@app.route('/home')
@login_required
def home():
    user = USERS_DB.get(session.get('username'))
    user_role = _user_role()

    portals = _accessible_portals(user_role)
    modules = _accessible_modules(user_role)

    # Resumen de módulos por portal para mostrar en home
    portal_stats = []
    for p in portals:
        count = len([m for m in modules if m.get('portal') == p['id']])
        portal_stats.append({**p, 'module_count': count})

    return render_template('home.html',
                         user=user,
                         portals=portal_stats,
                         modules=modules,
                         total_modules=len(modules),
                         total_portals=len(portals))

@app.route('/portal/<portal_id>')
@login_required
def portal_view(portal_id):
    user = USERS_DB.get(session.get('username'))
    user_role = _user_role()

    portal = next((p for p in PORTALS_DB if p['id'] == portal_id), None)
    if not portal:
        return render_template('error.html', error='Portal no encontrado', code=404), 404

    if user_role not in portal['permissions']:
        return render_template('error.html', error='No tienes acceso a este portal', code=403), 403

    modules = _accessible_modules(user_role, portal_id=portal_id)

    return render_template('portal.html',
                         user=user,
                         portal=portal,
                         modules=modules,
                         total_modules=len(modules))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    user = USERS_DB.get(session.get('username'))
    return render_template('admin/dashboard.html',
                         user=user,
                         users=list(USERS_DB.values()),
                         modules=MODULES_DB,
                         stats={
                             'total_users': len(USERS_DB),
                             'total_modules': len(MODULES_DB),
                             'active_sessions': len([u for u in USERS_DB.values() if u.get('last_seen')]),
                             'system_health': 'healthy'
                         })

# API Routes
@app.route('/api/search')
@login_required
def search():
    query = request.args.get('q', '').lower().strip()
    user_role = _user_role()

    results = []
    if not query:
        return jsonify(results)

    # Buscar portales
    for portal in PORTALS_DB:
        if user_role in portal['permissions']:
            if query in portal['name'].lower() or query in portal['description'].lower():
                results.append({
                    'type': 'portal',
                    'name': portal['name'],
                    'description': portal['description'],
                    'icon': portal['icon'],
                    'route': f"/portal/{portal['id']}"
                })

    # Buscar módulos
    for module in MODULES_DB:
        if user_role in module['permissions']:
            if query in module['name'].lower() or query in module['description'].lower():
                results.append({
                    'type': 'module',
                    'name': module['name'],
                    'description': module['description'],
                    'icon': module['icon'],
                    'route': module['route']
                })

    return jsonify(results)

@app.route('/api/user/photo/<username>')
def get_user_photo(username):
    user = USERS_DB.get(username)
    if user and user.get('photo'):
        return send_file(user['photo'])
    return '', 404

@app.route('/api/modules')
@login_required
def get_modules():
    user = USERS_DB.get(session.get('username'))
    user_role = user['role'] if user else 'user'
    accessible_modules = [m for m in MODULES_DB if user_role in m['permissions']]
    return jsonify(accessible_modules)

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        emit('notification', {
            'type': 'info',
            'title': 'Connected',
            'message': 'Real-time connection established',
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('disconnect')
def handle_disconnect():
    pass

# Module routes (placeholder - aquí se registran blueprints reales)
@app.route('/module/<module_name>')
@login_required
def module_view(module_name):
    user = USERS_DB.get(session.get('username'))
    expected_route = f'/module/{module_name}'
    module = next((m for m in MODULES_DB if m['route'] == expected_route), None)

    if not module:
        return render_template('error.html', error='Módulo no encontrado', code=404), 404

    if user['role'] not in module['permissions']:
        return render_template('error.html', error='No tienes permiso para acceder a este módulo', code=403), 403

    portal = next((p for p in PORTALS_DB if p['id'] == module.get('portal')), None)

    return render_template('modules/module_frame.html',
                         user=user,
                         module=module,
                         portal=portal)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found', code=404), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error', code=500), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5012))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    socketio.run(app, debug=debug, host='0.0.0.0', port=port, allow_unsafe_werkzeug=debug)

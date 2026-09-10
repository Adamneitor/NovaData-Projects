# Arranque local NOVA + Helios (wsgi.py).
# El venv vive FUERA de OneDrive (regla AGENTS.md).
# No uses el python.exe de pythoncore-3.14-64 a pelo: no tiene Flask-SQLAlchemy.
$ErrorActionPreference = "Stop"
$Venv = Join-Path $env:LOCALAPPDATA "NovaProjects-venv"
$Py = Join-Path $Venv "Scripts\python.exe"
$Req = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path $Py)) {
  Write-Host "Creando venv en $Venv ..."
  $boot = $null
  foreach ($c in @(
      "C:\Users\adsanchez\AppData\Local\Python\pythoncore-3.14-64\python.exe",
      "python"
    )) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $boot = $c; break }
    if (Test-Path $c) { $boot = $c; break }
  }
  if (-not $boot) { throw "No se encontró Python para crear el venv." }
  & $boot -m venv $Venv
}

& $Py -m pip install -q --upgrade pip
# Python 3.14 no tiene rueda de psycopg2-binary==2.9.10 (local usa SQLite).
& $Py -m pip install -q Flask==3.0.0 Flask-SocketIO==5.3.6 Flask-SQLAlchemy==3.1.1 "SQLAlchemy>=2.0.41,<2.1" Werkzeug==3.0.1 python-dotenv==1.0.0 "fastapi>=0.115" "uvicorn[standard]>=0.30" "a2wsgi>=1.10" "python-multipart>=0.0.9" "httpx>=0.27" "itsdangerous>=2.2" "bcrypt>=4.1" "openpyxl>=3.1" python-socketio==5.11.0 python-engineio==4.9.0

Write-Host "http://127.0.0.1:5000  (login NOVA → Helios). Ctrl+C para parar."
Set-Location $PSScriptRoot
& $Py wsgi.py

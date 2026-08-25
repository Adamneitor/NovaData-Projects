# Helios BPM

Aplicación web para automatizar procesos operativos y de crédito mediante flujos configurables (BPM).

## Conceptos

- **Flujo**: proceso de negocio (ej. "Préstamo personal"). Tiene un tipo, etapas ordenadas y, opcionalmente, un API de integración que se invoca al concluir.
- **Etapa**: fase del flujo. En cada etapa se configura:
  - Documentos a solicitar (del catálogo), marcando cuáles son obligatorios.
  - Datos complementarios a capturar (del catálogo), obligatorios o no.
  - Grupos de usuarios que intervienen (si no se asigna ninguno, la etapa queda abierta a todos).
  - Marcas: etapa final, permite retroceso, solicita documentación al solicitante.
- **Estado**: situación dentro de una etapa. Se define cuál es el inicial y cuáles cierran la etapa. Un estado puede tener un **API asociado**: al entrar el caso a ese estado se ejecuta la llamada y las **reglas de direccionamiento** (output + operador + valor) mueven el caso a la etapa/estado que corresponda.
- **Transición**: movimiento manual permitido desde un estado hacia otra etapa/estado.
- **Caso**: instancia de un flujo en ejecución, con historial, documentos cargados, datos capturados y bitácora de ejecuciones de API.
- **API**: definición reutilizable de una llamada HTTP: método, URL (admite `{placeholders}` de path), headers, parámetros (valor fijo, dato complementario del caso o campo intrínseco del caso) y outputs (nombre + ruta JSON + formato).

## Requisitos

- Python 3.12+
- SQL Server con autenticación de Windows (servidor `BVNBEET0110\BIDEV`, base de datos `Helios`)
- ODBC Driver 17 o 18 para SQL Server

## Instalación

```powershell
pip install -r requirements.txt
python init_db.py        # crea tablas y datos semilla
uvicorn app.main:app --reload --port 8000
```

Abrir <http://localhost:8000> → **catálogo de soluciones NOVA**.  
Click en **Helios** → login → home Helios → Casos.  
Usuario inicial: `admin` / `admin`.

## Flujo de entrada

1. `/` — Catálogo público (Helios disponible; Hermes/Venus/Zeus/Ares = Próximamente)
2. `/entrar/helios` — pide login si no hay sesión
3. `/login?next=/helios` — identidad NOVA (logo `icon-n`)
4. `/helios` — home del producto
5. `/casos` … — BPM existente

## Configuración

Variables de entorno opcionales:

| Variable | Default |
|---|---|
| `HELIOS_SQL_SERVER` | `BVNBEET0110\BIDEV` |
| `HELIOS_SQL_DATABASE` | `Helios` |
| `HELIOS_SQL_DRIVER` | `ODBC Driver 17 for SQL Server` |
| `HELIOS_SECRET_KEY` | clave de desarrollo |

## Perfiles de usuario

1. **Super Usuario**: acceso total.
2. **Administrador de Credenciales**: gestiona usuarios y grupos.
3. **Soporte Operativo**: diseña flujos/APIs/catálogos y puede actuar sobre cualquier caso o cancelarlo.
4. **Operativo**: trabaja los casos en las etapas donde sus grupos intervienen.

## Orden sugerido de configuración

1. Seguridad → Grupos y Usuarios.
2. Diseño BPM → Documentos y Datos complementarios (catálogos).
3. Diseño BPM → APIs (si aplica): URL, parámetros y outputs.
4. Diseño BPM → Flujos: crear flujo → etapas → estados, transiciones, reglas de API, documentos/datos/grupos por etapa.
5. Operación → Clientes y Casos.

# Guía — Demo Helios multi-rol

## Ejecutar API (fix SQLite IdLog)

Si fallaba con `Casos_Api_Log.IdLog`, ya está corregido: PKs BigInteger en SQLite se asignan de forma segura.

## Clientes 360

Al abrir **Clientes** se listan los recientes (12 demo). También puedes buscar por cédula/nombre.

## Flujo «Demo Originacion TDC» (8 etapas)

| # | Etapa | Rol |
|---|--------|-----|
| 1 | Captura | Ejecutivo de Servicio |
| 2 | Documentación | Ejecutivo de Servicio |
| 3 | Consulta Buró (API) | Analista de Crédito |
| 4 | Evaluación Motor (API) | Analista de Crédito |
| 5 | Aprobación Gerente | Gerente Análisis (si motor = APROBADA) |
| 5b | Comité / Referimiento | Comité (si motor = REFERIDA) |
| 5c | Declinada | Final (si motor = DECLINADA) |
| 6 | Formalización | Operaciones Cierre |

Post-buró → siempre Evaluación Motor → ramifica a Gerente / Comité / Declinada.

## Usuarios demo (password `demo123`)

| Usuario | Rol |
|---------|-----|
| `admin` / `admin` | Super (todos los grupos) |
| `ejecutivo` | Ejecutivo de Servicio |
| `analista` | Analista de Crédito |
| `gerente` | Gerente Análisis |
| `comite` | Comité de Crédito |
| `operaciones` | Operaciones Cierre |

## Seed

```powershell
cd blueprints\Helios
python scripts\seed_demo_flujo.py --force --base-url https://novadata-projects-production.up.railway.app
```

También corre solo al arrancar Helios (`HELIOS_SEED_DEMO=1`).

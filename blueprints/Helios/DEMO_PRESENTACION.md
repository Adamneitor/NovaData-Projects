# Guía rápida — Demo Helios (presentación)

## Por qué no veía flujos/APIs

El seed anterior escribió en **SQLite local** (`instance/helios.db`). En Railway Helios usa **Postgres** (`DATABASE_URL`). Ahora el seed demo corre solo al arrancar Helios (`helios_bridge` + `init_helios_db`).

Tras el deploy, refresca Helios (o reinicia el servicio). Debes ver:
- **APIs**: Demo Motor Credito, Demo Buro Reporte
- **Flujos**: Demo Originacion TDC
- **Casos**: 3 dummy (Captura / Consulta Buro / Aprobacion cerrada)
- **Catálogos**: 14 datos, 2 documentos, 3 clientes, grupo Demo Operaciones

Opt-out: `HELIOS_SEED_DEMO=0`

---

## Endpoints demo

| API | URL | Dictamen |
|-----|-----|----------|
| Motor | `POST /demo-api/evaluacion` | APROBADA / REFERIDA / DECLINADA |
| Buró | `POST /demo-api/buro/reporte` | OK / ALERTA / RIESGO |

Auth: `Authorization: Bearer test-token-123`

---

## Seed manual (local o forzar)

```powershell
cd blueprints\Helios
python scripts\seed_demo_flujo.py --base-url https://novadata-projects-production.up.railway.app
python scripts\seed_demo_flujo.py --force   # recrea flujo+casos
```

---

## Casos dummy

| Cliente | Cédula | Etapa |
|---------|--------|-------|
| Ana María Pérez Rosario | 001-1234567-8 | Captura (datos llenos) |
| Carlos Enrique Méndez Ruiz | 002-9876543-2 | Consulta Buro (ALERTA) |
| Laura Beatriz Fernández Díaz | 003-4567890-1 | Aprobacion CERRADO |

---

## Checklist presentación

1. Login NOVA → Helios
2. Flujos → **Demo Originacion TDC**
3. APIs → las 2 demo
4. Casos → abrir Ana y avanzar Captura → Buro → Motor
5. Catálogos → datos / documentos / clientes

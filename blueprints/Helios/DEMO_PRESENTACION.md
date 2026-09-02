# Guía rápida — APIs demo Helios (presentación)

## Endpoints disponibles

| API | URL (Railway / NOVA) | Dictamen |
|-----|----------------------|----------|
| Motor crédito | `POST /demo-api/evaluacion` | `APROBADA` · `REFERIDA` · `DECLINADA` |
| Buró reporte | `POST /demo-api/buro/reporte` | `OK` · `ALERTA` · `RIESGO` |

Auth en ambas: `Authorization: Bearer test-token-123`

Health: `GET /demo-api/health`

Local standalone (opcional):
```powershell
cd blueprints\Helios\mock_api_evaluacion
uvicorn main:app --host 127.0.0.1 --port 3000 --reload
# POST http://127.0.0.1:3000/api/evaluacion
# POST http://127.0.0.1:3000/api/buro/reporte
```

---

## Seed en Helios (registra las 2 APIs)

```powershell
cd blueprints\Helios
python scripts\seed_demo_apis.py --base-url https://novadata-projects-production.up.railway.app
# o local:
python scripts\seed_demo_apis.py --base-url http://127.0.0.1:5012
```

Crea/actualiza:
- **Demo Motor Credito**
- **Demo Buro Reporte**
- Clientes demo: `001-1234567-8` (OK), `002-9876543-2` (ALERTA), `003-4567890-1` (RIESGO)

---

## Flujo sugerido para la demo (originación TDC)

1. **Captura** — datos: Salario, Asalariado, Tiempo laborando (meses)
2. **Consulta Buró** — asociar API `Demo Buro Reporte` (cedula ← cliente_identificacion)
   - Mapear outputs a datos: Score, MoraMaxDias, DictamenBuro, EicMax
3. **Evaluación Motor** — asociar API `Demo Motor Credito`
   - Inputs: salario/es_asalariado/tiempo_laborando ← datos; cedula ← caso
   - Reglas AUTO:
     - `Dictamen = APROBADA` → etapa Aprobación / Desembolso
     - `Dictamen = REFERIDA` → etapa Comité / Referimiento
     - `Dictamen = DECLINADA` → etapa Decl Soft / Cierre declinado
4. Etapas finales con `es_final` + estado `cierra_etapa`

---

## Request / Response

### Motor
```json
POST /demo-api/evaluacion
{"salario":45000,"es_asalariado":true,"tiempo_laborando":24,"cedula":"00112345678"}

→ {"Dictamen":"APROBADA","Monto_DOP":185000.0,"Monto_USD":3217.39,"Razon":"..."}
```

### Buró
```json
POST /demo-api/buro/reporte
{"cedula":"00112345678"}

→ {"Score":782,"DictamenBuro":"OK","MoraMaxDias":0,"EicMax":780000,"Resumen":"..."}
```

---

## Checklist presentación (15 min)

1. Login NOVA → elegir Helios
2. Catálogo → APIs → ver las 2 demo (botón Probar con caso)
3. Abrir flujo demo → mover caso Captura → Buró → Evaluación
4. Mostrar rama APROBADA / REFERIDA / DECLINADA según Dictamen
5. Con cliente `001-1234567-8` el buró sale limpio (OK); con `003-4567890-1` sale RIESGO

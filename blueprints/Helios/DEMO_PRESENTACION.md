# Guía rápida — Demo Helios (presentación)

## Endpoints disponibles

| API | URL (Railway / NOVA) | Dictamen |
|-----|----------------------|----------|
| Motor crédito | `POST /demo-api/evaluacion` | `APROBADA` · `REFERIDA` · `DECLINADA` |
| Buró reporte | `POST /demo-api/buro/reporte` | `OK` · `ALERTA` · `RIESGO` |

Auth en ambas: `Authorization: Bearer test-token-123`

Health: `GET /demo-api/health`

---

## Seed completo (APIs + flujo BPM)

```powershell
cd blueprints\Helios
python scripts\seed_demo_flujo.py --base-url https://novadata-projects-production.up.railway.app
# local:
python scripts\seed_demo_flujo.py --base-url http://127.0.0.1:5012
# recrear si ya hay casos:
python scripts\seed_demo_flujo.py --force --base-url http://127.0.0.1:5012
```

Solo APIs (sin flujo):
```powershell
python scripts\seed_demo_apis.py --base-url https://novadata-projects-production.up.railway.app
```

Crea/actualiza:
- APIs **Demo Motor Credito** y **Demo Buro Reporte**
- Datos: Salario, Asalariado, Tiempo laborando, outputs buró/motor
- Grupo **Demo Operaciones** (admin vinculado)
- Flujo **Demo Originacion TDC**
- Clientes: `001-1234567-8` (OK), `002-9876543-2` (ALERTA), `003-4567890-1` (RIESGO)

---

## Flujo BPM sembrado

1. **Captura** — Salario, Asalariado, Tiempo laborando (meses) → transición a buró
2. **Consulta Buró** — estado *Consultando* + API `Demo Buro Reporte`
   - Inputs: cedula ← `cliente_identificacion`
   - Outputs → Score Buró, Mora, EIC, Dictamen Buró, …
   - Reglas AUTO: DictamenBuro OK|ALERTA|RIESGO → Evaluación
3. **Evaluación** — estado *Ejecutando motor* + API `Demo Motor Credito`
   - Inputs: salario / asalariado / tiempo ← datos; cedula ← caso
   - Reglas AUTO:
     - `Dictamen = APROBADA` → **Aprobación**
     - `Dictamen = REFERIDA` → **Comité / Referimiento**
     - `Dictamen = DECLINADA` → **Declinada**
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
2. Flujos → abrir **Demo Originacion TDC**
3. Nuevo caso con cliente `001-1234567-8` → Captura (ej. salario 45000, asalariado sí, 24 meses)
4. Avanzar a buró (API + outputs) → motor → rama APROBADA / REFERIDA / DECLINADA
5. Con `003-4567890-1` el buró sale RIESGO (sigue a evaluación; el dictamen final lo define el motor)

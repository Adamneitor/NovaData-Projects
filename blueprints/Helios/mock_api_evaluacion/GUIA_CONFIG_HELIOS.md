# Guía de configuración — APIs demo Helios

## URLs

| Ambiente | Motor | Buró |
|----------|-------|------|
| Railway (NOVA) | `https://novadata-projects-production.up.railway.app/demo-api/evaluacion` | `.../demo-api/buro/reporte` |
| Local Flask | `http://127.0.0.1:5012/demo-api/evaluacion` | `.../demo-api/buro/reporte` |
| Mock uvicorn | `http://127.0.0.1:3000/api/evaluacion` | `http://127.0.0.1:3000/api/buro/reporte` |

Headers:
```json
{"Authorization":"Bearer test-token-123","Content-Type":"application/json"}
```

## Motor — Dictamen

Valores: **`APROBADA`** | **`REFERIDA`** | **`DECLINADA`**

Body:
```json
{"salario":45000,"es_asalariado":true,"tiempo_laborando":24,"cedula":"00112345678"}
```

Outputs: `Dictamen`, `Monto_DOP`, `Monto_USD`, `Razon`

## Buró — Reporte

Body: `{"cedula":"00112345678"}`

Outputs: `Score`, `ChanceFavor`, `EicMax`, `MoraMaxDias`, `DictamenBuro`, `Resumen`, `CuentasAbiertas`

DictamenBuro: `OK` | `ALERTA` | `RIESGO`

## Seed automático

```powershell
cd blueprints\Helios
python scripts\seed_demo_apis.py --base-url https://novadata-projects-production.up.railway.app
```

Detalle del flujo: `DEMO_PRESENTACION.md`

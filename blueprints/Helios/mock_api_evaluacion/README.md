# API Mock — Evaluación Crediticia

API de prueba independiente de Helios. Autenticación Bearer + respuestas aleatorias.

## Arranque rápido

```bash
cd mock_api_evaluacion
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 3000 --reload
```

- Health: http://127.0.0.1:3000/health  
- Docs Swagger: http://127.0.0.1:3000/docs  
- Endpoint: `POST http://127.0.0.1:3000/api/evaluacion`

## Token

```
Authorization: Bearer test-token-123
```

## Prueba con curl

```bash
curl -X POST http://127.0.0.1:3000/api/evaluacion ^
  -H "Authorization: Bearer test-token-123" ^
  -H "Content-Type: application/json" ^
  -d "{\"salario\":45000,\"es_asalariado\":true,\"tiempo_laborando\":24,\"cedula\":\"00112345678\"}"
```

Ver `GUIA_CONFIG_HELIOS.md` para configurar el API manualmente en Helios.

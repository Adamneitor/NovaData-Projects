# Guía de configuración manual en Helios

Este documento describe **cómo configurar** el API mock en Helios.  
**No está preconfigurado** en el sistema: usted debe crearlo en Catálogo → APIs y mapearlo en el flujo.

---

## 1. URL base del API

| Ambiente | URL |
|----------|-----|
| Local (recomendado) | `http://127.0.0.1:3000/api/evaluacion` |
| Alternativa | `http://localhost:3000/api/evaluacion` |

Health check (sin auth): `http://127.0.0.1:3000/health`

---

## 2. Headers necesarios

| Header | Valor |
|--------|-------|
| `Authorization` | `Bearer test-token-123` |
| `Content-Type` | `application/json` |

En Helios (detalle del API → Headers JSON), use algo como:

```json
{
  "Authorization": "Bearer test-token-123",
  "Content-Type": "application/json"
}
```

> El token de prueba es fijo: `test-token-123`. Sin este header el API responde **401**.

---

## 3. Método HTTP

**POST**

---

## 4. Request body (estructura exacta)

```json
{
  "salario": 45000,
  "es_asalariado": true,
  "tiempo_laborando": 24,
  "cedula": "00112345678"
}
```

### Campos (Inputs)

| Campo API | Tipo | Descripción | Origen sugerido en Helios |
|-----------|------|-------------|---------------------------|
| `salario` | float | Ingreso mensual | Dato adicional (ej. Salario) |
| `es_asalariado` | boolean | Si es asalariado | Dato adicional (ej. Asalariado) → `true`/`false` o Sí/No |
| `tiempo_laborando` | number | Meses laborando | Dato adicional |
| `cedula` | string | Documento | Cliente → Identificación (`cliente_identificacion`) |

> Ubicación de cada parámetro en Helios: **body**.

---

## 5. Response (estructura exacta)

Cada llamada genera valores **distintos**:

```json
{
  "Monto_DOP": 120000.5,
  "Monto_USD": 2086.96,
  "Dictamen": "APROBADO",
  "Razon": "Perfil estable con ingresos consistentes"
}
```

### Campos (Outputs) — para mapear en Helios

| Nombre output | JsonPath | Formato | Destino sugerido |
|---------------|----------|--------|------------------|
| `Monto_DOP` | `Monto_DOP` | número | Dato adicional (moneda/número) |
| `Monto_USD` | `Monto_USD` | número | Dato adicional (moneda/número) |
| `Dictamen` | `Dictamen` | texto | Dato adicional (texto) |
| `Razon` | `Razon` | texto | Dato adicional (texto) |

Valores posibles de `Dictamen`: `APROBADO` | `RECHAZADO`.

---

## 6. Checklist de configuración en Helios

### A) Catálogo → APIs → Crear

| Campo | Valor |
|-------|-------|
| Nombre | `Mock Evaluación Crediticia` |
| Método | `POST` |
| URL | `http://127.0.0.1:3000/api/evaluacion` |
| Headers | JSON con `Authorization` y `Content-Type` (ver §2) |
| Timeout | `30` |

### B) Parámetros (Inputs)

| Nombre | Ubicación | Origen | Valor / campo |
|--------|-----------|--------|---------------|
| `salario` | body | Dato compl. | → su dato Salario |
| `es_asalariado` | body | Dato compl. | → su dato Asalariado |
| `tiempo_laborando` | body | Dato compl. | → su dato Tiempo laborando |
| `cedula` | body | Campo del caso | `cliente_identificacion` |

### C) Outputs (Response)

| Nombre | Ruta JSON | Formato |
|--------|-----------|---------|
| `Monto_DOP` | `Monto_DOP` | número |
| `Monto_USD` | `Monto_USD` | número |
| `Dictamen` | `Dictamen` | texto |
| `Razon` | `Razon` | texto |

### D) Editor de flujo → Estado

1. Asocie el API al estado.
2. En **Inputs (Request Mapping)** confirme orígenes (dato / cliente / fijo).
3. En **Outputs (Response Mapping)** asigne cada output a un dato adicional.
4. (Opcional) Reglas API: ej. `Dictamen = APROBADO` → estado Aprobado; `Dictamen = RECHAZADO` → estado Rechazo.
5. Guarde el flujo.

### E) Probar

1. Arranque el mock: `uvicorn main:app --host 127.0.0.1 --port 3000`
2. En Helios → API → **Test API** (indique un Id de caso), o avance un caso hasta el estado con el API.
3. Verifique montos/dictamen en datos adicionales (campos de solo lectura si están mapeados como output).

---

## 7. Errores esperados del mock

| HTTP | Causa |
|------|--------|
| 401 | Falta o token incorrecto |
| 422 | Body inválido (campos faltantes o tipos incorrectos) |
| 200 | Evaluación OK (dictamen aleatorio) |

---

## 8. Ejemplo curl (Windows PowerShell)

```powershell
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:3000/api/evaluacion" `
  -Headers @{ Authorization = "Bearer test-token-123" } `
  -ContentType "application/json" `
  -Body '{"salario":45000,"es_asalariado":true,"tiempo_laborando":24,"cedula":"00112345678"}'
```

Ejecute dos veces: verá `Monto_DOP` / `Dictamen` / `Razon` diferentes.

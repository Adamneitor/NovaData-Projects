# Guía — Demo Helios multi-rol

## Usuarios demo (login NOVA / Helios)

| Usuario | Contraseña | Rol | Qué ve en Casos |
|---------|------------|-----|-----------------|
| `admin` | `admin` | Super (todos los grupos) | Toda la bandeja |
| `ejecutivo` | `demo123` | Ejecutivo de Servicio | Captura + Documentación |
| `analista` | `demo123` | Analista de Crédito | Buró + Evaluación Motor (+ Declinada) |
| `gerente` | `demo123` | Gerente Análisis de Crédito | Aprobación Gerente (+ Comité) |
| `comite` | `demo123` | Comité de Crédito | Referimiento / Comité |
| `operaciones` | `demo123` | Operaciones Cierre | Formalización |

### Casos demo sugeridos por rol
- Ejecutivo → caso Ana (Captura)
- Analista → caso Carlos (Consulta Buró) — Ejecutar API
- Gerente → caso Laura (Aprobación Gerente)
- Comité → caso José (Comité)
- Operaciones → caso Patricia (Formalización)
- Declinada (Ricardo) → visible a analista/gerente

Salir de sesión y entrar con cada usuario en `/login`.

# Salud del servicio

Rutas públicas (sin token) para orquestadores y balanceadores. No llevan el prefijo `/api/v1` y no
exponen datos internos.

## GET `/health/live` — ¿El proceso está vivo?

No consulta dependencias.

```http
GET /health/live
```

```json
{ "status": "ok" }
```

Es la que usa el `healthcheck` del contenedor.

## GET `/health/ready` — ¿Puede atender solicitudes?

Comprueba la conexión con PostgreSQL.

| Situación | Respuesta |
| --- | --- |
| Base de datos disponible | `200 { "status": "ready" }` |
| Base de datos no disponible | `503 { "status": "not_ready" }` |

No revisa Party Identity: su caída solo afecta la asignación de fabricantes.

## Documentación interactiva

Con `SIO_DOCS_ENABLED=true` quedan públicas `/docs` (Swagger) y `/openapi.json`. Con `false` no
existen: responden `401`, porque cualquier ruta no declarada como pública exige token.

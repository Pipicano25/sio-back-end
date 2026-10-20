# Audit API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Audit guarda el **historial inmutable de lo que ocurre en SIO**: quién hizo qué, sobre qué entidad, cuándo y con qué resultado. Los demás microservicios le envían eventos; el frontend solo **consulta** ese historial, por empresa o de plataforma, para pantallas de trazabilidad y soporte.

## Responsabilidad

- Recibir eventos de auditoría desde los microservicios (cuentas de servicio) de forma idempotente, individualmente o por lotes.
- Conservar los eventos con los valores anteriores y nuevos, ya **redactados**: los valores de claves sensibles (contraseñas, tokens…) se reemplazan por `"***"` y la lista de rutas ocultadas queda en `redacted_paths`.
- Exponer consultas por empresa (con aislamiento multi-tenant) y de plataforma (eventos sin empresa), incluido el historial cronológico de una entidad.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-audit-dev.onrender.com/api/v1` |
| Salud | `https://sio-audit-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-audit-dev.onrender.com/docs) · [/openapi.json](https://sio-audit-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `AUDIT.*` y `trace_id` ([Errores](../guias/errores.md)) |
| Operaciones en el contrato desplegado | 10 (8 de negocio + 2 de salud) |
| Verificación | Contrato OpenAPI de Render del 2026-10-19 cruzado con el código del servicio (`services/audit-service`) |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>` ([Autenticación](../guias/autenticacion.md)).

| Permiso | Operaciones | Quién lo tiene en la plantilla del realm |
|---|---|---|
| `perm:audit:audit-events:create` | Registrar eventos (una y por lote) | Solo cuentas de servicio técnicas de los microservicios. Ningún grupo de usuarios lo tiene salvo `administradores` vía `perm:all:all:all`, pero además la ruta exige que el token sea de una **cuenta de servicio** (ver más abajo) |
| `perm:audit:audit-events:read` | Consultas de una empresa | `administradores` (`perm:all:all:all`), `supervisores` (`perm:all:all:read`) |
| `perm:audit:platform-events:read` | Consultas de plataforma | `administradores`, `supervisores` |

Los grupos `compras`, `ventas`, `inventario`, `reportes` y `consulta` **no** tienen permisos de Audit en la plantilla: sus usuarios reciben `403` en todas las consultas.

**Restricción de las rutas de registro:** además del permiso, el token debe pertenecer a una cuenta de servicio de Keycloak. El código comprueba que el token tenga el claim `client_id` y que `preferred_username` sea exactamente `service-account-<client_id>`. Un token de usuario (`sio-web`) recibe `403 AUDIT.FORBIDDEN` aunque tuviera el permiso. El frontend **no debe** registrar eventos: los generan los propios microservicios.

## Alcance de datos

| Alcance | Rutas | Regla |
|---|---|---|
| Empresa | `/companies/{company_id}/…` | El servicio consulta a Operational Context, con el token del usuario, si tiene membresía `ACTIVE` en la empresa. Si no, `404 AUDIT.NOT_FOUND` (igual que si la empresa no existiera). Nunca devuelve eventos de plataforma |
| Plataforma | `/platform-audit-events…`, `/platform-entity-history/…` | Solo eventos con `company_id` nulo. No consulta Operational Context; basta el permiso |

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Proceso y base de datos listos | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `POST` | `/audit-events` | Registrar un evento | `perm:audit:audit-events:create` + cuenta de servicio | `WRITE` | [Ver](#3-post-audit-events) |
| 4 | `POST` | `/audit-events/batch` | Registrar de 1 a 100 eventos (atómico) | `perm:audit:audit-events:create` + cuenta de servicio | `WRITE` | [Ver](#4-post-audit-eventsbatch) |
| 5 | `GET` | `/companies/{company_id}/audit-events` | Listar eventos de una empresa | `perm:audit:audit-events:read` | `READ` | [Ver](#5-get-companiescompany_idaudit-events) |
| 6 | `GET` | `/companies/{company_id}/audit-events/{audit_id}` | Obtener un evento de una empresa | `perm:audit:audit-events:read` | `READ` | [Ver](#6-get-companiescompany_idaudit-eventsaudit_id) |
| 7 | `GET` | `/companies/{company_id}/entity-history/{entity_type}/{entity_id}` | Historial cronológico de una entidad de la empresa | `perm:audit:audit-events:read` | `READ` | [Ver](#7-get-companiescompany_identity-historyentity_typeentity_id) |
| 8 | `GET` | `/platform-audit-events` | Listar eventos de plataforma | `perm:audit:platform-events:read` | `READ` | [Ver](#8-get-platform-audit-events) |
| 9 | `GET` | `/platform-audit-events/{audit_id}` | Obtener un evento de plataforma | `perm:audit:platform-events:read` | `READ` | [Ver](#9-get-platform-audit-eventsaudit_id) |
| 10 | `GET` | `/platform-entity-history/{entity_type}/{entity_id}` | Historial cronológico de una entidad de plataforma | `perm:audit:platform-events:read` | `READ` | [Ver](#10-get-platform-entity-historyentity_typeentity_id) |

## El objeto evento (`AuditEventResponse`)

Todas las consultas devuelven este objeto, solo o dentro de `items[]`:

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | Identificador interno asignado por Audit (`audit_id` en las rutas) |
| `event_id` | UUID | Identificador del evento asignado por el servicio emisor; clave de idempotencia |
| `company_id` | UUID \| null | Empresa del evento; `null` en eventos de plataforma |
| `branch_id` | UUID \| null | Sucursal, si aplica |
| `application_user_id` | UUID \| null | Usuario de aplicación que actuó |
| `keycloak_user_id` | UUID \| null | `sub` del token del actor |
| `username_snapshot` | string \| null | Nombre de usuario en el momento del evento (máx. 160) |
| `action` | string | Acción en mayúsculas, patrón `^[A-Z][A-Z0-9_]{0,49}$` (por ejemplo `CREATE`, `CONFIRM_SALE`) |
| `entity_type` | string | Entidad en PascalCase, patrón `^[A-Z][A-Za-z0-9]{0,59}$` (por ejemplo `Sale`, `CompanyProduct`) |
| `entity_id` | UUID \| null | Identificador de la entidad afectada |
| `previous_values` | object \| null | Valores antes del cambio, ya redactados |
| `new_values` | object \| null | Valores después del cambio, ya redactados |
| `redacted_paths` | array<string> | Rutas de `previous_values`/`new_values` cuyo valor se reemplazó por `"***"` |
| `result` | `"SUCCESS"` \| `"FAILURE"` | Resultado de la acción |
| `reason` | string \| null | Motivo (máx. 2000), típico en fallos y anulaciones |
| `request_id`, `correlation_id` | UUID \| null | Identificadores de trazabilidad del emisor |
| `source_service` | string | `client_id` de la cuenta de servicio emisora (lo fija Audit) |
| `occurred_at` | date-time | Cuándo ocurrió, según el emisor (con zona horaria) |
| `recorded_at` | date-time | Cuándo lo guardó Audit |
| `created_by` | string | `sub` de la cuenta de servicio emisora |

Los valores concretos de `action` y `entity_type` los define cada servicio emisor; Audit solo valida el formato. El catálogo de valores que emiten hoy los servicios (verificado en el código de cada uno) está en [Administración empresarial §16](../principales/administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría): por ejemplo Sales emite `CREATE_SALE`, `CONFIRM_SALE`, `CANCEL_SALE` sobre `Sale`, Purchase emite `CONFIRM_PURCHASE`, `RECEIVE_PURCHASE`, `CANCEL_PURCHASE` sobre `Purchase`, y Commercial Relationship `ADOPT_COMPANY_PRODUCT`, `CHANGE_PRICE_LIST_ITEM_PRICE`, etc. Las acciones siguen el patrón `VERBO_ENTIDAD` en mayúsculas.

## Operaciones

### 1. `GET /health/live`

| | |
|---|---|
| Clasificación | `READ` · sin autenticación |
| URL | `https://sio-audit-dev.onrender.com/health/live` |
| Respuesta | `200` `{"status": "ok"}` |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

| | |
|---|---|
| Clasificación | `READ` · sin autenticación |
| URL | `https://sio-audit-dev.onrender.com/health/ready` |
| Respuestas | `200` `{"status": "ok"}` cuando la base de datos responde; `503` `{"detail": "..."}` si no |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/health/ready'
```

### 3. `POST /audit-events`

| | |
|---|---|
| Clasificación | `WRITE` (crea un registro de auditoría inmutable) |
| URL | `https://sio-audit-dev.onrender.com/api/v1/audit-events` |
| Permiso | `perm:audit:audit-events:create` **y** token de cuenta de servicio |
| Alcance | Empresa (`company_id` informado) o plataforma (`company_id` nulo), según el evento |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

**Para el frontend:** no usar. Un token de usuario recibe `403 AUDIT.FORBIDDEN`. Se documenta porque forma parte del contrato y para interpretar los eventos que luego se consultan.

Cuerpo (`AuditEventIn`; rechaza campos adicionales con `422`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `event_id` | UUID | Sí | Único por emisor; clave de idempotencia |
| `company_id` | UUID \| null | No | — |
| `branch_id` | UUID \| null | No | — |
| `application_user_id` | UUID \| null | No | — |
| `keycloak_user_id` | UUID \| null | No | — |
| `username_snapshot` | string \| null | No | máx. 160 caracteres |
| `action` | string | Sí | `^[A-Z][A-Z0-9_]{0,49}$` |
| `entity_type` | string | Sí | `^[A-Z][A-Za-z0-9]{0,59}$` |
| `entity_id` | UUID \| null | No | — |
| `previous_values` | object \| null | No | Hasta 64 KiB serializado; profundidad limitada |
| `new_values` | object \| null | No | Ídem |
| `redacted_paths` | array<string> | No (por defecto `[]`) | Sin rutas repetidas |
| `result` | string | Sí | `SUCCESS` o `FAILURE` |
| `reason` | string \| null | No | máx. 2000 caracteres |
| `request_id`, `correlation_id` | UUID \| null | No | — |
| `occurred_at` | date-time | Sí | Con zona horaria; no puede estar más de 300 s en el futuro |

Ejemplo de solicitud (valores ilustrativos):

```json
{
  "event_id": "1e2d3c4b-5a69-4788-9a0b-1c2d3e4f5a6b",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "username_snapshot": "ventas.test",
  "action": "CONFIRM_SALE",
  "entity_type": "Sale",
  "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "previous_values": {"status": "DRAFT"},
  "new_values": {"status": "CONFIRMED", "number": "V-000123"},
  "redacted_paths": [],
  "result": "SUCCESS",
  "reason": null,
  "request_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
  "correlation_id": null,
  "occurred_at": "2026-10-19T15:04:05Z"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-audit-dev.onrender.com/api/v1/audit-events' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "1e2d3c4b-5a69-4788-9a0b-1c2d3e4f5a6b",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "username_snapshot": "ventas.test",
    "action": "CONFIRM_SALE",
    "entity_type": "Sale",
    "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
    "previous_values": {
      "status": "DRAFT"
    },
    "new_values": {
      "status": "CONFIRMED",
      "number": "V-000123"
    },
    "redacted_paths": [],
    "result": "SUCCESS",
    "reason": null,
    "request_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
    "correlation_id": null,
    "occurred_at": "2026-10-19T15:04:05Z"
  }'
```

Respuestas:

| HTTP | Significado |
|---|---|
| `201` | Evento guardado; cuerpo `AuditEventResponse` con `id`, `source_service`, `recorded_at` y `created_by` fijados por Audit |
| `200` | Ya existía un evento con el mismo `event_id`, el mismo emisor y el mismo contenido (idempotente); sin cuerpo según el contrato |
| `400 AUDIT.MALFORMED_BODY` | El cuerpo no es JSON |
| `403 AUDIT.FORBIDDEN` | Sin permiso o el token no es de cuenta de servicio |
| `409 AUDIT.EVENT_ID_CONFLICT` | `event_id` existente con contenido o emisor distinto |
| `422 AUDIT.VALIDATION_ERROR` | Formato inválido; `errors[]` indica el campo |
| `503 AUDIT.DEPENDENCY_UNAVAILABLE` | `dependency`: `database` |

Reglas y efectos: Audit vuelve a aplicar la redacción de claves sensibles antes de guardar (defensa en profundidad); `source_service` y `created_by` salen siempre del token, nunca del cuerpo. El registro es inmutable: no hay operaciones de modificación ni borrado.

### 4. `POST /audit-events/batch`

| | |
|---|---|
| Clasificación | `WRITE` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/audit-events/batch` |
| Permiso | `perm:audit:audit-events:create` **y** token de cuenta de servicio |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`AuditEventBatchIn`; rechaza campos adicionales): `{"events": [AuditEventIn, …]}` con **1 a 100** eventos, cada uno con las reglas de la operación 3.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-audit-dev.onrender.com/api/v1/audit-events/batch' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "events": [
      {
        "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
        "company_id": "550e8400-e29b-41d4-a716-446655440000",
        "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
        "username_snapshot": "ventas.test",
        "action": "CONFIRM_SALE",
        "entity_type": "Sale",
        "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
        "previous_values": {
          "status": "DRAFT"
        },
        "new_values": {
          "status": "CONFIRMED",
          "number": "V-000123"
        },
        "result": "SUCCESS",
        "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
        "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
        "occurred_at": "2026-10-19T15:04:05Z"
      }
    ]
  }'
```

Respuesta `200` (`AuditEventBatchResponse`):

```json
{
  "items": [
    {"index": 0, "event_id": "1e2d3c4b-5a69-4788-9a0b-1c2d3e4f5a6b", "id": "5c6d7e8f-9a0b-4c1d-8e2f-3a4b5c6d7e8f", "outcome": "CREATED"},
    {"index": 1, "event_id": "2e3d4c5b-6a79-4899-9b1c-2d3e4f5a6b7c", "id": "6d7e8f9a-0b1c-4d2e-8f3a-4b5c6d7e8f9a", "outcome": "ALREADY_EXISTS"}
  ]
}
```

| HTTP | Significado |
|---|---|
| `200` | Lote procesado; `outcome` por evento: `CREATED` o `ALREADY_EXISTS` (mismo contenido) |
| `409 AUDIT.EVENT_ID_CONFLICT` | Algún `event_id` existía con otro contenido o emisor. Extensión `conflicts: [{"index", "event_id"}]`. **No se guarda ningún evento del lote** |
| `422 AUDIT.VALIDATION_ERROR` | Algún evento inválido; no se guarda ninguno |
| `400`, `401`, `403`, `503` | Como en la operación 3 |

El lote es **atómico**: o se guardan todos los eventos nuevos o ninguno.

### 5. `GET /companies/{company_id}/audit-events`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events` |
| Permiso | `perm:audit:audit-events:read` |
| Alcance | Empresa (membresía `ACTIVE` evaluada en Operational Context) |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación / valores | Cómo obtenerlo |
|---|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | — | [company_id](../parametros/company-id.md) |
| `page` | query | integer | No | ≥ 1, por defecto 1 | — |
| `page_size` | query | integer | No | 1–100, por defecto 20 | — |
| `occurred_at_from` | query | date-time | No | **Con zona horaria**; ≤ `occurred_at_to` | — |
| `occurred_at_to` | query | date-time | No | Con zona horaria | — |
| `result` | query | `SUCCESS` \| `FAILURE` | No | — | — |
| `action` | query | string | No | Igualdad exacta | Valor de `action` de eventos previos |
| `entity_type` | query | string | No | Igualdad exacta | Valor de `entity_type` de eventos previos |
| `entity_id` | query | UUID | No | — | `id` del recurso en su servicio (venta, compra, producto…) |
| `source_service` | query | string | No | `client_id` emisor (por ejemplo `sales-service`) | — |
| `keycloak_user_id` | query | UUID | No | — | `sub` del token o `keycloak_user_id` de `/me/operational-context` |
| `application_user_id` | query | UUID | No | — | `memberships[].application_user_id` de `/me/operational-context` |
| `event_id`, `correlation_id`, `request_id` | query | UUID | No | — | De eventos previos o de las cabeceras de trazabilidad |
| `branch_id` | query | UUID | No | — | [branch_id](../parametros/branch-id.md) |

Ejemplo:

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events?entity_type=Sale&result=SUCCESS&occurred_at_from=2026-10-01T00:00:00Z&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`AuditEventPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "5c6d7e8f-9a0b-4c1d-8e2f-3a4b5c6d7e8f",
      "event_id": "1e2d3c4b-5a69-4788-9a0b-1c2d3e4f5a6b",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "username_snapshot": "ventas.test",
      "action": "CONFIRM_SALE",
      "entity_type": "Sale",
      "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "previous_values": {"status": "DRAFT"},
      "new_values": {"status": "CONFIRMED", "number": "V-000123"},
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
      "correlation_id": null,
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:04:05Z",
      "recorded_at": "2026-10-19T15:04:06Z",
      "created_by": "8a7b6c5d-4e3f-4a2b-9c1d-0e9f8a7b6c5d"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Errores: `403 AUDIT.FORBIDDEN` (sin permiso), `403 AUDIT.OPERATIONAL_ACCESS_DENIED` (Operational Context respondió `403` al evaluar la membresía; suele faltar `perm:operational-context:application_users:read`), `404 AUDIT.NOT_FOUND` (sin membresía `ACTIVE` o empresa inexistente), `422` (fecha sin zona horaria, rango invertido, `page_size` fuera de rango), `503 AUDIT.DEPENDENCY_UNAVAILABLE` (`dependency`: `database` u `operational-context`).

Reglas: la membresía se evalúa en **cada solicitud**, sin caché. Los filtros nunca amplían el alcance: solo se devuelven eventos con ese `company_id`. Orden de la lista: `occurred_at` descendente y, a igualdad, `id` descendente (del más reciente al más antiguo; verificado en el repositorio del servicio). El historial de entidad (operación 7) es ascendente.

Dependencias: Operational Context (`GET /operational-access?company_id=`, con el token del usuario).

### 6. `GET /companies/{company_id}/audit-events/{audit_id}`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events/{audit_id}` |
| Permiso | `perm:audit:audit-events:read` |
| Alcance | Empresa |

| Nombre | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | [company_id](../parametros/company-id.md) |
| `audit_id` | ruta | UUID | Sí | Campo `id` de un elemento de la operación 5 o 7 (no confundir con `event_id`) |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events/8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: un `AuditEventResponse` (mismo objeto que en `items[]` de la operación 5). Errores: `404 AUDIT.NOT_FOUND` si el evento no existe, pertenece a otra empresa, es de plataforma o el usuario no tiene membresía; `403` y `503` como en la operación 5.

Ejemplo de respuesta `200` (`AuditEventResponse`; valores ilustrativos):

```json
{
  "id": "8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9",
  "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "username_snapshot": "ventas.test",
  "action": "CONFIRM_SALE",
  "entity_type": "Sale",
  "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "previous_values": {
    "status": "DRAFT"
  },
  "new_values": {
    "status": "CONFIRMED",
    "number": "V-000123"
  },
  "redacted_paths": [],
  "result": "SUCCESS",
  "reason": null,
  "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "source_service": "sales-service",
  "occurred_at": "2026-10-19T15:04:05Z",
  "recorded_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 7. `GET /companies/{company_id}/entity-history/{entity_type}/{entity_id}`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}` |
| Permiso | `perm:audit:audit-events:read` |
| Alcance | Empresa |

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | — | [company_id](../parametros/company-id.md) |
| `entity_type` | ruta | string | Sí | `^[A-Z][A-Za-z0-9]{0,59}$` (PascalCase) | `entity_type` de los eventos; coincide con la entidad del servicio emisor (por ejemplo `Sale`) |
| `entity_id` | ruta | UUID | Sí | — | `id` del recurso en su servicio |
| `page`, `page_size` | query | integer | No | 1–100, por defecto 20 | — |
| `occurred_at_from`, `occurred_at_to` | query | date-time | No | Con zona horaria; `from` ≤ `to` | — |
| `result` | query | `SUCCESS` \| `FAILURE` | No | — | — |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/entity-history/Sale/dffc4713-b6bf-426d-80d3-e2805bc742fd?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: `AuditEventPage` con los eventos de esa entidad en **orden cronológico ascendente**. Útil para la línea de tiempo de una venta, compra o producto. Errores como en la operación 5.

Ejemplo de respuesta `200` (`AuditEventPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "username_snapshot": "ventas.test",
      "action": "CONFIRM_SALE",
      "entity_type": "Sale",
      "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "previous_values": {
        "status": "DRAFT"
      },
      "new_values": {
        "status": "CONFIRMED",
        "number": "V-000123"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:04:05Z",
      "recorded_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 8. `GET /platform-audit-events`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/platform-audit-events` |
| Permiso | `perm:audit:platform-events:read` |
| Alcance | Plataforma: solo eventos con `company_id` nulo (por ejemplo cambios en catálogos globales) |

Parámetros de consulta: los mismos de la operación 5 **excepto** `branch_id`: `page`, `page_size`, `occurred_at_from`, `occurred_at_to`, `result`, `action`, `entity_type`, `entity_id`, `source_service`, `keycloak_user_id`, `application_user_id`, `event_id`, `correlation_id`, `request_id`.

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/platform-audit-events?entity_type=GlobalCountry&page_size=50' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: `AuditEventPage` (los elementos traen `company_id: null`). Errores: `403 AUDIT.FORBIDDEN`, `422`, `503` (`dependency`: `database`). No consulta Operational Context.

Ejemplo de respuesta `200` (`AuditEventPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "username_snapshot": "ventas.test",
      "action": "CONFIRM_SALE",
      "entity_type": "Sale",
      "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "previous_values": {
        "status": "DRAFT"
      },
      "new_values": {
        "status": "CONFIRMED",
        "number": "V-000123"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:04:05Z",
      "recorded_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 9. `GET /platform-audit-events/{audit_id}`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/platform-audit-events/{audit_id}` |
| Permiso | `perm:audit:platform-events:read` |
| Parámetro | `audit_id` (ruta, UUID): campo `id` de un elemento de la operación 8 o 10 |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/platform-audit-events/8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: `AuditEventResponse`. `404 AUDIT.NOT_FOUND` si no existe o pertenece a una empresa (no es de plataforma).

Ejemplo de respuesta `200` (`AuditEventResponse`; valores ilustrativos):

```json
{
  "id": "8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9",
  "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "username_snapshot": "ventas.test",
  "action": "CONFIRM_SALE",
  "entity_type": "Sale",
  "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "previous_values": {
    "status": "DRAFT"
  },
  "new_values": {
    "status": "CONFIRMED",
    "number": "V-000123"
  },
  "redacted_paths": [],
  "result": "SUCCESS",
  "reason": null,
  "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "source_service": "sales-service",
  "occurred_at": "2026-10-19T15:04:05Z",
  "recorded_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 10. `GET /platform-entity-history/{entity_type}/{entity_id}`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-audit-dev.onrender.com/api/v1/platform-entity-history/{entity_type}/{entity_id}` |
| Permiso | `perm:audit:platform-events:read` |
| Parámetros | `entity_type` (ruta, PascalCase `^[A-Z][A-Za-z0-9]{0,59}$`), `entity_id` (ruta, UUID), `page`, `page_size`, `occurred_at_from`, `occurred_at_to`, `result` (query, como en la operación 7) |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-audit-dev.onrender.com/api/v1/platform-entity-history/Sale/dffc4713-b6bf-426d-80d3-e2805bc742fd?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: `AuditEventPage` en orden cronológico ascendente, solo eventos de plataforma. Errores: `403`, `422`, `503`.

Ejemplo de respuesta `200` (`AuditEventPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "event_id": "4437cfac-a07f-4bc3-87b3-6b521305be41",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "username_snapshot": "ventas.test",
      "action": "CONFIRM_SALE",
      "entity_type": "Sale",
      "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "previous_values": {
        "status": "DRAFT"
      },
      "new_values": {
        "status": "CONFIRMED",
        "number": "V-000123"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:04:05Z",
      "recorded_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 AUDIT.FORBIDDEN` en consultas | El grupo del usuario no tiene permisos de Audit (solo administradores y supervisores en la plantilla) | Ocultar el módulo de auditoría a los demás perfiles |
| `403 AUDIT.FORBIDDEN` al registrar | Token de usuario en una ruta reservada a cuentas de servicio | No registrar eventos desde el frontend |
| `403 AUDIT.OPERATIONAL_ACCESS_DENIED` | El token no cubre `perm:operational-context:application_users:read` | Revisar permisos del grupo |
| `404 AUDIT.NOT_FOUND` | Empresa sin membresía, evento de otra empresa o de plataforma, `audit_id` inexistente | Verificar `company_id` en `/me/operational-context` y usar `id` (no `event_id`) |
| `422` con `occurred_at_from` | Fecha sin zona horaria o posterior a `occurred_at_to` | Enviar ISO 8601 con `Z` u offset |
| `503` con `dependency: operational-context` | Operational Context no respondió | Reintentar más tarde |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Evalúa la membresía `ACTIVE` del usuario en las consultas por empresa (`GET /operational-access?company_id=`, con el token del usuario) |
| Microservicios emisores | Envían los eventos con sus cuentas de servicio (`source_service`) |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 10 |
| Operaciones documentadas | 10 |
| Permisos contrastados con el código | Sí (`audit_events.py`, `company_audit_events.py`, `platform_audit_events.py`) |
| Esquemas contrastados con los modelos Pydantic | Sí (`api/schemas/audit_event.py`, reglas de `sio_audit.event`) |
| Verificado | Orden de las listas de las operaciones 5 y 8: `occurred_at` desc, `id` desc; catálogo de `action`/`entity_type` por servicio emisor en [Administración empresarial §16](../principales/administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) |

# Payment Reference API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Payment Reference mantiene dos **catálogos globales** compartidos por todas las empresas: los **tipos de condición de pago** (contado, crédito a 30 días…) y los **métodos de pago** (efectivo, transferencia, tarjeta…). Las ventas y las compras referencian un método de pago; las condiciones de pago de clientes y proveedores en Commercial Relationship referencian un tipo de condición.

## Responsabilidad

- Exponer y administrar los dos catálogos globales con código único, estado `ACTIVE`/`INACTIVE` y trazabilidad de autor.
- No conoce empresas ni sucursales: sus datos son de alcance **global**.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-payment-reference-dev.onrender.com` (**sin** `/api/v1`) |
| Salud | `https://sio-payment-reference-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-payment-reference-dev.onrender.com/docs) · [/openapi.json](https://sio-payment-reference-dev.onrender.com/openapi.json) |
| Formato de error | **Básico** (`{"detail": ...}`); dos `409` añaden `code`. Sin `trace_id` ni `X-Trace-Id` ([Errores §1.2](../guias/errores.md#12-formato-básico-geography-y-payment-reference)) |
| Operaciones en el contrato desplegado | 12 (10 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/payment-reference-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`.

| Permiso | Operaciones | Grupos de la plantilla que lo tienen |
|---|---|---|
| `perm:payment-reference:global_payment_condition_types:read` | Listar y consultar tipos de condición | `administradores`, `supervisores`, `compras` y `ventas` (vía `perm:payment-reference:all:read`), `reportes`, `consulta` |
| `perm:payment-reference:global_payment_condition_types:create` | Crear tipo de condición | `administradores`, `supervisores` (`perm:all:all:create`) |
| `perm:payment-reference:global_payment_condition_types:update` | Actualizar y reactivar tipo de condición | `administradores`, `supervisores` (`perm:all:all:update`) |
| `perm:payment-reference:global_payment_condition_types:delete` | Inactivar tipo de condición | `administradores` |
| `perm:payment-reference:global_payment_methods:read` | Listar y consultar métodos de pago | Igual que la lectura de tipos |
| `perm:payment-reference:global_payment_methods:create` | Crear método de pago | `administradores`, `supervisores` |
| `perm:payment-reference:global_payment_methods:update` | Actualizar método de pago | `administradores`, `supervisores` |

## Alcance de datos

Global. No hay aislamiento por empresa: cualquier usuario con el permiso de lectura ve los mismos registros. Las escrituras afectan a **todas las empresas** de la plataforma.

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` | Proceso y base de datos listos | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/global-payment-condition-types` | Listar tipos de condición de pago | `…global_payment_condition_types:read` | `READ` | [Ver](#3-get-global-payment-condition-types) |
| 4 | `POST` | `/global-payment-condition-types` | Crear tipo de condición | `…global_payment_condition_types:create` | `WRITE` | [Ver](#4-post-global-payment-condition-types) |
| 5 | `GET` | `/global-payment-condition-types/{condition_type_id}` | Consultar un tipo | `…global_payment_condition_types:read` | `READ` | [Ver](#5-get-global-payment-condition-typescondition_type_id) |
| 6 | `PUT` | `/global-payment-condition-types/{condition_type_id}` | Reemplazar un tipo (con versión) | `…global_payment_condition_types:update` | `WRITE` | [Ver](#6-put-global-payment-condition-typescondition_type_id) |
| 7 | `POST` | `/global-payment-condition-types/{condition_type_id}/deactivate` | Inactivar un tipo | `…global_payment_condition_types:delete` | `HIGH_RISK` | [Ver](#7-post-global-payment-condition-typescondition_type_iddeactivate) |
| 8 | `POST` | `/global-payment-condition-types/{condition_type_id}/reactivate` | Reactivar un tipo | `…global_payment_condition_types:update` | `WRITE` | [Ver](#8-post-global-payment-condition-typescondition_type_idreactivate) |
| 9 | `GET` | `/global-payment-methods` | Listar métodos de pago | `…global_payment_methods:read` | `READ` | [Ver](#9-get-global-payment-methods) |
| 10 | `POST` | `/global-payment-methods` | Crear método de pago | `…global_payment_methods:create` | `WRITE` | [Ver](#10-post-global-payment-methods) |
| 11 | `GET` | `/global-payment-methods/{payment_method_id}` | Consultar un método | `…global_payment_methods:read` | `READ` | [Ver](#11-get-global-payment-methodspayment_method_id) |
| 12 | `PUT` | `/global-payment-methods/{payment_method_id}` | Reemplazar un método (incluido `status`) | `…global_payment_methods:update` | `HIGH_RISK` | [Ver](#12-put-global-payment-methodspayment_method_id) |

Todos los permisos empiezan por `perm:payment-reference:`.

## Objetos

**`GlobalPaymentConditionTypeResponse`**

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | Identificador (`condition_type_id`); lo usan las condiciones de pago de Commercial Relationship (`payment_condition_type_id`) |
| `code` | string (≤ 30) | Código único |
| `name` | string (≤ 100) | Nombre |
| `description` | string \| null | Descripción |
| `status` | `ACTIVE` \| `INACTIVE` | Estado de uso |
| `version` | integer | Versión para control de concurrencia; obligatoria en `PUT`, `deactivate` y `reactivate` |
| `created_by`, `updated_by` | string | `sub` del usuario autor |
| `created_at`, `updated_at` | date-time | Marcas de tiempo |

**`GlobalPaymentMethodResponse`**

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | Identificador ([payment_method_id](../parametros/payment-method-id.md)) |
| `code` | string (≤ 40) | Código único |
| `name` | string (≤ 120) | Nombre |
| `method_type` | `CASH` \| `BANK` \| `CARD` \| `WALLET` \| `CHECK` \| `OTHER` | Tipo funcional |
| `requires_reference` | boolean | Si el pago exige una referencia externa |
| `status` | `ACTIVE` \| `INACTIVE` | Estado |
| `created_by`, `updated_by`, `created_at`, `updated_at` | — | Trazabilidad |

Los métodos de pago **no** tienen `version` ni operaciones de inactivación separadas: el estado se cambia con `PUT`.

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-payment-reference-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-payment-reference-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` `{"detail": "..."}` si la base de datos no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/health/ready'
```

### 3. `GET /global-payment-condition-types`

| | |
|---|---|
| Clasificación | `READ` · Alcance global |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types` |
| Permiso | `perm:payment-reference:global_payment_condition_types:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Valores |
|---|---|---|---|---|
| `page` | query | integer | No | ≥ 1, por defecto 1 |
| `page_size` | query | integer | No | 1–100, por defecto 20 |
| `search` | query | string | No | Busca por código, nombre o descripción |
| `status` | query | `ACTIVE` \| `INACTIVE` | No | Sin filtro devuelve ambos |

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types?status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PaginatedResponse[GlobalPaymentConditionTypeResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e7f8a9b0-c1d2-4e3f-8a4b-5c6d7e8f9a0b",
      "code": "CREDITO_30",
      "name": "Crédito a 30 días",
      "description": "Pago a 30 días calendario",
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z",
      "version": 1
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Errores: `401`, `403` (`{"detail": ...}`), `422` (formato FastAPI) por `page_size` fuera de rango.

### 4. `POST /global-payment-condition-types`

| | |
|---|---|
| Clasificación | `WRITE` · crea un registro del catálogo global visible para todas las empresas |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types` |
| Permiso | `perm:payment-reference:global_payment_condition_types:create` |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`GlobalPaymentConditionTypeCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 30 caracteres; **único** |
| `name` | string | Sí | ≤ 100 |
| `description` | string \| null | No | — |

```json
{
  "code": "CREDITO_60",
  "name": "Crédito a 60 días",
  "description": "Pago a 60 días calendario"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CREDITO_60",
    "name": "Crédito a 60 días",
    "description": "Pago a 60 días calendario"
  }'
```

Respuestas: `201` con el objeto creado (`status` `ACTIVE`, `version` 1); `409` `{"detail": "Ya existe un tipo de condición de pago con el código indicado."}`; `422` validación; `401`/`403`. Efectos: el nuevo tipo queda disponible de inmediato para las condiciones de pago de clientes y proveedores de cualquier empresa. `created_by` y `updated_by` se toman del `sub` del token.

### 5. `GET /global-payment-condition-types/{condition_type_id}`

`READ`. URL `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/{condition_type_id}`; permiso de lectura. `condition_type_id` (ruta, UUID) proviene del campo `id` de la operación 3. `200` con el objeto; `404` `{"detail": "..."}` si no existe.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/08fa0f04-b71b-43a4-8715-ae2d2961f889' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GlobalPaymentConditionTypeResponse`; valores ilustrativos):

```json
{
  "id": "08fa0f04-b71b-43a4-8715-ae2d2961f889",
  "code": "CASH",
  "name": "Contado",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "version": 1
}
```

### 6. `PUT /global-payment-condition-types/{condition_type_id}`

| | |
|---|---|
| Clasificación | `WRITE` · reemplazo completo de un registro global |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/{condition_type_id}` |
| Permiso | `perm:payment-reference:global_payment_condition_types:update` |

Cuerpo (`GlobalPaymentConditionTypeUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | La versión que el cliente leyó |
| `code` | string | Sí | ≤ 30; único |
| `name` | string | Sí | ≤ 100 |
| `description` | string \| null | No | — |

```json
{
  "version": 1,
  "code": "CREDITO_30",
  "name": "Crédito a 30 días calendario",
  "description": null
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X PUT 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/08fa0f04-b71b-43a4-8715-ae2d2961f889' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "code": "CREDITO_30",
    "name": "Crédito a 30 días calendario",
    "description": null
  }'
```

Reglas: reemplaza `code`, `name` y `description`; **no cambia `status`** (usar las operaciones 7 y 8). `created_by` y `created_at` no cambian; `updated_by`/`updated_at` se actualizan y `version` se incrementa. Respuestas: `200` con el objeto; `404`; `409` `{"detail": "El registro fue modificado por otra operación. Consulte nuevamente antes de modificarlo.", "code": "PAYMENT_REFERENCE.VERSION_CONFLICT"}` si la versión no coincide; `409` `{"detail": "Ya existe un tipo de condición de pago con el código indicado."}` por código duplicado; `422`.

### 7. `POST /global-payment-condition-types/{condition_type_id}/deactivate`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · inactiva un valor de catálogo usado por condiciones de pago de todas las empresas |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/{condition_type_id}/deactivate` |
| Permiso | `perm:payment-reference:global_payment_condition_types:delete` |

Cuerpo (`VersionRequest`): `{"version": 1}`. Respuestas: `200` con el objeto en `INACTIVE`; `404`; `409` `PAYMENT_REFERENCE.VERSION_CONFLICT`; `409` `{"detail": "...", "code": "PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION"}` si ya estaba `INACTIVE`; `422`.

Advertencia: no existe borrado físico. Un tipo inactivo deja de ser elegible para nuevas condiciones de pago en Commercial Relationship (`422 PAYMENT_CONDITION_TYPE_INACTIVE`); las condiciones existentes conservan la referencia. Confirmar con el usuario antes de enviar.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/08fa0f04-b71b-43a4-8715-ae2d2961f889/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

### 8. `POST /global-payment-condition-types/{condition_type_id}/reactivate`

`WRITE`. URL `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/{condition_type_id}/reactivate`; permiso `…update`. Cuerpo `{"version": 2}`. `200` con el objeto en `ACTIVE`; `404`; `409` versión o transición inválida (ya estaba `ACTIVE`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types/08fa0f04-b71b-43a4-8715-ae2d2961f889/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GlobalPaymentConditionTypeResponse`; valores ilustrativos):

```json
{
  "id": "08fa0f04-b71b-43a4-8715-ae2d2961f889",
  "code": "CASH",
  "name": "Contado",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "version": 1
}
```

### 9. `GET /global-payment-methods`

| | |
|---|---|
| Clasificación | `READ` · Alcance global |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-methods` |
| Permiso | `perm:payment-reference:global_payment_methods:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Valores |
|---|---|---|---|---|
| `page`, `page_size` | query | integer | No | 1–100, por defecto 20 |
| `search` | query | string | No | Código o nombre |
| `status` | query | `ACTIVE` \| `INACTIVE` | No | — |
| `method_type` | query | `CASH` \| `BANK` \| `CARD` \| `WALLET` \| `CHECK` \| `OTHER` | No | — |
| `requires_reference` | query | boolean | No | — |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/global-payment-methods?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: ver ejemplo completo en la guía [payment_method_id](../parametros/payment-method-id.md). Es la consulta que debe usar el frontend para poblar el selector de método de pago en ventas y compras (filtrar `status=ACTIVE`).

Ejemplo de respuesta `200` (`PaginatedResponse_GlobalPaymentMethodResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "code": "CASH",
      "name": "Efectivo",
      "method_type": "CASH",
      "requires_reference": false,
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 10. `POST /global-payment-methods`

| | |
|---|---|
| Clasificación | `WRITE` |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-methods` |
| Permiso | `perm:payment-reference:global_payment_methods:create` |

Cuerpo (`GlobalPaymentMethodCreate`):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `code` | string | Sí | ≤ 40; único |
| `name` | string | Sí | ≤ 120 |
| `method_type` | enum | Sí | `CASH`, `BANK`, `CARD`, `WALLET`, `CHECK`, `OTHER` |
| `requires_reference` | boolean | No | `false` |
| `status` | `ACTIVE` \| `INACTIVE` | Sí | — |

```json
{
  "code": "TRANSFER",
  "name": "Transferencia bancaria",
  "method_type": "BANK",
  "requires_reference": true,
  "status": "ACTIVE"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-payment-reference-dev.onrender.com/global-payment-methods' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "TRANSFER",
    "name": "Transferencia bancaria",
    "method_type": "BANK",
    "requires_reference": true,
    "status": "ACTIVE"
  }'
```

Respuestas: `201` con el objeto; `409` `{"detail": "Ya existe un método de pago con el código indicado."}`; `422`; `401`/`403`. `GlobalPaymentMethodCreate` y `GlobalPaymentMethodUpdate` no declaran `extra="forbid"`: los campos adicionales se **ignoran** (verificado en el código; los modelos de tipos de condición sí los rechazan).

### 11. `GET /global-payment-methods/{payment_method_id}`

`READ`. URL `https://sio-payment-reference-dev.onrender.com/global-payment-methods/{payment_method_id}`; permiso de lectura. `200` con `GlobalPaymentMethodResponse`; `404` `{"detail": "..."}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/global-payment-methods/b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GlobalPaymentMethodResponse`; valores ilustrativos):

```json
{
  "id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "code": "CASH",
  "name": "Efectivo",
  "method_type": "CASH",
  "requires_reference": false,
  "status": "ACTIVE",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 12. `PUT /global-payment-methods/{payment_method_id}`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · reemplazo completo, incluido `status`, de un método usado por ventas y compras de todas las empresas |
| URL | `https://sio-payment-reference-dev.onrender.com/global-payment-methods/{payment_method_id}` |
| Permiso | `perm:payment-reference:global_payment_methods:update` |

Cuerpo (`GlobalPaymentMethodUpdate`; todos obligatorios): `code` (≤ 40, único), `name` (≤ 120), `method_type` (enum), `requires_reference` (boolean), `status` (`ACTIVE` \| `INACTIVE`).

```json
{
  "code": "TRANSFER",
  "name": "Transferencia bancaria",
  "method_type": "BANK",
  "requires_reference": true,
  "status": "INACTIVE"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X PUT 'https://sio-payment-reference-dev.onrender.com/global-payment-methods/b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "TRANSFER",
    "name": "Transferencia bancaria",
    "method_type": "BANK",
    "requires_reference": true,
    "status": "INACTIVE"
  }'
```

Reglas: **sin control de versión**: el último que escribe gana. Poner `status` en `INACTIVE` hace que el método deje de ser elegible en nuevas ventas y compras (`409 REFERENCES_NOT_ELIGIBLE` en Sales y Purchase); las operaciones ya registradas conservan sus *snapshots* (`payment_method_code_snapshot`, `payment_method_name_snapshot`). Respuestas: `200`; `404`; `409` por código duplicado; `422`.

Ejemplo de respuesta `200` (`GlobalPaymentMethodResponse`; valores ilustrativos):

```json
{
  "id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "code": "CASH",
  "name": "Efectivo",
  "method_type": "CASH",
  "requires_reference": false,
  "status": "ACTIVE",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `401` `{"detail": "Se requiere un token de acceso Bearer"}` | Sin token | Autenticar |
| `403` `{"detail": "Su usuario no tiene permiso…"}` | Falta el permiso | Ocultar la acción; este servicio no devuelve `trace_id` |
| `404` `{"detail": "..."}` | UUID inexistente | Revisar el identificador |
| `409` con `code` `PAYMENT_REFERENCE.VERSION_CONFLICT` | `version` desactualizada (solo tipos de condición) | Recargar y repetir |
| `409` con `code` `PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION` | Inactivar algo ya inactivo o reactivar algo ya activo | Recargar el estado |
| `409` sin `code` | Código duplicado | Elegir otro `code` |
| `422` con `detail` en lista | Validación FastAPI (longitud, enumeración, `page_size`) | Leer `loc` y `msg` |
| `503` `{"detail": "Payment Reference no puede atender la solicitud porque su base de datos no está disponible. Intente de nuevo en unos momentos."}` | Base de datos caída | Reintentar |

## Dependencias

Ninguna hacia otros servicios. Lo consumen Sales y Purchase (`payment_method_id`) y Commercial Relationship (`payment_condition_type_id` en condiciones de pago de clientes y proveedores; además su cuenta técnica lee los tipos de condición).

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 12 |
| Operaciones documentadas | 12 |
| Permisos contrastados con el código | Sí (`api/global_payment_condition_types.py`, `api/global_payment_methods.py`) |
| Esquemas contrastados | Sí (`api/schemas/*.py`, restricciones únicas en `infrastructure/models.py`) |
| Verificado | `GlobalPaymentMethodCreate`/`Update` ignoran los campos adicionales; los modelos de tipos de condición los rechazan con `422` |

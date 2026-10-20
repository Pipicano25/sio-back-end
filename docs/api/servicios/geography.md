# Geography API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Geography es el catálogo **global** de países, divisiones administrativas (departamentos, estados, provincias…) y ciudades. Lo usan las empresas, sucursales e identidades de SIO para sus direcciones. El frontend lo consume sobre todo para **selectores en cascada**: país → división administrativa → ciudad.

## Responsabilidad

- Mantener los tres catálogos con códigos únicos, jerarquía coherente (una división pertenece a un país; una ciudad a un país y, opcionalmente, a una división del mismo país) y control de concurrencia por `version`.
- Es un catálogo compartido: no conoce empresas ni sucursales.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-geography-dev.onrender.com` (**sin** `/api/v1`) |
| Salud | `https://sio-geography-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-geography-dev.onrender.com/docs) · [/openapi.json](https://sio-geography-dev.onrender.com/openapi.json) |
| Formato de error | **Básico** (`{"detail": ...}`), sin `code`, `trace_id` ni `X-Trace-Id` ([Errores §1.2](../guias/errores.md#12-formato-básico-geography-y-payment-reference)) |
| Operaciones en el contrato desplegado | 17 (15 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/geography-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos con formato `perm:geography:{recurso}:{accion}`, recurso `global_countries`, `global_administrative_divisions` o `global_cities`:

| Acción | Operaciones | Grupos de la plantilla que la tienen |
|---|---|---|
| `read` | Listar y consultar | Todos los grupos: `administradores`, `supervisores`, `compras`, `ventas`, `inventario` (vía `perm:geography:all:read`), `reportes` y `consulta` (permisos de lectura por recurso) |
| `create` | Crear | `administradores`, `supervisores` (`perm:all:all:create`) |
| `update` | Actualizar | `administradores`, `supervisores` (`perm:all:all:update`) |
| `delete` | Eliminar físicamente | `administradores` |

## Alcance de datos

Global: todos los usuarios ven los mismos registros. Las escrituras afectan a toda la plataforma.

## Convenciones comunes

- Listas paginadas con `page` (≥ 1) y `page_size` (1–100, por defecto 20) y la envoltura `items`, `page`, `page_size`, `total_records`, `total_pages`.
- `status` es `ACTIVE` o `INACTIVE`. Sin filtro, las listas devuelven ambos estados. **No existe** operación de inactivación separada: el estado se cambia con `PUT`.
- `PUT` es reemplazo completo y exige `version` (≥ 1), la última leída. Versión desactualizada → `409` `{"detail": "El registro fue modificado por otra operación. Consulte nuevamente antes de actualizar."}`.
- `DELETE` es **borrado físico** (`204`). Si existen registros relacionados (divisiones o ciudades del país, ciudades de la división, o referencias desde otros servicios no comprobables aquí), responde `409` con `detail` «No se puede eliminar … porque existen registros relacionados.».
- `422` usa el formato estándar de FastAPI (`detail` como lista con `loc`, `msg`, `type`).
- Todas las respuestas de recurso incluyen `created_by`, `updated_by` (`sub` del autor), `created_at`, `updated_at` y `version`.

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` | Proceso y base de datos listos | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/global-countries` | Listar países | `perm:geography:global_countries:read` | `READ` | [Ver](#3-get-global-countries) |
| 4 | `POST` | `/global-countries` | Crear país | `perm:geography:global_countries:create` | `WRITE` | [Ver](#4-post-global-countries) |
| 5 | `GET` | `/global-countries/{country_id}` | Consultar país | `perm:geography:global_countries:read` | `READ` | [Ver](#5-get-global-countriescountry_id) |
| 6 | `PUT` | `/global-countries/{country_id}` | Reemplazar país | `perm:geography:global_countries:update` | `WRITE` | [Ver](#6-put-global-countriescountry_id) |
| 7 | `DELETE` | `/global-countries/{country_id}` | Eliminar país | `perm:geography:global_countries:delete` | `HIGH_RISK` | [Ver](#7-delete-global-countriescountry_id) |
| 8 | `GET` | `/global-administrative-divisions` | Listar divisiones | `perm:geography:global_administrative_divisions:read` | `READ` | [Ver](#8-get-global-administrative-divisions) |
| 9 | `POST` | `/global-administrative-divisions` | Crear división | `perm:geography:global_administrative_divisions:create` | `WRITE` | [Ver](#9-post-global-administrative-divisions) |
| 10 | `GET` | `/global-administrative-divisions/{division_id}` | Consultar división | `perm:geography:global_administrative_divisions:read` | `READ` | [Ver](#10-get-global-administrative-divisionsdivision_id) |
| 11 | `PUT` | `/global-administrative-divisions/{division_id}` | Reemplazar división | `perm:geography:global_administrative_divisions:update` | `WRITE` | [Ver](#11-put-global-administrative-divisionsdivision_id) |
| 12 | `DELETE` | `/global-administrative-divisions/{division_id}` | Eliminar división | `perm:geography:global_administrative_divisions:delete` | `HIGH_RISK` | [Ver](#12-delete-global-administrative-divisionsdivision_id) |
| 13 | `GET` | `/global-cities` | Listar ciudades | `perm:geography:global_cities:read` | `READ` | [Ver](#13-get-global-cities) |
| 14 | `POST` | `/global-cities` | Crear ciudad | `perm:geography:global_cities:create` | `WRITE` | [Ver](#14-post-global-cities) |
| 15 | `GET` | `/global-cities/{city_id}` | Consultar ciudad | `perm:geography:global_cities:read` | `READ` | [Ver](#15-get-global-citiescity_id) |
| 16 | `PUT` | `/global-cities/{city_id}` | Reemplazar ciudad | `perm:geography:global_cities:update` | `WRITE` | [Ver](#16-put-global-citiescity_id) |
| 17 | `DELETE` | `/global-cities/{city_id}` | Eliminar ciudad | `perm:geography:global_cities:delete` | `HIGH_RISK` | [Ver](#17-delete-global-citiescity_id) |

## Objetos

**`GlobalCountryResponse`**: `id` (UUID), `iso2_code` (2 caracteres, único), `iso3_code` (3 caracteres, único), `name` (≤ 120), `phone_prefix` (string \| null, ≤ 10), `status`, `version`, trazabilidad.

**`GlobalAdministrativeDivisionResponse`**: `id`, `country_id` (UUID), `parent_division_id` (UUID \| null; división superior del mismo país), `code` (≤ 40), `name` (≤ 160), `division_type` (`DEPARTMENT`, `STATE`, `PROVINCE`, `REGION`, `DISTRICT`, `OTHER`), `status`, `version`, trazabilidad.

**`GlobalCityResponse`**: `id`, `country_id`, `administrative_division_id` (UUID \| null), `code` (string \| null, ≤ 40), `name` (≤ 160), `latitude` y `longitude` (cadenas decimales \| null), `status`, `version`, trazabilidad.

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-geography-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-geography-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-geography-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` `{"detail": "La base de datos no está disponible."}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-geography-dev.onrender.com/health/ready'
```

### 3. `GET /global-countries`

| | |
|---|---|
| Clasificación | `READ` · global |
| URL | `https://sio-geography-dev.onrender.com/global-countries` |
| Permiso | `perm:geography:global_countries:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Validación |
|---|---|---|---|---|
| `page`, `page_size` | query | integer | No | 1–100, por defecto 20 |
| `search` | query | string | No | ≤ 120; parcial por nombre, ISO2 o ISO3 |
| `iso2_code` | query | string | No | Exactamente 2 caracteres; igualdad |
| `iso3_code` | query | string | No | Exactamente 3 caracteres; igualdad |
| `status` | query | `ACTIVE` \| `INACTIVE` | No | — |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-countries?status=ACTIVE&page_size=100' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000001",
      "iso2_code": "CO",
      "iso3_code": "COL",
      "name": "Colombia",
      "phone_prefix": "+57",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto para `country_id`:** `items[].id`. Se usa en empresas y sucursales (Operational Context), identidades (Party Identity) y como filtro en las operaciones 8 y 13.

### 4. `POST /global-countries`

| | |
|---|---|
| Clasificación | `WRITE` · catálogo global |
| URL | `https://sio-geography-dev.onrender.com/global-countries` |
| Permiso | `perm:geography:global_countries:create` |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`GlobalCountryCreate`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `iso2_code` | string | Sí | 2 caracteres (ISO 3166-1 alpha-2); único |
| `iso3_code` | string | Sí | 3 caracteres (alpha-3); único |
| `name` | string | Sí | 1–120 |
| `phone_prefix` | string \| null | No | ≤ 10 |
| `status` | `ACTIVE` \| `INACTIVE` | Sí | — |

```json
{
  "iso2_code": "PE",
  "iso3_code": "PER",
  "name": "Perú",
  "phone_prefix": "+51",
  "status": "ACTIVE"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-geography-dev.onrender.com/global-countries' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "iso2_code": "PE",
    "iso3_code": "PER",
    "name": "Perú",
    "phone_prefix": "+51",
    "status": "ACTIVE"
  }'
```

Respuestas: `201` con `GlobalCountryResponse` (`version` 1); `409` `{"detail": "Ya existe un país con alguno de los códigos ISO indicados."}`; `422`; `401`/`403`.

### 5. `GET /global-countries/{country_id}`

`READ`. URL `https://sio-geography-dev.onrender.com/global-countries/{country_id}`; `country_id` (ruta, UUID) del campo `id` de la operación 3. `200` con el objeto; `404` `{"detail": "El país solicitado no existe."}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-countries/c0a80101-0000-4000-8000-000000000001' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GlobalCountryResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000001",
  "iso2_code": "CO",
  "iso3_code": "COL",
  "name": "Colombia",
  "phone_prefix": "+57",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 6. `PUT /global-countries/{country_id}`

`WRITE`. URL `https://sio-geography-dev.onrender.com/global-countries/{country_id}`; permiso `perm:geography:global_countries:update`. Cuerpo (`GlobalCountryUpdate`): los mismos campos de la operación 4 **más `version`** (integer ≥ 1, obligatorio). Reemplazo completo, incluido `status`.

```json
{
  "iso2_code": "CO",
  "iso3_code": "COL",
  "name": "Colombia",
  "phone_prefix": "+57",
  "status": "ACTIVE",
  "version": 1
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X PUT 'https://sio-geography-dev.onrender.com/global-countries/c0a80101-0000-4000-8000-000000000001' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "iso2_code": "CO",
    "iso3_code": "COL",
    "name": "Colombia",
    "phone_prefix": "+57",
    "status": "ACTIVE",
    "version": 1
  }'
```

Respuestas: `200` con el objeto (`version` incrementada); `404`; `409` por versión desactualizada o códigos ISO duplicados; `422`. Efecto: cambiar `status` a `INACTIVE` deja el país no elegible en los servicios que validan ubicaciones activas (Operational Context responde `422 LOCATION_INACTIVE` al crear o editar empresas y sucursales con él).

Ejemplo de respuesta `200` (`GlobalCountryResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000001",
  "iso2_code": "CO",
  "iso3_code": "COL",
  "name": "Colombia",
  "phone_prefix": "+57",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 7. `DELETE /global-countries/{country_id}`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · borrado físico de un registro global |
| URL | `https://sio-geography-dev.onrender.com/global-countries/{country_id}` |
| Permiso | `perm:geography:global_countries:delete` |

Sin cuerpo. Respuestas: `204` sin contenido; `404` `{"detail": "El país solicitado no existe."}`; `409` si tiene divisiones o ciudades (las claves foráneas usan `RESTRICT`). **Advertencia:** otros servicios guardan `country_id` sin clave foránea (empresas, sucursales, identidades); Geography no puede detectar esas referencias y el borrado las deja apuntando a un país inexistente. Prefiera `PUT` con `status: "INACTIVE"`. Confirmar siempre con el usuario.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-geography-dev.onrender.com/global-countries/c0a80101-0000-4000-8000-000000000001' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 8. `GET /global-administrative-divisions`

| | |
|---|---|
| Clasificación | `READ` · global |
| URL | `https://sio-geography-dev.onrender.com/global-administrative-divisions` |
| Permiso | `perm:geography:global_administrative_divisions:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `page`, `page_size` | query | integer | No | 1–100 | — |
| `search` | query | string | No | ≤ 160; parcial por código o nombre | — |
| `country_id` | query | UUID | No | — | Operación 3, `items[].id` |
| `parent_division_id` | query | UUID | No | — | Esta operación, `items[].id` |
| `division_type` | query | enum | No | `DEPARTMENT`, `STATE`, `PROVINCE`, `REGION`, `DISTRICT`, `OTHER` | — |
| `status` | query | `ACTIVE` \| `INACTIVE` | No | — | — |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-administrative-divisions?country_id=c0a80101-0000-4000-8000-000000000001&status=ACTIVE&page_size=100' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000002",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "parent_division_id": null,
      "code": "05",
      "name": "Antioquia",
      "division_type": "DEPARTMENT",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto para `administrative_division_id`:** `items[].id`. Para un selector en cascada, filtra por el `country_id` elegido.

### 9. `POST /global-administrative-divisions`

`WRITE`. URL `https://sio-geography-dev.onrender.com/global-administrative-divisions`; permiso `perm:geography:global_administrative_divisions:create`. Cuerpo (`GlobalAdministrativeDivisionCreate`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `country_id` | UUID | Sí | Debe existir (`409` «El país indicado no existe.») |
| `parent_division_id` | UUID \| null | No | Debe existir y pertenecer al **mismo país** (`409`) |
| `code` | string | Sí | 1–40 |
| `name` | string | Sí | 1–160 |
| `division_type` | enum | Sí | `DEPARTMENT`, `STATE`, `PROVINCE`, `REGION`, `DISTRICT`, `OTHER` |
| `status` | `ACTIVE` \| `INACTIVE` | Sí | — |

```json
{
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "parent_division_id": null,
  "code": "11",
  "name": "Bogotá, D.C.",
  "division_type": "DISTRICT",
  "status": "ACTIVE"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-geography-dev.onrender.com/global-administrative-divisions' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "parent_division_id": null,
    "code": "11",
    "name": "Bogotá, D.C.",
    "division_type": "DISTRICT",
    "status": "ACTIVE"
  }'
```

Respuestas: `201`; `409` (país inexistente, división superior inválida o de otro país, conflicto de integridad «No fue posible guardar la división administrativa.»); `422`. `code` **no** es único en divisiones ni ciudades (verificado en los modelos: las únicas restricciones de unicidad del servicio son `iso2_code` e `iso3_code` de países); el frontend no debe asumir que un `code` repetido se rechace.

Ejemplo de respuesta `201` (`GlobalAdministrativeDivisionResponse`; valores ilustrativos):

```json
{
  "id": "ae461ef2-a5f2-4c7b-8918-2b3c14efa9f1",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "parent_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "CUN",
  "name": "Cundinamarca",
  "division_type": "DEPARTMENT",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 10. `GET /global-administrative-divisions/{division_id}`

`READ`. URL `https://sio-geography-dev.onrender.com/global-administrative-divisions/{division_id}`. `200` con el objeto; `404` `{"detail": "..."}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-administrative-divisions/c0a80101-0000-4000-8000-000000000002' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GlobalAdministrativeDivisionResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000002",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "parent_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "CUN",
  "name": "Cundinamarca",
  "division_type": "DEPARTMENT",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 11. `PUT /global-administrative-divisions/{division_id}`

`WRITE`. URL `https://sio-geography-dev.onrender.com/global-administrative-divisions/{division_id}`; permiso `…update`. Cuerpo (`GlobalAdministrativeDivisionUpdate`): los campos de la operación 9 **más `version`** (≥ 1). Reglas adicionales: una división no puede ser su propia superior (`409` «Una división administrativa no puede ser su propia división superior…»). Respuestas: `200`; `404`; `409` (versión, padre inválido, integridad); `422`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-geography-dev.onrender.com/global-administrative-divisions/c0a80101-0000-4000-8000-000000000002' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "parent_division_id": "c0a80101-0000-4000-8000-000000000002",
    "code": "CUN",
    "name": "Cundinamarca",
    "division_type": "DEPARTMENT",
    "status": "ACTIVE",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GlobalAdministrativeDivisionResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000002",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "parent_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "CUN",
  "name": "Cundinamarca",
  "division_type": "DEPARTMENT",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 12. `DELETE /global-administrative-divisions/{division_id}`

`HIGH_RISK`. URL `https://sio-geography-dev.onrender.com/global-administrative-divisions/{division_id}`; permiso `…delete`. `204`; `404`; `409` `{"detail": "No se puede eliminar la división porque existen registros relacionados."}` si tiene ciudades o divisiones hijas. Misma advertencia que la operación 7 sobre referencias en otros servicios.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-geography-dev.onrender.com/global-administrative-divisions/c0a80101-0000-4000-8000-000000000002' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 13. `GET /global-cities`

| | |
|---|---|
| Clasificación | `READ` · global |
| URL | `https://sio-geography-dev.onrender.com/global-cities` |
| Permiso | `perm:geography:global_cities:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `page`, `page_size` | query | integer | No | 1–100 | — |
| `search` | query | string | No | ≤ 160; parcial por código o nombre | — |
| `country_id` | query | UUID | No | — | Operación 3 |
| `administrative_division_id` | query | UUID | No | — | Operación 8 |
| `code` | query | string | No | ≤ 40; igualdad | — |
| `status` | query | `ACTIVE` \| `INACTIVE` | No | — | — |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=c0a80101-0000-4000-8000-000000000002&status=ACTIVE&page_size=100' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000003",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "code": "05001",
      "name": "Medellín",
      "latitude": "6.244203",
      "longitude": "-75.581212",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto para `city_id`:** `items[].id`. Operational Context exige coherencia: la ciudad debe pertenecer a la división y al país enviados (`422 GEOGRAPHY_INCOHERENT`).

### 14. `POST /global-cities`

`WRITE`. URL `https://sio-geography-dev.onrender.com/global-cities`; permiso `perm:geography:global_cities:create`. Cuerpo (`GlobalCityCreate`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `country_id` | UUID | Sí | Debe existir (`409` «El país indicado no existe.») |
| `administrative_division_id` | UUID \| null | No | Debe existir y ser del mismo país (`409`) |
| `code` | string \| null | No | ≤ 40; código oficial cuando exista |
| `name` | string | Sí | 1–160 |
| `latitude` | number \| string \| null | No | −90 a 90 |
| `longitude` | number \| string \| null | No | −180 a 180 |
| `status` | `ACTIVE` \| `INACTIVE` | Sí | — |

```json
{
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "05001",
  "name": "Medellín",
  "latitude": "6.244203",
  "longitude": "-75.581212",
  "status": "ACTIVE"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-geography-dev.onrender.com/global-cities' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "code": "05001",
    "name": "Medellín",
    "latitude": "6.244203",
    "longitude": "-75.581212",
    "status": "ACTIVE"
  }'
```

Respuestas: `201` (coordenadas devueltas como cadenas); `409` (país inexistente, división inválida o de otro país, integridad «No fue posible guardar la ciudad.»); `422` (rango de coordenadas, longitudes).

Ejemplo de respuesta `201` (`GlobalCityResponse`; valores ilustrativos):

```json
{
  "id": "fa1730d8-2668-4b82-8b1d-1acc0ddce804",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "BOG",
  "name": "Bogotá",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 15. `GET /global-cities/{city_id}`

`READ`. URL `https://sio-geography-dev.onrender.com/global-cities/{city_id}`. `200`; `404` `{"detail": "La ciudad solicitada no existe."}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-cities/c0a80101-0000-4000-8000-000000000003' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GlobalCityResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000003",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "BOG",
  "name": "Bogotá",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 16. `PUT /global-cities/{city_id}`

`WRITE`. URL `https://sio-geography-dev.onrender.com/global-cities/{city_id}`; permiso `…update`. Cuerpo (`GlobalCityUpdate`): los campos de la operación 14 **más `version`** (≥ 1). Respuestas: `200`; `404`; `409` (versión, división inválida, integridad); `422`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-geography-dev.onrender.com/global-cities/c0a80101-0000-4000-8000-000000000003' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "code": "BOG",
    "name": "Bogotá",
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "status": "ACTIVE",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GlobalCityResponse`; valores ilustrativos):

```json
{
  "id": "c0a80101-0000-4000-8000-000000000003",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "code": "BOG",
  "name": "Bogotá",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 17. `DELETE /global-cities/{city_id}`

`HIGH_RISK`. URL `https://sio-geography-dev.onrender.com/global-cities/{city_id}`; permiso `…delete`. `204`; `404`; `409` `{"detail": "No se puede eliminar la ciudad porque existen registros relacionados."}`. Las empresas, sucursales y perfiles de contacto de otros servicios guardan `city_id` sin clave foránea: prefiera inactivar con `PUT`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-geography-dev.onrender.com/global-cities/c0a80101-0000-4000-8000-000000000003' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `401` / `403` `{"detail": ...}` | Sin token o sin permiso | Autenticar; ocultar acciones de escritura a perfiles sin permiso |
| `404` | UUID inexistente | Revisar el identificador |
| `409` «El registro fue modificado por otra operación…» | `version` desactualizada | Recargar y repetir |
| `409` «Ya existe un país con alguno de los códigos ISO indicados.» | ISO2 o ISO3 duplicado | Corregir códigos |
| `409` «…debe pertenecer al mismo país…» | División o ciudad con padre de otro país | Corregir jerarquía |
| `409` «No se puede eliminar … registros relacionados.» | Borrado con hijos | Inactivar en lugar de borrar |
| `422` con lista en `detail` | Longitudes, enumeraciones, coordenadas fuera de rango, `page_size` | Leer `loc` y `msg` |
| `503` `{"detail": "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."}` | Base de datos caída | Reintentar |

## Dependencias

Ninguna hacia otros servicios. Lo consumen Operational Context (empresas y sucursales validan país, división y ciudad activos y coherentes), Party Identity (países de identificación y perfiles de contacto) y la cuenta técnica de Party Identity (lectura de países).

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 17 |
| Operaciones documentadas | 17 |
| Permisos contrastados con el código | Sí (`api/global_countries.py`, `api/global_administrative_divisions.py`, `api/global_cities.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado; mensajes de error de `infrastructure/*_repository.py`) |
| Verificado | `code` de divisiones y ciudades no tiene restricción de unicidad; solo `iso2_code`/`iso3_code` de países son únicos |

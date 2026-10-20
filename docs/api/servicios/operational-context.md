# Operational Context API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Operational Context define **quién puede operar dónde**: las empresas cliente de SIO, sus sucursales, los usuarios operativos (membresía de una persona en una empresa), las sucursales asignadas a cada usuario y los asesores de cada empresa. Es la **única fuente de membresías**: todos los servicios de negocio le consultan, con el token del usuario, si una persona tiene acceso a una empresa o sucursal. Para el frontend es el primer servicio que se llama después del login.

## Responsabilidad

- Empresas (vinculadas a una identidad de organización de Party Identity) y sucursales, con ubicación validada en Geography.
- Usuarios operativos: membresía de una persona (cuenta de Keycloak + identidad de Party Identity) en una empresa; asignaciones usuario–sucursal.
- Asesores de empresa (varios vigentes, uno principal).
- Contratos de acceso operativo: contexto propio (`/me/operational-context`) y comprobación de acceso (`/operational-access`).

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-operational-context-dev.onrender.com/api/v1` |
| Salud | `https://sio-operational-context-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-operational-context-dev.onrender.com/docs) · [/openapi.json](https://sio-operational-context-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `OPERATIONAL_CONTEXT.*` y `trace_id` |
| Operaciones en el contrato desplegado | 33 (31 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/operational-context-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos con formato `perm:operational-context:{recurso}:{accion}`:

| Recurso | Acciones y operaciones | Grupos de la plantilla con lectura | Grupos con escritura |
|---|---|---|---|
| `companies` | `read` (listar, consultar), `create` (+ `platform:administer`), `update` (modificar, reactivar + `platform:administer`), `delete` (inactivar + `platform:administer`) | Todos (`compras`, `ventas`, `inventario` vía `perm:operational-context:all:read`; `reportes` y `consulta` por recurso) | `administradores` (único con `platform:administer`); `supervisores` pueden `PUT` (no exige `platform:administer`) |
| `branches` | `read`, `create`, `update` (modificar, reactivar), `delete` (inactivar) | Todos | `administradores`, `supervisores` (salvo `delete`) |
| `application_users` | `read` (listar, consultar, **`/me/operational-context`**, **`/operational-access`**), `create`, `update` (modificar, reactivar), `delete` (inactivar) | Todos | `administradores`, `supervisores` (salvo `delete`) |
| `user_branches` | `read`, `create`, `update` (reactivar), `delete` (retirar) | Todos | `administradores`, `supervisores` (salvo `delete`) |
| `company_advisor_assignments` | `read`, `create`, `delete` (cerrar), `create` + `delete` (cambiar principal) | Todos | `administradores`; `supervisores` solo `create` |
| `platform` | `administer` (ver y administrar todas las empresas sin membresía), `lookup` (lecturas por UUID sin membresía, para identidades técnicas) | — | `administradores` (vía `perm:all:all:all`) |

## Alcance de datos

El alcance se calcula en **cada solicitud** a partir de las membresías `ACTIVE` del `sub` del token, sin caché:

| Situación | Efecto |
|---|---|
| Usuario con `perm:operational-context:platform:administer` | Ve y administra todas las empresas y sucursales |
| Usuario con membresía `ACTIVE` | Ve y opera solo sus empresas; las listas (`GET /companies`) se filtran a ellas |
| Lecturas por UUID (`GET /companies/{id}`, `GET /branches/{id}`, `GET /application-users/{id}`, …) | Además, las permite `perm:operational-context:platform:lookup` sin membresía |
| Fuera de alcance | `404 OPERATIONAL_CONTEXT.NOT_FOUND` con el mismo mensaje que un UUID inexistente («La empresa solicitada no existe.») |

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | PostgreSQL disponible | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/companies` | Listar empresas del alcance | `companies:read` | `READ` | [Ver](#3-get-companies) |
| 4 | `POST` | `/companies` | Registrar empresa | `companies:create` + `platform:administer` | `WRITE` | [Ver](#4-post-companies) |
| 5 | `GET` | `/companies/{company_id}` | Consultar empresa | `companies:read` | `READ` | [Ver](#5-get-companiescompany_id) |
| 6 | `PUT` | `/companies/{company_id}` | Modificar empresa | `companies:update` | `WRITE` | [Ver](#6-put-companiescompany_id) |
| 7 | `POST` | `/companies/{company_id}/deactivate` | Inactivar empresa | `companies:delete` + `platform:administer` | `HIGH_RISK` | [Ver](#7-post-companiescompany_iddeactivate) |
| 8 | `POST` | `/companies/{company_id}/reactivate` | Reactivar empresa | `companies:update` + `platform:administer` | `WRITE` | [Ver](#8-post-companiescompany_idreactivate) |
| 9 | `GET` | `/companies/{company_id}/branches` | Listar sucursales | `branches:read` | `READ` | [Ver](#9-get-companiescompany_idbranches) |
| 10 | `POST` | `/companies/{company_id}/branches` | Registrar sucursal | `branches:create` | `WRITE` | [Ver](#10-post-companiescompany_idbranches) |
| 11 | `GET` | `/branches/{branch_id}` | Consultar sucursal | `branches:read` | `READ` | [Ver](#11-get-branchesbranch_id) |
| 12 | `PUT` | `/branches/{branch_id}` | Modificar sucursal | `branches:update` | `WRITE` | [Ver](#12-put-branchesbranch_id) |
| 13 | `POST` | `/branches/{branch_id}/deactivate` | Inactivar sucursal | `branches:delete` | `HIGH_RISK` | [Ver](#13-post-branchesbranch_iddeactivate) |
| 14 | `POST` | `/branches/{branch_id}/reactivate` | Reactivar sucursal | `branches:update` | `WRITE` | [Ver](#14-post-branchesbranch_idreactivate) |
| 15 | `GET` | `/companies/{company_id}/application-users` | Listar usuarios operativos | `application_users:read` | `READ` | [Ver](#15-get-companiescompany_idapplication-users) |
| 16 | `POST` | `/companies/{company_id}/application-users` | Registrar usuario operativo | `application_users:create` | `HIGH_RISK` | [Ver](#16-post-companiescompany_idapplication-users) |
| 17 | `GET` | `/application-users/{application_user_id}` | Consultar usuario operativo | `application_users:read` | `READ` | [Ver](#17-get-application-usersapplication_user_id) |
| 18 | `PUT` | `/application-users/{application_user_id}` | Modificar datos de referencia | `application_users:update` | `WRITE` | [Ver](#18-put-application-usersapplication_user_id) |
| 19 | `POST` | `/application-users/{application_user_id}/deactivate` | Inactivar membresía | `application_users:delete` | `HIGH_RISK` | [Ver](#19-post-application-usersapplication_user_iddeactivate) |
| 20 | `POST` | `/application-users/{application_user_id}/reactivate` | Reactivar membresía | `application_users:update` | `HIGH_RISK` | [Ver](#20-post-application-usersapplication_user_idreactivate) |
| 21 | `GET` | `/application-users/{application_user_id}/user-branches` | Sucursales asignadas a un usuario | `user_branches:read` | `READ` | [Ver](#21-get-application-usersapplication_user_iduser-branches) |
| 22 | `POST` | `/application-users/{application_user_id}/user-branches` | Asignar sucursal | `user_branches:create` | `HIGH_RISK` | [Ver](#22-post-application-usersapplication_user_iduser-branches) |
| 23 | `GET` | `/branches/{branch_id}/user-branches` | Usuarios asignados a una sucursal | `user_branches:read` | `READ` | [Ver](#23-get-branchesbranch_iduser-branches) |
| 24 | `GET` | `/user-branches/{user_branch_id}` | Consultar asignación | `user_branches:read` | `READ` | [Ver](#24-get-user-branchesuser_branch_id) |
| 25 | `POST` | `/user-branches/{user_branch_id}/deactivate` | Retirar asignación | `user_branches:delete` | `HIGH_RISK` | [Ver](#25-post-user-branchesuser_branch_iddeactivate) |
| 26 | `POST` | `/user-branches/{user_branch_id}/reactivate` | Reactivar asignación | `user_branches:update` | `HIGH_RISK` | [Ver](#26-post-user-branchesuser_branch_idreactivate) |
| 27 | `GET` | `/companies/{company_id}/advisor-assignments` | Historial de asesores | `company_advisor_assignments:read` | `READ` | [Ver](#27-get-companiescompany_idadvisor-assignments) |
| 28 | `POST` | `/companies/{company_id}/advisor-assignments` | Registrar asesor | `company_advisor_assignments:create` | `WRITE` | [Ver](#28-post-companiescompany_idadvisor-assignments) |
| 29 | `GET` | `/advisor-assignments/{assignment_id}` | Consultar asignación de asesor | `company_advisor_assignments:read` | `READ` | [Ver](#29-get-advisor-assignmentsassignment_id) |
| 30 | `POST` | `/advisor-assignments/{assignment_id}/close` | Cerrar asignación | `company_advisor_assignments:delete` | `WRITE` | [Ver](#30-post-advisor-assignmentsassignment_idclose) |
| 31 | `POST` | `/companies/{company_id}/advisor-assignments/change-primary` | Cambiar asesor principal | `company_advisor_assignments:create` + `delete` | `WRITE` | [Ver](#31-post-companiescompany_idadvisor-assignmentschange-primary) |
| 32 | `GET` | `/me/operational-context` | Contexto operativo propio | `application_users:read` | `READ` | [Ver](#32-get-meoperational-context) |
| 33 | `GET` | `/operational-access` | Comprobar acceso operativo | `application_users:read` | `READ` | [Ver](#33-get-operational-access) |

Todos los permisos de la tabla empiezan por `perm:operational-context:`.

## Convenciones comunes

- Listas paginadas (`page` ≥ 1, `page_size` 1–100, por defecto 20) con la envoltura `items`, `page`, `page_size`, `total_records`, `total_pages`. Por defecto devuelven solo `status=ACTIVE`; `status=INACTIVE` muestra las inactivas.
- Escrituras con `version` (≥ 1): `409 OPERATIONAL_CONTEXT.VERSION_CONFLICT` si no coincide. Las operaciones de estado (`deactivate`, `reactivate`) reciben `{"version": n}`.
- No hay borrado físico: inactivar conserva el registro. Inactivar algo ya inactivo (o reactivar algo activo) → `409 INVALID_STATUS_TRANSITION`.
- Todos los modelos rechazan campos adicionales (`422`). Las cadenas en blanco en campos opcionales se tratan como `null`.
- Ubicación (`country_id`, `administrative_division_id`, `city_id`): se valida en Geography sin transacción abierta; valores inexistentes → `422 COUNTRY_NOT_FOUND` / `ADMINISTRATIVE_DIVISION_NOT_FOUND` / `CITY_NOT_FOUND`; inactivos → `422 LOCATION_INACTIVE`; incoherentes entre sí → `422 GEOGRAPHY_INCOHERENT`; división o ciudad sin país → `422 GEOGRAPHY_PARENT_REQUIRED`. `latitude`/`longitude` son decimales (número o texto) y se devuelven como cadenas.
- `422 IMMUTABLE_FIELD` cuando se envía un campo que no puede cambiar.
- Formato de 401/403/404/503 como en [Errores](../guias/errores.md); `503 DEPENDENCY_UNAVAILABLE` lleva `dependency` (`database`, `party-identity`, `geography`, `keycloak`).

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-operational-context-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-operational-context-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si PostgreSQL no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/health/ready'
```

### 3. `GET /companies`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/companies` |
| Permiso | `perm:operational-context:companies:read` |
| Alcance | Solo las empresas con membresía `ACTIVE` del usuario; todas con `platform:administer` |

Parámetros de consulta: `page`, `page_size`, `status` (`ACTIVE` por defecto, `INACTIVE`), `organization_identity_id`, `country_id`, `city_id` (UUID). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[CompanyResponse]`. Ejemplo completo en [company_id](../parametros/company-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_CompanyResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "email": "contacto@laeconomia.com",
      "phone": "+57 300 123 4567",
      "address_line": "Calle 10 # 5-20",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": null,
      "latitude": "4.6097",
      "longitude": "-74.0817",
      "timezone": "America/Bogota",
      "default_currency": "COP",
      "status": "ACTIVE",
      "version": 1,
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

`CompanyResponse`: `id`, `organization_identity_id` ([identidad](../parametros/organization-identity-id.md) con la razón social), `email`, `phone`, `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code`, `latitude`, `longitude`, `timezone` (IANA, por ejemplo `America/Bogota`), `default_currency` (por ejemplo `COP`), `status`, `version`, `created_by`, `updated_by`, `created_at`, `updated_at`. **No tiene `name`.**

### 4. `POST /companies`

| | |
|---|---|
| Clasificación | `WRITE` · crea una empresa de la plataforma |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/companies` |
| Permisos | `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer` |

Cuerpo (`CompanyCreate`):

| Campo | Tipo | Obligatorio | Validación / valor por defecto | Cómo obtenerlo |
|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Identidad `ACTIVE` en Party Identity (`422 ORGANIZATION_IDENTITY_NOT_FOUND` / `_INACTIVE`); una sola empresa por identidad (`409 DUPLICATE_ORGANIZATION_IDENTITY`) | [organization_identity_id](../parametros/organization-identity-id.md) |
| `email` | email \| null | No | Formato de correo | — |
| `phone` | string \| null | No | ≤ 40 | — |
| `address_line` | string \| null | No | — | — |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | No | Coherentes y activos en Geography | [Geography](geography.md) |
| `postal_code` | string \| null | No | ≤ 20 | — |
| `latitude`, `longitude` | number \| string \| null | No | Decimales | — |
| `timezone` | string | No | 1–60; por defecto `America/Bogota` | — |
| `default_currency` | string | No | Por defecto `COP` | — |

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322110",
  "email": "contacto@empresa-ejemplo.test",
  "phone": "+57 601 000 0000",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
  "timezone": "America/Bogota",
  "default_currency": "COP"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322110",
    "email": "contacto@empresa-ejemplo.test",
    "phone": "+57 601 000 0000",
    "address_line": "Calle 1 # 2-3",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "postal_code": "110111",
    "timezone": "America/Bogota",
    "default_currency": "COP"
  }'
```

Respuesta `201`: `CompanyResponse` (`status` `ACTIVE`, `version` 1). El `id` es el [company_id](../parametros/company-id.md). Dependencias: Party Identity y Geography.

Ejemplo de respuesta `201` (`CompanyResponse`; valores ilustrativos):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 5. `GET /companies/{company_id}`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`; permiso `companies:read`. Devuelve la empresa **en cualquier estado** si está en el alcance (membresía, `platform:administer` o `platform:lookup`). `404` si no.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompanyResponse`; valores ilustrativos):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 6. `PUT /companies/{company_id}`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`; permiso `companies:update`. Cuerpo (`CompanyUpdate`): los campos de la operación 4 con `timezone` y `default_currency` **obligatorios** más `version`. Reemplazo completo; si nada cambia no escribe ni incrementa la versión. Una empresa `INACTIVE` no se modifica (`422 COMPANY_INACTIVE`). Errores: `409 VERSION_CONFLICT`, `409 DUPLICATE_ORGANIZATION_IDENTITY`, `422` de ubicación e identidad, `404`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "email": "contacto@laeconomia.com",
    "phone": "+57 300 123 4567",
    "address_line": "Calle 10 # 5-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "timezone": "America/Bogota",
    "default_currency": "COP",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyResponse`; valores ilustrativos):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 7. `POST /companies/{company_id}/deactivate`

`HIGH_RISK`: la empresa deja de ser operable para **todos** sus usuarios (las API de negocio responderán `404`/`403 COMPANY_INACTIVE`). URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/deactivate`; permisos `companies:delete` + `platform:administer`; cuerpo `{"version": n}`. No elimina ni modifica sus sucursales. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `status: "INACTIVE"`; `409 INVALID_STATUS_TRANSITION` si ya estaba inactiva.

Ejemplo de respuesta `200` (`CompanyResponse`; valores ilustrativos):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 8. `POST /companies/{company_id}/reactivate`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/reactivate`; permisos `companies:update` + `platform:administer`; cuerpo `{"version": n}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `status: "ACTIVE"`.

Ejemplo de respuesta `200` (`CompanyResponse`; valores ilustrativos):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 9. `GET /companies/{company_id}/branches`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches`; permiso `branches:read`; alcance: membresía en la empresa. Parámetros: `page`, `page_size`, `search` (≤ 160; código y nombre), `status` (`ACTIVE` por defecto), `city_id`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[BranchResponse]`. Ejemplo completo en [branch_id](../parametros/branch-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_BranchResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "code": "SUC-01",
      "name": "Sucursal Centro",
      "email": "centro@laeconomia.com",
      "phone": "+57 300 123 4567",
      "address_line": "Calle 10 # 5-20",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": null,
      "latitude": "4.6097",
      "longitude": "-74.0817",
      "timezone": "America/Bogota",
      "effective_timezone": "America/Bogota",
      "status": "ACTIVE",
      "version": 1,
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

`BranchResponse`: `id`, `company_id`, `company_status`, `code`, `name`, `email`, `phone`, `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code`, `latitude`, `longitude`, `timezone` (propia o `null`), `effective_timezone` (la propia o la de la empresa), `status`, `version`, trazabilidad.

### 10. `POST /companies/{company_id}/branches`

| | |
|---|---|
| Clasificación | `WRITE` |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches` |
| Permiso | `perm:operational-context:branches:create` |
| Alcance | Membresía en la empresa (o `platform:administer`); la empresa debe estar `ACTIVE` (`422 COMPANY_INACTIVE`) |

Cuerpo (`BranchCreate`): `code` (string, obligatorio, único por empresa: `409 DUPLICATE_BRANCH_CODE`), `name` (1–160, obligatorio), `email`, `phone` (≤ 40), `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code` (≤ 20), `latitude`, `longitude`, `timezone` (≤ 60; `null` hereda la de la empresa).

```json
{
  "code": "SUC-002",
  "name": "Sucursal Norte",
  "email": "norte@empresa-ejemplo.test",
  "phone": "+57 601 000 0002",
  "address_line": "Autopista Norte # 100-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "timezone": null
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "SUC-002",
    "name": "Sucursal Norte",
    "email": "norte@empresa-ejemplo.test",
    "phone": "+57 601 000 0002",
    "address_line": "Autopista Norte # 100-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "timezone": null
  }'
```

Respuesta `201`: `BranchResponse`; su `id` es el [branch_id](../parametros/branch-id.md). Para que un usuario opere en ella hay que asignársela (operación 22).

Ejemplo de respuesta `201` (`BranchResponse`; valores ilustrativos):

```json
{
  "id": "b361a654-58d4-422f-8ffe-9699a87e91e3",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 11. `GET /branches/{branch_id}`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`; permiso `branches:read`. Sucursal en cualquier estado, con `company_status`. `404` fuera de alcance.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`BranchResponse`; valores ilustrativos):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 12. `PUT /branches/{branch_id}`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`; permiso `branches:update`. Cuerpo (`BranchUpdate`): los campos de la operación 10 más `version`. La empresa de la sucursal es **inmutable**. Geography solo se consulta si cambia la ubicación. Errores: `409 VERSION_CONFLICT`, `409 DUPLICATE_BRANCH_CODE`, `422`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "SUC-01",
    "name": "Sucursal Centro",
    "email": "centro@laeconomia.com",
    "phone": "+57 300 123 4567",
    "address_line": "Calle 10 # 5-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "timezone": "America/Bogota",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BranchResponse`; valores ilustrativos):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 13. `POST /branches/{branch_id}/deactivate`

`HIGH_RISK`: los usuarios asignados pierden el acceso (`allowed: false`, `BRANCH_INACTIVE`) y las ventas y compras de la sucursal fallan con `403 BRANCH_ACCESS_DENIED`; las existencias se conservan. URL `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/deactivate`; permiso `branches:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BranchResponse`; valores ilustrativos):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 14. `POST /branches/{branch_id}/reactivate`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/reactivate`; permiso `branches:update`; cuerpo `{"version": n}`. Solo si la empresa está `ACTIVE` (`422 COMPANY_INACTIVE`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BranchResponse`; valores ilustrativos):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@laeconomia.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 15. `GET /companies/{company_id}/application-users`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users`; permiso `application_users:read`. Parámetros: `page`, `page_size`, `status` (`ACTIVE` por defecto), `search` (≤ 160; nombre y correo de referencia), `keycloak_user_id` (≤ 255), `person_identity_id` (UUID). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[ApplicationUserResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_ApplicationUserResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "display_name": "Ana Pérez",
      "reference_email": "compras@ejemplo.com",
      "status": "ACTIVE",
      "version": 1,
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

`ApplicationUserResponse`:

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | `application_user_id` (el que aparece en `/me/operational-context` y en `created_by_user_id` de ventas y compras) |
| `company_id`, `company_status` | — | Empresa de la membresía |
| `keycloak_user_id` | string | `sub` de la cuenta en Keycloak |
| `person_identity_id` | UUID | [Persona](../parametros/person-identity-id.md) en Party Identity |
| `display_name` | string (≤ 160) | Nombre para mostrar |
| `reference_email` | email \| null | Correo de referencia propio de SIO |
| `status`, `version`, trazabilidad | — | — |

### 16. `POST /companies/{company_id}/application-users`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · concede a una cuenta de Keycloak membresía (y, por tanto, acceso a los datos) de la empresa |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` |
| Permiso | `perm:operational-context:application_users:create` |
| Alcance | Membresía en la empresa (o `platform:administer`); empresa `ACTIVE` |

Cuerpo (`ApplicationUserCreate`):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `keycloak_user_id` | string \| null | Exactamente uno de los dos | 1–255; `sub` de la cuenta | El administrador de Keycloak, o `keycloak_user_id` de `/me/operational-context` del propio usuario |
| `username` | string \| null | Exactamente uno de los dos | 1–255; nombre de usuario en Keycloak | Keycloak |
| `person_identity_id` | UUID | Sí | Persona `ACTIVE` en Party Identity | [person_identity_id](../parametros/person-identity-id.md) |
| `display_name` | string | Sí | 1–160 | — |
| `reference_email` | email \| null | No | — | — |

```json
{
  "username": "ventas.test",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ventas.test@ejemplo.test"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "ventas.test",
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "display_name": "Ana Pérez",
    "reference_email": "ventas.test@ejemplo.test"
  }'
```

Orden de validación (verificado): empresa visible y `ACTIVE` → duplicado por persona (`409 DUPLICATE_MEMBERSHIP`) → cuenta en Keycloak (`422 KEYCLOAK_USER_NOT_FOUND`, `422 KEYCLOAK_USER_DISABLED`, `422 TECHNICAL_ACCOUNT_NOT_ALLOWED` si es cuenta de servicio) → duplicado por `sub` → persona en Party Identity (`422 PERSON_IDENTITY_NOT_FOUND` / `_INACTIVE`) → inserción. Respuesta `201`: `ApplicationUserResponse` con `keycloak_user_id` resuelto. El servicio consulta la Admin API de Keycloak con su cuenta técnica. Dependencias: Keycloak, Party Identity.

Ejemplo de respuesta `201` (`ApplicationUserResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 17. `GET /application-users/{application_user_id}`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}`; permiso `application_users:read`. Membresía en cualquier estado; `404` fuera de alcance.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`ApplicationUserResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "compras@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 18. `PUT /application-users/{application_user_id}`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}`; permiso `application_users:update`. Cuerpo (`ApplicationUserUpdate`): `display_name` (1–160), `reference_email` (opcional), `version`. Enviar `keycloak_user_id`, `person_identity_id` o `company_id` → `422 IMMUTABLE_FIELD`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "display_name": "Ana Pérez",
    "reference_email": "ana.perez@ejemplo.com",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ApplicationUserResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 19. `POST /application-users/{application_user_id}/deactivate`

`HIGH_RISK`: el usuario pierde el acceso a esa empresa (`USER_MEMBERSHIP_INACTIVE`) en todos los servicios. URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/deactivate`; permiso `application_users:delete`; cuerpo `{"version": n}`. Solo inactiva esta membresía.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ApplicationUserResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "compras@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 20. `POST /application-users/{application_user_id}/reactivate`

`HIGH_RISK` (restituye acceso). URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/reactivate`; permiso `application_users:update`; cuerpo `{"version": n}`. Revalida la cuenta en Keycloak y la persona en Party Identity (mismos `422` de la operación 16).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ApplicationUserResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "compras@ejemplo.com",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 21. `GET /application-users/{application_user_id}/user-branches`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`; permiso `user_branches:read`. Parámetros: `status` (`ACTIVE` por defecto), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[UserBranchResponse]`.

`UserBranchResponse`: `id` (`user_branch_id`), `application_user_id`, `branch_id`, `company_id`, `status`, `assigned_at`, `assigned_by` (`sub`), `deactivated_at`, `membership_status`, `branch_status`, `company_status`, `operational_access` (`{"allowed": boolean, "reason": string | null}`, acceso efectivo sin evaluar permisos), `version`, trazabilidad.

```json
{
  "items": [
    {
      "id": "9f0a1b2c-3d4e-4f5a-8b6c-7d8e9f0a1b2c",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "assigned_at": "2026-01-15T15:00:00Z",
      "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "deactivated_at": null,
      "membership_status": "ACTIVE",
      "branch_status": "ACTIVE",
      "company_status": "ACTIVE",
      "operational_access": {"allowed": true, "reason": null},
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T15:00:00Z",
      "updated_at": "2026-01-15T15:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 22. `POST /application-users/{application_user_id}/user-branches`

`HIGH_RISK` (concede acceso operativo a una sucursal). URL `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`; permiso `user_branches:create`. Cuerpo (`UserBranchCreate`): `{"branch_id": "…"}` ([branch_id](../parametros/branch-id.md)). Reglas: la sucursal debe ser de la misma empresa que la membresía (`422 BRANCH_COMPANY_MISMATCH`); membresía, sucursal y empresa `ACTIVE` (`422 MEMBERSHIP_INACTIVE`, `BRANCH_INACTIVE`, `COMPANY_INACTIVE`); no duplicar (`409 DUPLICATE_USER_BRANCH`). `assigned_by` es el `sub` del token. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  }'
```
Respuesta `201`: `UserBranchResponse`.

Ejemplo de respuesta `201` (`UserBranchResponse`; valores ilustrativos):

```json
{
  "id": "e8c5f9de-8af8-4aa7-8f96-536c03dc33ac",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "assigned_at": "2026-10-19T15:04:05Z",
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "deactivated_at": null,
  "membership_status": "ACTIVE",
  "branch_status": "ACTIVE",
  "company_status": "ACTIVE",
  "operational_access": {
    "allowed": true,
    "reason": "Solicitud del cliente"
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 23. `GET /branches/{branch_id}/user-branches`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/user-branches`; permiso `user_branches:read`. Parámetros: `status`, `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/user-branches?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[UserBranchResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_UserBranchResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "assigned_at": "2026-10-19T15:04:05Z",
      "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "deactivated_at": null,
      "membership_status": "ACTIVE",
      "branch_status": "ACTIVE",
      "company_status": "ACTIVE",
      "operational_access": {
        "allowed": true,
        "reason": "Solicitud del cliente"
      },
      "version": 1,
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

### 24. `GET /user-branches/{user_branch_id}`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/user-branches/{user_branch_id}`; permiso `user_branches:read`. `200` con `UserBranchResponse`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/user-branches/fd88f6a7-3e56-466b-8b82-e0b19abfb3df' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`UserBranchResponse`; valores ilustrativos):

```json
{
  "id": "fd88f6a7-3e56-466b-8b82-e0b19abfb3df",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "assigned_at": "2026-10-19T15:04:05Z",
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "deactivated_at": null,
  "membership_status": "ACTIVE",
  "branch_status": "ACTIVE",
  "company_status": "ACTIVE",
  "operational_access": {
    "allowed": true,
    "reason": "Solicitud del cliente"
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 25. `POST /user-branches/{user_branch_id}/deactivate`

`HIGH_RISK` (retira el acceso a la sucursal: `USER_BRANCH_INACTIVE`). URL `https://sio-operational-context-dev.onrender.com/api/v1/user-branches/{user_branch_id}/deactivate`; permiso `user_branches:delete`; cuerpo `{"version": n}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/user-branches/fd88f6a7-3e56-466b-8b82-e0b19abfb3df/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `status: "INACTIVE"` y `deactivated_at`.

Ejemplo de respuesta `200` (`UserBranchResponse`; valores ilustrativos):

```json
{
  "id": "fd88f6a7-3e56-466b-8b82-e0b19abfb3df",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "assigned_at": "2026-10-19T15:04:05Z",
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "deactivated_at": null,
  "membership_status": "ACTIVE",
  "branch_status": "ACTIVE",
  "company_status": "ACTIVE",
  "operational_access": {
    "allowed": true,
    "reason": "Solicitud del cliente"
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 26. `POST /user-branches/{user_branch_id}/reactivate`

`HIGH_RISK`. URL `https://sio-operational-context-dev.onrender.com/api/v1/user-branches/{user_branch_id}/reactivate`; permiso `user_branches:update`; cuerpo `{"version": n}`. Exige membresía, sucursal y empresa `ACTIVE`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/user-branches/fd88f6a7-3e56-466b-8b82-e0b19abfb3df/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`UserBranchResponse`; valores ilustrativos):

```json
{
  "id": "fd88f6a7-3e56-466b-8b82-e0b19abfb3df",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "assigned_at": "2026-10-19T15:04:05Z",
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "deactivated_at": null,
  "membership_status": "ACTIVE",
  "branch_status": "ACTIVE",
  "company_status": "ACTIVE",
  "operational_access": {
    "allowed": true,
    "reason": "Solicitud del cliente"
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 27. `GET /companies/{company_id}/advisor-assignments`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/advisor-assignments`; permiso `company_advisor_assignments:read`. Parámetros: `page`, `page_size`, `status` (`ACTIVE` = vigentes, `INACTIVE` = cerradas; sin valor, todas), `is_primary` (boolean), `person_identity_id` (UUID). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/advisor-assignments?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[AdvisorAssignmentResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_AdvisorAssignmentResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "is_primary": true,
      "status": "ACTIVE",
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "version": 1,
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

`AdvisorAssignmentResponse`: `id` (`assignment_id`), `company_id`, `person_identity_id`, `is_primary`, `status`, `valid_from`, `valid_to` (null si vigente), `assigned_by`, `version`, trazabilidad.

### 28. `POST /companies/{company_id}/advisor-assignments`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/advisor-assignments`; permiso `company_advisor_assignments:create`. Cuerpo (`AdvisorAssignmentCreate`): `person_identity_id` (UUID, obligatorio; persona `ACTIVE` en Party Identity), `is_primary` (boolean, por defecto `true`), `valid_from` (date-time, opcional; por defecto ahora). Reglas: varios asesores vigentes, **uno solo principal** (`409 PRIMARY_ADVISOR_EXISTS`); la misma persona no puede tener dos asignaciones vigentes (`409 DUPLICATE_ADVISOR_ASSIGNMENT`); `422 INVALID_VALIDITY_PERIOD`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/advisor-assignments' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "is_primary": true,
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`AdvisorAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "4af4ba18-a34d-462e-8392-d290e6c4d674",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "is_primary": true,
  "status": "ACTIVE",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 29. `GET /advisor-assignments/{assignment_id}`

`READ`. URL `https://sio-operational-context-dev.onrender.com/api/v1/advisor-assignments/{assignment_id}`; permiso `company_advisor_assignments:read`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/advisor-assignments/93c4899b-7130-4feb-878a-e72c2e3b9d97' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`AdvisorAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "is_primary": true,
  "status": "ACTIVE",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 30. `POST /advisor-assignments/{assignment_id}/close`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/advisor-assignments/{assignment_id}/close`; permiso `company_advisor_assignments:delete`. Cuerpo (`AdvisorCloseRequest`): `version` y `valid_to` (opcional; por defecto ahora; ≥ `valid_from`, si no `422 INVALID_VALIDITY_PERIOD`). Una asignación cerrada es inmutable (no se reabre). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/advisor-assignments/93c4899b-7130-4feb-878a-e72c2e3b9d97/close' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `status: "INACTIVE"` y `valid_to`.

Ejemplo de respuesta `200` (`AdvisorAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "is_primary": true,
  "status": "ACTIVE",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 31. `POST /companies/{company_id}/advisor-assignments/change-primary`

`WRITE`. URL `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/advisor-assignments/change-primary`; permisos `company_advisor_assignments:create` **y** `delete`. Cuerpo (`ChangePrimaryRequest`): `current_assignment_id` (UUID de la asignación principal vigente), `version` (su versión), `person_identity_id` (nueva persona, `ACTIVE`), `effective_at` (date-time, opcional). Cierra la vigente y crea la nueva en una sola transacción. Errores: `409 NO_ACTIVE_PRIMARY_ADVISOR`, `409 PRIMARY_ADVISOR_MISMATCH` (la indicada no es la principal vigente), `409 VERSION_CONFLICT`, `422`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/advisor-assignments/change-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "current_assignment_id": "78fd5a21-6769-49cb-89b8-313ec380c752",
    "version": 1,
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110"
  }'
```
Respuesta `201` (`ChangePrimaryResponse`): `{"closed": AdvisorAssignmentResponse, "created": AdvisorAssignmentResponse}`.

### 32. `GET /me/operational-context`

| | |
|---|---|
| Clasificación | `READ` · la primera llamada tras el login |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Permiso | `perm:operational-context:application_users:read` |
| Parámetros | Ninguno |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`MeOperationalContextResponse`): `keycloak_user_id` y `memberships[]` con `application_user_id`, `company_id`, `company_status`, `status` y `branches[]` (`branch_id`, `user_branch_status`, `branch_status`, `allowed`, `reason`). Ejemplo completo y uso en [company_id](../parametros/company-id.md) y [branch_id](../parametros/branch-id.md). Devuelve también membresías y asignaciones inactivas (con `allowed: false` y su `reason`), para que la interfaz pueda explicarlo. Un usuario sin membresías recibe `memberships: []`.

Ejemplo de respuesta `200` (`MeOperationalContextResponse`; valores ilustrativos):

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "memberships": [
    {
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": [
        {
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "user_branch_status": "ACTIVE",
          "branch_status": "ACTIVE",
          "allowed": true,
          "reason": null
        }
      ]
    }
  ]
}
```

### 33. `GET /operational-access`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-operational-context-dev.onrender.com/api/v1/operational-access` |
| Permiso | `perm:operational-context:application_users:read` |

Parámetros de consulta: `company_id` (UUID), `branch_id` (UUID), `permission` (≤ 255; `perm:{servicio}:{recurso}:{accion}`), `keycloak_user_id` (≤ 255; solo con `platform:lookup`, evalúa a otro usuario). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/operational-access' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`OperationalAccessResponse`): `allowed`, `reason`, `keycloak_user_id`, `company_id`, `branch_id`, `application_user_id`, `permission`. Catálogo de `reason` y ejemplo en [Permisos §6](../guias/permisos.md#6-comprobar-el-acceso-antes-de-actuar).

Ejemplo de respuesta `200` (`OperationalAccessResponse`; valores ilustrativos):

```json
{
  "allowed": true,
  "reason": null,
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "permission": "perm:sales:sales:read"
}
```

Reglas: una denegación funcional responde `200` con `allowed: false`, nunca `403`. Por la vía propia (token del usuario), una empresa o sucursal ajena **o inexistente** responde `USER_NOT_MEMBER` sin revelar más. Por la vía técnica (`platform:lookup` + `keycloak_user_id`), un objetivo inexistente responde `404` y el permiso se evalúa con los roles efectivos del usuario objetivo leídos de Keycloak. Es la operación que invocan Sales, Purchase, Inventory, Commercial Relationship, Audit, Business Reporting y Product Inventory Query para decidir el alcance.

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` «La empresa solicitada no existe.» | UUID inexistente o sin membresía | Comprobar `/me/operational-context` |
| `403 OPERATIONAL_CONTEXT.FORBIDDEN` | Falta el permiso (p. ej. `platform:administer` al crear empresas) | Solo administradores de plataforma |
| `409 …DUPLICATE_BRANCH_CODE` / `DUPLICATE_MEMBERSHIP` / `DUPLICATE_USER_BRANCH` / `DUPLICATE_ORGANIZATION_IDENTITY` | Unicidad | Buscar el registro existente |
| `409 …VERSION_CONFLICT` / `INVALID_STATUS_TRANSITION` | Concurrencia o estado | Recargar |
| `422 …KEYCLOAK_USER_NOT_FOUND` / `KEYCLOAK_USER_DISABLED` / `TECHNICAL_ACCOUNT_NOT_ALLOWED` | La cuenta no existe, está deshabilitada o es técnica | Crear o habilitar la cuenta en Keycloak |
| `422 …PERSON_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_NOT_FOUND` / `_INACTIVE` | Identidad inválida en Party Identity | Crear o reactivar la identidad |
| `422 …GEOGRAPHY_INCOHERENT` / `LOCATION_INACTIVE` / `*_NOT_FOUND` | Ubicación inválida | Usar selectores en cascada de Geography |
| `422 …IMMUTABLE_FIELD` | Se envió un campo inmutable | Quitarlo del cuerpo |
| `503` con `dependency` `keycloak`, `party-identity` o `geography` | Dependencia caída | Reintentar |

## Dependencias

| Servicio | Uso |
|---|---|
| Party Identity | Validar identidades de organización (empresas) y de persona (usuarios, asesores), con el token del usuario |
| Geography | Validar país, división y ciudad activos y coherentes, con el token del usuario |
| Keycloak (Admin API) | Verificar la cuenta al crear o reactivar usuarios operativos y leer roles efectivos en la vía técnica, con la cuenta de servicio del propio Operational Context |
| Audit | Eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 33 |
| Operaciones documentadas | 33 |
| Permisos contrastados con el código | Sí (`api/companies.py`, `branches.py`, `application_users.py`, `user_branches.py`, `advisor_assignments.py`, `operational_access.py`) |
| Esquemas contrastados | Sí (`api/schemas/*.py`, `application/access_scope.py`, `domain/access.py`, `api/errors.py`) |
| Verificado | En asesores, el inicio de vigencia es el valor enviado o el instante actual; nunca puede ser futuro y debe llevar zona horaria |

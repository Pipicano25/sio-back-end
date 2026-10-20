# Party Identity API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Party Identity es el **registro global de identidades**: personas naturales y organizaciones identificadas por país, tipo y número de documento, con sus perfiles de contacto versionados, personas de contacto, sectores económicos y representantes legales. Las empresas de SIO, sus usuarios, los clientes y los proveedores apuntan a estas identidades. Es un registro **compartido por todas las empresas**: antes de crear una identidad hay que buscarla.

## Responsabilidad

- Identidades de personas y organizaciones con validación del número según **reglas de identificación** por país, tipo de parte y sigla (expresión regular, rango de edad).
- Reglas de identificación versionadas (una activa por tipo de parte, país y tipo).
- Perfiles de contacto versionados (correo, teléfono, dirección geográfica validada en Geography), confirmados desde una empresa.
- Personas de contacto, sectores económicos (catálogo jerárquico y asignaciones) y representantes legales de una organización.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-party-identity-dev.onrender.com/api/v1` |
| Salud | `https://sio-party-identity-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-party-identity-dev.onrender.com/docs) · [/openapi.json](https://sio-party-identity-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `PARTY_IDENTITY.*` y `trace_id` |
| Operaciones en el contrato desplegado | 54 (52 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/party-identity-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos `perm:party-identity:{recurso}:{accion}`:

| Recurso | Operaciones | Grupos con lectura (plantilla) | Grupos con escritura |
|---|---|---|---|
| `person_identities` | Personas (3–8) | Todos los grupos (`compras`, `ventas`, `reportes`, `consulta` por recurso; `inventario` **no**) | `administradores`, `supervisores` (salvo `delete`) |
| `organization_identities` | Organizaciones (9–14) | Todos salvo `inventario` | `administradores`, `supervisores` (salvo `delete`) |
| `identification_type_rules` | Reglas (15–20) | Todos salvo `inventario` | `administradores`, `supervisores` (salvo `delete`) |
| `person_contact_profiles` | Perfiles de personas (21–25) | `administradores`, `supervisores`, `compras`, `ventas` | `administradores`, `supervisores` (salvo `delete`) |
| `organization_contact_profiles` | Perfiles de organizaciones (26–30) | Ídem | Ídem |
| `organization_contact_persons` | Personas de contacto (31–37) | `administradores`, `supervisores`, `compras`, `ventas` | Ídem |
| `global_business_sectors` | Catálogo de sectores (38–43) | Todos salvo `inventario` | Ídem |
| `organization_business_sectors` | Sectores de una organización (44–48) | Todos salvo `inventario` | Ídem |
| `organization_legal_representatives` | Representantes legales (49–54) | `administradores`, `supervisores` (`perm:all:all:read`) | `administradores`, `supervisores` (salvo `delete`) |

Acciones: `read` (listar, consultar), `create`, `update` (modificar, reactivar, `set-primary`), `delete` (inactivar, cerrar). Los grupos `reportes` y `consulta` no ven perfiles de contacto ni personas de contacto en la plantilla.

## Alcance de datos

Global: cualquier usuario con el permiso ve todas las identidades, sin membresía. La única excepción es el registro de un perfil de contacto, que exige que el usuario tenga **membresía `ACTIVE` en la empresa** indicada en `confirmed_by_company_id` (verificado en Operational Context con el token del usuario).

## Convenciones comunes

- Listas paginadas (`page` ≥ 1, `page_size` 1–100, por defecto 20). Identidades y sectores devuelven por defecto solo `ACTIVE` (`status=INACTIVE` para las inactivas). Asignaciones (sectores, representantes) usan `state` = `active` (vigentes), `closed`, `all`.
- Escrituras con `version` (≥ 1); desactualizada → `409 PARTY_IDENTITY.VERSION_CONFLICT`. Inactivar algo inactivo o reactivar algo activo → `409 INVALID_STATUS_TRANSITION`.
- Sin borrado físico. Las asignaciones (sectores de organización, representantes) se **cierran** con `valid_to` y no se reabren.
- Modelos con `extra="forbid"`: campos desconocidos → `422`; campos inmutables enviados → `422 IMMUTABLE_FIELD`.
- Direcciones de los perfiles: `country_id`, `administrative_division_id`, `city_id` validados en Geography (`422 COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND`, `LOCATION_INACTIVE`, `GEOGRAPHY_INCOHERENT`, `GEOGRAPHY_PARENT_REQUIRED`).
- `503 DEPENDENCY_UNAVAILABLE` con `dependency` (`database`, `geography`, `operational-context`).

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso (`perm:party-identity:…`) | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | PostgreSQL disponible | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/person-identities` | Listar personas | `person_identities:read` | `READ` | [Ver](#3-get-person-identities) |
| 4 | `POST` | `/person-identities` | Crear persona | `person_identities:create` | `WRITE` | [Ver](#4-post-person-identities) |
| 5 | `GET` | `/person-identities/{person_identity_id}` | Consultar persona | `person_identities:read` | `READ` | [Ver](#5-get-person-identitiesperson_identity_id) |
| 6 | `PUT` | `/person-identities/{person_identity_id}` | Modificar persona | `person_identities:update` | `WRITE` | [Ver](#6-put-person-identitiesperson_identity_id) |
| 7 | `POST` | `/person-identities/{person_identity_id}/deactivate` | Inactivar persona | `person_identities:delete` | `HIGH_RISK` | [Ver](#7-post-person-identitiesperson_identity_iddeactivate) |
| 8 | `POST` | `/person-identities/{person_identity_id}/reactivate` | Reactivar persona | `person_identities:update` | `WRITE` | [Ver](#8-post-person-identitiesperson_identity_idreactivate) |
| 9 | `GET` | `/organization-identities` | Listar organizaciones | `organization_identities:read` | `READ` | [Ver](#9-get-organization-identities) |
| 10 | `POST` | `/organization-identities` | Crear organización | `organization_identities:create` | `WRITE` | [Ver](#10-post-organization-identities) |
| 11 | `GET` | `/organization-identities/{organization_identity_id}` | Consultar organización | `organization_identities:read` | `READ` | [Ver](#11-get-organization-identitiesorganization_identity_id) |
| 12 | `PUT` | `/organization-identities/{organization_identity_id}` | Modificar organización | `organization_identities:update` | `WRITE` | [Ver](#12-put-organization-identitiesorganization_identity_id) |
| 13 | `POST` | `/organization-identities/{organization_identity_id}/deactivate` | Inactivar organización | `organization_identities:delete` | `HIGH_RISK` | [Ver](#13-post-organization-identitiesorganization_identity_iddeactivate) |
| 14 | `POST` | `/organization-identities/{organization_identity_id}/reactivate` | Reactivar organización | `organization_identities:update` | `WRITE` | [Ver](#14-post-organization-identitiesorganization_identity_idreactivate) |
| 15 | `GET` | `/identification-type-rules` | Listar reglas | `identification_type_rules:read` | `READ` | [Ver](#15-get-identification-type-rules) |
| 16 | `POST` | `/identification-type-rules` | Crear regla | `identification_type_rules:create` | `WRITE` | [Ver](#16-post-identification-type-rules) |
| 17 | `GET` | `/identification-type-rules/{rule_id}` | Consultar regla | `identification_type_rules:read` | `READ` | [Ver](#17-get-identification-type-rulesrule_id) |
| 18 | `PUT` | `/identification-type-rules/{rule_id}` | Modificar descripción o ejemplo | `identification_type_rules:update` | `WRITE` | [Ver](#18-put-identification-type-rulesrule_id) |
| 19 | `POST` | `/identification-type-rules/{rule_id}/versions` | Nueva versión de la regla | `identification_type_rules:create` | `HIGH_RISK` | [Ver](#19-post-identification-type-rulesrule_idversions) |
| 20 | `POST` | `/identification-type-rules/{rule_id}/deactivate` | Retirar regla | `identification_type_rules:delete` | `HIGH_RISK` | [Ver](#20-post-identification-type-rulesrule_iddeactivate) |
| 21 | `GET` | `/person-identities/{person_identity_id}/contact-profile` | Perfil vigente de una persona | `person_contact_profiles:read` | `READ` | [Ver](#21-get-person-identitiesperson_identity_idcontact-profile) |
| 22 | `POST` | `/person-identities/{person_identity_id}/contact-profile` | Nueva versión del perfil | `person_contact_profiles:create` | `WRITE` | [Ver](#22-post-person-identitiesperson_identity_idcontact-profile) |
| 23 | `GET` | `/person-identities/{person_identity_id}/contact-profile/versions` | Historial del perfil | `person_contact_profiles:read` | `READ` | [Ver](#23-get-person-identitiesperson_identity_idcontact-profileversions) |
| 24 | `GET` | `/person-contact-profiles/{profile_id}` | Versión por UUID | `person_contact_profiles:read` | `READ` | [Ver](#24-get-person-contact-profilesprofile_id) |
| 25 | `POST` | `/person-identities/{person_identity_id}/contact-profile:close` | Cerrar perfil vigente | `person_contact_profiles:delete` | `WRITE` | [Ver](#25-post-person-identitiesperson_identity_idcontact-profileclose) |
| 26 | `GET` | `/organization-identities/{organization_identity_id}/contact-profile` | Perfil vigente de una organización | `organization_contact_profiles:read` | `READ` | [Ver](#26-get-organization-identitiesorganization_identity_idcontact-profile) |
| 27 | `POST` | `/organization-identities/{organization_identity_id}/contact-profile` | Nueva versión del perfil | `organization_contact_profiles:create` | `WRITE` | [Ver](#27-post-organization-identitiesorganization_identity_idcontact-profile) |
| 28 | `GET` | `/organization-identities/{organization_identity_id}/contact-profile/versions` | Historial del perfil | `organization_contact_profiles:read` | `READ` | [Ver](#28-get-organization-identitiesorganization_identity_idcontact-profileversions) |
| 29 | `GET` | `/organization-contact-profiles/{profile_id}` | Versión por UUID | `organization_contact_profiles:read` | `READ` | [Ver](#29-get-organization-contact-profilesprofile_id) |
| 30 | `POST` | `/organization-identities/{organization_identity_id}/contact-profile:close` | Cerrar perfil vigente | `organization_contact_profiles:delete` | `WRITE` | [Ver](#30-post-organization-identitiesorganization_identity_idcontact-profileclose) |
| 31 | `GET` | `/organization-identities/{organization_identity_id}/contact-persons` | Personas de contacto | `organization_contact_persons:read` | `READ` | [Ver](#31-get-organization-identitiesorganization_identity_idcontact-persons) |
| 32 | `POST` | `/organization-identities/{organization_identity_id}/contact-persons` | Registrar persona de contacto | `organization_contact_persons:create` | `WRITE` | [Ver](#32-post-organization-identitiesorganization_identity_idcontact-persons) |
| 33 | `GET` | `/organization-contact-persons/{contact_id}` | Consultar persona de contacto | `organization_contact_persons:read` | `READ` | [Ver](#33-get-organization-contact-personscontact_id) |
| 34 | `PUT` | `/organization-contact-persons/{contact_id}` | Modificar persona de contacto | `organization_contact_persons:update` | `WRITE` | [Ver](#34-put-organization-contact-personscontact_id) |
| 35 | `POST` | `/organization-contact-persons/{contact_id}:set-primary` | Establecer contacto principal | `organization_contact_persons:update` | `WRITE` | [Ver](#35-post-organization-contact-personscontact_idset-primary) |
| 36 | `POST` | `/organization-contact-persons/{contact_id}:deactivate` | Inactivar contacto | `organization_contact_persons:delete` | `WRITE` | [Ver](#36-post-organization-contact-personscontact_iddeactivate) |
| 37 | `POST` | `/organization-contact-persons/{contact_id}:reactivate` | Reactivar contacto | `organization_contact_persons:update` | `WRITE` | [Ver](#37-post-organization-contact-personscontact_idreactivate) |
| 38 | `GET` | `/global-business-sectors` | Listar sectores | `global_business_sectors:read` | `READ` | [Ver](#38-get-global-business-sectors) |
| 39 | `POST` | `/global-business-sectors` | Crear sector | `global_business_sectors:create` | `WRITE` | [Ver](#39-post-global-business-sectors) |
| 40 | `GET` | `/global-business-sectors/{sector_id}` | Consultar sector | `global_business_sectors:read` | `READ` | [Ver](#40-get-global-business-sectorssector_id) |
| 41 | `PUT` | `/global-business-sectors/{sector_id}` | Modificar sector | `global_business_sectors:update` | `WRITE` | [Ver](#41-put-global-business-sectorssector_id) |
| 42 | `POST` | `/global-business-sectors/{sector_id}:deactivate` | Inactivar sector | `global_business_sectors:delete` | `WRITE` | [Ver](#42-post-global-business-sectorssector_iddeactivate) |
| 43 | `POST` | `/global-business-sectors/{sector_id}:reactivate` | Reactivar sector | `global_business_sectors:update` | `WRITE` | [Ver](#43-post-global-business-sectorssector_idreactivate) |
| 44 | `GET` | `/organization-identities/{organization_identity_id}/business-sectors` | Sectores de una organización | `organization_business_sectors:read` | `READ` | [Ver](#44-get-organization-identitiesorganization_identity_idbusiness-sectors) |
| 45 | `POST` | `/organization-identities/{organization_identity_id}/business-sectors` | Asignar sector | `organization_business_sectors:create` | `WRITE` | [Ver](#45-post-organization-identitiesorganization_identity_idbusiness-sectors) |
| 46 | `GET` | `/organization-business-sectors/{assignment_id}` | Consultar asignación | `organization_business_sectors:read` | `READ` | [Ver](#46-get-organization-business-sectorsassignment_id) |
| 47 | `POST` | `/organization-business-sectors/{assignment_id}:set-primary` | Sector principal | `organization_business_sectors:update` | `WRITE` | [Ver](#47-post-organization-business-sectorsassignment_idset-primary) |
| 48 | `POST` | `/organization-business-sectors/{assignment_id}:close` | Cerrar asignación | `organization_business_sectors:delete` | `WRITE` | [Ver](#48-post-organization-business-sectorsassignment_idclose) |
| 49 | `GET` | `/organization-identities/{organization_identity_id}/legal-representatives` | Representantes legales | `organization_legal_representatives:read` | `READ` | [Ver](#49-get-organization-identitiesorganization_identity_idlegal-representatives) |
| 50 | `POST` | `/organization-identities/{organization_identity_id}/legal-representatives` | Registrar representante | `organization_legal_representatives:create` | `WRITE` | [Ver](#50-post-organization-identitiesorganization_identity_idlegal-representatives) |
| 51 | `POST` | `/organization-identities/{organization_identity_id}/legal-representatives:set-primary` | Establecer representante PRIMARY | `organization_legal_representatives:create` | `WRITE` | [Ver](#51-post-organization-identitiesorganization_identity_idlegal-representativesset-primary) |
| 52 | `GET` | `/organization-legal-representatives/{representative_id}` | Consultar representante | `organization_legal_representatives:read` | `READ` | [Ver](#52-get-organization-legal-representativesrepresentative_id) |
| 53 | `PUT` | `/organization-legal-representatives/{representative_id}` | Modificar cargo o referencia | `organization_legal_representatives:update` | `WRITE` | [Ver](#53-put-organization-legal-representativesrepresentative_id) |
| 54 | `POST` | `/organization-legal-representatives/{representative_id}:close` | Cerrar representación | `organization_legal_representatives:delete` | `WRITE` | [Ver](#54-post-organization-legal-representativesrepresentative_idclose) |

## Validación de números de identificación

Al crear o modificar una identidad, el servicio busca las **reglas activas** del tipo de parte (`PERSON` u `ORGANIZATION`), el país y la sigla (`identification_type`, normalizado a mayúsculas). Si existen reglas para esa sigla, el número (normalizado) debe cumplir la expresión regular de al menos una; si no, `422 INVALID_IDENTIFICATION_NUMBER` con la descripción de las reglas. Si la regla define edades (`min_age_years`, `max_age_years`), `birth_date` es obligatoria (`422 BIRTH_DATE_REQUIRED`) y debe estar en rango (`422 AGE_OUT_OF_RANGE`); una fecha futura → `422 BIRTH_DATE_IN_FUTURE`. Sin reglas para la sigla solo aplican las validaciones básicas. Un país inexistente en Geography → `422 COUNTRY_NOT_FOUND`. La combinación país + tipo + número es **única** (`409 DUPLICATE_IDENTIFICATION`). Las siglas válidas por país se consultan con la operación 15.

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-party-identity-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-party-identity-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si PostgreSQL no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/health/ready'
```

### 3. `GET /person-identities`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities`; permiso `person_identities:read`. Parámetros: `page`, `page_size`, `search` (≤ 120; identificación o nombres), `identification_country_id` (UUID), `identification_type` (sigla), `verification_status` (`UNVERIFIED`, `VERIFIED`, `SUSPENDED`), `status` (`ACTIVE` por defecto, `INACTIVE`). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PersonIdentityResponse]`. Ejemplo completo en [person_identity_id](../parametros/person-identity-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_PersonIdentityResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "CC",
      "identification_number": "1012345678",
      "first_name": "Ana",
      "middle_name": null,
      "last_name": "Pérez",
      "second_last_name": null,
      "birth_date": null,
      "verification_status": "VERIFIED",
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

`PersonIdentityResponse`: `id`, `identification_country_id`, `identification_type`, `identification_number`, `first_name`, `middle_name`, `last_name`, `second_last_name`, `birth_date`, `verification_status`, `status`, `version`, trazabilidad.

### 4. `POST /person-identities`

| | |
|---|---|
| Clasificación | `WRITE` · crea un registro global compartido |
| URL | `https://sio-party-identity-dev.onrender.com/api/v1/person-identities` |
| Permiso | `perm:party-identity:person_identities:create` |

Cuerpo (`PersonIdentityCreate`):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `identification_country_id` | UUID | Sí | País activo en Geography | [Geography](geography.md), `GET /global-countries` |
| `identification_type` | string | Sí | 1–40; sigla (p. ej. `CC`); se normaliza a mayúsculas | Operación 15 (`sigla`) |
| `identification_number` | string | Sí | 1–40; debe cumplir la regla activa | — |
| `first_name`, `last_name` | string | Sí | 1–100 | — |
| `middle_name`, `second_last_name` | string \| null | No | ≤ 100 | — |
| `birth_date` | date \| null | Según la regla | No futura; en rango de edad | — |
| `verification_status` | enum | No | `UNVERIFIED` (por defecto), `VERIFIED`, `SUSPENDED` | — |

```json
{
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "last_name": "Pérez",
  "birth_date": "1990-05-20"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "identification_number": "1012345678",
    "first_name": "Ana",
    "last_name": "Pérez",
    "birth_date": "1990-05-20"
  }'
```

Respuesta `201`: `PersonIdentityResponse` (`status` `ACTIVE`, `version` 1); su `id` es el [person_identity_id](../parametros/person-identity-id.md). Errores: `409 DUPLICATE_IDENTIFICATION`, `422 INVALID_IDENTIFICATION_NUMBER` / `BIRTH_DATE_REQUIRED` / `AGE_OUT_OF_RANGE` / `BIRTH_DATE_IN_FUTURE` / `COUNTRY_NOT_FOUND`, `503` (`geography`). Busque antes de crear (operación 3 con `search`).

Ejemplo de respuesta `201` (`PersonIdentityResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 5. `GET /person-identities/{person_identity_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}`. Persona en cualquier estado; `404 NOT_FOUND`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PersonIdentityResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 6. `PUT /person-identities/{person_identity_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}`; permiso `person_identities:update`. Cuerpo (`PersonIdentityUpdate`): los campos de la operación 4 con `verification_status` **obligatorio** más `version`. Reemplazo completo; sin cambios no escribe. Cambiar país, tipo o número vuelve a validar la regla y la unicidad. Errores: `409 VERSION_CONFLICT`, `409 DUPLICATE_IDENTIFICATION`, `422`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "identification_number": "1012345678",
    "first_name": "Ana",
    "last_name": "Pérez",
    "verification_status": "VERIFIED",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PersonIdentityResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 7. `POST /person-identities/{person_identity_id}/deactivate`

`HIGH_RISK`: una persona inactiva deja de ser utilizable como cliente nuevo (`422 PERSON_IDENTITY_INACTIVE` en Commercial Relationship), como usuario operativo nuevo (Operational Context) y para nuevos perfiles de contacto. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/deactivate`; permiso `person_identities:delete`; cuerpo `{"version": n}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `status: "INACTIVE"`; `409 INVALID_STATUS_TRANSITION`.

Ejemplo de respuesta `200` (`PersonIdentityResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 8. `POST /person-identities/{person_identity_id}/reactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/reactivate`; permiso `person_identities:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PersonIdentityResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": null,
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 9. `GET /organization-identities`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities`; permiso `organization_identities:read`. Parámetros: `page`, `page_size`, `search` (≤ 120; identificación o nombre), `country_id`, `identification_type`, `registration_status` (≤ 30), `status`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[OrganizationIdentityResponse]`. Ejemplo completo en [organization_identity_id](../parametros/organization-identity-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_OrganizationIdentityResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "NIT",
      "identification_number": "900123456",
      "legal_name": "Droguería La Economía S.A.S.",
      "trade_name": null,
      "organization_type": "SAS",
      "registration_status": "VIGENTE",
      "website": null,
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

`OrganizationIdentityResponse`: `id`, `country_id`, `identification_type`, `identification_number`, `legal_name`, `trade_name`, `organization_type`, `registration_status`, `website`, `status`, `version`, trazabilidad.

### 10. `POST /organization-identities`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities`; permiso `organization_identities:create`. Cuerpo (`OrganizationIdentityCreate`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `country_id` | UUID | Sí | País activo en Geography |
| `identification_type` | string | Sí | 1–40; sigla (p. ej. `NIT`) |
| `identification_number` | string | Sí | 1–40; regla activa de `ORGANIZATION` |
| `legal_name` | string | Sí | 1–200 |
| `trade_name` | string \| null | No | ≤ 200 |
| `organization_type` | string \| null | No | ≤ 40 |
| `registration_status` | string \| null | No | ≤ 30 |
| `website` | string \| null | No | ≤ 300 |

```json
{
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456-7",
  "legal_name": "Distribuidora Ejemplo S.A.S.",
  "trade_name": "DistriEjemplo"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "NIT",
    "identification_number": "900123456-7",
    "legal_name": "Distribuidora Ejemplo S.A.S.",
    "trade_name": "DistriEjemplo"
  }'
```

Respuesta `201`; errores como en la operación 4 (`DUPLICATE_IDENTIFICATION`, `INVALID_IDENTIFICATION_NUMBER`, `COUNTRY_NOT_FOUND`).

Ejemplo de respuesta `201` (`OrganizationIdentityResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 11. `GET /organization-identities/{organization_identity_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`. Cualquier estado; `404`. Es la consulta para mostrar la **razón social de una empresa** de la plataforma (`legal_name`).

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`OrganizationIdentityResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 12. `PUT /organization-identities/{organization_identity_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`; permiso `organization_identities:update`. Cuerpo (`OrganizationIdentityUpdate`): campos de la operación 10 más `version`. Reemplazo completo; sin cambios no escribe.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "NIT",
    "identification_number": "900123456",
    "legal_name": "Droguería La Economía S.A.S.",
    "organization_type": "SAS",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationIdentityResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 13. `POST /organization-identities/{organization_identity_id}/deactivate`

`HIGH_RISK`: una organización inactiva deja de ser utilizable para nuevos proveedores, clientes organización y empresas. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/deactivate`; permiso `organization_identities:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationIdentityResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 14. `POST /organization-identities/{organization_identity_id}/reactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/reactivate`; permiso `organization_identities:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationIdentityResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": null,
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null,
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 15. `GET /identification-type-rules`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules`; permiso `identification_type_rules:read`. Parámetros: `page`, `page_size`, `party_kind` (`PERSON` \| `ORGANIZATION`), `country_id`, `identification_type`, `sigla`, `is_active`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[IdentificationTypeRuleResponse]`.

`IdentificationTypeRuleResponse`: `id`, `party_kind`, `country_id`, `identification_type`, `sigla` (≤ 10; lo que el usuario escribe en `identification_type` de las identidades), `number_pattern` (expresión regular), `number_pattern_description`, `example_value`, `min_age_years`, `max_age_years`, `is_active`, `valid_from`, `valid_to`, `version`, trazabilidad. Úsalo para poblar el selector de tipo de documento por país y validar el número en la interfaz antes de enviar.

```json
{
  "items": [
    {
      "id": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b",
      "party_kind": "PERSON",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "CC",
      "sigla": "CC",
      "number_pattern": "^[0-9]{6,10}$",
      "number_pattern_description": "Cédula de ciudadanía: de 6 a 10 dígitos.",
      "example_value": "1012345678",
      "min_age_years": 18,
      "max_age_years": null,
      "is_active": true,
      "valid_from": "2025-10-01T00:00:00Z",
      "valid_to": null,
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 16. `POST /identification-type-rules`

`WRITE` (catálogo global). URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules`; permiso `identification_type_rules:create`. Cuerpo (`IdentificationTypeRuleCreate`): `party_kind` (enum, obligatorio), `country_id` (UUID), `identification_type` (1–40), `sigla` (1–10), `number_pattern` (1–300, expresión regular válida: `422 INVALID_NUMBER_PATTERN`), `number_pattern_description` (1–1000), `example_value` (≤ 40; debe cumplir el patrón: `422 EXAMPLE_DOES_NOT_MATCH_PATTERN`), `min_age_years`, `max_age_years` (0–150; `422 INVALID_AGE_RANGE`), `valid_from`, `valid_to` (date-time; `422 INVALID_VALIDITY_RANGE`). Una sola regla activa por tipo de parte, país y tipo (`409 DUPLICATE_ACTIVE_RULE`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "party_kind": "PERSON",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "sigla": "CC",
    "number_pattern": "^[0-9]{6,10}$",
    "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
    "min_age_years": 18,
    "max_age_years": 120,
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`IdentificationTypeRuleResponse`; valores ilustrativos):

```json
{
  "id": "c5acc2bf-70a0-4825-81b0-9eb60c5f2435",
  "party_kind": "PERSON",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "sigla": "CC",
  "number_pattern": "^[0-9]{6,10}$",
  "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
  "example_value": "1012345678",
  "min_age_years": 18,
  "max_age_years": 120,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 17. `GET /identification-type-rules/{rule_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/{rule_id}`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/e1150e65-5bbd-4863-8748-e47a8a1e70b8' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`IdentificationTypeRuleResponse`; valores ilustrativos):

```json
{
  "id": "e1150e65-5bbd-4863-8748-e47a8a1e70b8",
  "party_kind": "PERSON",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "sigla": "CC",
  "number_pattern": "^[0-9]{6,10}$",
  "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
  "example_value": "1012345678",
  "min_age_years": 18,
  "max_age_years": 120,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 18. `PUT /identification-type-rules/{rule_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/{rule_id}`; permiso `identification_type_rules:update`. Cuerpo (`IdentificationTypeRuleUpdate`): `number_pattern_description` (obligatorio), `example_value`, `version`. Los demás campos (`party_kind`, `country_id`, `identification_type`, `sigla`, `number_pattern`, edades) son inmutables aquí: enviarlos → `422 RULE_CHANGE_REQUIRES_NEW_VERSION` («El patrón y las edades de una regla no se modifican en sitio; cree una nueva versión de la regla.») o `IMMUTABLE_FIELD`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/e1150e65-5bbd-4863-8748-e47a8a1e70b8' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
    "version": 1,
    "party_kind": "PERSON",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "sigla": "CC",
    "number_pattern": "^[0-9]{6,10}$",
    "min_age_years": 18,
    "max_age_years": 120
  }'
```

Ejemplo de respuesta `200` (`IdentificationTypeRuleResponse`; valores ilustrativos):

```json
{
  "id": "e1150e65-5bbd-4863-8748-e47a8a1e70b8",
  "party_kind": "PERSON",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "sigla": "CC",
  "number_pattern": "^[0-9]{6,10}$",
  "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
  "example_value": "1012345678",
  "min_age_years": 18,
  "max_age_years": 120,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 19. `POST /identification-type-rules/{rule_id}/versions`

`HIGH_RISK`: cambia cómo se validan los números de identificación de todas las empresas a partir de ahora. URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/{rule_id}/versions`; permiso `identification_type_rules:create`. Cuerpo (`IdentificationTypeRuleVersionCreate`): `number_pattern`, `number_pattern_description` (obligatorios), `example_value`, `min_age_years`, `max_age_years`, `version` (de la regla vigente). Cierra la regla vigente (`valid_to`, `is_active: false`) y crea la sucesora. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/e1150e65-5bbd-4863-8748-e47a8a1e70b8/versions' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "number_pattern": "^[0-9]{6,10}$",
    "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
    "min_age_years": 18,
    "max_age_years": 120,
    "version": 1
  }'
```
Respuesta `201` con la nueva regla. Las identidades existentes no se revalidan.

Ejemplo de respuesta `201` (`IdentificationTypeRuleResponse`; valores ilustrativos):

```json
{
  "id": "e1150e65-5bbd-4863-8748-e47a8a1e70b8",
  "party_kind": "PERSON",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "sigla": "CC",
  "number_pattern": "^[0-9]{6,10}$",
  "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
  "example_value": "1012345678",
  "min_age_years": 18,
  "max_age_years": 120,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 20. `POST /identification-type-rules/{rule_id}/deactivate`

`HIGH_RISK`: sin regla activa para una sigla solo aplican las validaciones básicas. URL `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/{rule_id}/deactivate`; permiso `identification_type_rules:delete`; cuerpo `{"version": n}`. La regla queda histórica.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules/e1150e65-5bbd-4863-8748-e47a8a1e70b8/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`IdentificationTypeRuleResponse`; valores ilustrativos):

```json
{
  "id": "e1150e65-5bbd-4863-8748-e47a8a1e70b8",
  "party_kind": "PERSON",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "sigla": "CC",
  "number_pattern": "^[0-9]{6,10}$",
  "number_pattern_description": "Prefijo, separador y número con ceros a la izquierda",
  "example_value": "1012345678",
  "min_age_years": 18,
  "max_age_years": 120,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 21. `GET /person-identities/{person_identity_id}/contact-profile`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile`; permiso `person_contact_profiles:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`PersonContactProfileResponse`): `id` (`profile_id`), `person_identity_id`, `email`, `phone`, `address_line`, `country_id`, `administrative_division_id`, `city_id`, `postal_code`, `is_active`, `valid_from`, `valid_to`, `confirmed_by_company_id`, `confirmed_by_user_id`, `version`, trazabilidad. `404 CONTACT_PROFILE_NOT_FOUND` si no hay perfil vigente.

Ejemplo de respuesta `200` (`PersonContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "74425284-85e7-4e98-8c8c-76979eb4ad58",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110"
}
```

### 22. `POST /person-identities/{person_identity_id}/contact-profile`

| | |
|---|---|
| Clasificación | `WRITE` · crea una versión nueva del perfil y cierra la vigente |
| URL | `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile` |
| Permiso | `perm:party-identity:person_contact_profiles:create` |
| Alcance | El usuario debe tener membresía `ACTIVE` en `confirmed_by_company_id` |

Cuerpo (`ContactProfileCreate`):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `email` | string \| null | No | ≤ 254; patrón `^[^@\s]+@[^@\s]+\.[^@\s]+$` | — |
| `phone` | string \| null | No | ≤ 40; dígitos, espacios, `+`, `-`, `(`, `)` | — |
| `address_line` | string \| null | No | — | — |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | No | Coherentes y activos en Geography; división o ciudad exigen país | [Geography](geography.md) |
| `postal_code` | string \| null | No | ≤ 20 | — |
| `confirmed_by_company_id` | UUID | Sí | Empresa `ACTIVE` en la que el usuario tiene membresía (`422 COMPANY_NOT_FOUND`, `COMPANY_INACTIVE`, `CONFIRMATION_MEMBERSHIP_INVALID`) | [company_id](../parametros/company-id.md) |
| `version` | integer \| null | Si existe perfil vigente | Versión del vigente; se ignora si no hay | Operación 21 |

```json
{
  "email": "ana.perez@ejemplo.test",
  "phone": "+57 300 000 0000",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 1
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "ana.perez@ejemplo.test",
    "phone": "+57 300 000 0000",
    "address_line": "Calle 10 # 5-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": 1
  }'
```

Respuestas: `201` con la versión nueva (la anterior queda con `valid_to` e `is_active: false`); `200` sin cuerpo si la solicitud es idéntica a la vigente; `422 PERSON_IDENTITY_INACTIVE`; `409 VERSION_CONFLICT`; `422` de geografía; `503` (`geography`, `operational-context`). Orden verificado: identidad `ACTIVE` → versión → no-op → geografía (solo si cambió) → membresía en Operational Context → escritura.

### 23. `GET /person-identities/{person_identity_id}/contact-profile/versions`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile/versions`; `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile/versions?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PersonContactProfileResponse]` con todas las versiones.

Ejemplo de respuesta `200` (`PaginatedResponse_PersonContactProfileResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "email": "ana.perez@ejemplo.com",
      "phone": "+57 300 123 4567",
      "address_line": "Calle 10 # 5-20",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": null,
      "is_active": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
      "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 24. `GET /person-contact-profiles/{profile_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-contact-profiles/{profile_id}`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-contact-profiles/83a0eb3f-0729-43a8-8f64-a340e9e89003' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PersonContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "83a0eb3f-0729-43a8-8f64-a340e9e89003",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110"
}
```

### 25. `POST /person-identities/{person_identity_id}/contact-profile:close`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile:close`; permiso `person_contact_profiles:delete`. Cuerpo (`ContactProfileClose`): `{"version": n}` del vigente. Cierra sin reemplazo. `409 CONTACT_PROFILE_ALREADY_CLOSED`; `404 CONTACT_PROFILE_NOT_FOUND`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile:close' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PersonContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110"
}
```

### 26. `GET /organization-identities/{organization_identity_id}/contact-profile`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile`; permiso `organization_contact_profiles:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-profile' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`OrganizationContactProfileResponse`): mismos campos que el de persona con `organization_identity_id`.

Ejemplo de respuesta `200` (`OrganizationContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "3ff72d45-964e-440a-8400-715d200bea1b",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
}
```

### 27. `POST /organization-identities/{organization_identity_id}/contact-profile`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile`; permiso `organization_contact_profiles:create`. Cuerpo `ContactProfileCreate` y reglas idénticas a la operación 22 (`422 ORGANIZATION_IDENTITY_INACTIVE` si la organización está inactiva).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-profile' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "ana.perez@ejemplo.com",
    "phone": "+57 300 123 4567",
    "address_line": "Calle 10 # 5-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": 1
  }'
```

Ejemplo de respuesta `201` (`OrganizationContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "21a937f3-5707-49e5-80d6-e3d460726eb9",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
}
```

### 28. `GET /organization-identities/{organization_identity_id}/contact-profile/versions`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile/versions`; `page`, `page_size`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-profile/versions?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_OrganizationContactProfileResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "email": "ana.perez@ejemplo.com",
      "phone": "+57 300 123 4567",
      "address_line": "Calle 10 # 5-20",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": null,
      "is_active": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
      "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 29. `GET /organization-contact-profiles/{profile_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-profiles/{profile_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-profiles/83a0eb3f-0729-43a8-8f64-a340e9e89003' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`OrganizationContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "83a0eb3f-0729-43a8-8f64-a340e9e89003",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
}
```

### 30. `POST /organization-identities/{organization_identity_id}/contact-profile:close`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile:close`; permiso `organization_contact_profiles:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-profile:close' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationContactProfileResponse`; valores ilustrativos):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "confirmed_by_company_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
}
```

### 31. `GET /organization-identities/{organization_identity_id}/contact-persons`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons`; permiso `organization_contact_persons:read`. Parámetros: `is_active` (boolean, `true` por defecto), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-persons?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[ContactPersonResponse]` con `id` (`contact_id`), `organization_identity_id`, `person_identity_id` (opcional), `position`, `email`, `phone`, `is_primary`, `is_active`, `version`, trazabilidad. El `id` del contacto principal es el que Commercial Relationship acepta como `preferred_contact_person_id`.

Ejemplo de respuesta `200` (`PaginatedResponse_ContactPersonResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "position": "Gerente de compras",
      "email": "ana.perez@ejemplo.com",
      "phone": "+57 300 123 4567",
      "is_primary": true,
      "is_active": true,
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

### 32. `POST /organization-identities/{organization_identity_id}/contact-persons`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons`; permiso `organization_contact_persons:create`. Cuerpo (`ContactPersonCreate`): `person_identity_id` (UUID \| null; [persona](../parametros/person-identity-id.md) activa), `position` (≤ 120), `email` (≤ 254, patrón), `phone` (≤ 40, patrón), `is_primary` (boolean, `false`). Reglas: `409 DUPLICATE_ACTIVE_CONTACT_PERSON` (misma persona activa dos veces), `409 PRIMARY_CONTACT_CONFLICT` si ya hay principal («use set-primary para cambiarlo»), `422 ORGANIZATION_IDENTITY_INACTIVE`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-persons' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "position": "Gerente de compras",
    "email": "ana.perez@ejemplo.com",
    "phone": "+57 300 123 4567",
    "is_primary": true
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "5a2404fc-5655-496d-833f-9f8daf44d40c",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 33. `GET /organization-contact-persons/{contact_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/{contact_id}`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/6d82f13d-88a5-4659-8ce9-132a4fcdbf6d' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "6d82f13d-88a5-4659-8ce9-132a4fcdbf6d",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 34. `PUT /organization-contact-persons/{contact_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/{contact_id}`; permiso `organization_contact_persons:update`. Cuerpo (`ContactPersonUpdate`): `person_identity_id`, `position`, `email`, `phone`, `version`. `is_primary` no se modifica aquí (usar la operación 35) y `organization_identity_id` es inmutable (`422 IMMUTABLE_FIELD`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/6d82f13d-88a5-4659-8ce9-132a4fcdbf6d' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "position": "Gerente de compras",
    "email": "ana.perez@ejemplo.com",
    "phone": "+57 300 123 4567",
    "version": 1,
    "is_primary": true,
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111"
  }'
```

Ejemplo de respuesta `200` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "6d82f13d-88a5-4659-8ce9-132a4fcdbf6d",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 35. `POST /organization-contact-persons/{contact_id}:set-primary`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/{contact_id}:set-primary`; permiso `organization_contact_persons:update`; cuerpo `{"version": n}`. Atómico: el contacto pasa a principal y el anterior deja de serlo. `422 INVALID_PRIMARY_CONTACT` si el contacto está inactivo.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/6d82f13d-88a5-4659-8ce9-132a4fcdbf6d:set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "6d82f13d-88a5-4659-8ce9-132a4fcdbf6d",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 36. `POST /organization-contact-persons/{contact_id}:deactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/{contact_id}:deactivate`; permiso `organization_contact_persons:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/6d82f13d-88a5-4659-8ce9-132a4fcdbf6d:deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "6d82f13d-88a5-4659-8ce9-132a4fcdbf6d",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 37. `POST /organization-contact-persons/{contact_id}:reactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/{contact_id}:reactivate`; permiso `organization_contact_persons:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-contact-persons/6d82f13d-88a5-4659-8ce9-132a4fcdbf6d:reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ContactPersonResponse`; valores ilustrativos):

```json
{
  "id": "6d82f13d-88a5-4659-8ce9-132a4fcdbf6d",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "position": "Gerente de compras",
  "email": "ana.perez@ejemplo.com",
  "phone": "+57 300 123 4567",
  "is_primary": true,
  "is_active": true,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 38. `GET /global-business-sectors`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors`; permiso `global_business_sectors:read`. Parámetros: `classification_system` (≤ 30, p. ej. `CIIU`), `code` (≤ 40), `parent_sector_id` (UUID), `level_root` (boolean; solo sectores sin padre), `status` (`ACTIVE` por defecto), `search` (≤ 255), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[BusinessSectorResponse]` (`id`, `parent_sector_id`, `classification_system`, `code`, `name`, `description`, `status`, `version`, trazabilidad). Para un árbol, pida `level_root=true` y después por `parent_sector_id`.

Ejemplo de respuesta `200` (`PaginatedResponse_BusinessSectorResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "parent_sector_id": null,
      "classification_system": "CIIU",
      "code": "4773",
      "name": "Comercio al por menor de productos farmacéuticos",
      "description": "Descripción ilustrativa",
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

### 39. `POST /global-business-sectors`

`WRITE` (catálogo global). URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors`; permiso `global_business_sectors:create`. Cuerpo (`BusinessSectorCreate`): `classification_system` (1–30), `code` (1–40; único por sistema: `409 DUPLICATE_SECTOR_CODE`), `name` (1–255), `description`, `parent_sector_id` (debe existir, estar activo, ser del mismo sistema y no formar ciclos: `422 INVALID_SECTOR_HIERARCHY`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "classification_system": "CIIU",
    "code": "4773",
    "name": "Comercio al por menor de productos farmacéuticos",
    "description": "Descripción ilustrativa"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`BusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "144a3595-0ff6-45b0-8464-d87a643534e5",
  "parent_sector_id": null,
  "classification_system": "CIIU",
  "code": "4773",
  "name": "Comercio al por menor de productos farmacéuticos",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 40. `GET /global-business-sectors/{sector_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/{sector_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/5b1d2adf-4905-4a54-8549-2026e5fc0d69' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`BusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "5b1d2adf-4905-4a54-8549-2026e5fc0d69",
  "parent_sector_id": null,
  "classification_system": "CIIU",
  "code": "4773",
  "name": "Comercio al por menor de productos farmacéuticos",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 41. `PUT /global-business-sectors/{sector_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/{sector_id}`; permiso `global_business_sectors:update`. Cuerpo (`BusinessSectorUpdate`): `name` (obligatorio), `description`, `parent_sector_id`, `version`. `classification_system` y `code` son inmutables (`422 IMMUTABLE_FIELD`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/5b1d2adf-4905-4a54-8549-2026e5fc0d69' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Comercio al por menor de productos farmacéuticos",
    "description": "Descripción ilustrativa",
    "version": 1,
    "classification_system": "ATC",
    "code": "4773"
  }'
```

Ejemplo de respuesta `200` (`BusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "5b1d2adf-4905-4a54-8549-2026e5fc0d69",
  "parent_sector_id": null,
  "classification_system": "ATC",
  "code": "4773",
  "name": "Comercio al por menor de productos farmacéuticos",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 42. `POST /global-business-sectors/{sector_id}:deactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/{sector_id}:deactivate`; permiso `global_business_sectors:delete`; cuerpo `{"version": n}`. Sin cascada: con hijos activos → `409 SECTOR_HAS_ACTIVE_CHILDREN`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/5b1d2adf-4905-4a54-8549-2026e5fc0d69:deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "5b1d2adf-4905-4a54-8549-2026e5fc0d69",
  "parent_sector_id": null,
  "classification_system": "CIIU",
  "code": "4773",
  "name": "Comercio al por menor de productos farmacéuticos",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 43. `POST /global-business-sectors/{sector_id}:reactivate`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/{sector_id}:reactivate`; permiso `global_business_sectors:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/global-business-sectors/5b1d2adf-4905-4a54-8549-2026e5fc0d69:reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "5b1d2adf-4905-4a54-8549-2026e5fc0d69",
  "parent_sector_id": null,
  "classification_system": "CIIU",
  "code": "4773",
  "name": "Comercio al por menor de productos farmacéuticos",
  "description": "Descripción ilustrativa",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 44. `GET /organization-identities/{organization_identity_id}/business-sectors`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/business-sectors`; permiso `organization_business_sectors:read`. Parámetros: `state` (`active` por defecto, `closed`, `all`), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/business-sectors?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[OrganizationBusinessSectorResponse]` (`id` = `assignment_id`, `organization_identity_id`, `global_business_sector_id`, `is_primary`, `is_active`, `valid_from`, `valid_to`, `version`, trazabilidad).

Ejemplo de respuesta `200` (`PaginatedResponse_OrganizationBusinessSectorResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
      "is_primary": true,
      "is_active": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
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

### 45. `POST /organization-identities/{organization_identity_id}/business-sectors`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/business-sectors`; permiso `organization_business_sectors:create`. Cuerpo (`OrganizationBusinessSectorCreate`): `global_business_sector_id` (UUID, sector `ACTIVE`: `422 SECTOR_INACTIVE`), `is_primary` (`false`), `valid_from` (opcional). Reglas: `409 DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT`, `409 PRIMARY_SECTOR_CONFLICT` (ya hay principal; use set-primary). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/business-sectors' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
    "is_primary": true,
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`OrganizationBusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "8033f725-db6a-4a7c-8d3a-494f3b6f5245",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 46. `GET /organization-business-sectors/{assignment_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/{assignment_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/93c4899b-7130-4feb-878a-e72c2e3b9d97' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`OrganizationBusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 47. `POST /organization-business-sectors/{assignment_id}:set-primary`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/{assignment_id}:set-primary`; permiso `organization_business_sectors:update`; cuerpo `{"version": n}`. Atómico. `422 INVALID_PRIMARY_SECTOR` si la asignación está cerrada.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/93c4899b-7130-4feb-878a-e72c2e3b9d97:set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationBusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 48. `POST /organization-business-sectors/{assignment_id}:close`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/{assignment_id}:close`; permiso `organization_business_sectors:delete`; cuerpo `{"version": n}`. Cierra con `valid_to`; no se reactiva.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-business-sectors/93c4899b-7130-4feb-878a-e72c2e3b9d97:close' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OrganizationBusinessSectorResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "global_business_sector_id": "d129cf82-f695-43b0-8c79-ecf09ddbc121",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 49. `GET /organization-identities/{organization_identity_id}/legal-representatives`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/legal-representatives`; permiso `organization_legal_representatives:read`. Parámetros: `state` (`active`, `closed`, `all`), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/legal-representatives?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[LegalRepresentativeResponse]` (`id` = `representative_id`, `organization_identity_id`, `person_identity_id`, `representative_type` (`PRIMARY`, `ALTERNATE`, `OTHER`), `position`, `is_primary`, `is_active`, `valid_from`, `valid_to`, `source_document_reference`, `version`, trazabilidad).

Ejemplo de respuesta `200` (`PaginatedResponse_LegalRepresentativeResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "representative_type": "PRIMARY",
      "position": "Representante legal",
      "is_primary": true,
      "is_active": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "source_document_reference": null,
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

### 50. `POST /organization-identities/{organization_identity_id}/legal-representatives`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/legal-representatives`; permiso `organization_legal_representatives:create`. Cuerpo (`LegalRepresentativeCreate`): `person_identity_id` (UUID, obligatorio; persona activa), `representative_type` (enum, obligatorio), `position` (≤ 120), `valid_from`, `source_document_reference` (≤ 1000), `is_primary` (derivado del tipo; si se envía debe coincidir). Reglas: un solo `PRIMARY` vigente (`409 PRIMARY_REPRESENTATIVE_CONFLICT`: «use set-primary para sustituirlo»); una persona no puede tener dos representaciones vigentes con la misma organización (`409 DUPLICATE_ACTIVE_REPRESENTATIVE`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/legal-representatives' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "representative_type": "PRIMARY",
    "position": "Representante legal",
    "valid_from": "2026-10-01T00:00:00Z",
    "is_primary": true
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`LegalRepresentativeResponse`; valores ilustrativos):

```json
{
  "id": "89d85df5-0f75-4506-86b1-0b1c71429874",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "representative_type": "PRIMARY",
  "position": "Representante legal",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "source_document_reference": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 51. `POST /organization-identities/{organization_identity_id}/legal-representatives:set-primary`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/legal-representatives:set-primary`; permiso `organization_legal_representatives:create`. Cuerpo (`LegalRepresentativeSetPrimary`): `person_identity_id` (obligatorio), `position`, `valid_from`, `source_document_reference`, `current_primary_version` (versión del `PRIMARY` vigente; se omite si no existe). Crea el primero o cierra el vigente y crea el nuevo. `201` con el nuevo; `200` sin cuerpo si la persona ya es el `PRIMARY` vigente.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/legal-representatives:set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "position": "Representante legal",
    "valid_from": "2026-10-01T00:00:00Z",
    "current_primary_version": 1
  }'
```

### 52. `GET /organization-legal-representatives/{representative_id}`

`READ`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/{representative_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/82a0aa35-e2d1-4f36-81d1-efa8198fd8b8' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`LegalRepresentativeResponse`; valores ilustrativos):

```json
{
  "id": "82a0aa35-e2d1-4f36-81d1-efa8198fd8b8",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "representative_type": "PRIMARY",
  "position": "Representante legal",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "source_document_reference": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 53. `PUT /organization-legal-representatives/{representative_id}`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/{representative_id}`; permiso `organization_legal_representatives:update`. Cuerpo (`LegalRepresentativeUpdate`): `position`, `source_document_reference`, `version`. `person_identity_id`, `organization_identity_id` y `representative_type` son inmutables.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/82a0aa35-e2d1-4f36-81d1-efa8198fd8b8' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "position": "Representante legal",
    "version": 1,
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "representative_type": "PRIMARY"
  }'
```

Ejemplo de respuesta `200` (`LegalRepresentativeResponse`; valores ilustrativos):

```json
{
  "id": "82a0aa35-e2d1-4f36-81d1-efa8198fd8b8",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "representative_type": "PRIMARY",
  "position": "Representante legal",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "source_document_reference": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

### 54. `POST /organization-legal-representatives/{representative_id}:close`

`WRITE`. URL `https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/{representative_id}:close`; permiso `organization_legal_representatives:delete`; cuerpo `{"version": n}`. Cierra la relación; no se reactiva.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-party-identity-dev.onrender.com/api/v1/organization-legal-representatives/82a0aa35-e2d1-4f36-81d1-efa8198fd8b8:close' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`LegalRepresentativeResponse`; valores ilustrativos):

```json
{
  "id": "82a0aa35-e2d1-4f36-81d1-efa8198fd8b8",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "representative_type": "PRIMARY",
  "position": "Representante legal",
  "is_primary": true,
  "is_active": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "source_document_reference": null,
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `409 PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | Ya existe una identidad con ese país, tipo y número | Buscarla (operaciones 3 o 9) y reutilizar su `id` |
| `422 PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple la regla activa de la sigla | Mostrar `number_pattern_description` de la regla (operación 15) |
| `422 …BIRTH_DATE_REQUIRED` / `AGE_OUT_OF_RANGE` | La regla exige edad | Pedir fecha de nacimiento |
| `422 …CONFIRMATION_MEMBERSHIP_INVALID` | El usuario no tiene membresía activa en `confirmed_by_company_id` | Usar la empresa activa del usuario |
| `422 …PERSON_IDENTITY_INACTIVE` / `ORGANIZATION_IDENTITY_INACTIVE` | Identidad inactiva | Reactivarla (operaciones 8 o 14) si procede |
| `409 …PRIMARY_*_CONFLICT` | Ya existe un principal | Usar la operación `set-primary` correspondiente |
| `409 …VERSION_CONFLICT` | Versión desactualizada | Recargar |
| `422 …IMMUTABLE_FIELD` / `RULE_CHANGE_REQUIRES_NEW_VERSION` | Campo inmutable | Quitar el campo o crear una versión nueva |
| `503` con `dependency` `geography` u `operational-context` | Dependencia caída | Reintentar |

## Dependencias

| Servicio | Uso |
|---|---|
| Geography | Validar país de identificación y ubicación de los perfiles de contacto (con el token del usuario; la cuenta técnica de Party Identity lee países) |
| Operational Context | Confirmar la membresía del usuario en `confirmed_by_company_id` al registrar perfiles de contacto |
| Audit | Eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 54 |
| Operaciones documentadas | 54 |
| Permisos contrastados con el código | Sí (`api/person_identities.py`, `organization_identities.py`, `identification_type_rules.py`, `contact_profiles.py`, `contact_persons.py`, `business_sectors.py`, `legal_representatives.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado; `application/exceptions.py`; `application/identification_rules.py`) |
| Verificado | `valid_from` omitido en sectores económicos y representantes legales toma la fecha y hora actuales del servicio |

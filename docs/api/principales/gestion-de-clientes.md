# 6.3 Gestión de clientes

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un usuario de la empresa registra, busca, consulta, actualiza e inactiva a los clientes a los que vende. Un cliente de SIO se compone de dos partes que viven en servicios distintos:

| Parte | Servicio | Qué guarda | Alcance |
|---|---|---|---|
| **Identidad** (quién es) | [Party Identity](../servicios/party-identity.md) | Persona (`person_identity_id`: documento, nombres) u organización (`organization_identity_id`: NIT, razón social), más sus perfiles de contacto | Global: una misma identidad puede ser cliente de varias empresas, proveedor o empresa de la plataforma |
| **Relación comercial** (es mi cliente) | [Commercial Relationship](../servicios/commercial-relationship.md) | `company_customer_id`, `customer_kind`, `internal_code`, `display_name`, `preferred_contact_person_id`, `status` | Empresa: solo existe dentro de un `company_id` |

Ventas usa **siempre** el `company_customer_id` ([customer_id](../parametros/customer-id.md)); nunca la identidad directamente. Flujo de uso: [Crear una venta](../ejemplos/crear-venta.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Buscar la identidad de una persona | `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities` | `perm:party-identity:person_identities:read` | [PI 3](../servicios/party-identity.md#3-get-person-identities) |
| 2 | Crear la identidad de una persona | `POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities` | `perm:party-identity:person_identities:create` | [PI 4](../servicios/party-identity.md#4-post-person-identities) |
| 3 | Buscar la identidad de una organización | `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | [PI 9](../servicios/party-identity.md#9-get-organization-identities) |
| 4 | Crear la identidad de una organización | `POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | [PI 10](../servicios/party-identity.md#10-post-organization-identities) |
| 5 | Consultar los tipos de identificación admitidos por país | `GET https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:read` | [PI 15](../servicios/party-identity.md#15-get-identification-type-rules) |
| 6 | Registrar un cliente de la empresa | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` | `perm:commercial-relationship:company_customers:create` | [CR 14](../servicios/commercial-relationship.md#14-post-companiescompany_idcompany-customers) |
| 7 | Buscar y listar los clientes de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` | `perm:commercial-relationship:company_customers:read` | [CR 13](../servicios/commercial-relationship.md#13-get-companiescompany_idcompany-customers) |
| 8 | Consultar un cliente | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}` | `perm:commercial-relationship:company_customers:read` | [CR 15](../servicios/commercial-relationship.md#15-get-company-customerscompany_customer_id) |
| 9 | Consultar los datos de identidad de una persona | `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}` | `perm:party-identity:person_identities:read` | [PI 5](../servicios/party-identity.md#5-get-person-identitiesperson_identity_id) |
| 10 | Consultar los datos de identidad de una organización | `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}` | `perm:party-identity:organization_identities:read` | [PI 11](../servicios/party-identity.md#11-get-organization-identitiesorganization_identity_id) |
| 11 | Consultar los datos de contacto vigentes del cliente | `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile` y `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` · `perm:party-identity:organization_contact_profiles:read` | [PI 21](../servicios/party-identity.md#21-get-person-identitiesperson_identity_idcontact-profile) · [PI 26](../servicios/party-identity.md#26-get-organization-identitiesorganization_identity_idcontact-profile) |
| 12 | Actualizar un cliente | `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}` | `perm:commercial-relationship:company_customers:update` | [CR 16](../servicios/commercial-relationship.md#16-put-company-customerscompany_customer_id) |
| 13 | Actualizar la identidad de una persona | `PUT https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}` | `perm:party-identity:person_identities:update` | [PI 6](../servicios/party-identity.md#6-put-person-identitiesperson_identity_id) |
| 14 | Actualizar la identidad de una organización | `PUT https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}` | `perm:party-identity:organization_identities:update` | [PI 12](../servicios/party-identity.md#12-put-organization-identitiesorganization_identity_id) |
| 15 | Inactivar un cliente | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/deactivate` | `perm:commercial-relationship:company_customers:delete` | [CR 17](../servicios/commercial-relationship.md#17-post-company-customerscompany_customer_iddeactivate) |
| 16 | Reactivar un cliente | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/reactivate` | `perm:commercial-relationship:company_customers:update` | [CR 18](../servicios/commercial-relationship.md#18-post-company-customerscompany_customer_idreactivate) |

Operaciones relacionadas que no se consideran principales (ver las fichas): inactivar o reactivar una identidad de Party Identity (PI 7, 8, 13, 14), registrar o cerrar perfiles de contacto (PI 22–25, 27–30), administrar las personas de contacto de una organización (PI 31–37) y la consulta por lotes de clientes que usa Sales internamente.

Orden habitual para dar de alta un cliente: [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) (tipos de documento del país) → [API 1](#1-buscar-la-identidad-de-una-persona) o [API 3](#3-buscar-la-identidad-de-una-organización) (¿ya existe la identidad?) → si no existe, [API 2](#2-crear-la-identidad-de-una-persona) o [API 4](#4-crear-la-identidad-de-una-organización) → [API 6](#6-registrar-un-cliente-de-la-empresa) (convertir la identidad en cliente de la empresa).

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Todas las API de escritura con cuerpo JSON de Party Identity y de Commercial Relationship **rechazan campos desconocidos** con `422 …VALIDATION_ERROR` (modelos estrictos).
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `PARTY_IDENTITY.FORBIDDEN` o `COMMERCIAL_RELATIONSHIP.FORBIDDEN` cuando el token no tiene el permiso indicado (mostrar que faltan permisos y el `trace_id`); `503` con `code` `…DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde (reintentar más tarde; nada se guarda). Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `PARTY_IDENTITY.…` o `COMMERCIAL_RELATIONSHIP.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).
- **Alcance.** Las identidades de Party Identity son globales: cualquier usuario con el permiso de lectura las ve. Los clientes de Commercial Relationship solo se ven y modifican con membresía `ACTIVE` en la empresa; fuera de ese alcance la respuesta es `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND`, igual que si no existieran.
- **Empresa inactiva.** Si la empresa está `INACTIVE`, Commercial Relationship solo permite consultar e inactivar clientes; registrar, actualizar o reactivar responde `422 COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE`.
- **Control de versión.** Toda modificación envía la `version` actual del recurso; si otra persona lo cambió antes, la API responde `409 …VERSION_CONFLICT` y el frontend debe volver a leer el recurso y repetir con la nueva `version`.
- Las respuestas traen siempre `created_by`, `updated_by` (el `sub` de Keycloak de quien actuó), `created_at` y `updated_at`.
- Toda escritura sobre clientes queda registrada en [Audit](../servicios/audit.md) con las acciones `CREATE_COMPANY_CUSTOMER`, `UPDATE_COMPANY_CUSTOMER`, `DEACTIVATE_COMPANY_CUSTOMER` y `REACTIVATE_COMPANY_CUSTOMER` sobre la entidad `CompanyCustomer`; se consultan con la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (lista los eventos de auditoría de la empresa; sus errores están en esa sección).

---

## 1. Buscar la identidad de una persona

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/person-identities`
**Permiso requerido:** `perm:party-identity:person_identities:read`

### ¿Qué hace esta API?

Busca personas naturales registradas en Party Identity por número de documento o por nombres, con paginación. Es el primer paso antes de registrar un cliente persona: si la persona ya existe (porque otra empresa la registró, porque es usuaria de la plataforma o contacto de una organización) se reutiliza su `id` y **no** se crea de nuevo. El resultado también sirve para filtrar clientes por documento en la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa), que no busca por documento sino por código interno y nombre.

Por defecto solo devuelve personas `ACTIVE`; una persona `INACTIVE` no puede registrarse como cliente (la [API 6](#6-registrar-un-cliente-de-la-empresa) responde `422 PERSON_IDENTITY_INACTIVE`).

Antes necesita: solo el token. Para filtrar por país y tipo de documento, el `identification_country_id` ([country_id](../parametros/country-id.md)) y la sigla del tipo ([API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=1012345678&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 120) | No | Búsqueda parcial, sin distinguir mayúsculas, en `identification_number`, `first_name`, `middle_name`, `last_name` y `second_last_name` | Texto libre: número de documento o parte de un nombre o apellido; p. ej. `1012345678` o `perez` | `&search=1012345678` | Interfaz (documento o nombre que escribe el usuario) |
| `identification_country_id` | UUID | No | Solo personas con documento de ese país | UUID de un país; p. ej. `c0a80101-0000-4000-8000-000000000001` | `&identification_country_id=c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string | No | Sigla del tipo de documento (`CC`, `CE`, `PA`…) | Sigla de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país); p. ej. `CC`, `CE`, `PA` | `&identification_type=CC` | `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) (lista los tipos de identificación por país; errores en §5) |
| `verification_status` | `UNVERIFIED` \| `VERIFIED` \| `SUSPENDED` | No | Estado de verificación de la identidad | Uno de: `UNVERIFIED`, `VERIFIED`, `SUSPENDED`; p. ej. `VERIFIED` | `&verification_status=VERIFIED` | Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de la identidad | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=1012345678&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PersonIdentityResponse]`):

```json
{
  "items": [
    {
      "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "CC",
      "identification_number": "1012345678",
      "first_name": "Ana",
      "middle_name": null,
      "last_name": "Pérez",
      "second_last_name": null,
      "birth_date": "1990-05-20",
      "verification_status": "UNVERIFIED",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [person_identity_id](../parametros/person-identity-id.md) que se envía en la [API 6](#6-registrar-un-cliente-de-la-empresa) y con el que se consulta la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) |
| `items[].identification_country_id`, `identification_type`, `identification_number` | UUID, string, string | Documento de identidad; la terna es única en toda la plataforma |
| `items[].first_name`, `middle_name`, `last_name`, `second_last_name` | string \| null | Nombres para mostrar; `middle_name` y `second_last_name` pueden ser `null` |
| `items[].birth_date` | date \| null | Fecha de nacimiento, si la regla del documento la exige |
| `items[].verification_status` | `UNVERIFIED` \| `VERIFIED` \| `SUSPENDED` | Grado de verificación de la identidad; informativo |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo una persona `ACTIVE` puede registrarse como cliente |
| `items[].version` | integer | Valor que debe enviarse en la [API 13](#13-actualizar-la-identidad-de-una-persona) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío y `total_records: 0` cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `search` > 120 caracteres, `page` < 1, `page_size` fuera de 1–100, UUID o enumeración inválidos | Corregir los filtros; el detalle viene en `errors[]` con `field` |

## 2. Crear la identidad de una persona

**Método:** `POST`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/person-identities`
**Permiso requerido:** `perm:party-identity:person_identities:create`

### ¿Qué hace esta API?

Registra una persona natural en Party Identity cuando la [API 1](#1-buscar-la-identidad-de-una-persona) no la encontró. Party Identity valida el número de documento contra las reglas activas del país y la sigla ([API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)): formato (expresión regular) y, si la regla define rango de edad, exige `birth_date` y comprueba la edad. La identidad creada es global: queda disponible para cualquier empresa de SIO, por eso la unicidad del documento se verifica en toda la plataforma.

Efectos verificados en el código: crea la persona con `status` `ACTIVE`, `version` `1` y `verification_status` `UNVERIFIED` si no se envía; devuelve la cabecera `Location: /api/v1/person-identities/{id}`. Crear la identidad **no la convierte en cliente**: eso lo hace la [API 6](#6-registrar-un-cliente-de-la-empresa).

Antes necesita: el país del documento ([country_id](../parametros/country-id.md)) y una sigla admitida para ese país y para `party_kind` `PERSON` ([API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)). Buscar antes con la [API 1](#1-buscar-la-identidad-de-una-persona) para no recibir `409 DUPLICATE_IDENTIFICATION`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "identification_number": "1012345678",
    "first_name": "Ana",
    "middle_name": null,
    "last_name": "Pérez",
    "second_last_name": null,
    "birth_date": "1990-05-20",
    "verification_status": "UNVERIFIED"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": null,
  "last_name": "Pérez",
  "second_last_name": null,
  "birth_date": "1990-05-20",
  "verification_status": "UNVERIFIED"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `identification_country_id` | UUID | Sí | País que expidió el documento; debe existir en Geography | `c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string (1–40) | Sí | Sigla del tipo de documento; se normaliza a mayúsculas y debe tener una regla activa para el país | `CC` | `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) (lista los tipos de identificación por país; errores en §5) |
| `identification_number` | string (1–40) | Sí | Número del documento; debe cumplir `number_pattern` de la regla | `1012345678` | Formulario; validar en la interfaz con `items[].number_pattern` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) |
| `first_name` | string (1–100) | Sí | Primer nombre | `Ana` | Formulario |
| `middle_name` | string (≤ 100) \| null | No; acepta `null` | Segundo nombre | `null` | Formulario |
| `last_name` | string (1–100) | Sí | Primer apellido | `Pérez` | Formulario |
| `second_last_name` | string (≤ 100) \| null | No; acepta `null` | Segundo apellido | `null` | Formulario |
| `birth_date` | date (`AAAA-MM-DD`) \| null | Obligatoria si la regla del documento define `min_age_years` o `max_age_years`; si no, opcional | Fecha de nacimiento; no puede ser futura | `1990-05-20` | Formulario; la obligatoriedad se lee en `items[].min_age_years` / `max_age_years` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) |
| `verification_status` | `UNVERIFIED` \| `VERIFIED` \| `SUSPENDED` | No; por defecto `UNVERIFIED` | Estado de verificación inicial | `UNVERIFIED` | Formulario |

### Respuesta exitosa

`201 Created` (`PersonIdentityResponse`), con cabecera `Location: /api/v1/person-identities/{id}`:

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
  "birth_date": "1990-05-20",
  "verification_status": "UNVERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [person_identity_id](../parametros/person-identity-id.md): se guarda para enviarlo en la [API 6](#6-registrar-un-cliente-de-la-empresa) |
| `identification_type` | string | La sigla ya normalizada a mayúsculas |
| `status`, `version` | — | `ACTIVE` y `1` al crear |
| `verification_status` | enum | El enviado o `UNVERIFIED` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | Ya existe una identidad con el mismo país, tipo y número de documento (en cualquier estado) | No crear otra: buscarla con la [API 1](#1-buscar-la-identidad-de-una-persona) (con `status=INACTIVE` si no aparece) y reutilizar su `id` |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple ninguna regla activa para la sigla y el país; `detail` incluye la descripción del formato esperado | Mostrar `detail` junto al campo número y pedir corrección |
| `422` | `PARTY_IDENTITY.BIRTH_DATE_REQUIRED` | La regla del documento define rango de edad y no se envió `birth_date` | Pedir la fecha de nacimiento |
| `422` | `PARTY_IDENTITY.AGE_OUT_OF_RANGE` | La edad calculada no está en el rango de la regla | Mostrar el rango permitido (`min_age_years` / `max_age_years` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)) |
| `422` | `PARTY_IDENTITY.BIRTH_DATE_IN_FUTURE` | `birth_date` posterior a hoy | Corregir la fecha |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | `identification_country_id` no existe en Geography | Volver a cargar el selector de país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, fecha mal formada, enumeración inválida o campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `400` | `PARTY_IDENTITY.MALFORMED_REQUEST` | El cuerpo no es JSON válido | Error de programación del cliente |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Geography no responde al validar el país (`dependency: "geography"`) | Reintentar más tarde; nada se guardó |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/party-identity/duplicate-identification",
  "title": "Identificación duplicada",
  "status": 409,
  "detail": "Ya existe una identidad con el país, tipo y número de identificación indicados.",
  "instance": "/api/v1/person-identities",
  "code": "PARTY_IDENTITY.DUPLICATE_IDENTIFICATION",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo de `422` por número inválido:

```json
{
  "type": "https://sio/errors/party-identity/invalid-identification-number",
  "title": "Número de identificación inválido",
  "status": 422,
  "detail": "El número de identificación no cumple ninguna regla activa para la sigla indicada. Cédula de ciudadanía: de 6 a 10 dígitos.",
  "instance": "/api/v1/person-identities",
  "code": "PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 3. Buscar la identidad de una organización

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities`
**Permiso requerido:** `perm:party-identity:organization_identities:read`

### ¿Qué hace esta API?

Busca personas jurídicas (organizaciones) registradas en Party Identity por NIT o por nombre, con paginación. Es el primer paso antes de registrar un cliente organización: la organización puede existir ya porque es empresa de la plataforma, proveedor o cliente de otra empresa; en ese caso se reutiliza su `id`.

Por defecto solo devuelve organizaciones `ACTIVE`; una organización `INACTIVE` no puede registrarse como cliente (la [API 6](#6-registrar-un-cliente-de-la-empresa) responde `422 ORGANIZATION_IDENTITY_INACTIVE`).

Antes necesita: solo el token. Para filtrar por país, el `country_id` ([country_id](../parametros/country-id.md)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=900123456&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 120) | No | Búsqueda parcial, sin distinguir mayúsculas, en `identification_number`, `legal_name` y `trade_name` | Texto libre: NIT o parte de la razón social o del nombre comercial; p. ej. `900123456` o `economia` | `&search=900123456` | Interfaz (NIT o nombre que escribe el usuario) |
| `country_id` | UUID | No | Solo organizaciones registradas en ese país | UUID de un país; p. ej. `c0a80101-0000-4000-8000-000000000001` | `&country_id=c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string | No | Sigla del tipo de identificación (`NIT`…) | Sigla de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) con `party_kind=ORGANIZATION`; p. ej. `NIT` | `&identification_type=NIT` | `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) con `party_kind=ORGANIZATION` (lista los tipos de identificación por país; errores en §5) |
| `registration_status` | string (≤ 30) | No | Estado de registro mercantil tal como se guardó | Texto libre tal como se guardó (≤ 30); p. ej. `VIGENTE` | `&registration_status=VIGENTE` | Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de la identidad | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=900123456&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[OrganizationIdentityResponse]`):

```json
{
  "items": [
    {
      "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "NIT",
      "identification_number": "900123456",
      "legal_name": "Droguería La Economía S.A.S.",
      "trade_name": "La Economía",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [organization_identity_id](../parametros/organization-identity-id.md) que se envía en la [API 6](#6-registrar-un-cliente-de-la-empresa) y con el que se consulta la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) |
| `items[].country_id`, `identification_type`, `identification_number` | UUID, string, string | Identificación tributaria; la terna es única en toda la plataforma |
| `items[].legal_name` | string | Razón social (nombre legal) |
| `items[].trade_name` | string \| null | Nombre comercial |
| `items[].organization_type`, `registration_status`, `website` | string \| null | Datos informativos de registro |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo una organización `ACTIVE` puede registrarse como cliente |
| `items[].version` | integer | Valor que debe enviarse en la [API 14](#14-actualizar-la-identidad-de-una-organización) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `search` > 120, `registration_status` > 30, `page` < 1, `page_size` fuera de 1–100, UUID o enumeración inválidos | Corregir los filtros; `errors[]` trae `field` |

## 4. Crear la identidad de una organización

**Método:** `POST`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities`
**Permiso requerido:** `perm:party-identity:organization_identities:create`

### ¿Qué hace esta API?

Registra una persona jurídica en Party Identity cuando la [API 3](#3-buscar-la-identidad-de-una-organización) no la encontró. Valida el número de identificación contra las reglas activas del país para `party_kind` `ORGANIZATION` y la unicidad de país + tipo + número en toda la plataforma. La identidad es global: la misma organización puede ser después empresa de SIO, proveedor o cliente de varias empresas.

Efectos verificados en el código: crea la organización con `status` `ACTIVE` y `version` `1`; devuelve la cabecera `Location: /api/v1/organization-identities/{id}`. No crea perfiles de contacto ni personas de contacto (PI 27 y 32) ni la convierte en cliente ([API 6](#6-registrar-un-cliente-de-la-empresa)).

Antes necesita: el país ([country_id](../parametros/country-id.md)) y una sigla admitida para ese país y `party_kind` `ORGANIZATION` ([API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)). Buscar antes con la [API 3](#3-buscar-la-identidad-de-una-organización).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "NIT",
    "identification_number": "900123456",
    "legal_name": "Droguería La Economía S.A.S.",
    "trade_name": "La Economía",
    "organization_type": "SAS",
    "registration_status": "VIGENTE",
    "website": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": "La Economía",
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": null
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `country_id` | UUID | Sí | País de registro; debe existir en Geography | `c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string (1–40) | Sí | Sigla del tipo de identificación; se normaliza a mayúsculas y debe tener regla activa para el país y `ORGANIZATION` | `NIT` | `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) con `party_kind=ORGANIZATION` (lista los tipos de identificación por país; errores en §5) |
| `identification_number` | string (1–40) | Sí | Número de identificación; debe cumplir `number_pattern` de la regla | `900123456` | Formulario; validar en la interfaz con `items[].number_pattern` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) |
| `legal_name` | string (1–200) | Sí | Razón social | `Droguería La Economía S.A.S.` | Formulario |
| `trade_name` | string (≤ 200) \| null | No; acepta `null` | Nombre comercial | `La Economía` | Formulario |
| `organization_type` | string (≤ 40) \| null | No; acepta `null` | Tipo societario (texto libre) | `SAS` | Formulario |
| `registration_status` | string (≤ 30) \| null | No; acepta `null` | Estado del registro mercantil (texto libre) | `VIGENTE` | Formulario |
| `website` | string (≤ 300) \| null | No; acepta `null` | Sitio web | `null` | Formulario |

### Respuesta exitosa

`201 Created` (`OrganizationIdentityResponse`), con cabecera `Location: /api/v1/organization-identities/{id}`:

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": "La Economía",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [organization_identity_id](../parametros/organization-identity-id.md): se guarda para enviarlo en la [API 6](#6-registrar-un-cliente-de-la-empresa) |
| `identification_type` | string | La sigla ya normalizada a mayúsculas |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | Ya existe una identidad con el mismo país, tipo y número (en cualquier estado) | No crear otra: buscarla con la [API 3](#3-buscar-la-identidad-de-una-organización) (con `status=INACTIVE` si no aparece) y reutilizar su `id` |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple ninguna regla activa para la sigla y el país; `detail` incluye el formato esperado | Mostrar `detail` junto al campo número |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | `country_id` no existe en Geography | Volver a cargar el selector de país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango o campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `400` | `PARTY_IDENTITY.MALFORMED_REQUEST` | El cuerpo no es JSON válido | Error de programación del cliente |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Geography no responde al validar el país (`dependency: "geography"`) | Reintentar más tarde; nada se guardó |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/party-identity/duplicate-identification",
  "title": "Identificación duplicada",
  "status": 409,
  "detail": "Ya existe una identidad con el país, tipo y número de identificación indicados.",
  "instance": "/api/v1/organization-identities",
  "code": "PARTY_IDENTITY.DUPLICATE_IDENTIFICATION",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 5. Consultar los tipos de identificación admitidos por país

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules`
**Permiso requerido:** `perm:party-identity:identification_type_rules:read`

### ¿Qué hace esta API?

Devuelve las reglas de identificación configuradas por la administración de la plataforma: para cada país y tipo de parte (`PERSON` u `ORGANIZATION`), las siglas de documento admitidas (`CC`, `CE`, `NIT`…), la expresión regular que debe cumplir el número, un valor de ejemplo y, si aplica, el rango de edad. El frontend la usa para poblar el selector de tipo de documento según el país elegido y para validar el número en la interfaz **antes** de llamar a la [API 2](#2-crear-la-identidad-de-una-persona) o la [API 4](#4-crear-la-identidad-de-una-organización), que aplican exactamente estas mismas reglas en el servidor.

Antes necesita: el `country_id` del documento ([country_id](../parametros/country-id.md)). Filtrar con `is_active=true` para mostrar solo las siglas vigentes.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules?country_id=c0a80101-0000-4000-8000-000000000001&party_kind=PERSON&is_active=true&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=50` | Interfaz |
| `party_kind` | `PERSON` \| `ORGANIZATION` | No | Reglas para personas naturales o para organizaciones | Uno de: `PERSON`, `ORGANIZATION`; p. ej. `PERSON` | `&party_kind=PERSON` | Interfaz (tipo de cliente que se va a registrar) |
| `country_id` | UUID | No | Reglas del país | UUID de un país; p. ej. `c0a80101-0000-4000-8000-000000000001` | `&country_id=c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string | No | Tipo de identificación de la regla | Texto de la sigla o tipo configurado; p. ej. `CC` | `&identification_type=CC` | Interfaz |
| `sigla` | string (≤ 10) | No | Sigla exacta | Texto (≤ 10); p. ej. `CC`, `CE`, `PA`, `NIT` | `&sigla=CC` | Interfaz |
| `is_active` | boolean | No | Solo reglas activas (`true`) o inactivas (`false`) | Booleano: `true` o `false`; p. ej. `true` | `&is_active=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules?country_id=c0a80101-0000-4000-8000-000000000001&party_kind=PERSON&is_active=true&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[IdentificationTypeRuleResponse]`):

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
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].sigla` | string (≤ 10) | **Lo que se envía como `identification_type`** en las API 1 a 4, 13 y 14 |
| `items[].party_kind` | `PERSON` \| `ORGANIZATION` | A qué tipo de identidad aplica la regla |
| `items[].number_pattern` | string (expresión regular) | Patrón que debe cumplir `identification_number`; úsalo para validar en la interfaz |
| `items[].number_pattern_description`, `example_value` | string | Texto de ayuda y ejemplo para mostrar al usuario |
| `items[].min_age_years`, `max_age_years` | integer \| null | Si alguno no es `null`, `birth_date` es obligatoria al crear la persona y la edad debe estar en el rango |
| `items[].is_active`, `valid_from`, `valid_to` | boolean, fecha, fecha \| null | Vigencia de la regla; solo las activas se aplican al validar |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `party_kind` fuera de la enumeración, `country_id` no UUID, `sigla` > 10, `is_active` no booleano, paginación fuera de rango | Corregir los filtros |

## 6. Registrar un cliente de la empresa

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`
**Permiso requerido:** `perm:commercial-relationship:company_customers:create`

### ¿Qué hace esta API?

Convierte una identidad de Party Identity (persona u organización) en cliente de la empresa, con el código interno y el nombre con que la empresa lo reconoce. El resultado es la relación comercial cuyo `id` ([customer_id](../parametros/customer-id.md)) exige [Ventas](ventas.md) al crear una venta.

Reglas verificadas en el código, en este orden: (1) coherencia del cuerpo: un cliente `PERSON` exige `person_identity_id` y no admite `organization_identity_id` ni `preferred_contact_person_id`; un cliente `ORGANIZATION` exige `organization_identity_id` y no admite `person_identity_id`; (2) la identidad no puede ser ya cliente de la empresa, en ningún estado (`409 DUPLICATE_CUSTOMER`); (3) `internal_code` único en la empresa sin distinguir mayúsculas (`409 DUPLICATE_INTERNAL_CODE`); (4) la identidad debe existir y estar `ACTIVE` en Party Identity; la organización no puede ser la de la propia empresa; la persona de contacto, si se envía, debe ser un contacto activo de esa organización. Nada se guarda si alguna regla falla. Crea el cliente con `status` `ACTIVE` y `version` `1`, devuelve `Location: /api/v1/company-customers/{id}` y registra `CREATE_COMPANY_CUSTOMER` en Audit.

Antes necesita: `company_id` con membresía `ACTIVE` y empresa `ACTIVE`; el `person_identity_id` ([API 1](#1-buscar-la-identidad-de-una-persona) o [API 2](#2-crear-la-identidad-de-una-persona)) o el `organization_identity_id` ([API 3](#3-buscar-la-identidad-de-una-organización) o [API 4](#4-crear-la-identidad-de-una-organización)). Para validar la identidad, Commercial Relationship consulta Party Identity **con el token del usuario**: el usuario necesita además `perm:party-identity:person_identities:read` u `organization_identities:read` (y `organization_contact_persons:read` si envía contacto); si no los tiene recibe `403 PARTY_IDENTITY_ACCESS_DENIED`.

### ¿Cómo se realiza la solicitud?

Cliente persona natural:

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_kind": "PERSON",
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "organization_identity_id": null,
    "internal_code": "CLI-0001",
    "display_name": "Ana Pérez",
    "preferred_contact_person_id": null
  }'
```

Cliente organización con persona de contacto preferida:

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_kind": "ORGANIZATION",
    "person_identity_id": null,
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "internal_code": "CLI-0002",
    "display_name": "Droguería La Economía",
    "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que registra al cliente | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "customer_kind": "ORGANIZATION",
  "person_identity_id": null,
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0002",
  "display_name": "Droguería La Economía",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `customer_kind` | `PERSON` \| `ORGANIZATION` | Sí | Tipo de cliente; inmutable después de crear | `ORGANIZATION` | Formulario |
| `person_identity_id` | UUID \| null | Sí con `PERSON`; debe ser `null` u omitirse con `ORGANIZATION` | Persona natural `ACTIVE` en Party Identity | `a0e1d2c3-b4a5-4968-8776-655443322110` | `items[].id` de la [API 1](#1-buscar-la-identidad-de-una-persona) (busca personas por documento o nombre; errores en §1) o `id` de la [API 2](#2-crear-la-identidad-de-una-persona) (crea la persona; errores en §2) · guía [person_identity_id](../parametros/person-identity-id.md) |
| `organization_identity_id` | UUID \| null | Sí con `ORGANIZATION`; debe ser `null` u omitirse con `PERSON` | Organización `ACTIVE` en Party Identity; no puede ser la de la propia empresa | `0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3](#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; errores en §3) o `id` de la [API 4](#4-crear-la-identidad-de-una-organización) (crea la organización; errores en §4) · guía [organization_identity_id](../parametros/organization-identity-id.md) |
| `internal_code` | string (1–60) | Sí | Código con que la empresa identifica al cliente; se recortan espacios; único en la empresa sin distinguir mayúsculas | `CLI-0002` | Formulario (numeración propia de la empresa) |
| `display_name` | string (1–200) | Sí | Nombre con que la empresa muestra al cliente (puede diferir de la razón social) | `Droguería La Economía` | Formulario; sugerir `first_name` + `last_name` de la [API 1](#1-buscar-la-identidad-de-una-persona) o `legal_name` / `trade_name` de la [API 3](#3-buscar-la-identidad-de-una-organización) |
| `preferred_contact_person_id` | UUID \| null | No; solo con `ORGANIZATION` | Persona de contacto preferida; debe ser un contacto **activo** de esa organización | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons?is_active=true` (lista las personas de contacto de la organización, permiso `perm:party-identity:organization_contact_persons:read`; errores `404 PARTY_IDENTITY.NOT_FOUND` si la organización no existe y `422 VALIDATION_ERROR` por filtros inválidos; ficha [PI 31](../servicios/party-identity.md#31-get-organization-identitiesorganization_identity_idcontact-persons)). Es el `id` del contacto, **no** su `person_identity_id` |

### Respuesta exitosa

`201 Created` (`CompanyCustomerResponse`), con cabecera `Location: /api/v1/company-customers/{id}`:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "ORGANIZATION",
  "person_identity_id": null,
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0002",
  "display_name": "Droguería La Economía",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [customer_id](../parametros/customer-id.md) (`company_customer_id`) que se envía en [Ventas](ventas.md) |
| `company_id` | UUID | Empresa dueña de la relación |
| `customer_kind` | `PERSON` \| `ORGANIZATION` | Determina cuál de las dos identidades viene informada |
| `person_identity_id`, `organization_identity_id` | UUID \| null | Solo una de las dos tiene valor; con ella se consultan las API 9/10 y 11 |
| `internal_code` | string | El código ya recortado |
| `preferred_contact_person_id` | UUID \| null | `null` siempre en clientes `PERSON` |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_CUSTOMER` | La identidad ya es cliente de la empresa (activo o inactivo) | Buscarlo con la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) filtrando por `person_identity_id` u `organization_identity_id` y `status=ALL`; si está inactivo, ofrecer la [API 16](#16-reactivar-un-cliente) |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un cliente con ese `internal_code` en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CUSTOMER_IDENTITY_MISMATCH` | `customer_kind` no corresponde con la identidad enviada: falta la obligatoria o se enviaron ambas | Error de formulario: enviar solo la identidad que exige el tipo |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_NOT_ALLOWED` | `preferred_contact_person_id` en un cliente `PERSON` | Ocultar el campo de contacto para personas |
| `422` | `COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED` | La organización es la de la propia empresa | Informar que una empresa no puede ser cliente de sí misma |
| `422` | `COMMERCIAL_RELATIONSHIP.PERSON_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_NOT_FOUND` | La identidad no existe en Party Identity | Volver a buscarla con la [API 1](#1-buscar-la-identidad-de-una-persona) o la [API 3](#3-buscar-la-identidad-de-una-organización) |
| `422` | `COMMERCIAL_RELATIONSHIP.PERSON_IDENTITY_INACTIVE` / `ORGANIZATION_IDENTITY_INACTIVE` | La identidad está `INACTIVE` en Party Identity | Informar; reactivar la identidad es una operación de Party Identity (PI 8 / PI 14) |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID` | El contacto no existe, está inactivo o pertenece a otra organización | Volver a cargar los contactos activos de la organización (PI 31) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar clientes en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `customer_kind` fuera de la enumeración, `internal_code` vacío o > 60, `display_name` vacío o > 200, UUID inválido o campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | El usuario no tiene permiso de lectura en Party Identity para validar la identidad o el contacto | Pedir al administrador los permisos de lectura de Party Identity; nada se guardó |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read`; nada se guardó |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden (`dependency` indica cuál) | Reintentar más tarde; nada se guardó |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/duplicate-customer",
  "title": "Cliente duplicado",
  "status": 409,
  "detail": "La identidad ya es cliente de la empresa; si está inactivo, reactívelo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers",
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_CUSTOMER",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "La identidad ya es cliente de la empresa; si está inactivo, reactívelo.",
      "code": "DUPLICATE_CUSTOMER"
    }
  ]
}
```

Ejemplo de `422` por identidad incoherente:

```json
{
  "type": "https://sio/errors/commercial-relationship/customer-identity-mismatch",
  "title": "Identidad del cliente inválida",
  "status": 422,
  "detail": "Un cliente PERSON exige person_identity_id y un cliente ORGANIZATION exige organization_identity_id; nunca ambos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers",
  "code": "COMMERCIAL_RELATIONSHIP.CUSTOMER_IDENTITY_MISMATCH",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "person_identity_id",
      "message": "Un cliente PERSON exige person_identity_id y un cliente ORGANIZATION exige organization_identity_id; nunca ambos.",
      "code": "CUSTOMER_IDENTITY_MISMATCH"
    }
  ]
}
```

## 7. Buscar y listar los clientes de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`
**Permiso requerido:** `perm:commercial-relationship:company_customers:read`

### ¿Qué hace esta API?

Lista, con paginación y búsqueda, los clientes de la empresa. Es la consulta con la que el vendedor encuentra al cliente al iniciar una venta y con la que se administra la cartera. La búsqueda es sobre los datos de la relación (`internal_code` y `display_name`), **no** sobre el documento de identidad: para encontrar un cliente por documento hay que buscar la identidad con la [API 1](#1-buscar-la-identidad-de-una-persona) o la [API 3](#3-buscar-la-identidad-de-una-organización) y filtrar aquí por `person_identity_id` u `organization_identity_id`.

Por defecto solo devuelve clientes `ACTIVE`, que son los únicos que acepta [Ventas](ventas.md).

Antes necesita: `company_id` con membresía `ACTIVE`. Funciona también con la empresa `INACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en `internal_code` y `display_name` | Texto libre: parte del código interno o del nombre para mostrar; p. ej. `CLI-0001` o `perez` | `&search=perez` | Interfaz (código o nombre que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de los clientes | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `customer_kind` | `PERSON` \| `ORGANIZATION` | No | Solo personas o solo organizaciones | Uno de: `PERSON`, `ORGANIZATION`; p. ej. `PERSON` | `&customer_kind=PERSON` | Interfaz |
| `person_identity_id` | UUID | No | Solo el cliente con esa identidad de persona | UUID de una persona; p. ej. `a0e1d2c3-b4a5-4968-8776-655443322110` | `&person_identity_id=a0e1d2c3-b4a5-4968-8776-655443322110` | `items[].id` de la [API 1](#1-buscar-la-identidad-de-una-persona) (busca personas por documento o nombre; errores en §1) · guía [person_identity_id](../parametros/person-identity-id.md) |
| `organization_identity_id` | UUID | No | Solo el cliente con esa identidad de organización | UUID de una organización; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&organization_identity_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3](#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; errores en §3) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyCustomerResponse]`):

```json
{
  "items": [
    {
      "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "customer_kind": "PERSON",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "organization_identity_id": null,
      "internal_code": "CLI-0001",
      "display_name": "Ana Pérez",
      "preferred_contact_person_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [customer_id](../parametros/customer-id.md) que se envía en la venta y en las API 8, 12, 15 y 16 |
| `items[].customer_kind` | `PERSON` \| `ORGANIZATION` | Indica qué identidad consultar para mostrar documento y nombres (API 9 o 10) |
| `items[].person_identity_id`, `organization_identity_id` | UUID \| null | Identidad asociada; solo una tiene valor |
| `items[].internal_code`, `display_name` | string | Lo que se muestra en el selector de cliente de la venta |
| `items[].preferred_contact_person_id` | UUID \| null | Contacto preferido (solo organizaciones) |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo los `ACTIVE` se pueden usar en ventas |
| `items[].version` | integer | Valor que debe enviarse en las API 12, 15 y 16 |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` o `customer_kind` fuera de la enumeración, UUID inválido, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 8. Consultar un cliente

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}`
**Permiso requerido:** `perm:commercial-relationship:company_customers:read`

### ¿Qué hace esta API?

Devuelve la ficha completa de un cliente, en cualquier estado, si pertenece a una empresa en la que el usuario tiene membresía `ACTIVE`. Se usa para abrir el detalle del cliente y para leer su `version` antes de modificarlo, inactivarlo o reactivarlo. Para mostrar documento, nombres completos o razón social hay que encadenar la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) o la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) con la identidad que devuelve, y la [API 11](#11-consultar-los-datos-de-contacto-vigentes-del-cliente) para correo, teléfono y dirección.

Antes necesita: el `company_customer_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_customer_id` | UUID | Sí | Cliente a consultar | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `items[].id` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (lista los clientes de la empresa; errores en §7) o `id` de la [API 6](#6-registrar-un-cliente-de-la-empresa) (registra el cliente; errores en §6) · guía [customer_id](../parametros/customer-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CompanyCustomerResponse`), mismo objeto y campos que la respuesta de la [API 6](#6-registrar-un-cliente-de-la-empresa):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": null,
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `customer_kind`, `person_identity_id`, `organization_identity_id` | — | Con ellos se decide si consultar la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) o la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) |
| `status` | `ACTIVE` \| `INACTIVE` | Un cliente `INACTIVE` se consulta pero no se usa en ventas |
| `version` | integer | Valor que debe enviarse en las API 12, 15 y 16 |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no existe o pertenece a una empresa en la que el usuario no tiene membresía `ACTIVE` | Volver a la lista; no distinguir entre «no existe» y «sin acceso» |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `company_customer_id` no es un UUID | Corregir el identificador |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 9. Consultar los datos de identidad de una persona

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}`
**Permiso requerido:** `perm:party-identity:person_identities:read`

### ¿Qué hace esta API?

Devuelve la identidad completa de una persona natural, en cualquier estado: documento, nombres, fecha de nacimiento y estado de verificación. Se encadena después de la [API 8](#8-consultar-un-cliente) para mostrar la ficha de un cliente `PERSON`, y antes de la [API 13](#13-actualizar-la-identidad-de-una-persona) para leer la `version` vigente.

Antes necesita: el `person_identity_id` del cliente.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `person_identity_id` | UUID | Sí | Persona a consultar | `a0e1d2c3-b4a5-4968-8776-655443322110` | `person_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) o de `items[]` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (lista los clientes; errores en §7); también `items[].id` de la [API 1](#1-buscar-la-identidad-de-una-persona) · guía [person_identity_id](../parametros/person-identity-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PersonIdentityResponse`), mismo objeto y campos que la respuesta de la [API 2](#2-crear-la-identidad-de-una-persona):

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
  "birth_date": "1990-05-20",
  "verification_status": "UNVERIFIED",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `identification_type`, `identification_number` | string | Documento para mostrar en la ficha y en el comprobante de venta |
| `first_name` … `second_last_name` | string \| null | Nombre completo |
| `status` | `ACTIVE` \| `INACTIVE` | Si está `INACTIVE`, el cliente no podrá reactivarse ([API 16](#16-reactivar-un-cliente)) |
| `version` | integer | Valor que debe enviarse en la [API 13](#13-actualizar-la-identidad-de-una-persona) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La persona no existe («La persona solicitada no existe.») | Mostrar que la identidad ya no está disponible |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `person_identity_id` no es un UUID | Corregir el identificador |

## 10. Consultar los datos de identidad de una organización

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`
**Permiso requerido:** `perm:party-identity:organization_identities:read`

### ¿Qué hace esta API?

Devuelve la identidad completa de una organización, en cualquier estado: NIT, razón social, nombre comercial y datos de registro. Se encadena después de la [API 8](#8-consultar-un-cliente) para mostrar la ficha de un cliente `ORGANIZATION`, y antes de la [API 14](#14-actualizar-la-identidad-de-una-organización) para leer la `version` vigente.

Antes necesita: el `organization_identity_id` del cliente.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Organización a consultar | `0f1e2d3c-4b5a-4968-8776-655443322111` | `organization_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) o de `items[]` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (lista los clientes; errores en §7); también `items[].id` de la [API 3](#3-buscar-la-identidad-de-una-organización) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`OrganizationIdentityResponse`), mismo objeto y campos que la respuesta de la [API 4](#4-crear-la-identidad-de-una-organización):

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": "La Economía",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `identification_type`, `identification_number` | string | Identificación tributaria para la ficha y el comprobante |
| `legal_name`, `trade_name` | string, string \| null | Razón social y nombre comercial |
| `status` | `ACTIVE` \| `INACTIVE` | Si está `INACTIVE`, el cliente no podrá reactivarse ([API 16](#16-reactivar-un-cliente)) |
| `version` | integer | Valor que debe enviarse en la [API 14](#14-actualizar-la-identidad-de-una-organización) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La organización no existe («La organización solicitada no existe.») | Mostrar que la identidad ya no está disponible |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `organization_identity_id` no es un UUID | Corregir el identificador |

## 11. Consultar los datos de contacto vigentes del cliente

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}/contact-profile` (cliente `PERSON`) y `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-profile` (cliente `ORGANIZATION`)
**Permiso requerido:** `perm:party-identity:person_contact_profiles:read` y `perm:party-identity:organization_contact_profiles:read`, respectivamente

### ¿Qué hace esta API?

Devuelve el perfil de contacto **vigente** de la identidad: correo, teléfono, dirección y ubicación geográfica. Los perfiles de contacto viven en Party Identity y son versionados: solo hay uno vigente a la vez (`is_active: true`, `valid_to: null`) y las versiones anteriores se consultan en las fichas PI 23 y 28. Se usa para mostrar los datos de contacto del cliente en su ficha y en el comprobante de venta. Registrar o cerrar un perfil de contacto (PI 22, 25, 27, 30) no forma parte de las API principales de este módulo.

Antes necesita: el `person_identity_id` u `organization_identity_id` del cliente ([API 8](#8-consultar-un-cliente)).

### ¿Cómo se realiza la solicitud?

Cliente persona:

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Cliente organización:

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-profile' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `person_identity_id` | UUID | Sí (ruta de personas) | Persona cuyo contacto se consulta | `a0e1d2c3-b4a5-4968-8776-655443322110` | `person_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) · guía [person_identity_id](../parametros/person-identity-id.md) |
| `organization_identity_id` | UUID | Sí (ruta de organizaciones) | Organización cuyo contacto se consulta | `0f1e2d3c-4b5a-4968-8776-655443322111` | `organization_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PersonContactProfileResponse`; la de organización, `OrganizationContactProfileResponse`, tiene los mismos campos con `organization_identity_id` en lugar de `person_identity_id`):

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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | Identificador de esta versión del perfil (`profile_id`) |
| `email`, `phone`, `address_line`, `postal_code` | string \| null | Datos de contacto para mostrar |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | Ubicación; sus nombres se resuelven con Geography ([country_id](../parametros/country-id.md)) |
| `is_active`, `valid_from`, `valid_to` | boolean, fecha, fecha \| null | Vigencia; el perfil devuelto es siempre el vigente |
| `confirmed_by_company_id`, `confirmed_by_user_id` | UUID \| null | Empresa y usuario que confirmaron los datos |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.CONTACT_PROFILE_NOT_FOUND` | La identidad existe pero no tiene un perfil de contacto vigente | Mostrar «sin datos de contacto»; no es un fallo |
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La persona u organización no existe | Mostrar que la identidad ya no está disponible |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | El identificador de la ruta no es un UUID | Corregir el identificador |

Ejemplo de `404` sin perfil vigente:

```json
{
  "type": "https://sio/errors/party-identity/contact-profile-not-found",
  "title": "Perfil de contacto inexistente",
  "status": 404,
  "detail": "La identidad no tiene un perfil de contacto vigente.",
  "instance": "/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110/contact-profile",
  "code": "PARTY_IDENTITY.CONTACT_PROFILE_NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 12. Actualizar un cliente

**Método:** `PUT`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}`
**Permiso requerido:** `perm:commercial-relationship:company_customers:update`

### ¿Qué hace esta API?

Modifica los datos propios de la relación comercial: código interno, nombre con que la empresa muestra al cliente y persona de contacto preferida. Es un reemplazo completo: se envían los tres campos con sus valores finales más la `version` vigente. El tipo de cliente y su identidad (`customer_kind`, `person_identity_id`, `organization_identity_id`), la empresa y el `status` son **inmutables**: para cambiar la identidad hay que inactivar el cliente ([API 15](#15-inactivar-un-cliente)) y registrar otro ([API 6](#6-registrar-un-cliente-de-la-empresa)); los datos legales se corrigen en Party Identity con la [API 13](#13-actualizar-la-identidad-de-una-persona) o la [API 14](#14-actualizar-la-identidad-de-una-organización).

Efectos verificados en el código: funciona sobre clientes en cualquier estado; si no hay cambios no escribe ni incrementa `version`; si cambia `preferred_contact_person_id` lo revalida en Party Identity; registra `UPDATE_COMPANY_CUSTOMER` en Audit.

Antes necesita: la `version` actual ([API 8](#8-consultar-un-cliente)) y empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "CLI-0001",
    "display_name": "Ana María Pérez",
    "preferred_contact_person_id": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_customer_id` | UUID | Sí | Cliente a modificar | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) o `items[].id` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (lista los clientes; errores en §7) · guía [customer_id](../parametros/customer-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "internal_code": "CLI-0001",
  "display_name": "Ana María Pérez",
  "preferred_contact_person_id": null
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del cliente | `1` | `version` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) |
| `internal_code` | string (1–60) | Sí | Código interno final; único en la empresa sin distinguir mayúsculas | `CLI-0001` | Formulario (repetir el actual si no cambia) |
| `display_name` | string (1–200) | Sí | Nombre final para mostrar | `Ana María Pérez` | Formulario |
| `preferred_contact_person_id` | UUID \| null | Sí (acepta `null`); solo con valor en clientes `ORGANIZATION` | Contacto preferido final; debe ser un contacto activo de la organización del cliente | `null` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons?is_active=true` (lista las personas de contacto de la organización; permiso `perm:party-identity:organization_contact_persons:read`; errores `404 PARTY_IDENTITY.NOT_FOUND` y `422 VALIDATION_ERROR`; ficha [PI 31](../servicios/party-identity.md#31-get-organization-identitiesorganization_identity_idcontact-persons)) |

No se admiten en el cuerpo `customer_kind`, `person_identity_id`, `organization_identity_id`, `company_id` ni `status`: su presencia responde `422 IMMUTABLE_FIELD`.

### Respuesta exitosa

`200 OK` (`CompanyCustomerResponse`) con `version` incrementada si hubo cambios:

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": null,
  "internal_code": "CLI-0001",
  "display_name": "Ana María Pérez",
  "preferred_contact_person_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión; es la que debe enviarse en la siguiente modificación. Si no hubo cambios se mantiene |
| `updated_by`, `updated_at` | UUID, fecha | Quién y cuándo modificó |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 8](#8-consultar-un-cliente), mostrar los cambios y repetir con la nueva `version` |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Otro cliente de la empresa ya usa ese `internal_code` | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.IMMUTABLE_FIELD` | El cuerpo incluye `customer_kind`, `person_identity_id`, `organization_identity_id`, `company_id` o `status` | Error de programación: no enviar esos campos |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_NOT_ALLOWED` | `preferred_contact_person_id` con valor en un cliente `PERSON` | Enviar `null` |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID` | El contacto no existe, está inactivo o es de otra organización | Volver a cargar los contactos activos (PI 31) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar clientes en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` < 1, `internal_code` vacío o > 60, `display_name` vacío o > 200, campo faltante o desconocido | Corregir el formulario |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Sin permiso en Party Identity para validar el contacto | Pedir `perm:party-identity:organization_contact_persons:read` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden | Reintentar más tarde; nada se guardó |

Ejemplo de `409` por versión:

```json
{
  "type": "https://sio/errors/commercial-relationship/version-conflict",
  "title": "Versión desactualizada",
  "status": 409,
  "detail": "El recurso fue modificado por otra operación. Consulte la versión vigente y vuelva a intentarlo.",
  "instance": "/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "code": "COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 13. Actualizar la identidad de una persona

**Método:** `PUT`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}`
**Permiso requerido:** `perm:party-identity:person_identities:update`

### ¿Qué hace esta API?

Corrige los datos legales de una persona natural: documento, nombres, fecha de nacimiento y estado de verificación. Es un reemplazo completo: se envían **todos** los campos con sus valores finales (incluido `verification_status`, obligatorio aquí) más la `version` vigente. Como la identidad es global, el cambio lo ven todas las empresas que la tengan como cliente, proveedor o usuario.

Efectos verificados en el código: comprueba la existencia y la `version`; si no hay cambios devuelve el registro actual sin escribir; si cambian país, tipo o número vuelve a validar la regla del documento y la unicidad; si cambia `birth_date` revalida el rango de edad.

Antes necesita: la ficha actual con su `version` ([API 9](#9-consultar-los-datos-de-identidad-de-una-persona)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "CC",
    "identification_number": "1012345678",
    "first_name": "Ana",
    "middle_name": "María",
    "last_name": "Pérez",
    "second_last_name": "Gómez",
    "birth_date": "1990-05-20",
    "verification_status": "VERIFIED"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `person_identity_id` | UUID | Sí | Persona a modificar | `a0e1d2c3-b4a5-4968-8776-655443322110` | `id` de la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) (devuelve la identidad de la persona; errores en §9) o `person_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) · guía [person_identity_id](../parametros/person-identity-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": "María",
  "last_name": "Pérez",
  "second_last_name": "Gómez",
  "birth_date": "1990-05-20",
  "verification_status": "VERIFIED"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la identidad | `1` | `version` de la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) (devuelve la identidad de la persona; errores en §9) |
| `identification_country_id` | UUID | Sí | País del documento (repetir el actual si no cambia) | `c0a80101-0000-4000-8000-000000000001` | `identification_country_id` de la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona), o `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` si cambia (lista los países) · guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string (1–40) | Sí | Sigla del tipo de documento | `CC` | `identification_type` de la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona), o `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) si cambia (lista los tipos de identificación; errores en §5) |
| `identification_number` | string (1–40) | Sí | Número del documento | `1012345678` | Formulario (validar con `number_pattern` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)) |
| `first_name`, `last_name` | string (1–100) | Sí | Primer nombre y primer apellido | `Ana`, `Pérez` | Formulario |
| `middle_name`, `second_last_name` | string (≤ 100) \| null | No; aceptan `null` | Segundo nombre y segundo apellido | `María`, `Gómez` | Formulario |
| `birth_date` | date \| null | Según la regla del documento | Fecha de nacimiento, no futura | `1990-05-20` | Formulario |
| `verification_status` | `UNVERIFIED` \| `VERIFIED` \| `SUSPENDED` | **Sí** (a diferencia de la creación) | Estado de verificación final | `VERIFIED` | Formulario; repetir el actual de la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) si no cambia |

### Respuesta exitosa

`200 OK` (`PersonIdentityResponse`) con `version` incrementada si hubo cambios:

```json
{
  "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "CC",
  "identification_number": "1012345678",
  "first_name": "Ana",
  "middle_name": "María",
  "last_name": "Pérez",
  "second_last_name": "Gómez",
  "birth_date": "1990-05-20",
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión para la siguiente modificación; se mantiene si no hubo cambios |
| `status` | `ACTIVE` \| `INACTIVE` | No cambia con esta API |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La persona no existe | Volver a la ficha del cliente |
| `409` | `PARTY_IDENTITY.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 9](#9-consultar-los-datos-de-identidad-de-una-persona) y repetir con la nueva `version` |
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | El nuevo país + tipo + número ya pertenece a otra identidad | Informar; no se puede unificar desde el frontend |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple la regla de la sigla | Mostrar `detail` junto al número |
| `422` | `PARTY_IDENTITY.BIRTH_DATE_REQUIRED` / `AGE_OUT_OF_RANGE` / `BIRTH_DATE_IN_FUTURE` | Fecha de nacimiento ausente, fuera del rango de edad o futura | Corregir la fecha |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | El país no existe en Geography | Volver a cargar el selector de país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente (incluido `verification_status`), longitud fuera de rango o campo desconocido | Corregir el formulario |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Geography no responde al validar el país | Reintentar más tarde |

Ejemplo de `409` por versión:

```json
{
  "type": "https://sio/errors/party-identity/version-conflict",
  "title": "Versión desactualizada",
  "status": 409,
  "detail": "El registro fue modificado por otra operación. Consulte nuevamente antes de actualizar.",
  "instance": "/api/v1/person-identities/a0e1d2c3-b4a5-4968-8776-655443322110",
  "code": "PARTY_IDENTITY.VERSION_CONFLICT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 14. Actualizar la identidad de una organización

**Método:** `PUT`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`
**Permiso requerido:** `perm:party-identity:organization_identities:update`

### ¿Qué hace esta API?

Corrige los datos legales de una organización: identificación, razón social, nombre comercial y datos de registro. Reemplazo completo con `version`. Como la identidad es global, el cambio lo ven todas las empresas que la tengan como cliente o proveedor y, si la organización es una empresa de SIO, también la [Administración empresarial](administracion-empresarial.md).

Efectos verificados en el código: comprueba existencia y `version`; sin cambios devuelve el registro actual sin escribir; si cambian país, tipo o número revalida la regla y la unicidad.

Antes necesita: la ficha actual con su `version` ([API 10](#10-consultar-los-datos-de-identidad-de-una-organización)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "identification_type": "NIT",
    "identification_number": "900123456",
    "legal_name": "Droguería La Economía S.A.S.",
    "trade_name": "La Economía",
    "organization_type": "SAS",
    "registration_status": "VIGENTE",
    "website": "https://www.laeconomia.example"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Organización a modificar | `0f1e2d3c-4b5a-4968-8776-655443322111` | `id` de la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) (devuelve la identidad de la organización; errores en §10) u `organization_identity_id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": "La Economía",
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": "https://www.laeconomia.example"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la identidad | `1` | `version` de la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) (devuelve la identidad de la organización; errores en §10) |
| `country_id` | UUID | Sí | País de registro (repetir el actual si no cambia) | `c0a80101-0000-4000-8000-000000000001` | `country_id` de la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización), o `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` si cambia (lista los países) · guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `identification_type` | string (1–40) | Sí | Sigla del tipo de identificación | `NIT` | `identification_type` de la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización), o `items[].sigla` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país) con `party_kind=ORGANIZATION` si cambia |
| `identification_number` | string (1–40) | Sí | Número de identificación | `900123456` | Formulario (validar con `number_pattern` de la [API 5](#5-consultar-los-tipos-de-identificación-admitidos-por-país)) |
| `legal_name` | string (1–200) | Sí | Razón social final | `Droguería La Economía S.A.S.` | Formulario |
| `trade_name` | string (≤ 200) \| null | No; acepta `null` | Nombre comercial | `La Economía` | Formulario |
| `organization_type` | string (≤ 40) \| null | No; acepta `null` | Tipo societario | `SAS` | Formulario |
| `registration_status` | string (≤ 30) \| null | No; acepta `null` | Estado del registro mercantil | `VIGENTE` | Formulario |
| `website` | string (≤ 300) \| null | No; acepta `null` | Sitio web | `https://www.laeconomia.example` | Formulario |

### Respuesta exitosa

`200 OK` (`OrganizationIdentityResponse`) con `version` incrementada si hubo cambios:

```json
{
  "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "identification_type": "NIT",
  "identification_number": "900123456",
  "legal_name": "Droguería La Economía S.A.S.",
  "trade_name": "La Economía",
  "organization_type": "SAS",
  "registration_status": "VIGENTE",
  "website": "https://www.laeconomia.example",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión para la siguiente modificación; se mantiene si no hubo cambios |
| `status` | `ACTIVE` \| `INACTIVE` | No cambia con esta API |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La organización no existe | Volver a la ficha del cliente |
| `409` | `PARTY_IDENTITY.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 10](#10-consultar-los-datos-de-identidad-de-una-organización) y repetir |
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | El nuevo país + tipo + número ya pertenece a otra identidad | Informar |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple la regla de la sigla | Mostrar `detail` junto al número |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | El país no existe en Geography | Volver a cargar el selector de país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango o campo desconocido | Corregir el formulario |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Geography no responde al validar el país | Reintentar más tarde |

## 15. Inactivar un cliente

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/deactivate`
**Permiso requerido:** `perm:commercial-relationship:company_customers:delete`

### ¿Qué hace esta API?

Pasa el cliente a `INACTIVE` sin borrarlo ni borrar su historial. Desde ese momento [Ventas](ventas.md) rechaza nuevas ventas a ese cliente con `409 SALES.REFERENCES_NOT_ELIGIBLE`; las ventas ya registradas no cambian. La identidad en Party Identity no se toca. Es la única escritura permitida cuando la empresa está `INACTIVE`. Registra `DEACTIVATE_COMPANY_CUSTOMER` en Audit.

Antes necesita: la `version` actual ([API 8](#8-consultar-un-cliente)). Conviene pedir confirmación al usuario.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/deactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 2
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_customer_id` | UUID | Sí | Cliente a inactivar | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) o `items[].id` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (lista los clientes; errores en §7) · guía [customer_id](../parametros/customer-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 2
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del cliente | `2` | `version` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) |

### Respuesta exitosa

`200 OK` (`CompanyCustomerResponse`) con `status` `INACTIVE` y `version` incrementada:

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "INACTIVE",
  "version": 3,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:00:00Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": null,
  "internal_code": "CLI-0001",
  "display_name": "Ana María Pérez",
  "preferred_contact_person_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `INACTIVE` | El cliente deja de aparecer en la lista por defecto de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) (usar `status=INACTIVE` o `ALL`) |
| `version` | integer | Valor que debe enviarse en la [API 16](#16-reactivar-un-cliente) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 8](#8-consultar-un-cliente) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El cliente ya está `INACTIVE` | Refrescar la ficha; no es necesario repetir |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente, < 1 o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde | Reintentar más tarde |

Ejemplo de `409` por estado:

```json
{
  "type": "https://sio/errors/commercial-relationship/invalid-status-transition",
  "title": "Transición de estado inválida",
  "status": 409,
  "detail": "La acción no es válida para el estado actual del registro.",
  "instance": "/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/deactivate",
  "code": "COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 16. Reactivar un cliente

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/reactivate`
**Permiso requerido:** `perm:commercial-relationship:company_customers:update`

### ¿Qué hace esta API?

Devuelve un cliente `INACTIVE` a `ACTIVE` conservando su `id`, su código y su historial, de modo que [Ventas](ventas.md) vuelve a aceptarlo. Es la respuesta correcta al `409 DUPLICATE_CUSTOMER` de la [API 6](#6-registrar-un-cliente-de-la-empresa) cuando la identidad ya fue cliente antes.

Efectos verificados en el código: antes de reactivar vuelve a comprobar en Party Identity que la identidad exista y esté `ACTIVE` (no revalida la persona de contacto); exige empresa `ACTIVE`; registra `REACTIVATE_COMPANY_CUSTOMER` en Audit.

Antes necesita: la `version` actual ([API 8](#8-consultar-un-cliente)) y permisos de lectura en Party Identity (`perm:party-identity:person_identities:read` u `organization_identities:read`) para la revalidación.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/reactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 3
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_customer_id` | UUID | Sí | Cliente a reactivar | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `id` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) o `items[].id` de la [API 7](#7-buscar-y-listar-los-clientes-de-la-empresa) con `status=INACTIVE` (lista los clientes; errores en §7) · guía [customer_id](../parametros/customer-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 3
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del cliente | `3` | `version` de la [API 8](#8-consultar-un-cliente) (devuelve la ficha del cliente; errores en §8) |

### Respuesta exitosa

`200 OK` (`CompanyCustomerResponse`) con `status` `ACTIVE` y `version` incrementada:

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 4,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": null,
  "internal_code": "CLI-0001",
  "display_name": "Ana María Pérez",
  "preferred_contact_person_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` | El cliente vuelve a estar disponible para ventas |
| `version` | integer | Nueva versión para la siguiente modificación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 8](#8-consultar-un-cliente) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El cliente ya está `ACTIVE` | Refrescar la ficha |
| `422` | `COMMERCIAL_RELATIONSHIP.PERSON_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_NOT_FOUND` | La identidad ya no existe en Party Identity | Informar; registrar un cliente nuevo con otra identidad |
| `422` | `COMMERCIAL_RELATIONSHIP.PERSON_IDENTITY_INACTIVE` / `ORGANIZATION_IDENTITY_INACTIVE` | La identidad está `INACTIVE` en Party Identity | Reactivar primero la identidad (PI 8 / PI 14) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden reactivar clientes en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente, < 1 o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Sin permiso en Party Identity para revalidar la identidad | Pedir el permiso de lectura correspondiente |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden | Reintentar más tarde; nada se guardó |

---

## Dependencias con otros módulos

- [Ventas](ventas.md) exige un `company_customer_id` con `status` `ACTIVE` al crear el borrador de venta; un cliente inactivo se rechaza con `409 SALES.REFERENCES_NOT_ELIGIBLE`. Las ventas son de contado: las condiciones de pago a crédito por cliente no están implementadas en Sales (funcionalidad futura).
- [Administración empresarial](administracion-empresarial.md) y [Gestión de proveedores](gestion-de-proveedores.md) comparten las identidades de Party Identity: una organización puede ser a la vez empresa de SIO, proveedor y cliente de distintas empresas. Los proveedores son siempre organizaciones; los clientes pueden ser personas u organizaciones.
- [Reportes](reportes.md) agrupa ventas por sucursal y producto; no por cliente (no hay reporte por cliente en las 411 operaciones).
- La trazabilidad de las cuatro escrituras sobre clientes se consulta en la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (eventos `CREATE_COMPANY_CUSTOMER`, `UPDATE_COMPANY_CUSTOMER`, `DEACTIVATE_COMPANY_CUSTOMER`, `REACTIVATE_COMPANY_CUSTOMER`, entidad `CompanyCustomer`).

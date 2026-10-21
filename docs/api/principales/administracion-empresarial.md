# 6.2 Administración empresarial

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un administrador configura una empresa cliente de SIO: la empresa misma, sus sucursales, las personas que trabajan en ella (membresías), las sucursales a las que cada una puede acceder, la trazabilidad de lo que ocurre en la empresa (auditoría) y la numeración de los documentos comerciales.

Servicios implicados: [Operational Context](../servicios/operational-context.md) (empresas, sucursales, membresías y asignaciones), [Party Identity](../servicios/party-identity.md) (identidad legal de la empresa y de cada persona), [Geography](../servicios/geography.md) (ubicación), [Audit](../servicios/audit.md) (trazabilidad) y las secuencias de [Sales](../servicios/sales.md) y [Purchase](../servicios/purchase.md) (numeración). Flujo completo: [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Crear empresa | `POST https://sio-operational-context-dev.onrender.com/api/v1/companies` | `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer` | [OC 4](../servicios/operational-context.md#4-post-companies) |
| 2 | Consultar las empresas del usuario | `GET https://sio-operational-context-dev.onrender.com/api/v1/companies` | `perm:operational-context:companies:read` | [OC 3](../servicios/operational-context.md#3-get-companies) |
| 3 | Consultar una empresa | `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}` | `perm:operational-context:companies:read` | [OC 5](../servicios/operational-context.md#5-get-companiescompany_id) |
| 4 | Actualizar una empresa | `PUT https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}` | `perm:operational-context:companies:update` | [OC 6](../servicios/operational-context.md#6-put-companiescompany_id) |
| 5 | Crear una sucursal | `POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches` | `perm:operational-context:branches:create` | [OC 10](../servicios/operational-context.md#10-post-companiescompany_idbranches) |
| 6 | Consultar las sucursales de una empresa | `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches` | `perm:operational-context:branches:read` | [OC 9](../servicios/operational-context.md#9-get-companiescompany_idbranches) |
| 7 | Consultar una sucursal | `GET https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}` | `perm:operational-context:branches:read` | [OC 11](../servicios/operational-context.md#11-get-branchesbranch_id) |
| 8 | Actualizar una sucursal | `PUT https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}` | `perm:operational-context:branches:update` | [OC 12](../servicios/operational-context.md#12-put-branchesbranch_id) |
| 9 | Consultar los usuarios de una empresa | `GET https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` | `perm:operational-context:application_users:read` | [OC 15](../servicios/operational-context.md#15-get-companiescompany_idapplication-users) |
| 10 | Asociar un usuario a una empresa (crear membresía) | `POST https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` | `perm:operational-context:application_users:create` | [OC 16](../servicios/operational-context.md#16-post-companiescompany_idapplication-users) |
| 11 | Consultar las sucursales asignadas a un usuario | `GET https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` | `perm:operational-context:user_branches:read` | [OC 21](../servicios/operational-context.md#21-get-application-usersapplication_user_iduser-branches) |
| 12 | Asignar un usuario a una sucursal | `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` | `perm:operational-context:user_branches:create` | [OC 22](../servicios/operational-context.md#22-post-application-usersapplication_user_iduser-branches) |
| 13 | Consultar los usuarios asignados a una sucursal | `GET https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/user-branches` | `perm:operational-context:user_branches:read` | [OC 23](../servicios/operational-context.md#23-get-branchesbranch_iduser-branches) |
| 14 | Inactivar una membresía | `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/deactivate` | `perm:operational-context:application_users:delete` | [OC 19](../servicios/operational-context.md#19-post-application-usersapplication_user_iddeactivate) |
| 15 | Reactivar una membresía | `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/reactivate` | `perm:operational-context:application_users:update` | [OC 20](../servicios/operational-context.md#20-post-application-usersapplication_user_idreactivate) |
| 16 | Consultar la trazabilidad de la empresa (auditoría) | `GET https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events` y `…/audit-events/{audit_id}` | `perm:audit:audit-events:read` | [Audit 5](../servicios/audit.md#5-get-companiescompany_idaudit-events) · [Audit 6](../servicios/audit.md#6-get-companiescompany_idaudit-eventsaudit_id) |
| 17 | Consultar el historial de una venta, una compra o un producto | `GET https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}` | `perm:audit:audit-events:read` | [Audit 7](../servicios/audit.md#7-get-companiescompany_identity-historyentity_typeentity_id) |
| 18 | Consultar las secuencias de numeración | `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` y `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` | `perm:sales:sale_sequences:read` · `perm:purchase:purchase_sequences:read` | [Sales 17](../servicios/sales.md#17-get-companiescompany_idsale-sequences) · [Purchase 19](../servicios/purchase.md#19-get-companiescompany_idpurchase-sequences) |
| 19 | Crear una secuencia de numeración | `POST …/sale-sequences` y `POST …/purchase-sequences` | `perm:sales:sale_sequences:create` · `perm:purchase:purchase_sequences:create` | [Sales 16](../servicios/sales.md#16-post-companiescompany_idsale-sequences) · [Purchase 18](../servicios/purchase.md#18-post-companiescompany_idpurchase-sequences) |
| 20 | Desactivar o reactivar una secuencia | `POST …/sale-sequences/{sequence_id}/deactivate` · `…/reactivate` y `POST …/purchase-sequences/{sequence_id}/deactivate` · `…/reactivate` | `perm:sales:sale_sequences:update` · `perm:purchase:purchase_sequences:update` | [Sales 20](../servicios/sales.md#20-post-companiescompany_idsale-sequencessequence_iddeactivate) · [Sales 21](../servicios/sales.md#21-post-companiescompany_idsale-sequencessequence_idreactivate) · [Purchase 22](../servicios/purchase.md#22-post-companiescompany_idpurchase-sequencessequence_iddeactivate) · [Purchase 23](../servicios/purchase.md#23-post-companiescompany_idpurchase-sequencessequence_idreactivate) |
| 21 | Consultar y modificar una secuencia | `GET` · `PUT …/sale-sequences/{sequence_id}` y `GET` · `PUT …/purchase-sequences/{sequence_id}` | `perm:sales:sale_sequences:read` · `…:update` · `perm:purchase:purchase_sequences:read` · `…:update` | [Sales 18](../servicios/sales.md#18-get-companiescompany_idsale-sequencessequence_id) · [Sales 19](../servicios/sales.md#19-put-companiescompany_idsale-sequencessequence_id) · [Purchase 20](../servicios/purchase.md#20-get-companiescompany_idpurchase-sequencessequence_id) · [Purchase 21](../servicios/purchase.md#21-put-companiescompany_idpurchase-sequencessequence_id) |

Operaciones relacionadas que no se consideran principales (ver las fichas): inactivar o reactivar empresas y sucursales (OC 7, 8, 13, 14), retirar o reactivar una asignación de sucursal (OC 25, 26), modificar los datos de referencia de un usuario (OC 18), la gestión de asesores (OC 27–31) y los eventos de auditoría de plataforma (Audit 8–10).

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Las cuatro API de escritura de Operational Context con cuerpo JSON **rechazan campos desconocidos** con `422` (modelos estrictos). Las de Sales y Purchase también.
- Errores comunes a todas las API de SIO de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `…FORBIDDEN` cuando el token no tiene el permiso indicado (mostrar que faltan permisos y el `trace_id`); `503` con `code` `…DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde (reintentar más tarde). Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `OPERATIONAL_CONTEXT.…`, `AUDIT.…`, `SALES.…` o `PURCHASE.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).
- **Alcance por empresa.** Operational Context solo muestra una empresa a quien tiene membresía `ACTIVE` en ella o el permiso `perm:operational-context:platform:administer`. Fuera de ese alcance la respuesta es `404 OPERATIONAL_CONTEXT.NOT_FOUND`, igual que si no existiera. Audit, Sales y Purchase responden también `404` sin membresía `ACTIVE`.
- **Control de versión.** Toda modificación envía la `version` actual del recurso; si otra persona lo cambió antes, la API responde `409 …VERSION_CONFLICT` y el frontend debe volver a leer el recurso y repetir con la nueva `version`.
- Las respuestas de Operational Context traen siempre `created_by`, `updated_by` (el `sub` de Keycloak de quien actuó), `created_at` y `updated_at`.

---

## 1. Crear empresa

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies`
**Permiso requerido:** `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer` (ambos; en el realm de desarrollo solo el grupo `administradores` tiene el segundo).

### ¿Qué hace esta API?

Da de alta una empresa cliente de SIO vinculándola a la identidad legal de una organización registrada en Party Identity. La usa el administrador de la plataforma al incorporar un nuevo cliente. La empresa no tiene campo `name`: la razón social, el nombre comercial y el NIT viven en Party Identity y se consultan con `organization_identity_id`.

Efectos verificados en el código: crear la empresa **no crea sucursales ni membresías**. Quien la creó la ve gracias a `platform:administer`; el primer usuario de la empresa se incorpora con la [API 10](#10-asociar-un-usuario-a-una-empresa-crear-membresía) y sus sucursales se crean con la [API 5](#5-crear-una-sucursal).

Antes necesita: la identidad de la organización en Party Identity (`POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities`, ver [organization_identity_id](../parametros/organization-identity-id.md)), que debe estar `ACTIVE` y no estar vinculada a otra empresa. Si se envía dirección, los tres identificadores geográficos coherentes entre sí ([country_id, administrative_division_id, city_id](../parametros/country-id.md)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "email": "contacto@empresa-ejemplo.test",
    "phone": "+57 601 000 0000",
    "address_line": "Calle 1 # 2-3",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "postal_code": "110111",
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "timezone": "America/Bogota",
    "default_currency": "COP"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Obligatorio | Valor |
|---|---|---|
| `Authorization` | Sí | `Bearer TU_ACCESS_TOKEN` |
| `Content-Type` | Sí | `application/json` |

### Cuerpo de la solicitud (Body)

Modelo `CompanyCreate`:

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@empresa-ejemplo.test",
  "phone": "+57 601 000 0000",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP"
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Identidad legal de la organización; debe estar `ACTIVE` y solo puede tener una empresa | `0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` (busca organizaciones por identificación o nombre) o `id` de la respuesta `201` de su `POST` (registra la organización) · qué hacen y sus errores en la guía [organization_identity_id](../parametros/organization-identity-id.md) |
| `email` | string (correo) \| null | No; acepta `null` | Correo de contacto; una cadena vacía se guarda como `null` | `contacto@empresa-ejemplo.test` | Formulario |
| `phone` | string (≤ 40) \| null | No; acepta `null` | Teléfono de contacto | `+57 601 000 0000` | Formulario |
| `address_line` | string \| null | No; acepta `null` | Dirección | `Calle 1 # 2-3` | Formulario |
| `country_id` | UUID \| null | No; acepta `null` | País de la dirección; debe estar `ACTIVE` en Geography | `c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `administrative_division_id` | UUID \| null | No; acepta `null` | Departamento o estado; debe pertenecer al país | `c0a80101-0000-4000-8000-000000000002` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-administrative-divisions?country_id=…` (lista las divisiones del país) · qué hace y errores en la guía [administrative_division_id](../parametros/country-id.md#cómo-obtener-administrative_division_id) |
| `city_id` | UUID \| null | No; acepta `null` | Ciudad; debe pertenecer a la división | `c0a80101-0000-4000-8000-000000000003` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=…` (lista las ciudades de la división) · qué hace y errores en la guía [city_id](../parametros/country-id.md#cómo-obtener-city_id) |
| `postal_code` | string (≤ 20) \| null | No; acepta `null` | Código postal | `110111` | Formulario |
| `latitude` | decimal \| null | No; acepta `null` | Coordenada; se acepta como número o cadena; se validan ambas coordenadas juntas | `"4.6097"` | Formulario |
| `longitude` | decimal \| null | No; acepta `null` | Coordenada | `"-74.0817"` | Formulario |
| `timezone` | string (1–60) | No; valor por defecto `America/Bogota` | Zona horaria IANA de la empresa; la heredan las sucursales sin zona propia. Una zona inexistente responde `422` | `America/Bogota` | Formulario |
| `default_currency` | string | No; valor por defecto `COP` | Moneda por defecto; se guarda en mayúsculas | `COP` | Formulario |

Si se envía `country_id`, `administrative_division_id` o `city_id`, los tres deben ser coherentes entre sí (la ciudad pertenece a la división y esta al país). No se admite `{}`: `organization_identity_id` es obligatorio.

### Respuesta exitosa

`201 Created` (`CompanyResponse`), con cabecera `Location: /api/v1/companies/{id}`:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@empresa-ejemplo.test",
  "phone": "+57 601 000 0000",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [company_id](../parametros/company-id.md); se usa en todas las rutas `/companies/{company_id}/…` |
| `organization_identity_id` | UUID | Identidad con la razón social (Party Identity) |
| `status` | `ACTIVE` \| `INACTIVE` | Siempre `ACTIVE` al crear |
| `version` | integer | Siempre `1` al crear; se envía en la [API 4](#4-actualizar-una-empresa) |
| `latitude`, `longitude` | string decimal \| null | Las coordenadas se devuelven como cadenas |
| `timezone`, `default_currency` | string | Los valores aplicados (enviados o por defecto) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `companies:create` o `platform:administer` | Solo un administrador de plataforma puede crear empresas |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_ORGANIZATION_IDENTITY` | Esa organización ya tiene una empresa | Buscar la empresa existente ([API 2](#2-consultar-las-empresas-del-usuario)) en lugar de crearla |
| `422` | `OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND` | `organization_identity_id` no existe en Party Identity | Registrar o buscar la identidad |
| `422` | `OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_INACTIVE` | La identidad está inactiva | Reactivarla en Party Identity |
| `422` | `OPERATIONAL_CONTEXT.COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND` | Un identificador geográfico no existe | Corregir la ubicación |
| `422` | `OPERATIONAL_CONTEXT.LOCATION_INACTIVE` | País, división o ciudad inactivos en Geography | Elegir una ubicación activa |
| `422` | `OPERATIONAL_CONTEXT.GEOGRAPHY_INCOHERENT` | La ciudad no pertenece a la división o esta al país | Corregir la ubicación |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Campo con formato inválido (correo, coordenadas, zona horaria inexistente, moneda vacía) o campo desconocido; `errors[]` indica el campo | Corregir el formulario |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Party Identity o Geography no responden (`dependency` lo indica) | Reintentar más tarde |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/operational-context/duplicate-organization-identity",
  "title": "Organización ya vinculada",
  "status": 409,
  "detail": "La organización indicada ya está vinculada a otra empresa.",
  "instance": "/api/v1/companies",
  "code": "OPERATIONAL_CONTEXT.DUPLICATE_ORGANIZATION_IDENTITY",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "La organización indicada ya está vinculada a otra empresa.",
      "code": "DUPLICATE_ORGANIZATION_IDENTITY"
    }
  ]
}
```

## 2. Consultar las empresas del usuario

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies`
**Permiso requerido:** `perm:operational-context:companies:read`

### ¿Qué hace esta API?

Lista, con paginación, las empresas en las que el usuario tiene membresía `ACTIVE`; para un administrador de plataforma lista todas. Sirve para la pantalla de administración de empresas y para mostrar los datos de contacto de las empresas del contexto operativo. Por defecto solo devuelve empresas `ACTIVE`. No admite búsqueda por nombre: la razón social no está en este servicio.

Antes necesita: solo el Access Token.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies?page=1&page_size=20&status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Número de página | Entero desde `1`; p. ej. `1` | `?page=1` | Paginación de la interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Paginación de la interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de las empresas a listar | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Filtro de la interfaz |
| `organization_identity_id` | UUID | No | Solo la empresa de esa organización | UUID; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&organization_identity_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` (busca organizaciones por identificación o nombre) o `id` de la respuesta `201` de su `POST` (registra la organización) · qué hacen y sus errores en la guía [organization_identity_id](../parametros/organization-identity-id.md) |
| `country_id` | UUID | No | Empresas con dirección en ese país | UUID; p. ej. `c0a80101-0000-4000-8000-000000000001` | `&country_id=c0a80101-0000-4000-8000-000000000001` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-countries` (lista los países del catálogo global) · qué hace y errores en la guía [country_id](../parametros/country-id.md#cómo-obtener-country_id) |
| `city_id` | UUID | No | Empresas con dirección en esa ciudad | UUID; p. ej. `c0a80101-0000-4000-8000-000000000003` | `&city_id=c0a80101-0000-4000-8000-000000000003` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=…` (lista las ciudades de la división) · qué hace y errores en la guía [city_id](../parametros/country-id.md#cómo-obtener-city_id) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-operational-context-dev.onrender.com/api/v1/companies?page=1&page_size=20&status=ACTIVE`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyResponse]`):

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "email": "contacto@empresa-ejemplo.test",
      "phone": "+57 601 000 0000",
      "address_line": "Calle 1 # 2-3",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": "110111",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[]` | array de `CompanyResponse` | Las empresas de la página; mismos campos que la [API 1](#1-crear-empresa). Un usuario sin membresías recibe `[]` |
| `page`, `page_size` | integer | Página devuelta y tamaño aplicado |
| `total_records` | integer | Total de empresas que cumplen el filtro |
| `total_pages` | integer | Total de páginas; `0` si no hay registros |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `page` < 1, `page_size` fuera de 1–100, `status` distinto de `ACTIVE`/`INACTIVE` o un UUID mal formado | Corregir los parámetros |

Un usuario sin membresías no recibe error: recibe `items: []`.

## 3. Consultar una empresa

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`
**Permiso requerido:** `perm:operational-context:companies:read`

### ¿Qué hace esta API?

Devuelve la ficha completa de una empresa, en cualquier estado, si está en el alcance del usuario. Se usa para mostrar los datos de la empresa seleccionada en la sesión y para leer su `version` antes de modificarla. Para mostrar la razón social hay que consultar además Party Identity con `organization_identity_id` (`GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}`, permiso `perm:party-identity:organization_identities:read`).

Antes necesita: el `company_id` de la empresa (del contexto operativo o de la [API 2](#2-consultar-las-empresas-del-usuario)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa a consultar | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CompanyResponse`), mismo objeto y campos que la respuesta de la [API 1](#1-crear-empresa):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "contacto@empresa-ejemplo.test",
  "phone": "+57 601 000 0000",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | Una empresa `INACTIVE` se puede consultar pero no modificar ni operar |
| `version` | integer | Valor que debe enviarse en la [API 4](#4-actualizar-una-empresa) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella (ni `platform:administer` ni `platform:lookup`) | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `company_id` no es un UUID | Corregir el identificador |

## 4. Actualizar una empresa

**Método:** `PUT`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}`
**Permiso requerido:** `perm:operational-context:companies:update`

### ¿Qué hace esta API?

Reemplaza los datos de contacto, dirección, zona horaria y moneda de una empresa. Es un reemplazo completo: hay que enviar todos los campos con su valor final (los que no se envían quedan en `null`), más la `version` leída. Si nada cambia, no escribe ni incrementa la versión. `organization_identity_id` debe enviarse con el mismo valor: cambiarlo a otra organización responde `409` si esa organización ya tiene empresa o `422` si no existe o está inactiva. Una empresa `INACTIVE` no se puede modificar.

Antes necesita: la ficha actual de la empresa ([API 3](#3-consultar-una-empresa)) para conocer todos sus valores y su `version`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "email": "ventas@empresa-ejemplo.test",
    "phone": "+57 601 000 0001",
    "address_line": "Calle 1 # 2-3",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "postal_code": "110111",
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "timezone": "America/Bogota",
    "default_currency": "COP",
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa a modificar | `550e8400-e29b-41d4-a716-446655440000` | `id` de la [API 3](#3-consultar-una-empresa) (devuelve la ficha de la empresa; errores en §3) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `CompanyUpdate`: los mismos campos de la [API 1](#1-crear-empresa), con `timezone` y `default_currency` **obligatorios** (sin valor por defecto) y `version`:

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "ventas@empresa-ejemplo.test",
  "phone": "+57 601 000 0001",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "version": 1
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Debe repetirse el valor actual | `0f1e2d3c-4b5a-4968-8776-655443322111` | `organization_identity_id` de la [API 3](#3-consultar-una-empresa) (devuelve la ficha de la empresa); se repite sin cambios |
| `email`, `phone`, `address_line`, `postal_code` | string \| null | No; aceptan `null` | Valor final de cada dato; omitir un campo lo deja en `null` | — | Formulario |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | No; aceptan `null` | Ubicación final, coherente entre sí; Geography solo se consulta si cambia | — | `items[].id` de `GET …/global-countries`, `GET …/global-administrative-divisions` y `GET …/global-cities` de Geography (selectores en cascada país → división → ciudad) · qué hace cada una y sus errores en la guía [country_id, administrative_division_id, city_id](../parametros/country-id.md) |
| `latitude`, `longitude` | decimal \| null | No; aceptan `null` | Coordenadas | `"4.6097"` | Formulario |
| `timezone` | string (1–60) | **Sí** | Zona horaria IANA | `America/Bogota` | [API 3](#3-consultar-una-empresa) o formulario |
| `default_currency` | string | **Sí** | Moneda por defecto | `COP` | [API 3](#3-consultar-una-empresa) o formulario |
| `version` | integer ≥ 1 | Sí | Versión leída en la [API 3](#3-consultar-una-empresa) | `1` | [API 3](#3-consultar-una-empresa) |

### Respuesta exitosa

`200 OK` (`CompanyResponse`) con los datos aplicados y `version` incrementada (o igual, si nada cambió):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "email": "ventas@empresa-ejemplo.test",
  "phone": "+57 601 000 0001",
  "address_line": "Calle 1 # 2-3",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": "110111",
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión; guardarla para la siguiente modificación |
| `updated_at`, `updated_by` | date-time, string | Momento y autor del cambio |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Empresa inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `409` | `OPERATIONAL_CONTEXT.VERSION_CONFLICT` | La `version` enviada no es la actual | Releer la empresa ([API 3](#3-consultar-una-empresa)) y repetir con la nueva `version` |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_ORGANIZATION_IDENTITY` | Se intentó cambiar a una organización que ya tiene empresa | Mantener `organization_identity_id` |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se puede modificar; reactivarla primero (OC 8, administrador de plataforma) |
| `422` | `OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND` / `_INACTIVE`, `COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND`, `LOCATION_INACTIVE`, `GEOGRAPHY_INCOHERENT` | Referencias inválidas, como en la [API 1](#1-crear-empresa) | Corregir el formulario |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `timezone`, `default_currency` o `version`, formato inválido o campo desconocido | Corregir el formulario |

## 5. Crear una sucursal

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches`
**Permiso requerido:** `perm:operational-context:branches:create`

### ¿Qué hace esta API?

Registra un punto de operación de la empresa (tienda, bodega, farmacia) donde se venderá, comprará y controlará inventario. La empresa debe estar `ACTIVE`. El `code` es único dentro de la empresa y se guarda en mayúsculas. Si no se envía `timezone`, la sucursal hereda la de la empresa (la respuesta lo muestra en `effective_timezone`).

Efecto verificado: crear la sucursal **no la asigna a ningún usuario**. Cada usuario que deba operar en ella se asigna con la [API 12](#12-asignar-un-usuario-a-una-sucursal). Para confirmar ventas o compras en ella hará falta además una secuencia de numeración ([API 19](#19-crear-una-secuencia-de-numeración)) propia o de la empresa.

Antes necesita: el `company_id` de una empresa `ACTIVE` en la que el administrador tenga membresía (o `platform:administer`) y, si lleva dirección, los identificadores geográficos.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
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
    "postal_code": null,
    "latitude": null,
    "longitude": null,
    "timezone": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `BranchCreate`. No admite `company_id` en el cuerpo (viene de la ruta): enviarlo responde `422`.

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
  "postal_code": null,
  "latitude": null,
  "longitude": null,
  "timezone": null
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `code` | string | Sí | Código único por empresa; se normaliza a mayúsculas y sin espacios en los extremos | `SUC-002` | Formulario |
| `name` | string (1–160) | Sí | Nombre de la sucursal | `Sucursal Norte` | Formulario |
| `email` | string (correo) \| null | No; acepta `null` | Correo de contacto | `norte@empresa-ejemplo.test` | Formulario |
| `phone` | string (≤ 40) \| null | No; acepta `null` | Teléfono | `+57 601 000 0002` | Formulario |
| `address_line` | string \| null | No; acepta `null` | Dirección | `Autopista Norte # 100-20` | Formulario |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | No; aceptan `null` | Ubicación coherente y activa en Geography | — | `items[].id` de `GET …/global-countries`, `GET …/global-administrative-divisions` y `GET …/global-cities` de Geography (selectores en cascada país → división → ciudad) · qué hace cada una y sus errores en la guía [country_id, administrative_division_id, city_id](../parametros/country-id.md) |
| `postal_code` | string (≤ 20) \| null | No; acepta `null` | Código postal | `null` | Formulario |
| `latitude`, `longitude` | decimal \| null | No; aceptan `null` | Coordenadas | `null` | Formulario |
| `timezone` | string (≤ 60) \| null | No; acepta `null` (valor por defecto) | Zona horaria propia; `null` hereda la de la empresa | `null` | Formulario |

### Respuesta exitosa

`201 Created` (`BranchResponse`), con cabecera `Location: /api/v1/branches/{id}`:

```json
{
  "id": "b361a654-58d4-422f-8ffe-9699a87e91e3",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-002",
  "name": "Sucursal Norte",
  "email": "norte@empresa-ejemplo.test",
  "phone": "+57 601 000 0002",
  "address_line": "Autopista Norte # 100-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": null,
  "longitude": null,
  "timezone": null,
  "effective_timezone": "America/Bogota",
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
| `id` | UUID | El nuevo [branch_id](../parametros/branch-id.md) que se envía en ventas, compras e inventario |
| `company_id`, `company_status` | UUID, `ACTIVE` \| `INACTIVE` | Empresa dueña y su estado |
| `code` | string | El código normalizado (mayúsculas) |
| `timezone` | string \| null | Zona propia o `null` si hereda |
| `effective_timezone` | string | Zona horaria que realmente aplica (propia o de la empresa); es la que fija la fecha de negocio de ventas y compras |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Empresa inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE` | Ya existe una sucursal con ese `code` en la empresa | Pedir otro código |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear sucursales en ella |
| `422` | `OPERATIONAL_CONTEXT.COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND`, `LOCATION_INACTIVE`, `GEOGRAPHY_INCOHERENT` | Ubicación inválida | Corregir la ubicación |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `code` o `name` vacíos, `name` > 160, correo o zona horaria inválidos, `company_id` u otro campo desconocido en el cuerpo | Corregir el formulario |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Geography no responde | Reintentar más tarde |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/operational-context/duplicate-branch-code",
  "title": "Código de sucursal duplicado",
  "status": 409,
  "detail": "Ya existe una sucursal con ese código en la empresa.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches",
  "code": "OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "code",
      "message": "Ya existe una sucursal con ese código en la empresa.",
      "code": "DUPLICATE_BRANCH_CODE"
    }
  ]
}
```

## 6. Consultar las sucursales de una empresa

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches`
**Permiso requerido:** `perm:operational-context:branches:read`

### ¿Qué hace esta API?

Lista, con paginación, **todas** las sucursales de la empresa (no solo las asignadas al usuario), con búsqueda por código o nombre. Sirve para la administración de sucursales y para mostrar el nombre de cada `branch_id` del contexto operativo. Por defecto solo devuelve sucursales `ACTIVE`. Para saber en cuáles puede operar el usuario, usar `memberships[].branches[]` del contexto operativo.

Antes necesita: el `company_id` y membresía en la empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches?page=1&page_size=20&status=ACTIVE&search=norte' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 160) | No | Búsqueda parcial, sin distinguir mayúsculas, en `code` y `name` | Texto libre (≤ 160 caracteres); p. ej. `norte` | `&search=norte` | Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de las sucursales | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `city_id` | UUID | No | Solo sucursales de esa ciudad | UUID; p. ej. `c0a80101-0000-4000-8000-000000000003` | `&city_id=c0a80101-0000-4000-8000-000000000003` | `items[].id` de `GET https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=…` (lista las ciudades de la división) · qué hace y errores en la guía [city_id](../parametros/country-id.md#cómo-obtener-city_id) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches?page=1&page_size=20&status=ACTIVE&search=norte`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[BranchResponse]`):

```json
{
  "items": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "code": "SUC-01",
      "name": "Sucursal Centro",
      "email": "centro@empresa-ejemplo.test",
      "phone": "+57 601 000 0001",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[]` | array de `BranchResponse` | Mismos campos que la [API 5](#5-crear-una-sucursal); `items[].id` es el `branch_id` |
| `items[].effective_timezone` | string | Zona horaria aplicable a la sucursal |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Empresa inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 160, `status` inválido o UUID mal formado | Corregir los parámetros |

## 7. Consultar una sucursal

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`
**Permiso requerido:** `perm:operational-context:branches:read`

### ¿Qué hace esta API?

Devuelve una sucursal por su identificador, en cualquier estado, con el estado de su empresa. Se usa para mostrar la sucursal seleccionada en la sesión (nombre, zona horaria) y para leer su `version` antes de modificarla. Solo necesita el `branch_id`; no hace falta conocer la empresa.

Antes necesita: el `branch_id` (del contexto operativo o de la [API 6](#6-consultar-las-sucursales-de-una-empresa)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal a consultar | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6](#6-consultar-las-sucursales-de-una-empresa) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`BranchResponse`):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro",
  "email": "centro@empresa-ejemplo.test",
  "phone": "+57 601 000 0001",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `company_id` | UUID | Empresa dueña; permite llegar a la empresa desde el `branch_id` |
| `company_status`, `status` | `ACTIVE` \| `INACTIVE` | Una sucursal solo es operable si ambos son `ACTIVE` |
| `version` | integer | Valor que se envía en la [API 8](#8-actualizar-una-sucursal) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La sucursal no existe o su empresa está fuera del alcance | Volver a leer el contexto operativo |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `branch_id` no es un UUID | Corregir el identificador |

## 8. Actualizar una sucursal

**Método:** `PUT`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}`
**Permiso requerido:** `perm:operational-context:branches:update`

### ¿Qué hace esta API?

Reemplaza los datos de una sucursal: código, nombre, contacto, dirección y zona horaria. Es un reemplazo completo con `version`. La empresa de la sucursal es inmutable (no se envía). Geography solo se consulta si cambia la ubicación.

Antes necesita: la sucursal actual ([API 7](#7-consultar-una-sucursal)) con todos sus valores y su `version`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "SUC-01",
    "name": "Sucursal Centro Histórico",
    "email": "centro@empresa-ejemplo.test",
    "phone": "+57 601 000 0001",
    "address_line": "Calle 10 # 5-20",
    "country_id": "c0a80101-0000-4000-8000-000000000001",
    "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
    "city_id": "c0a80101-0000-4000-8000-000000000003",
    "postal_code": null,
    "latitude": "4.6097",
    "longitude": "-74.0817",
    "timezone": "America/Bogota",
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal a modificar | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `id` de la [API 7](#7-consultar-una-sucursal) (devuelve la ficha de la sucursal; errores en §7) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `BranchUpdate`: los campos de la [API 5](#5-crear-una-sucursal) más `version`. No admite `company_id`.

```json
{
  "code": "SUC-01",
  "name": "Sucursal Centro Histórico",
  "email": "centro@empresa-ejemplo.test",
  "phone": "+57 601 000 0001",
  "address_line": "Calle 10 # 5-20",
  "country_id": "c0a80101-0000-4000-8000-000000000001",
  "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
  "city_id": "c0a80101-0000-4000-8000-000000000003",
  "postal_code": null,
  "latitude": "4.6097",
  "longitude": "-74.0817",
  "timezone": "America/Bogota",
  "version": 1
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `code` | string | Sí | Código único por empresa (mayúsculas) | `SUC-01` | [API 7](#7-consultar-una-sucursal) o formulario |
| `name` | string (1–160) | Sí | Nombre | `Sucursal Centro Histórico` | Formulario |
| `email`, `phone`, `address_line`, `postal_code` | string \| null | No; aceptan `null` | Valor final | — | Formulario |
| `country_id`, `administrative_division_id`, `city_id` | UUID \| null | No; aceptan `null` | Ubicación final coherente | — | `items[].id` de `GET …/global-countries`, `GET …/global-administrative-divisions` y `GET …/global-cities` de Geography (selectores en cascada país → división → ciudad) · qué hace cada una y sus errores en la guía [country_id, administrative_division_id, city_id](../parametros/country-id.md) |
| `latitude`, `longitude` | decimal \| null | No; aceptan `null` | Coordenadas | `"4.6097"` | Formulario |
| `timezone` | string (≤ 60) \| null | No; acepta `null` | Zona propia o `null` para heredar la de la empresa | `America/Bogota` | Formulario |
| `version` | integer ≥ 1 | Sí | Versión leída en la [API 7](#7-consultar-una-sucursal) | `1` | [API 7](#7-consultar-una-sucursal) |

### Respuesta exitosa

`200 OK` (`BranchResponse`) con los datos aplicados y `version` incrementada:

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "code": "SUC-01",
  "name": "Sucursal Centro Histórico",
  "email": "centro@empresa-ejemplo.test",
  "phone": "+57 601 000 0001",
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
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión para la próxima modificación |
| `effective_timezone` | string | Zona aplicable tras el cambio |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Sucursal inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `409` | `OPERATIONAL_CONTEXT.VERSION_CONFLICT` | `version` desactualizada | Releer ([API 7](#7-consultar-una-sucursal)) y repetir |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE` | Otro registro de la empresa ya usa ese `code` | Pedir otro código |
| `422` | `OPERATIONAL_CONTEXT.COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND`, `LOCATION_INACTIVE`, `GEOGRAPHY_INCOHERENT` | Ubicación inválida | Corregir la ubicación |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `code`, `name` o `version`; formato inválido; `company_id` u otro campo desconocido | Corregir el formulario |

## 9. Consultar los usuarios de una empresa

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users`
**Permiso requerido:** `perm:operational-context:application_users:read`

### ¿Qué hace esta API?

Lista, con paginación, las membresías de la empresa: quiénes tienen acceso, su nombre para mostrar, su correo de referencia y su estado, con búsqueda por nombre o correo. Es la pantalla de administración de usuarios de la empresa. Por defecto solo devuelve membresías `ACTIVE`. Las sucursales de cada usuario no vienen aquí: se consultan con la [API 11](#11-consultar-las-sucursales-asignadas-a-un-usuario).

Antes necesita: el `company_id` y membresía en la empresa (o `platform:administer`).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users?page=1&page_size=20&status=ACTIVE&search=ana' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de la membresía | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `search` | string (≤ 160) | No | Búsqueda parcial, sin distinguir mayúsculas, en `display_name` y `reference_email` | Texto libre (≤ 160 caracteres); p. ej. `ana` | `&search=ana` | Interfaz |
| `keycloak_user_id` | string (≤ 255) | No | Solo la membresía de esa cuenta de Keycloak (`sub`) | Identificador `sub` de Keycloak (texto); p. ej. `3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | `&keycloak_user_id=3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | `sub` del token |
| `person_identity_id` | UUID | No | Solo la membresía de esa persona | UUID; p. ej. `a0e1d2c3-b4a5-4968-8776-655443322110` | `&person_identity_id=a0e1d2c3-b4a5-4968-8776-655443322110` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities` (busca personas por identificación o nombre) o `id` de la respuesta `201` de su `POST` (registra la persona) · qué hacen y sus errores en la guía [person_identity_id](../parametros/person-identity-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users?page=1&page_size=20&status=ACTIVE&search=ana`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[ApplicationUserResponse]`):

```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "display_name": "Ana Pérez",
      "reference_email": "ana.perez@empresa-ejemplo.test",
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
| `items[].id` | UUID | El [application_user_id](../parametros/application-user-id.md) de la membresía; se usa en las [API 11](#11-consultar-las-sucursales-asignadas-a-un-usuario), [12](#12-asignar-un-usuario-a-una-sucursal), [14](#14-inactivar-una-membresía) y [15](#15-reactivar-una-membresía) |
| `items[].keycloak_user_id` | string | `sub` de la cuenta en Keycloak (el mismo `sub` del token del usuario) · guía [keycloak_user_id](../parametros/keycloak-user-id.md) |
| `items[].person_identity_id` | UUID | Persona en Party Identity (nombres e identificación se consultan allí) |
| `items[].display_name`, `reference_email` | string, string \| null | Datos de referencia propios de SIO |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Estado de la membresía |
| `items[].company_status` | `ACTIVE` \| `INACTIVE` | Estado de la empresa |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Empresa inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 160, `keycloak_user_id` > 255, `status` inválido o UUID mal formado | Corregir los parámetros |

## 10. Asociar un usuario a una empresa (crear membresía)

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users`
**Permiso requerido:** `perm:operational-context:application_users:create`

### ¿Qué hace esta API?

Da acceso a la empresa a una persona que ya tiene cuenta en Keycloak, creando su membresía. Es una operación `HIGH_RISK` (concede acceso a los datos de la empresa): pedir confirmación al usuario. La cuenta se indica por su `sub` (`keycloak_user_id`) **o** por su `username`, exactamente uno; el servicio la verifica en Keycloak y guarda solo el `sub`. La persona debe existir y estar `ACTIVE` en Party Identity. Una cuenta y una persona solo pueden tener una membresía activa por empresa.

Efecto verificado: desde ese momento el usuario ve la empresa en su contexto operativo, pero **sin sucursales** hasta que se le asigne alguna con la [API 12](#12-asignar-un-usuario-a-una-sucursal). Los permisos (`perm:…`) no se asignan aquí sino en los grupos de Keycloak.

Antes necesita: (1) la cuenta del usuario en Keycloak, habilitada y en el grupo que corresponda a su función; (2) la identidad de la persona en Party Identity (`POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities`, ver [person_identity_id](../parametros/person-identity-id.md)); (3) que el administrador vea la empresa (membresía activa o `platform:administer`). La **primera membresía** de una empresa recién creada la registra el administrador de plataforma.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "ana.perez",
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "display_name": "Ana Pérez",
    "reference_email": "ana.perez@empresa-ejemplo.test"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa en la que se crea la membresía; debe estar `ACTIVE` | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `ApplicationUserCreate`:

```json
{
  "username": "ana.perez",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@empresa-ejemplo.test"
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `keycloak_user_id` | string (1–255) \| null | Exactamente uno de los dos | `sub` de la cuenta en Keycloak | `3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | `sub` del token del usuario ([API 4 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#4-identificar-al-usuario-y-sus-permisos), que explica cómo decodificarlo) o el administrador de Keycloak · guía [keycloak_user_id](../parametros/keycloak-user-id.md) |
| `username` | string (1–255) \| null | Exactamente uno de los dos | Nombre de usuario en Keycloak; el servicio lo resuelve al `sub` | `ana.perez` | El administrador de Keycloak |
| `person_identity_id` | UUID | Sí | Persona en Party Identity, `ACTIVE` | `a0e1d2c3-b4a5-4968-8776-655443322110` | `items[].id` de `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities` (busca personas por identificación o nombre) o `id` de la respuesta `201` de su `POST` (registra la persona) · qué hacen y sus errores en la guía [person_identity_id](../parametros/person-identity-id.md) |
| `display_name` | string (1–160) | Sí | Nombre para mostrar dentro de la empresa | `Ana Pérez` | Formulario |
| `reference_email` | string (correo) \| null | No; acepta `null` | Correo de referencia propio de SIO | `ana.perez@empresa-ejemplo.test` | Formulario |

Enviar `keycloak_user_id` y `username` a la vez, o ninguno, responde `422`. No se envían nombres ni identificación de la persona: pertenecen a Party Identity.

### Respuesta exitosa

`201 Created` (`ApplicationUserResponse`), con cabecera `Location: /api/v1/application-users/{id}`:

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@empresa-ejemplo.test",
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
| `id` | UUID | El nuevo [application_user_id](../parametros/application-user-id.md); se usa para asignar sucursales ([API 12](#12-asignar-un-usuario-a-una-sucursal)) y cambiar el estado ([API 14](#14-inactivar-una-membresía) y [15](#15-reactivar-una-membresía)) |
| `keycloak_user_id` | string | `sub` resuelto en Keycloak, aunque se haya enviado `username` |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

Orden de validación verificado en el código: empresa visible y `ACTIVE` → duplicado por persona → cuenta en Keycloak → duplicado por cuenta → persona en Party Identity.

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Empresa inexistente o fuera del alcance | Volver a leer el contexto operativo |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP` | La persona (`field: person_identity_id`) o la cuenta (`field: keycloak_user_id`) ya tiene membresía activa en la empresa | Buscarla con la [API 9](#9-consultar-los-usuarios-de-una-empresa); si está inactiva, reactivarla con la [API 15](#15-reactivar-una-membresía) |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear membresías |
| `422` | `OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND` | No existe una cuenta con ese `sub` o `username` | Verificar el usuario en Keycloak |
| `422` | `OPERATIONAL_CONTEXT.KEYCLOAK_USER_DISABLED` | La cuenta está deshabilitada en Keycloak | Habilitarla en Keycloak |
| `422` | `OPERATIONAL_CONTEXT.TECHNICAL_ACCOUNT_NOT_ALLOWED` | La cuenta es una cuenta de servicio, no una persona | Usar una cuenta de usuario |
| `422` | `OPERATIONAL_CONTEXT.PERSON_IDENTITY_NOT_FOUND` / `PERSON_IDENTITY_INACTIVE` | La persona no existe o está inactiva en Party Identity | Registrarla o reactivarla |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Ninguno o ambos de `keycloak_user_id`/`username`, `display_name` vacío o > 160, correo inválido, campo desconocido | Corregir el formulario |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Keycloak o Party Identity no responden (`dependency` lo indica) | Reintentar más tarde |

Ejemplo de `422` por cuenta inexistente:

```json
{
  "type": "https://sio/errors/operational-context/keycloak-user-not-found",
  "title": "Cuenta inexistente",
  "status": 422,
  "detail": "No existe una cuenta de Keycloak con el identificador indicado.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users",
  "code": "OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "username",
      "message": "No existe una cuenta de Keycloak con el identificador indicado.",
      "code": "KEYCLOAK_USER_NOT_FOUND"
    }
  ]
}
```

## 11. Consultar las sucursales asignadas a un usuario

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`
**Permiso requerido:** `perm:operational-context:user_branches:read`

### ¿Qué hace esta API?

Lista las asignaciones de sucursal de una membresía, con el acceso efectivo calculado para cada una (`operational_access`). Es la pantalla «sucursales de este usuario» de la administración. Por defecto solo devuelve asignaciones `ACTIVE`; con `status=INACTIVE` se ven las retiradas, que pueden reactivarse (OC 26).

Antes necesita: el `application_user_id` ([API 9](#9-consultar-los-usuarios-de-una-empresa) o [10](#10-asociar-un-usuario-a-una-empresa-crear-membresía)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches?status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `application_user_id` | UUID | Sí | Membresía del usuario | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` | `items[].id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) · guía [application_user_id](../parametros/application-user-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | No; por defecto `ACTIVE` | Estado de la asignación | Uno de: `ACTIVE` (por defecto), `INACTIVE`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches?status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[UserBranchResponse]`):

```json
{
  "items": [
    {
      "id": "9f0a1b2c-3d4e-4f5a-8b6c-7d8e9f0a1b2c",
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
        "reason": null
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [user_branch_id](../parametros/user-branch-id.md) de la asignación, necesario para retirarla o reactivarla (OC 25, 26) |
| `items[].branch_id` | UUID | Sucursal asignada; el nombre se consulta con la [API 7](#7-consultar-una-sucursal) |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Estado de la asignación |
| `items[].assigned_at`, `assigned_by` | date-time, string | Cuándo y quién (`sub`) la asignó |
| `items[].deactivated_at` | date-time \| null | Cuándo se retiró, si está inactiva |
| `items[].membership_status`, `branch_status`, `company_status` | `ACTIVE` \| `INACTIVE` | Estados que condicionan el acceso |
| `items[].operational_access.allowed` | boolean | `true` si el usuario puede operar hoy en esa sucursal |
| `items[].operational_access.reason` | string \| null | Si `allowed` es `false`, la primera causa: `USER_MEMBERSHIP_INACTIVE`, `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `USER_BRANCH_INACTIVE` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La membresía no existe o su empresa está fuera del alcance | Volver a leer la lista de usuarios ([API 9](#9-consultar-los-usuarios-de-una-empresa)) |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `status` inválido, paginación fuera de rango o UUID mal formado | Corregir los parámetros |

## 12. Asignar un usuario a una sucursal

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches`
**Permiso requerido:** `perm:operational-context:user_branches:create`

### ¿Qué hace esta API?

Autoriza a un miembro de la empresa a operar en una sucursal concreta (vender, comprar, ajustar inventario). Operación `HIGH_RISK`: pedir confirmación. La sucursal debe pertenecer a la misma empresa que la membresía, y membresía, sucursal y empresa deben estar `ACTIVE`. Un usuario puede tener varias sucursales; cada una es una asignación.

Efecto verificado: a partir de la respuesta, el usuario ve la sucursal con `allowed: true` en su contexto operativo y las API de negocio aceptan ese `branch_id` para él.

Antes necesita: el `application_user_id` de una membresía `ACTIVE` ([API 9](#9-consultar-los-usuarios-de-una-empresa) o [10](#10-asociar-un-usuario-a-una-empresa-crear-membresía)) y el `branch_id` de una sucursal `ACTIVE` de la misma empresa ([API 6](#6-consultar-las-sucursales-de-una-empresa)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `application_user_id` | UUID | Sí | Membresía a la que se asigna la sucursal | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` | `items[].id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) o `id` de la respuesta `201` de la [API 10](#10-asociar-un-usuario-a-una-empresa-crear-membresía) (crea la membresía; errores en §10) · guía [application_user_id](../parametros/application-user-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `UserBranchCreate`:

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal `ACTIVE` de la misma empresa que la membresía | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `items[].id` de la [API 6](#6-consultar-las-sucursales-de-una-empresa) (lista todas las sucursales de la empresa; errores en §6) · guía [branch_id](../parametros/branch-id.md) |

No se envía `application_user_id` (va en la ruta) ni quién asigna (se toma del token).

### Respuesta exitosa

`201 Created` (`UserBranchResponse`), con cabecera `Location: /api/v1/user-branches/{id}`:

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
    "reason": null
  },
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [user_branch_id](../parametros/user-branch-id.md) (para OC 25 y 26) |
| `operational_access` | objeto | Siempre `allowed: true` y `reason: null` justo al crear, porque todas las condiciones se validaron |
| `assigned_by` | string | `sub` del administrador que hizo la asignación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La membresía o la sucursal no existen o están fuera del alcance | Volver a leer las listas ([API 9](#9-consultar-los-usuarios-de-una-empresa) y [6](#6-consultar-las-sucursales-de-una-empresa)) |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_USER_BRANCH` | Ya existe una asignación (activa o inactiva) de ese usuario a esa sucursal | Si está inactiva, reactivarla con OC 26 en lugar de crearla |
| `422` | `OPERATIONAL_CONTEXT.BRANCH_COMPANY_MISMATCH` | La sucursal es de otra empresa | Elegir una sucursal de la empresa de la membresía |
| `422` | `OPERATIONAL_CONTEXT.MEMBERSHIP_INACTIVE` | La membresía está `INACTIVE` | Reactivarla primero ([API 15](#15-reactivar-una-membresía)) |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear asignaciones |
| `422` | `OPERATIONAL_CONTEXT.BRANCH_INACTIVE` | La sucursal está `INACTIVE` | Reactivarla (OC 14) o elegir otra |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `branch_id`, no es UUID o hay campos desconocidos | Corregir el cuerpo |

## 13. Consultar los usuarios asignados a una sucursal

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/user-branches`
**Permiso requerido:** `perm:operational-context:user_branches:read`

### ¿Qué hace esta API?

Lista las asignaciones de una sucursal, es decir, qué miembros pueden operar en ella y con qué acceso efectivo. Es la vista inversa de la [API 11](#11-consultar-las-sucursales-asignadas-a-un-usuario), para la pantalla de administración de una sucursal. Por defecto solo asignaciones `ACTIVE`.

Antes necesita: el `branch_id` ([API 6](#6-consultar-las-sucursales-de-una-empresa) o contexto operativo).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/user-branches?status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `items[].id` de la [API 6](#6-consultar-las-sucursales-de-una-empresa) (lista todas las sucursales de la empresa; errores en §6) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:** `status` (`ACTIVE` \| `INACTIVE`, por defecto `ACTIVE`), `page` (≥ 1, por defecto 1) y `page_size` (1–100, por defecto 20), igual que en la [API 11](#11-consultar-las-sucursales-asignadas-a-un-usuario).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[UserBranchResponse]`), con el mismo objeto por elemento que la [API 11](#11-consultar-las-sucursales-asignadas-a-un-usuario):

```json
{
  "items": [
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
        "reason": null
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].application_user_id` | UUID | Membresía asignada; su nombre se obtiene de la [API 9](#9-consultar-los-usuarios-de-una-empresa) |
| `items[].operational_access` | objeto | Acceso efectivo de cada usuario en esta sucursal (`allowed`, `reason`) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La sucursal no existe o su empresa está fuera del alcance | Volver a leer la lista de sucursales |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Parámetros inválidos | Corregirlos |

## 14. Inactivar una membresía

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/deactivate`
**Permiso requerido:** `perm:operational-context:application_users:delete`

### ¿Qué hace esta API?

Retira el acceso de una persona a la empresa sin borrar nada: la membresía pasa a `INACTIVE`. Operación `HIGH_RISK`: pedir confirmación. Efectos verificados: en el contexto operativo del usuario todas las sucursales de esa empresa pasan a `allowed: false` con `reason: USER_MEMBERSHIP_INACTIVE`, y las API de negocio le responden `404` o `403` en esa empresa; sus asignaciones de sucursal se conservan y vuelven a ser efectivas al reactivar. Solo afecta a esta membresía, no a la cuenta de Keycloak ni a otras empresas.

Antes necesita: el `application_user_id` y su `version` actual ([API 9](#9-consultar-los-usuarios-de-una-empresa)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/deactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `application_user_id` | UUID | Sí | Membresía a inactivar | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` | `items[].id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) · guía [application_user_id](../parametros/application-user-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `StatusActionRequest`:

```json
{
  "version": 1
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la membresía | `1` | `items[].version` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) |

No admite `{}` ni otros campos.

### Respuesta exitosa

`200 OK` (`ApplicationUserResponse`) con `status: "INACTIVE"` y `version` incrementada:

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@empresa-ejemplo.test",
  "status": "INACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `INACTIVE` | Confirmación del cambio |
| `version` | integer | Nueva versión, necesaria para reactivar ([API 15](#15-reactivar-una-membresía)) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Membresía inexistente o fuera del alcance | Volver a leer la lista |
| `409` | `OPERATIONAL_CONTEXT.VERSION_CONFLICT` | `version` desactualizada | Releer y repetir |
| `409` | `OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION` | La membresía ya estaba `INACTIVE` | Refrescar la pantalla; no hay nada que hacer |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `version` o hay campos desconocidos | Corregir el cuerpo |

## 15. Reactivar una membresía

**Método:** `POST`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/reactivate`
**Permiso requerido:** `perm:operational-context:application_users:update`

### ¿Qué hace esta API?

Devuelve el acceso a la empresa a una membresía `INACTIVE`. Operación `HIGH_RISK`. Antes de reactivar, el servicio vuelve a comprobar que la cuenta exista y esté habilitada en Keycloak, que la persona esté `ACTIVE` en Party Identity, que la empresa esté `ACTIVE` y que no exista otra membresía activa de la misma persona o cuenta en la empresa. Las asignaciones de sucursal que tenía vuelven a ser efectivas.

Antes necesita: el `application_user_id` y su `version` actual ([API 9](#9-consultar-los-usuarios-de-una-empresa) con `status=INACTIVE`).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/reactivate' \
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
| `application_user_id` | UUID | Sí | Membresía a reactivar | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` | `items[].id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) · guía [application_user_id](../parametros/application-user-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `StatusActionRequest`:

```json
{
  "version": 2
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la membresía | `2` | `items[].version` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) |

### Respuesta exitosa

`200 OK` (`ApplicationUserResponse`) con `status: "ACTIVE"` y `version` incrementada:

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "company_status": "ACTIVE",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@empresa-ejemplo.test",
  "status": "ACTIVE",
  "version": 3,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T11:00:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` | Confirmación del cambio; el usuario vuelve a ver la empresa en su contexto operativo |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | Membresía inexistente o fuera del alcance | Volver a leer la lista |
| `409` | `OPERATIONAL_CONTEXT.VERSION_CONFLICT` | `version` desactualizada | Releer y repetir |
| `409` | `OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION` | La membresía ya estaba `ACTIVE` | Refrescar la pantalla |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP` | Mientras estuvo inactiva se creó otra membresía activa de la misma persona o cuenta | Mantener la otra membresía |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se puede reactivar hasta reactivar la empresa |
| `422` | `OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND`, `KEYCLOAK_USER_DISABLED`, `TECHNICAL_ACCOUNT_NOT_ALLOWED`, `PERSON_IDENTITY_NOT_FOUND`, `PERSON_IDENTITY_INACTIVE` | La cuenta o la persona ya no son válidas | Corregir en Keycloak o Party Identity |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `version` o hay campos desconocidos | Corregir el cuerpo |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Keycloak o Party Identity no responden | Reintentar más tarde |

## 16. Consultar la trazabilidad de la empresa (auditoría)

**Método:** `GET`
**URL:** `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events` (lista) y `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/audit-events/{audit_id}` (un evento)
**Permiso requerido:** `perm:audit:audit-events:read`

### ¿Qué hace esta API?

Muestra quién hizo qué y cuándo en la empresa: creación, confirmación y anulación de ventas y compras, cambios de líneas, recepciones, altas y cambios de clientes, proveedores, productos adoptados, precios, políticas, sucursales y membresías. Devuelve los eventos del más reciente al más antiguo, con filtros por fecha, resultado, acción, tipo de entidad, usuario y sucursal. Los filtros nunca amplían el alcance: solo se devuelven eventos de ese `company_id`. Audit comprueba en cada solicitud, con el token del usuario, que tenga membresía `ACTIVE` en la empresa.

Antes necesita: el `company_id` y, para filtrar, los valores de `action` y `entity_type` de la tabla de más abajo.

### ¿Cómo se realiza la solicitud?

Lista filtrada (confirmaciones de venta desde una fecha):

```bash
curl -X GET \
  'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events?entity_type=Sale&action=CONFIRM_SALE&occurred_at_from=2026-10-01T00:00:00Z&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Un evento concreto:

```bash
curl -X GET \
  'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events/8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa cuyos eventos se consultan | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |
| `audit_id` | UUID | Solo en la segunda URL | Identificador del evento (`items[].id` de la lista; no confundir con `event_id`) | `8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9` | `items[].id` de la lista de esta misma [API 16](#16-consultar-la-trazabilidad-de-la-empresa-auditoría) |

**Parámetros de consulta (solo la lista; un parámetro desconocido responde `422`):**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | `1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | `20` | Interfaz |
| `occurred_at_from` | date-time **con zona horaria** | No | Desde cuándo; debe ser ≤ `occurred_at_to` | `2026-10-01T00:00:00Z` | Filtro de fechas |
| `occurred_at_to` | date-time con zona horaria | No | Hasta cuándo | `2026-10-31T23:59:59Z` | Filtro de fechas |
| `result` | `SUCCESS` \| `FAILURE` | No | Solo operaciones exitosas o fallidas | `SUCCESS` | Interfaz |
| `action` | string | No | Igualdad exacta con la acción (tabla siguiente) | `CONFIRM_SALE` | Tabla de acciones |
| `entity_type` | string | No | Igualdad exacta con el tipo de entidad | `Sale` | Tabla de acciones |
| `entity_id` | UUID | No | Identificador del registro afectado | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` del recurso en su servicio (por ejemplo `id` de la venta en Sales); ver la tabla de la [API 17](#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto) |
| `source_service` | string | No | Servicio emisor | `sales-service` | Tabla de acciones |
| `keycloak_user_id` | UUID | No | Eventos de un usuario (`sub`) | `3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | `keycloak_user_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].keycloak_user_id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) · guía [keycloak_user_id](../parametros/keycloak-user-id.md) |
| `application_user_id` | UUID | No | Eventos de una membresía | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` | `items[].id` de la [API 9](#9-consultar-los-usuarios-de-una-empresa) (lista las membresías de la empresa; errores en §9) · guía [application_user_id](../parametros/application-user-id.md) |
| `branch_id` | UUID | No | Eventos de una sucursal | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `items[].id` de la [API 6](#6-consultar-las-sucursales-de-una-empresa) (lista todas las sucursales de la empresa; errores en §6) · guía [branch_id](../parametros/branch-id.md) |
| `event_id`, `correlation_id`, `request_id` | UUID | No | Identificadores técnicos de trazabilidad | — | `event_id`, `correlation_id` o `request_id` de un evento previo de esta misma lista |

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`AuditEventPage`) en la lista; `200 OK` con un solo `AuditEventResponse` (mismo objeto que cada elemento de `items[]`) en la consulta por `audit_id`:

```json
{
  "items": [
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
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | Identificador del evento en Audit (`audit_id`) |
| `items[].event_id` | UUID | Identificador que asignó el servicio emisor |
| `items[].action` | string | Qué se hizo (`CONFIRM_SALE`, `CREATE_COMPANY_CUSTOMER`, …) |
| `items[].entity_type`, `entity_id` | string, UUID \| null | Sobre qué registro |
| `items[].previous_values`, `new_values` | objeto \| null | Valores antes y después; solo los campos relevantes para esa acción |
| `items[].redacted_paths` | array de string | Rutas de valores ocultados por confidencialidad |
| `items[].result`, `reason` | `SUCCESS` \| `FAILURE`, string \| null | Resultado y, en fallos, el motivo |
| `items[].application_user_id`, `keycloak_user_id`, `username_snapshot` | UUID \| null, UUID \| null, string \| null | Quién lo hizo (membresía, cuenta y nombre de usuario en ese momento) |
| `items[].branch_id` | UUID \| null | Sucursal, cuando aplica |
| `items[].source_service` | string | Servicio emisor (`sales-service`, `purchase-service`, …) |
| `items[].occurred_at`, `recorded_at` | date-time | Cuándo ocurrió y cuándo lo registró Audit |
| `items[].request_id`, `correlation_id` | UUID \| null | Trazabilidad técnica |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; la lista va de la más reciente a la más antigua |

Valores de `entity_type` y `action` que emiten hoy los servicios (verificados en el código de cada emisor):

| `source_service` | `entity_type` | `action` |
|---|---|---|
| `sales-service` | `Sale`, `SaleDetail`, `SaleSequence` | `CREATE_SALE`, `UPDATE_SALE`, `ADD_SALE_DETAIL`, `UPDATE_SALE_DETAIL`, `DELETE_SALE_DETAIL`, `CONFIRM_SALE`, `CANCEL_SALE`, `CREATE_SALE_SEQUENCE`, `UPDATE_SALE_SEQUENCE`, `DEACTIVATE_SALE_SEQUENCE`, `REACTIVATE_SALE_SEQUENCE` |
| `purchase-service` | `Purchase`, `PurchaseDetail`, `PurchaseLifecycleEvent`, `PurchaseSequence` | `CREATE_PURCHASE`, `UPDATE_PURCHASE`, `ADD_PURCHASE_DETAIL`, `UPDATE_PURCHASE_DETAIL`, `DELETE_PURCHASE_DETAIL`, `CONFIRM_PURCHASE`, `CANCEL_PURCHASE`, `RECEIVE_PURCHASE`, `RECORD_PURCHASE_LIFECYCLE_EVENT`, `CREATE_PURCHASE_SEQUENCE`, `UPDATE_PURCHASE_SEQUENCE`, `DEACTIVATE_PURCHASE_SEQUENCE`, `REACTIVATE_PURCHASE_SEQUENCE`, `OVERRIDE_PURCHASE_LINE_TAX` |
| `commercial-relationship-service` | `CompanyCustomer`, `CompanySupplier`, `CompanyProduct`, `CompanyProductPresentation`, `PriceList`, `PriceListItem`, `PricingPolicy` | `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_COMPANY_CUSTOMER`; lo mismo para `COMPANY_SUPPLIER` (más `BLOCK_`/`UNBLOCK_`), `COMPANY_PRODUCT_PRESENTATION`, `SUPPLIER_PRODUCT`, `SUPPLIER_PAYMENT_CONDITION`, `PRICE_LIST` y `PRICE_LIST_ITEM`; `ADOPT_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_COMPANY_PRODUCT`, `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX`, `CHANGE_PRICE_LIST_ITEM_PRICE`, `CREATE_`/`UPDATE_`/`DEACTIVATE_PRICING_POLICY`, `CHANGE_PRICING_POLICY_PERCENTAGE`, `ASSIGN_`/`UNASSIGN_PRICING_POLICY_PRESENTATION` |
| `operational-context-service` | `Company`, `Branch`, `ApplicationUser`, `UserBranch`, `CompanyAdvisorAssignment` | `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_COMPANY`; lo mismo para `BRANCH` y `APPLICATION_USER`; `ASSIGN_`/`DEACTIVATE_`/`REACTIVATE_USER_BRANCH`; `CREATE_ADVISOR_ASSIGNMENT` |
| `inventory-service` | `InventoryAdjustment`, `InventoryCount`, `InventoryOperation` | `CREATE_INVENTORY_ADJUSTMENT`; `START_`/`COMPLETE_`/`CANCEL_INVENTORY_COUNT`; `APPLY_`/`REVERSE_INVENTORY_ENTRY`; `APPLY_`/`REVERSE_INVENTORY_OUTPUT`; `CREATE_`/`UPDATE_`/`DEACTIVATE_INVENTORY_POLICY` |

Los eventos del catálogo global de Product Catalog (`Product`, `ProductPresentation`, …) no pertenecen a una empresa: se consultan en `GET https://sio-audit-dev.onrender.com/api/v1/platform-audit-events` con `perm:audit:platform-events:read` (Audit 8–10), reservado a la administración de la plataforma.

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `AUDIT.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read` en el token) | Revisar los permisos del usuario |
| `404` | `AUDIT.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa, la empresa no existe o, en la consulta por `audit_id`, el evento no existe o es de otra empresa | Volver a leer el contexto operativo |
| `422` | `AUDIT.VALIDATION_ERROR` | Fecha sin zona horaria, `occurred_at_from` posterior a `occurred_at_to`, `page_size` fuera de 1–100, `result` distinto de `SUCCESS`/`FAILURE`, UUID mal formado o parámetro desconocido | Corregir los parámetros |
| `503` | `AUDIT.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles (`dependency` lo indica) | Reintentar más tarde |

Ejemplo de `422` por fecha sin zona horaria:

```json
{
  "type": "https://sio/errors/audit/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/audit-events",
  "code": "AUDIT.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "occurred_at_from",
      "message": "Debe incluir zona horaria.",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

## 17. Consultar el historial de una venta, una compra o un producto

**Método:** `GET`
**URL:** `https://sio-audit-dev.onrender.com/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}`
**Permiso requerido:** `perm:audit:audit-events:read`

### ¿Qué hace esta API?

Devuelve la línea de tiempo completa de un registro de la empresa, del primer evento al último (orden cronológico ascendente), para mostrar el historial de una venta, una compra, un producto adoptado, un cliente, un proveedor, una sucursal o una membresía. Los eventos de inventario de una venta o compra no aparecen bajo `Sale`/`Purchase`: se consultan con `entity_type=InventoryOperation` y el `inventory_operation_id` del documento, o en el kardex ([Inventario](inventario.md)).

Antes necesita: el `company_id`, el `entity_type` en PascalCase y el identificador del registro:

| Qué rastrear | `entity_type` | `entity_id` |
|---|---|---|
| Una venta (creación, líneas, confirmación, anulación) | `Sale` | [sale_id](../parametros/sale-id.md) |
| Una línea de venta | `SaleDetail` | `lines[].id` de la venta |
| Una compra (creación, líneas, confirmación, recepción, anulación, hitos) | `Purchase` | [purchase_id](../parametros/purchase-id.md) |
| Un producto adoptado por la empresa | `CompanyProduct` | [company_product_id](../parametros/company-product-id.md) |
| Una presentación de la empresa | `CompanyProductPresentation` | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| Un precio, una lista o una política | `PriceListItem`, `PriceList`, `PricingPolicy` | su `id` |
| Un cliente o un proveedor | `CompanyCustomer`, `CompanySupplier` | [company_customer_id](../parametros/customer-id.md), [company_supplier_id](../parametros/supplier-id.md) |
| Una sucursal o una membresía | `Branch`, `ApplicationUser` | [branch_id](../parametros/branch-id.md), [application_user_id](../parametros/application-user-id.md) |

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/entity-history/Sale/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a?page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |
| `entity_type` | string, patrón `^[A-Z][A-Za-z0-9]{0,59}$` (PascalCase) | Sí | Tipo de entidad | `Sale` | Tabla anterior |
| `entity_id` | UUID | Sí | Registro a rastrear | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | Campo `id` del recurso, según la tabla anterior |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `occurred_at_from`, `occurred_at_to` | date-time con zona horaria | No | Rango de fechas (`from` ≤ `to`) | Fecha y hora ISO 8601 con zona horaria; p. ej. `2026-10-01T00:00:00Z` | `&occurred_at_from=2026-10-01T00:00:00Z` | Interfaz |
| `result` | `SUCCESS` \| `FAILURE` | No | Solo exitosos o fallidos | Uno de: `SUCCESS`, `FAILURE`; p. ej. `SUCCESS` | `&result=SUCCESS` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-audit-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/entity-history/Sale/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a?page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`AuditEventPage`), mismo formato y campos que la lista de la [API 16](#16-consultar-la-trazabilidad-de-la-empresa-auditoría), pero ordenado del evento más antiguo al más reciente:

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
      "action": "CREATE_SALE",
      "entity_type": "Sale",
      "entity_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "previous_values": null,
      "new_values": {
        "status": "DRAFT"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:00:00Z",
      "recorded_at": "2026-10-19T15:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    },
    {
      "id": "8b75ec30-6c7b-4e58-85d1-6be2ad9e8eb9",
      "event_id": "5548d0bd-b180-4cd4-98c4-7c632416cf52",
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
      "request_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
      "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
      "source_service": "sales-service",
      "occurred_at": "2026-10-19T15:04:05Z",
      "recorded_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 2,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[]` | array de `AuditEventResponse` | Los eventos del registro en orden cronológico; ver la tabla de campos de la [API 16](#16-consultar-la-trazabilidad-de-la-empresa-auditoría) |
| `items[].action` | string | Paso de la línea de tiempo (`CREATE_SALE` → `ADD_SALE_DETAIL` → `CONFIRM_SALE` → `CANCEL_SALE`, por ejemplo) |
| `total_records` | integer | `0` e `items: []` si el registro no tiene eventos (no es un error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `AUDIT.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía | Revisar los permisos del usuario |
| `404` | `AUDIT.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `AUDIT.VALIDATION_ERROR` | `entity_type` que no cumple el patrón PascalCase, `entity_id` no UUID, fechas sin zona horaria o invertidas, paginación fuera de rango | Corregir los parámetros |
| `503` | `AUDIT.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles | Reintentar más tarde |

## Numeración de documentos comerciales

Las ventas y las compras reciben su número (`V-000123`, `C-000045`) al **confirmarse**, tomándolo de una **secuencia** del servicio correspondiente: Sales numera ventas y Purchase numera compras, con API simétricas. Sin secuencia activa aplicable, la confirmación falla con `409 SEQUENCE_NOT_CONFIGURED`. Reglas verificadas en el código:

- Una secuencia pertenece a la empresa y, opcionalmente, a una sucursal (`branch_id`). Al confirmar se usa la secuencia **activa de la sucursal** del documento y, si no hay, la **activa de la empresa** (`branch_id: null`).
- A lo sumo **una secuencia activa** por empresa, sucursal (o ninguna) y tipo documental; activar otra en el mismo alcance responde `409 SEQUENCE_ALREADY_ACTIVE`. El `series_code` es único dentro de ese mismo alcance.
- El número se compone de `prefix` + `separator` + consecutivo rellenado a `number_length` dígitos, desde `initial_number`, con reinicio `NEVER`, `YEARLY` o `MONTHLY` (`reset_policy`) y tope opcional `maximum_number` (`409 SEQUENCE_EXHAUSTED` al superarlo). El número completo no puede superar 80 caracteres.
- Tras asignar el primer número, `prefix`, `separator`, `number_length`, `series_code`, `reset_policy`, `initial_number` y `branch_id` son inmutables (`409 SEQUENCE_IN_USE`); solo `maximum_number` puede cambiar, y nunca por debajo del último número asignado.
- Estas API exigen membresía `ACTIVE` en la empresa; sin ella responden `404`. No exigen asignación a la sucursal.

**Cómo resolver `409 SEQUENCE_NOT_CONFIGURED` al confirmar:** (1) consultar las secuencias ([API 18](#18-consultar-las-secuencias-de-numeración)) y comprobar si existe una para la `branch_id` del documento, o una de empresa (`branch_id: null`), con `is_active: true`; (2) si existe pero está inactiva, reactivarla ([API 20](#20-desactivar-o-reactivar-una-secuencia)); (3) si no existe, crearla ([API 19](#19-crear-una-secuencia-de-numeración)); (4) repetir la confirmación con la misma `Idempotency-Key` y la `version` actual del documento. No hace falta recrear el borrador.

## 18. Consultar las secuencias de numeración

**Método:** `GET`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` (ventas) y `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` (compras)
**Permiso requerido:** `perm:sales:sale_sequences:read` (ventas) · `perm:purchase:purchase_sequences:read` (compras)

### ¿Qué hace esta API?

Lista todas las secuencias de la empresa (activas e inactivas) con sus contadores por período. Es la pantalla de configuración de numeración: muestra qué sucursales tienen secuencia propia, cuál es la de la empresa, cuál está activa y cuál será el próximo número. También es el primer paso para diagnosticar un `409 SEQUENCE_NOT_CONFIGURED`.

Antes necesita: el `company_id` y membresía `ACTIVE` en la empresa.

### ¿Cómo se realiza la solicitud?

Secuencias de ventas:

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Secuencias de compras:

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta (la lista no está paginada).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`SequenceList`), ordenada por fecha de creación. En Purchase el objeto es idéntico con `document_kind: "PURCHASE"`:

```json
{
  "items": [
    {
      "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "document_kind": "SALE",
      "series_code": "POS-01",
      "prefix": "V",
      "separator": "-",
      "initial_number": 1,
      "maximum_number": 999999,
      "number_length": 6,
      "reset_policy": "NEVER",
      "is_active": true,
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "counters": [
        {
          "period_key": "",
          "current_number": 123,
          "next_number_preview": "V-000124"
        }
      ]
    },
    {
      "id": "4d5e6f7a-8b9c-4d0e-8f1a-2b3c4d5e6f7a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": null,
      "document_kind": "SALE",
      "series_code": "GENERAL",
      "prefix": "V",
      "separator": "-",
      "initial_number": 1,
      "maximum_number": null,
      "number_length": 6,
      "reset_policy": "YEARLY",
      "is_active": true,
      "version": 1,
      "created_at": "2026-10-19T15:00:00Z",
      "updated_at": "2026-10-19T15:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "counters": []
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [sequence_id](../parametros/sequence-id.md), para las [API 20](#20-desactivar-o-reactivar-una-secuencia) y [21](#21-consultar-y-modificar-una-secuencia) |
| `items[].branch_id` | UUID \| null | Sucursal de la secuencia; `null` = secuencia de la empresa (respaldo para toda sucursal sin secuencia propia) |
| `items[].document_kind` | `SALE` \| `PURCHASE` | Tipo documental |
| `items[].series_code` | string | Código de la serie, único por alcance |
| `items[].prefix`, `separator`, `number_length` | string, string, integer | Formato del número |
| `items[].initial_number`, `maximum_number` | integer, integer \| null | Primer número y tope opcional |
| `items[].reset_policy` | `NEVER` \| `YEARLY` \| `MONTHLY` | Cuándo reinicia el consecutivo |
| `items[].is_active` | boolean | Solo una activa por alcance; la que usa la confirmación |
| `items[].version` | integer | Para las [API 20](#20-desactivar-o-reactivar-una-secuencia) y [21](#21-consultar-y-modificar-una-secuencia) |
| `items[].counters[]` | array | Un contador por período ya usado; `[]` si aún no se asignó ningún número |
| `items[].counters[].period_key` | string | Período del contador según `reset_policy`: `""` con `NEVER`, `"2026"` con `YEARLY`, `"202610"` con `MONTHLY` |
| `items[].counters[].current_number` | integer | Último número asignado |
| `items[].counters[].next_number_preview` | string | Cómo se verá el próximo número |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa o la empresa no existe | Volver a leer el contexto operativo |
| `422` | `SALES.VALIDATION_ERROR` / `PURCHASE.VALIDATION_ERROR` | `company_id` no es UUID | Corregir el identificador |

## 19. Crear una secuencia de numeración

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` (ventas) y `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences` (compras)
**Permiso requerido:** `perm:sales:sale_sequences:create` (ventas) · `perm:purchase:purchase_sequences:create` (compras)

### ¿Qué hace esta API?

Crea una secuencia de numeración y la deja activa. Es el requisito para poder confirmar ventas (Sales) o compras (Purchase) en una sucursal o en toda la empresa. Con `branch_id` la secuencia es de esa sucursal; con `branch_id: null` (u omitido) es la secuencia de la empresa, que sirve de respaldo a todas las sucursales sin secuencia propia. El cuerpo es idéntico en los dos servicios.

Antes necesita: el `company_id`, opcionalmente el `branch_id` de una sucursal `ACTIVE` de la empresa ([API 6](#6-consultar-las-sucursales-de-una-empresa)), y que no exista ya una secuencia activa en ese mismo alcance ([API 18](#18-consultar-las-secuencias-de-numeración)).

### ¿Cómo se realiza la solicitud?

Secuencia de ventas de una sucursal:

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "series_code": "POS-01",
    "prefix": "V",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": 999999,
    "number_length": 6,
    "reset_policy": "NEVER"
  }'
```

Secuencia de compras de toda la empresa:

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": null,
    "series_code": "COMPRAS",
    "prefix": "C",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": null,
    "number_length": 6,
    "reset_policy": "YEARLY"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la secuencia | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `SequenceIn` (rechaza campos desconocidos):

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER"
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID \| null | No; valor por defecto `null` | Sucursal `ACTIVE` de la empresa; `null` crea la secuencia de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `items[].id` de la [API 6](#6-consultar-las-sucursales-de-una-empresa) (lista todas las sucursales de la empresa; errores en §6) · guía [branch_id](../parametros/branch-id.md) |
| `series_code` | string, patrón `^[A-Z0-9_-]{1,40}$` | Sí | Código de la serie (mayúsculas, dígitos, `_`, `-`); único por empresa, sucursal y tipo documental | `POS-01` | Formulario |
| `prefix` | string, patrón `^[A-Z0-9]{1,20}$` | Sí | Prefijo del número | `V` | Formulario |
| `separator` | `-` \| `/` \| `.` \| `_` \| `""` | Sí | Separador entre prefijo y consecutivo; cadena vacía para no usar separador | `-` | Formulario |
| `initial_number` | integer, 1 a 10¹⁷ | Sí | Primer número que se asignará | `1` | Formulario |
| `maximum_number` | integer \| null, 1 a 10¹⁸ − 1 | No; acepta `null` (sin tope) | Último número permitido; no puede ser menor que `initial_number` | `999999` | Formulario |
| `number_length` | integer, 1 a 18 | Sí | Dígitos del consecutivo, rellenado con ceros a la izquierda | `6` | Formulario |
| `reset_policy` | `NEVER` \| `YEARLY` \| `MONTHLY` | Sí | Cuándo vuelve a empezar el consecutivo | `NEVER` | Formulario |

El número resultante (`prefix` + `separator` + consecutivo) no puede superar 80 caracteres.

### Respuesta exitosa

`201 Created` (`SequenceResponse`) con `is_active: true` y `counters: []`. En Purchase, `document_kind` es `"PURCHASE"`:

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": []
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [sequence_id](../parametros/sequence-id.md) para las [API 20](#20-desactivar-o-reactivar-una-secuencia) y [21](#21-consultar-y-modificar-una-secuencia) |
| `is_active` | boolean | `true`: desde ahora las confirmaciones de ese alcance usan esta secuencia |
| `counters` | array | Vacío hasta que se confirme el primer documento |
| `version` | integer | `1`; necesaria para modificar o desactivar |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa | Volver a leer el contexto operativo |
| `409` | `SALES.SEQUENCE_ALREADY_ACTIVE` / `PURCHASE.SEQUENCE_ALREADY_ACTIVE` | Ya hay una secuencia activa para esa empresa y sucursal (o para la empresa, si `branch_id` es `null`) | Desactivarla primero ([API 20](#20-desactivar-o-reactivar-una-secuencia)) o modificar la existente ([API 21](#21-consultar-y-modificar-una-secuencia)) |
| `409` | `SALES.SEQUENCE_IN_USE` / `PURCHASE.SEQUENCE_IN_USE` (`field: series_code`) | Ya existe una secuencia con ese `series_code` en el mismo alcance | Elegir otro `series_code` |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` / `PURCHASE.REFERENCES_NOT_ELIGIBLE` (`errors[].code: BRANCH_INACTIVE`) | La sucursal está `INACTIVE` | Reactivarla o elegir otra |
| `422` | `SALES.VALIDATION_ERROR` / `PURCHASE.VALIDATION_ERROR` | `branch_id` no es de la empresa (`errors[].code: BRANCH_NOT_FOUND`); `series_code` o `prefix` fuera de patrón; `separator` no permitido; `maximum_number` < `initial_number` o número > 80 caracteres (`INVALID_FORMAT`); campo desconocido (`UNKNOWN_FIELD`) | Corregir el formulario |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/sales/sequence-already-active",
  "title": "Secuencia activa existente",
  "status": 409,
  "detail": "Ya existe una secuencia activa para la empresa, la sucursal y el tipo de documento. Desactívela antes.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences",
  "code": "SALES.SEQUENCE_ALREADY_ACTIVE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 20. Desactivar o reactivar una secuencia

**Método:** `POST`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}/deactivate` y `…/reactivate` (ventas); `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}/deactivate` y `…/reactivate` (compras)
**Permiso requerido:** `perm:sales:sale_sequences:update` (ventas) · `perm:purchase:purchase_sequences:update` (compras)

### ¿Qué hace esta API?

Cambia qué secuencia está en uso. **Desactivar** es `HIGH_RISK`: desde ese momento las confirmaciones de ese alcance fallan con `409 SEQUENCE_NOT_CONFIGURED`, salvo que exista la secuencia de respaldo de la empresa; pedir confirmación al usuario. **Reactivar** vuelve a poner en uso una secuencia inactiva, siempre que no haya otra activa en el mismo alcance. Los contadores no se reinician al desactivar y reactivar: la numeración continúa donde quedó. El procedimiento habitual para cambiar de serie es desactivar la actual y luego crear o reactivar la nueva.

Antes necesita: el `sequence_id` y su `version` actual ([API 18](#18-consultar-las-secuencias-de-numeración)).

### ¿Cómo se realiza la solicitud?

Desactivar una secuencia de ventas:

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/deactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Reactivar una secuencia de ventas:

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/reactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 2
  }'
```

Desactivar y reactivar una secuencia de compras:

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/bf15e2c9-5389-48a2-8013-a5528d8e92c8/deactivate' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

```bash
curl -X POST \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/bf15e2c9-5389-48a2-8013-a5528d8e92c8/reactivate' \
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
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |
| `sequence_id` | UUID | Sí | Secuencia | `d9cd7378-6b8f-4e54-8171-39db2f8ebfe1` | `items[].id` de la [API 18](#18-consultar-las-secuencias-de-numeración) (lista todas las secuencias de la empresa; errores en §18) · guía [sequence_id](../parametros/sequence-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` y `Content-Type: application/json`, ambos obligatorios.

### Cuerpo de la solicitud (Body)

Modelo `VersionIn` (rechaza campos desconocidos):

```json
{
  "version": 1
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión actual de la secuencia | `1` | `items[].version` de la [API 18](#18-consultar-las-secuencias-de-numeración) |

### Respuesta exitosa

`200 OK` (`SequenceResponse`) con el nuevo `is_active` y `version` incrementada. Tras desactivar:

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": false,
  "version": 2,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `is_active` | boolean | `false` tras desactivar, `true` tras reactivar |
| `version` | integer | Nueva versión para la siguiente acción |
| `counters[]` | array | Se conservan: al reactivar, la numeración continúa en `next_number_preview` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | Secuencia inexistente en la empresa o sin membresía `ACTIVE` | Volver a leer la lista ([API 18](#18-consultar-las-secuencias-de-numeración)) |
| `409` | `SALES.VERSION_CONFLICT` / `PURCHASE.VERSION_CONFLICT` | `version` desactualizada | Releer y repetir |
| `409` | `SALES.SEQUENCE_ALREADY_ACTIVE` / `PURCHASE.SEQUENCE_ALREADY_ACTIVE` | Al reactivar: ya hay otra secuencia activa en el mismo alcance | Desactivar la otra primero |
| `422` | `SALES.VALIDATION_ERROR` / `PURCHASE.VALIDATION_ERROR` | Falta `version` o hay campos desconocidos | Corregir el cuerpo |

## 21. Consultar y modificar una secuencia

**Método:** `GET` y `PUT`
**URL:** `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}` (ventas) y `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}` (compras)
**Permiso requerido:** `perm:sales:sale_sequences:read` (`GET`) · `perm:sales:sale_sequences:update` (`PUT`); en compras `perm:purchase:purchase_sequences:read` · `perm:purchase:purchase_sequences:update`

### ¿Qué hace esta API?

`GET` devuelve una secuencia con sus contadores. `PUT` reemplaza su configuración: permite ajustar el formato **solo mientras no se haya asignado ningún número**; una vez usada, lo único que puede cambiar es `maximum_number` (ampliar o quitar el tope), y nunca por debajo del último número asignado. El cuerpo del `PUT` es el de la [API 19](#19-crear-una-secuencia-de-numeración) más `version`, y debe enviarse completo con los valores actuales de los campos que no cambian.

Antes necesita: el `sequence_id` y, para `PUT`, la secuencia actual completa con su `version` (`GET` de esta misma API).

### ¿Cómo se realiza la solicitud?

Consultar una secuencia de ventas:

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Ampliar el tope de una secuencia de ventas ya usada:

```bash
curl -X PUT \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "series_code": "POS-01",
    "prefix": "V",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": 9999999,
    "number_length": 6,
    "reset_policy": "NEVER",
    "version": 1
  }'
```

Las mismas dos llamadas para compras usan `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}` con cuerpo idéntico.

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2](#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en §2) · guía [company_id](../parametros/company-id.md) |
| `sequence_id` | UUID | Sí | Secuencia | `d9cd7378-6b8f-4e54-8171-39db2f8ebfe1` | `items[].id` de la [API 18](#18-consultar-las-secuencias-de-numeración) (lista todas las secuencias de la empresa; errores en §18) · guía [sequence_id](../parametros/sequence-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio); `Content-Type: application/json` obligatorio en el `PUT`.

### Cuerpo de la solicitud (Body)

`GET`: no requiere Body. `PUT`: modelo `SequenceUpdateIn`, los campos de la [API 19](#19-crear-una-secuencia-de-numeración) más `version`:

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 9999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "version": 1
}
```

| Campo | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id`, `series_code`, `prefix`, `separator`, `initial_number`, `number_length`, `reset_policy` | como en la [API 19](#19-crear-una-secuencia-de-numeración) | Sí (salvo `branch_id`, que acepta `null`) | Deben repetir el valor actual si la secuencia ya asignó números | — | `GET` de esta API |
| `maximum_number` | integer \| null | No; acepta `null` | Nuevo tope; no puede ser menor que `initial_number` ni que el último número asignado | `9999999` | Formulario |
| `version` | integer ≥ 1 | Sí | Versión actual | `1` | `GET` de esta API |

### Respuesta exitosa

`200 OK` (`SequenceResponse`) en ambos métodos; tras el `PUT`, con la configuración aplicada y `version` incrementada:

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 9999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 2,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `counters[]` | array | Si no está vacío, la secuencia ya se usó y el formato es inmutable |
| `maximum_number` | integer \| null | Tope aplicado |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `SALES.NOT_FOUND` / `PURCHASE.NOT_FOUND` | Secuencia inexistente en la empresa o sin membresía `ACTIVE` | Volver a leer la lista ([API 18](#18-consultar-las-secuencias-de-numeración)) |
| `409` | `SALES.VERSION_CONFLICT` / `PURCHASE.VERSION_CONFLICT` | `version` desactualizada (`PUT`) | Releer y repetir |
| `409` | `SALES.SEQUENCE_IN_USE` / `PURCHASE.SEQUENCE_IN_USE` | La secuencia ya asignó números y se intentó cambiar `prefix`, `separator`, `number_length`, `series_code`, `reset_policy`, `initial_number` o `branch_id` (la respuesta indica los campos) | Dejar esos campos como están; para otro formato, desactivarla y crear una nueva |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` / `PURCHASE.REFERENCES_NOT_ELIGIBLE` | `branch_id` de una sucursal `INACTIVE` | Elegir una sucursal activa |
| `422` | `SALES.VALIDATION_ERROR` / `PURCHASE.VALIDATION_ERROR` | `maximum_number` menor que el último número asignado (`errors[].code: MAXIMUM_NUMBER_BELOW_CURRENT`) o que `initial_number`; `branch_id` ajeno (`BRANCH_NOT_FOUND`); formato inválido; campo desconocido | Corregir el formulario |

## Orden recomendado y efectos automáticos

1. Identidad de la organización en Party Identity → 2. Empresa ([API 1](#1-crear-empresa)) → 3. Sucursales ([API 5](#5-crear-una-sucursal)) → 4. Identidad de cada persona en Party Identity → 5. Membresía ([API 10](#10-asociar-un-usuario-a-una-empresa-crear-membresía)) → 6. Asignación de sucursales ([API 12](#12-asignar-un-usuario-a-una-sucursal)) → 7. Secuencias de numeración de ventas y compras ([API 19](#19-crear-una-secuencia-de-numeración)).

Ningún paso crea automáticamente el siguiente: crear la empresa no crea sucursales ni membresías; crear la membresía no asigna sucursales; las secuencias no se crean solas y sin ellas no se confirman documentos. El ejemplo [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md) recorre la cadena completa con cuerpos y respuestas.

## Dependencias con otros módulos

- [Acceso y contexto operativo](acceso-y-contexto-operativo.md) refleja al instante las membresías y asignaciones creadas aquí.
- [Gestión de clientes](gestion-de-clientes.md) y [Gestión de proveedores](gestion-de-proveedores.md) usan las mismas identidades de Party Identity que este módulo.
- [Ventas](ventas.md) y [Compras](compras.md) exigen la secuencia activa ([API 19](#19-crear-una-secuencia-de-numeración)) y que el usuario tenga asignada la sucursal sobre la que opera (`403 BRANCH_ACCESS_DENIED` en caso contrario); sus anulaciones y confirmaciones quedan registradas en la auditoría ([API 16](#16-consultar-la-trazabilidad-de-la-empresa-auditoría) y [17](#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto)).

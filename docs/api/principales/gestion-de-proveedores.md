# 6.4 Gestión de proveedores

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un usuario de la empresa registra, busca, consulta, actualiza, bloquea e inactiva a los proveedores a los que compra, y configura lo que [Compras](compras.md) necesita de ellos: condiciones de pago y productos que suministran. Como en clientes, un proveedor se compone de dos partes que viven en servicios distintos:

| Parte | Servicio | Qué guarda | Alcance |
|---|---|---|---|
| **Identidad** (quién es) | [Party Identity](../servicios/party-identity.md) | Siempre una **organización** (`organization_identity_id`: NIT, razón social), con sus personas de contacto y su perfil de contacto | Global: la misma organización puede ser proveedor de varias empresas, cliente o empresa de la plataforma |
| **Relación comercial** (es mi proveedor) | [Commercial Relationship](../servicios/commercial-relationship.md) | `company_supplier_id`, `internal_code`, `display_name`, `preferred_contact_person_id`, `status` (`ACTIVE`, `INACTIVE`, `BLOCKED`), `block_reason`, más sus condiciones de pago y sus productos | Empresa: solo existe dentro de un `company_id` |

Compras usa **siempre** el `company_supplier_id` ([supplier_id](../parametros/supplier-id.md)); nunca la identidad directamente. No existen proveedores persona natural: `CompanySupplierCreate` solo acepta `organization_identity_id`.

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Registrar un proveedor de la empresa | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` | `perm:commercial-relationship:company_suppliers:create` | [CR 20](../servicios/commercial-relationship.md#20-post-companiescompany_idcompany-suppliers) |
| 2 | Buscar y listar los proveedores de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` | `perm:commercial-relationship:company_suppliers:read` | [CR 19](../servicios/commercial-relationship.md#19-get-companiescompany_idcompany-suppliers) |
| 3 | Consultar un proveedor | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}` | `perm:commercial-relationship:company_suppliers:read` | [CR 21](../servicios/commercial-relationship.md#21-get-company-supplierscompany_supplier_id) |
| 4 | Consultar las personas de contacto del proveedor | `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | [PI 31](../servicios/party-identity.md#31-get-organization-identitiesorganization_identity_idcontact-persons) |
| 5 | Actualizar un proveedor | `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}` | `perm:commercial-relationship:company_suppliers:update` | [CR 22](../servicios/commercial-relationship.md#22-put-company-supplierscompany_supplier_id) |
| 6 | Inactivar un proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/deactivate` | `perm:commercial-relationship:company_suppliers:delete` | [CR 23](../servicios/commercial-relationship.md#23-post-company-supplierscompany_supplier_iddeactivate) |
| 7 | Reactivar un proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/reactivate` | `perm:commercial-relationship:company_suppliers:update` | [CR 24](../servicios/commercial-relationship.md#24-post-company-supplierscompany_supplier_idreactivate) |
| 8 | Bloquear un proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/block` | `perm:commercial-relationship:company_suppliers:delete` | [CR 75](../servicios/commercial-relationship.md#75-post-company-supplierscompany_supplier_idblock) |
| 9 | Desbloquear un proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/unblock` | `perm:commercial-relationship:company_suppliers:update` | [CR 76](../servicios/commercial-relationship.md#76-post-company-supplierscompany_supplier_idunblock) |
| 10 | Consultar los tipos de condición de pago | `GET https://sio-payment-reference-dev.onrender.com/global-payment-condition-types` | `perm:payment-reference:global_payment_condition_types:read` | [Payment Reference 3](../servicios/payment-reference.md#3-get-global-payment-condition-types) |
| 11 | Consultar las condiciones de pago de los proveedores | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions` | `perm:commercial-relationship:supplier_payment_conditions:read` | [CR 40](../servicios/commercial-relationship.md#40-get-companiescompany_idsupplier-payment-conditions) |
| 12 | Registrar una condición de pago del proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions` | `perm:commercial-relationship:supplier_payment_conditions:create` | [CR 41](../servicios/commercial-relationship.md#41-post-companiescompany_idsupplier-payment-conditions) |
| 13 | Consultar los productos que suministran los proveedores | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products` | `perm:commercial-relationship:supplier_products:read` | [CR 34](../servicios/commercial-relationship.md#34-get-companiescompany_idsupplier-products) |
| 14 | Registrar un producto que suministra el proveedor | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products` | `perm:commercial-relationship:supplier_products:create` | [CR 35](../servicios/commercial-relationship.md#35-post-companiescompany_idsupplier-products) |

Operaciones relacionadas que no se consideran principales (ver las fichas): consultar, modificar, inactivar y reactivar una condición de pago (CR 42–45) o un producto de proveedor (CR 36–39), y la administración de personas de contacto de la organización en Party Identity (PI 32–37).

Paso previo: la identidad de la organización se busca o se crea en Party Identity con las API [3](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) y [4 de Gestión de clientes](gestion-de-clientes.md#4-crear-la-identidad-de-una-organización) (buscan y crean organizaciones por NIT o razón social; sus errores están en esas secciones); los tipos de identificación admitidos por país están en la [API 5 de Gestión de clientes](gestion-de-clientes.md#5-consultar-los-tipos-de-identificación-admitidos-por-país). Orden habitual: identidad de la organización → [API 1](#1-registrar-un-proveedor-de-la-empresa) → opcionalmente [API 12](#12-registrar-una-condición-de-pago-del-proveedor) y [API 14](#14-registrar-un-producto-que-suministra-el-proveedor) → [Compras](compras.md).

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Todas las API de escritura con cuerpo JSON de Commercial Relationship **rechazan campos desconocidos** con `422 COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` (modelos estrictos). Los importes y cantidades se aceptan como número o cadena y se devuelven **siempre como cadena decimal** (`"1.0000"`, `"5000000.00"`), nunca como número JSON.
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `COMMERCIAL_RELATIONSHIP.FORBIDDEN` o `PARTY_IDENTITY.FORBIDDEN` cuando el token no tiene el permiso indicado (mostrar que faltan permisos y el `trace_id`); `503` con `code` `…DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde (`dependency` indica cuál; reintentar más tarde; nada se guarda). Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `COMMERCIAL_RELATIONSHIP.…` o `PARTY_IDENTITY.…` y `trace_id`; ver la [guía de errores](../guias/errores.md). Payment Reference ([API 10](#10-consultar-los-tipos-de-condición-de-pago)) responde errores en formato FastAPI simple (`{"detail": …}`), sin Problem Details.
- **Alcance.** Los proveedores, sus condiciones y sus productos solo se ven y modifican con membresía `ACTIVE` en la empresa (Commercial Relationship lo comprueba en Operational Context en cada solicitud); fuera de ese alcance la respuesta es `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND`, igual que si no existieran. Las identidades de Party Identity y los tipos de condición de Payment Reference son globales.
- **Empresa inactiva.** Si la empresa está `INACTIVE`, Commercial Relationship solo permite consultar e inactivar; registrar, actualizar, reactivar, bloquear o desbloquear responde `422 COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE`.
- **Control de versión.** Toda modificación envía la `version` actual del recurso; si otra persona lo cambió antes, la API responde `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` y el frontend debe volver a leer el recurso y repetir con la nueva `version`.
- **Estados del proveedor.** `ACTIVE` → `INACTIVE` (inactivar) → `ACTIVE` (reactivar); `ACTIVE` o `INACTIVE` → `BLOCKED` (bloquear, con motivo) → `ACTIVE` (desbloquear). Cualquier otra combinación responde `409 COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION`. Solo un proveedor `ACTIVE` sirve para comprar y para registrarle condiciones o productos.
- Las respuestas traen siempre `created_by`, `updated_by` (el `sub` de Keycloak de quien actuó), `created_at` y `updated_at`.
- Toda escritura queda registrada en [Audit](../servicios/audit.md) con las acciones `CREATE_`, `UPDATE_`, `DEACTIVATE_`, `REACTIVATE_`, `BLOCK_` y `UNBLOCK_COMPANY_SUPPLIER` (entidad `CompanySupplier`), `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_SUPPLIER_PAYMENT_CONDITION` (entidad `SupplierPaymentCondition`) y `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_SUPPLIER_PRODUCT` (entidad `SupplierProduct`); se consultan con la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (lista los eventos de auditoría de la empresa; sus errores están en esa sección).

---

## 1. Registrar un proveedor de la empresa

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:create`

### ¿Qué hace esta API?

Convierte una organización de Party Identity en proveedor de la empresa, con el código interno y el nombre con que la empresa lo reconoce. El resultado es la relación comercial cuyo `id` ([supplier_id](../parametros/supplier-id.md)) exige [Compras](compras.md) en la cabecera de cada compra.

Reglas verificadas en el código, en este orden: (1) la organización no puede ser ya proveedor de la empresa, en ningún estado (`409 DUPLICATE_SUPPLIER`); (2) `internal_code` único en la empresa sin distinguir mayúsculas (`409 DUPLICATE_INTERNAL_CODE`); (3) la organización no puede ser la de la propia empresa (`422 SELF_RELATIONSHIP_NOT_ALLOWED`); (4) la organización debe existir y estar `ACTIVE` en Party Identity; (5) la persona de contacto, si se envía, debe ser un contacto activo de esa organización. Nada se guarda si alguna regla falla. Crea el proveedor con `status` `ACTIVE`, `version` `1` y `block_reason` `null`, devuelve `Location: /api/v1/company-suppliers/{id}` y registra `CREATE_COMPANY_SUPPLIER` en Audit.

Antes necesita: `company_id` con membresía `ACTIVE` y empresa `ACTIVE`; el `organization_identity_id` de la [API 3](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) o la [API 4 de Gestión de clientes](gestion-de-clientes.md#4-crear-la-identidad-de-una-organización). Para validar la organización y el contacto, Commercial Relationship consulta Party Identity **con el token del usuario**: el usuario necesita además `perm:party-identity:organization_identities:read` (y `perm:party-identity:organization_contact_persons:read` si envía contacto); si no los tiene recibe `403 PARTY_IDENTITY_ACCESS_DENIED`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "internal_code": "PRV-0001",
    "display_name": "Distribuidora Farma S.A.S.",
    "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que registra al proveedor | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Organización `ACTIVE` en Party Identity; no puede ser la de la propia empresa; inmutable después de crear | `0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; errores en esa sección) o `id` de la [API 4 de Gestión de clientes](gestion-de-clientes.md#4-crear-la-identidad-de-una-organización) (crea la organización; errores en esa sección) · guía [organization_identity_id](../parametros/organization-identity-id.md) |
| `internal_code` | string (1–60) | Sí | Código con que la empresa identifica al proveedor; se recortan espacios; único en la empresa sin distinguir mayúsculas | `PRV-0001` | Formulario (numeración propia de la empresa) |
| `display_name` | string (1–200) | Sí | Nombre con que la empresa muestra al proveedor (puede diferir de la razón social) | `Distribuidora Farma S.A.S.` | Formulario; sugerir `legal_name` o `trade_name` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) |
| `preferred_contact_person_id` | UUID \| null | No; acepta `null` | Persona de contacto preferida; debe ser un contacto **activo** de esa organización | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) (lista las personas de contacto de la organización; errores en §4). Es el `id` del contacto, **no** su `person_identity_id` |

### Respuesta exitosa

`201 Created` (`CompanySupplierResponse`), con cabecera `Location: /api/v1/company-suppliers/{id}`:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [supplier_id](../parametros/supplier-id.md) (`company_supplier_id`) que se envía en [Compras](compras.md) y en las API 11 a 14 |
| `company_id` | UUID | Empresa dueña de la relación |
| `organization_identity_id` | UUID | Identidad con la razón social y el NIT; se consulta con la [API 10 de Gestión de clientes](gestion-de-clientes.md#10-consultar-los-datos-de-identidad-de-una-organización) |
| `internal_code` | string | El código ya recortado |
| `preferred_contact_person_id` | UUID \| null | Contacto preferido para mostrar en la compra |
| `status`, `version`, `block_reason` | — | `ACTIVE`, `1` y `null` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER` | La organización ya es proveedor de la empresa (activo, inactivo o bloqueado) | Buscarlo con la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) filtrando por `organization_identity_id` y `status=ALL`; si está inactivo o bloqueado, ofrecer la [API 7](#7-reactivar-un-proveedor) o la [API 9](#9-desbloquear-un-proveedor) |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un proveedor con ese `internal_code` en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED` | La organización es la de la propia empresa | Informar que una empresa no puede ser proveedor de sí misma |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_NOT_FOUND` | La organización no existe en Party Identity | Volver a buscarla con la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_INACTIVE` | La organización está `INACTIVE` en Party Identity | Informar; reactivar la identidad es una operación de Party Identity (PI 14) |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID` | El contacto no existe, está inactivo o pertenece a otra organización | Volver a cargar los contactos activos con la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `internal_code` vacío o > 60, `display_name` vacío o > 200, UUID inválido, campo obligatorio ausente o campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | El usuario no tiene permiso de lectura en Party Identity para validar la organización o el contacto | Pedir al administrador los permisos de lectura de Party Identity; nada se guardó |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read`; nada se guardó |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden (`dependency` indica cuál) | Reintentar más tarde; nada se guardó |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/duplicate-supplier",
  "title": "Proveedor duplicado",
  "status": 409,
  "detail": "La organización ya es proveedor de la empresa; si está inactivo, reactívelo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers",
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "La organización ya es proveedor de la empresa; si está inactivo, reactívelo.",
      "code": "DUPLICATE_SUPPLIER"
    }
  ]
}
```

Ejemplo de `422` por relación con la propia empresa:

```json
{
  "type": "https://sio/errors/commercial-relationship/self-relationship-not-allowed",
  "title": "Relación con la propia empresa",
  "status": 422,
  "detail": "Una empresa no puede ser cliente ni proveedor de sí misma.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers",
  "code": "COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "Una empresa no puede ser cliente ni proveedor de sí misma.",
      "code": "SELF_RELATIONSHIP_NOT_ALLOWED"
    }
  ]
}
```

## 2. Buscar y listar los proveedores de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:read`

### ¿Qué hace esta API?

Lista, con paginación y búsqueda, los proveedores de la empresa. Es la consulta con la que el comprador elige el proveedor al registrar una compra y con la que se administra la cartera de proveedores. La búsqueda es sobre los datos de la relación (`internal_code` y `display_name`), **no** sobre el NIT: para encontrar un proveedor por NIT hay que buscar la organización con la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) y filtrar aquí por `organization_identity_id`.

Por defecto solo devuelve proveedores `ACTIVE`, que son los únicos que acepta [Compras](compras.md); el selector de proveedor de una compra debe mantener ese filtro.

Antes necesita: `company_id` con membresía `ACTIVE`. Funciona también con la empresa `INACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?search=farma&status=ACTIVE&page=1&page_size=20' \
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
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en `internal_code` y `display_name` | Texto libre: parte del código interno o del nombre para mostrar; p. ej. `PRV-0001` o `farma` | `&search=farma` | Interfaz (código o nombre que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `BLOCKED` \| `ALL` | No; por defecto `ACTIVE` | Estado de los proveedores | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `BLOCKED`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `organization_identity_id` | UUID | No | Solo el proveedor con esa identidad de organización | UUID de una organización; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&organization_identity_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; errores en esa sección) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?search=farma&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanySupplierResponse]`):

```json
{
  "items": [
    {
      "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "PRV-0001",
      "display_name": "Distribuidora Farma S.A.S.",
      "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
      "block_reason": null
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
| `items[].id` | UUID | El [supplier_id](../parametros/supplier-id.md) que se envía en la compra y en las API 3, 5 a 9, 12 y 14 |
| `items[].organization_identity_id` | UUID | Identidad de la organización (NIT, razón social) para la [API 10 de Gestión de clientes](gestion-de-clientes.md#10-consultar-los-datos-de-identidad-de-una-organización) y para la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) |
| `items[].internal_code`, `display_name` | string | Lo que se muestra en el selector de proveedor de la compra |
| `items[].preferred_contact_person_id` | UUID \| null | Contacto preferido |
| `items[].status` | `ACTIVE` \| `INACTIVE` \| `BLOCKED` | Solo los `ACTIVE` se pueden usar en compras |
| `items[].block_reason` | string \| null | Motivo del bloqueo; solo tiene valor con `status` `BLOCKED` |
| `items[].version` | integer | Valor que debe enviarse en las API 5 a 9 |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, UUID inválido, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 3. Consultar un proveedor

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:read`

### ¿Qué hace esta API?

Devuelve la ficha completa de un proveedor, en cualquier estado, si pertenece a una empresa en la que el usuario tiene membresía `ACTIVE`. Se usa para abrir el detalle del proveedor y para leer su `version` antes de modificarlo o cambiar su estado. Para mostrar NIT, razón social y datos de contacto hay que encadenar la [API 10](gestion-de-clientes.md#10-consultar-los-datos-de-identidad-de-una-organización) y la [API 11 de Gestión de clientes](gestion-de-clientes.md#11-consultar-los-datos-de-contacto-vigentes-del-cliente) (identidad y perfil de contacto vigente de la organización; sus errores están en esas secciones) y la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) para las personas de contacto.

Antes necesita: el `company_supplier_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor a consultar | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores de la empresa; errores en §2) o `id` de la [API 1](#1-registrar-un-proveedor-de-la-empresa) (registra el proveedor; errores en §1) · guía [supplier_id](../parametros/supplier-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`), mismo objeto y campos que la respuesta de la [API 1](#1-registrar-un-proveedor-de-la-empresa):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` \| `BLOCKED` | Determina qué acciones mostrar: inactivar y bloquear desde `ACTIVE`; reactivar y bloquear desde `INACTIVE`; desbloquear desde `BLOCKED` |
| `block_reason` | string \| null | Motivo a mostrar cuando está `BLOCKED` |
| `version` | integer | Valor que debe enviarse en las API 5 a 9 |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o pertenece a una empresa en la que el usuario no tiene membresía `ACTIVE` | Volver a la lista; no distinguir entre «no existe» y «sin acceso» |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `company_supplier_id` no es un UUID | Corregir el identificador |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 4. Consultar las personas de contacto del proveedor

**Método:** `GET`
**URL:** `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}/contact-persons`
**Permiso requerido:** `perm:party-identity:organization_contact_persons:read`

### ¿Qué hace esta API?

Lista las personas de contacto registradas en Party Identity para una organización (cargo, correo, teléfono, si es la principal y si está activa). El `id` de cada contacto es lo que Commercial Relationship acepta como `preferred_contact_person_id` en las API [1](#1-registrar-un-proveedor-de-la-empresa) y [5](#5-actualizar-un-proveedor); solo los contactos con `is_active: true` son válidos. Por defecto devuelve solo los activos. Registrar o modificar contactos (PI 32–37) no forma parte de las API principales de este módulo.

Antes necesita: el `organization_identity_id` del proveedor ([API 3](#3-consultar-un-proveedor)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-persons?is_active=true&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Organización cuyos contactos se consultan | `0f1e2d3c-4b5a-4968-8776-655443322111` | `organization_identity_id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o de `items[]` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [organization_identity_id](../parametros/organization-identity-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `is_active` | boolean | No; por defecto `true` | Solo contactos activos (`true`) o solo inactivos (`false`) | Booleano: `true` o `false`; p. ej. `true` | `?is_active=true` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/0f1e2d3c-4b5a-4968-8776-655443322111/contact-persons?is_active=true&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[ContactPersonResponse]`):

```json
{
  "items": [
    {
      "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "position": "Gerente comercial",
      "email": "ventas@distrifarma.example",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | **Lo que se envía como `preferred_contact_person_id`** en las API 1 y 5 |
| `items[].person_identity_id` | UUID \| null | Persona de Party Identity del contacto, si está vinculada; sus nombres se leen con la [API 9 de Gestión de clientes](gestion-de-clientes.md#9-consultar-los-datos-de-identidad-de-una-persona) |
| `items[].position`, `email`, `phone` | string \| null | Datos del contacto para mostrar |
| `items[].is_primary` | boolean | Contacto principal de la organización; buena opción por defecto para `preferred_contact_person_id` |
| `items[].is_active` | boolean | Solo un contacto activo puede ser el preferido |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PARTY_IDENTITY.NOT_FOUND` | La organización no existe | Mostrar que la identidad ya no está disponible |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `organization_identity_id` no es un UUID, `is_active` no es booleano o paginación fuera de rango | Corregir los parámetros |

## 5. Actualizar un proveedor

**Método:** `PUT`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:update`

### ¿Qué hace esta API?

Modifica los datos propios de la relación comercial: código interno, nombre con que la empresa muestra al proveedor y persona de contacto preferida. Es un reemplazo completo: se envían los tres campos con sus valores finales más la `version` vigente. La organización (`organization_identity_id`), la empresa, el `status` y el `block_reason` son **inmutables** por esta vía: el estado cambia solo con las API 6 a 9, y los datos legales se corrigen en Party Identity con la [API 14 de Gestión de clientes](gestion-de-clientes.md#14-actualizar-la-identidad-de-una-organización).

Efectos verificados en el código: funciona sobre proveedores en cualquier estado (`ACTIVE`, `INACTIVE` o `BLOCKED`); si no hay cambios no escribe ni incrementa `version`; si cambia `preferred_contact_person_id` a un valor no nulo lo revalida en Party Identity; registra `UPDATE_COMPANY_SUPPLIER` en Audit.

Antes necesita: la `version` actual ([API 3](#3-consultar-un-proveedor)) y empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "PRV-0001",
    "display_name": "Distribuidora Farma",
    "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor a modificar | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del proveedor | `1` | `version` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) |
| `internal_code` | string (1–60) | Sí | Código interno final; único en la empresa sin distinguir mayúsculas | `PRV-0001` | Formulario (repetir el actual si no cambia) |
| `display_name` | string (1–200) | Sí | Nombre final para mostrar | `Distribuidora Farma` | Formulario |
| `preferred_contact_person_id` | UUID \| null | No; acepta `null` (si se omite queda `null`) | Contacto preferido final; debe ser un contacto activo de la organización del proveedor | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) (lista las personas de contacto de la organización; errores en §4) |

No se admiten en el cuerpo `organization_identity_id`, `company_id`, `status` ni `block_reason`: su presencia responde `422 IMMUTABLE_FIELD`.

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`) con `version` incrementada si hubo cambios:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión; es la que debe enviarse en la siguiente modificación. Si no hubo cambios se mantiene |
| `status`, `block_reason` | — | No cambian con esta API |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 3](#3-consultar-un-proveedor), mostrar los cambios y repetir con la nueva `version` |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Otro proveedor de la empresa ya usa ese `internal_code` | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.IMMUTABLE_FIELD` | El cuerpo incluye `organization_identity_id`, `company_id`, `status` o `block_reason` | Error de programación: no enviar esos campos |
| `422` | `COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID` | El contacto no existe, está inactivo o es de otra organización | Volver a cargar los contactos activos con la [API 4](#4-consultar-las-personas-de-contacto-del-proveedor) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` < 1, `internal_code` vacío o > 60, `display_name` vacío o > 200, campo faltante o desconocido | Corregir el formulario |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Sin permiso en Party Identity para validar el contacto | Pedir `perm:party-identity:organization_contact_persons:read` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por campo inmutable:

```json
{
  "type": "https://sio/errors/commercial-relationship/immutable-field",
  "title": "Campo inmutable",
  "status": 422,
  "detail": "Los campos organization_identity_id no pueden modificarse.",
  "instance": "/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "code": "COMMERCIAL_RELATIONSHIP.IMMUTABLE_FIELD",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "Los campos organization_identity_id no pueden modificarse.",
      "code": "IMMUTABLE_FIELD"
    }
  ]
}
```

## 6. Inactivar un proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/deactivate`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:delete`

### ¿Qué hace esta API?

Pasa un proveedor `ACTIVE` a `INACTIVE` sin borrarlo ni borrar su historial. Desde ese momento [Compras](compras.md) rechaza nuevas compras a ese proveedor con `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (motivo `SUPPLIER_NOT_ELIGIBLE`) y Commercial Relationship rechaza registrarle o reactivarle condiciones de pago y productos con `422 COMPANY_SUPPLIER_INACTIVE`; las compras ya confirmadas no cambian. La identidad en Party Identity no se toca. Es la única escritura sobre proveedores permitida cuando la empresa está `INACTIVE`. Registra `DEACTIVATE_COMPANY_SUPPLIER` en Audit. Clasificada como `HIGH_RISK` en la ficha: conviene pedir confirmación al usuario.

Antes necesita: la `version` actual ([API 3](#3-consultar-un-proveedor)) y que el proveedor esté `ACTIVE` (un proveedor `BLOCKED` no se inactiva: se desbloquea primero).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/deactivate' \
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
| `company_supplier_id` | UUID | Sí | Proveedor a inactivar | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |

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
| `version` | integer ≥ 1 | Sí | Versión vigente del proveedor | `2` | `version` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) |

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`) con `status` `INACTIVE` y `version` incrementada:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "INACTIVE",
  "version": 3,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:00:00Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `INACTIVE` | El proveedor deja de aparecer en la lista por defecto de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (usar `status=INACTIVE` o `ALL`) |
| `version` | integer | Valor que debe enviarse en la [API 7](#7-reactivar-un-proveedor) o la [API 8](#8-bloquear-un-proveedor) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 3](#3-consultar-un-proveedor) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El proveedor no está `ACTIVE` (ya `INACTIVE` o `BLOCKED`) | Refrescar la ficha; si está bloqueado, desbloquear primero ([API 9](#9-desbloquear-un-proveedor)) |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente, < 1 o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde | Reintentar más tarde |

Ejemplo de `409` por estado:

```json
{
  "type": "https://sio/errors/commercial-relationship/invalid-status-transition",
  "title": "Transición de estado inválida",
  "status": 409,
  "detail": "La acción deactivate no es válida desde el estado BLOCKED.",
  "instance": "/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/deactivate",
  "code": "COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 7. Reactivar un proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/reactivate`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:update`

### ¿Qué hace esta API?

Devuelve un proveedor `INACTIVE` a `ACTIVE` conservando su `id`, su código, sus condiciones y sus productos, de modo que [Compras](compras.md) vuelve a aceptarlo. Es la respuesta correcta al `409 DUPLICATE_SUPPLIER` de la [API 1](#1-registrar-un-proveedor-de-la-empresa) cuando la organización ya fue proveedor antes. Un proveedor `BLOCKED` no se reactiva por aquí: se desbloquea con la [API 9](#9-desbloquear-un-proveedor).

Efectos verificados en el código: antes de reactivar vuelve a comprobar en Party Identity que la organización exista y esté `ACTIVE` (no revalida la persona de contacto); deja `block_reason` en `null`; exige empresa `ACTIVE`; registra `REACTIVATE_COMPANY_SUPPLIER` en Audit. Las condiciones de pago y los productos del proveedor que se hubieran inactivado no se reactivan automáticamente.

Antes necesita: la `version` actual ([API 3](#3-consultar-un-proveedor)) y `perm:party-identity:organization_identities:read` para la revalidación.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/reactivate' \
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
| `company_supplier_id` | UUID | Sí | Proveedor a reactivar | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) con `status=INACTIVE` (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |

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
| `version` | integer ≥ 1 | Sí | Versión vigente del proveedor | `3` | `version` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) |

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`) con `status` `ACTIVE` y `version` incrementada:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 4,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:30:00Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` | El proveedor vuelve a estar disponible para compras |
| `version` | integer | Nueva versión para la siguiente modificación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 3](#3-consultar-un-proveedor) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El proveedor no está `INACTIVE` (ya `ACTIVE` o `BLOCKED`) | Refrescar la ficha; si está bloqueado, usar la [API 9](#9-desbloquear-un-proveedor) |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_NOT_FOUND` | La organización ya no existe en Party Identity | Informar; registrar un proveedor nuevo con otra identidad |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_INACTIVE` | La organización está `INACTIVE` en Party Identity | Reactivar primero la identidad (PI 14) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden reactivar proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente, < 1 o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Sin permiso en Party Identity para revalidar la organización | Pedir `perm:party-identity:organization_identities:read` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden | Reintentar más tarde; nada se guardó |

## 8. Bloquear un proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/block`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:delete`

### ¿Qué hace esta API?

Suspende temporalmente un proveedor, dejándolo en `BLOCKED` con un motivo obligatorio que queda visible en `block_reason` y en Audit. Se usa ante incumplimientos o disputas: el proveedor no sirve para compras nuevas (`409 PURCHASE.REFERENCES_NOT_ELIGIBLE`, motivo `SUPPLIER_NOT_ELIGIBLE`) ni para registrarle condiciones o productos (`422 COMPANY_SUPPLIER_BLOCKED`), pero conserva todo su historial y se levanta con la [API 9](#9-desbloquear-un-proveedor). Del estado `BLOCKED` solo se sale desbloqueando: no se puede inactivar ni reactivar directamente.

Efectos verificados en el código: se permite desde `ACTIVE` o `INACTIVE`; no consulta Party Identity; guarda `block_reason`; registra `BLOCK_COMPANY_SUPPLIER` en Audit con el motivo; exige empresa `ACTIVE`. Clasificada como `HIGH_RISK`: pedir confirmación y el motivo al usuario.

Antes necesita: la `version` actual ([API 3](#3-consultar-un-proveedor)) y el motivo escrito por el usuario.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/block' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "block_reason": "Incumplimiento reiterado en los plazos de entrega",
    "version": 4
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor a bloquear | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "block_reason": "Incumplimiento reiterado en los plazos de entrega",
  "version": 4
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `block_reason` | string (1–500) | Sí | Motivo del bloqueo; se recortan espacios; queda visible en la ficha y en Audit | `Incumplimiento reiterado en los plazos de entrega` | Formulario (texto del usuario) |
| `version` | integer ≥ 1 | Sí | Versión vigente del proveedor | `4` | `version` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) |

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`) con `status` `BLOCKED`, `block_reason` informado y `version` incrementada:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "BLOCKED",
  "version": 5,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T11:00:00Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": "Incumplimiento reiterado en los plazos de entrega"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `BLOCKED` | Mostrar el proveedor como bloqueado; la única acción disponible es desbloquear |
| `block_reason` | string | Motivo para mostrar en la ficha |
| `version` | integer | Valor que debe enviarse en la [API 9](#9-desbloquear-un-proveedor) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 3](#3-consultar-un-proveedor) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El proveedor ya está `BLOCKED` | Refrescar la ficha |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden bloquear proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `block_reason` vacío o > 500, `version` ausente o < 1, campo desconocido | Pedir el motivo y corregir |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde | Reintentar más tarde |

## 9. Desbloquear un proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/unblock`
**Permiso requerido:** `perm:commercial-relationship:company_suppliers:update`

### ¿Qué hace esta API?

Levanta el bloqueo de un proveedor `BLOCKED` y lo deja `ACTIVE` (aunque antes del bloqueo estuviera `INACTIVE`), borrando `block_reason`. A partir de ahí [Compras](compras.md) vuelve a aceptarlo.

Efectos verificados en el código: solo desde `BLOCKED`; antes de desbloquear vuelve a comprobar en Party Identity que la organización exista y esté `ACTIVE` (no revalida la persona de contacto); exige empresa `ACTIVE`; registra `UNBLOCK_COMPANY_SUPPLIER` en Audit.

Antes necesita: la `version` actual ([API 3](#3-consultar-un-proveedor)) y `perm:party-identity:organization_identities:read` para la revalidación.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/unblock' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 5
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor a desbloquear | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `id` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) o `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) con `status=BLOCKED` (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 5
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del proveedor | `5` | `version` de la [API 3](#3-consultar-un-proveedor) (devuelve la ficha del proveedor; errores en §3) |

### Respuesta exitosa

`200 OK` (`CompanySupplierResponse`) con `status` `ACTIVE`, `block_reason` `null` y `version` incrementada:

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 6,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T11:30:00Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma",
  "preferred_contact_person_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "block_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status`, `block_reason` | `ACTIVE`, `null` | El proveedor vuelve a estar disponible para compras |
| `version` | integer | Nueva versión para la siguiente modificación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 3](#3-consultar-un-proveedor) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El proveedor no está `BLOCKED` | Refrescar la ficha |
| `422` | `COMMERCIAL_RELATIONSHIP.ORGANIZATION_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_INACTIVE` | La organización ya no existe o está `INACTIVE` en Party Identity | Informar; reactivar primero la identidad (PI 14) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden desbloquear proveedores en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente, < 1 o campo desconocido | Corregir la solicitud |
| `403` | `COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED` | Sin permiso en Party Identity para revalidar la organización | Pedir `perm:party-identity:organization_identities:read` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Party Identity u Operational Context no responden | Reintentar más tarde; nada se guardó |

## 10. Consultar los tipos de condición de pago

**Método:** `GET`
**URL:** `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types`
**Permiso requerido:** `perm:payment-reference:global_payment_condition_types:read`

### ¿Qué hace esta API?

Devuelve el catálogo global de tipos de condición de pago administrado por la plataforma en Payment Reference (contado, crédito, financiación…), con su `code`, nombre y estado. Su `id` es el `payment_condition_type_id` que exige la [API 12](#12-registrar-una-condición-de-pago-del-proveedor). El `code` determina la regla del plazo en Commercial Relationship: `CASH` exige `payment_terms_days` igual a `0`; `CREDIT` y `FINANCING` exigen un plazo mayor que `0`; cualquier otro código admite de `0` a `3650`. Además, [Compras](compras.md) solo acepta hoy condiciones cuyo tipo tenga `code` `CASH` (compras de contado); una condición de otro tipo se rechaza al comprar con `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (motivo `PAYMENT_CONDITION_NOT_AVAILABLE`).

Payment Reference **no usa el prefijo `/api/v1`** y responde los errores en formato FastAPI simple (`{"detail": …}`), no en Problem Details.

Antes necesita: solo el token.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-payment-reference-dev.onrender.com/global-payment-condition-types?status=ACTIVE&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | No; sin filtro devuelve ambos | Estado del tipo | Uno de: `ACTIVE`, `INACTIVE`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz (usar `ACTIVE` para el selector) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `search` | string | No | Búsqueda por código, nombre o descripción | Texto libre; p. ej. `contado` o `CASH` | `&search=contado` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-payment-reference-dev.onrender.com/global-payment-condition-types?status=ACTIVE&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[GlobalPaymentConditionTypeResponse]`):

```json
{
  "items": [
    {
      "id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
      "code": "CASH",
      "name": "Contado",
      "description": "Pago contra entrega",
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z",
      "version": 1
    },
    {
      "id": "e7f8a9b0-c1d2-4e3f-8a4b-5c6d7e8f9a0b",
      "code": "CREDIT",
      "name": "Crédito",
      "description": "Pago a plazo en días calendario",
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z",
      "version": 1
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 2,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | **Lo que se envía como `payment_condition_type_id`** en la [API 12](#12-registrar-una-condición-de-pago-del-proveedor) |
| `items[].code` | string | `CASH` → plazo `0`; `CREDIT` / `FINANCING` → plazo > 0; solo `CASH` sirve hoy para comprar |
| `items[].name`, `description` | string \| null | Texto para el selector |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo un tipo `ACTIVE` se acepta al registrar o reactivar una condición |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `403` | `{"detail": …}` (formato FastAPI) | Falta `perm:payment-reference:global_payment_condition_types:read` | Mostrar que faltan permisos |
| `422` | Formato FastAPI (`detail[]` con `loc`, `msg`, `type`) | `page_size` fuera de 1–100, `page` < 1 o `status` fuera de la enumeración | Corregir los filtros |

## 11. Consultar las condiciones de pago de los proveedores

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions`
**Permiso requerido:** `perm:commercial-relationship:supplier_payment_conditions:read`

### ¿Qué hace esta API?

Lista, con paginación y filtros, las condiciones de pago acordadas con los proveedores de la empresa: tipo (de Payment Reference), moneda, plazo en días, cupo de crédito, porcentajes de interés y de descuento por pronto pago, si es la predeterminada del proveedor en esa moneda y su vigencia. Se usa para mostrar las condiciones de un proveedor y para que el comprador elija la `supplier_payment_condition_id` **opcional** de la cabecera de una compra. No admite búsqueda por texto; el filtro habitual es `company_supplier_id`.

Por defecto solo devuelve condiciones `ACTIVE`. Con `applicable_at` devuelve solo las vigentes en ese instante (`valid_from ≤ instante < valid_to`).

Antes necesita: `company_id` con membresía `ACTIVE`. Funciona también con la empresa `INACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60&status=ACTIVE&page=1&page_size=20' \
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
| `company_supplier_id` | UUID | No | Solo las condiciones de ese proveedor | UUID de un proveedor; p. ej. `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las condiciones | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `payment_condition_type_id` | UUID | No | Solo condiciones de ese tipo | UUID de un tipo de condición; p. ej. `83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd` | `&payment_condition_type_id=83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd` | `items[].id` de la [API 10](#10-consultar-los-tipos-de-condición-de-pago) (lista los tipos de condición de pago; errores en §10) |
| `currency_code` | string (3 letras) | No | Solo condiciones en esa moneda; se normaliza a mayúsculas | Código ISO 4217 de 3 letras; p. ej. `COP`, `USD` | `&currency_code=COP` | Interfaz (moneda de la empresa, `default_currency` de la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa)) |
| `is_default` | boolean | No | Solo la predeterminada (`true`) o las no predeterminadas (`false`) | Booleano: `true` o `false`; p. ej. `true` | `&is_default=true` | Interfaz |
| `applicable_at` | date-time con zona horaria | No | Solo las vigentes en ese instante | Fecha y hora ISO 8601 con zona; p. ej. `2026-10-20T00:00:00Z` | `&applicable_at=2026-10-20T00:00:00Z` | Interfaz (fecha de la compra) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[SupplierPaymentConditionResponse]`):

```json
{
  "items": [
    {
      "id": "6c87690b-4ca7-4c9d-8752-ca37a23afd94",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
      "currency_code": "COP",
      "payment_terms_days": 0,
      "credit_limit": "5000000.00",
      "interest_rate_percentage": null,
      "cash_discount_percentage": "2.0000",
      "is_default": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null
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
| `items[].id` | UUID | La `supplier_payment_condition_id` que acepta [Compras](compras.md) como campo opcional de la cabecera; debe ser del mismo proveedor de la compra |
| `items[].payment_condition_type_id` | UUID | Tipo del catálogo global; su `code` y nombre se leen con la [API 10](#10-consultar-los-tipos-de-condición-de-pago) (no se guardan aquí) |
| `items[].currency_code`, `payment_terms_days` | string, integer | Moneda y plazo en días |
| `items[].credit_limit` | string decimal \| null | Cupo de crédito con los decimales de la moneda |
| `items[].interest_rate_percentage`, `cash_discount_percentage` | string decimal (4 decimales) \| null | Porcentajes informativos |
| `items[].is_default` | boolean | Predeterminada del proveedor en esa moneda (solo una a la vez) |
| `items[].valid_from`, `valid_to` | date-time, date-time \| null | Vigencia; `valid_to` `null` es sin fin |
| `items[].status`, `version` | — | Estado y versión para las operaciones de mantenimiento (CR 43–45) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `currency_code` sin 3 caracteres, `applicable_at` sin zona horaria, `status` fuera de la enumeración, UUID o booleano inválidos, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 12. Registrar una condición de pago del proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions`
**Permiso requerido:** `perm:commercial-relationship:supplier_payment_conditions:create`

### ¿Qué hace esta API?

Registra una condición de pago acordada con un proveedor (tipo, moneda, plazo, cupo, porcentajes, vigencia) para poder elegirla al comprar. Es **opcional** para Compras: una compra sin `supplier_payment_condition_id` se registra de contado.

Reglas verificadas en el código, en este orden: (1) `currency_code` debe estar en la lista cerrada de monedas admitidas (ISO 4217; p. ej. `COP`, `USD`, `EUR`) y `credit_limit` no puede tener más decimales que su moneda; (2) el proveedor debe ser de la empresa y estar `ACTIVE` (`422 COMPANY_SUPPLIER_NOT_FOUND`, `COMPANY_SUPPLIER_INACTIVE` o `COMPANY_SUPPLIER_BLOCKED`); (3) si no se envía `valid_from`, se toma el instante del servidor; `valid_to`, si existe, debe ser posterior a `valid_from`; (4) el tipo debe existir y estar `ACTIVE` en Payment Reference; (5) el plazo debe ser coherente con el `code` del tipo (`CASH` → `0`; `CREDIT` / `FINANCING` → mayor que `0`); (6) si `is_default` es `true`, la condición predeterminada anterior del mismo proveedor y moneda deja de serlo. Nada se guarda si alguna regla falla. Crea la condición con `status` `ACTIVE` y `version` `1`, devuelve `Location: /api/v1/supplier-payment-conditions/{id}` y registra `CREATE_SUPPLIER_PAYMENT_CONDITION` en Audit.

Antes necesita: el proveedor `ACTIVE` ([API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa)), el tipo de condición ([API 10](#10-consultar-los-tipos-de-condición-de-pago)) y la moneda funcional de la empresa (`default_currency` de la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa)): Compras rechaza una condición en otra moneda (`PAYMENT_CONDITION_CURRENCY_MISMATCH`).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
    "currency_code": "COP",
    "payment_terms_days": 0,
    "credit_limit": "5000000.00",
    "interest_rate_percentage": null,
    "cash_discount_percentage": "2",
    "is_default": true,
    "valid_from": "2026-10-01T00:00:00Z",
    "valid_to": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del proveedor | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 0,
  "credit_limit": "5000000.00",
  "interest_rate_percentage": null,
  "cash_discount_percentage": "2",
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` de la empresa; inmutable después de crear | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) o `id` de la [API 1](#1-registrar-un-proveedor-de-la-empresa) (registra el proveedor; errores en §1) · guía [supplier_id](../parametros/supplier-id.md) |
| `payment_condition_type_id` | UUID | Sí | Tipo de condición `ACTIVE` en Payment Reference | `83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd` | `items[].id` de la [API 10](#10-consultar-los-tipos-de-condición-de-pago) (lista los tipos de condición de pago; errores en §10); para comprar hoy, el de `code` `CASH` |
| `currency_code` | string (1–10) | Sí | Moneda ISO 4217 de la lista cerrada admitida; se normaliza a mayúsculas | `COP` | `default_currency` de la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa) (devuelve la ficha de la empresa; errores en esa sección) |
| `payment_terms_days` | integer 0–3650 | No; por defecto `0` | Plazo en días; coherente con el `code` del tipo (`CASH` → `0`; `CREDIT` / `FINANCING` → > 0) | `0` | Formulario; la regla depende de `items[].code` de la [API 10](#10-consultar-los-tipos-de-condición-de-pago) |
| `credit_limit` | número o cadena decimal ≥ 0 (máx. 2 decimales, hasta 18 dígitos) \| null | No; acepta `null` | Cupo de crédito; no puede tener más decimales que la moneda | `"5000000.00"` | Formulario |
| `interest_rate_percentage` | número o cadena decimal 0–100 (máx. 4 decimales) \| null | No; acepta `null` | Tasa de interés informativa | `null` | Formulario |
| `cash_discount_percentage` | número o cadena decimal 0–100 (máx. 4 decimales) \| null | No; acepta `null` | Descuento por pronto pago informativo | `"2"` | Formulario |
| `is_default` | boolean | No; por defecto `false` | Marca esta condición como predeterminada del proveedor en esa moneda; desmarca la anterior | `true` | Formulario |
| `valid_from` | date-time con zona horaria \| null | No; si falta, el instante del servidor | Inicio de la vigencia | `2026-10-01T00:00:00Z` | Formulario |
| `valid_to` | date-time con zona horaria \| null | No; acepta `null` (sin fin) | Fin de la vigencia; debe ser posterior a `valid_from` | `null` | Formulario |

### Respuesta exitosa

`201 Created` (`SupplierPaymentConditionResponse`), con cabecera `Location: /api/v1/supplier-payment-conditions/{id}`:

```json
{
  "id": "6c87690b-4ca7-4c9d-8752-ca37a23afd94",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 0,
  "credit_limit": "5000000.00",
  "interest_rate_percentage": null,
  "cash_discount_percentage": "2.0000",
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | La nueva `supplier_payment_condition_id` que puede enviarse en la cabecera de la compra ([Compras](compras.md)) |
| `currency_code` | string | Ya normalizada a mayúsculas |
| `credit_limit`, `interest_rate_percentage`, `cash_discount_percentage` | string decimal \| null | Importes y porcentajes como cadena (2 decimales según la moneda; 4 en porcentajes) |
| `valid_from` | date-time | El enviado o el instante del servidor |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | `currency_code` no está en la lista cerrada de monedas | Ofrecer solo la moneda de la empresa |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_SCALE_NOT_ALLOWED` | `credit_limit` tiene más decimales que los de la moneda | Limitar los decimales del cupo |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_SUPPLIER_NOT_FOUND` | El proveedor no existe en la empresa | Volver a elegir el proveedor con la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_SUPPLIER_INACTIVE` / `COMPANY_SUPPLIER_BLOCKED` | El proveedor está `INACTIVE` o `BLOCKED` | Reactivar ([API 7](#7-reactivar-un-proveedor)) o desbloquear ([API 9](#9-desbloquear-un-proveedor)) antes |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no es posterior a `valid_from` | Corregir las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.PAYMENT_CONDITION_TYPE_NOT_FOUND` / `PAYMENT_CONDITION_TYPE_INACTIVE` | El tipo no existe o está `INACTIVE` en Payment Reference | Volver a cargar la [API 10](#10-consultar-los-tipos-de-condición-de-pago) |
| `422` | `COMMERCIAL_RELATIONSHIP.PAYMENT_TERMS_INCONSISTENT` | El plazo no corresponde al `code` del tipo (contado con días, crédito con `0`) o está fuera de 0–3650 | Ajustar el plazo según el tipo elegido |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar condiciones en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, fecha sin zona horaria, porcentaje fuera de 0–100, `payment_terms_days` no entero, campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Payment Reference u Operational Context no responden (`dependency` indica cuál) | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por plazo incoherente:

```json
{
  "type": "https://sio/errors/commercial-relationship/payment-terms-inconsistent",
  "title": "Plazo incoherente",
  "status": 422,
  "detail": "Una condición de contado exige un plazo de 0 días.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions",
  "code": "COMMERCIAL_RELATIONSHIP.PAYMENT_TERMS_INCONSISTENT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "payment_terms_days",
      "message": "Una condición de contado exige un plazo de 0 días.",
      "code": "PAYMENT_TERMS_INCONSISTENT"
    }
  ]
}
```

Ejemplo de `422` por proveedor bloqueado:

```json
{
  "type": "https://sio/errors/commercial-relationship/company-supplier-blocked",
  "title": "Proveedor bloqueado",
  "status": 422,
  "detail": "El proveedor está bloqueado: desbloquéelo antes de asociarle productos o condiciones de pago.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions",
  "code": "COMMERCIAL_RELATIONSHIP.COMPANY_SUPPLIER_BLOCKED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "company_supplier_id",
      "message": "El proveedor está bloqueado: desbloquéelo antes de asociarle productos o condiciones de pago.",
      "code": "COMPANY_SUPPLIER_BLOCKED"
    }
  ]
}
```

## 13. Consultar los productos que suministran los proveedores

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products`
**Permiso requerido:** `perm:commercial-relationship:supplier_products:read`

### ¿Qué hace esta API?

Lista, con paginación y filtros, qué productos empresariales le compra la empresa a cada proveedor, con el código del producto en el proveedor, la unidad de compra, cantidades mínimas y por empaque, el costo negociado de referencia, el tiempo de entrega esperado, la prioridad y si es el proveedor preferido para ese producto. Se usa para sugerir productos al armar una compra a un proveedor (filtro `company_supplier_id`) o para saber a quién comprarle un producto (filtro `company_product_id`). La búsqueda por texto es solo sobre `supplier_product_code`.

Por defecto solo devuelve relaciones `ACTIVE`.

Antes necesita: `company_id` con membresía `ACTIVE`. Funciona también con la empresa `INACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60&status=ACTIVE&page=1&page_size=20' \
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
| `company_supplier_id` | UUID | No | Solo los productos de ese proveedor | UUID de un proveedor; p. ej. `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) · guía [supplier_id](../parametros/supplier-id.md) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de la relación | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, solo en `supplier_product_code` | Texto libre: parte del código del producto en el proveedor; p. ej. `DF-ACET` | `&search=DF-ACET` | Interfaz |
| `company_product_id` | UUID | No | Solo las relaciones de ese producto empresarial (¿quién me lo vende?) | UUID de un producto empresarial; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` del listado de productos de la empresa en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) (qué hace y sus errores) |
| `company_product_presentation_id` | UUID | No | Solo las relaciones de esa presentación | UUID de una presentación; p. ej. `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `&company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | Guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) (qué hace y sus errores) |
| `is_preferred` | boolean | No | Solo los proveedores preferidos (`true`) o no preferidos (`false`) | Booleano: `true` o `false`; p. ej. `true` | `&is_preferred=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products?company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[SupplierProductResponse]`):

```json
{
  "items": [
    {
      "id": "1d51dc80-b75a-4a4a-8a2d-a2dce0fe061e",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_code": "DF-ACET-500",
      "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
      "minimum_order_quantity": "1.0000",
      "pack_quantity": "12.0000",
      "negotiated_unit_cost": "1850.0000",
      "currency_code": "COP",
      "expected_supplier_lead_time_hours": "48.00",
      "priority": 1,
      "is_preferred": true
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
| `items[].id` | UUID | La `supplier_product_id` que acepta [Compras](compras.md) como campo opcional de cada línea; debe ser del mismo proveedor, producto y presentación de la línea |
| `items[].company_product_id`, `company_product_presentation_id` | UUID, UUID \| null | Producto empresarial y presentación que suministra; son los que se envían en la línea de la compra |
| `items[].supplier_product_code` | string \| null | Código del producto en el catálogo del proveedor (para el pedido) |
| `items[].purchase_unit_id` | UUID | Unidad de compra; siempre la unidad base del producto global |
| `items[].minimum_order_quantity`, `pack_quantity` | string decimal (4 decimales) | Cantidad mínima y unidades por empaque, para validar la cantidad pedida en la interfaz |
| `items[].negotiated_unit_cost`, `currency_code` | string decimal (4 decimales) \| null, string | Costo de referencia para prellenar `unit_cost` en la compra; el comprador puede cambiarlo |
| `items[].expected_supplier_lead_time_hours` | string decimal (2 decimales) \| null | Tiempo de entrega esperado |
| `items[].priority`, `is_preferred` | integer \| null, boolean | Orden sugerido y proveedor preferido del producto (solo uno por producto) |
| `items[].status`, `version` | — | Estado y versión para las operaciones de mantenimiento (CR 37–39) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, UUID o booleano inválidos, paginación fuera de rango | Corregir los filtros |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context no responde al verificar la membresía | Reintentar más tarde |

## 14. Registrar un producto que suministra el proveedor

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products`
**Permiso requerido:** `perm:commercial-relationship:supplier_products:create`

### ¿Qué hace esta API?

Registra que un proveedor suministra un producto empresarial (y, opcionalmente, una presentación concreta), con el código del producto en el proveedor, la unidad de compra, cantidades, costo negociado y tiempos de entrega. Es **opcional** para Compras: sirve para sugerir productos y prellenar el costo; el `unit_cost` de la línea lo escribe siempre el comprador.

Reglas verificadas en el código, en este orden: (1) `currency_code` debe estar en la lista cerrada de monedas; (2) el proveedor debe ser de la empresa y estar `ACTIVE`; (3) el producto empresarial debe ser de la empresa y estar `ACTIVE`; (4) la presentación, si se envía, debe ser de la empresa, pertenecer a ese producto, estar `ACTIVE` y ser comprable (`is_purchasable`); (5) no puede existir otra relación `ACTIVE` para el mismo proveedor, producto y presentación (`409 DUPLICATE_SUPPLIER_PRODUCT`); (6) `purchase_unit_id` debe ser exactamente la unidad base del producto global en Product Catalog (`422 PURCHASE_UNIT_NOT_BASE_UNIT`); (7) si `is_preferred` es `true`, el proveedor preferido anterior del producto deja de serlo. Nada se guarda si alguna regla falla. Crea la relación con `status` `ACTIVE` y `version` `1`, devuelve `Location: /api/v1/supplier-products/{id}` y registra `CREATE_SUPPLIER_PRODUCT` en Audit.

Antes necesita: el proveedor `ACTIVE` ([API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa)); el producto empresarial y, si aplica, su presentación comprable ([Productos y precios](productos-y-precios.md)); la unidad base del producto global, que se lee en Product Catalog: `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/{global_product_id}` (permiso `perm:product-catalog:products:read`; devuelve la ficha del producto global con su `base_unit_id`; errores `404` si no existe y `422` si el UUID es inválido; ficha [Product Catalog 53](../servicios/product-catalog.md#53-get-productsproduct_id)), donde `global_product_id` es el campo del mismo nombre del producto empresarial.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "supplier_product_code": "DF-ACET-500",
    "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
    "minimum_order_quantity": "1",
    "pack_quantity": "12",
    "negotiated_unit_cost": "1850",
    "currency_code": "COP",
    "expected_supplier_lead_time_hours": "48",
    "priority": 1,
    "is_preferred": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del proveedor y del producto | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "12",
  "negotiated_unit_cost": "1850",
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": "48",
  "priority": 1,
  "is_preferred": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` de la empresa; inmutable después de crear | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` | `items[].id` de la [API 2](#2-buscar-y-listar-los-proveedores-de-la-empresa) (lista los proveedores; errores en §2) o `id` de la [API 1](#1-registrar-un-proveedor-de-la-empresa) (registra el proveedor; errores en §1) · guía [supplier_id](../parametros/supplier-id.md) |
| `company_product_id` | UUID | Sí | Producto empresarial `ACTIVE` de la empresa; inmutable después de crear | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` del listado de productos de la empresa en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) (qué hace y sus errores) |
| `company_product_presentation_id` | UUID \| null | No; acepta `null` | Presentación `ACTIVE` y comprable (`is_purchasable: true`) del mismo producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].id` de las presentaciones del producto en [Productos y precios](productos-y-precios.md) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) (qué hace y sus errores) |
| `supplier_product_code` | string (≤ 100) \| null | No; acepta `null`; en blanco se guarda `null` | Código del producto en el catálogo del proveedor | `DF-ACET-500` | Formulario |
| `purchase_unit_id` | UUID | Sí | Unidad de compra; debe ser la unidad base del producto global | `0e747814-44f0-4d53-86bd-831b90fb587e` | `base_unit_id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/{global_product_id}` (ficha del producto global; permiso `perm:product-catalog:products:read`; ficha [Product Catalog 53](../servicios/product-catalog.md#53-get-productsproduct_id)), con el `global_product_id` del producto empresarial · guía [global_product_id](../parametros/global-product-id.md) |
| `minimum_order_quantity` | número o cadena decimal ≥ 0 (máx. 4 decimales) | No; por defecto `0` | Cantidad mínima de pedido | `"1"` | Formulario |
| `pack_quantity` | número o cadena decimal > 0 (máx. 4 decimales) | No; por defecto `1` | Unidades por empaque | `"12"` | Formulario |
| `negotiated_unit_cost` | número o cadena decimal ≥ 0 (máx. 4 decimales) \| null | No; acepta `null` | Costo unitario negociado, solo de referencia | `"1850"` | Formulario |
| `currency_code` | string (1–10) | Sí | Moneda ISO 4217 de la lista cerrada; se normaliza a mayúsculas | `COP` | `default_currency` de la [API 3 de Administración empresarial](administracion-empresarial.md#3-consultar-una-empresa) (devuelve la ficha de la empresa; errores en esa sección) |
| `expected_supplier_lead_time_hours` | número o cadena decimal ≥ 0 (máx. 2 decimales) \| null | No; acepta `null` | Horas de entrega esperadas | `"48"` | Formulario |
| `priority` | integer 0–32767 \| null | No; acepta `null` | Orden sugerido entre proveedores del mismo producto | `1` | Formulario |
| `is_preferred` | boolean | No; por defecto `false` | Proveedor preferido del producto; desmarca al anterior | `true` | Formulario |

### Respuesta exitosa

`201 Created` (`SupplierProductResponse`), con cabecera `Location: /api/v1/supplier-products/{id}`:

```json
{
  "id": "1d51dc80-b75a-4a4a-8a2d-a2dce0fe061e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1.0000",
  "pack_quantity": "12.0000",
  "negotiated_unit_cost": "1850.0000",
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": "48.00",
  "priority": 1,
  "is_preferred": true
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | La nueva `supplier_product_id` que puede enviarse en cada línea de la compra ([Compras](compras.md)) |
| `minimum_order_quantity`, `pack_quantity`, `negotiated_unit_cost` | string decimal (4 decimales) | Cantidades y costo ya normalizados como cadena |
| `expected_supplier_lead_time_hours` | string decimal (2 decimales) \| null | Horas de entrega |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER_PRODUCT` | Ya existe una relación `ACTIVE` para ese proveedor, producto y presentación | Buscarla con la [API 13](#13-consultar-los-productos-que-suministran-los-proveedores) y modificarla (CR 37) |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | `currency_code` no está en la lista cerrada de monedas | Ofrecer solo la moneda de la empresa |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_SUPPLIER_NOT_FOUND` / `COMPANY_SUPPLIER_INACTIVE` / `COMPANY_SUPPLIER_BLOCKED` | El proveedor no existe en la empresa, está `INACTIVE` o `BLOCKED` | Elegir otro proveedor o reactivarlo / desbloquearlo antes |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_NOT_FOUND` / `COMPANY_PRODUCT_INACTIVE` | El producto empresarial no existe en la empresa o está `INACTIVE` | Elegir otro producto en [Productos y precios](productos-y-precios.md) |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_FOUND` / `PRESENTATION_OF_OTHER_PRODUCT` / `PRESENTATION_INACTIVE` / `PRESENTATION_NOT_PURCHASABLE` | La presentación no existe, es de otro producto, está `INACTIVE` o no es comprable | Elegir una presentación comprable del mismo producto |
| `422` | `COMMERCIAL_RELATIONSHIP.PURCHASE_UNIT_NOT_BASE_UNIT` | `purchase_unit_id` no es la unidad base del producto global | Enviar `base_unit_id` del producto global (Product Catalog) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar productos de proveedor en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, cantidad negativa o `pack_quantity` ≤ 0, más decimales de los admitidos, `priority` fuera de 0–32767, `supplier_product_code` > 100, campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Sin permiso en Operational Context para consultar el acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Product Catalog u Operational Context no responden (`dependency` indica cuál) | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por unidad de compra:

```json
{
  "type": "https://sio/errors/commercial-relationship/purchase-unit-not-base-unit",
  "title": "Unidad de compra inválida",
  "status": 422,
  "detail": "La unidad de compra debe ser la unidad base del producto global.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products",
  "code": "COMMERCIAL_RELATIONSHIP.PURCHASE_UNIT_NOT_BASE_UNIT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "purchase_unit_id",
      "message": "La unidad de compra debe ser la unidad base del producto global.",
      "code": "PURCHASE_UNIT_NOT_BASE_UNIT"
    }
  ]
}
```

---

## Lo que Compras exige del proveedor

| Requisito | Obligatorio | Dónde se configura | Si falta o no cumple |
|---|---|---|---|
| `company_supplier_id` con `status` `ACTIVE` | Sí | [API 1](#1-registrar-un-proveedor-de-la-empresa), [API 7](#7-reactivar-un-proveedor), [API 9](#9-desbloquear-un-proveedor) | `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (`SUPPLIER_NOT_ELIGIBLE`) |
| Organización del proveedor con tipo y número de identificación en Party Identity | Sí | [API 14 de Gestión de clientes](gestion-de-clientes.md#14-actualizar-la-identidad-de-una-organización) | `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (`ORGANIZATION_IDENTIFICATION_MISSING`) |
| `payment_method_id` activo | Sí (cabecera de la compra) | Payment Reference ([payment_method_id](../parametros/payment-method-id.md)) | Ver [Compras](compras.md) |
| `supplier_payment_condition_id` del mismo proveedor, `ACTIVE`, vigente en la fecha, en la moneda de la empresa y de tipo `CASH` | No | [API 12](#12-registrar-una-condición-de-pago-del-proveedor) | `422 PURCHASE.VALIDATION_ERROR` (`PAYMENT_CONDITION_NOT_FOUND`, `PAYMENT_CONDITION_OF_OTHER_SUPPLIER`) o `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (`PAYMENT_CONDITION_INACTIVE`, `PAYMENT_CONDITION_NOT_VALID_ON_DATE`, `PAYMENT_CONDITION_CURRENCY_MISMATCH`, `PAYMENT_CONDITION_NOT_AVAILABLE`) |
| `supplier_product_id` por línea, del mismo proveedor, producto y presentación, `ACTIVE` | No | [API 14](#14-registrar-un-producto-que-suministra-el-proveedor) | `422 PURCHASE.VALIDATION_ERROR` (`SUPPLIER_PRODUCT_NOT_FOUND`, `SUPPLIER_PRODUCT_MISMATCH`) o `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` (`SUPPLIER_PRODUCT_INACTIVE`) |
| Impuesto de compra y política de ganancia por producto o presentación | Sí para confirmar | [Productos y precios](productos-y-precios.md) | Ver [Compras](compras.md) |

## Dependencias con otros módulos

- [Compras](compras.md) consume el proveedor (`company_supplier_id`, obligatorio y `ACTIVE`), sus condiciones de pago (`supplier_payment_condition_id`, opcional) y sus productos (`supplier_product_id`, opcional por línea). El costo de la línea (`unit_cost`) lo escribe siempre el comprador: `negotiated_unit_cost` es solo una referencia.
- [Productos y precios](productos-y-precios.md) define los productos empresariales y presentaciones a los que se asocian los productos de proveedor; la unidad de compra es la unidad base del producto global en Product Catalog.
- [Gestión de clientes](gestion-de-clientes.md) y [Administración empresarial](administracion-empresarial.md) comparten las identidades de organización de Party Identity: una organización puede ser a la vez empresa de SIO, proveedor y cliente de distintas empresas. Los proveedores son siempre organizaciones; los clientes pueden ser personas u organizaciones.
- La trazabilidad de todas las escrituras de este módulo se consulta en la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (entidades `CompanySupplier`, `SupplierPaymentCondition` y `SupplierProduct`).

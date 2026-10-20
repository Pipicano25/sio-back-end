# 6.3 Gestión de clientes

[← API principales](README.md) · [← Índice](../index.md)

Registrar, buscar, consultar y actualizar los clientes a los que la empresa vende. Un cliente de SIO se compone de dos partes que viven en servicios distintos:

| Parte | Servicio | Qué guarda | Alcance |
|---|---|---|---|
| **Identidad** (quién es) | [Party Identity](../servicios/party-identity.md) | Persona (`person_identity_id`: documento, nombres) u organización (`organization_identity_id`: NIT, razón social), más perfiles de contacto | Global: una misma identidad puede ser cliente de varias empresas |
| **Relación comercial** (es mi cliente) | [Commercial Relationship](../servicios/commercial-relationship.md) | `company_customer_id`, `customer_kind`, `internal_code`, `display_name`, `preferred_contact_person_id`, `status` | Empresa: solo existe dentro de un `company_id` |

Ventas usa **siempre** el `company_customer_id` ([customer-id](../parametros/customer-id.md)); nunca la identidad directamente.

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar o crear la identidad de una persona | `GET /api/v1/person-identities` · `POST /api/v1/person-identities` (Party Identity) | `perm:party-identity:person_identities:read` · `…:create` | [PI 3](../servicios/party-identity.md#3-get-person-identities) · [PI 4](../servicios/party-identity.md#4-post-person-identities) |
| 2 | Buscar o crear la identidad de una organización | `GET /api/v1/organization-identities` · `POST /api/v1/organization-identities` (Party Identity) | `perm:party-identity:organization_identities:read` · `…:create` | [PI 9](../servicios/party-identity.md#9-get-organization-identities) · [PI 10](../servicios/party-identity.md#10-post-organization-identities) |
| 3 | Registrar un cliente de la empresa | `POST /api/v1/companies/{company_id}/company-customers` (CR) | `perm:commercial-relationship:company_customers:create` | [CR 14](../servicios/commercial-relationship.md#14-post-companiescompany_idcompany-customers) |
| 4 | Buscar y listar los clientes de la empresa | `GET /api/v1/companies/{company_id}/company-customers` (CR) | `perm:commercial-relationship:company_customers:read` | [CR 13](../servicios/commercial-relationship.md#13-get-companiescompany_idcompany-customers) |
| 5 | Consultar un cliente | `GET /api/v1/company-customers/{company_customer_id}` (CR) | `perm:commercial-relationship:company_customers:read` | [CR 15](../servicios/commercial-relationship.md#15-get-company-customerscompany_customer_id) |
| 6 | Consultar los datos de identidad del cliente | `GET /api/v1/person-identities/{person_identity_id}` · `GET /api/v1/organization-identities/{organization_identity_id}` (Party Identity) | `perm:party-identity:person_identities:read` · `…organization_identities:read` | [PI 5](../servicios/party-identity.md#5-get-person-identitiesperson_identity_id) · [PI 11](../servicios/party-identity.md#11-get-organization-identitiesorganization_identity_id) |
| 7 | Actualizar un cliente | `PUT /api/v1/company-customers/{company_customer_id}` (CR) | `perm:commercial-relationship:company_customers:update` | [CR 16](../servicios/commercial-relationship.md#16-put-company-customerscompany_customer_id) |
| 8 | Actualizar la identidad | `PUT /api/v1/person-identities/{person_identity_id}` · `PUT /api/v1/organization-identities/{organization_identity_id}` (Party Identity) | `perm:party-identity:person_identities:update` · `…organization_identities:update` | [PI 6](../servicios/party-identity.md#6-put-person-identitiesperson_identity_id) · [PI 12](../servicios/party-identity.md#12-put-organization-identitiesorganization_identity_id) |
| 9 | Inactivar o reactivar un cliente | `POST /api/v1/company-customers/{company_customer_id}/deactivate` · `…/reactivate` (CR) | `perm:commercial-relationship:company_customers:delete` · `…:update` | [CR 17](../servicios/commercial-relationship.md#17-post-company-customerscompany_customer_iddeactivate) · [CR 18](../servicios/commercial-relationship.md#18-post-company-customerscompany_customer_idreactivate) |

Bases: Party Identity `https://sio-party-identity-dev.onrender.com/api/v1`; Commercial Relationship `https://sio-commercial-relationship-dev.onrender.com/api/v1`.

---

## 1 y 2. Buscar o crear la identidad

**¿Qué puede hacer el usuario?** Antes de registrar un cliente, comprobar si la persona u organización ya existe en SIO (porque otra empresa la registró o porque ya es proveedor o usuario) y, si no, crearla.

**¿Qué API debe consumir el frontend?**

| Caso | Buscar | Crear |
|---|---|---|
| Persona natural | `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=<documento o nombre>` (también `identification_country_id`, `identification_type`, `verification_status`, `status`) | `POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities` con `identification_country_id`, `identification_type`, `identification_number`, `first_name`, `last_name` (+ `middle_name`, `second_last_name`, `birth_date`, `verification_status`) |
| Persona jurídica | `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=<NIT o nombre>` (también `country_id`, `identification_type`, `registration_status`, `status`) | `POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` con `country_id`, `identification_type`, `identification_number`, `legal_name` (+ `trade_name`, `organization_type`, `registration_status`, `website`) |

**¿Qué necesita antes?** El [`country_id`](../parametros/country-id.md) del documento y un `identification_type` admitido por las reglas del país (`GET https://sio-party-identity-dev.onrender.com/api/v1/identification-type-rules?country_id=…`, PI 15): Party Identity valida formato y dígito de verificación según esas reglas.

**¿Cómo sabe que funcionó?** Búsqueda: `200` con `items[]`; el identificador es `items[].id`. Creación: `201` con `PersonIdentityResponse` u `OrganizationIdentityResponse` (`id`, `status: "ACTIVE"`, `version: 1`). Errores: `409` si ya existe una identidad con el mismo país, tipo y número (reutiliza la existente), `422` si el número no cumple la regla del tipo. Detalle en [person_identity_id](../parametros/person-identity-id.md) y [organization_identity_id](../parametros/organization-identity-id.md).

## 3. Registrar un cliente de la empresa

**¿Qué puede hacer el usuario?** Convertir una identidad en cliente de su empresa, con el código interno y el nombre con que la empresa lo reconoce.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`. Permiso `perm:commercial-relationship:company_customers:create`. Cuerpo `CompanyCustomerCreate`:

| Campo | Obligatorio | Regla verificada (`company_customer_service.py`) |
|---|---|---|
| `customer_kind` | Sí | `PERSON` u `ORGANIZATION` |
| `person_identity_id` | Con `PERSON` | Debe existir y estar `ACTIVE` en Party Identity |
| `organization_identity_id` | Con `ORGANIZATION` | Debe existir y estar `ACTIVE`; no puede ser la organización de la propia empresa (`409 SELF_RELATIONSHIP_NOT_ALLOWED`) |
| `internal_code` | Sí | 1–60, único en la empresa (`409 DUPLICATE_INTERNAL_CODE`) |
| `display_name` | Sí | 1–200 |
| `preferred_contact_person_id` | No | Solo con `ORGANIZATION`; persona de contacto activa de esa organización (`422 CONTACT_PERSON_INVALID`) |

```json
{
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez"
}
```

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) con membresía activa y la identidad de la funcionalidad 1 o 2.

**¿Cómo sabe que funcionó?** `201` con `CompanyCustomerResponse`: `id` (el [company_customer_id](../parametros/customer-id.md) que usará Ventas), `company_id`, `customer_kind`, identidades, `internal_code`, `display_name`, `status: "ACTIVE"`, `version: 1`. Errores: `409 DUPLICATE_CUSTOMER` (la misma identidad ya es cliente de la empresa), `422 PERSON_IDENTITY_NOT_FOUND` / `ORGANIZATION_IDENTITY_NOT_FOUND` / `…_INACTIVE`, `422 VALIDATION_ERROR` si falta la identidad que exige el `customer_kind`, `503 DEPENDENCY_UNAVAILABLE` si Party Identity no responde. Nada se guarda ante un rechazo.

## 4. Buscar y listar los clientes de la empresa

**¿Qué puede hacer el usuario?** Encontrar un cliente por código o nombre al iniciar una venta, o administrar la cartera de clientes.

**¿Qué API debe consumir el frontend?** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`. Permiso `perm:commercial-relationship:company_customers:read`. Consulta: `page`, `page_size` (1–100), `search` (≤ 100; `internal_code` y `display_name`), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `customer_kind`, `person_identity_id`, `organization_identity_id`.

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Qué necesita antes?** [company_id](../parametros/company-id.md).

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[CompanyCustomerResponse]`. La búsqueda es sobre los datos de la relación (código y nombre de la empresa), **no** sobre el documento de identidad: para buscar por documento usa la funcionalidad 1 o 2 y luego filtra aquí por `person_identity_id` u `organization_identity_id`.

## 5 y 6. Consultar un cliente y su identidad

**¿Qué API debe consumir el frontend?** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}` (permiso `perm:commercial-relationship:company_customers:read`) devuelve la relación en cualquier estado. Para mostrar documento, nombres completos o razón social, encadena `GET https://sio-party-identity-dev.onrender.com/api/v1/person-identities/{person_identity_id}` u `…/organization-identities/{organization_identity_id}`; los perfiles de contacto vigentes (correo, teléfono, dirección) están en `GET …/person-identities/{id}/contact-profile` (PI 21) y `GET …/organization-identities/{id}/contact-profile` (PI 26).

**¿Cómo sabe que funcionó?** `200` en cada llamada. `404 NOT_FOUND` en Commercial Relationship si el cliente es de otra empresa.

## 7 y 8. Actualizar un cliente y su identidad

**¿Qué puede hacer el usuario?** Cambiar el código interno, el nombre comercial o la persona de contacto preferida; corregir los datos legales de la identidad.

**¿Qué API debe consumir el frontend?** `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}` (permiso `perm:commercial-relationship:company_customers:update`) con `version`, `internal_code`, `display_name`, `preferred_contact_person_id`. Los campos `customer_kind`, `person_identity_id`, `organization_identity_id` y `status` son **inmutables**: para cambiar de identidad hay que inactivar el cliente y crear otro. Los datos legales se corrigen en Party Identity con `PUT …/person-identities/{id}` o `PUT …/organization-identities/{id}` (con `version`).

**¿Cómo sabe que funcionó?** `200` con el recurso y `version` incrementada. Errores: `409 VERSION_CONFLICT`, `409 DUPLICATE_INTERNAL_CODE`, `422 IMMUTABLE_FIELD`.

## 9. Inactivar o reactivar un cliente

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/deactivate` (permiso `perm:commercial-relationship:company_customers:delete`, `HIGH_RISK`) y `…/reactivate` (`…:update`), ambos con `{"version": n}`.

**¿Cómo sabe que funcionó?** `200` con `status` `INACTIVE` o `ACTIVE`. Efecto: Sales rechaza nuevas ventas a un cliente inactivo con `409 REFERENCES_NOT_ELIGIBLE`; las ventas ya confirmadas no cambian.

## Dependencias con otros módulos

- [Ventas](ventas.md) exige un `company_customer_id` `ACTIVE` al crear el borrador. Las ventas son de contado: las condiciones de pago a crédito por cliente no están implementadas en Sales (funcionalidad futura).
- [Administración empresarial](administracion-empresarial.md) y [Gestión de proveedores](gestion-de-proveedores.md) comparten las identidades de Party Identity: una organización puede ser a la vez empresa, proveedor y cliente de distintas empresas.
- [Reportes](reportes.md) agrupa ventas por sucursal y producto; no por cliente (no hay reporte por cliente en las 411 operaciones).

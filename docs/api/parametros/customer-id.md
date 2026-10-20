# Parámetro `company_customer_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

> El nombre exacto del parámetro en las rutas y cuerpos es **`company_customer_id`** (cliente de la empresa). En esta documentación el archivo se llama `customer-id` por brevedad.

| Propiedad | Valor |
|---|---|
| Qué representa | Un **cliente de una empresa**: la relación comercial entre la empresa y una persona u organización identificada en Party Identity. Las ventas se registran contra este identificador |
| Nombre en las rutas y cuerpos | `company_customer_id` (en Sales: campo `company_customer_id` del cuerpo y filtro `?company_customer_id=`; en Commercial Relationship: ruta `/company-customers/{company_customer_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear una venta |
| Ejemplo (ficticio) | `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` |
| Quién lo genera | Commercial Relationship, al incorporar el cliente (`id` de la respuesta) |
| Alcance | Empresa: solo lo ven los miembros de la empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación y búsqueda, los clientes de la empresa (personas y organizaciones) con su código interno, nombre para mostrar, tipo, identidad en Party Identity y estado. Por defecto solo `ACTIVE`. Es el buscador de clientes del punto de venta y la fuente de `company_customer_id`. Ficha técnica: [Commercial Relationship 13](../servicios/commercial-relationship.md#13-get-companiescompany_idcompany-customers); guía principal: [Gestión de clientes](../principales/gestion-de-clientes.md).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-customers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `customer_kind` (`PERSON`, `ORGANIZATION`), `person_identity_id` (UUID), `organization_identity_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_customers:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[CompanyCustomerResponse]`; valores ilustrativos):

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
      "created_at": "2026-02-01T10:00:00Z",
      "updated_at": "2026-02-01T10:00:00Z",
      "customer_kind": "PERSON",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "organization_identity_id": null,
      "internal_code": "CLI-000123",
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

**Campo exacto:** `items[].id`. `display_name` e `internal_code` son los textos para mostrar en un buscador. `person_identity_id` u `organization_identity_id` enlazan con la identidad en Party Identity.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_customers:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 100, `status` u otro filtro inválido, UUID mal formado | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context, Party Identity o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde |

## Si el cliente no existe todavía (operación `WRITE`)

1. Obtén o crea la identidad en Party Identity: [person_identity_id](person-identity-id.md) para personas u [organization_identity_id](organization-identity-id.md) para organizaciones.
2. Incorpóralo a la empresa:

**¿Qué hace la API de creación?** Crea la relación comercial «cliente» entre la empresa y una identidad existente y activa de Party Identity, con un código interno único por empresa y un nombre para mostrar. Devuelve `201` con el cliente creado; su `id` es el `company_customer_id`. Ficha técnica: [Commercial Relationship 14](../servicios/commercial-relationship.md#14-post-companiescompany_idcompany-customers).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-customers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` |
| Permiso | `perm:commercial-relationship:company_customers:create` |
| Clasificación | `WRITE` (crea una relación comercial de la empresa) |

Cuerpo (modelo `CompanyCustomerCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `customer_kind` | `"PERSON"` \| `"ORGANIZATION"` | Sí | — |
| `person_identity_id` | UUID \| null | Según `customer_kind` = `PERSON` | Debe existir y estar `ACTIVE` en Party Identity |
| `organization_identity_id` | UUID \| null | Según `customer_kind` = `ORGANIZATION` | Debe existir y estar `ACTIVE` en Party Identity |
| `internal_code` | string | Sí | 1 a 60 caracteres; único por empresa |
| `display_name` | string | Sí | 1 a 200 caracteres |
| `preferred_contact_person_id` | UUID \| null | No | Persona de contacto de la organización en Party Identity |

```json
{
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": null,
  "internal_code": "CLI-000123",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

La respuesta `201` devuelve el mismo objeto que la lista; el `company_customer_id` es su campo `id`.

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_customers:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_CUSTOMER` | Esa identidad ya es cliente de la empresa | Buscar el cliente existente |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un cliente con ese `internal_code` en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CUSTOMER_IDENTITY_MISMATCH` | `customer_kind` no corresponde al identificador enviado (`PERSON` con `organization_identity_id` o viceversa) | Corregir el tipo o el identificador |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Identidad inexistente o inactiva en Party Identity, campo obligatorio ausente, formato inválido o campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context, Party Identity o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=CompanyCustomer`.
- `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` → campo `company_customer_id` del cuerpo.
- Filtro `?company_customer_id=` al listar ventas.
- Condiciones de pago y perfil de crédito del cliente en Commercial Relationship (`customer-payment-conditions`, `customer-credit-profiles`) se consultan con este identificador.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no pertenece a la empresa o el usuario no tiene membresía |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` al crear la venta | El cliente está `INACTIVE` o no es elegible |
| `422` al crear el cliente | Identidad inexistente o inactiva en Party Identity, o `customer_kind` incoherente con el identificador enviado |

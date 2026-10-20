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

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-customers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `customer_kind` (`PERSON`, `ORGANIZATION`), `person_identity_id` (UUID), `organization_identity_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_customers:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?search=perez&status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
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

## Si el cliente no existe todavía (operación `WRITE`)

1. Obtén o crea la identidad en Party Identity: [person_identity_id](person-identity-id.md) para personas u [organization_identity_id](organization-identity-id.md) para organizaciones.
2. Incorpóralo a la empresa:

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

La respuesta `201` devuelve el mismo objeto que la lista; el `company_customer_id` es su campo `id`. Las reglas completas (unicidad, validaciones contra Party Identity, errores `409` y `422`) están en la ficha de [Commercial Relationship](../servicios/commercial-relationship.md).

## Cómo usarlo después

- `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` → campo `company_customer_id` del cuerpo.
- Filtro `?company_customer_id=` al listar ventas.
- Condiciones de pago y perfil de crédito del cliente en Commercial Relationship (`customer-payment-conditions`, `customer-credit-profiles`) se consultan con este identificador.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El cliente no pertenece a la empresa o el usuario no tiene membresía |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` al crear la venta | El cliente está `INACTIVE` o no es elegible |
| `422` al crear el cliente | Identidad inexistente o inactiva en Party Identity, o `customer_kind` incoherente con el identificador enviado |

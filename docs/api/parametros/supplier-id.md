# Parámetro `company_supplier_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

> El nombre exacto del parámetro en las rutas y cuerpos es **`company_supplier_id`** (proveedor de la empresa). El archivo se llama `supplier-id` por brevedad.

| Propiedad | Valor |
|---|---|
| Qué representa | Un **proveedor de una empresa**: la relación comercial entre la empresa y una organización identificada en Party Identity. Las compras se registran contra este identificador |
| Nombre en las rutas y cuerpos | `company_supplier_id` (en Purchase: campo del cuerpo y filtro `?company_supplier_id=`; en Commercial Relationship: ruta `/company-suppliers/{company_supplier_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear una compra |
| Ejemplo (ficticio) | `d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60` |
| Quién lo genera | Commercial Relationship, al seleccionar el proveedor (`id` de la respuesta) |
| Alcance | Empresa |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-suppliers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `BLOCKED`, `ALL`), `organization_identity_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_suppliers:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[CompanySupplierResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 2,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-01T10:10:00Z",
      "updated_at": "2026-03-01T09:00:00Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "PRV-000045",
      "display_name": "Distribuidora Ejemplo S.A.S.",
      "preferred_contact_person_id": null,
      "block_reason": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Un proveedor `BLOCKED` tiene `block_reason` informado y no es elegible para compras.

## Si el proveedor no existe todavía (operación `WRITE`)

1. Obtén o crea la identidad de la organización en Party Identity: [organization_identity_id](organization-identity-id.md).
2. Selecciónalo como proveedor de la empresa:

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-suppliers` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers` |
| Permiso | `perm:commercial-relationship:company_suppliers:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanySupplierCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `organization_identity_id` | UUID | Sí | Debe existir y estar `ACTIVE` en Party Identity |
| `internal_code` | string | Sí | 1 a 60 caracteres; único por empresa |
| `display_name` | string | Sí | 1 a 200 caracteres |
| `preferred_contact_person_id` | UUID \| null | No | Persona de contacto de la organización |

```json
{
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-000045",
  "display_name": "Distribuidora Ejemplo S.A.S.",
  "preferred_contact_person_id": null
}
```

La respuesta `201` devuelve el proveedor; el `company_supplier_id` es su campo `id`.

## Cómo usarlo después

- `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` → campo `company_supplier_id`.
- Filtro `?company_supplier_id=` al listar compras y condiciones de pago del proveedor (`supplier-payment-conditions`).
- Productos que ofrece el proveedor (`supplier-products`) y evaluaciones (`supplier-evaluations`) en Commercial Relationship.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El proveedor no pertenece a la empresa o el usuario no tiene membresía |
| `409 PURCHASE.REFERENCES_NOT_ELIGIBLE` | El proveedor está `INACTIVE` o `BLOCKED` |

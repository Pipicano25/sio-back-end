# Parámetro `purchase_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Purchase](../servicios/purchase.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **compra** de la empresa a un proveedor, desde el borrador (`DRAFT`) hasta la confirmación (`CONFIRMED`) y la recepción física (`receipt_status` `PENDING` → `RECEIVED`), o su cancelación (`CANCELLED`) |
| Nombre en las rutas y cuerpos | `purchase_id` (Purchase: `/companies/{company_id}/purchases/{purchase_id}/…`; Inventory y Audit lo reciben como `origin_id` / `entity_id`; Commercial Relationship lo muestra en las aplicaciones automáticas de precio) |
| Tipo | UUID (texto) |
| Obligatorio | Sí en todas las operaciones de una compra existente |
| Ejemplo (ficticio) | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` |
| Quién lo genera | Purchase, al crear el borrador (`id` de la respuesta `201`) |
| Alcance | Empresa y sucursal: la compra pertenece a la `branch_id` que recibirá la mercancía |

## Cómo obtenerlo

**Al crear la compra:** la respuesta `201` de `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` trae el campo `id`. Guárdalo junto con `version`.

**Para buscar una compra existente:**

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/purchases` |
| URL completa | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page`, `page_size`, `status` (`DRAFT`, `CONFIRMED`, `CANCELLED`), `branch_id`, `company_supplier_id`, `operation_date_from`, `operation_date_to` (fecha `YYYY-MM-DD`), `number` (por ejemplo `C-000045`) |
| Permiso | `perm:purchase:purchases:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases?status=CONFIRMED&company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PaginatedResponse[PurchaseResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "supplier_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-19",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "CASH",
      "payment_method_name_snapshot": "Efectivo",
      "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
      "number": "C-000045",
      "sequence_value": 45,
      "status": "CONFIRMED",
      "operation_date": "2026-10-19",
      "promised_delivery_at": null,
      "supplier_document_number": null,
      "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
      "supplier_identification_snapshot": "NIT 900123456-7",
      "currency_code": "COP",
      "observations": "Entrega en mostrador",
      "subtotal": "1600.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "1600.00",
      "inventory_operation_id": null,
      "receipt_status": "PENDING",
      "received_at": null,
      "received_by_user_id": null,
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "lines": [
        {
          "id": "ce488045-ed3f-4b6c-81d2-68ee8c3fe7a0",
          "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
          "line_number": 1,
          "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "supplier_product_id": null,
          "supplier_lead_time_snapshot_hours": null,
          "product_code_snapshot": "PRD-0001",
          "product_name_snapshot": "Acetaminofén 500 mg",
          "presentation_code_snapshot": "UN",
          "presentation_name_snapshot": "Unidad",
          "base_quantity_factor_snapshot": "1.00000000",
          "unit_code_snapshot": "UN",
          "quantity": "2",
          "unit_cost": "500.00",
          "discount_amount": "0",
          "tax_amount": "0",
          "tax_percentage": "19",
          "tax_percentage_source": "PRODUCT_DEFAULT",
          "warnings": [],
          "subtotal": "1600.00",
          "total": "1600.00",
          "base_quantity": "2.0000",
          "inventory_unit_cost": "500.00",
          "created_at": "2026-10-19T15:04:05Z",
          "updated_at": "2026-10-19T15:04:05Z",
          "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
          "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Observa también `status`, `receipt_status` (una compra confirmada con `receipt_status: PENDING` todavía no ha entrado al inventario) y `version`.

## Cómo usarlo después

- Consultar la compra con líneas, impuestos y totales: `GET …/companies/{company_id}/purchases/{purchase_id}` ([operación 5](../servicios/purchase.md#5-get-companiescompany_idpurchasespurchase_id)).
- Agregar, modificar o eliminar líneas: `POST`/`PUT`/`DELETE …/purchases/{purchase_id}/details[/{detail_id}]` (siempre con `version`).
- Confirmar: `POST …/purchases/{purchase_id}/confirmation` con `{"version": n}` y `Idempotency-Key`. Registrar la recepción física completa: `POST …/purchases/{purchase_id}/receipt` con `{"version": n, "full_receipt_confirmed": true}` y `Idempotency-Key`.
- Ver el estado de las operaciones (confirmación, recepción, cancelación): `GET …/purchases/{purchase_id}/operations` y la línea de tiempo `GET …/purchases/{purchase_id}/timeline`.
- Rastrear la entrada de inventario: `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/kardex?origin_type=PURCHASE&origin_id={purchase_id}`.

Los pasos completos están en [Registrar una compra](../ejemplos/registrar-compra.md) y en [Compras](../principales/compras.md).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PURCHASE.NOT_FOUND` | La compra no pertenece a la empresa o el usuario no tiene membresía |
| `409 PURCHASE.VERSION_CONFLICT` | El `version` enviado no es el actual |
| `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` | Al confirmar, alguna línea no tiene porcentaje de impuesto resoluble |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` | Al confirmar, alguna presentación no tiene política de ganancia en una lista vigente ([pricing-policy-id](pricing-policy-id.md)) |

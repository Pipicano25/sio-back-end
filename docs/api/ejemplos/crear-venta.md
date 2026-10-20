# Crear y confirmar una venta

[← Flujos](README.md) · [← Índice](../index.md) · Ficha: [Sales](../servicios/sales.md) · Módulo: [Ventas](../principales/ventas.md)

Flujo del punto de venta: venta de contado, **lista de precios elegida por el vendedor en cada línea**, precio resuelto por el sistema, confirmación con descuento de inventario. Perfil típico: grupo `ventas`. Los identificadores son ficticios y las respuestas siguen los modelos reales de cada servicio.

Regla aprobada: el frontend consulta los precios vigentes de la presentación en todas las listas, los muestra de mayor a menor precio, preselecciona el mayor, el vendedor elige y el frontend envía `price_list_id` en la línea. **Nunca envía `unit_price`** (`422 UNIT_PRICE_NOT_ALLOWED`).

## 1. Contexto operativo

`GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` → tomar una membresía con `status: ACTIVE` y `company_status: ACTIVE`, y una sucursal con `allowed: true` ([company_id](../parametros/company-id.md), [branch_id](../parametros/branch-id.md)). Permiso: `perm:operational-context:application_users:read`. Si hay varias empresas o sucursales, el usuario elige ([Acceso y contexto operativo §7](../principales/acceso-y-contexto-operativo.md#7-seleccionar-empresa-y-sucursal-de-trabajo)).

## 2. Elegir el cliente

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers?search=perez&status=ACTIVE` → `items[].id` es el [company_customer_id](../parametros/customer-id.md). Permiso: `perm:commercial-relationship:company_customers:read`. Si no existe, crear primero la [identidad de persona](../parametros/person-identity-id.md) y después el cliente ([Gestión de clientes](../principales/gestion-de-clientes.md)).

## 3. Buscar productos con existencias

`GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews?search=acetaminofen&status=ACTIVE` ([Product Inventory Query, operación 4](../servicios/product-inventory-query.md#4-get-companiescompany_idbranchesbranch_idproduct-overviews)). De cada elemento tomar `company_product_id` y, de `presentations[]`, una con `is_sellable: true`: su `company_product_presentation_id`. `stock.total_base_quantity` y `stock.branches[].base_quantity` son las existencias en unidad base. `presentations[].price` muestra el precio de **una** lista (la de `price_list_id` o la predeterminada): no lo uses para elegir; el paso 4 trae todas las opciones. Permisos: `perm:product-inventory-query:product_overviews:read` (+ `perm:product-inventory-query:stock:read` para existencias, `perm:commercial-relationship:price_list_items:read` para precios).

Con lector de código de barras: `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/by-identifier/{codigo}` ([Product Catalog, operación 52](../servicios/product-catalog.md#52-get-productsby-identifiervalue)) devuelve el producto global y la presentación; después se localiza el producto empresarial con `GET …/companies/{company_id}/company-products?global_product_id=…` ([company_product_id](../parametros/company-product-id.md)). Alternativa en una llamada: `product-overviews?barcode={codigo}`.

## 4. Listar las opciones de precio y elegir la lista

**4a. Listas vigentes de la moneda** (una vez por sesión): `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists?status=ACTIVE&currency_code=COP` ([operación 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists)); permiso `perm:commercial-relationship:price_lists:read`. Conservar `id` → `name` de las listas cuya vigencia (`valid_from`, `valid_to`) cubra el momento actual.

**4b. Precios vigentes de la presentación en todas las listas:**

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-19T15:00:00Z' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

([operación 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items); permiso `perm:commercial-relationship:price_list_items:read`). Respuesta `200` (`PaginatedResponse[PriceListItemResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "unit_price": "800.00",
      "currency_code": "COP",
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "origin": "MANUAL",
      "closure_reason": null,
      "automatic_application_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Cada elemento es una opción: `price_list_id` + `unit_price`. El frontend las ordena por `unit_price` **descendente**, les pone el nombre de la lista (4a) y **preselecciona la primera** (la de mayor precio). El vendedor puede cambiar a otra lista. El `price_list_id` elegido es el que viaja en la línea. Si `items` está vacío, la presentación no tiene precio vigente y no puede venderse ([Productos y precios §12](../principales/productos-y-precios.md#12-registrar-un-precio-manual-por-presentación)).

## 5. Método de pago

`GET https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE` → `items[].id` ([payment_method_id](../parametros/payment-method-id.md)). Permiso: `perm:payment-reference:global_payment_methods:read`.

## 6. Crear el borrador

`POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` ([Sales, operación 3](../servicios/sales.md#3-post-companiescompany_idsales)); permiso `perm:sales:sales:create`.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "observations": "Entrega en mostrador",
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "quantity": "2",
      "discount_amount": "0",
      "tax_amount": "0"
    }
  ]
}
```

Respuesta `201` (`SaleResponse`; valores ilustrativos): `id` es el [sale_id](../parametros/sale-id.md); `lines[].unit_price`, `price_list_id` y `price_list_item_id` muestran el precio que Sales resolvió en Commercial Relationship para la lista elegida; `price_list_requested: true` registra que la lista fue pedida por el vendedor.

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Entrega en mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "has_unknown_cost": false,
  "inventory_operation_id": null,
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": true,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2",
      "base_quantity": "2.0000",
      "unit_price": "800.00",
      "discount_amount": "0",
      "tax_amount": "0",
      "subtotal": "1600.00",
      "total": "1600.00",
      "unit_cost_snapshot": "500.00",
      "cost_total": null,
      "cost_known": true,
      "gross_margin_amount": "600.00",
      "gross_margin_percentage": "37.50",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

Errores: `409 SALES.REFERENCES_NOT_ELIGIBLE` con `errors[]` (`PRICE_LIST_NOT_APPLICABLE`: la lista no está vigente o es de otra moneda; `NO_PRICE_IN_LIST`: la lista no tiene precio para la presentación; cliente o presentación no elegibles), `422 UNIT_PRICE_NOT_ALLOWED` si se envió `unit_price`, `403 BRANCH_ACCESS_DENIED` si el vendedor no tiene asignada la sucursal.

## 7. Ajustar líneas

Cada línea nueva repite los pasos 3 y 4 (buscar producto, elegir lista) y se envía con la `version` actual de la venta:

- Agregar: `POST …/sales/{sale_id}/details` ([operación 7](../servicios/sales.md#7-post-companiescompany_idsalessale_iddetails)):

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "quantity": "2",
  "discount_amount": "0",
  "tax_amount": "0",
  "version": 1
}
```

- Modificar (también para cambiar de lista): `PUT …/sales/{sale_id}/details/{detail_id}` con el mismo cuerpo completo ([operación 9](../servicios/sales.md#9-put-companiescompany_idsalessale_iddetailsdetail_id)).
- Eliminar: `DELETE …/sales/{sale_id}/details/{detail_id}?version=n` ([operación 10](../servicios/sales.md#10-delete-companiescompany_idsalessale_iddetailsdetail_id)).

Cada respuesta `200` devuelve la venta completa con la nueva `version`; el frontend reemplaza su copia local.

## 8. Verificar disponibilidad (opcional)

`GET …/sales/{sale_id}/availability` ([operación 15](../servicios/sales.md#15-get-companiescompany_idsalessale_idavailability)): `all_available` y, por producto, `required_base_quantity`, `available_base_quantity`, `is_available`. Es informativo y no reserva; la verificación definitiva la hace Inventory al confirmar.

## 9. Confirmar

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 0b1c2d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e' \
  -H 'Content-Type: application/json' \
  -d '{"version": 2}'
```

([operación 11](../servicios/sales.md#11-post-companiescompany_idsalessale_idconfirmation)); permiso `perm:sales:sales:update`. `HIGH_RISK`: pedir confirmación al usuario. La `Idempotency-Key` es un UUID generado por el frontend y reutilizado en los reintentos.

Respuesta `200` con `status: "CONFIRMED"`, `number` (consecutivo de la secuencia de la sucursal o de la empresa), `sequence_value` e `inventory_operation_id` (la salida registrada en Inventory):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
  "number": "V-000123",
  "sequence_value": 123,
  "status": "CONFIRMED",
  "operation_date": "2026-10-19",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Entrega en mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "has_unknown_cost": false,
  "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": true,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2",
      "base_quantity": "2.0000",
      "unit_price": "800.00",
      "discount_amount": "0",
      "tax_amount": "0",
      "subtotal": "1600.00",
      "total": "1600.00",
      "unit_cost_snapshot": "500.00",
      "cost_total": null,
      "cost_known": true,
      "gross_margin_amount": "600.00",
      "gross_margin_percentage": "37.50",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

Manejo de errores habituales:

| Respuesta | Acción |
|---|---|
| `409 SALES.PRICES_CHANGED` | Algún precio de la lista elegida cambió desde que se guardó la línea. Recargar la venta (`GET …/sales/{sale_id}`), mostrar en `errors[]` el precio guardado y el vigente, volver a guardar las líneas afectadas (paso 7) y confirmar con la nueva `version` |
| `409 SALES.INSUFFICIENT_STOCK` | Mostrar faltantes por producto; reducir cantidades |
| `422 SALES.SALE_WITHOUT_LINES` | La venta no tiene líneas |
| `409 SALES.SEQUENCE_NOT_CONFIGURED` | Un administrador debe crear la secuencia (`POST …/sale-sequences`, operación 16) |
| `409 SALES.VERSION_CONFLICT` | Recargar y repetir |
| `409 SALES.OPERATION_IN_PROGRESS` o `503` | Consultar `GET …/sales/{sale_id}/operations` (operación 13); repetir con la **misma** `Idempotency-Key` |

## 10. Anular (si hace falta)

`POST …/sales/{sale_id}/cancellation` con `Idempotency-Key`, `{"version": n, "reason": "…"}` ([operación 12](../servicios/sales.md#12-post-companiescompany_idsalessale_idcancellation)); permiso `perm:sales:sales:delete`. Si estaba confirmada, revierte la salida de inventario y conserva el número.

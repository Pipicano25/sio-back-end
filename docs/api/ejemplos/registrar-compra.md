# Registrar, confirmar y recibir una compra

[← Flujos](README.md) · [← Índice](../index.md) · Ficha: [Purchase](../servicios/purchase.md)

Flujo de compras del MVP: compra de contado, confirmación (numera, no mueve inventario) y recepción completa (ingresa la mercancía). Perfil típico: grupo `compras`.

## 1. Contexto operativo

`GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` → [company_id](../parametros/company-id.md) y [branch_id](../parametros/branch-id.md) receptora.

## 2. Proveedor

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers?status=ACTIVE` → `items[].id` ([company_supplier_id](../parametros/supplier-id.md)). Opcional: sus productos (`GET …/supplier-products?company_supplier_id=…`, con `id` = `supplier_product_id`) y condiciones de pago de contado (`GET …/supplier-payment-conditions?company_supplier_id=…`).

## 3. Productos y presentaciones comprables

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products?is_purchasable=true&status=ACTIVE` → [company_product_id](../parametros/company-product-id.md); y `GET …/company-product-presentations?company_product_id=…&is_purchasable=true` → [company_product_presentation_id](../parametros/company-product-presentation-id.md) (preferir `is_default_purchase`). Comprobar que el producto tenga `purchase_tax_percentage` configurado; si es `null`, la confirmación fallará con `409 PURCHASE_TAX_NOT_CONFIGURED` (lo configura un administrador con [Commercial Relationship, operación 11](../servicios/commercial-relationship.md#11-put-company-productscompany_product_idpurchase-tax)).

## 4. Método de pago

`GET https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE` → [payment_method_id](../parametros/payment-method-id.md).

## 5. Crear el borrador

`POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` ([Purchase, operación 3](../servicios/purchase.md#3-post-companiescompany_idpurchases)); permiso `perm:purchase:purchases:create`.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "operation_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "supplier_document_number": "FV-8891",
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "quantity": "10",
      "unit_cost": "50000.00"
    }
  ]
}
```

`unit_cost` es por presentación; el impuesto lo calcula el servidor con la tasa del producto (`tax_percentage` solo con `perm:purchase:purchase_line_taxes:override`). Respuesta `201` con `id` (`purchase_id`), `version`, `status: "DRAFT"`.

## 6. Ajustar líneas (opcional)

`POST …/purchases/{purchase_id}/details`, `PUT …/details/{detail_id}`, `DELETE …/details/{detail_id}?version=n` (operaciones 7, 9 y 10). Una presentación solo puede aparecer en una línea.

## 7. Confirmar

`POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation` con `Idempotency-Key` y `{"version": n}` ([operación 11](../servicios/purchase.md#11-post-companiescompany_idpurchasespurchase_idconfirmation)); permiso `perm:purchase:purchases:update`. Asigna `number`, congela los datos y deja `receipt_status: "PENDING"`. **No mueve inventario.**

| Respuesta | Acción |
|---|---|
| `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` / `PURCHASE_TAX_CHANGED` | Configurar la tasa del producto o volver a guardar la línea |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` | Un administrador debe crear la política de ganancia en Commercial Relationship (operaciones 61–70) |
| `409 PURCHASE.SEQUENCE_NOT_CONFIGURED` | Crear la secuencia de compras (operaciones 18–23) |

## 8. Registrar hitos logísticos (opcional)

`POST …/purchases/{purchase_id}/lifecycle-events` con `event_type` (`ORDERED`, `SUPPLIER_DISPATCHED`, `ARRIVED`…), `occurred_at` y `source` ([operación 16](../servicios/purchase.md#16-post-companiescompany_idpurchasespurchase_idlifecycle-events)). La línea de tiempo se consulta con la operación 17.

## 9. Recibir la mercancía

Cuando llega **toda** la compra: `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt` con `Idempotency-Key` y `{"version": n, "full_receipt_confirmed": true}` ([operación 12](../servicios/purchase.md#12-post-companiescompany_idpurchasespurchase_idreceipt)); permiso `perm:purchase:purchases:update`. `HIGH_RISK`: ingresa las cantidades en Inventory y abre capas de costo FIFO; además envía los costos a Commercial Relationship para la actualización automática de precios.

Respuesta `200` con `receipt_status: "RECEIVED"`, `received_at`, `inventory_operation_id`. Si Inventory no responde (`503` con `operation_id`), repetir con la misma `Idempotency-Key` o consultar `GET …/purchases/{purchase_id}/operations`.

## 10. Anular (si hace falta)

`POST …/purchases/{purchase_id}/cancellation` con `Idempotency-Key`, `{"version": n, "reason": "…"}` ([operación 13](../servicios/purchase.md#13-post-companiescompany_idpurchasespurchase_idcancellation)); permiso `perm:purchase:purchases:delete`. Si ya estaba recibida, revierte la entrada de inventario (`409 INVENTORY_ALREADY_CONSUMED` si la mercancía ya salió).

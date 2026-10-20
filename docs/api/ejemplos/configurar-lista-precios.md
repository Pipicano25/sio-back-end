# Configurar una lista de precios con política de ganancia

[← Flujos](README.md) · [← Índice](../index.md) · Ficha: [Commercial Relationship](../servicios/commercial-relationship.md) · Módulo: [Productos y precios](../principales/productos-y-precios.md)

Cómo una empresa crea su lista de precios, define un porcentaje de ganancia sobre el costo de compra, asocia las presentaciones y obtiene precios actualizados automáticamente cuando recibe mercancía. Perfil típico: grupos `administradores` o `supervisores`. Identificadores ficticios; cuerpos y respuestas según los modelos reales.

**Conceptos verificados en el código de Commercial Relationship:**

- El **porcentaje de la política es un recargo sobre el costo** de compra recibido: `precio = costo_de_referencia × (1 + porcentaje / 100)`, redondeado a los decimales de la moneda. El costo de referencia es el costo unitario de la compra; si el costo bajó respecto al anterior, se usa el promedio de ambos.
- **Cambiar el porcentaje no recalcula** los precios existentes: abre un término nuevo y se aplica en la siguiente recepción de compra.
- La actualización automática ocurre **después de la recepción** de la compra (no al confirmarla) y la ejecuta un proceso interno de Commercial Relationship; es asíncrona y su resultado se consulta en las aplicaciones automáticas.
- Una presentación puede estar en **una sola política por lista**. Una lista tiene una moneda inmutable y vigencia opcional; solo una lista puede ser predeterminada por moneda.

## 1. Contexto operativo

`GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` → [company_id](../parametros/company-id.md). Permiso: `perm:operational-context:application_users:read`.

## 2. Crear la lista de precios

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` ([operación 47](../servicios/commercial-relationship.md#47-post-companiescompany_idprice-lists)); permiso `perm:commercial-relationship:price_lists:create`.

```json
{
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "currency_code": "COP",
  "description": "Descripción ilustrativa",
  "valid_from": "2026-10-01T00:00:00Z",
  "is_default": true
}
```

Respuesta `201` (`PriceListResponse`; `id` es el [price_list_id](../parametros/price-list-id.md)):

```json
{
  "id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "description": "Descripción ilustrativa",
  "currency_code": "COP",
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

Vigencias: la lista aplica desde `valid_from` (o desde siempre si es `null`) hasta `valid_to` exclusivo (o sin fin si es `null`), siempre que `status` sea `ACTIVE`. Con `is_default: true` pasa a ser la lista predeterminada de su moneda (la usan Product Inventory Query y Sales cuando no se indica otra) y la anterior pierde la marca. Errores: `409 DUPLICATE_PRICE_LIST_CODE`, `422` si `valid_to` no es posterior a `valid_from`.

## 3. Identificar las presentaciones que tendrán precio

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations?status=ACTIVE&is_sellable=true` ([operación 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations)); permiso `perm:commercial-relationship:company_product_presentations:read`. Tomar `items[].id` ([company_product_presentation_id](../parametros/company-product-presentation-id.md)) y `company_product_id`. Si el producto o la presentación aún no están adoptados, ver [Productos y precios §5 y 7](../principales/productos-y-precios.md#5-adoptar-un-producto-global-en-la-empresa).

## 4. Crear la política de porcentaje de ganancia

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` ([operación 62](../servicios/commercial-relationship.md#62-post-companiescompany_idprice-listsprice_list_idpricing-policies)); permiso `perm:commercial-relationship:pricing_policies:create`.

```json
{
  "name": "Margen general 30 %",
  "markup_percentage": "30",
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
  ]
}
```

Respuesta `201` (`PricingPolicyResponse`; `id` es el [policy_id](../parametros/pricing-policy-id.md)):

```json
{
  "id": "e932921e-1005-42cc-8e58-e914441c5f98",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "name": "Margen general 30 %",
  "markup_percentage": "30",
  "presentation_count": 1,
  "deactivated_at": null,
  "deactivation_reason": null
}
```

`markup_percentage: "30"` significa que el precio será el costo recibido más un 30 %. La política nace con el término vigente desde ahora (`GET …/pricing-policies/{policy_id}/terms`, operación 65). Errores: `409 POLICY_NAME_DUPLICATE`, `409 PRESENTATION_ALREADY_IN_POLICY` (la presentación ya está en otra política de la misma lista), `409 PRICE_LIST_INACTIVE`, `422 PRESENTATION_NOT_SELLABLE`.

## 5. Asociar más presentaciones (opcional)

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations` ([operación 67](../servicios/commercial-relationship.md#67-post-pricing-policiespolicy_idpresentations)); permiso `perm:commercial-relationship:pricing_policies:update`.

```json
{
  "version": 1,
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
  ]
}
```

Respuesta `200` con la política y `presentation_count` actualizado. Para retirar: `…/presentations/remove` con el mismo cuerpo (operación 69). Para comprobar qué presentaciones de la empresa ya tienen política en alguna lista de la moneda: `POST …/companies/{company_id}/pricing-policies/coverage` (operación 60).

## 6. Registrar un precio inicial manual (opcional pero recomendable)

La política **no crea precios por sí sola**: el primer precio automático aparecerá tras la primera recepción de compra. Si la presentación debe venderse antes, registra un precio manual: `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` ([operación 53](../servicios/commercial-relationship.md#53-post-companiescompany_idprice-list-items)); permiso `perm:commercial-relationship:price_list_items:create`.

```json
{
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "unit_price": "800.00",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "valid_from": "2026-10-01T00:00:00Z"
}
```

Respuesta `201` (`PriceListItemResponse`, `origin: "MANUAL"`):

```json
{
  "id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
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
```

Vigencias del precio: `valid_from` (si se omite, el instante de creación) y `valid_to` opcional; los periodos de una misma lista y presentación no se solapan (`409 PRICE_PERIOD_OVERLAP`). Un precio está vigente cuando su lista está vigente, su `status` es `ACTIVE` y su periodo cubre el instante consultado.

## 7. Registrar y recibir una compra

Para que la política produzca precios hace falta una compra **confirmada y recibida** de la presentación, con `unit_cost` real. El flujo completo está en [Registrar una compra](registrar-compra.md); resumido:

1. `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` con la línea (`company_product_presentation_id`, `quantity`, `unit_cost: "500.00"`).
2. `POST …/purchases/{purchase_id}/confirmation` con `Idempotency-Key` y `{"version": n}`. La confirmación valida que la presentación tenga política en alguna lista vigente de la moneda (`409 PRICING_POLICY_NOT_CONFIGURED` si no) y que el impuesto de compra esté configurado.
3. `POST …/purchases/{purchase_id}/receipt` con `Idempotency-Key` y `{"version": n, "full_receipt_confirmed": true}`. La respuesta `200` trae `receipt_status: "RECEIVED"`. En ese momento Purchase envía a Commercial Relationship los costos recibidos (llamada interna, no del frontend).

## 8. Comprobar la aplicación automática y el precio actualizado

**8a. Aplicaciones automáticas de la compra:** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/automatic-price-applications?purchase_id={purchase_id}` ([operación 72](../servicios/commercial-relationship.md#72-get-companiescompany_idautomatic-price-applications)); permiso `perm:commercial-relationship:automatic_price_applications:read`. Respuesta `200`:

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "purchase_detail_id": "77cd1afa-2a02-454d-8b23-7a29331aab97",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "sequence": 1,
      "received_at": "2026-10-19T15:04:05Z",
      "received_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "policy_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
      "markup_percentage": "30",
      "current_unit_cost": "500.00",
      "previous_unit_cost": null,
      "reference_cost": "500.00",
      "previous_price": "800.00",
      "new_price": "650.00",
      "previous_price_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "new_price_item_id": "8b9c0d1e-2f3a-4b4c-9d5e-6f7a8b9c0d1e",
      "cancelled_future_item_ids": [
        "6c3a0e48-e654-4fd0-8983-0ba7e6d39921"
      ],
      "status": "APPLIED",
      "attempts": 1,
      "next_attempt_at": null,
      "last_error_code": null,
      "first_attempt_at": null,
      "completed_at": null,
      "resolved_by": null,
      "resolution_reason": null,
      "version": 1,
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

Lectura: con `markup_percentage: "30"` y `current_unit_cost: "500.00"`, el precio aplicado es `500.00 × 1.30 = 650.00`. `status: "APPLIED"` indica que se cerró el precio vigente y se creó uno nuevo (`new_price`, `new_price_item_id`, `origin: "AUTOMATIC"`); `UNCHANGED` que el precio ya era ese; `SKIPPED_NO_POLICY` o `SKIPPED_LIST_NOT_EFFECTIVE` que la política o la lista no aplicaban en ese momento; `PENDING` que el proceso interno aún no la procesó (vuelve a consultar en unos segundos); `FAILED` que reintentará.

**8b. Precio vigente de la presentación:** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items?price_list_id={price_list_id}&company_product_presentation_id={id}&status=ACTIVE&applicable_at=<ahora>` ([operación 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items)). El elemento devuelto es el precio que verá el vendedor en [Crear una venta §4](crear-venta.md#4-listar-las-opciones-de-precio-y-elegir-la-lista). También puede verse en Product Inventory Query con `product-overviews?price_list_id={price_list_id}`.

## 9. Cambiar el porcentaje más adelante

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/percentage` ([operación 68](../servicios/commercial-relationship.md#68-post-pricing-policiespolicy_idpercentage)); permiso `perm:commercial-relationship:pricing_policies:update`; `HIGH_RISK`.

```json
{
  "version": 1,
  "markup_percentage": "30"
}
```

Respuesta `200` con la política. El nuevo porcentaje queda como término vigente desde ahora, **sin recalcular** los precios actuales: se aplicará en la próxima recepción de compra de cada presentación. Si se necesita el precio nuevo de inmediato, cámbialo a mano con `POST …/price-list-items/{price_list_item_id}/change-price` (operación 56).

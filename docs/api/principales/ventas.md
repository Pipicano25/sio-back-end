# 6.6 Ventas

[← API principales](README.md) · [← Índice](../index.md)

El flujo de punto de venta: elegir cliente, buscar productos con existencias y precio, armar la venta en borrador eligiendo la lista de precios de cada línea, verificar disponibilidad, confirmar (numera el documento y descuenta inventario) y consultar lo vendido.

Servicios implicados: [Sales](../servicios/sales.md) (propietario de la venta), [Commercial Relationship](../servicios/commercial-relationship.md) (clientes, presentaciones, listas y precios), [Product Inventory Query](../servicios/product-inventory-query.md) (catálogo con precio y existencias), [Payment Reference](../servicios/payment-reference.md) (método de pago) e [Inventory](../servicios/inventory.md) (salida de existencias, invocada por Sales). Flujo completo con JSON: [Crear una venta](../ejemplos/crear-venta.md).

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar el cliente | `GET /api/v1/companies/{company_id}/company-customers` (CR) | `perm:commercial-relationship:company_customers:read` | [CR 13](../servicios/commercial-relationship.md#13-get-companiescompany_idcompany-customers) |
| 2 | Buscar productos con disponibilidad y precio | `GET /api/v1/companies/{company_id}/branches/{branch_id}/product-overviews` (PIQS) | `perm:product-inventory-query:product_overviews:read` | [PIQS 4](../servicios/product-inventory-query.md#4-get-companiescompany_idbranchesbranch_idproduct-overviews) |
| 3 | Consultar las listas de precios vigentes | `GET /api/v1/companies/{company_id}/price-lists` (CR) | `perm:commercial-relationship:price_lists:read` | [CR 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists) |
| 4 | Consultar los precios vigentes de una presentación | `GET /api/v1/companies/{company_id}/price-list-items` (CR) | `perm:commercial-relationship:price_list_items:read` | [CR 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items) |
| 5 | Elegir el método de pago | `GET /global-payment-methods` (Payment Reference) | `perm:payment-reference:global_payment_methods:read` | [PR 9](../servicios/payment-reference.md#9-get-global-payment-methods) |
| 6 | Crear la venta en borrador | `POST /api/v1/companies/{company_id}/sales` (Sales) | `perm:sales:sales:create` | [Sales 3](../servicios/sales.md#3-post-companiescompany_idsales) |
| 7 | Agregar una línea | `POST /api/v1/companies/{company_id}/sales/{sale_id}/details` (Sales) | `perm:sales:sale_details:create` | [Sales 7](../servicios/sales.md#7-post-companiescompany_idsalessale_iddetails) |
| 8 | Modificar una línea | `PUT /api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}` (Sales) | `perm:sales:sale_details:update` | [Sales 9](../servicios/sales.md#9-put-companiescompany_idsalessale_iddetailsdetail_id) |
| 9 | Eliminar una línea | `DELETE /api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}?version=` (Sales) | `perm:sales:sale_details:delete` | [Sales 10](../servicios/sales.md#10-delete-companiescompany_idsalessale_iddetailsdetail_id) |
| 10 | Consultar la venta con líneas y totales | `GET /api/v1/companies/{company_id}/sales/{sale_id}` (Sales) | `perm:sales:sales:read` | [Sales 5](../servicios/sales.md#5-get-companiescompany_idsalessale_id) |
| 11 | Verificar disponibilidad antes de confirmar | `GET /api/v1/companies/{company_id}/sales/{sale_id}/availability` (Sales) | `perm:sales:sales:read` | [Sales 15](../servicios/sales.md#15-get-companiescompany_idsalessale_idavailability) |
| 12 | Confirmar la venta | `POST /api/v1/companies/{company_id}/sales/{sale_id}/confirmation` (Sales) | `perm:sales:sales:update` | [Sales 11](../servicios/sales.md#11-post-companiescompany_idsalessale_idconfirmation) |
| 13 | Listar ventas | `GET /api/v1/companies/{company_id}/sales` (Sales) | `perm:sales:sales:read` | [Sales 4](../servicios/sales.md#4-get-companiescompany_idsales) |
| 14 | Anular una venta | `POST /api/v1/companies/{company_id}/sales/{sale_id}/cancellation` (Sales) | `perm:sales:sales:delete` | [Sales 12](../servicios/sales.md#12-post-companiescompany_idsalessale_idcancellation) |

Bases: Sales `https://sio-sales-dev.onrender.com/api/v1`; Commercial Relationship `https://sio-commercial-relationship-dev.onrender.com/api/v1`; Product Inventory Query `https://sio-product-inventory-query-dev.onrender.com/api/v1`; Payment Reference `https://sio-payment-reference-dev.onrender.com` (sin `/api/v1`).

Operaciones relacionadas que no se consideran principales: editar la cabecera del borrador (Sales 6), consultar las operaciones de confirmación y anulación (Sales 13, 14) y los agregados de ventas (Sales 22, 23; ver [Reportes](reportes.md)). Las secuencias de numeración (Sales 16–21) se documentan en [Administración empresarial](administracion-empresarial.md#numeración-de-documentos-comerciales).

**Alcance actual: ventas de contado.** El contrato de creación (`SaleCreateIn`) recibe únicamente `payment_method_id` y rechaza con `422` los campos `customer_payment_condition_id`, `payment_condition_code_snapshot`, `payment_terms_days_snapshot` y `due_date`; al confirmar, el servicio fija `payment_condition_code_snapshot: "CASH"` y `due_date` igual a `operation_date`. Las ventas a crédito son una funcionalidad **futura, no implementada** en Sales; esos campos y las condiciones de pago de clientes se conservan en las fichas como referencia técnica de los contratos existentes.

---

## Regla de precios aprobada para el frontend

1. Al agregar un producto, el frontend consulta los **precios vigentes de la presentación en todas las listas** (funcionalidad 4) y los nombres de las listas (funcionalidad 3).
2. Muestra las opciones **ordenadas de mayor a menor precio** y selecciona inicialmente la de **mayor precio**.
3. El vendedor elige la lista. El frontend envía **`price_list_id` de forma explícita** en cada línea (funcionalidades 6, 7 y 8).
4. El frontend **nunca envía `unit_price`**: el contrato de Sales lo rechaza con `422 UNIT_PRICE_NOT_ALLOWED`. Sales resuelve el precio en Commercial Relationship para la lista indicada, lo congela en la línea (`unit_price`, `price_list_item_id`, `price_source: "PRICE_LIST_ITEM"`) y lo vuelve a verificar al confirmar.

## Antes de empezar: configuración obligatoria

| Requisito | Dónde se configura | Qué pasa si falta |
|---|---|---|
| Sucursal asignada al vendedor | [Administración empresarial §12](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) | `403 BRANCH_ACCESS_DENIED` al crear la venta |
| Secuencia de numeración activa para la sucursal o la empresa | [Administración empresarial §18–21](administracion-empresarial.md#numeración-de-documentos-comerciales) (`POST …/sale-sequences`, Sales 16) | `409 SEQUENCE_NOT_CONFIGURED` al confirmar; se resuelve creando o reactivando la secuencia y repitiendo la confirmación |
| Cliente `ACTIVE` | [Gestión de clientes](gestion-de-clientes.md) | `409 REFERENCES_NOT_ELIGIBLE` |
| Presentación vendible con precio vigente en al menos una lista | [Productos y precios](productos-y-precios.md) | `409 REFERENCES_NOT_ELIGIBLE` (`NO_PRICE_IN_LIST`) |
| Método de pago activo | Payment Reference | `409 REFERENCES_NOT_ELIGIBLE` |
| Existencias en la sucursal (productos con control de inventario) | [Compras](compras.md) e [Inventario](inventario.md) | `409 INSUFFICIENT_STOCK` al confirmar |

Regla verificada en `sequence_repository.py`: Sales usa la secuencia activa de la **sucursal** y, si no hay, la de la **empresa** (`branch_id: null`).

## 1. Buscar el cliente

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers?search=<código o nombre>&status=ACTIVE` (permiso `perm:commercial-relationship:company_customers:read`). Responde `200`; el valor que necesita la venta es `items[].id` ([company_customer_id](../parametros/customer-id.md)). Detalle en [Gestión de clientes §4](gestion-de-clientes.md#4-buscar-y-listar-los-clientes-de-la-empresa).

## 2. Buscar productos con disponibilidad y precio

**¿Qué puede hacer el usuario?** Buscar por nombre, código interno, SKU o código de barras y ver, en una sola respuesta, las presentaciones vendibles, su precio en la lista elegida y las existencias de la sucursal.

**¿Qué API debe consumir el frontend?** `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews`. Permiso `perm:product-inventory-query:product_overviews:read` (más los permisos de lectura de precios y existencias que el servicio comprueba por detrás). Consulta: `search`, `internal_code`, `sku`, `barcode`, `identifier`, `brand_id[]`, `category_id[]` + `include_descendants`, `status`, `has_image`, `stock_state`, `price_list_id` (precio de esa lista; si se omite, el de la lista predeterminada de la moneda), `sort`, `page_size` (1–20), `cursor`.

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/product-overviews?search=acetaminofen&status=ACTIVE&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) y [branch_id](../parametros/branch-id.md) seleccionados.

**¿Cómo sabe que funcionó?** `200` con `items[]`: `company_product_id`, `display_name`, `internal_code`, `identifiers[]`, `presentations[]` (`company_product_presentation_id`, `code`, `name`, `sku`, `is_sellable`, `base_quantity_factor`, `price`) y `stock` (existencias de la sucursal; `null` si el producto no controla inventario o la fuente no respondió, en cuyo caso `partial: true` y `partial_reason`). Paginación por `cursor` y `has_next`. El `price` mostrado corresponde a **una** lista; las alternativas se obtienen con la funcionalidad 4.

## 3 y 4. Consultar las listas y los precios vigentes de una presentación

**¿Qué puede hacer el usuario?** Ver todas las opciones de precio de la presentación elegida (mostrador, mayorista, convenio) y escoger una.

**¿Qué API debe consumir el frontend?**

1. Listas vigentes (una vez por sesión y moneda): `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists?status=ACTIVE&currency_code=COP` (permiso `perm:commercial-relationship:price_lists:read`). Conserva `id`, `name`, `valid_from`, `valid_to`, `is_default`; descarta las que no estén vigentes ahora ([price_list_id](../parametros/price-list-id.md)).
2. Precios de la presentación: `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items?company_product_presentation_id=<id>&status=ACTIVE&applicable_at=<ahora en ISO 8601>` (permiso `perm:commercial-relationship:price_list_items:read`).

**¿Cómo sabe que funcionó?** `200` con `items[]`, un elemento por lista vigente con precio: `price_list_id`, `unit_price`, `currency_code`, `valid_from`, `valid_to`, `origin`. El frontend los ordena por `unit_price` descendente, les pone el `name` de la lista y preselecciona el primero. Si `items` llega vacío, la presentación no tiene precio vigente y no puede venderse hasta registrarlo ([Productos y precios §12](productos-y-precios.md#12-registrar-un-precio-manual-por-presentación)).

## 5. Elegir el método de pago

`GET https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE` (permiso `perm:payment-reference:global_payment_methods:read`). Responde `200` con `items[]` (`id`, `code`, `name`, `status`); el valor para la venta es `items[].id` ([payment_method_id](../parametros/payment-method-id.md)). Es un catálogo global: puede cargarse una vez por sesión.

## 6. Crear la venta en borrador

**¿Qué puede hacer el usuario?** Abrir una venta para un cliente en la sucursal actual, con o sin líneas iniciales.

**¿Qué API debe consumir el frontend?** `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales`. Permiso `perm:sales:sales:create`. Cuerpo `SaleCreateIn`:

| Campo | Obligatorio | Significado |
|---|---|---|
| `branch_id` | Sí | Sucursal de la venta ([branch_id](../parametros/branch-id.md)) |
| `company_customer_id` | Sí | Cliente ([customer-id](../parametros/customer-id.md)) |
| `payment_method_id` | Sí | Método de pago ([payment_method_id](../parametros/payment-method-id.md)) |
| `observations` | No | ≤ 2000 |
| `lines[]` | No | Líneas iniciales con la misma estructura de la funcionalidad 7 (sin `version`) |

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

**¿Qué necesita antes?** Los identificadores de las funcionalidades 1 a 5 y la sucursal asignada al vendedor.

**¿Cómo sabe que funcionó?** `201` con `SaleResponse`: `id` ([sale_id](../parametros/sale-id.md)), `status: "DRAFT"`, `number: null` (se asigna al confirmar), `version: 1`, instantáneas del cliente y del método de pago, totales (`subtotal`, `discount_total`, `tax_total`, `total`) y `lines[]` con el precio ya resuelto (`unit_price`, `price_list_id`, `price_list_item_id`, `price_source`). Errores: `403 BRANCH_ACCESS_DENIED`, `409 REFERENCES_NOT_ELIGIBLE` con `errors[]` por campo (`field`, `code`, `message`: cliente inactivo, presentación no vendible, `PRICE_LIST_NOT_APPLICABLE`, `NO_PRICE_IN_LIST`), `422 UNIT_PRICE_NOT_ALLOWED` si se envió `unit_price`, `422 VALIDATION_ERROR`, `503 DEPENDENCY_UNAVAILABLE`.

## 7, 8 y 9. Agregar, modificar y eliminar líneas

**¿Qué puede hacer el usuario?** Añadir productos a la venta, corregir cantidades, descuentos o la lista de precios de una línea, y quitar líneas, mientras la venta está en `DRAFT`.

**¿Qué API debe consumir el frontend?**

| Acción | Método y URL | Cuerpo / parámetros |
|---|---|---|
| Agregar | `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details` | `LineCreateIn`: `company_product_id`, `company_product_presentation_id`, `price_list_id`, `quantity`, `discount_amount` (por defecto `0`), `tax_amount` (por defecto `0`), `version` (de la venta) |
| Modificar | `PUT https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}` | El mismo `LineCreateIn` completo con la `version` actual de la venta |
| Eliminar | `DELETE https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}?version=<n>` | Sin cuerpo |

Permisos: `perm:sales:sale_details:create`, `…:update`, `…:delete`.

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

**¿Qué necesita antes?** El [sale_id](../parametros/sale-id.md) y la `version` actual de la venta; para modificar o eliminar, el `lines[].id` (`detail_id`) de la última lectura.

**¿Cómo sabe que funcionó?** Las tres responden `200` con la **venta completa** (`SaleResponse`) recalculada: nuevas `lines[]`, totales y `version` incrementada. El frontend reemplaza su copia local con esa respuesta. Errores: `409 VERSION_CONFLICT` (otro usuario cambió la venta: vuelve a leerla), `409 INVALID_STATUS` (ya no está en `DRAFT`), `409 REFERENCES_NOT_ELIGIBLE`, `404 NOT_FOUND` (venta o línea inexistente en la empresa).

## 10. Consultar la venta con líneas y totales

`GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}` (permiso `perm:sales:sales:read`). Responde `200` con `SaleResponse`: cabecera, `status`, `number`, totales, `version`, `inventory_operation_id` (tras confirmar) y `lines[]` con `line_number`, instantáneas del producto y la presentación, `quantity`, `base_quantity`, `unit_price`, `discount_amount`, `tax_amount`, `subtotal`, `total`, `unit_cost_snapshot` y margen (`gross_margin_amount`, `gross_margin_percentage`, `cost_known`). Solo las líneas: `GET …/sales/{sale_id}/details` (Sales 8).

## 11. Verificar disponibilidad antes de confirmar

**¿Qué puede hacer el usuario?** Saber si la sucursal tiene existencias para todas las líneas antes de intentar confirmar.

**¿Qué API debe consumir el frontend?** `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/availability` (permiso `perm:sales:sales:read`). No reserva existencias.

**¿Cómo sabe que funcionó?** `200` con `all_available` y `products[]` (`company_product_id`, `line_numbers[]`, `required_base_quantity`, `available_base_quantity`, `is_available`). Las cantidades se expresan en unidad base (cantidad × `base_quantity_factor`). Si Inventory no responde, `503 DEPENDENCY_UNAVAILABLE`.

## 12. Confirmar la venta

**¿Qué puede hacer el usuario?** Cerrar la venta: asignar el número de documento y descontar las existencias de la sucursal.

**¿Qué API debe consumir el frontend?** `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/confirmation`. Permiso `perm:sales:sales:update` (`HIGH_RISK`). Cabecera **`Idempotency-Key`** obligatoria (UUID generado por el frontend; el mismo valor en los reintentos). Cuerpo `{"version": n}`.

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 0b1c2d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e' \
  -H 'Content-Type: application/json' \
  -d '{"version": 3}'
```

**¿Qué necesita antes?** Venta en `DRAFT` con al menos una línea, la `version` actual, secuencia configurada y existencias suficientes.

**¿Cómo sabe que funcionó?** `200` con `SaleResponse` en `status: "CONFIRMED"`, `number` asignado (por ejemplo `V-000123`), `sequence_value`, `inventory_operation_id` (la salida registrada en Inventory) y `version` incrementada. Reglas verificadas en `confirmation_service.py`: Sales vuelve a resolver los precios y, si alguno cambió desde que se agregó la línea, responde `409 PRICES_CHANGED` con `errors[]` (precio, lista o ítem guardado frente al vigente) **sin confirmar**; el frontend debe mostrar el cambio, releer la venta y, si el vendedor acepta, volver a guardar las líneas afectadas y reintentar. Otros errores: `422 SALE_WITHOUT_LINES`, `409 SEQUENCE_NOT_CONFIGURED` / `SEQUENCE_EXHAUSTED`, `409 INSUFFICIENT_STOCK` (con el detalle por producto), `409 VERSION_CONFLICT`, `409 INVALID_STATUS`, `409 OPERATION_IN_PROGRESS` (hay una confirmación en curso: reintenta con la misma `Idempotency-Key`), `409 IDEMPOTENCY_KEY_CONFLICT` (misma clave con otro cuerpo), `503 DEPENDENCY_UNAVAILABLE`. Si Inventory no responde durante la confirmación, la operación queda `PENDING` y se concilia después: consulta `GET …/sales/{sale_id}/operations` (Sales 13) hasta ver `SUCCEEDED` o `FAILED`.

## 13. Listar ventas

`GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` (permiso `perm:sales:sales:read`). Consulta: `status` (`DRAFT`, `CONFIRMED`, `CANCELLED`), `branch_id`, `company_customer_id`, `operation_date_from`, `operation_date_to`, `number`, `page`, `page_size`. Responde `200` con `PaginatedResponse[SaleResponse]` (sin líneas en cada elemento: para verlas usa la funcionalidad 10). Detalle en [sale_id](../parametros/sale-id.md).

## 14. Anular una venta

**¿Qué puede hacer el usuario?** Dejar sin efecto una venta, en borrador o ya confirmada, indicando el motivo. Si estaba confirmada, la mercancía vuelve al inventario de la sucursal.

**¿Qué API debe consumir el frontend?** `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/cancellation`. Permiso `perm:sales:sales:delete`. Clasificación **`HIGH_RISK`**: pedir confirmación al usuario. Cabecera **`Idempotency-Key`** obligatoria (1–150 caracteres ASCII, generada por el frontend y reutilizada en los reintentos). Cuerpo `CancelIn`:

```json
{
  "version": 4,
  "reason": "Cliente desistió de la compra"
}
```

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/cancellation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 2d3e4f5a-6b7c-4d8e-9f0a-1b2c3d4e5f6a' \
  -H 'Content-Type: application/json' \
  -d '{"version": 4, "reason": "Cliente desistió de la compra"}'
```

**¿Qué necesita antes?** El [sale_id](../parametros/sale-id.md), su `version` actual, la sucursal asignada al usuario y un motivo no vacío. Estados permitidos (verificados en `cancellation_service.py`): `DRAFT` y `CONFIRMED`; una venta `CANCELLED` responde `409 INVALID_STATUS`.

**¿Cómo sabe que funcionó?** `200` con `SaleResponse` en `status: "CANCELLED"`, `cancelled_at`, `cancelled_by_user_id` y `cancellation_reason`; el `number` se conserva. Efectos sobre Inventory:

- Venta en `DRAFT`: se anula en una transacción local, sin tocar Inventory.
- Venta `CONFIRMED`: Sales abre una operación `CANCEL` (`PENDING`) y pide a Inventory el **reverso exacto** de la salida `inventory_operation_id`; cuando el reverso se aplica, la venta pasa a `CANCELLED` y la operación a `SUCCEEDED` con el `inventory_operation_id` del reverso (en el kardex aparece como `OUTPUT_REVERSAL`, `origin_type: SALE`). Si el reverso falla, la operación queda `FAILED` y la venta **sigue `CONFIRMED`**.
- La anulación no revalida cliente ni productos: funciona aunque estén inactivos.

Errores: `422 REASON_REQUIRED`, `422 IDEMPOTENCY_KEY_REQUIRED`, `409 IDEMPOTENCY_KEY_CONFLICT` (misma clave con otro cuerpo), `409 VERSION_CONFLICT`, `409 INVALID_STATUS`, `409 OPERATION_IN_PROGRESS` (otra confirmación o anulación en curso: reintenta con la misma clave), `409 INVENTORY_REJECTED` (Inventory rechazó el reverso, por ejemplo `ALREADY_REVERSED` o `REVERSAL_NOT_ALLOWED`; el detalle llega en `errors[]`), `403 BRANCH_ACCESS_DENIED`, `404`, `503 DEPENDENCY_UNAVAILABLE` (la operación queda `PENDING` y se concilia; consulta `GET …/sales/{sale_id}/operations`, Sales 13). La anulación queda registrada en Audit como `CANCEL_SALE` ([Administración empresarial §17](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto)).

## Dependencias con otros módulos

- [Gestión de clientes](gestion-de-clientes.md): el cliente de la venta.
- [Productos y precios](productos-y-precios.md): presentaciones vendibles, listas vigentes y precios; sin precio vigente no hay venta.
- [Inventario](inventario.md): la disponibilidad consultada, la salida registrada al confirmar y el reverso al anular (`inventory_operation_id`; kardex con `origin_type=SALE`).
- [Administración empresarial](administracion-empresarial.md): asignación del vendedor a la sucursal y secuencias de numeración.
- [Reportes](reportes.md): productos más vendidos y ventas por sucursal se calculan sobre las ventas `CONFIRMED`.

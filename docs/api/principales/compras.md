# 6.7 Compras

[← API principales](README.md) · [← Índice](../index.md)

El flujo de abastecimiento: elegir proveedor, armar la compra en borrador con productos, cantidades y costos, revisar impuestos y totales, confirmar (numera el documento) y registrar la recepción física completa (ingresa al inventario y dispara la actualización automática de precios).

Servicios implicados: [Purchase](../servicios/purchase.md) (propietario de la compra), [Commercial Relationship](../servicios/commercial-relationship.md) (proveedores, presentaciones, impuesto de compra, políticas de ganancia), [Payment Reference](../servicios/payment-reference.md) (método de pago) e [Inventory](../servicios/inventory.md) (entrada de existencias, invocada por Purchase). Flujo completo con JSON: [Registrar una compra](../ejemplos/registrar-compra.md).

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar el proveedor | `GET /api/v1/companies/{company_id}/company-suppliers` (CR) | `perm:commercial-relationship:company_suppliers:read` | [CR 19](../servicios/commercial-relationship.md#19-get-companiescompany_idcompany-suppliers) |
| 2 | Buscar productos y presentaciones comprables | `GET /api/v1/companies/{company_id}/company-product-presentations` (CR) | `perm:commercial-relationship:company_product_presentations:read` | [CR 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations) |
| 3 | Verificar la cobertura de políticas de ganancia | `POST /api/v1/companies/{company_id}/pricing-policies/coverage` (CR) | `perm:commercial-relationship:pricing_policy_coverage:read` | [CR 60](../servicios/commercial-relationship.md#60-post-companiescompany_idpricing-policiescoverage) |
| 4 | Crear la compra en borrador | `POST /api/v1/companies/{company_id}/purchases` (Purchase) | `perm:purchase:purchases:create` | [Purchase 3](../servicios/purchase.md#3-post-companiescompany_idpurchases) |
| 5 | Agregar una línea con cantidad y costo | `POST /api/v1/companies/{company_id}/purchases/{purchase_id}/details` (Purchase) | `perm:purchase:purchase_details:create` | [Purchase 7](../servicios/purchase.md#7-post-companiescompany_idpurchasespurchase_iddetails) |
| 6 | Modificar una línea | `PUT /api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}` (Purchase) | `perm:purchase:purchase_details:update` | [Purchase 9](../servicios/purchase.md#9-put-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 7 | Eliminar una línea | `DELETE /api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}?version=` (Purchase) | `perm:purchase:purchase_details:delete` | [Purchase 10](../servicios/purchase.md#10-delete-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 8 | Consultar la compra con impuestos y totales | `GET /api/v1/companies/{company_id}/purchases/{purchase_id}` (Purchase) | `perm:purchase:purchases:read` | [Purchase 5](../servicios/purchase.md#5-get-companiescompany_idpurchasespurchase_id) |
| 9 | Confirmar la compra | `POST /api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation` (Purchase) | `perm:purchase:purchases:update` | [Purchase 11](../servicios/purchase.md#11-post-companiescompany_idpurchasespurchase_idconfirmation) |
| 10 | Registrar la recepción física completa | `POST /api/v1/companies/{company_id}/purchases/{purchase_id}/receipt` (Purchase) | `perm:purchase:purchases:update` | [Purchase 12](../servicios/purchase.md#12-post-companiescompany_idpurchasespurchase_idreceipt) |
| 11 | Consultar el estado de las operaciones | `GET /api/v1/companies/{company_id}/purchases/{purchase_id}/operations` (Purchase) | `perm:purchase:purchase_operations:read` | [Purchase 14](../servicios/purchase.md#14-get-companiescompany_idpurchasespurchase_idoperations) |
| 12 | Listar compras | `GET /api/v1/companies/{company_id}/purchases` (Purchase) | `perm:purchase:purchases:read` | [Purchase 4](../servicios/purchase.md#4-get-companiescompany_idpurchases) |
| 13 | Anular una compra | `POST /api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation` (Purchase) | `perm:purchase:purchases:delete` | [Purchase 13](../servicios/purchase.md#13-post-companiescompany_idpurchasespurchase_idcancellation) |

Bases: Purchase `https://sio-purchase-dev.onrender.com/api/v1`; Commercial Relationship `https://sio-commercial-relationship-dev.onrender.com/api/v1`.

Operaciones relacionadas que no se consideran principales: editar la cabecera (Purchase 6), hitos logísticos `ORDERED`/`SUPPLIER_DISPATCHED`/`ARRIVED`/… (Purchase 16, 17) y el reporte de compras del período (Purchase 24; ver [Reportes](reportes.md)). Las secuencias de numeración (Purchase 18–23) se documentan en [Administración empresarial](administracion-empresarial.md#numeración-de-documentos-comerciales).

---

## Reglas verificadas que el frontend debe reflejar

- **Confirmar no mueve inventario.** La confirmación numera la compra (`status: CONFIRMED`, `receipt_status: PENDING`) y congela líneas y totales. Las existencias entran con la **recepción**.
- **Recepción completa o nada.** No existen recepciones parciales: el único cuerpo aceptado es `{"version": n, "full_receipt_confirmed": true}` con cabecera `Idempotency-Key`. La recepción registra la entrada en Inventory (`inventory_operation_id`) y deja `receipt_status: RECEIVED`.
- **Impuesto por línea.** Cada línea toma `purchase_tax_percentage` del producto empresarial (`tax_percentage_source: PRODUCT_DEFAULT`) salvo que envíe `tax_percentage` propio (`LINE_OVERRIDE`; requiere `perm:purchase:purchase_line_taxes:override`). Si ninguno existe, la confirmación falla con `409 PURCHASE_TAX_NOT_CONFIGURED`.
- **Política de ganancia obligatoria.** Al confirmar, Purchase valida que cada presentación tenga una política aplicable en alguna lista vigente de la moneda de la compra, **aunque el porcentaje sea `0`**; si no, `409 PRICING_POLICY_NOT_CONFIGURED`.
- **El costo lo escribe el comprador.** `unit_cost` es obligatorio en cada línea; `supplier_product_id` es opcional y solo valida coherencia con el proveedor.
- **Precios automáticos.** Tras la recepción, Purchase envía a Commercial Relationship (llamada interna, no del frontend) los costos recibidos; el *worker* de precios crea los precios `AUTOMATIC` según las políticas. El resultado se consulta en [Productos y precios §20](productos-y-precios.md#20-verificar-cobertura-y-ver-precios-automáticos-aplicados).

## Antes de empezar: configuración obligatoria

| Requisito | Dónde se configura | Qué pasa si falta |
|---|---|---|
| Sucursal asignada al comprador | [Administración empresarial §12](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) | `403 BRANCH_ACCESS_DENIED` |
| Secuencia de numeración activa (sucursal o empresa) | [Administración empresarial §18–21](administracion-empresarial.md#numeración-de-documentos-comerciales) (`POST …/purchase-sequences`, Purchase 18) | `409 SEQUENCE_NOT_CONFIGURED` al confirmar; se resuelve creando o reactivando la secuencia y repitiendo la confirmación |
| Proveedor `ACTIVE` | [Gestión de proveedores](gestion-de-proveedores.md) | `409 REFERENCES_NOT_ELIGIBLE` |
| Productos y presentaciones comprables (`is_purchasable`) | [Productos y precios §5 y 7](productos-y-precios.md#5-adoptar-un-producto-global-en-la-empresa) | `409 REFERENCES_NOT_ELIGIBLE` |
| Impuesto de compra por producto (o `tax_percentage` en la línea) | [Productos y precios §8](productos-y-precios.md#8-configurar-el-impuesto-de-compra-del-producto) | `409 PURCHASE_TAX_NOT_CONFIGURED` |
| Política de ganancia por presentación en una lista vigente | [Productos y precios §16](productos-y-precios.md#16-crear-una-política-de-porcentaje-de-ganancia) | `409 PRICING_POLICY_NOT_CONFIGURED` |
| Método de pago activo | Payment Reference ([payment_method_id](../parametros/payment-method-id.md)) | `409 REFERENCES_NOT_ELIGIBLE` |

## 1. Buscar el proveedor

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers?search=<código o nombre>&status=ACTIVE` (permiso `perm:commercial-relationship:company_suppliers:read`). El valor para la compra es `items[].id` ([company_supplier_id](../parametros/supplier-id.md)). Condiciones de pago del proveedor (opcional): `GET …/companies/{company_id}/supplier-payment-conditions?company_supplier_id=…`. Productos que suministra (opcional, para sugerir líneas y costos negociados): `GET …/companies/{company_id}/supplier-products?company_supplier_id=…`.

## 2. Buscar productos y presentaciones comprables

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations?search=<texto>&status=ACTIVE&is_purchasable=true` (permiso `perm:commercial-relationship:company_product_presentations:read`; también `company_product_id=` para ver las presentaciones de un producto). Responde `200` con `items[]`: `id` ([company_product_presentation_id](../parametros/company-product-presentation-id.md)), `company_product_id`, `code`, `name`, `base_quantity_factor`, `is_purchasable`, `is_default_purchase`. El impuesto por defecto del producto se ve en `GET …/company-products/{company_product_id}` (`purchase_tax_percentage`).

## 3. Verificar la cobertura de políticas de ganancia

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage` (permiso `perm:commercial-relationship:pricing_policy_coverage:read`) con `{"currency_code": "COP", "company_product_presentation_ids": ["…"]}`. Responde `200` con `items[]` (`covered`, `price_list_ids[]`). Hazlo al agregar líneas o antes de confirmar: una presentación con `covered: false` impedirá la confirmación hasta que se cree o complete una política ([Productos y precios §16 y 18](productos-y-precios.md#16-crear-una-política-de-porcentaje-de-ganancia)).

## 4. Crear la compra en borrador

**¿Qué API debe consumir el frontend?** `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases`. Permiso `perm:purchase:purchases:create`. Cuerpo `PurchaseCreateIn`:

| Campo | Obligatorio | Significado |
|---|---|---|
| `branch_id` | Sí | Sucursal que recibirá la mercancía ([branch_id](../parametros/branch-id.md)) |
| `company_supplier_id` | Sí | Proveedor ([supplier-id](../parametros/supplier-id.md)) |
| `operation_date` | Sí | Fecha de la compra (`YYYY-MM-DD`) |
| `payment_method_id` | Sí | Método de pago ([payment_method_id](../parametros/payment-method-id.md)) |
| `supplier_payment_condition_id` | No | Condición de pago del mismo proveedor |
| `promised_delivery_at` | No | Fecha y hora prometida (ISO 8601) |
| `supplier_document_number` | No | Número de la factura o remisión del proveedor (≤ 100) |
| `observations` | No | ≤ 2000 |
| `lines[]` | No | Líneas iniciales con la estructura de la funcionalidad 5 (sin `version`) |

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "operation_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "supplier_document_number": "FV-55012",
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "quantity": "10",
      "unit_cost": "500.00",
      "discount_amount": "0"
    }
  ]
}
```

**¿Cómo sabe que funcionó?** `201` con `PurchaseResponse`: `id` ([purchase_id](../parametros/purchase-id.md)), `status: "DRAFT"`, `receipt_status: null`, `number: null`, `version: 1`, instantáneas del proveedor y del método de pago, `due_date`, totales y `lines[]` con `tax_percentage`, `tax_percentage_source`, `tax_amount`, `subtotal`, `total`, `base_quantity`, `inventory_unit_cost` y `warnings[]`. Errores: `403 BRANCH_ACCESS_DENIED`, `409 REFERENCES_NOT_ELIGIBLE` (`SUPPLIER_NOT_ELIGIBLE`, `PAYMENT_CONDITION_OF_OTHER_SUPPLIER`, presentación no comprable, `SUPPLIER_PRODUCT_MISMATCH`), `409 DUPLICATE_PRESENTATION_IN_PURCHASE` (la misma presentación dos veces), `422 VALIDATION_ERROR`.

## 5, 6 y 7. Agregar, modificar y eliminar líneas

| Acción | Método y URL | Cuerpo / parámetros |
|---|---|---|
| Agregar | `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details` | `LineCreateIn`: `company_product_id`, `company_product_presentation_id`, `quantity`, `unit_cost` (obligatorios), `supplier_product_id`, `discount_amount` (por defecto `0`), `tax_percentage` (sobrescribe el del producto; exige el permiso explícito `perm:purchase:purchase_line_taxes:override`, que el grupo `compras` no tiene), `version` |
| Modificar | `PUT https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}` | El mismo `LineCreateIn` completo con la `version` actual |
| Eliminar | `DELETE https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}?version=<n>` | Sin cuerpo |

Permisos: `perm:purchase:purchase_details:create`, `…:update`, `…:delete`.

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "quantity": "10",
  "unit_cost": "500.00",
  "discount_amount": "0",
  "tax_percentage": "19",
  "version": 1
}
```

**¿Cómo sabe que funcionó?** `200` con la **compra completa** recalculada (`lines[]`, `subtotal`, `tax_total`, `total`, `version`). El frontend reemplaza su copia local. Errores: `409 VERSION_CONFLICT`, `409 INVALID_STATUS` (ya no está en `DRAFT`), `409 DUPLICATE_PRESENTATION_IN_PURCHASE`, `409 REFERENCES_NOT_ELIGIBLE`, `404 NOT_FOUND`.

## 8. Consultar la compra con impuestos y totales

`GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}` (permiso `perm:purchase:purchases:read`). Responde `200` con `PurchaseResponse` completo: `status`, `receipt_status`, `number`, `due_date`, `subtotal`, `discount_total`, `tax_total`, `total`, `inventory_operation_id`, `received_at`, `version` y `lines[]` (cada una con `unit_cost`, `tax_percentage`, `tax_percentage_source`, `tax_amount`, `total`, `base_quantity`, `inventory_unit_cost`). Solo las líneas: `GET …/purchases/{purchase_id}/details` (Purchase 8).

## 9. Confirmar la compra

**¿Qué puede hacer el usuario?** Cerrar el pedido al proveedor: asignar número de documento y congelar líneas y totales. **No ingresa mercancía.**

**¿Qué API debe consumir el frontend?** `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation`. Permiso `perm:purchase:purchases:update` (`HIGH_RISK`). Cabecera **`Idempotency-Key`** obligatoria. Cuerpo `{"version": n}`.

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 1c2d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f' \
  -H 'Content-Type: application/json' \
  -d '{"version": 2}'
```

**¿Cómo sabe que funcionó?** `200` con `PurchaseResponse` en `status: "CONFIRMED"`, `number` asignado (por ejemplo `C-000045`), `receipt_status: "PENDING"`, `inventory_operation_id: null`. Errores verificados en `confirmation_service.py`: `422 PURCHASE_WITHOUT_LINES`, `409 PURCHASE_TAX_NOT_CONFIGURED` y `409 PRICING_POLICY_NOT_CONFIGURED` (ambos con `errors[]` que indican la línea o presentación), `409 PURCHASE_TAX_CHANGED` (el impuesto del producto cambió desde que se agregó la línea: vuelve a leer la compra y guarda la línea de nuevo), `409 SEQUENCE_NOT_CONFIGURED` / `SEQUENCE_EXHAUSTED`, `409 VERSION_CONFLICT`, `409 INVALID_STATUS`, `409 OPERATION_IN_PROGRESS`, `409 IDEMPOTENCY_KEY_CONFLICT`, `503 DEPENDENCY_UNAVAILABLE`.

## 10. Registrar la recepción física completa

**¿Qué puede hacer el usuario?** Declarar que llegó toda la mercancía de la compra confirmada, para que entre al inventario de la sucursal y se actualicen los precios automáticos.

**¿Qué API debe consumir el frontend?** `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt`. Permiso `perm:purchase:purchases:update` (`HIGH_RISK`). Cabecera **`Idempotency-Key`** obligatoria. Cuerpo `ReceiptIn`:

```json
{
  "version": 3,
  "full_receipt_confirmed": true
}
```

`full_receipt_confirmed` debe ser `true`: es la declaración explícita de recepción total (no hay cantidades parciales).

**¿Qué necesita antes?** Compra en `status: CONFIRMED` con `receipt_status: PENDING`, la `version` actual y la sucursal asignada al usuario que recibe.

**¿Cómo sabe que funcionó?** `200` con `PurchaseResponse`: `receipt_status: "RECEIVED"`, `received_at`, `received_by_user_id` e `inventory_operation_id` (la entrada en Inventory, consultable con `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-operations/{operation_id}`). Después de esta respuesta: las existencias de la sucursal ya incluyen las cantidades en unidad base (`base_quantity` de cada línea) al costo `inventory_unit_cost`; y en segundos aparecen las aplicaciones automáticas de precio en Commercial Relationship. Errores: `409 PURCHASE_ALREADY_RECEIVED`, `409 INVALID_STATUS` (no está confirmada), `409 VERSION_CONFLICT`, `409 OPERATION_IN_PROGRESS`, `409 INVENTORY_REJECTED` (Inventory rechazó la entrada; ver `errors[]`), `503 DEPENDENCY_UNAVAILABLE` (la operación queda `PENDING` y se concilia; ver funcionalidad 11).

## 11. Consultar el estado de las operaciones

`GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/operations` (permiso `perm:purchase:purchase_operations:read`). Responde `200` con un arreglo de `PurchaseOperationResponse`: `operation_type` (`CONFIRM`, `RECEIVE`, `CANCEL`), `status` (`PENDING`, `SUCCEEDED`, `FAILED`), `error_code`, `error_details`, `inventory_operation_id`, `started_at`, `completed_at`. Úsalo cuando una confirmación o recepción respondió `503` o `OPERATION_IN_PROGRESS`, hasta que la operación termine; luego vuelve a leer la compra (funcionalidad 8). La línea de tiempo logística opcional (`ORDERED`, `ARRIVED`, …) está en `GET …/purchases/{purchase_id}/lifecycle-events` (Purchase 17).

## 12. Listar compras

`GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` (permiso `perm:purchase:purchases:read`). Consulta: `status`, `branch_id`, `company_supplier_id`, `operation_date_from`, `operation_date_to`, `number`, `page`, `page_size`. Responde `200` con `PaginatedResponse[PurchaseResponse]`; para la bandeja de "pendientes de recibir" filtra `status=CONFIRMED` y muestra `receipt_status`. Detalle en [purchase_id](../parametros/purchase-id.md).

## 13. Anular una compra

**¿Qué puede hacer el usuario?** Dejar sin efecto una compra en borrador, confirmada sin recibir o ya recibida, indicando el motivo. Si estaba recibida, la mercancía sale del inventario de la sucursal.

**¿Qué API debe consumir el frontend?** `POST https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation`. Permiso `perm:purchase:purchases:delete`. Clasificación **`HIGH_RISK`**: pedir confirmación al usuario. Cabecera **`Idempotency-Key`** obligatoria (1–150 caracteres ASCII). Cuerpo `CancelIn`:

```json
{
  "version": 5,
  "reason": "Pedido duplicado"
}
```

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/cancellation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 3e4f5a6b-7c8d-4e9f-8a0b-1c2d3e4f5a6b' \
  -H 'Content-Type: application/json' \
  -d '{"version": 5, "reason": "Pedido duplicado"}'
```

**¿Qué necesita antes?** El [purchase_id](../parametros/purchase-id.md), su `version` actual, la sucursal asignada al usuario y un motivo no vacío. Estados permitidos (verificados en `cancellation_service.py`): `DRAFT`, `CONFIRMED` con `receipt_status: PENDING` y `CONFIRMED` con `receipt_status: RECEIVED`; una compra `CANCELLED` responde `409 INVALID_STATUS`.

**¿Cómo sabe que funcionó?** `200` con `PurchaseResponse` en `status: "CANCELLED"`, `cancelled_at`, `cancelled_by_user_id` y `cancellation_reason`; el `number` y los datos de la recepción se conservan. Efectos sobre Inventory:

- `DRAFT` o `CONFIRMED` sin recibir: se anula en una transacción local, sin tocar Inventory (no había entrada).
- `CONFIRMED` y recibida: Purchase abre una operación `CANCEL` (`PENDING`) y pide a Inventory el **reverso exacto** de la entrada `inventory_operation_id`; cuando se aplica, la compra pasa a `CANCELLED` y la operación a `SUCCEEDED` (en el kardex aparece como `ENTRY_REVERSAL`, `origin_type: PURCHASE`). Si el reverso falla, la operación queda `FAILED` y la compra **sigue `CONFIRMED`**.
- **Reverso imposible:** si parte de la mercancía recibida ya se vendió o se ajustó (sus capas de costo FIFO fueron consumidas), Inventory rechaza el reverso (`ENTRY_LAYER_CONSUMED`) y Purchase responde `409 INVENTORY_ALREADY_CONSUMED`. La compra no puede anularse; la corrección debe hacerse con un ajuste de inventario ([Inventario §8](inventario.md#8-registrar-un-ajuste-manual)).
- La anulación no revalida proveedor ni productos.

Errores: `422 REASON_REQUIRED`, `422 IDEMPOTENCY_KEY_REQUIRED`, `409 IDEMPOTENCY_KEY_CONFLICT`, `409 VERSION_CONFLICT`, `409 INVALID_STATUS`, `409 OPERATION_IN_PROGRESS`, `409 INVENTORY_ALREADY_CONSUMED`, `409 INVENTORY_REJECTED` (otros rechazos de Inventory, por ejemplo `ALREADY_REVERSED`; detalle en `errors[]`), `403 BRANCH_ACCESS_DENIED`, `404`, `503 DEPENDENCY_UNAVAILABLE` (operación `PENDING`; consulta `GET …/purchases/{purchase_id}/operations`, funcionalidad 11). La anulación queda registrada en Audit como `CANCEL_PURCHASE` ([Administración empresarial §17](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto)). Los precios automáticos ya aplicados por la recepción **no** se revierten al anular.

## Dependencias con otros módulos

- [Gestión de proveedores](gestion-de-proveedores.md): proveedor activo, condiciones de pago y productos de proveedor.
- [Productos y precios](productos-y-precios.md): presentaciones comprables, impuesto de compra, políticas de ganancia; la recepción alimenta los precios automáticos.
- [Inventario](inventario.md): la recepción crea la entrada (`origin_type=PURCHASE` en el kardex) y las capas de costo FIFO; la anulación de una compra recibida las revierte si no se consumieron.
- [Administración empresarial](administracion-empresarial.md): asignación de sucursal y secuencias.
- [Reportes](reportes.md): compras del período por categoría.

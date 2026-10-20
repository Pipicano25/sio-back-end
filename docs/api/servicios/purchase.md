# Purchase API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Purchase registra las **compras a proveedores** de una empresa: se crean en borrador con sus líneas y costos, se **confirman** (lo que asigna el número consecutivo y congela los datos, sin mover inventario), se **reciben** (lo que ingresa la mercancía en Inventory) y pueden **anularse** (lo que revierte la entrada si ya se había recibido). También registra hitos logísticos, administra las secuencias de numeración y expone una consulta de compras del período para reportes.

## Responsabilidad

- Ciclo de vida: `DRAFT` → `CONFIRMED` (pendiente de recepción) → recibida (`receipt_status: RECEIVED`) → `CANCELLED` opcional en cualquiera de esos puntos.
- Validar referencias (proveedor, productos comprables, presentaciones, método de pago, condición de pago de contado) y congelar *snapshots* al confirmar.
- Calcular el impuesto de cada línea a partir de la **tasa de impuesto de compra del producto** (Commercial Relationship) o de una tasa ajustada con permiso especial.
- Coordinar con Inventory la entrada de mercancía y su reverso mediante operaciones idempotentes y reconciliables; tras cada recepción, informar los costos reales a Commercial Relationship para la actualización automática de precios.
- Compras del MVP: **solo de contado**, con recepción **completa** (sin recepciones parciales).

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-purchase-dev.onrender.com/api/v1` |
| Salud | `https://sio-purchase-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-purchase-dev.onrender.com/docs) · [/openapi.json](https://sio-purchase-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `PURCHASE.*` y `trace_id`; `400` usa `MALFORMED_BODY` |
| Operaciones en el contrato desplegado | 24 (22 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/purchase-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>` de un **usuario humano**: un token de cuenta de servicio recibe `403 PURCHASE.FORBIDDEN` en todas las rutas de negocio.

| Permiso | Operaciones | Grupos de la plantilla |
|---|---|---|
| `perm:purchase:purchases:create` | Crear compra | `administradores`, `supervisores`, `compras` |
| `perm:purchase:purchases:read` | Listar, consultar, reporte del período | `administradores`, `supervisores`, `compras`, `reportes`, `consulta` |
| `perm:purchase:purchases:update` | Editar cabecera, **confirmar**, **recibir** | `administradores`, `supervisores`, `compras` |
| `perm:purchase:purchases:delete` | **Anular** | `administradores`, `compras` |
| `perm:purchase:purchase_details:create` / `read` / `update` / `delete` | Líneas | `administradores`, `supervisores` (salvo `delete`), `compras`; lectura también `reportes` y `consulta` |
| `perm:purchase:purchase_line_taxes:override` | Enviar `tax_percentage` en una línea (tasa distinta de la del producto) | `administradores`, `supervisores` (permiso explícito; los comodines CRUD **no** lo cubren). El grupo `compras` **no** lo tiene |
| `perm:purchase:purchase_operations:read` | Operaciones de confirmación, recepción y anulación | `administradores`, `supervisores`, `compras`, `reportes`, `consulta` |
| `perm:purchase:purchase_lifecycle_events:create` / `read` | Hitos logísticos | `administradores`, `supervisores`, `compras`; lectura también `reportes` y `consulta` |
| `perm:purchase:purchase_sequences:create` / `read` / `update` | Secuencias | `administradores`, `supervisores`, `compras`; lectura también `reportes` y `consulta` |

## Alcance de datos

| Regla | Detalle |
|---|---|
| Empresa | Membresía `ACTIVE` en `company_id` evaluada en Operational Context con el token del usuario; sin ella, `404 PURCHASE.NOT_FOUND`. Las lecturas y las secuencias solo exigen membresía |
| Sucursal (escrituras sobre compras e hitos) | Además, acceso del usuario a la sucursal de la compra: `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`, `BRANCH_INACTIVE` o `COMPANY_INACTIVE` → `403 PURCHASE.BRANCH_ACCESS_DENIED`; sucursal de otra empresa → `404` |
| Operational Context con `403` | `403 PURCHASE.OPERATIONAL_ACCESS_DENIED` |

## Conceptos clave

| Concepto | Detalle |
|---|---|
| Estados | `status`: `DRAFT`, `CONFIRMED`, `CANCELLED`. `receipt_status` (solo desde la confirmación): `PENDING` o `RECEIVED`. Una compra `CONFIRMED` con `receipt_status: PENDING` está **pendiente de recepción**: no es mercancía recibida |
| `version` | Concurrencia optimista; toda escritura la exige; `409 PURCHASE.VERSION_CONFLICT` si no coincide |
| Costos | El comprador envía `unit_cost` por presentación (cadena decimal, > 0). El servicio calcula `base_quantity` (`quantity × base_quantity_factor_snapshot`) e `inventory_unit_cost` (costo por unidad base), que es el que recibe Inventory |
| Impuesto | `tax_amount` lo calcula el servidor con la tasa de la línea: por defecto la `purchase_tax_percentage` del producto empresarial (`tax_percentage_source: PRODUCT_DEFAULT`); con `perm:purchase:purchase_line_taxes:override` se puede enviar `tax_percentage` (0 a 100, hasta 4 decimales; `LINE_OVERRIDE`). Enviar `tax_amount` produce `422 UNKNOWN_FIELD` |
| Descuentos | `discount_amount` por línea (≥ 0, 2 decimales) |
| Totales | `subtotal` (Σ cantidad × costo − descuento), `tax_total`, `discount_total`, `total`. Cadenas decimales |
| Operaciones | `CONFIRM` (local, siempre `SUCCEEDED`), `RECEIVE` y `CANCEL` (distribuidas con Inventory; `PENDING` → `SUCCEEDED`/`FAILED`). Con una `PENDING`, `pending_operation_id` está informado y toda escritura responde `409 OPERATION_IN_PROGRESS` |
| Idempotencia | Confirmación, recepción y anulación exigen `Idempotency-Key` ([Primeros pasos §6](../guias/primeros-pasos.md#6-idempotencia-en-operaciones-de-negocio)) |
| Numeración | Al confirmar se asigna `number` desde la secuencia activa de la sucursal o, si no hay, de la empresa |
| Política de ganancia | Al confirmar, cada presentación debe tener una política de ganancia aplicable en Commercial Relationship; si no, `409 PRICING_POLICY_NOT_CONFIGURED`. Tras recibir, Purchase envía los costos reales a Commercial Relationship para la actualización automática de precios |

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Proceso y base de datos listos | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `POST` | `/companies/{company_id}/purchases` | Crear compra en borrador | `perm:purchase:purchases:create` | `WRITE` | [Ver](#3-post-companiescompany_idpurchases) |
| 4 | `GET` | `/companies/{company_id}/purchases` | Listar compras | `perm:purchase:purchases:read` | `READ` | [Ver](#4-get-companiescompany_idpurchases) |
| 5 | `GET` | `/companies/{company_id}/purchases/{purchase_id}` | Consultar compra con líneas | `perm:purchase:purchases:read` | `READ` | [Ver](#5-get-companiescompany_idpurchasespurchase_id) |
| 6 | `PUT` | `/companies/{company_id}/purchases/{purchase_id}` | Editar cabecera del borrador | `perm:purchase:purchases:update` | `WRITE` | [Ver](#6-put-companiescompany_idpurchasespurchase_id) |
| 7 | `POST` | `/companies/{company_id}/purchases/{purchase_id}/details` | Agregar línea | `perm:purchase:purchase_details:create` | `WRITE` | [Ver](#7-post-companiescompany_idpurchasespurchase_iddetails) |
| 8 | `GET` | `/companies/{company_id}/purchases/{purchase_id}/details` | Líneas de la compra | `perm:purchase:purchase_details:read` | `READ` | [Ver](#8-get-companiescompany_idpurchasespurchase_iddetails) |
| 9 | `PUT` | `/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}` | Modificar línea | `perm:purchase:purchase_details:update` | `WRITE` | [Ver](#9-put-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 10 | `DELETE` | `/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}` | Eliminar línea | `perm:purchase:purchase_details:delete` | `WRITE` | [Ver](#10-delete-companiescompany_idpurchasespurchase_iddetailsdetail_id) |
| 11 | `POST` | `/companies/{company_id}/purchases/{purchase_id}/confirmation` | Confirmar (numera; no mueve inventario) | `perm:purchase:purchases:update` | `HIGH_RISK` | [Ver](#11-post-companiescompany_idpurchasespurchase_idconfirmation) |
| 12 | `POST` | `/companies/{company_id}/purchases/{purchase_id}/receipt` | Confirmar recepción completa e ingresar en Inventory | `perm:purchase:purchases:update` | `HIGH_RISK` | [Ver](#12-post-companiescompany_idpurchasespurchase_idreceipt) |
| 13 | `POST` | `/companies/{company_id}/purchases/{purchase_id}/cancellation` | Anular (revierte la entrada si estaba recibida) | `perm:purchase:purchases:delete` | `HIGH_RISK` | [Ver](#13-post-companiescompany_idpurchasespurchase_idcancellation) |
| 14 | `GET` | `/companies/{company_id}/purchases/{purchase_id}/operations` | Operaciones de la compra | `perm:purchase:purchase_operations:read` | `READ` | [Ver](#14-get-companiescompany_idpurchasespurchase_idoperations) |
| 15 | `GET` | `/companies/{company_id}/purchase-operations/{operation_id}` | Operación por id | `perm:purchase:purchase_operations:read` | `READ` | [Ver](#15-get-companiescompany_idpurchase-operationsoperation_id) |
| 16 | `POST` | `/companies/{company_id}/purchases/{purchase_id}/lifecycle-events` | Registrar hito logístico | `perm:purchase:purchase_lifecycle_events:create` | `WRITE` | [Ver](#16-post-companiescompany_idpurchasespurchase_idlifecycle-events) |
| 17 | `GET` | `/companies/{company_id}/purchases/{purchase_id}/lifecycle-events` | Línea de tiempo de hitos | `perm:purchase:purchase_lifecycle_events:read` | `READ` | [Ver](#17-get-companiescompany_idpurchasespurchase_idlifecycle-events) |
| 18 | `POST` | `/companies/{company_id}/purchase-sequences` | Crear secuencia | `perm:purchase:purchase_sequences:create` | `WRITE` | [Ver](#18-post-companiescompany_idpurchase-sequences) |
| 19 | `GET` | `/companies/{company_id}/purchase-sequences` | Listar secuencias | `perm:purchase:purchase_sequences:read` | `READ` | [Ver](#19-get-companiescompany_idpurchase-sequences) |
| 20 | `GET` | `/companies/{company_id}/purchase-sequences/{sequence_id}` | Consultar secuencia | `perm:purchase:purchase_sequences:read` | `READ` | [Ver](#20-get-companiescompany_idpurchase-sequencessequence_id) |
| 21 | `PUT` | `/companies/{company_id}/purchase-sequences/{sequence_id}` | Modificar secuencia | `perm:purchase:purchase_sequences:update` | `WRITE` | [Ver](#21-put-companiescompany_idpurchase-sequencessequence_id) |
| 22 | `POST` | `/companies/{company_id}/purchase-sequences/{sequence_id}/deactivate` | Desactivar secuencia | `perm:purchase:purchase_sequences:update` | `HIGH_RISK` | [Ver](#22-post-companiescompany_idpurchase-sequencessequence_iddeactivate) |
| 23 | `POST` | `/companies/{company_id}/purchase-sequences/{sequence_id}/reactivate` | Activar secuencia | `perm:purchase:purchase_sequences:update` | `WRITE` | [Ver](#23-post-companiescompany_idpurchase-sequencessequence_idreactivate) |
| 24 | `GET` | `/companies/{company_id}/purchase-reports/period` | Compras del período con totales por categoría | `perm:purchase:purchases:read` | `READ` | [Ver](#24-get-companiescompany_idpurchase-reportsperiod) |

## Objetos

### `PurchaseResponse`

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | `purchase_id` |
| `company_id`, `branch_id` | UUID | Empresa y sucursal receptora |
| `company_supplier_id` | UUID | [Proveedor](../parametros/supplier-id.md) |
| `supplier_payment_condition_id`, `payment_condition_code_snapshot`, `payment_terms_days_snapshot`, `due_date` | — | Condición de pago (solo contado en el MVP: código `CASH`, 0 días) y vencimiento |
| `payment_method_id`, `payment_method_code_snapshot`, `payment_method_name_snapshot` | — | [Método de pago](../parametros/payment-method-id.md) declarado |
| `purchase_sequence_id`, `number`, `sequence_value` | — | Numeración; `null` hasta confirmar |
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | Estado |
| `operation_date` | date | Fecha de negocio (la envía el comprador) |
| `promised_delivery_at` | date-time \| null | Entrega prometida |
| `supplier_document_number` | string \| null | Número de factura o documento del proveedor |
| `supplier_name_snapshot`, `supplier_identification_snapshot` | string | Datos del proveedor congelados |
| `currency_code` | string | Moneda |
| `observations` | string \| null | ≤ 2000 |
| `subtotal`, `discount_total`, `tax_total`, `total` | string | Totales |
| `inventory_operation_id` | UUID \| null | Entrada aplicada en Inventory (tras la recepción) |
| `receipt_status` | `PENDING` \| `RECEIVED` \| null | Estado de recepción; `null` en borrador |
| `received_at`, `received_by_user_id` | — | Datos de la recepción |
| `created_by_user_id` | UUID | `application_user_id` del comprador |
| `cancelled_by_user_id`, `cancelled_at`, `cancellation_reason` | — | Datos de anulación |
| `pending_operation_id` | UUID \| null | Operación distribuida en curso |
| `version`, `created_at`, `updated_at`, `created_by`, `updated_by` | — | Concurrencia y trazabilidad |
| `lines` | array<`PurchaseDetailResponse`> \| null | En la consulta individual y en las respuestas de escritura |

### `PurchaseDetailResponse`

| Campo | Tipo | Significado |
|---|---|---|
| `id`, `purchase_id`, `line_number` | — | Línea |
| `company_product_id`, `company_product_presentation_id` | UUID | [Producto](../parametros/company-product-id.md) y [presentación](../parametros/company-product-presentation-id.md) |
| `supplier_product_id` | UUID \| null | Producto del proveedor en Commercial Relationship (`supplier-products`), si se indicó |
| `supplier_lead_time_snapshot_hours` | string \| null | Plazo de entrega del proveedor congelado |
| `product_code_snapshot`, `product_name_snapshot`, `presentation_code_snapshot`, `presentation_name_snapshot`, `unit_code_snapshot`, `base_quantity_factor_snapshot` | — | Datos congelados |
| `quantity`, `unit_cost`, `discount_amount`, `tax_amount`, `subtotal`, `total` | string | Importes de la línea |
| `tax_percentage`, `tax_percentage_source` | string \| null, `PRODUCT_DEFAULT` \| `LINE_OVERRIDE` \| null | Tasa aplicada y su origen |
| `warnings` | array<string> | Avisos no bloqueantes de la línea (por ejemplo presentación sin política de ganancia) |
| `base_quantity`, `inventory_unit_cost` | string | Cantidad y costo por unidad base enviados a Inventory |
| `created_at`, `updated_at`, `created_by`, `updated_by` | — | Trazabilidad |

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-purchase-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-purchase-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si la base de datos no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/health/ready'
```

### 3. `POST /companies/{company_id}/purchases`

| | |
|---|---|
| Clasificación | `WRITE` · crea una compra en `DRAFT` |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` |
| Permiso | `perm:purchase:purchases:create` (+ `perm:purchase:purchase_line_taxes:override` si alguna línea trae `tax_percentage`) |
| Alcance | Empresa + acceso a `branch_id` |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`PurchaseCreateIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal con acceso | [branch_id](../parametros/branch-id.md) |
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` (no `BLOCKED`) | [company_supplier_id](../parametros/supplier-id.md) |
| `operation_date` | date | Sí | Fecha de negocio | — |
| `supplier_payment_condition_id` | UUID \| null | No | Condición del proveedor cuyo tipo sea de contado (`CASH`); otra → `409 PAYMENT_CONDITION_NOT_AVAILABLE` | `supplier-payment-conditions` en Commercial Relationship |
| `payment_method_id` | UUID | Sí | Método `ACTIVE` | [payment_method_id](../parametros/payment-method-id.md) |
| `promised_delivery_at` | date-time \| null | No | **Con zona horaria** | — |
| `supplier_document_number` | string \| null | No | 1–100 | Factura del proveedor |
| `observations` | string \| null | No | ≤ 2000 | — |
| `lines[]` | array | No | Máx. 100 (`LINES_LIMIT_EXCEEDED`); una presentación a lo sumo en una línea | — |
| `lines[].company_product_id` | UUID | Sí | Producto `ACTIVE`, comprable, con control de inventario | [company_product_id](../parametros/company-product-id.md) |
| `lines[].company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y comprable del mismo producto | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `lines[].supplier_product_id` | UUID \| null | No | Producto del proveedor, del mismo proveedor y producto | `supplier-products` en Commercial Relationship |
| `lines[].quantity` | number \| string | Sí | > 0, hasta 4 decimales | — |
| `lines[].unit_cost` | number \| string | Sí | > 0 por presentación; el costo por unidad base resultante debe ser > 0 (`BASE_UNIT_COST_NOT_POSITIVE`) | — |
| `lines[].discount_amount` | number \| string | No (0) | ≥ 0 | — |
| `lines[].tax_percentage` | string \| number \| null | No | 0 a 100, hasta 4 decimales (`TAX_PERCENTAGE_OUT_OF_RANGE`); **exige** `perm:purchase:purchase_line_taxes:override` | — |

`tax_amount` **no** se acepta (`422 UNKNOWN_FIELD`): lo calcula el servidor.

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

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
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
  }'
```

Respuesta `201` (`PurchaseResponse` con `lines`; valores ilustrativos):

```json
{
  "id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-19",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "TRANSFER",
  "payment_method_name_snapshot": "Transferencia bancaria",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-19",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "supplier_name_snapshot": "Distribuidora Ejemplo S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456-7",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "500000.00",
  "discount_total": "0.00",
  "tax_total": "95000.00",
  "total": "595000.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-19T16:10:00Z",
  "updated_at": "2026-10-19T16:10:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "5b6c7d8e-9f0a-4b1c-8d2e-3f4a5b6c7d8e",
      "purchase_id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "CJ100",
      "presentation_name_snapshot": "Caja x 100",
      "base_quantity_factor_snapshot": "100.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "10.0000",
      "unit_cost": "50000.00",
      "discount_amount": "0.00",
      "tax_amount": "95000.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "500000.00",
      "total": "595000.00",
      "base_quantity": "1000.0000",
      "inventory_unit_cost": "595.00",
      "created_at": "2026-10-19T16:10:00Z",
      "updated_at": "2026-10-19T16:10:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

Reglas de negocio: referencia inexistente, de otra empresa o incoherente (presentación de otro producto, producto de otro proveedor) → `422 PURCHASE.VALIDATION_ERROR`; existente pero no utilizable (proveedor inactivo o bloqueado, producto no comprable o sin control de inventario, presentación inactiva, método inactivo, condición no vigente, otra moneda) → `409 PURCHASE.REFERENCES_NOT_ELIGIBLE`. Una presentación repetida en dos líneas → `409 DUPLICATE_PRESENTATION_IN_PURCHASE`. Si el producto no tiene tasa de impuesto configurada y no se ajusta en la línea, el borrador se guarda igualmente y el problema se informa al confirmar. `inventory_unit_cost` = (subtotal de la línea − descuento) ÷ `base_quantity`, redondeado a 4 decimales (`ROUND_HALF_UP`), **sin impuestos** (verificado en el código): es el costo que Inventory usa en las capas FIFO.

Errores: `403 FORBIDDEN` (también sin el permiso de `override` cuando se envía `tax_percentage`) / `BRANCH_ACCESS_DENIED` / `OPERATIONAL_ACCESS_DENIED`; `404`; `409`; `422` con `errors[].code` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`, `LINES_LIMIT_EXCEEDED`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `TAX_PERCENTAGE_OUT_OF_RANGE`, `BASE_UNIT_COST_NOT_POSITIVE`, `PRESENTATION_REQUIRED`…); `503` (`dependency`: `database`, `operational-context`, `commercial-relationship`, `product-catalog`, `party-identity`, `payment-reference`, `inventory`, `keycloak`).

### 4. `GET /companies/{company_id}/purchases`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` |
| Permiso | `perm:purchase:purchases:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | Membresía | [company_id](../parametros/company-id.md) |
| `page`, `page_size` | query | integer | No | 1–100, por defecto 20 | — |
| `status` | query | string | No | `DRAFT`, `CONFIRMED`, `CANCELLED` | — |
| `branch_id` | query | UUID | No | — | [branch_id](../parametros/branch-id.md) |
| `company_supplier_id` | query | UUID | No | — | [company_supplier_id](../parametros/supplier-id.md) |
| `operation_date_from`, `operation_date_to` | query | date | No | `to` ≥ `from` (`INVALID_DATE_RANGE`) | — |
| `number` | query | string | No | 1–80 | `number` de una compra confirmada |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PurchasePage`): `items[]` de `PurchaseResponse` sin `lines`, más la paginación. Orden: `operation_date` descendente, `created_at` descendente e `id` (verificado en el repositorio).

Ejemplo de respuesta `200` (`PurchasePage`; valores ilustrativos):

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

### 5. `GET /companies/{company_id}/purchases/{purchase_id}`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}`; permiso `perm:purchase:purchases:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PurchaseResponse` **con `lines`**. `404` si no existe, es de otra empresa o no hay membresía.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 6. `PUT /companies/{company_id}/purchases/{purchase_id}`

`WRITE`, solo en `DRAFT`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}`; permiso `perm:purchase:purchases:update`. Cuerpo (`PurchaseUpdateIn`): los campos de cabecera de la operación 3 (`branch_id`, `company_supplier_id`, `operation_date`, `payment_method_id` obligatorios; `supplier_payment_condition_id`, `promised_delivery_at`, `supplier_document_number`, `observations` opcionales) **más `version`**.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "operation_date": "2026-10-20",
  "supplier_payment_condition_id": null,
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "promised_delivery_at": "2026-10-25T14:00:00Z",
  "supplier_document_number": "FV-8891",
  "observations": "Entrega en bodega",
  "version": 1
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X PUT 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "operation_date": "2026-10-20",
    "supplier_payment_condition_id": null,
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "promised_delivery_at": "2026-10-25T14:00:00Z",
    "supplier_document_number": "FV-8891",
    "observations": "Entrega en bodega",
    "version": 1
  }'
```

Respuesta `200`: compra completa con `version` incrementada. Cambiar de proveedor revalida las líneas (`supplier_product_id` debe ser del nuevo proveedor). Errores: `409 INVALID_STATUS`, `VERSION_CONFLICT`, `OPERATION_IN_PROGRESS`, `REFERENCES_NOT_ELIGIBLE`; `422`; `403`; `404`.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
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
  "receipt_status": null,
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 7. `POST /companies/{company_id}/purchases/{purchase_id}/details`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details`; permiso `perm:purchase:purchase_details:create` (+ `override` si trae `tax_percentage`). Cuerpo (`LineCreateIn`): los campos de `lines[]` de la operación 3 **más `version`**.

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_id": null,
  "quantity": "5",
  "unit_cost": "48000.00",
  "discount_amount": "0",
  "version": 2
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "supplier_product_id": null,
    "quantity": "5",
    "unit_cost": "48000.00",
    "discount_amount": "0",
    "version": 2
  }'
```

Respuesta `201`: compra completa con la línea nueva. Máximo 100 líneas; `409 DUPLICATE_PRESENTATION_IN_PURCHASE` si la presentación ya está en otra línea.

Ejemplo de respuesta `201` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
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
  "receipt_status": null,
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 8. `GET /companies/{company_id}/purchases/{purchase_id}/details`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details`; permiso `perm:purchase:purchase_details:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: **array** de `PurchaseDetailResponse`.

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
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
```

### 9. `PUT /companies/{company_id}/purchases/{purchase_id}/details/{detail_id}`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}`; permiso `perm:purchase:purchase_details:update` (+ `override`). Cuerpo: `LineCreateIn`. Reemplaza la línea y recalcula el impuesto con la tasa vigente. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/f9b730a5-216e-4723-882a-387c3ae071ef' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "quantity": "2",
    "unit_cost": "500.00",
    "discount_amount": "0",
    "tax_percentage": "19",
    "version": 1
  }'
```
Respuesta `200`: compra completa.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "f9b730a5-216e-4723-882a-387c3ae071ef",
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
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
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
  "receipt_status": null,
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 10. `DELETE /companies/{company_id}/purchases/{purchase_id}/details/{detail_id}`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/details/{detail_id}?version=3`; permiso `perm:purchase:purchase_details:delete`. `version` como parámetro de consulta (≥ 1). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/details/f9b730a5-216e-4723-882a-387c3ae071ef?version=1' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: compra completa sin la línea.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "f9b730a5-216e-4723-882a-387c3ae071ef",
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
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
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
  "receipt_status": null,
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 11. `POST /companies/{company_id}/purchases/{purchase_id}/confirmation`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · asigna el número consecutivo y congela la compra; **no mueve inventario** |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/confirmation` |
| Permiso | `perm:purchase:purchases:update` |
| Cabeceras | `Authorization`, `Content-Type: application/json`, **`Idempotency-Key`** |

Cuerpo (`VersionIn`): `{"version": 3}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/confirmation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 94419401-f0a8-48c6-8808-8e6d93d898fc' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Respuesta `200`: `PurchaseResponse` con `status: "CONFIRMED"`, `receipt_status: "PENDING"`, `number`, `sequence_value`, `purchase_sequence_id` y *snapshots* congelados.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

Secuencia verificada en el código: acceso a la sucursal e idempotencia; validación completa de referencias (solo contado, método de pago, presentaciones, costos) fuera de transacción; después, en una transacción: revalida estado, versión, líneas y operación en curso, refresca y congela *snapshots* y `due_date`, asigna el número del período y pasa a `CONFIRMED`; la operación `CONFIRM` queda `SUCCEEDED`. La confirmación es **local y atómica**: un error de numeración responde `409` sin efectos.

Errores propios: `422 PURCHASE_WITHOUT_LINES`; `409 PURCHASE_TAX_NOT_CONFIGURED` («Una o más líneas no tienen tasa de impuesto de compra: configure la tasa del producto (0 es válido) o ajuste la de la línea antes de confirmar.»; `errors[]` indica las líneas); `409 PURCHASE_TAX_CHANGED` (la tasa predeterminada del producto cambió desde que se guardó la línea: vuelva a guardar la línea); `409 PRICING_POLICY_NOT_CONFIGURED` (presentaciones sin política de ganancia aplicable en una lista activa y vigente de la moneda de la compra: configúrela en Commercial Relationship); `409 SEQUENCE_NOT_CONFIGURED` / `SEQUENCE_EXHAUSTED`; `409 DUPLICATE_PRESENTATION_IN_PURCHASE`; `409 INVALID_STATUS`, `VERSION_CONFLICT`, `OPERATION_IN_PROGRESS`, `IDEMPOTENCY_KEY_CONFLICT`, `REFERENCES_NOT_ELIGIBLE`; `422 IDEMPOTENCY_KEY_REQUIRED`. En todos los casos el borrador se conserva.

### 12. `POST /companies/{company_id}/purchases/{purchase_id}/receipt`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · **ingresa la mercancía en Inventory** (entrada en unidad base con costo) |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/receipt` |
| Permiso | `perm:purchase:purchases:update` |
| Cabeceras | `Authorization`, `Content-Type: application/json`, **`Idempotency-Key`** |

Cuerpo (`ReceiptIn`): `{"version": 4, "full_receipt_confirmed": true}`. `full_receipt_confirmed` declara que se recibió **toda** la compra; no hay recepciones parciales ni por línea. Enviar `false` se rechaza con `422 FULL_RECEIPT_NOT_CONFIRMED` (verificado en el código).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/receipt' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: aa29bb14-1269-4404-84bd-7605c5b42329' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "full_receipt_confirmed": true
  }'
```

Respuesta `200`: `PurchaseResponse` con `receipt_status: "RECEIVED"`, `received_at`, `received_by_user_id`, `inventory_operation_id`.

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
  "inventory_operation_id": "5f6a7b8c-9d0e-4f1a-8b2c-3d4e5f6a7b8c",
  "receipt_status": "RECEIVED",
  "received_at": "2026-10-19T16:30:00Z",
  "received_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
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
```

Reglas: la compra debe estar `CONFIRMED`, no recibida, sin operación en curso y con la versión vigente; los costos congelados deben ser positivos. No se revalidan proveedor ni productos (Inventory valida los productos al aplicar la entrada). Se registra la operación `RECEIVE` `PENDING` cuyo `id` es la clave de la entrada en Inventory; con la entrada aplicada se completa. Si Inventory no responde, la operación queda `PENDING` y la respuesta es `503` con el `operation_id`: reintente con la **misma** `Idempotency-Key` o consulte la operación (14/15); nunca habrá dos entradas. Tras la recepción, en la misma transacción se registran los costos reales para la actualización automática de precios en Commercial Relationship.

Errores: `409 INVALID_STATUS` (no confirmada o ya recibida), `409 INVENTORY_REJECTED`, `409 OPERATION_IN_PROGRESS`, `409 VERSION_CONFLICT`, `409 IDEMPOTENCY_KEY_CONFLICT`, `403 BRANCH_ACCESS_DENIED`, `503`.

### 13. `POST /companies/{company_id}/purchases/{purchase_id}/cancellation`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · anula la compra y, si estaba recibida, **revierte la entrada de inventario** |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/cancellation` |
| Permiso | `perm:purchase:purchases:delete` |
| Cabeceras | `Authorization`, `Content-Type: application/json`, **`Idempotency-Key`** |

Cuerpo (`CancelIn`): `version` (≥ 1) y `reason` (obligatorio, no vacío, ≤ 1000).

Reglas: `DRAFT` o `CONFIRMED` pendiente de recepción → `CANCELLED` en una transacción local sin Inventory (conserva el número si lo tiene). `CONFIRMED` recibida → operación `CANCEL` `PENDING`, reverso exacto de `inventory_operation_id` y después `CANCELLED` (conserva número y datos de recepción); si el reverso falla, `FAILED` y la compra sigue `CONFIRMED`; si la mercancía ya se consumió, `409 INVENTORY_ALREADY_CONSUMED`. No revalida proveedor ni productos. Errores: `422 REASON_REQUIRED`, `409 INVALID_STATUS` (ya anulada), `VERSION_CONFLICT`, `OPERATION_IN_PROGRESS`, `IDEMPOTENCY_KEY_CONFLICT`, `INVENTORY_REJECTED`, `403`, `404`, `503`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/cancellation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 1172772c-e6c5-4e3a-87f3-a2d0f4775be3' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "reason": "Solicitud del cliente"
  }'
```

Ejemplo de respuesta `200` (`PurchaseResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
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
  "status": "CANCELLED",
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
  "cancelled_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_at": "2026-10-19T16:00:00Z",
  "cancellation_reason": "Solicitud del cliente",
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "b1a1e4be-5fb8-42b0-81c5-ca85b2fdcea6",
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
```

### 14. `GET /companies/{company_id}/purchases/{purchase_id}/operations`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/operations`; permiso `perm:purchase:purchase_operations:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/operations' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: **array** de `OperationResponse` con `id`, `purchase_id`, `operation_type` (`CONFIRM`, `RECEIVE`, `CANCEL`), `status` (`PENDING`, `SUCCEEDED`, `FAILED`), `correlation_id`, `error_code`, `error_details`, `inventory_operation_id`, `started_at`, `updated_at`, `completed_at`.

```json
[
  {
    "id": "6c7d8e9f-0a1b-4c2d-8e3f-4a5b6c7d8e9f",
    "purchase_id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
    "operation_type": "RECEIVE",
    "status": "SUCCEEDED",
    "correlation_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
    "started_at": "2026-10-20T09:00:00Z",
    "updated_at": "2026-10-20T09:00:03Z",
    "completed_at": "2026-10-20T09:00:03Z"
  }
]
```

### 15. `GET /companies/{company_id}/purchase-operations/{operation_id}`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-operations/{operation_id}`; permiso `perm:purchase:purchase_operations:read`. `operation_id` = `pending_operation_id` o `id` de la operación 14. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-operations/1741498a-d933-4d84-899c-9b85ba801695' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `OperationResponse`; `404`.

Ejemplo de respuesta `200` (`OperationResponse`; valores ilustrativos):

```json
{
  "id": "1741498a-d933-4d84-899c-9b85ba801695",
  "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "operation_type": "CONFIRM",
  "status": "SUCCEEDED",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "error_code": null,
  "error_details": null,
  "inventory_operation_id": null,
  "started_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "completed_at": null
}
```

### 16. `POST /companies/{company_id}/purchases/{purchase_id}/lifecycle-events`

| | |
|---|---|
| Clasificación | `WRITE` · registra un hito logístico inmutable (no cambia `version` ni `status`) |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/lifecycle-events` |
| Permiso | `perm:purchase:purchase_lifecycle_events:create` |
| Alcance | Empresa + acceso a la sucursal de la compra |

Cuerpo (`LifecycleEventIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `event_type` | enum | Sí | `ORDERED`, `SUPPLIER_DISPATCHED`, `ARRIVED`, `RECEIVED`, `AVAILABLE_FOR_SALE` |
| `occurred_at` | date-time | Sí | No más de 5 min en el futuro (`EVENT_IN_FUTURE`); coherente con el orden de los hitos vigentes (`EVENT_OUT_OF_ORDER`, con `conflicting_event_type`) |
| `source` | enum | Sí | `USER`, `SUPPLIER`, `INTEGRATION`, `SYSTEM` |
| `notes` | string \| null | No | ≤ 2000 |

Estados en los que se admite cada hito: `ORDERED`, `SUPPLIER_DISPATCHED` y `ARRIVED` en `DRAFT` o `CONFIRMED`; `RECEIVED` y `AVAILABLE_FOR_SALE` solo en `CONFIRMED` **y después de la recepción** (operación 12). Fuera de eso, `409 PURCHASE.EVENT_NOT_ALLOWED_IN_STATUS` (o `PURCHASE_NOT_RECEIVED`). Un hito erróneo se corrige registrando otro del mismo tipo, que pasa a ser el vigente.

```json
{
  "event_type": "SUPPLIER_DISPATCHED",
  "occurred_at": "2026-10-20T08:30:00Z",
  "source": "SUPPLIER",
  "notes": "Guía 12345"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/lifecycle-events' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "event_type": "SUPPLIER_DISPATCHED",
    "occurred_at": "2026-10-20T08:30:00Z",
    "source": "SUPPLIER",
    "notes": "Guía 12345"
  }'
```

Respuesta `201` (`LifecycleEventResponse`): `id`, `purchase_id`, `event_type`, `occurred_at`, `recorded_by_user_id`, `source`, `notes`, `created_at`, `created_by`, `is_current`.

Ejemplo de respuesta `201` (`LifecycleEventResponse`; valores ilustrativos):

```json
{
  "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
  "event_type": "RECEIVED",
  "occurred_at": "2026-10-19T15:04:05Z",
  "recorded_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "source": "USER",
  "notes": "Nota ilustrativa",
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "is_current": true
}
```

### 17. `GET /companies/{company_id}/purchases/{purchase_id}/lifecycle-events`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/lifecycle-events`; permiso `perm:purchase:purchase_lifecycle_events:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases/4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e/lifecycle-events' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`TimelineResponse`):

```json
{
  "items": [
    {
      "id": "8e9f0a1b-2c3d-4e4f-8a5b-6c7d8e9f0a1b",
      "purchase_id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
      "event_type": "ORDERED",
      "occurred_at": "2026-10-19T16:30:00Z",
      "recorded_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "source": "USER",
      "notes": null,
      "created_at": "2026-10-19T16:30:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "is_current": true
    }
  ],
  "current": {"ORDERED": "8e9f0a1b-2c3d-4e4f-8a5b-6c7d8e9f0a1b"},
  "intervals": [],
  "total_lead_time_hours": null
}
```

`current` mapea cada tipo de hito a su registro vigente; `intervals[]` (`from`, `to`, `hours`) son los tiempos entre hitos vigentes consecutivos y `total_lead_time_hours` el total (`null` hasta tener los extremos).

### 18. `POST /companies/{company_id}/purchase-sequences`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences`; permiso `perm:purchase:purchase_sequences:create`. Cuerpo (`SequenceIn`), respuesta (`SequenceResponse` con `document_kind: "PURCHASE"`) y reglas **idénticas** a las secuencias de Sales ([ver Sales, operación 16](sales.md#16-post-companiescompany_idsale-sequences)): `branch_id` opcional, `series_code` `^[A-Z0-9_-]{1,40}$`, `prefix` `^[A-Z0-9]{1,20}$`, `separator` (`-`, `/`, `.`, `_`, vacío), `initial_number` (1–10¹⁷), `maximum_number` (opcional, ≤ 10¹⁸), `number_length` (1–18), `reset_policy` (`NEVER`, `YEARLY`, `MONTHLY`). A lo sumo una secuencia activa por alcance (`409 SEQUENCE_ALREADY_ACTIVE`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "series_code": "POS-01",
    "prefix": "V",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": 999999,
    "number_length": 6,
    "reset_policy": "NEVER"
  }'
```

Ejemplo de respuesta `201` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "bf15e2c9-5389-48a2-8013-a5528d8e92c8",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "2026",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

### 19. `GET /companies/{company_id}/purchase-sequences`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences`; permiso `perm:purchase:purchase_sequences:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`SequenceList`): `{"items": [SequenceResponse, …]}` con `counters[]` (`period_key`, `current_number`, `next_number_preview`).

### 20. `GET /companies/{company_id}/purchase-sequences/{sequence_id}`

`READ`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}`. `200` con `SequenceResponse`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "2026",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

### 21. `PUT /companies/{company_id}/purchase-sequences/{sequence_id}`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}`; permiso `perm:purchase:purchase_sequences:update`. Cuerpo (`SequenceUpdateIn`): campos de la operación 18 **más `version`**. Tras el primer número asignado, el formato es inmutable (`409 SEQUENCE_IN_USE`); solo `maximum_number` puede cambiar sin quedar por debajo de un contador.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "series_code": "POS-01",
    "prefix": "V",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": 999999,
    "number_length": 6,
    "reset_policy": "NEVER",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "2026",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

### 22. `POST /companies/{company_id}/purchase-sequences/{sequence_id}/deactivate`

`HIGH_RISK` (sin secuencia activa, las confirmaciones fallan con `409 SEQUENCE_NOT_CONFIGURED`). URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}/deactivate`; cuerpo `{"version": 1}`; respuesta `200` con `is_active: false`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "2026",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

### 23. `POST /companies/{company_id}/purchase-sequences/{sequence_id}/reactivate`

`WRITE`. URL `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-sequences/{sequence_id}/reactivate`; cuerpo `{"version": 2}`; respuesta `200` con `is_active: true`; `409 SEQUENCE_ALREADY_ACTIVE` si ya hay otra activa en el mismo alcance.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "d9cd7378-6b8f-4e54-8171-39db2f8ebfe1",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-01",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": 999999,
  "number_length": 6,
  "reset_policy": "NEVER",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": [
    {
      "period_key": "2026",
      "current_number": 123,
      "next_number_preview": "V-000124"
    }
  ]
}
```

### 24. `GET /companies/{company_id}/purchase-reports/period`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchase-reports/period` |
| Permiso | `perm:purchase:purchases:read` (solo membresía; sin asignación a la sucursal) |

| Parámetro | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `date_from`, `date_to` | date | Sí | Inclusivas; `to` ≥ `from`; ≤ 366 días |
| `branch_id` | UUID, repetible | No | Máx. 100 |
| `category` | repetible | No | `RECEIVED`, `PENDING_RECEIPT`, `CANCELLED` (máx. 3) |
| `page`, `page_size` | integer | No | `page_size` 1–100, por defecto **50** |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchase-reports/period?date_from=2026-10-01&date_to=2026-10-19&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PeriodPage`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "branch_ids": [],
  "items": [
    {
      "id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
      "operation_date": "2026-10-19",
      "received_at": "2026-10-20T09:00:03Z",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "supplier_name": "Distribuidora Ejemplo S.A.S.",
      "supplier_identification": "NIT 900123456-7",
      "number": "C-000045",
      "supplier_document_number": "FV-8891",
      "status": "CONFIRMED",
      "category": "RECEIVED",
      "receipt_status": "RECEIVED",
      "currency_code": "COP",
      "total": "595000.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "received_count": 1,
      "received_total": "595000.00",
      "pending_receipt_count": 0,
      "pending_receipt_total": "0.00",
      "cancelled_count": 0,
      "cancelled_total": "0.00",
      "effective_total": "595000.00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```

Reglas: compras no `DRAFT` por `operation_date`; `category` deriva del estado: `RECEIVED` (confirmada y recibida), `PENDING_RECEIPT` (confirmada sin recibir), `CANCELLED` (anulada, aunque se hubiera recibido). `totals` es del período completo por moneda; `effective_total` = recibidas + pendientes. Orden: `operation_date`, `number`, `id`. Lo consume Business Reporting.

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 PURCHASE.FORBIDDEN` al enviar `tax_percentage` | Falta `perm:purchase:purchase_line_taxes:override` | Ocultar el ajuste de tasa a quien no lo tenga (el grupo `compras` no lo tiene) |
| `403 PURCHASE.BRANCH_ACCESS_DENIED` | Sin acceso a la sucursal | Ofrecer solo sucursales con `allowed: true` |
| `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` | Producto sin tasa de impuesto de compra | Configurar `purchase_tax_percentage` en el producto empresarial (Commercial Relationship) o ajustar la línea |
| `409 PURCHASE.PURCHASE_TAX_CHANGED` | La tasa del producto cambió tras guardar la línea | Volver a guardar la línea |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` | Presentación sin política de ganancia aplicable | Configurar la política en Commercial Relationship |
| `409 PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | Misma presentación en dos líneas | Unificar la línea |
| `409 PURCHASE.INVALID_STATUS` | Escritura fuera de `DRAFT`, recepción sin confirmar o ya recibida, anular una anulada | Bloquear la acción según `status` y `receipt_status` |
| `409 PURCHASE.INVENTORY_ALREADY_CONSUMED` | Anular una compra recibida cuya mercancía ya salió | No es anulable; registrar un ajuste de inventario |
| `409 …VERSION_CONFLICT` / `OPERATION_IN_PROGRESS` / `IDEMPOTENCY_KEY_CONFLICT` | Concurrencia | Recargar; esperar la operación; clave nueva |
| `422 PURCHASE.PURCHASE_WITHOUT_LINES` | Confirmar sin líneas | Agregar líneas |
| `503` con `operation_id` en la recepción | Inventory no respondió | Reintentar con la misma `Idempotency-Key` o consultar la operación |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía y acceso a la sucursal |
| Commercial Relationship | Proveedor, productos, presentaciones, productos del proveedor, condiciones de pago, tasa de impuesto de compra, políticas de ganancia; recibe los costos de cada recepción |
| Product Catalog | Unidades y datos globales |
| Party Identity | Identificación del proveedor para el *snapshot* |
| Payment Reference | Método de pago declarado |
| Inventory | Entrada al recibir y reverso al anular |
| Keycloak, Audit | Identidad técnica y eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 24 |
| Operaciones documentadas | 24 |
| Permisos contrastados con el código | Sí (`api/purchases.py`, `operations.py`, `lifecycle_events.py`, `sequences.py`, `purchase_reports.py`, `identity.py`) |
| Esquemas contrastados | Sí (`api/schemas/purchases.py`, `domain/lifecycle.py`, `domain/status.py`, OpenAPI desplegado) |
| Verificado | Lista de compras ordenada por `operation_date` desc, `created_at` desc, `id`; `full_receipt_confirmed: false` → `422 FULL_RECEIPT_NOT_CONFIRMED`; `inventory_unit_cost` sin impuestos |

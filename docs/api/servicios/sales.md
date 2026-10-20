# Sales API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Sales registra las **ventas** de una empresa: se crean en borrador, se les agregan líneas, se **confirman** (lo que asigna el número consecutivo y descuenta las existencias en Inventory) y pueden **anularse** (lo que revierte la salida). El vendedor nunca envía precios: los resuelve Commercial Relationship según la lista de precios aplicable. También administra las secuencias de numeración y expone agregaciones de solo lectura para reportes.

## Responsabilidad

- Ciclo de vida de la venta: `DRAFT` → `CONFIRMED` → `CANCELLED` (o `DRAFT` → `CANCELLED`).
- Validar referencias (cliente, productos, presentaciones, método de pago) contra sus servicios propietarios y congelar *snapshots* al confirmar.
- Coordinar con Inventory la salida de mercancía y su reverso mediante operaciones idempotentes y reconciliables.
- Numerar las ventas con secuencias por empresa o sucursal.
- Ventas del MVP: **de contado**, sin descuentos ni impuestos adicionales; el precio de lista es el importe final.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-sales-dev.onrender.com/api/v1` |
| Salud | `https://sio-sales-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-sales-dev.onrender.com/docs) · [/openapi.json](https://sio-sales-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `SALES.*` y `trace_id`; `400` usa `MALFORMED_BODY` |
| Operaciones en el contrato desplegado | 23 (21 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/sales-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>` de un **usuario humano**: un token de cuenta de servicio recibe `403 SALES.FORBIDDEN` en todas las rutas de negocio aunque tenga permisos.

| Permiso | Operaciones | Grupos de la plantilla |
|---|---|---|
| `perm:sales:sales:create` | Crear venta | `administradores`, `supervisores`, `ventas` (`perm:sales:all:*`) |
| `perm:sales:sales:read` | Listar, consultar, disponibilidad, agregaciones | `administradores`, `supervisores`, `ventas`, `reportes`, `consulta` |
| `perm:sales:sales:update` | Editar cabecera, **confirmar** | `administradores`, `supervisores`, `ventas` |
| `perm:sales:sales:delete` | **Anular** | `administradores`, `ventas` |
| `perm:sales:sale_details:create` / `read` / `update` / `delete` | Líneas | `administradores`, `supervisores` (salvo `delete`), `ventas`; lectura también `reportes` y `consulta` |
| `perm:sales:sale_operations:read` | Operaciones de confirmación y anulación | `administradores`, `supervisores`, `ventas`, `reportes`, `consulta` |
| `perm:sales:sale_sequences:create` / `read` / `update` | Secuencias | `administradores`, `supervisores`, `ventas`; lectura también `reportes` y `consulta` |
| `perm:sales:sales:read-profitability` | Añade costo y margen a las respuestas de venta y líneas | `administradores`, `supervisores` (permiso explícito; los comodines `read` **no** lo cubren) |

## Alcance de datos

| Regla | Detalle |
|---|---|
| Empresa | Membresía `ACTIVE` en `company_id` evaluada en Operational Context con el token del usuario; sin ella, `404 SALES.NOT_FOUND`. Las lecturas y las secuencias solo exigen membresía (una empresa inactiva se puede consultar) |
| Sucursal (escrituras sobre ventas) | Además, el usuario debe tener acceso a la sucursal de la venta: `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`, `BRANCH_INACTIVE` o `COMPANY_INACTIVE` producen `403 SALES.BRANCH_ACCESS_DENIED`; una sucursal de otra empresa, `404` |
| Operational Context con `403` | `403 SALES.OPERATIONAL_ACCESS_DENIED` (falta `perm:operational-context:application_users:read`) |

## Conceptos clave

| Concepto | Detalle |
|---|---|
| Estados de la venta | `DRAFT` (editable), `CONFIRMED` (numerada; existencias descontadas), `CANCELLED` (anulada; conserva el número si estaba confirmada) |
| `version` | Entero de concurrencia de la venta. Toda escritura exige la última versión leída; si no, `409 SALES.VERSION_CONFLICT`. Cada cambio la incrementa |
| Precio | Lo resuelve Commercial Relationship (`applicable-prices/resolve`) con la lista pedida en la línea (`price_list_id`) o la predeterminada. Se guarda como `unit_price`, `price_list_id`, `price_list_item_id`, `price_source` (`PRICE_LIST_ITEM`) y `price_list_requested`. Enviar `unit_price` produce `422 UNIT_PRICE_NOT_ALLOWED` |
| Importes | Cadenas decimales: cantidades con 4 decimales, dinero con 2. `discount_amount` y `tax_amount` deben ser `0` (MVP) |
| Cantidad base | `quantity × base_quantity_factor_snapshot` de la presentación; es la que se descuenta en Inventory |
| Operaciones (`sale_operations`) | Cada confirmación o anulación crea una operación `CONFIRM` o `CANCEL` con estado `PENDING` → `SUCCEEDED` o `FAILED`. Mientras exista una `PENDING`, la venta tiene `pending_operation_id` y toda escritura responde `409 SALES.OPERATION_IN_PROGRESS` |
| Idempotencia | Confirmación y anulación exigen `Idempotency-Key` ([Primeros pasos §6](../guias/primeros-pasos.md#6-idempotencia-en-operaciones-de-negocio)) |
| Fecha de negocio | `operation_date` y `due_date` las fija el servicio al confirmar (fecha del día en la zona horaria de la sucursal). No se envían |
| Numeración | Al confirmar se asigna `number` (`prefix` + `separator` + número con `number_length` dígitos) desde la secuencia activa de la sucursal o, si no hay, de la empresa |

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Proceso y base de datos listos | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `POST` | `/companies/{company_id}/sales` | Crear venta en borrador | `perm:sales:sales:create` | `WRITE` | [Ver](#3-post-companiescompany_idsales) |
| 4 | `GET` | `/companies/{company_id}/sales` | Listar ventas | `perm:sales:sales:read` | `READ` | [Ver](#4-get-companiescompany_idsales) |
| 5 | `GET` | `/companies/{company_id}/sales/{sale_id}` | Consultar venta con líneas | `perm:sales:sales:read` | `READ` | [Ver](#5-get-companiescompany_idsalessale_id) |
| 6 | `PUT` | `/companies/{company_id}/sales/{sale_id}` | Editar cabecera del borrador | `perm:sales:sales:update` | `WRITE` | [Ver](#6-put-companiescompany_idsalessale_id) |
| 7 | `POST` | `/companies/{company_id}/sales/{sale_id}/details` | Agregar línea | `perm:sales:sale_details:create` | `WRITE` | [Ver](#7-post-companiescompany_idsalessale_iddetails) |
| 8 | `GET` | `/companies/{company_id}/sales/{sale_id}/details` | Líneas de la venta | `perm:sales:sale_details:read` | `READ` | [Ver](#8-get-companiescompany_idsalessale_iddetails) |
| 9 | `PUT` | `/companies/{company_id}/sales/{sale_id}/details/{detail_id}` | Modificar línea | `perm:sales:sale_details:update` | `WRITE` | [Ver](#9-put-companiescompany_idsalessale_iddetailsdetail_id) |
| 10 | `DELETE` | `/companies/{company_id}/sales/{sale_id}/details/{detail_id}` | Eliminar línea | `perm:sales:sale_details:delete` | `WRITE` | [Ver](#10-delete-companiescompany_idsalessale_iddetailsdetail_id) |
| 11 | `POST` | `/companies/{company_id}/sales/{sale_id}/confirmation` | Confirmar y descontar inventario | `perm:sales:sales:update` | `HIGH_RISK` | [Ver](#11-post-companiescompany_idsalessale_idconfirmation) |
| 12 | `POST` | `/companies/{company_id}/sales/{sale_id}/cancellation` | Anular (revierte la salida) | `perm:sales:sales:delete` | `HIGH_RISK` | [Ver](#12-post-companiescompany_idsalessale_idcancellation) |
| 13 | `GET` | `/companies/{company_id}/sales/{sale_id}/operations` | Operaciones de la venta | `perm:sales:sale_operations:read` | `READ` | [Ver](#13-get-companiescompany_idsalessale_idoperations) |
| 14 | `GET` | `/companies/{company_id}/sale-operations/{operation_id}` | Operación por id | `perm:sales:sale_operations:read` | `READ` | [Ver](#14-get-companiescompany_idsale-operationsoperation_id) |
| 15 | `GET` | `/companies/{company_id}/sales/{sale_id}/availability` | Disponibilidad de existencias (sin reservar) | `perm:sales:sales:read` | `READ` | [Ver](#15-get-companiescompany_idsalessale_idavailability) |
| 16 | `POST` | `/companies/{company_id}/sale-sequences` | Crear secuencia | `perm:sales:sale_sequences:create` | `WRITE` | [Ver](#16-post-companiescompany_idsale-sequences) |
| 17 | `GET` | `/companies/{company_id}/sale-sequences` | Listar secuencias | `perm:sales:sale_sequences:read` | `READ` | [Ver](#17-get-companiescompany_idsale-sequences) |
| 18 | `GET` | `/companies/{company_id}/sale-sequences/{sequence_id}` | Consultar secuencia | `perm:sales:sale_sequences:read` | `READ` | [Ver](#18-get-companiescompany_idsale-sequencessequence_id) |
| 19 | `PUT` | `/companies/{company_id}/sale-sequences/{sequence_id}` | Modificar secuencia | `perm:sales:sale_sequences:update` | `WRITE` | [Ver](#19-put-companiescompany_idsale-sequencessequence_id) |
| 20 | `POST` | `/companies/{company_id}/sale-sequences/{sequence_id}/deactivate` | Desactivar secuencia | `perm:sales:sale_sequences:update` | `HIGH_RISK` | [Ver](#20-post-companiescompany_idsale-sequencessequence_iddeactivate) |
| 21 | `POST` | `/companies/{company_id}/sale-sequences/{sequence_id}/reactivate` | Activar secuencia | `perm:sales:sale_sequences:update` | `WRITE` | [Ver](#21-post-companiescompany_idsale-sequencessequence_idreactivate) |
| 22 | `GET` | `/companies/{company_id}/sales-aggregates/by-product` | Ventas efectivas por producto | `perm:sales:sales:read` | `READ` | [Ver](#22-get-companiescompany_idsales-aggregatesby-product) |
| 23 | `GET` | `/companies/{company_id}/sales-aggregates/by-branch` | Ventas efectivas por sucursal | `perm:sales:sales:read` | `READ` | [Ver](#23-get-companiescompany_idsales-aggregatesby-branch) |

## Objetos

### `SaleResponse`

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | `sale_id` |
| `company_id`, `branch_id` | UUID | Empresa y sucursal |
| `company_customer_id` | UUID | [Cliente](../parametros/customer-id.md) |
| `customer_payment_condition_id` | UUID \| null | Siempre `null` en el MVP (ventas de contado) |
| `payment_condition_code_snapshot` | string | Código de la condición de pago congelado (contado) |
| `payment_method_id`, `payment_method_code_snapshot`, `payment_method_name_snapshot` | — | [Método de pago](../parametros/payment-method-id.md) declarado y sus datos congelados |
| `payment_terms_days_snapshot` | integer | Días de plazo (0 en contado) |
| `due_date` | date | Vencimiento; se fija al confirmar |
| `sale_sequence_id`, `number`, `sequence_value` | — | Secuencia usada, número de documento y valor del contador; `null` hasta confirmar |
| `status` | `DRAFT` \| `CONFIRMED` \| `CANCELLED` | Estado |
| `operation_date` | date | Fecha de negocio (se fija al confirmar; en borrador es provisional) |
| `customer_name_snapshot`, `customer_identification_snapshot` | string | Datos del cliente congelados |
| `currency_code` | string | Moneda de la venta |
| `observations` | string \| null | ≤ 2000 |
| `subtotal`, `discount_total`, `tax_total`, `total` | string (decimal) | Totales |
| `has_unknown_cost` | boolean \| null | Solo con `read-profitability`: alguna línea sin costo conocido |
| `inventory_operation_id` | UUID \| null | Salida aplicada en Inventory |
| `created_by_user_id` | UUID | `application_user_id` del vendedor |
| `cancelled_by_user_id`, `cancelled_at`, `cancellation_reason` | — | Datos de anulación |
| `pending_operation_id` | UUID \| null | Operación en curso; si no es `null`, no se puede escribir |
| `version` | integer | Concurrencia |
| `created_at`, `updated_at`, `created_by`, `updated_by` | — | Trazabilidad (`sub`) |
| `lines` | array<`SaleDetailResponse`> \| null | Solo en la consulta individual y en respuestas de escritura |

### `SaleDetailResponse`

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | `detail_id` |
| `sale_id`, `line_number` | — | Venta y número de línea |
| `company_product_id`, `company_product_presentation_id` | UUID | [Producto](../parametros/company-product-id.md) y [presentación](../parametros/company-product-presentation-id.md) |
| `price_list_id`, `price_list_item_id`, `price_list_requested`, `price_source` | — | Cómo se resolvió el precio (`price_source`: `PRICE_LIST_ITEM`) |
| `product_code_snapshot`, `product_name_snapshot`, `presentation_code_snapshot`, `presentation_name_snapshot`, `unit_code_snapshot` | string | Datos congelados |
| `base_quantity_factor_snapshot` | string | Unidades base por presentación |
| `quantity`, `base_quantity` | string | Cantidad en presentación y en unidad base |
| `unit_price`, `discount_amount`, `tax_amount`, `subtotal`, `total` | string | Importes |
| `unit_cost_snapshot`, `cost_total`, `cost_known`, `gross_margin_amount`, `gross_margin_percentage` | — | Solo con `read-profitability`; costo FIFO informado por Inventory al confirmar |
| `created_at`, `updated_at`, `created_by`, `updated_by` | — | Trazabilidad |

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-sales-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-sales-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si la base de datos no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/health/ready'
```

### 3. `POST /companies/{company_id}/sales`

| | |
|---|---|
| Clasificación | `WRITE` · crea una venta en `DRAFT` (sin efectos en inventario ni numeración) |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` |
| Permiso | `perm:sales:sales:create` |
| Alcance | Empresa + acceso a `branch_id` |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`SaleCreateIn`; rechaza campos adicionales; recorta espacios):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal con acceso | [branch_id](../parametros/branch-id.md) |
| `company_customer_id` | UUID | Sí | Cliente `ACTIVE` de la empresa | [company_customer_id](../parametros/customer-id.md) |
| `payment_method_id` | UUID | Sí | Método `ACTIVE` en Payment Reference | [payment_method_id](../parametros/payment-method-id.md) |
| `observations` | string \| null | No | ≤ 2000 | — |
| `lines[]` | array | No (puede crearse vacía) | Máx. 100 líneas (`LINES_LIMIT_EXCEEDED`) | — |
| `lines[].company_product_id` | UUID | Sí | Producto `ACTIVE`, vendible, con control de inventario | [company_product_id](../parametros/company-product-id.md) |
| `lines[].company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y vendible del mismo producto | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `lines[].price_list_id` | UUID \| null | No | Lista de precios de la empresa aplicable al cliente; sin ella, la predeterminada | Listas de precios en Commercial Relationship |
| `lines[].quantity` | number \| string | Sí | > 0, hasta 4 decimales, < 10¹⁴ (`QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`) | — |
| `lines[].discount_amount` | number \| string | No | Debe ser `0` | — |
| `lines[].tax_amount` | number \| string | No | Debe ser `0` | — |

Campos **rechazados** con `422` si se envían: `operation_date`, `due_date`, `customer_payment_condition_id`, `payment_condition_code_snapshot`, `payment_terms_days_snapshot` y `lines[].unit_price`.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "observations": "Venta mostrador",
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "quantity": "2"
    }
  ]
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "observations": "Venta mostrador",
    "lines": [
      {
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
        "quantity": "2"
      }
    ]
  }'
```

Respuesta `201` (`SaleResponse` con `lines`; valores ilustrativos):

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
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-19T15:50:00Z",
  "updated_at": "2026-10-19T15:50:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "PRD-0001",
      "product_name_snapshot": "Acetaminofén 500 mg",
      "presentation_code_snapshot": "UN",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UN",
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.00",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-19T15:50:00Z",
      "updated_at": "2026-10-19T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

Reglas de negocio (verificadas en el código):

- Referencias: una referencia inexistente, de otra empresa o incoherente (presentación de otro producto) → `422 SALES.VALIDATION_ERROR`; una referencia existente pero no utilizable (cliente inactivo, producto no vendible o sin control de inventario, presentación inactiva, método de pago inactivo, lista no aplicable, sin precio vigente, otra moneda) → `409 SALES.REFERENCES_NOT_ELIGIBLE`. Si hay ambas clases, se informa el `422`.
- Precio: una sola resolución por venta en Commercial Relationship; solo se acepta un precio explícito de la presentación (`PRICE_LIST_ITEM`). Sin precio vigente → `409`.
- Importes: `subtotal = quantity × unit_price`; `total = subtotal` (sin descuentos ni impuestos).
- Los *snapshots* de cliente, producto y presentación se capturan al crear o modificar; se vuelven a validar al confirmar.

Errores: `403 FORBIDDEN` / `BRANCH_ACCESS_DENIED` / `OPERATIONAL_ACCESS_DENIED`; `404 NOT_FOUND`; `409 REFERENCES_NOT_ELIGIBLE`; `422 VALIDATION_ERROR` con `errors[].code` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`, `LINES_LIMIT_EXCEEDED`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `AMOUNT_OUT_OF_RANGE`, `UNIT_PRICE_NOT_ALLOWED`, `OPERATION_DATE_NOT_ALLOWED`, `PAYMENT_CONDITION_NOT_ALLOWED`…); `503 DEPENDENCY_UNAVAILABLE` (`dependency`: `database`, `operational-context`, `commercial-relationship`, `product-catalog`, `party-identity`, `inventory`, `keycloak`).

Dependencias: Operational Context (acceso), Commercial Relationship (cliente, productos, presentaciones, precio), Party Identity (identificación del cliente), Payment Reference (método de pago), Audit (evento).

### 4. `GET /companies/{company_id}/sales`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` |
| Permiso | `perm:sales:sales:read` |

| Parámetro | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | Membresía | [company_id](../parametros/company-id.md) |
| `page`, `page_size` | query | integer | No | 1–100, por defecto 20 | — |
| `status` | query | string | No | `DRAFT`, `CONFIRMED` o `CANCELLED` | — |
| `branch_id` | query | UUID | No | — | [branch_id](../parametros/branch-id.md) |
| `company_customer_id` | query | UUID | No | — | [company_customer_id](../parametros/customer-id.md) |
| `operation_date_from`, `operation_date_to` | query | date | No | — | — |
| `number` | query | string | No | 1–80 caracteres; número de documento | `number` de una venta confirmada |

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`SalePage`): `items[]` de `SaleResponse` **sin `lines`**, más `page`, `page_size`, `total_records`, `total_pages`. Con `read-profitability` cada venta incluye `has_unknown_cost`. Orden de la lista: `operation_date` descendente, `created_at` descendente e `id` (verificado en el repositorio).

Ejemplo de respuesta `200` (`SalePage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
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
          "id": "ce488045-ed3f-4b6c-81d2-68ee8c3fe7a0",
          "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
          "line_number": 1,
          "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
          "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
          "price_list_requested": false,
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
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 5. `GET /companies/{company_id}/sales/{sale_id}`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}`; permiso `perm:sales:sales:read`. `sale_id` es el `id` devuelto al crear o listar. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `SaleResponse` **con `lines`** (y, con `read-profitability`, costo y margen por línea). `404 SALES.NOT_FOUND` si no existe, es de otra empresa o el usuario no tiene membresía.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

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
      "price_list_requested": false,
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

### 6. `PUT /companies/{company_id}/sales/{sale_id}`

| | |
|---|---|
| Clasificación | `WRITE` · solo en `DRAFT` |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}` |
| Permiso | `perm:sales:sales:update` |
| Alcance | Empresa + acceso a la sucursal actual y a la nueva |

Cuerpo (`SaleUpdateIn`): `branch_id` (UUID), `company_customer_id` (UUID), `payment_method_id` (UUID), `observations` (≤ 2000, opcional) y **`version`** (≥ 1), todos salvo `observations` obligatorios. Rechaza campos adicionales y los campos prohibidos de la operación 3.

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "observations": "Cliente recoge en tienda",
  "version": 1
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X PUT 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "observations": "Cliente recoge en tienda",
    "version": 1
  }'
```

Respuesta `200`: `SaleResponse` con `lines` y `version` incrementada. Reglas: cambiar de cliente o sucursal vuelve a validar referencias y a resolver precios de las líneas. Errores: `409 INVALID_STATUS` (no es `DRAFT`), `409 VERSION_CONFLICT`, `409 OPERATION_IN_PROGRESS`, `409 REFERENCES_NOT_ELIGIBLE`, `422`, `403`, `404`.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

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
      "price_list_requested": false,
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

### 7. `POST /companies/{company_id}/sales/{sale_id}/details`

| | |
|---|---|
| Clasificación | `WRITE` · agrega una línea a un borrador |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details` |
| Permiso | `perm:sales:sale_details:create` |

Cuerpo (`LineCreateIn`): los campos de `lines[]` de la operación 3 **más `version`** de la venta (≥ 1).

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "price_list_id": null,
  "quantity": "3.5",
  "version": 2
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "price_list_id": null,
    "quantity": "3.5",
    "version": 2
  }'
```

Respuesta `201`: la **venta completa** (`SaleResponse` con `lines`) con la nueva línea y totales recalculados. Máximo 100 líneas por venta. Errores como en la operación 6.

Ejemplo de respuesta `201` (`SaleResponse`; valores ilustrativos):

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
      "price_list_requested": false,
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

### 8. `GET /companies/{company_id}/sales/{sale_id}/details`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details`; permiso `perm:sales:sale_details:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: **array** de `SaleDetailResponse` (sin envoltura de paginación). `404` si la venta no está en el alcance.

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
    "line_number": 1,
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
    "price_list_requested": false,
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
```

### 9. `PUT /companies/{company_id}/sales/{sale_id}/details/{detail_id}`

`WRITE`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}`; permiso `perm:sales:sale_details:update`. `detail_id` es el `id` de la línea. Cuerpo: `LineCreateIn` (igual que la operación 7). Reemplaza producto, presentación, lista y cantidad de la línea y vuelve a resolver el precio. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/f9b730a5-216e-4723-882a-387c3ae071ef' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "quantity": "2",
    "discount_amount": "0",
    "tax_amount": "0",
    "version": 1
  }'
```
Respuesta `200`: venta completa. Errores como en la operación 6.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

```json
{
  "id": "f9b730a5-216e-4723-882a-387c3ae071ef",
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
      "price_list_requested": false,
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

### 10. `DELETE /companies/{company_id}/sales/{sale_id}/details/{detail_id}`

`WRITE`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/details/{detail_id}?version=3`; permiso `perm:sales:sale_details:delete`. La versión va como **parámetro de consulta** `version` (obligatorio, ≥ 1). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/details/f9b730a5-216e-4723-882a-387c3ae071ef?version=1' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: venta completa sin la línea; las líneas restantes **no** se renumeran y una línea nueva toma el menor número libre (verificado en el código). Errores: `409 INVALID_STATUS`, `VERSION_CONFLICT`, `OPERATION_IN_PROGRESS`; `404`.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

```json
{
  "id": "f9b730a5-216e-4723-882a-387c3ae071ef",
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
      "price_list_requested": false,
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

### 11. `POST /companies/{company_id}/sales/{sale_id}/confirmation`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · asigna número consecutivo, fija la fecha de negocio y **descuenta existencias** en Inventory |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/confirmation` |
| Permiso | `perm:sales:sales:update` |
| Alcance | Empresa + acceso a la sucursal |
| Cabeceras | `Authorization`, `Content-Type: application/json`, **`Idempotency-Key`** (obligatoria; 1–150 caracteres ASCII imprimibles sin espacios) |

Cuerpo (`VersionIn`): `{"version": 3}`.

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/confirmation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"version": 3}'
```

Respuesta `200`: `SaleResponse` con `status: "CONFIRMED"`, `number`, `sequence_value`, `sale_sequence_id`, `operation_date`, `due_date`, `inventory_operation_id` y, con `read-profitability`, los costos FIFO y márgenes por línea.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

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
      "price_list_requested": false,
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

Secuencia verificada en el código:

1. Acceso a la sucursal; idempotencia (la clave queda ligada a la venta, al tipo de operación y al usuario); si hay una operación en curso, `409 OPERATION_IN_PROGRESS`; después, versión.
2. Revalidación de cliente, productos, presentaciones y usuario operativo, y **nueva resolución del precio** con la intención original de cada línea. Si el precio, la lista o el ítem cambiaron → `409 SALES.PRICES_CHANGED` sin efectos: el frontend debe mostrar los nuevos precios y pedir confirmación de nuevo (la venta actualizada se obtiene con la operación 5).
3. Consulta informativa de existencias; la barrera real es Inventory. Sin existencias suficientes → `409 SALES.INSUFFICIENT_STOCK`; si Inventory rechaza por otra causa → `409 SALES.INVENTORY_REJECTED`.
4. Se busca la secuencia activa de la sucursal o, si no hay, de la empresa, para el período de la fecha del día en la zona horaria de la sucursal: sin secuencia → `409 SEQUENCE_NOT_CONFIGURED`; agotada → `409 SEQUENCE_EXHAUSTED`.
5. Se registra la operación `CONFIRM` `PENDING`, se fijan `operation_date` y `due_date`, se congelan los *snapshots* y se envía la salida a Inventory con la clave = `id` de la operación.
6. Con la salida aplicada se copian los costos FIFO, se calcula el margen, se asigna el número y la venta pasa a `CONFIRMED`.

Otros errores: `422 SALES.SALE_WITHOUT_LINES` (borrador sin líneas), `422 IDEMPOTENCY_KEY_REQUIRED`, `409 IDEMPOTENCY_KEY_CONFLICT` (misma clave con otro cuerpo u otra venta), `409 INVALID_STATUS` (no es `DRAFT`), `409 VERSION_CONFLICT`, `409 OPERATION_NOT_APPLIED`, `503`. Si Inventory no responde, la operación queda `PENDING` y la venta con `pending_operation_id`: consulte la operación 13 o 14 hasta que el conciliador la resuelva; repetir la misma `Idempotency-Key` devuelve el mismo resultado.

Efectos secundarios: salida de inventario en la sucursal (Inventory), consumo de un número de la secuencia, evento de auditoría. **Nunca se consume un número sin confirmar la venta**: si la numeración falla tras aplicar la salida, el servicio pide el reverso (compensación).

### 12. `POST /companies/{company_id}/sales/{sale_id}/cancellation`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · anula la venta y, si estaba confirmada, **revierte la salida de inventario** |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/cancellation` |
| Permiso | `perm:sales:sales:delete` |
| Cabeceras | `Authorization`, `Content-Type: application/json`, **`Idempotency-Key`** |

Cuerpo (`CancelIn`): `version` (≥ 1) y `reason` (obligatorio, sin espacios en blanco solos, ≤ 1000 caracteres).

```json
{
  "version": 4,
  "reason": "Cliente desistió de la compra"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/cancellation' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: 31b95ed2-e521-4ee6-8e96-af1c71670acd' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 4,
    "reason": "Cliente desistió de la compra"
  }'
```

Respuesta `200`: `SaleResponse` con `status: "CANCELLED"`, `cancelled_by_user_id`, `cancelled_at` y `cancellation_reason`. Una venta confirmada **conserva su `number`**.

Ejemplo de respuesta `200` (`SaleResponse`; valores ilustrativos):

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
  "status": "CANCELLED",
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
      "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "line_number": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "price_list_requested": false,
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

Reglas: `DRAFT` → `CANCELLED` en una transacción local sin Inventory (la operación `CANCEL` queda `SUCCEEDED` como traza). `CONFIRMED` → operación `CANCEL` `PENDING`, reverso en Inventory de exactamente `inventory_operation_id` y después `CANCELLED`; si el reverso falla, la operación queda `FAILED` y la venta sigue `CONFIRMED`. La anulación no revalida cliente ni productos. Una venta ya `CANCELLED` → `409 INVALID_STATUS`. Errores: `422 REASON_REQUIRED`, `422 IDEMPOTENCY_KEY_REQUIRED`, `409 IDEMPOTENCY_KEY_CONFLICT`, `409 VERSION_CONFLICT`, `409 OPERATION_IN_PROGRESS`, `409 INVENTORY_REJECTED`, `403`, `404`, `503`.

### 13. `GET /companies/{company_id}/sales/{sale_id}/operations`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/operations`; permiso `perm:sales:sale_operations:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/operations' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: **array** de `OperationResponse`:

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | `operation_id`; es también la clave enviada a Inventory |
| `sale_id` | UUID | Venta |
| `operation_type` | `CONFIRM` \| `CANCEL` | Tipo |
| `status` | `PENDING` \| `SUCCEEDED` \| `FAILED` | Estado |
| `correlation_id` | UUID | Correlación con Inventory y Audit |
| `error_code`, `error_details` | string \| null, object \| null | Causa del fallo |
| `inventory_operation_id` | UUID \| null | Salida o reverso aplicado en Inventory |
| `started_at`, `updated_at`, `completed_at` | date-time | Tiempos |

```json
[
  {
    "id": "0b1c2d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e",
    "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
    "operation_type": "CONFIRM",
    "status": "SUCCEEDED",
    "correlation_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
    "started_at": "2026-10-19T16:00:00Z",
    "updated_at": "2026-10-19T16:00:02Z",
    "completed_at": "2026-10-19T16:00:02Z"
  }
]
```

Úsalo para mostrar el estado de una confirmación o anulación que quedó `PENDING` (por ejemplo, si Inventory no respondió).

### 14. `GET /companies/{company_id}/sale-operations/{operation_id}`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-operations/{operation_id}`; permiso `perm:sales:sale_operations:read`. `operation_id` = `pending_operation_id` de la venta o `id` de la operación 13. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-operations/1741498a-d933-4d84-899c-9b85ba801695' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `OperationResponse`; `404` si no existe o es de otra empresa.

Ejemplo de respuesta `200` (`OperationResponse`; valores ilustrativos):

```json
{
  "id": "1741498a-d933-4d84-899c-9b85ba801695",
  "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
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

### 15. `GET /companies/{company_id}/sales/{sale_id}/availability`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales/{sale_id}/availability`; permiso `perm:sales:sales:read`. Consulta a Inventory las existencias disponibles para las líneas de la venta en su sucursal, **sin reservar**. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales/9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a/availability' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`AvailabilityResponse`):

```json
{
  "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "all_available": false,
  "products": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "line_numbers": [1, 3],
      "required_base_quantity": "5.5000",
      "available_base_quantity": "2.0000",
      "is_available": false
    }
  ]
}
```

Las líneas del mismo producto se suman (`line_numbers`). Útil antes de confirmar; la verificación definitiva la hace Inventory al confirmar. `503` con `dependency: inventory` si Inventory no responde.

### 16. `POST /companies/{company_id}/sale-sequences`

| | |
|---|---|
| Clasificación | `WRITE` · crea una secuencia de numeración y la deja activa |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences` |
| Permiso | `perm:sales:sale_sequences:create` |
| Alcance | Empresa (solo membresía) |

Cuerpo (`SequenceIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `branch_id` | UUID \| null | No | `null` = secuencia de la empresa; con valor, de esa sucursal |
| `series_code` | string | Sí | `^[A-Z0-9_-]{1,40}$` |
| `prefix` | string | Sí | `^[A-Z0-9]{1,20}$` |
| `separator` | enum | Sí | `-`, `/`, `.`, `_` o cadena vacía |
| `initial_number` | integer | Sí | 1 a 10¹⁷ |
| `maximum_number` | integer \| null | No | 1 a 10¹⁸; ≥ contadores existentes |
| `number_length` | integer | Sí | 1 a 18 dígitos (relleno con ceros) |
| `reset_policy` | enum | Sí | `NEVER`, `YEARLY`, `MONTHLY` |

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "series_code": "POS-CENTRO",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": null,
  "number_length": 6,
  "reset_policy": "YEARLY"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "series_code": "POS-CENTRO",
    "prefix": "V",
    "separator": "-",
    "initial_number": 1,
    "maximum_number": null,
    "number_length": 6,
    "reset_policy": "YEARLY"
  }'
```

Respuesta `201` (`SequenceResponse`; valores ilustrativos):

```json
{
  "id": "4d5e6f7a-8b9c-4d0e-8f1a-2b3c4d5e6f7a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "document_kind": "SALE",
  "series_code": "POS-CENTRO",
  "prefix": "V",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": null,
  "number_length": 6,
  "reset_policy": "YEARLY",
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:00:00Z",
  "updated_at": "2026-10-19T15:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "counters": []
}
```

Reglas: **a lo sumo una secuencia activa** por empresa, sucursal (o ninguna) y tipo documental; crear otra activa en el mismo alcance → `409 SALES.SEQUENCE_ALREADY_ACTIVE`. `branch_id` debe ser de la empresa (`409 REFERENCES_NOT_ELIGIBLE` o `404`). Los `counters` (`period_key`, `current_number`, `next_number_preview`) aparecen a medida que se asignan números por período (`period_key` según `reset_policy`).

### 17. `GET /companies/{company_id}/sale-sequences`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences`; permiso `perm:sales:sale_sequences:read`. Sin parámetros de consulta. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`SequenceList`): `{"items": [SequenceResponse, …]}` con sus contadores, ordenadas por creación.

### 18. `GET /companies/{company_id}/sale-sequences/{sequence_id}`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}`. `200` con `SequenceResponse`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
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

### 19. `PUT /companies/{company_id}/sale-sequences/{sequence_id}`

`WRITE`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}`; permiso `perm:sales:sale_sequences:update`. Cuerpo (`SequenceUpdateIn`): los campos de la operación 16 **más `version`**. Regla: tras el primer número asignado son **inmutables** `prefix`, `separator`, `number_length`, `series_code`, `reset_policy`, `initial_number` y `branch_id` → `409 SALES.SEQUENCE_IN_USE`; `maximum_number` puede cambiar si no queda por debajo de ningún contador. Los contadores no se modifican por la API. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1' \
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
Respuesta `200`; errores `409 VERSION_CONFLICT`, `SEQUENCE_IN_USE`, `422`, `404`.

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

### 20. `POST /companies/{company_id}/sale-sequences/{sequence_id}/deactivate`

`HIGH_RISK`: sin secuencia activa aplicable, las confirmaciones de esa sucursal o empresa fallan con `409 SEQUENCE_NOT_CONFIGURED`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}/deactivate`; permiso `perm:sales:sale_sequences:update`. Cuerpo `{"version": 1}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `is_active: false`.

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

### 21. `POST /companies/{company_id}/sale-sequences/{sequence_id}/reactivate`

`WRITE`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sale-sequences/{sequence_id}/reactivate`; permiso `perm:sales:sale_sequences:update`. Cuerpo `{"version": 2}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sale-sequences/d9cd7378-6b8f-4e54-8171-39db2f8ebfe1/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `is_active: true`; `409 SEQUENCE_ALREADY_ACTIVE` si ya hay otra activa en el mismo alcance.

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

### 22. `GET /companies/{company_id}/sales-aggregates/by-product`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales-aggregates/by-product` |
| Permiso | `perm:sales:sales:read` (no incluye costos: `read-profitability` no cambia la respuesta) |

| Parámetro | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `date_from`, `date_to` | date | Sí | `date_to` ≥ `date_from` (`INVALID_DATE_RANGE`); ≤ 366 días (`PERIOD_TOO_LONG`) |
| `branch_id` | UUID, repetible | No | Máx. 100; sin él, toda la empresa |
| `order_by` | `quantity_base` \| `amount` | No (`quantity_base`) | — |
| `limit` | integer | No (20) | 1–100 |
| `include_presentations` | boolean | No (`false`) | Desglose por presentación |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales-aggregates/by-product?date_from=2026-10-01&date_to=2026-10-19' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`ByProductOut`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "branch_ids": [],
  "sales_status": "CONFIRMED",
  "order_by": "quantity_base",
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "product_code": "PRD-0001",
      "product_name": "Acetaminofén 500 mg",
      "currency_code": "COP",
      "quantity_base": "1200.0000",
      "amount": "960000.00",
      "sales_count": 85,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "code": "UN",
          "name": "Unidad",
          "quantity": "1200.0000",
          "quantity_base": "1200.0000",
          "amount": "960000.00"
        }
      ]
    }
  ],
  "totals": [
    {"currency_code": "COP", "amount": "4350000.00", "sales_count": 310}
  ]
}
```

Reglas: solo ventas `CONFIRMED` con `operation_date` en el período (las anuladas se excluyen por su estado actual; los borradores nunca cuentan). `quantity_base` = Σ `quantity × base_quantity_factor_snapshot`; `amount` = Σ (`subtotal − discount_amount`). `totals` cubre todas las ventas efectivas del alcance, no solo las filas devueltas. Lo consume Business Reporting.

### 23. `GET /companies/{company_id}/sales-aggregates/by-branch`

`READ`. URL `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales-aggregates/by-branch`; permiso `perm:sales:sales:read`. Parámetros: `date_from`, `date_to` (obligatorios; mismas reglas) y `branch_id` repetible. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales-aggregates/by-branch?date_from=2026-10-01&date_to=2026-10-19' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`ByBranchOut`): `items[]` con `branch_id`, `currency_code`, `sales_count`, `total_amount` (Σ `total`), y `totals[]` por moneda. Una sucursal sin ventas efectivas **no aparece**.

Ejemplo de respuesta `200` (`ByBranchOut`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "branch_ids": [
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ],
  "sales_status": "CONFIRMED",
  "items": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "currency_code": "COP",
      "sales_count": 5,
      "total_amount": "1600.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "sales_count": 5,
      "total_amount": "1600.00"
    }
  ]
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 SALES.FORBIDDEN` | Sin permiso o token de cuenta de servicio | Revisar permisos del grupo |
| `403 SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignada la sucursal, o sucursal/empresa inactiva | Ofrecer solo sucursales con `allowed: true` en `/me/operational-context` |
| `404 SALES.NOT_FOUND` | Sin membresía, venta de otra empresa o inexistente | Verificar `company_id` y `sale_id` |
| `409 SALES.VERSION_CONFLICT` | `version` desactualizada | Recargar la venta y repetir |
| `409 SALES.INVALID_STATUS` | Escritura sobre una venta que no está en `DRAFT` (o anular una ya anulada) | Bloquear la edición en la interfaz |
| `409 SALES.OPERATION_IN_PROGRESS` | Hay una operación `PENDING` | Consultar la operación y esperar |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` | Cliente, producto, presentación, método de pago o lista no utilizables | Mostrar el `detail`; elegir otra referencia |
| `409 SALES.PRICES_CHANGED` | El precio cambió entre el borrador y la confirmación | Recargar la venta, mostrar precios y volver a confirmar |
| `409 SALES.INSUFFICIENT_STOCK` / `INVENTORY_REJECTED` | Inventory no pudo aplicar la salida | Revisar disponibilidad (operación 15) |
| `409 SALES.SEQUENCE_NOT_CONFIGURED` / `SEQUENCE_EXHAUSTED` | Falta secuencia activa o se agotó | Configurar secuencia (operaciones 16 a 21) |
| `409 SALES.IDEMPOTENCY_KEY_CONFLICT` | Misma clave con otro cuerpo u otra venta | Generar una clave nueva por operación |
| `422 SALES.SALE_WITHOUT_LINES` | Confirmar un borrador vacío | Agregar líneas |
| `422 SALES.VALIDATION_ERROR` | Ver `errors[].field` y `errors[].code` | Marcar el campo |
| `503 SALES.DEPENDENCY_UNAVAILABLE` | `dependency` indica el servicio caído | Reintentar; si fue en confirmación, consultar la operación |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía y acceso a la sucursal (`operational-access`, con el token del usuario) |
| Commercial Relationship | Cliente, productos, presentaciones y resolución de precios (`applicable-prices/resolve`) |
| Product Catalog | Unidades y datos globales de los productos |
| Party Identity | Identificación del cliente para el *snapshot* |
| Payment Reference | Método de pago declarado |
| Inventory | Disponibilidad, salida al confirmar, reverso al anular, costo FIFO |
| Keycloak | Identidad técnica del servicio para algunas llamadas internas |
| Audit | Eventos de auditoría de cada cambio |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 23 |
| Operaciones documentadas | 23 |
| Permisos contrastados con el código | Sí (`api/sales.py`, `operations.py`, `availability.py`, `sequences.py`, `sales_aggregates.py`, `profitability.py`, `identity.py`) |
| Esquemas contrastados | Sí (`api/schemas/sales.py`, `api/schemas/sales_aggregates.py`, OpenAPI desplegado) |
| Verificado | Lista de ventas ordenada por `operation_date` desc, `created_at` desc, `id`; al eliminar una línea las demás conservan su número |

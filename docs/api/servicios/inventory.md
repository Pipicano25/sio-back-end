# Inventory API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Inventory lleva las **existencias por producto y sucursal** de cada empresa y su valoración FIFO. Las entradas de compra y las salidas de venta las aplican Purchase y Sales con sus cuentas técnicas; el frontend usa Inventory para **consultar** saldos, kardex, valoración y evolución, para registrar **ajustes manuales** y **conteos físicos**, y para administrar las **políticas** de inventario (mínimos por producto y sucursal). Para pantallas de catálogo con existencias conviene usar [Product Inventory Query](product-inventory-query.md), que ya combina Inventory con Commercial Relationship y Product Catalog.

## Responsabilidad

- Saldos por (empresa, sucursal, producto) en **unidad base**, nunca negativos; kardex cronológico de movimientos.
- Operaciones idempotentes de entrada, salida, reverso y ajuste, todo o nada, con clave de operación.
- Valoración FIFO: capas de costo, consumos y valor del inventario.
- Conteos físicos con aplicación de diferencias como ajustes.
- Políticas de la empresa (sistema de inventario, método de valoración) y de producto por sucursal (stock mínimo, reposición).
- Consultas agregadas para Product Inventory Query y Business Reporting.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-inventory-dev.onrender.com/api/v1` |
| Salud | `https://sio-inventory-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-inventory-dev.onrender.com/docs) · [/openapi.json](https://sio-inventory-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `INVENTORY.*` y `trace_id`; `400` usa `MALFORMED_BODY` |
| Operaciones en el contrato desplegado | 38 (36 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/inventory-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos `perm:inventory:{recurso}:{accion}`:

| Permiso | Operaciones | Quién debe usarlo | Grupos de la plantilla |
|---|---|---|---|
| `entries:create` | Aplicar y revertir entradas | **Solo cuentas de servicio** (Purchase). Un usuario humano recibe `403` | Ninguno (cuentas técnicas) |
| `outputs:create` | Aplicar y revertir salidas | **Solo cuentas de servicio** (Sales) | Ninguno |
| `balances:read` | Stock, saldo, lookup de saldos, conjuntos de productos, resumen | Usuarios con membresía | `administradores`, `supervisores`, `inventario` |
| `movements:read` | Kardex y operaciones | Usuarios con membresía | `administradores`, `supervisores`, `inventario` |
| `valuation:read` | Valoración, capas, consumos; `include_valuation` del resumen | Usuarios con membresía | `administradores`, `supervisores`, `inventario` |
| `adjustments:create` | Registrar ajuste | **Usuario humano asignado a la sucursal** | `administradores`, `supervisores`, `inventario` |
| `adjustments:read` | Listar y consultar ajustes | Membresía | `administradores`, `supervisores`, `inventario` |
| `counts:create` | Crear, iniciar, registrar, completar y cancelar conteos | **Usuario humano asignado a la sucursal** | `administradores`, `supervisores`, `inventario` |
| `counts:read` | Listar y consultar conteos | Membresía | `administradores`, `supervisores`, `inventario` |
| `company-policies:read` / `update` | Política de la empresa (leer / registrar y actualizar) | Membresía; escritura por usuario humano | Lectura: `administradores`, `supervisores`, `inventario`. Escritura: `administradores`, `supervisores` |
| `product-policies:read` / `update` | Políticas de producto (leer, lookup / crear, actualizar, inactivar) | Ídem | Ídem |
| `stock_evolution:read` | Evolución de existencias (sucursal y consolidada) | Membresía | `administradores`, `supervisores`, `inventario`, `reportes` |
| `platform:lookup` | Lecturas técnicas sin membresía | Cuentas de servicio | — |

Los grupos `compras`, `ventas` y `consulta` no tienen permisos de Inventory en la plantilla (ventas accede a existencias a través de Product Inventory Query).

## Alcance de datos

| Operaciones | Regla |
|---|---|
| Lecturas (`/companies/{company_id}/…`) | Membresía `ACTIVE` en la empresa (evaluada en Operational Context con el token del usuario) o cuenta técnica con `platform:lookup`. Sin asignación a la sucursal. Fuera de alcance → `404 INVENTORY.NOT_FOUND` |
| Ajustes y conteos | Además, asignación `ACTIVE` del usuario a la sucursal: `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`, `BRANCH_INACTIVE`, `COMPANY_INACTIVE` → `403 INVENTORY.BRANCH_ACCESS_DENIED`; sucursal de otra empresa → `404` |
| Políticas (escritura) | Usuario humano con membresía en la empresa |
| Entradas y salidas | Cuenta de servicio; la empresa y sucursal van en el cuerpo |
| Operational Context responde `403` | `403 INVENTORY.OPERATIONAL_ACCESS_DENIED` |

## Conceptos clave

| Concepto | Detalle |
|---|---|
| Unidad base y decimales | Todas las cantidades se expresan en la unidad base del producto, como cadenas con hasta 4 decimales; los importes con 2 |
| Operación (`InventoryOperationResponse`) | Registro atómico con 1 a 100 movimientos. `operation_type`: `ENTRY`, `OUTPUT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`, `ADJUSTMENT`. `origin_type`: `PURCHASE` (entradas y sus reversos), `SALE` (salidas y sus reversos), `ADJUSTMENT` o `COUNT` (ajustes) |
| Movimiento (`MovementResponse` / `KardexMovement`) | `movement_type`: `PURCHASE_ENTRY`, `SALE_OUTPUT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`, `POSITIVE_ADJUSTMENT`, `NEGATIVE_ADJUSTMENT`; `previous_balance`, `new_balance`, `balance_sequence` (orden del saldo), `unit_cost`, `movement_value`, `cost_known` |
| Clave de operación | `operation_key` / `adjustment_key` / `completion_key` (UUID generado por el cliente): repetir la misma solicitud con la misma clave devuelve `200` con el resultado original sin volver a aplicar; la misma clave con otro contenido u otro cliente → `409 OPERATION_KEY_CONFLICT` |
| Saldo nunca negativo | Una salida, un reverso de entrada o un ajuste negativo que dejaría saldo negativo → `409 INSUFFICIENT_STOCK` con la extensión `shortages` (faltantes por producto) |
| FIFO | Cada entrada o ajuste positivo abre una **capa de costo** (`layer_kind`: `ENTRY`, `ADJUSTMENT`, `OPENING`; `status`: `OPEN`, `CLOSED`). Las salidas consumen capas en orden (`consumption_type`: `CONSUME`, `RESTORE`, `ENTRY_REVERSAL`). `cost_known: false` marca cantidades sin costo conocido |
| Reversos | Un reverso deshace una operación completa, una sola vez (`409 ALREADY_REVERSED`); un reverso no se revierte (`409 REVERSAL_NOT_ALLOWED`); revertir una entrada cuyas capas ya se consumieron → `409 ENTRY_LAYER_CONSUMED` |

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Base de datos lista | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `POST` | `/inventory-entries` | Aplicar entrada de compra | `entries:create` + cuenta de servicio | `HIGH_RISK` | [Ver](#3-post-inventory-entries) |
| 4 | `POST` | `/inventory-entries/{operation_id}/reversal` | Revertir entrada | `entries:create` + cuenta de servicio | `HIGH_RISK` | [Ver](#4-post-inventory-entriesoperation_idreversal) |
| 5 | `POST` | `/inventory-outputs` | Aplicar salida de venta | `outputs:create` + cuenta de servicio | `HIGH_RISK` | [Ver](#5-post-inventory-outputs) |
| 6 | `POST` | `/inventory-outputs/{operation_id}/reversal` | Revertir salida | `outputs:create` + cuenta de servicio | `HIGH_RISK` | [Ver](#6-post-inventory-outputsoperation_idreversal) |
| 7 | `GET` | `/companies/{company_id}/branches/{branch_id}/balances` | Stock de una sucursal | `balances:read` | `READ` | [Ver](#7-get-companiescompany_idbranchesbranch_idbalances) |
| 8 | `GET` | `/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}` | Saldo de un producto | `balances:read` | `READ` | [Ver](#8-get-companiescompany_idbranchesbranch_idbalancescompany_product_id) |
| 9 | `POST` | `/companies/{company_id}/branches/{branch_id}/balances/lookup` | Saldos de hasta 100 productos | `balances:read` | `READ` | [Ver](#9-post-companiescompany_idbranchesbranch_idbalanceslookup) |
| 10 | `GET` | `/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}` | Kardex de un producto | `movements:read` | `READ` | [Ver](#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id) |
| 11 | `GET` | `/companies/{company_id}/inventory-operations/{operation_id}` | Operación por id | `movements:read` | `READ` | [Ver](#11-get-companiescompany_idinventory-operationsoperation_id) |
| 12 | `GET` | `/companies/{company_id}/inventory-operations/by-key/{operation_key}` | Operación por clave | `movements:read` | `READ` | [Ver](#12-get-companiescompany_idinventory-operationsby-keyoperation_key) |
| 13 | `GET` | `/companies/{company_id}/branches/{branch_id}/valuation` | Valor del inventario de la sucursal | `valuation:read` | `READ` | [Ver](#13-get-companiescompany_idbranchesbranch_idvaluation) |
| 14 | `GET` | `/companies/{company_id}/branches/{branch_id}/valuation/{company_product_id}/layers` | Capas FIFO de un producto | `valuation:read` | `READ` | [Ver](#14-get-companiescompany_idbranchesbranch_idvaluationcompany_product_idlayers) |
| 15 | `GET` | `/companies/{company_id}/inventory-movements/{movement_id}/cost-consumptions` | Consumos de capas de un movimiento | `valuation:read` | `READ` | [Ver](#15-get-companiescompany_idinventory-movementsmovement_idcost-consumptions) |
| 16 | `POST` | `/companies/{company_id}/inventory-adjustments` | Registrar y aplicar ajuste | `adjustments:create` + asignación | `HIGH_RISK` | [Ver](#16-post-companiescompany_idinventory-adjustments) |
| 17 | `GET` | `/companies/{company_id}/inventory-adjustments` | Listar ajustes | `adjustments:read` | `READ` | [Ver](#17-get-companiescompany_idinventory-adjustments) |
| 18 | `GET` | `/companies/{company_id}/inventory-adjustments/{adjustment_id}` | Ajuste por id | `adjustments:read` | `READ` | [Ver](#18-get-companiescompany_idinventory-adjustmentsadjustment_id) |
| 19 | `POST` | `/companies/{company_id}/inventory-counts` | Crear conteo (`DRAFT`) | `counts:create` + asignación | `WRITE` | [Ver](#19-post-companiescompany_idinventory-counts) |
| 20 | `GET` | `/companies/{company_id}/inventory-counts` | Listar conteos | `counts:read` | `READ` | [Ver](#20-get-companiescompany_idinventory-counts) |
| 21 | `POST` | `/companies/{company_id}/inventory-counts/{count_id}/start` | Iniciar conteo | `counts:create` + asignación | `WRITE` | [Ver](#21-post-companiescompany_idinventory-countscount_idstart) |
| 22 | `PUT` | `/companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}` | Registrar cantidad contada | `counts:create` + asignación | `WRITE` | [Ver](#22-put-companiescompany_idinventory-countscount_iddetailscompany_product_id) |
| 23 | `POST` | `/companies/{company_id}/inventory-counts/{count_id}/complete` | Completar conteo (aplica ajustes) | `counts:create` + asignación | `HIGH_RISK` | [Ver](#23-post-companiescompany_idinventory-countscount_idcomplete) |
| 24 | `POST` | `/companies/{company_id}/inventory-counts/{count_id}/cancel` | Cancelar conteo | `counts:create` + asignación | `WRITE` | [Ver](#24-post-companiescompany_idinventory-countscount_idcancel) |
| 25 | `GET` | `/companies/{company_id}/inventory-counts/{count_id}` | Conteo con detalles y ajustes | `counts:read` | `READ` | [Ver](#25-get-companiescompany_idinventory-countscount_id) |
| 26 | `GET` | `/companies/{company_id}/inventory-policy` | Política de la empresa | `company-policies:read` | `READ` | [Ver](#26-get-companiescompany_idinventory-policy) |
| 27 | `POST` | `/companies/{company_id}/inventory-policy` | Registrar política de la empresa | `company-policies:update` | `WRITE` | [Ver](#27-post-companiescompany_idinventory-policy) |
| 28 | `PUT` | `/companies/{company_id}/inventory-policy` | Actualizar política de la empresa | `company-policies:update` | `WRITE` | [Ver](#28-put-companiescompany_idinventory-policy) |
| 29 | `GET` | `/companies/{company_id}/inventory-policies` | Listar políticas de producto | `product-policies:read` | `READ` | [Ver](#29-get-companiescompany_idinventory-policies) |
| 30 | `POST` | `/companies/{company_id}/inventory-policies` | Crear política de producto | `product-policies:update` | `WRITE` | [Ver](#30-post-companiescompany_idinventory-policies) |
| 31 | `GET` | `/companies/{company_id}/inventory-policies/{policy_id}` | Política de producto por id | `product-policies:read` | `READ` | [Ver](#31-get-companiescompany_idinventory-policiespolicy_id) |
| 32 | `PUT` | `/companies/{company_id}/inventory-policies/{policy_id}` | Actualizar política de producto | `product-policies:update` | `WRITE` | [Ver](#32-put-companiescompany_idinventory-policiespolicy_id) |
| 33 | `POST` | `/companies/{company_id}/inventory-policies/{policy_id}/deactivate` | Inactivar política de producto | `product-policies:update` | `WRITE` | [Ver](#33-post-companiescompany_idinventory-policiespolicy_iddeactivate) |
| 34 | `POST` | `/companies/{company_id}/branches/{branch_id}/inventory-policies/lookup` | Política activa de hasta 100 productos | `product-policies:read` | `READ` | [Ver](#34-post-companiescompany_idbranchesbranch_idinventory-policieslookup) |
| 35 | `POST` | `/companies/{company_id}/inventory-product-sets` | Productos por estado de existencias y mínimo | `balances:read` + `product-policies:read` | `READ` | [Ver](#35-post-companiescompany_idinventory-product-sets) |
| 36 | `POST` | `/companies/{company_id}/inventory-summary` | Indicadores por sucursal y consolidados | `balances:read` + `product-policies:read` (+ `valuation:read`) | `READ` | [Ver](#36-post-companiescompany_idinventory-summary) |
| 37 | `GET` | `/companies/{company_id}/branches/{branch_id}/stock-evolution` | Evolución de existencias de una sucursal | `stock_evolution:read` | `READ` | [Ver](#37-get-companiescompany_idbranchesbranch_idstock-evolution) |
| 38 | `GET` | `/companies/{company_id}/stock-evolution` | Evolución consolidada | `stock_evolution:read` | `READ` | [Ver](#38-get-companiescompany_idstock-evolution) |

Todos los permisos empiezan por `perm:inventory:`. Las listas paginan con `page` (≥ 1) y `page_size` (1–100, por defecto 20; fuera de rango `422 PAGE_SIZE_OUT_OF_RANGE`).

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-inventory-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-inventory-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si la base de datos no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/health/ready'
```

### 3. `POST /inventory-entries`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · aumenta existencias y abre capas de costo |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/inventory-entries` |
| Permiso | `perm:inventory:entries:create` **y** token de cuenta de servicio |

**Para el frontend:** no usar. La invoca Purchase al recibir una compra. Se documenta para interpretar las operaciones y el kardex.

Cuerpo (`OperationIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `operation_key` | UUID | Sí | Clave de idempotencia (Purchase envía el `id` de su operación `RECEIVE`) |
| `company_id`, `branch_id` | UUID | Sí | Empresa y sucursal |
| `origin_type` | string | Sí | `PURCHASE` para entradas |
| `origin_id` | UUID | Sí | Compra de origen |
| `application_user_id` | UUID | Sí | Usuario operativo que recibió |
| `correlation_id` | UUID | Sí | Trazabilidad |
| `reason` | string \| null | No | ≤ 2000 |
| `lines[]` | array | Sí | 1 a 100 líneas (`LINES_OUT_OF_RANGE`), sin repetir producto |
| `lines[].origin_detail_id` | UUID | Sí | Línea de la compra |
| `lines[].company_product_id` | UUID | Sí | Producto con control de inventario (validado en Commercial Relationship) |
| `lines[].quantity` | number \| string | Sí | > 0, hasta 4 decimales, en unidad base |
| `lines[].unit_cost` | number \| string \| null | No | Costo por unidad base; si falta, la capa queda con `cost_known: false` |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/inventory-entries' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "origin_type": "PURCHASE",
    "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
    "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
    "reason": "Solicitud del cliente",
    "lines": [
      {
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "quantity": "2",
        "unit_cost": "500.00"
      }
    ]
  }'
```

Respuestas: `201` `InventoryOperationResponse` (`id`, `operation_key`, `operation_type: "ENTRY"`, `company_id`, `branch_id`, `origin_type`, `origin_id`, `application_user_id`, `correlation_id`, `reason`, `reverses_operation_id`, `reversed_by_operation_id`, `created_at`, `created_by`, `movements[]`, `balances[]` con los saldos resultantes); `200` sin cuerpo si la misma clave ya se aplicó; `409 OPERATION_KEY_CONFLICT`; `422 VALIDATION_ERROR` (`errors[].code`); `403 FORBIDDEN` (sin permiso o no es cuenta de servicio); `503` (`dependency`: `database`, `operational-context`, `commercial-relationship`).

Flujo verificado: formato → idempotencia (misma clave, mismo cliente y misma huella → resultado original sin tocar saldos) → validación de referencias con sus dueños fuera de transacción → transacción todo o nada.

### 4. `POST /inventory-entries/{operation_id}/reversal`

`HIGH_RISK` (resta las existencias de la entrada). URL `https://sio-inventory-dev.onrender.com/api/v1/inventory-entries/{operation_id}/reversal`; permiso `entries:create` + cuenta de servicio. Cuerpo (`ReversalIn`): `operation_key` (UUID), `company_id` (UUID, obligatorio: la operación original se busca dentro de esa empresa), `application_user_id`, `correlation_id`, `reason` (opcional). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/inventory-entries/1741498a-d933-4d84-899c-9b85ba801695/reversal' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
    "reason": "Solicitud del cliente"
  }'
```
Respuesta `201` con la operación `ENTRY_REVERSAL` (`reverses_operation_id` = la entrada). Errores: `404` (no existe en esa empresa o no es una entrada), `409 ALREADY_REVERSED`, `409 REVERSAL_NOT_ALLOWED` (es un reverso), `409 INSUFFICIENT_STOCK` (la mercancía ya salió), `409 ENTRY_LAYER_CONSUMED`, `409 OPERATION_KEY_CONFLICT`. Lo invoca Purchase al anular una compra recibida.

Ejemplo de respuesta `201` (`InventoryOperationResponse`; valores ilustrativos):

```json
{
  "id": "ded98412-e987-4448-858e-ae547e5f2cec",
  "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_type": "ENTRY",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "origin_type": "PURCHASE",
  "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "reason": "Solicitud del cliente",
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movements": [
    {
      "id": "b2d6ef5e-8b34-4dd8-85ec-4f473293561b",
      "line_index": 0,
      "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "2",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "balance_sequence": 7,
      "unit_cost": "500.00",
      "movement_value": null,
      "cost_known": true,
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "has_unknown_cost": false
    }
  ]
}
```

### 5. `POST /inventory-outputs`

`HIGH_RISK` (resta existencias; nunca deja saldo negativo). URL `https://sio-inventory-dev.onrender.com/api/v1/inventory-outputs`; permiso `outputs:create` + cuenta de servicio. Cuerpo: `OperationIn` con `origin_type: "SALE"`, `origin_id` = venta; `lines[].unit_cost` **no se admite** en salidas (el costo lo calcula FIFO). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/inventory-outputs' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "origin_type": "PURCHASE",
    "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
    "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
    "reason": "Solicitud del cliente",
    "lines": [
      {
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "quantity": "2",
        "unit_cost": "500.00"
      }
    ]
  }'
```
Respuesta `201` con la operación `OUTPUT` y, por movimiento, `unit_cost`/`movement_value` FIFO y `cost_known`. `409 INSUFFICIENT_STOCK` con `shortages`. Lo invoca Sales al confirmar.

Ejemplo de respuesta `201` (`InventoryOperationResponse`; valores ilustrativos):

```json
{
  "id": "c4d736a6-bd90-420f-828c-caab140ae775",
  "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_type": "ENTRY",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "origin_type": "PURCHASE",
  "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "reason": "Solicitud del cliente",
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movements": [
    {
      "id": "b2d6ef5e-8b34-4dd8-85ec-4f473293561b",
      "line_index": 0,
      "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "2",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "balance_sequence": 7,
      "unit_cost": "500.00",
      "movement_value": null,
      "cost_known": true,
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "has_unknown_cost": false
    }
  ]
}
```

### 6. `POST /inventory-outputs/{operation_id}/reversal`

`HIGH_RISK` (restituye existencias y capas). URL `https://sio-inventory-dev.onrender.com/api/v1/inventory-outputs/{operation_id}/reversal`; permiso `outputs:create` + cuenta de servicio. Cuerpo `ReversalIn`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/inventory-outputs/1741498a-d933-4d84-899c-9b85ba801695/reversal' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
    "reason": "Solicitud del cliente"
  }'
```
Respuesta `201` con la operación `OUTPUT_REVERSAL`. Errores: `404`, `409 ALREADY_REVERSED`, `REVERSAL_NOT_ALLOWED`, `OUTPUT_NOT_VALUED`, `OPERATION_KEY_CONFLICT`. Lo invoca Sales al anular una venta confirmada.

Ejemplo de respuesta `201` (`InventoryOperationResponse`; valores ilustrativos):

```json
{
  "id": "3d66d3e9-cf79-46f5-81f9-710f1696d721",
  "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_type": "ENTRY",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "origin_type": "PURCHASE",
  "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "reason": "Solicitud del cliente",
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movements": [
    {
      "id": "b2d6ef5e-8b34-4dd8-85ec-4f473293561b",
      "line_index": 0,
      "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "2",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "balance_sequence": 7,
      "unit_cost": "500.00",
      "movement_value": null,
      "cost_known": true,
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "has_unknown_cost": false
    }
  ]
}
```

### 7. `GET /companies/{company_id}/branches/{branch_id}/balances`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances` |
| Permiso | `perm:inventory:balances:read` |
| Alcance | Membresía en la empresa (cualquier sucursal) |

| Parámetro | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | [company_id](../parametros/company-id.md) |
| `branch_id` | ruta | UUID | Sí | [branch_id](../parametros/branch-id.md) |
| `page`, `page_size` | query | integer | No | — |
| `company_product_id` | query | UUID | No | [company_product_id](../parametros/company-product-id.md) |
| `in_stock_only` | query | boolean | No (`false`) | Solo saldos > 0 |

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances?in_stock_only=true' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`BalancePage`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "800.0000",
      "last_movement_at": "2026-10-19T16:00:02Z",
      "balance_sequence": 97,
      "inventory_value": "476000.00",
      "average_unit_cost": "595.00",
      "has_unknown_cost": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

`inventory_value` y `average_unit_cost` provienen de las capas FIFO abiertas; `has_unknown_cost: true` indica cantidades sin costo conocido.

### 8. `GET /companies/{company_id}/branches/{branch_id}/balances/{company_product_id}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}`; permiso `balances:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: un `BalanceResponse`; si el producto no tiene movimientos devuelve `quantity: "0"` (no `404`).

Ejemplo de respuesta `200` (`BalanceResponse`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "quantity": "2",
  "last_movement_at": "2026-10-19T15:04:05Z",
  "balance_sequence": 7,
  "inventory_value": "20000.00",
  "average_unit_cost": "500.00",
  "has_unknown_cost": false
}
```

### 9. `POST /companies/{company_id}/branches/{branch_id}/balances/lookup`

`READ` (consulta por `POST`). URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances/lookup`; permiso `balances:read`. Cuerpo (`BalanceLookupIn`): `{"company_product_ids": ["…"]}` con 1 a 100 UUID sin repetir. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances/lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_ids": [
      "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
    ]
  }'
```
Respuesta `200`: `{"items": [BalanceResponse, …]}`.

### 10. `GET /companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}` |
| Permiso | `perm:inventory:movements:read` |

Parámetros de consulta: `page`, `page_size`, `occurred_at_from`, `occurred_at_to` (date-time **con zona horaria**), `movement_type` (`PURCHASE_ENTRY`, `SALE_OUTPUT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`, `POSITIVE_ADJUSTMENT`, `NEGATIVE_ADJUSTMENT`), `origin_type` (`PURCHASE`, `SALE`, `ADJUSTMENT`, `COUNT`), `origin_id` (UUID de la compra, venta, ajuste o conteo).

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/kardex/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`KardexPage`) en **orden cronológico**; cada `KardexMovement`:

```json
{
  "id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
  "operation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
  "line_index": 0,
  "origin_detail_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "movement_type": "SALE_OUTPUT",
  "quantity": "2.0000",
  "previous_balance": "802.0000",
  "new_balance": "800.0000",
  "balance_sequence": 97,
  "unit_cost": "595.00",
  "movement_value": "1190.00",
  "cost_known": true,
  "reversed_movement_id": null,
  "origin_type": "SALE",
  "origin_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
  "reason": null,
  "created_at": "2026-10-19T16:00:02Z",
  "created_by": "8a7b6c5d-4e3f-4a2b-9c1d-0e9f8a7b6c5d"
}
```

### 11. `GET /companies/{company_id}/inventory-operations/{operation_id}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-operations/{operation_id}`; permiso `movements:read`. `operation_id` = `inventory_operation_id` de una venta o compra, u `operation_id` del kardex. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-operations/1741498a-d933-4d84-899c-9b85ba801695' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `InventoryOperationResponse` con sus movimientos; `404` si no es de la empresa.

Ejemplo de respuesta `200` (`InventoryOperationResponse`; valores ilustrativos):

```json
{
  "id": "1741498a-d933-4d84-899c-9b85ba801695",
  "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_type": "ENTRY",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "origin_type": "PURCHASE",
  "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "reason": "Solicitud del cliente",
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movements": [
    {
      "id": "b2d6ef5e-8b34-4dd8-85ec-4f473293561b",
      "line_index": 0,
      "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "2",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "balance_sequence": 7,
      "unit_cost": "500.00",
      "movement_value": null,
      "cost_known": true,
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "has_unknown_cost": false
    }
  ]
}
```

### 12. `GET /companies/{company_id}/inventory-operations/by-key/{operation_key}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-operations/by-key/{operation_key}`; permiso `movements:read`. Busca por la clave de operación (en Sales y Purchase, el `id` de la operación de confirmación, recepción o anulación). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-operations/by-key/cfaf2336-92a2-4ece-8f6c-d759523c7bda' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`; `404`.

Ejemplo de respuesta `200` (`InventoryOperationResponse`; valores ilustrativos):

```json
{
  "id": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_key": "cfaf2336-92a2-4ece-8f6c-d759523c7bda",
  "operation_type": "ENTRY",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "origin_type": "PURCHASE",
  "origin_id": "c78b92ae-ed94-43db-85d5-935f67baa62b",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "correlation_id": "d725508d-77ec-4d78-8adc-933ea0debbda",
  "reason": "Solicitud del cliente",
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movements": [
    {
      "id": "b2d6ef5e-8b34-4dd8-85ec-4f473293561b",
      "line_index": 0,
      "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "2",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "balance_sequence": 7,
      "unit_cost": "500.00",
      "movement_value": null,
      "cost_known": true,
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "has_unknown_cost": false
    }
  ]
}
```

### 13. `GET /companies/{company_id}/branches/{branch_id}/valuation`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/valuation`; permiso `valuation:read`; `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/valuation?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`BranchValuationResponse`): `items[]` con `company_product_id`, `quantity`, `inventory_value`, `average_unit_cost`, `open_layers`, `has_unknown_cost`; más `total_value`, `has_unknown_cost` (global), `page`, `page_size`, `total_records`. Valor calculado sobre las capas FIFO abiertas.

Ejemplo de respuesta `200` (`BranchValuationResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "2",
      "inventory_value": "20000.00",
      "average_unit_cost": "500.00",
      "open_layers": 1,
      "has_unknown_cost": false
    }
  ],
  "total_value": "20000.00",
  "has_unknown_cost": false,
  "page": 1,
  "page_size": 20,
  "total_records": 1
}
```

### 14. `GET /companies/{company_id}/branches/{branch_id}/valuation/{company_product_id}/layers`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/valuation/{company_product_id}/layers`; permiso `valuation:read`; `page`, `page_size`, `include_closed` (boolean, `false`). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/valuation/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/layers?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`LayersPage`): capas en orden FIFO con `id`, `layer_kind` (`ENTRY`, `ADJUSTMENT`, `OPENING`), `origin_movement_id`, `original_quantity`, `remaining_quantity`, `unit_cost`, `cost_known`, `currency_code`, `received_at`, `status` (`OPEN`, `CLOSED`).

Ejemplo de respuesta `200` (`LayersPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "layer_kind": "ENTRY",
      "origin_movement_id": null,
      "original_quantity": "100.0000",
      "remaining_quantity": "40.0000",
      "unit_cost": "500.00",
      "cost_known": true,
      "currency_code": "COP",
      "received_at": "2026-10-19T15:04:05Z",
      "status": "OPEN"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1
}
```

### 15. `GET /companies/{company_id}/inventory-movements/{movement_id}/cost-consumptions`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-movements/{movement_id}/cost-consumptions`; permiso `valuation:read`. `movement_id` = `id` de un movimiento del kardex. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-movements/c0855f58-5b2b-4a21-8581-afba55b0ed9a/cost-consumptions' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`CostConsumptionsResponse`): `movement_id` e `items[]` con `id`, `cost_layer_id`, `consumption_type` (`CONSUME`, `RESTORE`, `ENTRY_REVERSAL`), `quantity`, `unit_cost`, `cost_amount`, `cost_known`, `restores_consumption_id`. Explica de qué capas salió el costo de una salida.

Ejemplo de respuesta `200` (`CostConsumptionsResponse`; valores ilustrativos):

```json
{
  "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "cost_layer_id": "84826241-4ce4-4524-8879-4b4df5ad847f",
      "consumption_type": "CONSUME",
      "quantity": "2",
      "unit_cost": "500.00",
      "cost_amount": "500.00",
      "cost_known": true,
      "restores_consumption_id": null
    }
  ]
}
```

### 16. `POST /companies/{company_id}/inventory-adjustments`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · modifica existencias de inmediato (no hay borrador ni aprobación) |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments` |
| Permiso | `perm:inventory:adjustments:create` · usuario humano con asignación `ACTIVE` a la sucursal |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Cuerpo (`AdjustmentIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `adjustment_key` | UUID | Sí | Clave de idempotencia generada por el cliente (`crypto.randomUUID()`) | — |
| `branch_id` | UUID | Sí | Sucursal asignada al usuario | [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | Producto apto para movimientos (control de inventario, validado en Commercial Relationship) | [company_product_id](../parametros/company-product-id.md) |
| `adjustment_type` | `POSITIVE` \| `NEGATIVE` | Sí | — | — |
| `quantity` | number \| string | Sí | > 0, hasta 4 decimales, unidad base | — |
| `unit_cost` | number \| string \| null | Solo en positivos | Costo por unidad base (moneda de la empresa); **no se admite** en ajustes negativos (`422`) | — |
| `reason` | string | Sí | 1 a 2000 caracteres (`REASON_REQUIRED`) | — |

```json
{
  "adjustment_key": "c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "NEGATIVE",
  "quantity": "3",
  "reason": "Producto vencido retirado de la estantería"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "adjustment_key": "c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "adjustment_type": "NEGATIVE",
    "quantity": "3",
    "reason": "Producto vencido retirado de la estantería"
  }'
```

Respuesta `201` (`InventoryAdjustmentResponse`; valores ilustrativos):

```json
{
  "id": "d4e5f6a7-b8c9-4d0e-8f1a-2b3c4d5e6f7a",
  "operation_id": "e5f6a7b8-c9d0-4e1f-8a2b-3c4d5e6f7a8b",
  "movement_id": "f6a7b8c9-d0e1-4f2a-8b3c-4d5e6f7a8b9c",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "NEGATIVE",
  "quantity": "3.0000",
  "reason": "Producto vencido retirado de la estantería",
  "previous_balance": "800.0000",
  "new_balance": "797.0000",
  "unit_cost": "595.00",
  "adjustment_value": "1785.00",
  "inventory_count_id": null,
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "created_at": "2026-10-19T17:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movement": {
    "id": "f6a7b8c9-d0e1-4f2a-8b3c-4d5e6f7a8b9c",
    "line_index": 0,
    "origin_detail_id": "d4e5f6a7-b8c9-4d0e-8f1a-2b3c4d5e6f7a",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "movement_type": "NEGATIVE_ADJUSTMENT",
    "quantity": "3.0000",
    "previous_balance": "800.0000",
    "new_balance": "797.0000",
    "balance_sequence": 98,
    "unit_cost": "595.00",
    "movement_value": "1785.00",
    "cost_known": true,
    "reversed_movement_id": null
  }
}
```

Reglas (verificadas): idempotencia por `adjustment_key` ligada al usuario y a la huella de la solicitud (misma solicitud → `200` con el ajuste original); el usuario operativo sale de `operational-access?branch_id=`; un ajuste positivo abre una capa FIFO con el `unit_cost` dado; un negativo consume capas (costo FIFO). El ajuste y su evento de auditoría se escriben en la misma transacción. Errores: `403 BRANCH_ACCESS_DENIED` / `FORBIDDEN` (también si el token es de cuenta de servicio), `404`, `409 INSUFFICIENT_STOCK` (`shortages`), `409 OPERATION_KEY_CONFLICT`, `422` (`REASON_REQUIRED`, `QUANTITY_NOT_POSITIVE`, costo en negativo, producto sin control de inventario), `503`.

### 17. `GET /companies/{company_id}/inventory-adjustments`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments`; permiso `adjustments:read`. Parámetros: `page`, `page_size`, `branch_id`, `company_product_id`, `adjustment_type`, `inventory_count_id` (UUID; ajustes generados por un conteo), `created_at_from`, `created_at_to` (date-time con zona). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`AdjustmentPage`), **más recientes primero**.

Ejemplo de respuesta `200` (`AdjustmentPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "593dcd21-669d-4884-8c5a-f8d535094bb1",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 18. `GET /companies/{company_id}/inventory-adjustments/{adjustment_id}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments/{adjustment_id}`; permiso `adjustments:read`. `200` con `InventoryAdjustmentResponse`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments/63659f3c-7eab-4ac4-8096-66eea4640a6c' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`InventoryAdjustmentResponse`; valores ilustrativos):

```json
{
  "id": "63659f3c-7eab-4ac4-8096-66eea4640a6c",
  "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
  "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "POSITIVE",
  "quantity": "2",
  "reason": "Solicitud del cliente",
  "previous_balance": "42.0000",
  "new_balance": "40.0000",
  "unit_cost": "500.00",
  "adjustment_value": "2",
  "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movement": {
    "id": "d0d5400d-f318-4a70-88b1-855ae33273c6",
    "line_index": 0,
    "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "movement_type": "PURCHASE_ENTRY",
    "quantity": "2",
    "previous_balance": "42.0000",
    "new_balance": "40.0000",
    "balance_sequence": 7,
    "unit_cost": "500.00",
    "movement_value": null,
    "cost_known": true,
    "reversed_movement_id": null
  }
}
```

### 19. `POST /companies/{company_id}/inventory-counts`

| | |
|---|---|
| Clasificación | `WRITE` · crea el conteo en `DRAFT` (sin efectos en existencias) |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts` |
| Permiso | `perm:inventory:counts:create` · usuario humano asignado a la sucursal |

Cuerpo (`CountCreateIn`): `branch_id` (UUID, obligatorio), `observations` (≤ 2000, opcional).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "observations": "Entrega en mostrador"
  }'
```

Respuesta `201` (`InventoryCountResponse`): `id` (`count_id`), `company_id`, `branch_id`, `status` (`DRAFT`), `started_by_user_id`, `started_at`, `completed_by_user_id`, `completed_at`, `cancelled_by_user_id`, `cancelled_at`, `cancel_reason`, `operation_id` (ajuste aplicado al completar), `observations`, `version`, trazabilidad, `details[]` y `adjustments[]` (en la consulta individual).

Ejemplo de respuesta `201` (`InventoryCountResponse`; valores ilustrativos):

```json
{
  "id": "89225d31-90a0-4369-8062-15496f5e0e8d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "DRAFT",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": null,
  "completed_by_user_id": null,
  "completed_at": "2026-10-19T17:00:00Z",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Entrega en mostrador",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": [
    {
      "id": "dbd0569c-4940-4d28-864b-c5ce87b0f524",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "89225d31-90a0-4369-8062-15496f5e0e8d",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "66ebe298-81db-4f9f-8d7b-ddedd8d84e33",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

Ciclo de vida: `DRAFT` → `IN_PROGRESS` (operación 21) → `COMPLETED` (23) o `CANCELLED` (24, desde `DRAFT` o `IN_PROGRESS`). Solo puede haber **un conteo en curso por sucursal** (`409 COUNT_ALREADY_IN_PROGRESS`).

### 20. `GET /companies/{company_id}/inventory-counts`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts`; permiso `counts:read`. Parámetros: `page`, `page_size`, `branch_id`, `status` (`DRAFT`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`CountPage`) sin `details` ni `adjustments`.

Ejemplo de respuesta `200` (`CountPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "status": "COMPLETED",
      "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "started_at": "2026-10-19T15:04:05Z",
      "completed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "completed_at": "2026-10-19T17:00:00Z",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancel_reason": null,
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "observations": "Entrega en mostrador",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_at": "2026-10-19T15:04:05Z",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "details": [
        {
          "id": "6904cc55-8e0e-4ceb-8b99-6de1834d6ad0",
          "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
          "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
          "system_quantity_snapshot": "42.0000",
          "counted_quantity": "40",
          "difference_quantity": "-2.0000",
          "unit_cost": "500.00",
          "inventory_adjustment_id": null,
          "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
          "counted_at": "2026-10-19T15:04:05Z"
        }
      ],
      "adjustments": [
        {
          "id": "be386630-3c9e-4ac5-88d2-8b642efca8d9",
          "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
          "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
          "company_id": "550e8400-e29b-41d4-a716-446655440000",
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
          "adjustment_type": "POSITIVE",
          "quantity": "2",
          "reason": "Solicitud del cliente",
          "previous_balance": "42.0000",
          "new_balance": "40.0000",
          "unit_cost": "500.00",
          "adjustment_value": "2",
          "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
          "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
          "created_at": "2026-10-19T15:04:05Z",
          "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
          "movement": {
            "id": "222e7d2a-1a48-4770-8887-64c4bd34f456",
            "line_index": 0,
            "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
            "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
            "movement_type": "PURCHASE_ENTRY",
            "quantity": "2",
            "previous_balance": "42.0000",
            "new_balance": "40.0000",
            "balance_sequence": 7,
            "unit_cost": "500.00",
            "movement_value": null,
            "cost_known": true,
            "reversed_movement_id": null
          }
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

### 21. `POST /companies/{company_id}/inventory-counts/{count_id}/start`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/start`; permiso `counts:create` + asignación. Cuerpo (`CountTransitionIn`): `{"version": 1}`. Pasa a `IN_PROGRESS` y fija `started_at`. Errores: `409 COUNT_ALREADY_IN_PROGRESS` (otro conteo en curso en la sucursal), `409 INVALID_COUNT_TRANSITION`, `409 VERSION_CONFLICT`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/6241dbc0-4ff0-4591-8380-e0115fb8e1b7/start' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`InventoryCountResponse`; valores ilustrativos):

```json
{
  "id": "6241dbc0-4ff0-4591-8380-e0115fb8e1b7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "IN_PROGRESS",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-19T15:04:05Z",
  "completed_by_user_id": null,
  "completed_at": "2026-10-19T17:00:00Z",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Entrega en mostrador",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": [
    {
      "id": "dbd0569c-4940-4d28-864b-c5ce87b0f524",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "66ebe298-81db-4f9f-8d7b-ddedd8d84e33",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

### 22. `PUT /companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}`; permiso `counts:create` + asignación. Solo con el conteo `IN_PROGRESS` (`409 COUNT_NOT_IN_PROGRESS`). Cuerpo (`CountDetailIn`): `counted_quantity` (≥ 0, puede ser 0, hasta 4 decimales; obligatorio), `unit_cost` (opcional; costo por unidad base para la capa que abriría una diferencia positiva). Registrar de nuevo el mismo producto **reemplaza** la cantidad. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/6241dbc0-4ff0-4591-8380-e0115fb8e1b7/details/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "counted_quantity": "40",
    "unit_cost": "500.00"
  }'
```
Respuesta `200` (`InventoryCountDetailResponse`): `id`, `inventory_count_id`, `company_product_id`, `system_quantity_snapshot` (saldo del sistema al registrar), `counted_quantity`, `difference_quantity`, `unit_cost`, `inventory_adjustment_id` (tras completar), `counted_by_user_id`, `counted_at`.

Ejemplo de respuesta `200` (`InventoryCountDetailResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "system_quantity_snapshot": "42.0000",
  "counted_quantity": "40",
  "difference_quantity": "-2.0000",
  "unit_cost": "500.00",
  "inventory_adjustment_id": null,
  "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "counted_at": "2026-10-19T15:04:05Z"
}
```

### 23. `POST /companies/{company_id}/inventory-counts/{count_id}/complete`

`HIGH_RISK` · aplica **todas** las diferencias como ajustes, todo o nada. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/complete`; permiso `counts:create` + asignación. Cuerpo (`CountCompleteIn`): `completion_key` (UUID de idempotencia) y `version`. Reglas (verificadas): una sola operación `ADJUSTMENT` con origen `COUNT` y una línea por diferencia distinta de cero calculada **sobre el saldo vigente** en ese momento; crea un ajuste por línea y cierra el conteo en una transacción. Un conteo sin diferencias se completa sin operación. Repetir con la misma clave y versión devuelve el conteo. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/6241dbc0-4ff0-4591-8380-e0115fb8e1b7/complete' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "completion_key": "3b73766e-ca70-454b-8fe4-39c811427b76",
    "version": 1
  }'
```
Respuesta `200` con `status: "COMPLETED"`, `operation_id` y `adjustments[]`. Errores: `409 COUNT_NOT_IN_PROGRESS`, `409 INSUFFICIENT_STOCK` (una diferencia negativa mayor que el saldo vigente), `409 VERSION_CONFLICT`, `409 OPERATION_KEY_CONFLICT`.

Ejemplo de respuesta `200` (`InventoryCountResponse`; valores ilustrativos):

```json
{
  "id": "6241dbc0-4ff0-4591-8380-e0115fb8e1b7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "COMPLETED",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-19T15:04:05Z",
  "completed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "completed_at": "2026-10-19T17:00:00Z",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
  "observations": "Entrega en mostrador",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [
    {
      "id": "c57c6082-948e-470d-8d13-27d3263a86e8",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "system_quantity_snapshot": "42.0000",
      "counted_quantity": "40",
      "difference_quantity": "-2.0000",
      "unit_cost": "500.00",
      "inventory_adjustment_id": null,
      "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "counted_at": "2026-10-19T15:04:05Z"
    }
  ],
  "adjustments": [
    {
      "id": "dbd0569c-4940-4d28-864b-c5ce87b0f524",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "66ebe298-81db-4f9f-8d7b-ddedd8d84e33",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

### 24. `POST /companies/{company_id}/inventory-counts/{count_id}/cancel`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/cancel`; permiso `counts:create` + asignación. Cuerpo (`CountCancelIn`): `reason` (1–2000, obligatorio) y `version`. Desde `DRAFT` o `IN_PROGRESS`; no afecta existencias. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/6241dbc0-4ff0-4591-8380-e0115fb8e1b7/cancel' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "reason": "Solicitud del cliente",
    "version": 1
  }'
```
Respuesta `200` con `status: "CANCELLED"`, `cancel_reason`, `cancelled_at`.

Ejemplo de respuesta `200` (`InventoryCountResponse`; valores ilustrativos):

```json
{
  "id": "6241dbc0-4ff0-4591-8380-e0115fb8e1b7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "CANCELLED",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": null,
  "completed_by_user_id": null,
  "completed_at": "2026-10-19T17:00:00Z",
  "cancelled_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_at": "2026-10-19T16:00:00Z",
  "cancel_reason": "Conteo duplicado",
  "operation_id": null,
  "observations": "Entrega en mostrador",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": [
    {
      "id": "dbd0569c-4940-4d28-864b-c5ce87b0f524",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "66ebe298-81db-4f9f-8d7b-ddedd8d84e33",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

### 25. `GET /companies/{company_id}/inventory-counts/{count_id}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}`; permiso `counts:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/6241dbc0-4ff0-4591-8380-e0115fb8e1b7' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: conteo con `details[]` y, si está completado, `adjustments[]`.

Ejemplo de respuesta `200` (`InventoryCountResponse`; valores ilustrativos):

```json
{
  "id": "6241dbc0-4ff0-4591-8380-e0115fb8e1b7",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "COMPLETED",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-19T15:04:05Z",
  "completed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "completed_at": "2026-10-19T17:00:00Z",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
  "observations": "Entrega en mostrador",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [
    {
      "id": "c57c6082-948e-470d-8d13-27d3263a86e8",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "system_quantity_snapshot": "42.0000",
      "counted_quantity": "40",
      "difference_quantity": "-2.0000",
      "unit_cost": "500.00",
      "inventory_adjustment_id": null,
      "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "counted_at": "2026-10-19T15:04:05Z"
    }
  ],
  "adjustments": [
    {
      "id": "dbd0569c-4940-4d28-864b-c5ce87b0f524",
      "operation_id": "1741498a-d933-4d84-899c-9b85ba801695",
      "movement_id": "c0855f58-5b2b-4a21-8581-afba55b0ed9a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "POSITIVE",
      "quantity": "2",
      "reason": "Solicitud del cliente",
      "previous_balance": "42.0000",
      "new_balance": "40.0000",
      "unit_cost": "500.00",
      "adjustment_value": "2",
      "inventory_count_id": "f4843c35-6633-44a7-888e-2c8ef44ff8b4",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "66ebe298-81db-4f9f-8d7b-ddedd8d84e33",
        "line_index": 0,
        "origin_detail_id": "0e888eb9-c5b9-44fd-8c94-cd75b4fa9a65",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "PURCHASE_ENTRY",
        "quantity": "2",
        "previous_balance": "42.0000",
        "new_balance": "40.0000",
        "balance_sequence": 7,
        "unit_cost": "500.00",
        "movement_value": null,
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

### 26. `GET /companies/{company_id}/inventory-policy`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policy`; permiso `company-policies:read`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policy' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`CompanyPolicyResponse`): `id` (null si no registrada), `company_id`, `inventory_system` (`PERPETUAL` \| `PERIODIC`), `valuation_method` (`FIFO`), `replenishment_strategy` (`STANDARD` \| `JIT`), `is_active`, `version`, `registered` (`false` si la empresa aún no registró política; en ese caso el servicio devuelve `id: null`, `inventory_system: "PERPETUAL"`, `valuation_method: "FIFO"`, `replenishment_strategy: "STANDARD"`, `is_active: true`, `version: null` y trazabilidad nula; verificado en el código), trazabilidad.

Ejemplo de respuesta `200` (`CompanyPolicyResponse`; valores ilustrativos):

```json
{
  "id": "8fa0e8c5-e16c-4dd8-8fad-a62d4e6a735b",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "STANDARD",
  "is_active": true,
  "version": 1,
  "registered": true,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 27. `POST /companies/{company_id}/inventory-policy`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policy`; permiso `company-policies:update`; usuario humano con membresía. Cuerpo (`CompanyPolicyIn`): `inventory_system` (`PERPETUAL` \| `PERIODIC`, obligatorio), `valuation_method` (opcional, solo se acepta `FIFO`), `replenishment_strategy` (`STANDARD` \| `JIT`, obligatorio). Una por empresa (`409 POLICY_ALREADY_EXISTS`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policy' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "inventory_system": "PERPETUAL",
    "valuation_method": "FIFO",
    "replenishment_strategy": "STANDARD"
  }'
```
Respuesta `201`. Solo configuración: `PERIODIC` y `JIT` se guardan sin cambiar el motor.

Ejemplo de respuesta `201` (`CompanyPolicyResponse`; valores ilustrativos):

```json
{
  "id": "07a94e2d-2391-4601-8fc8-05fbaac23d16",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "STANDARD",
  "is_active": true,
  "version": 1,
  "registered": true,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 28. `PUT /companies/{company_id}/inventory-policy`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policy`; permiso `company-policies:update`. Cuerpo (`CompanyPolicyUpdateIn`): los campos de la operación 27 más `version`. `409 VERSION_CONFLICT`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policy' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "inventory_system": "PERPETUAL",
    "valuation_method": "FIFO",
    "replenishment_strategy": "STANDARD",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyPolicyResponse`; valores ilustrativos):

```json
{
  "id": "769b9f3f-84ec-4b2d-8130-78dfbb7810e6",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "STANDARD",
  "is_active": true,
  "version": 1,
  "registered": true,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 29. `GET /companies/{company_id}/inventory-policies`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies`; permiso `product-policies:read`. Parámetros: `page`, `page_size`, `branch_id`, `company_product_id`, `is_active`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`ProductPolicyPage`): `items[]` con `id`, `company_id`, `branch_id`, `company_product_id`, `minimum_stock`, `target_stock`, `service_level`, `safety_stock_method` (`BASIC` \| `STATISTICAL`), `calculation_window_days`, `replenishment_mode` (`MANUAL` \| `AUTO_DRAFT`), `auto_purchase_enabled`, `is_active`, `version`, trazabilidad.

Ejemplo de respuesta `200` (`ProductPolicyPage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "minimum_stock": "10",
      "target_stock": null,
      "service_level": null,
      "safety_stock_method": "BASIC",
      "calculation_window_days": 30,
      "replenishment_mode": "MANUAL",
      "auto_purchase_enabled": true,
      "is_active": true,
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_at": "2026-10-19T15:04:05Z",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 30. `POST /companies/{company_id}/inventory-policies`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies`; permiso `product-policies:update`; usuario humano con membresía. Cuerpo (`ProductPolicyIn`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `branch_id` | UUID | Sí | [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | [company_product_id](../parametros/company-product-id.md) |
| `minimum_stock` | number \| string \| null | No | `0`; unidad base |
| `target_stock` | number \| string \| null | No | — |
| `service_level` | number \| string \| null | No | — |
| `safety_stock_method` | `BASIC` \| `STATISTICAL` | Sí | — |
| `calculation_window_days` | integer | No | 90 |
| `replenishment_mode` | `MANUAL` \| `AUTO_DRAFT` | Sí | `AUTO_DRAFT` solo se guarda; no genera compras |
| `auto_purchase_enabled` | boolean | No | `false`; solo configuración |

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "300",
  "target_stock": "1000",
  "safety_stock_method": "BASIC",
  "replenishment_mode": "MANUAL"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "minimum_stock": "300",
    "target_stock": "1000",
    "safety_stock_method": "BASIC",
    "replenishment_mode": "MANUAL"
  }'
```

Una sola política **activa** por producto y sucursal (`409 ACTIVE_POLICY_EXISTS`). Respuesta `201` (`ProductPolicyResponse`). El `minimum_stock` es el que usan `minimum_state`, los productos bajo mínimo de Product Inventory Query y los indicadores del resumen. `service_level` (decimal opcional) y `calculation_window_days` (entero, por defecto 90) no tienen validación de rango en el contrato (verificado en el código): el frontend debe acotarlos (por ejemplo 0–1 y ≥ 1).

Ejemplo de respuesta `201` (`ProductPolicyResponse`; valores ilustrativos):

```json
{
  "id": "c75c5e43-70bc-403c-83bc-6144888086f6",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "10",
  "target_stock": null,
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 30,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": true,
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 31. `GET /companies/{company_id}/inventory-policies/{policy_id}`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies/{policy_id}`; permiso `product-policies:read`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`ProductPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "10",
  "target_stock": null,
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 30,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": true,
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 32. `PUT /companies/{company_id}/inventory-policies/{policy_id}`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies/{policy_id}`; permiso `product-policies:update`. Cuerpo (`ProductPolicyUpdateIn`): los campos de la operación 30 salvo `branch_id` y `company_product_id`, más `version`. `409 VERSION_CONFLICT`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "minimum_stock": "10",
    "safety_stock_method": "BASIC",
    "calculation_window_days": 30,
    "replenishment_mode": "MANUAL",
    "auto_purchase_enabled": true,
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ProductPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "10",
  "target_stock": null,
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 30,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": true,
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 33. `POST /companies/{company_id}/inventory-policies/{policy_id}/deactivate`

`WRITE`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies/{policy_id}/deactivate`; permiso `product-policies:update`. Cuerpo `{"version": n}`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```
Respuesta `200` con `is_active: false`; el producto deja de tener mínimo (`NO_POLICY`).

Ejemplo de respuesta `200` (`ProductPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "10",
  "target_stock": null,
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 30,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": true,
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-19T15:04:05Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

### 34. `POST /companies/{company_id}/branches/{branch_id}/inventory-policies/lookup`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-policies/lookup`; permiso `product-policies:read`. Cuerpo (`PolicyLookupIn`): `{"company_product_ids": [...]}` (1–100, sin repetir). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/inventory-policies/lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_ids": [
      "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
    ]
  }'
```
Respuesta `200` (`PolicyLookupResponse`): `items[]` con `company_product_id` y `policy` (`{"id", "minimum_stock", "status": "ACTIVE"}` o `null`).

### 35. `POST /companies/{company_id}/inventory-product-sets`

`READ` (consulta por `POST`; la usa Product Inventory Query para filtrar por existencias y mínimos). URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-product-sets`; permisos `balances:read` **y** `product-policies:read`. Cuerpo (`ProductSetsIn`): `branch_ids` (1–100 UUID, sin repetir, obligatorio), `stock_state` (`IN_STOCK` \| null), `minimum_state` (`BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM`, `WITH_POLICY` \| null), `unit` (`PRODUCTS` por defecto; `PAIRS` solo con `BELOW_MINIMUM`), `after` (posición `{"k": [...], "id": "…", "branch_id": "…"}` devuelta antes, para paginar), `limit` (1–100, obligatorio). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-product-sets' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_ids": [
      "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    ],
    "minimum_state": "BELOW_MINIMUM",
    "unit": "PRODUCTS",
    "limit": 20
  }'
```
Respuesta `200` (`ProductSetsResponse`): `items[]` (productos en orden `company_product_id`, o pares producto–sucursal por faltante descendente) y `has_more`. Reglas: `IN_STOCK` = suma de las sucursales pedidas > 0; `minimum_state` se cumple si al menos una sucursal tiene ese estado (un par sin saldo cuenta con 0). Sin costos. `ProductSetItem` = `{company_product_id, position}` y `PairSetItem` = `{company_product_id, branch_id, base_quantity, minimum_stock, shortfall, position}`, con cantidades como cadenas decimales y `position` como cursor *keyset* opaco que se reenvía en `after` (verificado en el código; la consume Product Inventory Query, no el frontend).

Ejemplo de respuesta `200` (`ProductSetsResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "position": {
        "k": [
          "display_name"
        ],
        "id": "6bc29f47-1f6c-4e62-84b4-5f482cd9ba49",
        "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
      }
    }
  ],
  "has_more": false
}
```

### 36. `POST /companies/{company_id}/inventory-summary`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-summary`; permisos `balances:read` **y** `product-policies:read`; con `include_valuation: true` además `valuation:read` (si falta, `403`). Cuerpo (`InventorySummaryIn`): `branch_ids` (1–100, obligatorio), `include_valuation` (boolean, `false`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-summary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_ids": [
      "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    ],
    "include_valuation": false
  }'
```
Respuesta `200` (`InventorySummaryResponse`):

```json
{
  "branches": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "products_with_positive_balance": 280,
      "products_with_zero_balance": 15,
      "products_with_policy": 120,
      "products_below_minimum": 9,
      "inventory_value": "152300000.00"
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 280,
    "products_with_zero_balance": 15,
    "products_with_policy": 120,
    "products_below_minimum": 9,
    "inventory_value": "152300000.00"
  }
}
```

Una sola consulta agregada sobre saldos y políticas, sin límite de productos y sin filtrar por estado comercial; `inventory_value` solo con `include_valuation` y el permiso.

### 37. `GET /companies/{company_id}/branches/{branch_id}/stock-evolution`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/stock-evolution` |
| Permiso | `perm:inventory:stock_evolution:read` (solo esta consulta; no da acceso a kardex ni costos) |

| Parámetro | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `from`, `to` | date-time **con zona horaria** | Sí | Período `[from, to)` de hasta 366 días |
| `company_product_id` | UUID, repetible | No | Máx. 100 |
| `page`, `page_size` | integer | No | 1–100 |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/stock-evolution?from=2026-10-01T00:00:00Z&to=2026-10-19T23:59:59Z&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`StockEvolutionPage`): `company_id`, `branch_id`, `from`, `to`, `items[]` (por producto, en unidad base: `opening_quantity`, `entries`, `outputs`, `entry_reversals`, `output_reversals`, `positive_adjustments`, `negative_adjustments`, `closing_quantity`, `movement_count`) y paginación. Se cumple `closing = opening + entries − outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments`. Incluye productos con movimientos en el período o saldo inicial positivo, en orden `company_product_id`. **Sin costos.** Lo consume Business Reporting.

Ejemplo de respuesta `200` (`StockEvolutionPage`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "from": "2026-10-01T00:00:00Z",
  "to": "2026-10-19T23:59:59Z",
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "opening_quantity": "0.0000",
      "entries": "120.0000",
      "outputs": "80.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "0.0000",
      "positive_adjustments": "0.0000",
      "negative_adjustments": "0.0000",
      "closing_quantity": "40.0000",
      "movement_count": 3,
      "branch_count": 2
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 38. `GET /companies/{company_id}/stock-evolution`

`READ`. URL `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/stock-evolution`; permiso `stock_evolution:read`. Como la operación 37, sumando por producto las sucursales de `branch_id` (**obligatorio**, repetible, 1–100). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/stock-evolution?from=2026-10-01T00:00:00Z&to=2026-10-19T23:59:59Z&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`ConsolidatedStockEvolutionPage`) con `branch_ids` y, por producto, `branch_count` (sucursales que aportan). Nunca suma productos distintos. Sucursales que no son de la empresa no aportan filas.

Ejemplo de respuesta `200` (`ConsolidatedStockEvolutionPage`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_ids": [
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ],
  "from": "2026-10-01T00:00:00Z",
  "to": "2026-10-19T23:59:59Z",
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "opening_quantity": "0.0000",
      "entries": "120.0000",
      "outputs": "80.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "0.0000",
      "positive_adjustments": "0.0000",
      "negative_adjustments": "0.0000",
      "closing_quantity": "40.0000",
      "movement_count": 3,
      "branch_count": 2
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 INVENTORY.FORBIDDEN` en entradas o salidas | Token de usuario en rutas de cuentas de servicio | No usarlas desde el frontend |
| `403 INVENTORY.FORBIDDEN` en ajustes o conteos | Token de cuenta de servicio, o sin permiso | Usar un usuario humano del grupo `inventario` |
| `403 INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignada la sucursal | Asignarla en Operational Context |
| `404 INVENTORY.NOT_FOUND` | Sin membresía, recurso de otra empresa o inexistente | Revisar `company_id` |
| `409 INVENTORY.INSUFFICIENT_STOCK` (`shortages`) | Saldo insuficiente | Mostrar faltantes por producto |
| `409 INVENTORY.OPERATION_KEY_CONFLICT` | Misma clave con otro contenido | Generar clave nueva por operación |
| `409 INVENTORY.COUNT_ALREADY_IN_PROGRESS` / `COUNT_NOT_IN_PROGRESS` / `INVALID_COUNT_TRANSITION` | Estado del conteo | Consultar el conteo y respetar el ciclo |
| `409 INVENTORY.POLICY_ALREADY_EXISTS` / `ACTIVE_POLICY_EXISTS` | Política duplicada | Actualizar la existente |
| `422 PAGE_SIZE_OUT_OF_RANGE` / `REASON_REQUIRED` / `QUANTITY_NOT_POSITIVE` | Validación | Corregir el campo |
| `503` con `dependency` `operational-context` o `commercial-relationship` | Dependencia caída | Reintentar |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía y asignación a la sucursal (con el token del usuario); datos de empresa y sucursal con la cuenta técnica |
| Commercial Relationship | Verificar que el producto es de la empresa y tiene control de inventario; moneda de la empresa |
| Purchase, Sales | Emisores de entradas, salidas y reversos (cuentas de servicio) |
| Audit | Eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 38 |
| Operaciones documentadas | 38 |
| Permisos contrastados con el código | Sí (`api/entries.py`, `outputs.py`, `queries.py`, `valuation.py`, `adjustments.py`, `counts.py`, `policies.py`, `inventory_reads.py`, `stock_evolution.py`, `identity.py`) |
| Esquemas contrastados | Sí (`api/schemas/*.py`, `domain/balance_math.py`, `domain/fifo.py`, `infrastructure/models.py`) |
| Verificado | Política de empresa no registrada: `PERPETUAL`/`FIFO`/`STANDARD`, `is_active: true`, `version: null`; `service_level` y `calculation_window_days` sin validación de rango; `ProductSetItem`/`PairSetItem` documentados en la operación 35 |

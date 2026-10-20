# Business Reporting API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Business Reporting genera, **bajo demanda y solo en lectura**, cuatro reportes de negocio por empresa o por sucursal: productos más vendidos, ventas por sucursal, compras del período y evolución de existencias. Cada reporte existe en dos rutas (empresa y sucursal) y puede devolverse en JSON o descargarse en CSV. No almacena datos propios: consulta Sales, Purchase, Inventory, Commercial Relationship, Product Catalog y Operational Context en cada solicitud.

## Responsabilidad

- Autorizar el alcance con Operational Context (membresía `ACTIVE`, sucursales de la empresa) antes de consultar cualquier otro servicio.
- Agregar la información de los servicios propietarios **con el token del usuario**: el usuario necesita el permiso del reporte y el permiso de lectura del servicio propietario.
- Entregar reportes consistentes: nunca parciales; si una dependencia falla, responde `503`.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-business-reporting-dev.onrender.com/api/v1` |
| Salud | `https://sio-business-reporting-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-business-reporting-dev.onrender.com/docs) · [/openapi.json](https://sio-business-reporting-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `BUSINESS_REPORTING.*` y `trace_id` |
| Operaciones en el contrato desplegado | 10 (8 reportes + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/business-reporting-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Cada reporte exige **dos permisos**: el del reporte (lo evalúa Business Reporting) y el de lectura del servicio propietario (lo evalúa ese servicio cuando Business Reporting le reenvía el token del usuario). Si falta el segundo, la respuesta también es `403 BUSINESS_REPORTING.FORBIDDEN`.

| Reporte | Permiso del reporte | Permiso del propietario | Grupos de la plantilla que tienen ambos |
|---|---|---|---|
| Productos más vendidos | `perm:business-reporting:top_selling_products:read` | `perm:sales:sales:read` (Sales) | `administradores`, `supervisores`, `ventas`, `reportes` |
| Ventas por sucursal | `perm:business-reporting:sales_by_branch:read` | `perm:sales:sales:read` | `administradores`, `supervisores`, `reportes` |
| Compras | `perm:business-reporting:purchases:read` | `perm:purchase:purchases:read` (Purchase) | `administradores`, `supervisores`, `compras`, `reportes` |
| Evolución de existencias | `perm:business-reporting:stock_evolution:read` | `perm:inventory:stock_evolution:read` (Inventory) | `administradores`, `supervisores`, `inventario`, `reportes` |

El grupo `consulta` no tiene permisos de Business Reporting en la plantilla.

## Alcance de datos

| Regla | Detalle |
|---|---|
| Empresa | El usuario debe tener membresía `ACTIVE` en `company_id`; si no, o si la empresa no existe, `404 BUSINESS_REPORTING.NOT_FOUND` (sin distinguir el caso) |
| Sucursales en rutas de empresa | Sin `branch_id`: todas las sucursales `ACTIVE` de la empresa (en compras y existencias también las inactivas, que pueden conservar datos). Con `branch_id` (repetible, máx. 100): esas sucursales, que deben pertenecer a la empresa (`404` si alguna no) |
| Rutas por sucursal | `branch_id` va en la ruta; debe ser de la empresa (`404` si no). No se admite `branch_id` por consulta (`422`) |
| Asignación a la sucursal | **No se exige** que el usuario tenga asignada la sucursal: con membresía y permisos puede consultar cualquier sucursal de la empresa |

## Parámetros comunes a los ocho reportes

| Parámetro | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `company_id` | ruta | UUID | Sí | Membresía `ACTIVE` | [company_id](../parametros/company-id.md) |
| `branch_id` | ruta (rutas por sucursal) o query repetible (rutas de empresa; máx. 100) | UUID | Según la ruta | De la empresa | [branch_id](../parametros/branch-id.md) |
| `date_from` | query | date `YYYY-MM-DD` | Sí | — | — |
| `date_to` | query | date `YYYY-MM-DD` | Sí | ≥ `date_from` (`INVALID_DATE_RANGE`); período ≤ 366 días (`PERIOD_TOO_LONG`); no posterior a hoy en la zona horaria de la empresa (`DATE_IN_FUTURE`) | — |
| `format` | query | `json` \| `csv` | No (`json`) | — | — |
| `bom` | query | boolean | No (`true`) | Solo afecta a CSV: antepone la marca de orden de bytes UTF-8 para Excel | — |

Todos los `422` de período llegan como `BUSINESS_REPORTING.VALIDATION_ERROR` con `errors[]` (`field`, `message`, `code`).

### Respuesta JSON común

Todos los reportes incluyen: `report` (nombre del reporte), `company_id`, `date_from`, `date_to`, `generated_at` (date-time), `criteria` (objeto con los parámetros aplicados; verificado en el código: productos más vendidos `{sales_status: "CONFIRMED", date_basis: "operation_date", rank_by}`, ventas por sucursal `{sales_status: "CONFIRMED", date_basis: "operation_date"}`, compras `{date_basis: "operation_date", categories: [...]}`, evolución de existencias `{date_basis: "created_at", from, to, consolidation: "by_product"}`) y, según la ruta, `branch_ids` (empresa) o `branch_id`, `branch_code`, `branch_name` (sucursal). Los importes y cantidades son **cadenas decimales** (por ejemplo `"1250000.00"`), nunca números flotantes.

### Descarga CSV

Con `format=csv` la respuesta es `text/csv; charset=utf-8` con cabecera `Content-Disposition: attachment; filename="<reporte>-<company_id>-<date_from>-<date_to>.csv"` (las rutas por sucursal añaden el `branch_id` al nombre). Separador coma, fin de línea CRLF, misma información que el JSON. En compras y existencias el CSV incluye **todas las páginas**, con un máximo de 50 000 filas (si se supera, `422`). El servidor dedica hasta 120 s a un CSV y 10 s a un JSON; si una dependencia no responde a tiempo, `503`.

```ts
const url = new URL(`https://sio-business-reporting-dev.onrender.com/api/v1/companies/${companyId}/reports/purchases`);
url.searchParams.set("date_from", "2026-10-01");
url.searchParams.set("date_to", "2026-10-19");
url.searchParams.set("format", "csv");
const respuesta = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
const blob = await respuesta.blob(); // guardar con el nombre de Content-Disposition
```

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso del reporte | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Configuración válida y JWKS disponible | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/companies/{company_id}/reports/top-selling-products` | Productos más vendidos de la empresa | `perm:business-reporting:top_selling_products:read` | `READ` | [Ver](#3-get-companiescompany_idreportstop-selling-products) |
| 4 | `GET` | `/companies/{company_id}/branches/{branch_id}/reports/top-selling-products` | Productos más vendidos de una sucursal | ídem | `READ` | [Ver](#4-get-companiescompany_idbranchesbranch_idreportstop-selling-products) |
| 5 | `GET` | `/companies/{company_id}/reports/sales-by-branch` | Ventas por sucursal (comparativo) | `perm:business-reporting:sales_by_branch:read` | `READ` | [Ver](#5-get-companiescompany_idreportssales-by-branch) |
| 6 | `GET` | `/companies/{company_id}/branches/{branch_id}/reports/sales-by-branch` | Ventas de una sucursal | ídem | `READ` | [Ver](#6-get-companiescompany_idbranchesbranch_idreportssales-by-branch) |
| 7 | `GET` | `/companies/{company_id}/reports/purchases` | Compras del período (empresa) | `perm:business-reporting:purchases:read` | `READ` | [Ver](#7-get-companiescompany_idreportspurchases) |
| 8 | `GET` | `/companies/{company_id}/branches/{branch_id}/reports/purchases` | Compras del período (sucursal) | ídem | `READ` | [Ver](#8-get-companiescompany_idbranchesbranch_idreportspurchases) |
| 9 | `GET` | `/companies/{company_id}/reports/stock-evolution` | Evolución de existencias consolidada | `perm:business-reporting:stock_evolution:read` | `READ` | [Ver](#9-get-companiescompany_idreportsstock-evolution) |
| 10 | `GET` | `/companies/{company_id}/branches/{branch_id}/reports/stock-evolution` | Evolución de existencias de una sucursal | ídem | `READ` | [Ver](#10-get-companiescompany_idbranchesbranch_idreportsstock-evolution) |

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-business-reporting-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-business-reporting-dev.onrender.com/health/ready` → `200` `{"status": "ok"}` si la configuración es válida y el JWKS de Keycloak responde; `503` si no. Este servicio no tiene base de datos propia.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/health/ready'
```

### 3. `GET /companies/{company_id}/reports/top-selling-products`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/top-selling-products` |
| Permisos | `perm:business-reporting:top_selling_products:read` + `perm:sales:sales:read` |
| Alcance | Empresa; `branch_id` repetible como filtro |

Parámetros propios (además de los comunes):

| Parámetro | Tipo | Obligatorio | Valores |
|---|---|---|---|
| `rank_by` | `quantity` \| `amount` | No (`quantity`) | Ranking por cantidad en unidad base o por importe |
| `limit` | integer | No (20) | 1–100 filas |
| `include_presentations` | boolean | No (`false`) | Añade el desglose por presentación en cada producto |
| `branch_id` | UUID, repetible | No | Máx. 100 |

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19&rank_by=amount&limit=10&include_presentations=true' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`TopProductsOut`; valores ilustrativos):

```json
{
  "report": "top-selling-products",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:30:00Z",
  "criteria": {},
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "mixed_base_units": false,
  "items": [
    {
      "rank": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "product_code": "PRD-0001",
      "product_name": "Acetaminofén 500 mg",
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "quantity_base": "1200",
      "currency_code": "COP",
      "amount": "960000.00",
      "sales_count": 85,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "code": "PRD-0001-U",
          "name": "Unidad",
          "quantity": "1200",
          "quantity_base": "1200",
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

Reglas de negocio: solo ventas `CONFIRMED` por `operation_date`; las anuladas se excluyen. Nunca se suman cantidades de productos distintos; `mixed_base_units: true` avisa de que el ranking compara productos con unidades base distintas. Los importes se agrupan por moneda. `presentations` es `null` salvo con `include_presentations=true`. Dependencias: Operational Context, Sales, Commercial Relationship y Product Catalog (nombres, códigos y unidades).

### 4. `GET /companies/{company_id}/branches/{branch_id}/reports/top-selling-products`

Igual que la operación 3 pero **solo** para la sucursal de la ruta (`branch_id` obligatorio en la ruta; debe ser de la empresa, si no `404`). Mismos parámetros propios salvo `branch_id` por consulta, que no se admite. Misma respuesta `TopProductsOut` con `branch_ids` de un solo elemento.

URL: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/top-selling-products`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`TopProductsOut`; valores ilustrativos):

```json
{
  "report": "top-selling-products",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:04:05Z",
  "criteria": {
    "status": "CONFIRMED"
  },
  "branch_ids": [
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ],
  "mixed_base_units": false,
  "items": [
    {
      "rank": 1,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "product_code": "PRD-0001",
      "product_name": "Acetaminofén 500 mg",
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "quantity_base": "2.0000",
      "currency_code": "COP",
      "amount": "1600.00",
      "sales_count": 5,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "code": "CJ100",
          "name": "Caja x 100",
          "quantity": "2",
          "quantity_base": "2.0000",
          "amount": "1600.00"
        }
      ]
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "amount": "1600.00",
      "sales_count": 5
    }
  ]
}
```

### 5. `GET /companies/{company_id}/reports/sales-by-branch`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/sales-by-branch` |
| Permisos | `perm:business-reporting:sales_by_branch:read` + `perm:sales:sales:read` |
| Parámetros propios | `branch_id` (UUID, repetible, máx. 100) |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`SalesByBranchOut`; valores ilustrativos):

```json
{
  "report": "sales-by-branch",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:30:00Z",
  "criteria": {},
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7", "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f"],
  "items": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "branch_code": "SUC-001",
      "branch_name": "Sucursal Centro",
      "currency_code": "COP",
      "sales_count": 210,
      "total_amount": "3100000.00",
      "share_percentage": "71.26"
    },
    {
      "branch_id": "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f",
      "branch_code": "SUC-002",
      "branch_name": "Sucursal Norte",
      "currency_code": "COP",
      "sales_count": 100,
      "total_amount": "1250000.00",
      "share_percentage": "28.74"
    }
  ],
  "totals": [
    {"currency_code": "COP", "sales_count": 310, "total_amount": "4350000.00"}
  ]
}
```

Reglas: compara sucursales; las del alcance sin ventas aparecen con cero. `share_percentage` = total de la sucursal ÷ suma de los totales de **las sucursales de la respuesta** en la misma moneda × 100 (con un solo `branch_id` con ventas da `100`). Solo ventas `CONFIRMED` por `operation_date`.

### 6. `GET /companies/{company_id}/branches/{branch_id}/reports/sales-by-branch`

Número de ventas y total vendido **solo** de la sucursal de la ruta, por moneda, también con cero ventas. Sin `share_percentage`. `branch_id` por consulta produce `422`.

URL: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/sales-by-branch`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`BranchSalesReportOut`): campos comunes + `branch_id`, `branch_code`, `branch_name` e `items[]` con `currency_code`, `sales_count`, `total_amount`.

```json
{
  "report": "sales-by-branch",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:30:00Z",
  "criteria": {},
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "branch_code": "SUC-001",
  "branch_name": "Sucursal Centro",
  "items": [
    {"currency_code": "COP", "sales_count": 210, "total_amount": "3100000.00"}
  ]
}
```

### 7. `GET /companies/{company_id}/reports/purchases`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/purchases` |
| Permisos | `perm:business-reporting:purchases:read` + `perm:purchase:purchases:read` |
| Alcance | Empresa; sin `branch_id` incluye también sucursales inactivas |

Parámetros propios:

| Parámetro | Tipo | Obligatorio | Valores |
|---|---|---|---|
| `category` | repetible, máx. 3 | No (todas) | `RECEIVED` (recibida), `PENDING_RECEIPT` (pendiente de recepción), `CANCELLED` (anulada) |
| `page` | integer | No (1) | ≥ 1 |
| `page_size` | integer | No (**50**) | 1–100 |
| `branch_id` | UUID, repetible | No | Máx. 100 |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PurchasesOut`; paginada; valores ilustrativos):

```json
{
  "report": "purchases",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:30:00Z",
  "criteria": {},
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "items": [
    {
      "purchase_id": "4a5b6c7d-8e9f-4a0b-9c1d-2e3f4a5b6c7d",
      "operation_date": "2026-10-05",
      "received_at": "2026-10-06T14:00:00Z",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "branch_name": "Sucursal Centro",
      "supplier_name": "Distribuidora Ejemplo S.A.S.",
      "supplier_identification": "900123456-7",
      "number": "C-000045",
      "supplier_document_number": "FV-8891",
      "status": "CONFIRMED",
      "category": "RECEIVED",
      "receipt_status": "RECEIVED",
      "currency_code": "COP",
      "total": "2500000.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "received_count": 12,
      "received_total": "18500000.00",
      "pending_receipt_count": 2,
      "pending_receipt_total": "3100000.00",
      "cancelled_count": 1,
      "cancelled_total": "400000.00",
      "effective_total": "21600000.00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 15,
  "total_pages": 1
}
```

Reglas: compras **no borrador** por `operation_date`. `totals` es del período completo por moneda (no de la página): `effective_total` = recibidas + pendientes; las anuladas se informan y nunca suman. `received_at` es informativa. Los valores de `status` y `receipt_status` son los de Purchase (ver su ficha); los mostrados son ilustrativos. El CSV descarga todas las páginas (máx. 50 000 filas).

### 8. `GET /companies/{company_id}/branches/{branch_id}/reports/purchases`

Igual que la operación 7 para una sola sucursal (en la ruta). Mismos parámetros propios salvo `branch_id` por consulta. Misma respuesta `PurchasesOut`.

URL: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/purchases`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PurchasesOut`; valores ilustrativos):

```json
{
  "report": "purchases",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:04:05Z",
  "criteria": {
    "status": "CONFIRMED"
  },
  "branch_ids": [
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ],
  "items": [
    {
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "operation_date": "2026-10-19",
      "received_at": "2026-10-19T15:04:05Z",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "branch_name": "Sucursal Centro",
      "supplier_name": "Distribuidora Farma S.A.S.",
      "supplier_identification": "NIT 900123456-7",
      "number": null,
      "supplier_document_number": null,
      "status": "CONFIRMED",
      "category": "RECEIVED",
      "receipt_status": "RECEIVED",
      "currency_code": "COP",
      "total": "1600.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "received_count": 1,
      "received_total": "1600.00",
      "pending_receipt_count": 0,
      "pending_receipt_total": "0.00",
      "cancelled_count": 0,
      "cancelled_total": "0.00",
      "effective_total": "1600.00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 9. `GET /companies/{company_id}/reports/stock-evolution`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/stock-evolution` |
| Permisos | `perm:business-reporting:stock_evolution:read` + `perm:inventory:stock_evolution:read` |
| Alcance | Empresa; consolida las sucursales del alcance (todas, incluidas inactivas, o las de `branch_id`). Máximo 100 sucursales consolidables (`422` si la empresa tiene más y no se filtra) |

Parámetros propios:

| Parámetro | Tipo | Obligatorio | Valores |
|---|---|---|---|
| `company_product_id` | UUID, repetible, máx. 100 | No | Limita a esos productos ([company_product_id](../parametros/company-product-id.md)) |
| `page` | integer | No (1) | ≥ 1 |
| `page_size` | integer | No (50) | 1–100 |
| `branch_id` | UUID, repetible, máx. 100 | No | — |

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`CompanyStockEvolutionOut`; valores ilustrativos):

```json
{
  "report": "stock-evolution",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:30:00Z",
  "criteria": {},
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7", "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f"],
  "timezone": "America/Bogota",
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "product_code": "PRD-0001",
      "product_name": "Acetaminofén 500 mg",
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "opening_quantity": "500",
      "entries": "1500",
      "outputs": "1200",
      "entry_reversals": "0",
      "output_reversals": "10",
      "positive_adjustments": "5",
      "negative_adjustments": "15",
      "closing_quantity": "800",
      "movement_count": 97,
      "branch_count": 2
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```

Reglas: por producto, en su unidad base, existencias y movimientos **sumados** sobre las sucursales del alcance; `branch_count` = sucursales que aportan. Los días se cuentan en la zona horaria de la empresa (`timezone`). Se verifica la identidad `closing = opening + entries − outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments`; si no cuadra, `503` (incidente de integridad). **Sin costos.** La consolidación la calcula Inventory.

### 10. `GET /companies/{company_id}/branches/{branch_id}/reports/stock-evolution`

Igual que la operación 9 para la sucursal de la ruta, sin `branch_count`, con `branch_id`, `branch_code`, `branch_name` y `timezone` de la sucursal. Parámetros propios: `company_product_id` (repetible), `page`, `page_size`.

URL: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/stock-evolution`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`StockEvolutionReportOut`): `items[]` con `company_product_id`, `product_code`, `product_name`, `base_unit`, `opening_quantity`, `entries`, `outputs`, `entry_reversals`, `output_reversals`, `positive_adjustments`, `negative_adjustments`, `closing_quantity`, `movement_count`, más `page`, `page_size`, `total_records`, `total_pages`.

Ejemplo de respuesta `200` (`StockEvolutionReportOut`; valores ilustrativos):

```json
{
  "report": "stock-evolution",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-19T15:04:05Z",
  "criteria": {
    "status": "CONFIRMED"
  },
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "branch_code": "SUC-01",
  "branch_name": "Sucursal Centro",
  "timezone": "America/Bogota",
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "product_code": "PRD-0001",
      "product_name": "Acetaminofén 500 mg",
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "opening_quantity": "0.0000",
      "entries": "120.0000",
      "outputs": "80.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "0.0000",
      "positive_adjustments": "0.0000",
      "negative_adjustments": "0.0000",
      "closing_quantity": "40.0000",
      "movement_count": 3
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
| `403 BUSINESS_REPORTING.FORBIDDEN` | Falta el permiso del reporte **o** el permiso de lectura del servicio propietario | Comprobar ambos permisos en el token |
| `404 BUSINESS_REPORTING.NOT_FOUND` | Empresa inexistente, sin membresía `ACTIVE`, o `branch_id` de otra empresa | Validar `company_id` y `branch_id` con `/me/operational-context` |
| `422` `INVALID_DATE_RANGE` / `PERIOD_TOO_LONG` / `DATE_IN_FUTURE` | Período inválido (orden, más de 366 días, fecha final futura) | Corregir fechas; el «hoy» se calcula en la zona horaria de la empresa |
| `422` por `branch_id` en ruta de sucursal | Se envió `branch_id` por consulta en una ruta `/branches/{branch_id}/…` | Quitar el parámetro |
| `422` por CSV | Más de 50 000 filas | Acotar el período o filtrar |
| `503 BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Un servicio no respondió a tiempo (10 s JSON, 120 s CSV), respondió algo inválido o falló la identidad de existencias | Reintentar; no hay reportes parciales |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía, datos de la empresa (zona horaria) y sucursales; siempre antes de cualquier otra llamada |
| Sales | Agregaciones de ventas (reportes 3 a 6), con el token del usuario |
| Purchase | Compras del período (7 y 8) |
| Inventory | Evolución de existencias por sucursal y consolidada (9 y 10) |
| Commercial Relationship, Product Catalog | Códigos, nombres, presentaciones y unidades base de los productos |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 10 |
| Operaciones documentadas | 10 |
| Permisos contrastados con el código | Sí (`api/reports.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado generado desde los modelos del servicio) |
| Pendiente | Contenido exacto de `criteria`; valores de `status`/`receipt_status` en compras (se documentan en la ficha de Purchase) |

# 6.9 Reportes

[← API principales](README.md) · [← Índice](../index.md)

Información de negocio consolidada para dueños, administradores y supervisores: qué se vende más, cuánto vende cada sucursal, qué se compró en el período y cómo evolucionaron las existencias. Todos los reportes son de solo lectura, se calculan sobre documentos confirmados y se entregan en JSON o, con `format=csv`, como archivo CSV descargable.

Servicio implicado: [Business Reporting](../servicios/business-reporting.md). Business Reporting no guarda datos propios: en cada solicitud verifica la membresía y las sucursales en Operational Context, pide **una** agregación ya calculada al servicio dueño de la información (Sales, Purchase o Inventory) y completa códigos, nombres y unidades base con Commercial Relationship y Product Catalog. Esas agregaciones se piden con el token del usuario, por eso cada reporte exige dos permisos: el del reporte y el de lectura del servicio dueño. El frontend consume solo los reportes de esta sección.

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Productos más vendidos de la empresa | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/top-selling-products` | `perm:business-reporting:top_selling_products:read` **y** `perm:sales:sales:read` | [BR 3](../servicios/business-reporting.md#3-get-companiescompany_idreportstop-selling-products) |
| 2 | Productos más vendidos de una sucursal | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/top-selling-products` | `perm:business-reporting:top_selling_products:read` **y** `perm:sales:sales:read` | [BR 4](../servicios/business-reporting.md#4-get-companiescompany_idbranchesbranch_idreportstop-selling-products) |
| 3 | Ventas por sucursal (comparativo) | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/sales-by-branch` | `perm:business-reporting:sales_by_branch:read` **y** `perm:sales:sales:read` | [BR 5](../servicios/business-reporting.md#5-get-companiescompany_idreportssales-by-branch) |
| 4 | Ventas de una sucursal | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/sales-by-branch` | `perm:business-reporting:sales_by_branch:read` **y** `perm:sales:sales:read` | [BR 6](../servicios/business-reporting.md#6-get-companiescompany_idbranchesbranch_idreportssales-by-branch) |
| 5 | Compras del período de la empresa | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/purchases` | `perm:business-reporting:purchases:read` **y** `perm:purchase:purchases:read` | [BR 7](../servicios/business-reporting.md#7-get-companiescompany_idreportspurchases) |
| 6 | Compras del período de una sucursal | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/purchases` | `perm:business-reporting:purchases:read` **y** `perm:purchase:purchases:read` | [BR 8](../servicios/business-reporting.md#8-get-companiescompany_idbranchesbranch_idreportspurchases) |
| 7 | Evolución de existencias consolidada de la empresa | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/stock-evolution` | `perm:business-reporting:stock_evolution:read` **y** `perm:inventory:stock_evolution:read` | [BR 9](../servicios/business-reporting.md#9-get-companiescompany_idreportsstock-evolution) |
| 8 | Evolución de existencias de una sucursal | `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/stock-evolution` | `perm:business-reporting:stock_evolution:read` **y** `perm:inventory:stock_evolution:read` | [BR 10](../servicios/business-reporting.md#10-get-companiescompany_idbranchesbranch_idreportsstock-evolution) |

Operaciones relacionadas que no se consideran principales: las comprobaciones de salud del servicio (BR 1 y 2, sin token) y las agregaciones internas de Sales (`sales-aggregates/by-product`, `by-branch`), Purchase (`purchase-reports/period`) e Inventory (`stock-evolution`), que son las fuentes de estos reportes y no se consumen desde el frontend. Las consultas operativas de inventario (existencias actuales, productos bajo el mínimo, indicadores del tablero) son de Product Inventory Query y están en [Inventario](inventario.md); completan la vista gerencial pero no son reportes de Business Reporting.

Orden habitual: el usuario elige la empresa y, opcionalmente, la sucursal en el contexto operativo ([API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario)), fija el período y llama al reporte de la empresa ([API 1](#1-productos-más-vendidos-de-la-empresa), [3](#3-ventas-por-sucursal-comparativo), [5](#5-compras-del-período-de-la-empresa) o [7](#7-evolución-de-existencias-consolidada-de-la-empresa)) o al de una sola sucursal ([API 2](#2-productos-más-vendidos-de-una-sucursal), [4](#4-ventas-de-una-sucursal), [6](#6-compras-del-período-de-una-sucursal) u [8](#8-evolución-de-existencias-de-una-sucursal)); para exportar repite la misma llamada con `format=csv`.

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- **Período.** `date_from` y `date_to` son obligatorios, en formato `AAAA-MM-DD`, ambos incluidos. Verificado en el código: `date_to` no puede ser anterior a `date_from` (`422`, código `INVALID_DATE_RANGE`), el período no puede superar 366 días (`PERIOD_TOO_LONG`) y `date_to` no puede ser posterior a «hoy» calculado en la zona horaria de la empresa (`DATE_IN_FUTURE`). Las ventas y compras se filtran por su fecha de operación (`operation_date`); las existencias por el instante del movimiento (`created_at`), contando los días en la zona horaria de la sucursal o de la empresa.
- **Parámetros estrictos.** Los parámetros de consulta se validan con modelo estricto: un parámetro desconocido, un valor fuera de rango o un formato inválido responde `422 BUSINESS_REPORTING.VALIDATION_ERROR` con `errors[]` (`field`, `message`, `code`: `REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD` o los códigos de período anteriores). En las rutas por sucursal no se admite `branch_id` por consulta (`422`).
- **Exportar a CSV.** Todos los reportes aceptan `format=csv` (por defecto `json`). La respuesta es `200` con `Content-Type: text/csv; charset=utf-8` y `Content-Disposition: attachment; filename="<reporte>-<company_id>-<date_from>-<date_to>.csv"` (las rutas por sucursal añaden `-<branch_id>` al nombre del reporte). Separador coma, misma información que el JSON, con filas `TOTAL` al final cuando el JSON trae `totals`. `bom=true` (por defecto) antepone la marca de orden de bytes para que Excel abra el archivo en UTF-8; `bom=false` la omite. En compras y existencias el CSV incluye **todas las páginas** (ignora `page` y `page_size`), hasta 50 000 filas; si el reporte tiene más, `422` con código `CSV_TOO_LARGE`. Ejemplo:

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19&format=csv&bom=true' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -o ventas-por-sucursal.csv
```

- **Cabecera común de la respuesta JSON.** Todos los reportes traen `report` (nombre), `company_id`, `date_from`, `date_to`, `generated_at` (fecha y hora de generación, UTC) y `criteria` (objeto con los criterios aplicados, verificado en el código para cada reporte). Las rutas de empresa añaden `branch_ids[]` (vacío cuando no se filtró por sucursal y el reporte abarca toda la empresa; en el reporte 7 siempre trae las sucursales consolidadas); las rutas por sucursal añaden `branch_id`, `branch_code` y `branch_name`.
- **Números como texto.** Cantidades con 4 decimales (`"1200.0000"`), importes con 2 (`"960000.00"`) y porcentajes con 4; siempre cadenas, nunca números flotantes. Los importes se agrupan por moneda (`currency_code`); nunca se suman monedas distintas.
- **Alcance.** El usuario necesita membresía `ACTIVE` en la empresa; si no la tiene, la empresa no existe o una sucursal no es de la empresa, la respuesta es `404 BUSINESS_REPORTING.NOT_FOUND` («La empresa o la sucursal no existe o no tiene acceso.»), sin distinguir el caso. **No se exige** que el usuario tenga asignada la sucursal: con membresía y permisos puede consultar cualquier sucursal de la empresa. Sin `branch_id`, las rutas de empresa abarcan todas las sucursales `ACTIVE` (compras y existencias incluyen también las inactivas, que conservan datos); con `branch_id` (repetible, máximo 100), solo esas, aunque estén inactivas.
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `401 BUSINESS_REPORTING.UNAUTHENTICATED` en Problem Details si el token venció mientras el servicio dueño lo evaluaba (mismo tratamiento); `403 BUSINESS_REPORTING.FORBIDDEN` cuando falta el permiso del reporte **o** el permiso de lectura del servicio dueño (el `detail` nunca dice cuál: mostrar que faltan permisos y el `trace_id`); `503 BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` («Una dependencia del servicio no está disponible. Intente de nuevo más tarde.») cuando un servicio no respondió a tiempo (10 s para JSON, 120 s para CSV), respondió algo inesperado o falló la verificación de integridad de los datos; nunca se entrega un reporte parcial. Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `BUSINESS_REPORTING.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).

---

## 1. Productos más vendidos de la empresa

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/top-selling-products`
**Permiso requerido:** `perm:business-reporting:top_selling_products:read` **y** `perm:sales:sales:read` (Sales lo evalúa al entregar la agregación; sin él la respuesta es `403`)

### ¿Qué hace esta API?

Devuelve el ranking de los productos más vendidos de la empresa en el período, por cantidad vendida en unidad base (por defecto) o por importe, con el número de ventas de cada producto y, si se pide, el desglose por presentación. Sirve para decidir compras, promociones y espacio en estantería.

Efectos verificados en el código: solo cuenta ventas `CONFIRMED` por `operation_date` (las anuladas se excluyen); Sales ordena y limita el ranking y Business Reporting solo completa la unidad base de cada producto. Nunca suma cantidades de productos distintos: si los productos del ranking tienen unidades base diferentes, `mixed_base_units` es `true` y conviene comparar por `amount`. Sin `branch_id` abarca todas las sucursales `ACTIVE` de la empresa; con `branch_id` (repetible) solo esas. Si Sales devuelve un producto que Commercial Relationship no reconoce como de la empresa, el reporte no se entrega (`503`).

Antes necesita: `company_id` con membresía `ACTIVE` y el período. Opcionalmente los `branch_id` a comparar.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19&rank_by=amount&limit=10&include_presentations=true&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `rank_by` | `quantity` \| `amount` | No; por defecto `quantity` | Criterio del ranking: cantidad en unidad base o importe vendido | Uno de: `quantity` (por defecto), `amount`; p. ej. `amount` | `&rank_by=amount` | Interfaz |
| `limit` | integer 1–100 | No; por defecto `20` | Número máximo de productos del ranking | Entero de `1` a `100`; p. ej. `10` | `&limit=10` | Interfaz |
| `include_presentations` | boolean | No; por defecto `false` | Añade a cada producto el desglose `presentations[]` | Booleano: `true` o `false`; p. ej. `true` | `&include_presentations=true` | Interfaz |
| `branch_id` | UUID, repetible (≤ 100) | No | Limita el reporte a esas sucursales; sin él, todas las `ACTIVE` de la empresa | UUID de una sucursal de la empresa, repetido por cada sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (una vez por sucursal: `&branch_id=…&branch_id=…`) | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `csv` | `&format=csv` | Interfaz (botón de exportar) |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: antepone la marca de orden de bytes UTF-8 | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19&rank_by=amount&limit=10&include_presentations=true&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`TopProductsOut`):

```json
{
  "report": "top-selling-products",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date",
    "rank_by": "amount"
  },
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
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
      "quantity_base": "1200.0000",
      "currency_code": "COP",
      "amount": "960000.00",
      "sales_count": 85,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "code": "PRD-0001-U",
          "name": "Unidad",
          "quantity": "1200.0000",
          "quantity_base": "1200.0000",
          "amount": "960000.00"
        }
      ]
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "amount": "4350000.00",
      "sales_count": 310
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `report`, `company_id`, `date_from`, `date_to`, `generated_at` | — | Cabecera común: nombre del reporte, empresa, período aplicado y momento de generación (UTC) |
| `criteria` | objeto | Criterios aplicados: `sales_status` `CONFIRMED`, `date_basis` `operation_date` y el `rank_by` usado |
| `branch_ids` | UUID[] | Sucursales filtradas; `[]` cuando el reporte abarca toda la empresa |
| `mixed_base_units` | boolean | `true` si el ranking mezcla productos con unidades base distintas: mostrar un aviso y preferir la comparación por `amount` |
| `items[].rank` | integer | Posición en el ranking, desde 1 |
| `items[].company_product_id`, `product_code`, `product_name` | UUID, string, string | Producto de la empresa; el `id` sirve para abrirlo en [Productos y precios](productos-y-precios.md) o filtrar la [API 7](#7-evolución-de-existencias-consolidada-de-la-empresa) · guía [company_product_id](../parametros/company-product-id.md) |
| `items[].base_unit` | objeto \| null | Unidad base (`id`, `code`, `name`) en la que está `quantity_base`; `null` si Product Catalog no la informa |
| `items[].quantity_base` | string (4 decimales) | Cantidad vendida en unidad base |
| `items[].currency_code`, `amount` | string, string (2 decimales) | Moneda e importe vendido del producto |
| `items[].sales_count` | integer | Número de ventas confirmadas que incluyeron el producto |
| `items[].presentations[]` | array \| null | Solo con `include_presentations=true`: por presentación, `company_product_presentation_id`, `code`, `name`, `quantity` (en la unidad de la presentación), `quantity_base` y `amount`; los tres primeros pueden ser `null` si la venta no guardó la presentación |
| `totals[]` | array | Por moneda: `amount` total vendido y `sales_count` de **todas** las ventas del período en el alcance, no solo de los productos listados |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o algún `branch_id` no es de la empresa | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`errors[].code` `INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | `date_to` anterior a `date_from`, período mayor de 366 días o `date_to` posterior a hoy en la zona horaria de la empresa | Corregir el período y mostrar `errors[].message` junto al selector de fechas |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Falta `date_from` o `date_to`, fecha mal formada, `rank_by` fuera de la enumeración, `limit` fuera de 1–100, más de 100 `branch_id`, UUID inválido o parámetro desconocido | Corregir la solicitud |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_TIMEZONE`) | La zona horaria configurada en la empresa no es válida | Informar al administrador de la empresa |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta `perm:business-reporting:top_selling_products:read` o `perm:sales:sales:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context, Sales, Commercial Relationship o Product Catalog no respondieron a tiempo o devolvieron datos incoherentes | Reintentar más tarde; no hay reporte parcial |

Ejemplo de `422` por período:

```json
{
  "type": "https://sio/errors/business-reporting/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene parámetros inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products",
  "code": "BUSINESS_REPORTING.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "date_to",
      "message": "El período no puede superar 366 días.",
      "code": "PERIOD_TOO_LONG"
    }
  ]
}
```

Ejemplo de `404`:

```json
{
  "type": "https://sio/errors/business-reporting/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "La empresa o la sucursal no existe o no tiene acceso.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products",
  "code": "BUSINESS_REPORTING.NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 2. Productos más vendidos de una sucursal

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/top-selling-products`
**Permiso requerido:** `perm:business-reporting:top_selling_products:read` **y** `perm:sales:sales:read`

### ¿Qué hace esta API?

Mismo ranking que la [API 1](#1-productos-más-vendidos-de-la-empresa), restringido a la sucursal de la ruta. Es la variante para el supervisor de una sucursal o para la pantalla de una sucursal concreta; equivale a la API 1 con un único `branch_id`, pero aquí la sucursal va en la ruta y no se admite `branch_id` por consulta.

Efectos verificados en el código: la sucursal debe pertenecer a la empresa (si no, `404`); puede estar inactiva. Solo ventas `CONFIRMED` por `operation_date`. El CSV se llama `top-selling-products-<branch_id>-<company_id>-<date_from>-<date_to>.csv`.

Antes necesita: `company_id`, el `branch_id` de la sucursal y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19&rank_by=quantity&limit=20&include_presentations=false' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal del reporte; debe ser de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `rank_by` | `quantity` \| `amount` | No; por defecto `quantity` | Criterio del ranking | Uno de: `quantity` (por defecto), `amount`; p. ej. `quantity` | `&rank_by=quantity` | Interfaz |
| `limit` | integer 1–100 | No; por defecto `20` | Número máximo de productos | Entero de `1` a `100`; p. ej. `20` | `&limit=20` | Interfaz |
| `include_presentations` | boolean | No; por defecto `false` | Añade el desglose `presentations[]` | Booleano: `true` o `false`; p. ej. `false` | `&include_presentations=false` | Interfaz |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `json` | `&format=json` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-19&rank_by=quantity&limit=20&include_presentations=false`

No se admite `branch_id` como parámetro de consulta en esta ruta (`422 UNKNOWN_FIELD`).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`TopProductsOut`), mismo objeto que la [API 1](#1-productos-más-vendidos-de-la-empresa); `branch_ids` trae la sucursal de la ruta:

```json
{
  "report": "top-selling-products",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date",
    "rank_by": "quantity"
  },
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
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
      "quantity_base": "1200.0000",
      "currency_code": "COP",
      "amount": "960000.00",
      "sales_count": 85,
      "presentations": null
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "amount": "3100000.00",
      "sales_count": 210
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `branch_ids` | UUID[] | Siempre la sucursal de la ruta |
| `items[].presentations` | null | `null` cuando no se pidió `include_presentations=true` |
| Resto de campos | — | Igual que en la [API 1](#1-productos-más-vendidos-de-la-empresa) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la sucursal no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, `rank_by` o `limit` inválidos, `branch_id` enviado por consulta o parámetro desconocido | Corregir la solicitud |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta el permiso del reporte o `perm:sales:sales:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Alguna dependencia no respondió o devolvió datos incoherentes | Reintentar más tarde |

## 3. Ventas por sucursal (comparativo)

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/sales-by-branch`
**Permiso requerido:** `perm:business-reporting:sales_by_branch:read` **y** `perm:sales:sales:read`

### ¿Qué hace esta API?

Compara las sucursales de la empresa en el período: número de ventas, total vendido y participación porcentual de cada una, por moneda. Es el reporte del tablero gerencial para ver qué sucursal vende más.

Efectos verificados en el código: solo ventas `CONFIRMED` por `operation_date`. Las sucursales del alcance sin ventas aparecen con `sales_count` `0` y `total_amount` `"0.00"`. `share_percentage` = total de la sucursal ÷ suma de los totales de **las sucursales de la respuesta** en la misma moneda × 100, redondeado a 4 decimales: sin `branch_id` se calcula sobre toda la empresa; con `branch_id` solo sobre las filtradas (una sola sucursal con ventas da `100.0000`). Si una sucursal inactiva tuvo ventas en el período y no se filtró por sucursal, se añade a la respuesta. Las filas se ordenan por moneda y, dentro de cada moneda, de mayor a menor total.

Antes necesita: `company_id` con membresía `ACTIVE` y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `branch_id` | UUID, repetible (≤ 100) | No | Compara solo esas sucursales; sin él, todas las `ACTIVE` de la empresa | UUID de una sucursal de la empresa, repetido por cada sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (una vez por sucursal) | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `csv` | `&format=csv` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`SalesByBranchOut`):

```json
{
  "report": "sales-by-branch",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date"
  },
  "branch_ids": [],
  "items": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "branch_code": "SUC-001",
      "branch_name": "Sucursal Centro",
      "currency_code": "COP",
      "sales_count": 210,
      "total_amount": "3100000.00",
      "share_percentage": "71.2644"
    },
    {
      "branch_id": "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f",
      "branch_code": "SUC-002",
      "branch_name": "Sucursal Norte",
      "currency_code": "COP",
      "sales_count": 100,
      "total_amount": "1250000.00",
      "share_percentage": "28.7356"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "sales_count": 310,
      "total_amount": "4350000.00"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `criteria` | objeto | `sales_status` `CONFIRMED` y `date_basis` `operation_date` |
| `branch_ids` | UUID[] | `[]` cuando abarca toda la empresa; las filtradas cuando se envió `branch_id` |
| `items[].branch_id`, `branch_code`, `branch_name` | UUID, string, string | Sucursal (nombre y código tomados de Operational Context) |
| `items[].currency_code` | string | Moneda de la fila; una sucursal con ventas en dos monedas aparece dos veces |
| `items[].sales_count` | integer | Ventas confirmadas de la sucursal en esa moneda |
| `items[].total_amount` | string (2 decimales) | Total vendido |
| `items[].share_percentage` | string (4 decimales) | Participación sobre la suma de las sucursales de la respuesta en esa moneda; `"0.0000"` si nadie vendió |
| `totals[]` | array | Por moneda: `sales_count` y `total_amount` de todas las sucursales de la respuesta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o algún `branch_id` no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, más de 100 `branch_id`, UUID inválido o parámetro desconocido | Corregir la solicitud |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta `perm:business-reporting:sales_by_branch:read` o `perm:sales:sales:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context o Sales no respondieron, o Sales devolvió ventas de una sucursal que no es de la empresa | Reintentar más tarde |

## 4. Ventas de una sucursal

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/sales-by-branch`
**Permiso requerido:** `perm:business-reporting:sales_by_branch:read` **y** `perm:sales:sales:read`

### ¿Qué hace esta API?

Devuelve el número de ventas y el total vendido **solo** de la sucursal de la ruta, por moneda, también cuando no hubo ventas. No trae `share_percentage`: con una sola sucursal no hay comparación (la participación entre sucursales está en la [API 3](#3-ventas-por-sucursal-comparativo)). Es el resumen de ventas de la pantalla de una sucursal.

Efectos verificados en el código: la sucursal debe ser de la empresa (`404` si no); solo ventas `CONFIRMED` por `operation_date`; si la sucursal no tuvo ventas en la moneda por defecto de la empresa, la fila aparece con ceros. El CSV no incluye fila de totales.

Antes necesita: `company_id`, `branch_id` y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal del reporte; debe ser de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `json` | `&format=json` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-19`

No se admite `branch_id` como parámetro de consulta en esta ruta (`422 UNKNOWN_FIELD`).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`BranchSalesReportOut`):

```json
{
  "report": "sales-by-branch",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date"
  },
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "branch_code": "SUC-001",
  "branch_name": "Sucursal Centro",
  "items": [
    {
      "currency_code": "COP",
      "sales_count": 210,
      "total_amount": "3100000.00"
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `branch_id`, `branch_code`, `branch_name` | UUID, string, string | Sucursal de la ruta |
| `items[].currency_code` | string | Moneda; una fila por moneda con ventas (al menos la moneda por defecto de la empresa) |
| `items[].sales_count`, `total_amount` | integer, string (2 decimales) | Ventas confirmadas y total vendido en esa moneda |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la sucursal no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, `branch_id` enviado por consulta o parámetro desconocido | Corregir la solicitud |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta el permiso del reporte o `perm:sales:sales:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context o Sales no respondieron | Reintentar más tarde |

## 5. Compras del período de la empresa

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/purchases`
**Permiso requerido:** `perm:business-reporting:purchases:read` **y** `perm:purchase:purchases:read` (Purchase lo evalúa al entregar el listado)

### ¿Qué hace esta API?

Lista, una fila por compra, las compras no borrador de la empresa en el período, clasificadas en tres categorías: `RECEIVED` (confirmada y recibida: la mercancía ya entró al inventario), `PENDING_RECEIPT` (confirmada pero sin recibir: comprometida, no es mercancía recibida) y `CANCELLED` (anulada). Incluye totales por categoría y el total efectivo. Sirve para el seguimiento de proveedores y de la mercancía pendiente de llegar.

Efectos verificados en el código: filtra por `operation_date`; sin `branch_id` abarca todas las sucursales de la empresa, **también las inactivas** (sus compras siguen siendo de la empresa); `totals[]` es del período completo por moneda, no de la página: `effective_total` = recibidas + pendientes; las anuladas se informan y nunca suman. Los valores de `status` y `receipt_status` son los de [Compras](compras.md): `status` `CONFIRMED` o `CANCELLED` y `receipt_status` `PENDING` o `RECEIVED`. `received_at` es informativa. La paginación la hace Purchase; con `format=csv` se descargan todas las páginas (máximo 50 000 filas).

Antes necesita: `company_id` con membresía `ACTIVE` y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&category=RECEIVED&category=PENDING_RECEIPT&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `category` | enumeración, repetible (≤ 3) | No; por defecto las tres | Categorías a incluir | Uno o varios de: `RECEIVED`, `PENDING_RECEIPT`, `CANCELLED`; p. ej. `RECEIVED` | `&category=RECEIVED` (una vez por categoría: `&category=RECEIVED&category=PENDING_RECEIPT`) | Interfaz (casillas de categoría) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página (se ignora con `csv`) | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `50` | Compras por página (se ignora con `csv`) | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `branch_id` | UUID, repetible (≤ 100) | No | Solo compras de esas sucursales; sin él, todas las de la empresa, activas e inactivas | UUID de una sucursal de la empresa, repetido por cada sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (una vez por sucursal) | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `csv` | `&format=csv` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&category=RECEIVED&category=PENDING_RECEIPT&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PurchasesOut`, paginada):

```json
{
  "report": "purchases",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "date_basis": "operation_date",
    "categories": ["RECEIVED", "PENDING_RECEIPT"]
  },
  "branch_ids": [],
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
    },
    {
      "purchase_id": "5b6c7d8e-9f0a-4b1c-8d2e-3f4a5b6c7d8e",
      "operation_date": "2026-10-15",
      "received_at": null,
      "branch_id": "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f",
      "branch_name": "Sucursal Norte",
      "supplier_name": "Distribuidora Ejemplo S.A.S.",
      "supplier_identification": "900123456-7",
      "number": "C-000052",
      "supplier_document_number": "FV-9020",
      "status": "CONFIRMED",
      "category": "PENDING_RECEIPT",
      "receipt_status": "PENDING",
      "currency_code": "COP",
      "total": "1550000.00"
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
  "total_records": 14,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `criteria` | objeto | `date_basis` `operation_date` y `categories` aplicadas (las tres si no se filtró) |
| `branch_ids` | UUID[] | `[]` cuando abarca toda la empresa |
| `items[].purchase_id` | UUID | Compra; con él se abre el detalle en [Compras](compras.md) · guía [purchase_id](../parametros/purchase-id.md) |
| `items[].operation_date`, `received_at` | date, date-time \| null | Fecha de operación (la que filtra el período) y momento de la recepción; `null` si no se ha recibido |
| `items[].branch_id`, `branch_name` | UUID, string | Sucursal de la compra |
| `items[].supplier_name`, `supplier_identification` | string | Proveedor tal como quedó congelado en la compra |
| `items[].number`, `supplier_document_number` | string \| null | Número interno asignado al confirmar y número del documento del proveedor |
| `items[].status`, `receipt_status` | string, string \| null | Estado de la compra (`CONFIRMED`, `CANCELLED`) y de la recepción (`PENDING`, `RECEIVED`) según Purchase |
| `items[].category` | `RECEIVED` \| `PENDING_RECEIPT` \| `CANCELLED` | Categoría del reporte; es la que debe usarse para agrupar en pantalla |
| `items[].currency_code`, `total` | string, string (2 decimales) | Moneda y total de la compra |
| `totals[]` | array | Por moneda y para **todo el período** (no la página): conteo y total de recibidas, pendientes y anuladas, y `effective_total` = recibidas + pendientes |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `total_records` cuenta las compras de las categorías pedidas |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o algún `branch_id` no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, `category` fuera de la enumeración o repetida más de 3 veces, `page` < 1, `page_size` fuera de 1–100, más de 100 `branch_id` o parámetro desconocido | Corregir la solicitud |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`CSV_TOO_LARGE`) | Con `format=csv`, el reporte supera 50 000 filas | Acotar el período o filtrar por sucursal o categoría |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta `perm:business-reporting:purchases:read` o `perm:purchase:purchases:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context o Purchase no respondieron, o Purchase devolvió una compra de una sucursal fuera del alcance o una categoría desconocida | Reintentar más tarde |

Ejemplo de `422` por CSV demasiado grande:

```json
{
  "type": "https://sio/errors/business-reporting/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "El reporte supera el máximo de filas del CSV.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/purchases",
  "code": "BUSINESS_REPORTING.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "format",
      "message": "El CSV admite como máximo 50000 filas; reduzca el período o use los filtros.",
      "code": "CSV_TOO_LARGE"
    }
  ]
}
```

## 6. Compras del período de una sucursal

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/purchases`
**Permiso requerido:** `perm:business-reporting:purchases:read` **y** `perm:purchase:purchases:read`

### ¿Qué hace esta API?

Mismo listado de compras que la [API 5](#5-compras-del-período-de-la-empresa), restringido a la sucursal de la ruta; `totals[]` es de esa sucursal. Equivale a la API 5 con un único `branch_id`, pero aquí la sucursal va en la ruta y no se admite `branch_id` por consulta.

Efectos verificados en el código: la sucursal debe ser de la empresa (`404` si no); puede estar inactiva. Mismas categorías, paginación y reglas de CSV que la API 5; el archivo se llama `purchases-<branch_id>-<company_id>-<date_from>-<date_to>.csv`.

Antes necesita: `company_id`, `branch_id` y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&category=PENDING_RECEIPT&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal del reporte; debe ser de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `category` | enumeración, repetible (≤ 3) | No; por defecto las tres | Categorías a incluir | Uno o varios de: `RECEIVED`, `PENDING_RECEIPT`, `CANCELLED`; p. ej. `PENDING_RECEIPT` | `&category=PENDING_RECEIPT` (una vez por categoría) | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página (se ignora con `csv`) | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `50` | Compras por página (se ignora con `csv`) | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `json` | `&format=json` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/purchases?date_from=2026-10-01&date_to=2026-10-19&category=PENDING_RECEIPT&page=1&page_size=50`

No se admite `branch_id` como parámetro de consulta en esta ruta (`422 UNKNOWN_FIELD`).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PurchasesOut`), mismo objeto que la [API 5](#5-compras-del-período-de-la-empresa); `branch_ids` trae la sucursal de la ruta y `totals[]` es de esa sucursal:

```json
{
  "report": "purchases",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "date_basis": "operation_date",
    "categories": ["PENDING_RECEIPT"]
  },
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "items": [
    {
      "purchase_id": "6c7d8e9f-0a1b-4c2d-9e3f-4a5b6c7d8e9f",
      "operation_date": "2026-10-18",
      "received_at": null,
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "branch_name": "Sucursal Centro",
      "supplier_name": "Distribuidora Ejemplo S.A.S.",
      "supplier_identification": "900123456-7",
      "number": "C-000058",
      "supplier_document_number": null,
      "status": "CONFIRMED",
      "category": "PENDING_RECEIPT",
      "receipt_status": "PENDING",
      "currency_code": "COP",
      "total": "800000.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "received_count": 8,
      "received_total": "12400000.00",
      "pending_receipt_count": 1,
      "pending_receipt_total": "800000.00",
      "cancelled_count": 0,
      "cancelled_total": "0.00",
      "effective_total": "13200000.00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `branch_ids` | UUID[] | Siempre la sucursal de la ruta |
| `totals[]` | array | Conteos y totales del período completo **de esa sucursal**, por moneda, para todas las categorías (no solo las filtradas) |
| Resto de campos | — | Igual que en la [API 5](#5-compras-del-período-de-la-empresa) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la sucursal no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, `category` inválida, paginación fuera de rango, `branch_id` enviado por consulta o parámetro desconocido | Corregir la solicitud |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`CSV_TOO_LARGE`) | Con `format=csv`, más de 50 000 filas | Acotar el período o filtrar por categoría |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta el permiso del reporte o `perm:purchase:purchases:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context o Purchase no respondieron o devolvieron datos incoherentes | Reintentar más tarde |

## 7. Evolución de existencias consolidada de la empresa

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/stock-evolution`
**Permiso requerido:** `perm:business-reporting:stock_evolution:read` **y** `perm:inventory:stock_evolution:read` (Inventory lo evalúa al entregar la agregación)

### ¿Qué hace esta API?

Muestra, por producto y en su unidad base, cómo se llegó a la existencia final del período sumando todas las sucursales del alcance: existencia inicial, entradas, salidas, reversos de entrada y de salida, ajustes positivos y negativos y existencia final, con el número de movimientos y de sucursales que aportan. Permite explicar el saldo actual de un producto en toda la empresa. **No incluye costos.**

Efectos verificados en el código: sin `branch_id` consolida todas las sucursales de la empresa, **activas e inactivas** (las inactivas pueden conservar existencias); con `branch_id`, esas. Como máximo se consolidan 100 sucursales: si la empresa tiene más y no se filtra, `422` con código `TOO_MANY_BRANCHES`. Los días del período se cuentan en la zona horaria de la empresa (`timezone`), desde la medianoche de `date_from` hasta la medianoche siguiente a `date_to`, sobre el instante del movimiento (`created_at`). La consolidación la calcula Inventory; Business Reporting verifica en cada fila la identidad `closing_quantity = opening_quantity + entries − outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments` y que `branch_count` esté entre 1 y el número de sucursales del alcance; si no cuadra, no entrega el reporte (`503`). Cada fila es un producto: nunca se suman productos distintos. Con `format=csv` se descargan todas las páginas (máximo 50 000 filas).

Antes necesita: `company_id` con membresía `ACTIVE` y el período. Opcionalmente los `company_product_id` a seguir.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `company_product_id` | UUID, repetible (≤ 100) | No | Limita el reporte a esos productos de la empresa; sin él, todos los que tuvieron existencias o movimientos | UUID de un producto de la empresa, repetido por cada producto; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` (una vez por producto) | `items[].company_product_id` de la [API 1](#1-productos-más-vendidos-de-la-empresa) (ranking de productos vendidos; errores en §1) o `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` (lista los productos adoptados por la empresa, permiso `perm:commercial-relationship:company_products:read`; qué hace y sus errores en [Productos y precios](productos-y-precios.md) y en la ficha [CR 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products)) · guía [company_product_id](../parametros/company-product-id.md) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página (se ignora con `csv`) | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `50` | Productos por página (se ignora con `csv`) | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `branch_id` | UUID, repetible (≤ 100) | No | Consolida solo esas sucursales; sin él, todas las de la empresa, activas e inactivas | UUID de una sucursal de la empresa, repetido por cada sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (una vez por sucursal) | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `csv` | `&format=csv` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CompanyStockEvolutionOut`, paginada):

```json
{
  "report": "stock-evolution",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "date_basis": "created_at",
    "from": "2026-10-01T00:00:00-05:00",
    "to": "2026-10-20T00:00:00-05:00",
    "consolidation": "by_product"
  },
  "branch_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7", "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f"],
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
      "opening_quantity": "500.0000",
      "entries": "1500.0000",
      "outputs": "1200.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "10.0000",
      "positive_adjustments": "5.0000",
      "negative_adjustments": "15.0000",
      "closing_quantity": "800.0000",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `criteria` | objeto | `date_basis` `created_at`, los instantes `from` y `to` realmente aplicados (en la zona de la empresa) y `consolidation` `by_product` |
| `branch_ids` | UUID[] | Sucursales consolidadas (todas las de la empresa si no se filtró) |
| `timezone` | string | Zona horaria con la que se cortaron los días |
| `items[].company_product_id`, `product_code`, `product_name` | UUID, string \| null, string | Producto de la empresa (código interno y nombre según Commercial Relationship) · guía [company_product_id](../parametros/company-product-id.md) |
| `items[].base_unit` | objeto \| null | Unidad base de todas las cantidades de la fila |
| `items[].opening_quantity` | string (4 decimales) | Existencia al inicio del período, sumada en las sucursales |
| `items[].entries`, `outputs` | string | Entradas y salidas aplicadas en el período |
| `items[].entry_reversals`, `output_reversals` | string | Entradas y salidas revertidas en el período |
| `items[].positive_adjustments`, `negative_adjustments` | string | Ajustes de inventario que sumaron o restaron |
| `items[].closing_quantity` | string | Existencia al cierre; cumple la identidad descrita arriba |
| `items[].movement_count` | integer | Movimientos que intervinieron |
| `items[].branch_count` | integer | Sucursales que aportan a la fila |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación de productos |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o algún `branch_id` no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`TOO_MANY_BRANCHES`) | La empresa tiene más de 100 sucursales y no se filtró con `branch_id` | Pedir al usuario que elija hasta 100 sucursales |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, más de 100 `company_product_id` o `branch_id`, UUID inválido, paginación fuera de rango o parámetro desconocido | Corregir la solicitud |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`CSV_TOO_LARGE`) | Con `format=csv`, más de 50 000 filas | Filtrar por producto o sucursal |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_TIMEZONE`) | La zona horaria de la empresa no es válida | Informar al administrador de la empresa |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta `perm:business-reporting:stock_evolution:read` o `perm:inventory:stock_evolution:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context, Inventory, Commercial Relationship o Product Catalog no respondieron, o una fila no cumple la identidad de existencias | Reintentar más tarde; no hay reporte parcial |

Ejemplo de `422` por demasiadas sucursales:

```json
{
  "type": "https://sio/errors/business-reporting/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La empresa tiene más sucursales de las que se pueden consolidar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/stock-evolution",
  "code": "BUSINESS_REPORTING.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "branch_id",
      "message": "Indique como máximo 100 sucursales.",
      "code": "TOO_MANY_BRANCHES"
    }
  ]
}
```

## 8. Evolución de existencias de una sucursal

**Método:** `GET`
**URL:** `https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/reports/stock-evolution`
**Permiso requerido:** `perm:business-reporting:stock_evolution:read` **y** `perm:inventory:stock_evolution:read`

### ¿Qué hace esta API?

Misma evolución de existencias que la [API 7](#7-evolución-de-existencias-consolidada-de-la-empresa) para la sucursal de la ruta, sin `branch_count`. Los días se cuentan en la zona horaria de la sucursal (si no tiene una propia, la de la empresa). Es el reporte para explicar el saldo de un producto en una sucursal; el detalle movimiento a movimiento (kardex) está en [Inventario](inventario.md). **No incluye costos.**

Efectos verificados en el código: la sucursal debe ser de la empresa (`404` si no); puede estar inactiva. Se verifica la identidad de cada fila (`503` si no cuadra). Con `format=csv` se descargan todas las páginas (máximo 50 000 filas) en el archivo `stock-evolution-<branch_id>-<company_id>-<date_from>-<date_to>.csv`.

Antes necesita: `company_id`, `branch_id` y el período.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa del reporte | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal del reporte; debe ser de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `date_from` | date | Sí | Primer día del período (incluido) | Fecha `AAAA-MM-DD`; p. ej. `2026-10-01` | `?date_from=2026-10-01` | Selector de fechas de la interfaz |
| `date_to` | date | Sí | Último día del período (incluido); no anterior a `date_from`, no futuro, período ≤ 366 días | Fecha `AAAA-MM-DD`; p. ej. `2026-10-19` | `&date_to=2026-10-19` | Selector de fechas de la interfaz |
| `company_product_id` | UUID, repetible (≤ 100) | No | Limita el reporte a esos productos | UUID de un producto de la empresa, repetido por cada producto; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` (una vez por producto) | `items[].company_product_id` de la [API 2](#2-productos-más-vendidos-de-una-sucursal) (ranking de productos vendidos en la sucursal; errores en §2) o `items[].id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` (lista los productos adoptados por la empresa, permiso `perm:commercial-relationship:company_products:read`; qué hace y sus errores en [Productos y precios](productos-y-precios.md) y en la ficha [CR 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products)) · guía [company_product_id](../parametros/company-product-id.md) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página (se ignora con `csv`) | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `50` | Productos por página (se ignora con `csv`) | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `format` | `json` \| `csv` | No; por defecto `json` | Formato de la respuesta | Uno de: `json` (por defecto), `csv`; p. ej. `json` | `&format=json` | Interfaz |
| `bom` | boolean | No; por defecto `true` | Solo con `csv`: marca de orden de bytes | Booleano: `true` o `false`; p. ej. `true` | `&bom=true` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-19&page=1&page_size=50`

No se admite `branch_id` como parámetro de consulta en esta ruta (`422 UNKNOWN_FIELD`).

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`StockEvolutionReportOut`, paginada):

```json
{
  "report": "stock-evolution",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_from": "2026-10-01",
  "date_to": "2026-10-19",
  "generated_at": "2026-10-20T09:30:00Z",
  "criteria": {
    "date_basis": "created_at",
    "from": "2026-10-01T00:00:00-05:00",
    "to": "2026-10-20T00:00:00-05:00"
  },
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "branch_code": "SUC-001",
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
      "opening_quantity": "300.0000",
      "entries": "900.0000",
      "outputs": "720.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "10.0000",
      "positive_adjustments": "0.0000",
      "negative_adjustments": "10.0000",
      "closing_quantity": "480.0000",
      "movement_count": 61
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `criteria` | objeto | `date_basis` `created_at` y los instantes `from` y `to` aplicados en la zona de la sucursal |
| `branch_id`, `branch_code`, `branch_name`, `timezone` | — | Sucursal de la ruta y zona horaria con la que se cortaron los días |
| `items[]` | array | Mismos campos que en la [API 7](#7-evolución-de-existencias-consolidada-de-la-empresa), sin `branch_count`; se cumple `closing_quantity = opening_quantity + entries − outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments` |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación de productos |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `BUSINESS_REPORTING.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la sucursal no es de la empresa | Volver a leer el contexto operativo |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_DATE_RANGE`, `PERIOD_TOO_LONG`, `DATE_IN_FUTURE`) | Período inválido | Corregir el período |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD`) | Fechas ausentes o mal formadas, más de 100 `company_product_id`, UUID inválido, paginación fuera de rango, `branch_id` enviado por consulta o parámetro desconocido | Corregir la solicitud |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`CSV_TOO_LARGE`) | Con `format=csv`, más de 50 000 filas | Filtrar por producto |
| `422` | `BUSINESS_REPORTING.VALIDATION_ERROR` (`INVALID_TIMEZONE`) | La zona horaria de la sucursal o de la empresa no es válida | Informar al administrador de la empresa |
| `403` | `BUSINESS_REPORTING.FORBIDDEN` | Falta el permiso del reporte o `perm:inventory:stock_evolution:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE` | Operational Context, Inventory, Commercial Relationship o Product Catalog no respondieron, o una fila no cumple la identidad de existencias | Reintentar más tarde; no hay reporte parcial |

---

## Dependencias con otros módulos

- [Ventas](ventas.md) produce las ventas `CONFIRMED` que alimentan las API 1 a 4; una venta anulada deja de contar en el período. No existe reporte por cliente: ninguna de las 411 operaciones agrupa ventas por `company_customer_id`; la relación con el cliente se consulta venta a venta en Ventas.
- [Compras](compras.md) produce las compras confirmadas, recibidas y anuladas de las API 5 y 6; `purchase_id` abre el detalle de cada compra. Confirmar y recibir son pasos distintos: solo la categoría `RECEIVED` es mercancía en inventario.
- [Inventario](inventario.md) produce los movimientos que explican las API 7 y 8; el kardex de Inventario da el detalle movimiento a movimiento, y las consultas de existencias actuales, productos bajo el mínimo e indicadores del tablero son de Product Inventory Query y están documentadas allí.
- [Productos y precios](productos-y-precios.md) aporta el `company_product_id`, el código y el nombre de los productos, y Product Catalog la unidad base en la que se expresan las cantidades.
- [Administración empresarial](administracion-empresarial.md): la membresía, la zona horaria de la empresa y de las sucursales (que fija el corte de los días) y los nombres de sucursal salen de Operational Context.
- [Acceso y contexto operativo](acceso-y-contexto-operativo.md): el usuario necesita el permiso del reporte y el permiso de lectura del servicio dueño en su token; en el realm de desarrollo los tienen los grupos `administradores`, `supervisores` y `reportes` (además `ventas` para las API 1 y 2, `compras` para 5 y 6 e `inventario` para 7 y 8).

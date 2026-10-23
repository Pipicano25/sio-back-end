# 6.8 Inventario

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que un usuario de la empresa consulta las existencias de la empresa y de cada sucursal, encuentra productos con disponibilidad, sigue los movimientos de un producto (kardex), conoce el valor del inventario y ejecuta las operaciones manuales: ajustes, conteos físicos y mínimos por producto. Intervienen dos servicios:

| Parte | Servicio | Qué guarda o calcula | Alcance |
|---|---|---|---|
| **Vista para el frontend** (producto + precio + existencias) | [Product Inventory Query](../servicios/product-inventory-query.md) | Nada propio: combina en una sola respuesta los datos de Commercial Relationship, Product Catalog e Inventory; sin costos | Empresa y sucursales; paginación por cursor |
| **Propietario de las existencias** | [Inventory](../servicios/inventory.md) | Saldos por sucursal y producto, movimientos (kardex), capas de costo FIFO, ajustes, conteos físicos y políticas de mínimo | Empresa y sucursal; paginación por página |

Las existencias **entran** por la recepción de [Compras](compras.md) y **salen** por la confirmación de [Ventas](ventas.md); esas operaciones las invocan Purchase y Sales con su cuenta técnica (Inventory 3–6) y **no** se llaman desde el frontend. Flujo de uso: [Consultar inventario](../ejemplos/consultar-inventario.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Buscar productos con precio y existencias | `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/product-overviews` y `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews` | `perm:product-inventory-query:product_overviews:read` | [PIQS 3](../servicios/product-inventory-query.md#3-get-companiescompany_idproduct-overviews) · [PIQS 4](../servicios/product-inventory-query.md#4-get-companiescompany_idbranchesbranch_idproduct-overviews) |
| 2 | Consultar existencias por producto, sucursal y empresa | `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-overviews` y `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-overviews` | `perm:product-inventory-query:inventory_overviews:read` | [PIQS 5](../servicios/product-inventory-query.md#5-get-companiescompany_idinventory-overviews) · [PIQS 6](../servicios/product-inventory-query.md#6-get-companiescompany_idbranchesbranch_idinventory-overviews) |
| 3 | Consultar productos bajo el mínimo | `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/low-stock-products` y `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/low-stock-products` | `perm:product-inventory-query:low_stock_products:read` + `perm:product-inventory-query:stock:read` + `perm:inventory:product-policies:read` | [PIQS 7](../servicios/product-inventory-query.md#7-get-companiescompany_idlow-stock-products) · [PIQS 8](../servicios/product-inventory-query.md#8-get-companiescompany_idbranchesbranch_idlow-stock-products) |
| 4 | Consultar los indicadores de inventario | `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-summary` y `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-summary` | `perm:product-inventory-query:inventory_summary:read` | [PIQS 9](../servicios/product-inventory-query.md#9-get-companiescompany_idinventory-summary) · [PIQS 10](../servicios/product-inventory-query.md#10-get-companiescompany_idbranchesbranch_idinventory-summary) |
| 5 | Consultar los saldos de una sucursal | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances` | `perm:inventory:balances:read` | [Inv 7](../servicios/inventory.md#7-get-companiescompany_idbranchesbranch_idbalances) |
| 6 | Consultar el saldo de un producto en una sucursal | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}` | `perm:inventory:balances:read` | [Inv 8](../servicios/inventory.md#8-get-companiescompany_idbranchesbranch_idbalancescompany_product_id) |
| 7 | Consultar el kardex de un producto | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}` | `perm:inventory:movements:read` | [Inv 10](../servicios/inventory.md#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id) |
| 8 | Consultar el valor del inventario de una sucursal | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/valuation` | `perm:inventory:valuation:read` | [Inv 13](../servicios/inventory.md#13-get-companiescompany_idbranchesbranch_idvaluation) |
| 9 | Registrar un ajuste manual | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments` | `perm:inventory:adjustments:create` + asignación `ACTIVE` a la sucursal | [Inv 16](../servicios/inventory.md#16-post-companiescompany_idinventory-adjustments) |
| 10 | Consultar los ajustes | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments` | `perm:inventory:adjustments:read` | [Inv 17](../servicios/inventory.md#17-get-companiescompany_idinventory-adjustments) |
| 11 | Crear un conteo físico | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts` | `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal | [Inv 19](../servicios/inventory.md#19-post-companiescompany_idinventory-counts) |
| 12 | Iniciar el conteo | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/start` | `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal | [Inv 21](../servicios/inventory.md#21-post-companiescompany_idinventory-countscount_idstart) |
| 13 | Registrar la cantidad contada de un producto | `PUT https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}` | `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal | [Inv 22](../servicios/inventory.md#22-put-companiescompany_idinventory-countscount_iddetailscompany_product_id) |
| 14 | Completar el conteo | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/complete` | `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal | [Inv 23](../servicios/inventory.md#23-post-companiescompany_idinventory-countscount_idcomplete) |
| 15 | Cancelar el conteo | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/cancel` | `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal | [Inv 24](../servicios/inventory.md#24-post-companiescompany_idinventory-countscount_idcancel) |
| 16 | Consultar los conteos | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts` | `perm:inventory:counts:read` | [Inv 20](../servicios/inventory.md#20-get-companiescompany_idinventory-counts) |
| 17 | Consultar un conteo | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}` | `perm:inventory:counts:read` | [Inv 25](../servicios/inventory.md#25-get-companiescompany_idinventory-countscount_id) |
| 18 | Consultar las políticas de mínimo | `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies` | `perm:inventory:product-policies:read` | [Inv 29](../servicios/inventory.md#29-get-companiescompany_idinventory-policies) |
| 19 | Definir el mínimo de un producto en una sucursal | `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies` | `perm:inventory:product-policies:update` | [Inv 30](../servicios/inventory.md#30-post-companiescompany_idinventory-policies) |

Operaciones relacionadas que no se consideran principales (ver la [ficha de Inventory](../servicios/inventory.md)): aplicar y revertir entradas y salidas (Inv 3–6, solo cuentas técnicas de Purchase y Sales), saldos por lotes (Inv 9), operaciones por id o por clave (Inv 11, 12), capas FIFO y consumos de costo (Inv 14, 15), ajuste por id (Inv 18), política general de la empresa (Inv 26–28), consultar, modificar o inactivar una política de producto (Inv 31–33), consultas por lotes de políticas y conjuntos de productos (Inv 34, 35), indicadores detallados (Inv 36) y la evolución de existencias (Inv 37, 38), que se consulta desde [Reportes](reportes.md).

Orden habitual para un conteo físico: [API 5](#5-consultar-los-saldos-de-una-sucursal) (productos con saldo en la sucursal) → [API 11](#11-crear-un-conteo-físico) (crear en `DRAFT`) → [API 12](#12-iniciar-el-conteo) (pasar a `IN_PROGRESS`) → [API 13](#13-registrar-la-cantidad-contada-de-un-producto) por cada producto contado → [API 14](#14-completar-el-conteo) (aplicar las diferencias) o [API 15](#15-cancelar-el-conteo). Para mantener mínimos: [API 19](#19-definir-el-mínimo-de-un-producto-en-una-sucursal) → [API 3](#3-consultar-productos-bajo-el-mínimo) (productos que quedan por debajo).

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `INVENTORY.FORBIDDEN` o `PRODUCT_INVENTORY_QUERY.FORBIDDEN` cuando el token no tiene el permiso indicado (mostrar que faltan permisos y el `trace_id`); `503` con `code` `INVENTORY.DEPENDENCY_UNAVAILABLE` o `PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde (reintentar más tarde; nada se guarda). Inventory agrega la extensión `dependency` (`database`, `operational-context`, `commercial-relationship`); Product Inventory Query no la agrega. Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `INVENTORY.…` o `PRODUCT_INVENTORY_QUERY.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).
- **Unidad base.** Inventory lleva las existencias en la unidad base del producto empresarial (`company_product_id`), nunca por presentación. Una venta de 2 cajas de 100 unidades descuenta 200 unidades base. Las cantidades y los costos unitarios se devuelven como texto con 4 decimales (`"200.0000"`, `"595.0000"`) y los valores monetarios con 2 (`"1190.00"`); al enviar cantidades se aceptan número o texto, mayores que cero, con hasta 4 decimales.
- **Control de inventario por producto.** Solo los productos con `inventory_control_enabled: true`, configurado al adoptarlos en [Productos y precios](productos-y-precios.md), admiten ajustes, conteos y políticas; con otro producto Inventory responde `422 INVENTORY.VALIDATION_ERROR` con `errors[].code` `INVENTORY_CONTROL_DISABLED`.
- **Costeo FIFO.** Cada entrada abre una capa de costo y las salidas consumen primero las capas más antiguas. `average_unit_cost` e `inventory_value` se calculan sobre las capas abiertas; `has_unknown_cost: true` indica que hay unidades sin costo conocido.
- **Alcance.** Las lecturas exigen membresía `ACTIVE` en la empresa, sin asignación a la sucursal; sin membresía la respuesta es `404 …NOT_FOUND`, igual que si la empresa no existiera. Los ajustes y conteos exigen además un **usuario humano** (un token de cuenta de servicio recibe `403 INVENTORY.FORBIDDEN`) con asignación `ACTIVE` a la sucursal en una sucursal y empresa activas; si falta, `403 INVENTORY.BRANCH_ACCESS_DENIED`. Una sucursal de otra empresa responde `404 INVENTORY.NOT_FOUND`. Las políticas de mínimo exigen usuario humano y membresía.
- **Idempotencia.** Los ajustes llevan `adjustment_key` y la finalización de conteos `completion_key`: UUID que genera el frontend, uno por operación. Repetir la llamada con la misma clave y el mismo cuerpo devuelve el resultado original sin duplicar movimientos; la misma clave con otro cuerpo responde `409 INVENTORY.OPERATION_KEY_CONFLICT`.
- **Control de versión.** Iniciar, completar y cancelar un conteo envían la `version` actual; si otra persona lo cambió antes, la API responde `409 INVENTORY.VERSION_CONFLICT` y el frontend debe volver a leer el conteo y repetir con la nueva `version`.
- **Paginación.** Inventory pagina con `page` (desde `1`) y `page_size` (`1` a `100`, por defecto `20`) y responde `items`, `page`, `page_size`, `total_records` y `total_pages`. Product Inventory Query pagina por cursor: `page_size` de `1` a `20` y `cursor` con el `next_cursor` de la página anterior; ver la [API 1](#1-buscar-productos-con-precio-y-existencias).
- Las escrituras quedan registradas en [Audit](../servicios/audit.md) con las acciones `CREATE_INVENTORY_ADJUSTMENT` (entidad `InventoryAdjustment`), `START_INVENTORY_COUNT`, `COMPLETE_INVENTORY_COUNT` y `CANCEL_INVENTORY_COUNT` (entidad `InventoryCount`) y `CREATE_INVENTORY_POLICY` (entidad `InventoryPolicy`); se consultan con la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (lista los eventos de auditoría de la empresa; sus errores están en esa sección).

---

## 1. Buscar productos con precio y existencias

**Método:** `GET`
**URL:** `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/product-overviews` (todas las sucursales activas o las indicadas en `branch_id`) y `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews` (una sucursal)
**Permiso requerido:** `perm:product-inventory-query:product_overviews:read`

### ¿Qué hace esta API?

Devuelve en una sola consulta el catálogo de la empresa con lo que necesita una pantalla de productos de ventas, compras o inventario: nombre, códigos, marca, categorías, identificadores (códigos de barras), imagen, presentaciones con su precio en la lista indicada y existencias por sucursal. Product Inventory Query no guarda datos: los combina desde Commercial Relationship (productos, presentaciones y precios), Product Catalog (datos globales e imagen) e Inventory (existencias y mínimos). **No devuelve costos.**

Efectos verificados en el código: la respuesta incluye o **omite** bloques según los permisos del usuario, nunca los envía con `null` por falta de permiso. `presentations[].price` aparece solo con `perm:commercial-relationship:price_list_items:read`; `stock` solo con `perm:product-inventory-query:stock:read`; `stock.branches[].minimum_stock` y `minimum_state` solo con `perm:inventory:product-policies:read`. Un producto sin control de inventario trae `stock: null`. La paginación es por cursor: no hay total de registros; se pide la página siguiente con `cursor` igual al `next_cursor` recibido. Si cambian los filtros, el orden o `page_size`, o el cursor venció (900 s), la respuesta trae `pagination_reset: true` y empieza desde la primera página. Si la consulta alcanza el límite de trabajo (5 s), responde con `partial: true` y un `next_cursor` para continuar. No escribe nada ni genera auditoría.

Antes necesita: `company_id` con membresía `ACTIVE`; para la variante por sucursal, un `branch_id` de esa empresa. No exige asignación a la sucursal. Para mostrar precios, el `price_list_id` de la lista elegida ([price_list_id](../parametros/price-list-id.md)).

### ¿Cómo se realiza la solicitud?

Toda la empresa, con precio de una lista:

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/product-overviews?search=acetaminofen&status=ACTIVE&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Una sucursal, solo productos con existencia:

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/product-overviews?stock_state=IN_STOCK&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa cuyo catálogo se consulta | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí, solo en la URL por sucursal | Sucursal cuyas existencias se muestran; debe pertenecer a la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `search` | string (≤ 200) | No | Búsqueda en el nombre, `internal_code`, `reference_code` o SKU de presentación | Texto libre; p. ej. `acetaminofen` o `PRD-0001` | `?search=acetaminofen` | Interfaz (texto que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado del producto empresarial | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `price_list_id` | UUID | No; recomendado para mostrar precios | Lista de precios cuyo precio se devuelve en `presentations[].price` | UUID de una lista de la empresa; p. ej. `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | Lista de precios elegida en [Productos y precios](productos-y-precios.md) · guía [price_list_id](../parametros/price-list-id.md) |
| `page_size` | integer 1–20 | No; por defecto `20` | Productos por página | Entero de `1` a `20`; p. ej. `20` | `&page_size=20` | Interfaz |
| `cursor` | string (≤ 2048) | No | Cursor opaco de la página siguiente; se envía sin modificar y con los mismos filtros, orden y `page_size` | Valor de `next_cursor`; p. ej. `eyJ2IjoxfQ` (ilustrativo) | `&cursor=eyJ2IjoxfQ` | `next_cursor` de la respuesta anterior de esta misma API |
| `branch_id` | UUID, repetible (hasta 100) | No; solo en la URL de empresa; excluyente con `scope` | Limita las existencias a esas sucursales; admite sucursales inactivas | UUID de una sucursal de la empresa; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (repetir para varias) | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `scope` | `COMPANY` | No; por defecto `COMPANY`; solo en la URL de empresa | Todas las sucursales activas de la empresa; excluyente con `branch_id` | Único valor: `COMPANY` (por defecto) | `&scope=COMPANY` | Interfaz |
| `internal_code` | string (≤ 60) | No | Código interno exacto, sin distinguir mayúsculas | Texto; p. ej. `PRD-0001` | `&internal_code=PRD-0001` | Interfaz (lector o campo de código) |
| `sku` | string (≤ 80) | No | SKU exacto de una presentación | Texto; p. ej. `7701234567890` | `&sku=7701234567890` | Interfaz |
| `barcode` | string (≤ 120) | No | Código de barras exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&barcode=7701234567890` | Interfaz (lector de código de barras) |
| `identifier` | string (≤ 120) | No | Identificador global exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&identifier=7701234567890` | Interfaz |
| `brand_id` | UUID, repetible (hasta 100) | No | Marca; varias marcas se combinan con O | UUID de una marca; p. ej. `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `&brand_id=b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` (repetir para varias) | `items[].brand.id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (marca de cada producto; errores en §1) o el catálogo de marcas de [Productos y precios](productos-y-precios.md) |
| `category_id` | UUID, repetible (hasta 100) | No | Categoría; varias categorías se combinan con O | UUID de una categoría; p. ej. `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `&category_id=c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` (repetir para varias) | `items[].categories[].id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (categorías de cada producto; errores en §1) o el catálogo de categorías de [Productos y precios](productos-y-precios.md) |
| `include_descendants` | boolean | No | Incluye las subcategorías de `category_id` | `true` o `false`; p. ej. `true` | `&include_descendants=true` | Interfaz |
| `product_type` | string (≤ 20) | No | Tipo de producto de Product Catalog | Valor definido por Product Catalog (lista exacta NO VERIFICADO); p. ej. `GOOD` | `&product_type=GOOD` | `items[].product_type` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (tipo de cada producto; errores en §1) |
| `has_image` | boolean | No | Solo productos con (`true`) o sin (`false`) imagen principal | `true` o `false`; p. ej. `true` | `&has_image=true` | Interfaz |
| `stock_state` | `IN_STOCK` \| `OUT_OF_STOCK` | No | Solo productos con existencia total mayor que cero (`IN_STOCK`) o en cero (`OUT_OF_STOCK`); exige `perm:product-inventory-query:stock:read` | Uno de: `IN_STOCK`, `OUT_OF_STOCK`; p. ej. `IN_STOCK` | `&stock_state=IN_STOCK` | Interfaz (solo si el usuario ve existencias) |
| `sort` | string | No; por defecto según los filtros (ver `sort_applied`) | Orden de la lista | `display_name`, `internal_code` o `created_at` seguidos de `:asc` o `:desc`; p. ej. `display_name:asc` | `&sort=display_name:asc` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/product-overviews?search=acetaminofen&status=ACTIVE&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CursorPage[ProductOverview]`; token con los tres bloques):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {"id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "GEN", "name": "Genérico"},
      "categories": [
        {"id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f", "code": "ANALG", "name": "Analgésicos", "is_primary": true}
      ],
      "identifiers": [
        {"type": "EAN13", "value": "7701234567890", "is_primary": true, "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94"}
      ],
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "has_image": true,
      "image_url": "https://sio-product-catalog-dev.onrender.com/public/product-images/firma-ilustrativa",
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
          "code": "UN",
          "name": "Unidad",
          "sku": "7701234567890",
          "internal_code": "PRD-0001-U",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "price": {
            "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
            "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
            "unit_price": "800.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        }
      ],
      "stock": {
        "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
        "total_base_quantity": "800.0000",
        "branches": [
          {
            "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "base_quantity": "800.0000",
            "balance_state": "REGISTERED",
            "minimum_stock": "100.0000",
            "minimum_state": "ABOVE_MINIMUM"
          }
        ],
        "equivalences": [
          {"company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83", "whole_units": 800, "remainder_base_quantity": "0.0000"}
        ]
      }
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-20T15:40:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_id` | UUID | El [company_product_id](../parametros/company-product-id.md) que se usa en ventas, compras, ajustes, conteos y políticas |
| `items[].display_name`, `internal_code`, `reference_code` | string \| null | Nombre y códigos de la empresa para mostrar y buscar |
| `items[].status`, `global_status` | string | Estado del producto empresarial y del producto global |
| `items[].brand`, `categories[]`, `identifiers[]`, `base_unit` | objeto \| lista | Datos del catálogo global: marca, categorías (con la principal), códigos de barras u otros identificadores y unidad base |
| `items[].has_image`, `image_url` | boolean, string \| null | Imagen principal; la URL se usa tal cual y es `null` si `has_image` es `false`. Spec 024 (pendiente de despliegue): pasan a cada presentación (`presentations[].has_image`, `asset_id`, `image_url`); ver [Product Inventory Query](../servicios/product-inventory-query.md#imágenes-por-presentación-spec-024-pendiente-de-despliegue) |
| `items[].presentations[]` | lista | Presentaciones con `company_product_presentation_id` ([guía](../parametros/company-product-presentation-id.md)), `sku`, `is_sellable` y `base_quantity_factor` (unidades base por presentación) |
| `items[].presentations[].price` | objeto | Solo con permiso de precios. `unit_price` tiene valor cuando `resolution` es `PRICE_LIST_ITEM`; con `NO_PRICE_IN_LIST`, `NO_APPLICABLE_PRICE_LIST` o `PRICE_LIST_NOT_APPLICABLE` viene `null` |
| `items[].stock` | objeto \| null | Solo con permiso de existencias; `null` si el producto no tiene control de inventario |
| `items[].stock.total_base_quantity` | string | Existencia total en unidad base de las sucursales consultadas |
| `items[].stock.branches[]` | lista | Por sucursal: `base_quantity`, `balance_state` (`REGISTERED` hay saldo registrado aunque sea cero; `NOT_REGISTERED` nunca tuvo movimientos) y, con permiso de políticas, `minimum_stock` y `minimum_state` (`NO_POLICY`, `BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM`) |
| `items[].stock.equivalences[]` | lista | Cuántas unidades enteras de cada presentación caben en el total (`whole_units`) y el resto en unidad base |
| `page_size`, `has_next`, `next_cursor` | integer, boolean, string \| null | Tamaño de página, si hay más resultados y cursor para pedir la página siguiente (`null` al final) |
| `pagination_reset`, `pagination_reset_reason` | boolean, string \| null | `true` cuando se reinició la paginación por `FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED` o `CURSOR_EXPIRED` (900 s): descartar las páginas ya mostradas |
| `partial`, `partial_reason` | boolean, string \| null | `true` con `WORK_LIMIT_REACHED` cuando la página se cortó por el límite de trabajo (5 s): seguir pidiendo con `next_cursor`; no es el final |
| `sort_applied` | string | Orden aplicado. Sin `sort` depende de los filtros: `display_name:asc` sin filtros, `canonical_name:asc` con código de barras, identificador o filtros de catálogo, `company_product_id:asc` con `stock_state=IN_STOCK` o un `minimum_state` distinto de `NO_POLICY`, y `shortfall:desc` en la [API 3](#3-consultar-productos-bajo-el-mínimo) |
| `resolved_at` | date-time | Momento en que se resolvió la consulta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_INVENTORY_QUERY.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o el `branch_id` es de otra empresa (`detail`: «La empresa o la sucursal no existe o no tiene acceso.») | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `422` | `PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR` | Parámetro desconocido o de otra API (`UNKNOWN_FIELD`), `branch_id` junto con `scope`, `branch_id` o `scope` en la URL por sucursal, parámetro no repetible enviado dos veces (`INVALID_FORMAT`), `page_size` fuera de 1–20 o texto más largo que su límite | Corregir la consulta; el detalle viene en `errors[]` con `field` |
| `422` | `PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` | El cursor está alterado o es de otra consulta (`detail`: «El cursor no es válido. Repita la consulta sin cursor.») | Repetir la consulta sin `cursor` desde la primera página |
| `403` | `PRODUCT_INVENTORY_QUERY.FORBIDDEN` | Se usó `stock_state` sin `perm:product-inventory-query:stock:read` (`detail`: «No tiene permiso para usar este filtro.») | No ofrecer ese filtro a perfiles sin el bloque de existencias |

Ejemplo de `422` por enviar `branch_id` y `scope` a la vez:

```json
{
  "type": "https://sio/errors/product-inventory-query/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene parámetros inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/product-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "query",
      "message": "Use `branch_id` o `scope=COMPANY`, no ambos.",
      "code": "INVALID_FORMAT"
    }
  ]
}
```

## 2. Consultar existencias por producto, sucursal y empresa

**Método:** `GET`
**URL:** `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-overviews` (todas las sucursales activas o las indicadas en `branch_id`) y `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-overviews` (una sucursal)
**Permiso requerido:** `perm:product-inventory-query:inventory_overviews:read`

### ¿Qué hace esta API?

Muestra cuánto hay de cada producto en cada sucursal y el total consolidado, **sin precios ni costos**. Es la pantalla de existencias del módulo: devuelve la misma identificación del producto que la [API 1](#1-buscar-productos-con-precio-y-existencias) con sus presentaciones sin precio y el bloque `stock` con el detalle por sucursal. Admite además el filtro `minimum_state` para encontrar productos frente a su mínimo.

Efectos verificados en el código: `stock` aparece solo con `perm:product-inventory-query:stock:read` y los mínimos por sucursal solo con `perm:inventory:product-policies:read`; el filtro `stock_state` exige el primer permiso y `minimum_state` el segundo (`403` si faltan). `price_list_id` no se admite aquí (`422 UNKNOWN_FIELD`). Paginación por cursor igual que en la [API 1](#1-buscar-productos-con-precio-y-existencias). No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE` y, para la variante por sucursal, un `branch_id` de la empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-overviews?scope=COMPANY&minimum_state=BELOW_MINIMUM&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa cuyas existencias se consultan | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí, solo en la URL por sucursal | Sucursal cuyas existencias se muestran | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `scope` | `COMPANY` | No; por defecto `COMPANY`; solo en la URL de empresa | Todas las sucursales activas de la empresa; excluyente con `branch_id` | Único valor: `COMPANY` (por defecto) | `?scope=COMPANY` | Interfaz |
| `minimum_state` | `NO_POLICY` \| `BELOW_MINIMUM` \| `AT_MINIMUM` \| `ABOVE_MINIMUM` | No | Productos que, en al menos una sucursal consultada, no tienen política, están por debajo, en o por encima del mínimo; exige `perm:inventory:product-policies:read` | Uno de: `NO_POLICY`, `BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM`; p. ej. `BELOW_MINIMUM` | `&minimum_state=BELOW_MINIMUM` | Interfaz (solo si el usuario ve mínimos) |
| `page_size` | integer 1–20 | No; por defecto `20` | Productos por página | Entero de `1` a `20`; p. ej. `20` | `&page_size=20` | Interfaz |
| `cursor` | string (≤ 2048) | No | Cursor opaco de la página siguiente; se envía sin modificar y con los mismos filtros, orden y `page_size` | Valor de `next_cursor`; p. ej. `eyJ2IjoxfQ` (ilustrativo) | `&cursor=eyJ2IjoxfQ` | `next_cursor` de la respuesta anterior de esta misma API |
| `branch_id` | UUID, repetible (hasta 100) | No; solo en la URL de empresa; excluyente con `scope` | Limita las existencias a esas sucursales; admite sucursales inactivas | UUID de una sucursal de la empresa; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (repetir para varias) | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `search` | string (≤ 200) | No | Búsqueda en el nombre, `internal_code`, `reference_code` o SKU de presentación | Texto libre; p. ej. `acetaminofen` | `&search=acetaminofen` | Interfaz (texto que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado del producto empresarial | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `internal_code` | string (≤ 60) | No | Código interno exacto, sin distinguir mayúsculas | Texto; p. ej. `PRD-0001` | `&internal_code=PRD-0001` | Interfaz (lector o campo de código) |
| `sku` | string (≤ 80) | No | SKU exacto de una presentación | Texto; p. ej. `7701234567890` | `&sku=7701234567890` | Interfaz |
| `barcode` | string (≤ 120) | No | Código de barras exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&barcode=7701234567890` | Interfaz (lector de código de barras) |
| `identifier` | string (≤ 120) | No | Identificador global exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&identifier=7701234567890` | Interfaz |
| `brand_id` | UUID, repetible (hasta 100) | No | Marca; varias marcas se combinan con O | UUID de una marca; p. ej. `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `&brand_id=b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` (repetir para varias) | `items[].brand.id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (marca de cada producto; errores en §1) o el catálogo de marcas de [Productos y precios](productos-y-precios.md) |
| `category_id` | UUID, repetible (hasta 100) | No | Categoría; varias categorías se combinan con O | UUID de una categoría; p. ej. `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `&category_id=c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` (repetir para varias) | `items[].categories[].id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (categorías de cada producto; errores en §1) o el catálogo de categorías de [Productos y precios](productos-y-precios.md) |
| `include_descendants` | boolean | No | Incluye las subcategorías de `category_id` | `true` o `false`; p. ej. `true` | `&include_descendants=true` | Interfaz |
| `product_type` | string (≤ 20) | No | Tipo de producto de Product Catalog | Valor definido por Product Catalog (lista exacta NO VERIFICADO); p. ej. `GOOD` | `&product_type=GOOD` | `items[].product_type` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (tipo de cada producto; errores en §1) |
| `has_image` | boolean | No | Solo productos con (`true`) o sin (`false`) imagen principal | `true` o `false`; p. ej. `true` | `&has_image=true` | Interfaz |
| `stock_state` | `IN_STOCK` \| `OUT_OF_STOCK` | No | Solo productos con existencia total mayor que cero o en cero; exige `perm:product-inventory-query:stock:read` | Uno de: `IN_STOCK`, `OUT_OF_STOCK`; p. ej. `OUT_OF_STOCK` | `&stock_state=OUT_OF_STOCK` | Interfaz |
| `sort` | string | No; por defecto según los filtros (ver `sort_applied`) | Orden de la lista | `display_name`, `internal_code` o `created_at` seguidos de `:asc` o `:desc`; p. ej. `display_name:asc` | `&sort=display_name:asc` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-overviews?scope=COMPANY&minimum_state=BELOW_MINIMUM&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CursorPage[InventoryOverview]`):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {"id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "GEN", "name": "Genérico"},
      "categories": [
        {"id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f", "code": "ANALG", "name": "Analgésicos", "is_primary": true}
      ],
      "identifiers": [],
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "has_image": false,
      "image_url": null,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
          "code": "CJ100",
          "name": "Caja x 100",
          "sku": "7701234567891",
          "internal_code": "PRD-0001-C",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "100.0000"
        }
      ],
      "stock": {
        "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
        "total_base_quantity": "250.0000",
        "branches": [
          {
            "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "base_quantity": "250.0000",
            "balance_state": "REGISTERED",
            "minimum_stock": "300.0000",
            "minimum_state": "BELOW_MINIMUM"
          }
        ],
        "equivalences": [
          {"company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83", "whole_units": 2, "remainder_base_quantity": "50.0000"}
        ]
      }
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "company_product_id:asc",
  "resolved_at": "2026-10-20T15:40:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_id` | UUID | Producto empresarial; con él se consulta el saldo exacto ([API 6](#6-consultar-el-saldo-de-un-producto-en-una-sucursal)) o el kardex ([API 7](#7-consultar-el-kardex-de-un-producto)) |
| `items[].presentations[]` | lista | Presentaciones **sin** precio |
| `items[].stock.total_base_quantity` | string | Total en unidad base de las sucursales consultadas |
| `items[].stock.branches[]` | lista | `base_quantity`, `balance_state` y, con permiso de políticas, `minimum_stock` y `minimum_state` por sucursal |
| `items[].stock.equivalences[]` | lista | Unidades enteras de cada presentación y resto en unidad base; en el ejemplo, 250 unidades son 2 cajas de 100 y 50 unidades |
| `page_size`, `has_next`, `next_cursor` | integer, boolean, string \| null | Tamaño de página, si hay más resultados y cursor para pedir la página siguiente (`null` al final) |
| `pagination_reset`, `pagination_reset_reason` | boolean, string \| null | `true` cuando se reinició la paginación por `FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED` o `CURSOR_EXPIRED` (900 s): descartar las páginas ya mostradas |
| `partial`, `partial_reason` | boolean, string \| null | `true` con `WORK_LIMIT_REACHED` cuando la página se cortó por el límite de trabajo (5 s): seguir pidiendo con `next_cursor`; no es el final |
| `sort_applied` | string | Orden aplicado. Sin `sort` depende de los filtros: `display_name:asc` sin filtros, `canonical_name:asc` con código de barras, identificador o filtros de catálogo, `company_product_id:asc` con `stock_state=IN_STOCK` o un `minimum_state` distinto de `NO_POLICY`, y `shortfall:desc` en la [API 3](#3-consultar-productos-bajo-el-mínimo) |
| `resolved_at` | date-time | Momento en que se resolvió la consulta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_INVENTORY_QUERY.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o el `branch_id` es de otra empresa (`detail`: «La empresa o la sucursal no existe o no tiene acceso.») | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `422` | `PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR` | Parámetro desconocido o de otra API (`UNKNOWN_FIELD`), `branch_id` junto con `scope`, `branch_id` o `scope` en la URL por sucursal, parámetro no repetible enviado dos veces (`INVALID_FORMAT`), `page_size` fuera de 1–20 o texto más largo que su límite | Corregir la consulta; el detalle viene en `errors[]` con `field` |
| `422` | `PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` | El cursor está alterado o es de otra consulta (`detail`: «El cursor no es válido. Repita la consulta sin cursor.») | Repetir la consulta sin `cursor` desde la primera página |
| `403` | `PRODUCT_INVENTORY_QUERY.FORBIDDEN` | Se usó `stock_state` sin permiso de existencias o `minimum_state` sin `perm:inventory:product-policies:read` (`detail`: «No tiene permiso para usar este filtro.») | No ofrecer esos filtros a perfiles sin el bloque correspondiente |

Ejemplo de `403` por filtro no autorizado:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "No tiene permiso para usar este filtro.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 3. Consultar productos bajo el mínimo

**Método:** `GET`
**URL:** `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/low-stock-products` (todas las sucursales activas o las indicadas en `branch_id`) y `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/low-stock-products` (una sucursal)
**Permiso requerido:** `perm:product-inventory-query:low_stock_products:read` + `perm:product-inventory-query:stock:read` + `perm:inventory:product-policies:read`

### ¿Qué hace esta API?

Lista los pares producto–sucursal que necesitan reposición: los que tienen una **política de mínimo activa** ([API 19](#19-definir-el-mínimo-de-un-producto-en-una-sucursal)) y una existencia **estrictamente menor** que ese mínimo. Cada fila trae la existencia, el mínimo y el faltante. Es la lista de trabajo para preparar compras; la API no crea compras ni sugerencias.

Efectos verificados en el código: un producto con existencia igual al mínimo **no** aparece; un producto sin política tampoco. El orden predeterminado es `shortfall:desc` (mayor faltante primero). Sin los tres permisos la respuesta es `403`. Paginación por cursor igual que en la [API 1](#1-buscar-productos-con-precio-y-existencias). No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`; políticas de mínimo creadas con la [API 19](#19-definir-el-mínimo-de-un-producto-en-una-sucursal).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/low-stock-products?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa consultada | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí, solo en la URL por sucursal | Sucursal consultada | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `branch_id` | UUID, repetible (hasta 100) | No; solo en la URL de empresa; excluyente con `scope` | Limita la consulta a esas sucursales; admite sucursales inactivas | UUID de una sucursal de la empresa; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (repetir para varias) | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `scope` | `COMPANY` | No; por defecto `COMPANY`; solo en la URL de empresa | Todas las sucursales activas de la empresa; excluyente con `branch_id` | Único valor: `COMPANY` (por defecto) | `&scope=COMPANY` | Interfaz |
| `page_size` | integer 1–20 | No; por defecto `20` | Productos por página | Entero de `1` a `20`; p. ej. `20` | `&page_size=20` | Interfaz |
| `cursor` | string (≤ 2048) | No | Cursor opaco de la página siguiente; se envía sin modificar y con los mismos filtros, orden y `page_size` | Valor de `next_cursor`; p. ej. `eyJ2IjoxfQ` (ilustrativo) | `&cursor=eyJ2IjoxfQ` | `next_cursor` de la respuesta anterior de esta misma API |
| `search` | string (≤ 200) | No | Búsqueda en el nombre, `internal_code`, `reference_code` o SKU de presentación | Texto libre; p. ej. `acetaminofen` | `&search=acetaminofen` | Interfaz (texto que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado del producto empresarial | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `internal_code` | string (≤ 60) | No | Código interno exacto, sin distinguir mayúsculas | Texto; p. ej. `PRD-0001` | `&internal_code=PRD-0001` | Interfaz (lector o campo de código) |
| `sku` | string (≤ 80) | No | SKU exacto de una presentación | Texto; p. ej. `7701234567890` | `&sku=7701234567890` | Interfaz |
| `barcode` | string (≤ 120) | No | Código de barras exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&barcode=7701234567890` | Interfaz (lector de código de barras) |
| `identifier` | string (≤ 120) | No | Identificador global exacto (Product Catalog) | Texto; p. ej. `7701234567890` | `&identifier=7701234567890` | Interfaz |
| `brand_id` | UUID, repetible (hasta 100) | No | Marca; varias marcas se combinan con O | UUID de una marca; p. ej. `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `&brand_id=b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` (repetir para varias) | `items[].brand.id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (marca de cada producto; errores en §1) o el catálogo de marcas de [Productos y precios](productos-y-precios.md) |
| `category_id` | UUID, repetible (hasta 100) | No | Categoría; varias categorías se combinan con O | UUID de una categoría; p. ej. `c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` | `&category_id=c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f` (repetir para varias) | `items[].categories[].id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (categorías de cada producto; errores en §1) o el catálogo de categorías de [Productos y precios](productos-y-precios.md) |
| `include_descendants` | boolean | No | Incluye las subcategorías de `category_id` | `true` o `false`; p. ej. `true` | `&include_descendants=true` | Interfaz |
| `product_type` | string (≤ 20) | No | Tipo de producto de Product Catalog | Valor definido por Product Catalog (lista exacta NO VERIFICADO); p. ej. `GOOD` | `&product_type=GOOD` | `items[].product_type` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (tipo de cada producto; errores en §1) |
| `has_image` | boolean | No | Solo productos con (`true`) o sin (`false`) imagen principal | `true` o `false`; p. ej. `true` | `&has_image=true` | Interfaz |
| `sort` | string | No; por defecto `shortfall:desc` | Orden alternativo de la lista | `display_name`, `internal_code` o `created_at` seguidos de `:asc` o `:desc`; p. ej. `display_name:asc` | `&sort=display_name:asc` | Interfaz |

No admite `stock_state`, `minimum_state` ni `price_list_id` (`422 UNKNOWN_FIELD`).

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/low-stock-products?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CursorPage[LowStockPair]`):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "display_name": "Acetaminofén 500 mg",
      "internal_code": "PRD-0001",
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "base_quantity": "250.0000",
      "minimum_stock": "300.0000",
      "shortfall": "50.0000",
      "policy_status": "ACTIVE",
      "has_image": false,
      "image_url": null
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "shortfall:desc",
  "resolved_at": "2026-10-20T15:40:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_id`, `display_name`, `internal_code`, `base_unit` | — | Producto que está por debajo del mínimo |
| `items[].branch_id` | UUID | Sucursal en la que falta |
| `items[].base_quantity` | string | Existencia actual en unidad base |
| `items[].minimum_stock` | string | Mínimo de la política activa |
| `items[].shortfall` | string | Faltante: `minimum_stock` − `base_quantity`; siempre mayor que cero |
| `items[].policy_status` | `ACTIVE` | Siempre `ACTIVE`: solo cuentan políticas activas |
| `page_size`, `has_next`, `next_cursor` | integer, boolean, string \| null | Tamaño de página, si hay más resultados y cursor para pedir la página siguiente (`null` al final) |
| `pagination_reset`, `pagination_reset_reason` | boolean, string \| null | `true` cuando se reinició la paginación por `FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED` o `CURSOR_EXPIRED` (900 s): descartar las páginas ya mostradas |
| `partial`, `partial_reason` | boolean, string \| null | `true` con `WORK_LIMIT_REACHED` cuando la página se cortó por el límite de trabajo (5 s): seguir pidiendo con `next_cursor`; no es el final |
| `sort_applied` | string | Orden aplicado. Sin `sort` depende de los filtros: `display_name:asc` sin filtros, `canonical_name:asc` con código de barras, identificador o filtros de catálogo, `company_product_id:asc` con `stock_state=IN_STOCK` o un `minimum_state` distinto de `NO_POLICY`, y `shortfall:desc` en la [API 3](#3-consultar-productos-bajo-el-mínimo) |
| `resolved_at` | date-time | Momento en que se resolvió la consulta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_INVENTORY_QUERY.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o el `branch_id` es de otra empresa (`detail`: «La empresa o la sucursal no existe o no tiene acceso.») | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `422` | `PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR` | Parámetro desconocido o de otra API (`UNKNOWN_FIELD`), `branch_id` junto con `scope`, `branch_id` o `scope` en la URL por sucursal, parámetro no repetible enviado dos veces (`INVALID_FORMAT`), `page_size` fuera de 1–20 o texto más largo que su límite | Corregir la consulta; el detalle viene en `errors[]` con `field` |
| `422` | `PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` | El cursor está alterado o es de otra consulta (`detail`: «El cursor no es válido. Repita la consulta sin cursor.») | Repetir la consulta sin `cursor` desde la primera página |
| `403` | `PRODUCT_INVENTORY_QUERY.FORBIDDEN` | El usuario tiene el permiso de la API pero le falta `perm:product-inventory-query:stock:read` o `perm:inventory:product-policies:read` (`detail`: «No tiene permiso para consultar productos bajo el mínimo.») | Ocultar la pantalla a perfiles sin los tres permisos |

## 4. Consultar los indicadores de inventario

**Método:** `GET`
**URL:** `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-summary` (todas las sucursales activas o las indicadas en `branch_id`) y `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-summary` (una sucursal)
**Permiso requerido:** `perm:product-inventory-query:inventory_summary:read`

### ¿Qué hace esta API?

Devuelve los contadores del tablero de inicio del módulo: productos adoptados con control de inventario, productos con saldo positivo, con saldo en cero, con política de mínimo y bajo el mínimo, por sucursal y consolidados. Es un resumen **solo operativo**: no trae costos ni valor del inventario (para eso, la [API 8](#8-consultar-el-valor-del-inventario-de-una-sucursal)).

Efectos verificados en el código: `adopted_products` lo cuenta Commercial Relationship (productos `ACTIVE` con control de inventario) y solo existe a nivel de empresa. Los demás contadores vienen de Inventory: un producto sin registro de saldo no cuenta en ninguno y pueden contar productos inactivos o sin control que conservan saldo. Sin paginación. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-summary?scope=COMPANY' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa consultada | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí, solo en la URL por sucursal | Sucursal consultada | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `scope` | `COMPANY` | No; por defecto `COMPANY`; solo en la URL de empresa | Todas las sucursales activas de la empresa; excluyente con `branch_id` | Único valor: `COMPANY` (por defecto) | `?scope=COMPANY` | Interfaz |
| `branch_id` | UUID, repetible (hasta 100) | No; solo en la URL de empresa; excluyente con `scope` | Indicadores solo de esas sucursales | UUID de una sucursal de la empresa; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` (repetir para varias; sin `scope`) | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

La URL por sucursal no admite parámetros de consulta (`422 UNKNOWN_FIELD`).

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-summary?scope=COMPANY`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`InventorySummaryOut`):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolved_at": "2026-10-20T15:40:00Z",
  "adopted_products": 320,
  "branches": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "products_with_positive_balance": 280,
      "products_with_zero_balance": 15,
      "products_with_policy": 120,
      "products_below_minimum": 9
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 280,
    "products_with_zero_balance": 15,
    "products_with_policy": 120,
    "products_below_minimum": 9
  }
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `adopted_products` | integer | Productos `ACTIVE` de la empresa con control de inventario; solo a nivel de empresa |
| `branches[].branch_id` | UUID | Sucursal del indicador |
| `branches[].products_with_positive_balance` | integer | Productos con existencia mayor que cero |
| `branches[].products_with_zero_balance` | integer | Productos con saldo registrado en cero; nunca cuenta productos sin registro |
| `branches[].products_with_policy` | integer | Productos con política de mínimo activa |
| `branches[].products_below_minimum` | integer | Productos bajo el mínimo; el detalle está en la [API 3](#3-consultar-productos-bajo-el-mínimo) |
| `consolidated` | objeto | Los mismos cuatro contadores para todas las sucursales consultadas |
| `resolved_at` | date-time | Momento en que se calcularon los datos |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_INVENTORY_QUERY.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la sucursal es de otra empresa (`detail`: «La empresa o la sucursal no existe o no tiene acceso.») | Volver a leer el contexto operativo |
| `422` | `PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR` | `branch_id` junto con `scope`, más de 100 `branch_id`, parámetro desconocido o cualquier parámetro en la URL por sucursal | Corregir la consulta; el detalle viene en `errors[]` |

## 5. Consultar los saldos de una sucursal

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances`
**Permiso requerido:** `perm:inventory:balances:read`

### ¿Qué hace esta API?

Lista el saldo exacto de cada producto de una sucursal, en unidad base, con su valor y su costo promedio según las capas FIFO abiertas. Es la fuente que usan Sales (disponibilidad) y Product Inventory Query; el frontend la usa cuando necesita el saldo con valor y sin el resto de datos del producto, por ejemplo para preparar un conteo físico.

Efectos verificados en el código: solo aparecen productos que alguna vez tuvieron saldo registrado en la sucursal; con `in_stock_only=true` solo los de cantidad mayor que cero. La consulta exige membresía `ACTIVE` en la empresa, no asignación a la sucursal, y no valida la sucursal: una sucursal sin movimientos devuelve `items` vacío. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE` y un `branch_id` de la empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances?in_stock_only=true&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal cuyos saldos se consultan | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `in_stock_only` | boolean | No; por defecto `false` | Solo productos con cantidad mayor que cero | `true` o `false` (por defecto); p. ej. `true` | `?in_stock_only=true` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `company_product_id` | UUID | No | Solo el saldo de ese producto | UUID de un producto de la empresa; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances?in_stock_only=true&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`BalancePage`):

```json
{
  "items": [
    {
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "800.0000",
      "last_movement_at": "2026-10-20T16:00:02Z",
      "balance_sequence": 97,
      "inventory_value": "476000.00",
      "average_unit_cost": "595.0000",
      "has_unknown_cost": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].company_product_id` | UUID | Producto; con él se abre el kardex ([API 7](#7-consultar-el-kardex-de-un-producto)) o se registra lo contado ([API 13](#13-registrar-la-cantidad-contada-de-un-producto)) |
| `items[].quantity` | string | Saldo en unidad base, 4 decimales |
| `items[].last_movement_at` | date-time \| null | Fecha del último movimiento; `null` si nunca tuvo movimientos |
| `items[].balance_sequence` | integer | Número de movimientos aplicados al saldo; crece con cada movimiento |
| `items[].inventory_value` | string | Valor del saldo según las capas FIFO abiertas, 2 decimales |
| `items[].average_unit_cost` | string \| null | Costo promedio de las capas abiertas; `null` si no hay capas |
| `items[].has_unknown_cost` | boolean | `true` si parte del saldo no tiene costo conocido: mostrar el valor como incompleto |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío y `total_records: 0` cuando no hay saldos (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `page` < 1 (`INVALID_FORMAT`), `page_size` fuera de 1–100 (`PAGE_SIZE_OUT_OF_RANGE`), UUID o booleano inválidos | Corregir la consulta; el detalle viene en `errors[]` con `field` |

Ejemplo de `422`:

```json
{
  "type": "https://sio/errors/inventory/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances",
  "code": "INVENTORY.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "page_size",
      "message": "El tamaño de página debe estar entre 1 y 100.",
      "code": "PAGE_SIZE_OUT_OF_RANGE"
    }
  ]
}
```

## 6. Consultar el saldo de un producto en una sucursal

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}`
**Permiso requerido:** `perm:inventory:balances:read`

### ¿Qué hace esta API?

Devuelve el saldo exacto de un producto en una sucursal, con su valor y costo promedio. Sirve para mostrar la disponibilidad antes de un ajuste negativo ([API 9](#9-registrar-un-ajuste-manual)) o junto al kardex.

Efectos verificados en el código: si el producto nunca tuvo movimientos en la sucursal **no** responde `404`, sino un saldo en cero: `quantity` `"0.0000"`, `balance_sequence` `0`, `inventory_value` `"0.00"`, `average_unit_cost` `null` y `last_movement_at` `null`. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`, el `branch_id` y el `company_product_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/balances/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal consultada | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | Producto empresarial consultado | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 5](#5-consultar-los-saldos-de-una-sucursal) (lista los saldos de la sucursal; errores en §5) o `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`BalanceResponse`):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "quantity": "800.0000",
  "last_movement_at": "2026-10-20T16:00:02Z",
  "balance_sequence": 97,
  "inventory_value": "476000.00",
  "average_unit_cost": "595.0000",
  "has_unknown_cost": false
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `quantity` | string | Saldo en unidad base; `"0.0000"` si nunca tuvo movimientos |
| `last_movement_at` | date-time \| null | `null` cuando nunca tuvo movimientos |
| `balance_sequence` | integer | `0` cuando nunca tuvo movimientos |
| `inventory_value`, `average_unit_cost`, `has_unknown_cost` | string, string \| null, boolean | Valor FIFO, costo promedio y aviso de costo desconocido, como en la [API 5](#5-consultar-los-saldos-de-una-sucursal) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | Algún identificador de la ruta no es un UUID válido | Corregir la URL |

## 7. Consultar el kardex de un producto

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}`
**Permiso requerido:** `perm:inventory:movements:read`

### ¿Qué hace esta API?

Devuelve la historia de movimientos de un producto en una sucursal: compras recibidas, ventas confirmadas, ajustes, diferencias de conteo y reversos, con el saldo antes y después de cada uno y su costo. Con `origin_type` y `origin_id` el frontend puede saltar al documento que originó el movimiento.

Efectos verificados en el código: los movimientos salen en **orden cronológico** (del más antiguo al más reciente). `occurred_at_from` y `occurred_at_to` deben llevar zona horaria. Un producto sin movimientos devuelve `items` vacío. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`, el `branch_id` y el `company_product_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/kardex/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61?occurred_at_from=2026-10-01T00:00:00-05:00&occurred_at_to=2026-10-31T23:59:59-05:00&movement_type=SALE_OUTPUT&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal consultada | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | Producto cuyo kardex se consulta | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 5](#5-consultar-los-saldos-de-una-sucursal) (lista los saldos de la sucursal; errores en §5) o `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `occurred_at_from` | date-time con zona horaria | No | Movimientos desde ese momento, inclusive | Fecha y hora ISO 8601 con zona; p. ej. `2026-10-01T00:00:00-05:00` (el `+` de una zona positiva se codifica como `%2B`) | `?occurred_at_from=2026-10-01T00:00:00-05:00` | Interfaz (selector de fechas) |
| `occurred_at_to` | date-time con zona horaria | No | Movimientos hasta ese momento, inclusive; no puede ser anterior a `occurred_at_from` | Fecha y hora ISO 8601 con zona; p. ej. `2026-10-31T23:59:59-05:00` | `&occurred_at_to=2026-10-31T23:59:59-05:00` | Interfaz (selector de fechas) |
| `movement_type` | string | No | Tipo de movimiento | Uno de: `PURCHASE_ENTRY`, `SALE_OUTPUT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`, `POSITIVE_ADJUSTMENT`, `NEGATIVE_ADJUSTMENT`; p. ej. `SALE_OUTPUT` | `&movement_type=SALE_OUTPUT` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `origin_type` | string | No | Tipo de documento de origen | Uno de: `PURCHASE`, `SALE`, `ADJUSTMENT`, `COUNT`; p. ej. `SALE` | `&origin_type=SALE` | Interfaz |
| `origin_id` | UUID | No | Documento de origen: compra, venta, ajuste o conteo | UUID del documento; p. ej. `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `&origin_id=9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` | `id` de la venta ([sale_id](../parametros/sale-id.md)) o de la compra ([purchase_id](../parametros/purchase-id.md)); `items[].id` de la [API 10](#10-consultar-los-ajustes) (lista los ajustes; errores en §10) o de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/kardex/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61?occurred_at_from=2026-10-01T00:00:00-05:00&occurred_at_to=2026-10-31T23:59:59-05:00&movement_type=SALE_OUTPUT&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`KardexPage`):

```json
{
  "items": [
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
      "unit_cost": "595.0000",
      "movement_value": "1190.00",
      "cost_known": true,
      "reversed_movement_id": null,
      "origin_type": "SALE",
      "origin_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "correlation_id": "2f3e4d5c-6b7a-4899-8a1b-2c3d4e5f6a7b",
      "reason": null,
      "created_at": "2026-10-20T16:00:02Z",
      "created_by": "8a7b6c5d-4e3f-4a2b-9c1d-0e9f8a7b6c5d"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].movement_type` | string | `PURCHASE_ENTRY` (compra recibida), `SALE_OUTPUT` (venta confirmada), `POSITIVE_ADJUSTMENT` / `NEGATIVE_ADJUSTMENT` (ajuste o diferencia de conteo), `ENTRY_REVERSAL` / `OUTPUT_REVERSAL` (reversos por anulación) |
| `items[].quantity`, `previous_balance`, `new_balance` | string | Cantidad del movimiento y saldo antes y después, en unidad base |
| `items[].unit_cost`, `movement_value`, `cost_known` | string \| null, string \| null, boolean \| null | Costo unitario (4 decimales), valor del movimiento (2 decimales) y si el costo es conocido |
| `items[].origin_type`, `origin_id` | string, UUID | Documento que originó el movimiento (`PURCHASE`, `SALE`, `ADJUSTMENT`, `COUNT`) |
| `items[].reversed_movement_id` | UUID \| null | En un reverso, el movimiento que revierte |
| `items[].application_user_id` | UUID | Usuario operativo que ejecutó la operación de origen |
| `items[].reason` | string \| null | Motivo, en ajustes y diferencias de conteo |
| `items[].operation_id` | UUID | Operación de inventario que agrupa los movimientos de un mismo documento |
| `items[].created_by` | string | `sub` del token que aplicó el movimiento; en compras y ventas es la cuenta técnica del servicio |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `occurred_at_from` posterior a `occurred_at_to` (`INVALID_DATE_RANGE`), fecha sin zona horaria, UUID inválido, `page` o `page_size` fuera de rango | Corregir los filtros; el detalle viene en `errors[]` |

Ejemplo de `422` por rango de fechas:

```json
{
  "type": "https://sio/errors/inventory/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/kardex/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "code": "INVENTORY.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "query",
      "message": "`occurred_at_from` no puede ser posterior a `occurred_at_to`.",
      "code": "INVALID_DATE_RANGE"
    }
  ]
}
```

## 8. Consultar el valor del inventario de una sucursal

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/valuation`
**Permiso requerido:** `perm:inventory:valuation:read`

### ¿Qué hace esta API?

Devuelve el valor del inventario de una sucursal por producto y el total, calculado sobre las capas FIFO abiertas. Es la consulta económica del módulo; los indicadores de la [API 4](#4-consultar-los-indicadores-de-inventario) no traen valores.

Efectos verificados en el código: solo incluye productos con cantidad mayor que cero, ordenados por `company_product_id`; `total_value` suma todos esos productos, no solo los de la página; `has_unknown_cost` del total es `true` si algún producto tiene unidades sin costo conocido. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE` y el `branch_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/valuation?page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `branch_id` | UUID | Sí | Sucursal valorizada | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Productos por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/valuation?page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`BranchValuationResponse`):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "quantity": "800.0000",
      "inventory_value": "476000.00",
      "average_unit_cost": "595.0000",
      "open_layers": 2,
      "has_unknown_cost": false
    }
  ],
  "total_value": "476000.00",
  "has_unknown_cost": false,
  "page": 1,
  "page_size": 20,
  "total_records": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].quantity`, `inventory_value`, `average_unit_cost` | string, string, string \| null | Cantidad en unidad base, valor y costo promedio del producto |
| `items[].open_layers` | integer | Capas de costo FIFO abiertas del producto |
| `items[].has_unknown_cost` | boolean | Parte de las unidades del producto no tiene costo conocido |
| `total_value` | string | Valor total de la sucursal, 2 decimales |
| `has_unknown_cost` | boolean | `true` si algún producto tiene costo desconocido: el total es incompleto |
| `page`, `page_size`, `total_records` | integer | Paginación; esta respuesta no trae `total_pages` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `page` < 1 o `page_size` fuera de 1–100 | Corregir la consulta |

## 9. Registrar un ajuste manual

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments`
**Permiso requerido:** `perm:inventory:adjustments:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Corrige el saldo de un producto en una sucursal por merma, rotura, vencimiento, hallazgo o error, dejando el motivo. Un ajuste `POSITIVE` suma unidades y abre una capa de costo; un ajuste `NEGATIVE` resta unidades y toma su costo de las capas FIFO más antiguas. Es una operación sensible (`HIGH_RISK`): solo la ejecuta un usuario humano asignado a la sucursal.

Efectos verificados en el código, en este orden: (1) formato del cuerpo: campos desconocidos rechazados, `quantity` mayor que cero con hasta 4 decimales, `reason` obligatorio y `unit_cost` prohibido en un ajuste negativo; (2) idempotencia: si la `adjustment_key` ya se usó con el mismo cuerpo, devuelve `200` con el ajuste original sin aplicar nada; con otro cuerpo, `409 OPERATION_KEY_CONFLICT`; (3) acceso a la sucursal; (4) el producto debe existir en la empresa, estar `ACTIVE` y tener control de inventario; (5) en un ajuste positivo, la moneda de la empresa y el costo: si no se envía `unit_cost` se usa el de la capa de costo más reciente del producto en la sucursal; si no hay capas o la más reciente no tiene costo conocido, `422 UNIT_COST_REQUIRED`; (6) aplica una operación de inventario de origen `ADJUSTMENT` con un movimiento `POSITIVE_ADJUSTMENT` o `NEGATIVE_ADJUSTMENT`. Un ajuste negativo que deje el saldo por debajo de cero responde `409 INSUFFICIENT_STOCK` y no cambia nada. Registra `CREATE_INVENTORY_ADJUSTMENT` en Audit sobre la entidad `InventoryAdjustment`, en la misma transacción.

Antes necesita: un `branch_id` en el que el usuario tenga asignación `ACTIVE` y el `company_product_id` de un producto con control de inventario. Para un ajuste negativo conviene mostrar antes el saldo con la [API 6](#6-consultar-el-saldo-de-un-producto-en-una-sucursal). El frontend genera un UUID nuevo para `adjustment_key` al abrir el formulario y lo reutiliza solo si reintenta la misma solicitud.

### ¿Cómo se realiza la solicitud?

Ajuste positivo (hallazgo):

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "adjustment_key": "7275dce1-3641-4e91-8854-2271a233576f",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "adjustment_type": "POSITIVE",
    "quantity": "2",
    "unit_cost": "500.00",
    "reason": "Hallazgo en bodega"
  }'
```

Ajuste negativo (rotura), sin `unit_cost`:

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "adjustment_key": "8a3c1f2e-5b6d-4e7f-9a0b-1c2d3e4f5a6b",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "adjustment_type": "NEGATIVE",
    "quantity": "3",
    "reason": "Unidades rotas en el traslado"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "adjustment_key": "7275dce1-3641-4e91-8854-2271a233576f",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "POSITIVE",
  "quantity": "2",
  "unit_cost": "500.00",
  "reason": "Hallazgo en bodega"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `adjustment_key` | UUID | Sí | Clave de idempotencia del ajuste: una nueva por ajuste | `7275dce1-3641-4e91-8854-2271a233576f` | Generada por el frontend (UUID v4) al abrir el formulario |
| `branch_id` | UUID | Sí | Sucursal del ajuste; el usuario debe tener asignación `ACTIVE` | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | Producto `ACTIVE` con control de inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |
| `adjustment_type` | `POSITIVE` \| `NEGATIVE` | Sí | Suma o resta unidades | `POSITIVE` | Formulario |
| `quantity` | number \| string | Sí | Unidades base que se suman o restan; mayor que cero, hasta 4 decimales | `"2"` | Formulario (en unidad base; convertir presentaciones con `base_quantity_factor` de la [API 1](#1-buscar-productos-con-precio-y-existencias)) |
| `unit_cost` | number \| string \| null | No; solo en `POSITIVE` | Costo unitario de la capa que abre el ajuste; mayor o igual que cero. Si se omite, se usa el de la capa más reciente. Prohibido en `NEGATIVE` | `"500.00"` | Formulario; sugerir `average_unit_cost` de la [API 6](#6-consultar-el-saldo-de-un-producto-en-una-sucursal) |
| `reason` | string (1–2000) | Sí | Motivo del ajuste; queda en el kardex y en Audit | `Hallazgo en bodega` | Formulario |

### Respuesta exitosa

`201 Created` (`InventoryAdjustmentResponse`). Repetir la misma solicitud con la misma `adjustment_key` devuelve `200 OK` con el mismo cuerpo.

```json
{
  "id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "operation_id": "c3d4e5f6-a7b8-4c9d-8e0f-2a3b4c5d6e7f",
  "movement_id": "d4e5f6a7-b8c9-4d0e-9f1a-3b4c5d6e7f80",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "POSITIVE",
  "quantity": "2.0000",
  "reason": "Hallazgo en bodega",
  "previous_balance": "800.0000",
  "new_balance": "802.0000",
  "unit_cost": "500.0000",
  "adjustment_value": "1000.00",
  "inventory_count_id": null,
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "created_at": "2026-10-20T17:10:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "movement": {
    "id": "d4e5f6a7-b8c9-4d0e-9f1a-3b4c5d6e7f80",
    "line_index": 0,
    "origin_detail_id": null,
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "movement_type": "POSITIVE_ADJUSTMENT",
    "quantity": "2.0000",
    "previous_balance": "800.0000",
    "new_balance": "802.0000",
    "balance_sequence": 98,
    "unit_cost": "500.0000",
    "movement_value": "1000.00",
    "cost_known": true,
    "reversed_movement_id": null
  }
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | Identificador del ajuste; es el `origin_id` del movimiento en el kardex ([API 7](#7-consultar-el-kardex-de-un-producto)) |
| `operation_id`, `movement_id` | UUID | Operación de inventario y movimiento creados |
| `previous_balance`, `new_balance` | string | Saldo antes y después del ajuste; mostrar `new_balance` como saldo actual |
| `unit_cost`, `adjustment_value` | string | Costo unitario aplicado (informado, tomado de la capa más reciente o de las capas FIFO) y valor del ajuste |
| `inventory_count_id` | UUID \| null | `null` en ajustes manuales; trae el conteo cuando el ajuste salió de la [API 14](#14-completar-el-conteo) |
| `application_user_id` | UUID | Usuario operativo que registró el ajuste |
| `movement` | objeto | Movimiento creado, tal como aparece en el kardex |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `409` | `INVENTORY.INSUFFICIENT_STOCK` | El ajuste negativo deja el saldo por debajo de cero; la extensión `shortages` trae el saldo disponible y lo pedido | Mostrar el disponible y corregir la cantidad; nada se aplicó |
| `409` | `INVENTORY.OPERATION_KEY_CONFLICT` | La `adjustment_key` ya se usó con un cuerpo distinto | Generar una clave nueva para un ajuste nuevo |
| `422` | `INVENTORY.VALIDATION_ERROR` | `errors[].code`: `REQUIRED`, `UNKNOWN_FIELD`, `INVALID_FORMAT`, `QUANTITY_NOT_POSITIVE`, `TOO_MANY_DECIMALS`, `QUANTITY_OUT_OF_RANGE`, `UNIT_COST_NEGATIVE`, `UNIT_COST_NOT_ALLOWED` (costo en un ajuste negativo), `UNIT_COST_REQUIRED` (positivo sin costo y sin capa previa con costo), `REASON_REQUIRED`, `COMPANY_PRODUCT_NOT_FOUND`, `COMPANY_PRODUCT_INACTIVE`, `INVENTORY_CONTROL_DISABLED` | Corregir el campo indicado en `errors[].field`; nada se aplicó |

Ejemplo de `409` por saldo insuficiente:

```json
{
  "type": "https://sio/errors/inventory/insufficient-stock",
  "title": "Saldo insuficiente",
  "status": 409,
  "detail": "No hay saldo suficiente para aplicar la operación; no se aplicó ninguna línea.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments",
  "code": "INVENTORY.INSUFFICIENT_STOCK",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "shortages": [
    {
      "index": 0,
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "available": "2.0000",
      "requested": "3.0000"
    }
  ]
}
```

Ejemplo de `403` por falta de asignación a la sucursal:

```json
{
  "type": "https://sio/errors/inventory/branch-access-denied",
  "title": "Acceso a la sucursal denegado",
  "status": 403,
  "detail": "No tiene una asignación activa a la sucursal, o la sucursal o la empresa no están activas. Solicite la asignación al administrador de la empresa.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments",
  "code": "INVENTORY.BRANCH_ACCESS_DENIED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 10. Consultar los ajustes

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments`
**Permiso requerido:** `perm:inventory:adjustments:read`

### ¿Qué hace esta API?

Lista los ajustes de la empresa, manuales y generados por conteos, con filtros por sucursal, producto, tipo, conteo y fechas. Cada ajuste trae su movimiento y, si salió de un conteo, el `inventory_count_id`.

Efectos verificados en el código: ordena del más reciente al más antiguo. `created_at_from` y `created_at_to` deben llevar zona horaria. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&adjustment_type=NEGATIVE&created_at_from=2026-10-01T00:00:00-05:00&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa consultada | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `branch_id` | UUID | No | Solo ajustes de esa sucursal | UUID de una sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `adjustment_type` | `POSITIVE` \| `NEGATIVE` | No | Tipo de ajuste | Uno de: `POSITIVE`, `NEGATIVE`; p. ej. `NEGATIVE` | `&adjustment_type=NEGATIVE` | Interfaz |
| `created_at_from` | date-time con zona horaria | No | Ajustes desde ese momento, inclusive | ISO 8601 con zona; p. ej. `2026-10-01T00:00:00-05:00` | `&created_at_from=2026-10-01T00:00:00-05:00` | Interfaz (selector de fechas) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `created_at_to` | date-time con zona horaria | No | Ajustes hasta ese momento, inclusive; no puede ser anterior a `created_at_from` | ISO 8601 con zona; p. ej. `2026-10-31T23:59:59-05:00` | `&created_at_to=2026-10-31T23:59:59-05:00` | Interfaz (selector de fechas) |
| `company_product_id` | UUID | No | Solo ajustes de ese producto | UUID de un producto; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |
| `inventory_count_id` | UUID | No | Solo los ajustes generados por ese conteo | UUID de un conteo; p. ej. `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `&inventory_count_id=f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) o `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-adjustments?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&adjustment_type=NEGATIVE&created_at_from=2026-10-01T00:00:00-05:00&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`AdjustmentPage`; cada elemento tiene la forma de la respuesta de la [API 9](#9-registrar-un-ajuste-manual)):

```json
{
  "items": [
    {
      "id": "e5f6a7b8-c9d0-4e1f-8a2b-4c5d6e7f8091",
      "operation_id": "f6a7b8c9-d0e1-4f2a-9b3c-5d6e7f8091a2",
      "movement_id": "a7b8c9d0-e1f2-4a3b-8c4d-6e7f8091a2b3",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "NEGATIVE",
      "quantity": "3.0000",
      "reason": "Unidades rotas en el traslado",
      "previous_balance": "802.0000",
      "new_balance": "799.0000",
      "unit_cost": "595.0000",
      "adjustment_value": "1785.00",
      "inventory_count_id": null,
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-20T17:20:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "a7b8c9d0-e1f2-4a3b-8c4d-6e7f8091a2b3",
        "line_index": 0,
        "origin_detail_id": null,
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "NEGATIVE_ADJUSTMENT",
        "quantity": "3.0000",
        "previous_balance": "802.0000",
        "new_balance": "799.0000",
        "balance_sequence": 99,
        "unit_cost": "595.0000",
        "movement_value": "1785.00",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[]` | lista | Ajustes con los mismos campos de la [API 9](#9-registrar-un-ajuste-manual), del más reciente al más antiguo |
| `items[].inventory_count_id` | UUID \| null | Conteo que generó el ajuste; `null` en ajustes manuales |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `created_at_from` posterior a `created_at_to` (`INVALID_DATE_RANGE`), fecha sin zona horaria, enumeración o UUID inválidos, `page` o `page_size` fuera de rango | Corregir los filtros |

## 11. Crear un conteo físico

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts`
**Permiso requerido:** `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Abre un conteo físico (inventario) de una sucursal en estado `DRAFT`. El conteo sigue el ciclo `DRAFT` → `IN_PROGRESS` ([API 12](#12-iniciar-el-conteo)) → `COMPLETED` ([API 14](#14-completar-el-conteo)) o `CANCELLED` ([API 15](#15-cancelar-el-conteo)). Crear el conteo no toca los saldos.

Efectos verificados en el código: exige usuario humano con asignación `ACTIVE` a la sucursal; crea el conteo con `status` `DRAFT`, `version` `1` y `started_by_user_id` igual al usuario operativo que lo crea; `details` y `adjustments` vienen vacíos. Se pueden tener varios conteos en `DRAFT` en la misma sucursal; la restricción de uno solo aplica al iniciar. No genera evento de auditoría.

Antes necesita: un `branch_id` en el que el usuario tenga asignación `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "observations": "Conteo de cierre de octubre"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "observations": "Conteo de cierre de octubre"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal que se cuenta; el usuario debe tener asignación `ACTIVE` | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `observations` | string (≤ 2000) \| null | No | Nota libre del conteo | `Conteo de cierre de octubre` | Formulario |

### Respuesta exitosa

`201 Created` (`InventoryCountResponse`):

```json
{
  "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "DRAFT",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": null,
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Conteo de cierre de octubre",
  "version": 1,
  "created_at": "2026-10-20T08:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T08:00:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": []
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El `count_id` que se usa en las API 12 a 15 y 17 |
| `status` | `DRAFT` | Estado inicial |
| `version` | integer | `1`; se envía al iniciar o cancelar |
| `started_by_user_id` | UUID | Usuario operativo que creó el conteo |
| `started_at`, `completed_at`, `cancelled_at` | date-time \| null | `null` hasta la transición correspondiente |
| `details`, `adjustments` | lista | Vacías al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `branch_id` ausente o inválido, `observations` > 2000 o campo desconocido | Corregir el formulario |

## 12. Iniciar el conteo

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/start`
**Permiso requerido:** `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Pasa el conteo de `DRAFT` a `IN_PROGRESS`; desde ese momento se registran las cantidades contadas ([API 13](#13-registrar-la-cantidad-contada-de-un-producto)).

Efectos verificados en el código: comprueba primero la `version` (`409 VERSION_CONFLICT`) y luego que el conteo esté en `DRAFT` (`409 INVALID_COUNT_TRANSITION`). Solo puede haber **un conteo en curso por sucursal** (`409 COUNT_ALREADY_IN_PROGRESS`). Registra `started_at`, incrementa `version` y registra `START_INVENTORY_COUNT` en Audit sobre la entidad `InventoryCount`.

Antes necesita: el `count_id` y la `version` vigente del conteo ([API 11](#11-crear-un-conteo-físico) o [API 17](#17-consultar-un-conteo)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/start' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del conteo | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `count_id` | UUID | Sí | Conteo que se inicia | `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) o `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer | Sí | Versión vigente del conteo | `1` | `version` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) o de la [API 17](#17-consultar-un-conteo) (consulta el conteo; errores en §17) |

### Respuesta exitosa

`200 OK` (`InventoryCountResponse`):

```json
{
  "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "IN_PROGRESS",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-20T08:05:00Z",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Conteo de cierre de octubre",
  "version": 2,
  "created_at": "2026-10-20T08:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T08:05:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": []
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `IN_PROGRESS` | Ya se pueden registrar cantidades |
| `started_at` | date-time | Momento del inicio |
| `version` | integer | Nueva versión; se envía al completar o cancelar |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `404` | `INVENTORY.NOT_FOUND` | El conteo no existe en la empresa | Volver a la lista de conteos |
| `409` | `INVENTORY.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 17](#17-consultar-un-conteo) y repetir |
| `409` | `INVENTORY.INVALID_COUNT_TRANSITION` | El conteo no está en `DRAFT` | Refrescar el conteo; mostrar su estado actual |
| `409` | `INVENTORY.COUNT_ALREADY_IN_PROGRESS` | Ya hay otro conteo en curso en la sucursal | Abrir el conteo en curso ([API 16](#16-consultar-los-conteos) con `status=IN_PROGRESS`) o cancelarlo |
| `422` | `INVENTORY.VALIDATION_ERROR` | `version` ausente o no entera, o campo desconocido | Corregir la solicitud |

Ejemplo de `409` por conteo en curso:

```json
{
  "type": "https://sio/errors/inventory/count-already-in-progress",
  "title": "Conteo en curso",
  "status": 409,
  "detail": "Ya hay un conteo en curso en la sucursal.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/start",
  "code": "INVENTORY.COUNT_ALREADY_IN_PROGRESS",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 13. Registrar la cantidad contada de un producto

**Método:** `PUT`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}`
**Permiso requerido:** `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Registra cuántas unidades base se contaron de un producto en un conteo `IN_PROGRESS`. Inventory guarda como foto el saldo del sistema en ese momento (`system_quantity_snapshot`) y calcula la diferencia (`difference_quantity` = contado − sistema). Volver a enviar el mismo producto **reemplaza** la cantidad y vuelve a tomar la foto del saldo.

Efectos verificados en el código: solo con el conteo en `IN_PROGRESS` (`409 COUNT_NOT_IN_PROGRESS`); el producto debe existir en la empresa, estar `ACTIVE` y tener control de inventario; si el producto nunca tuvo saldo, la foto es `0`; un conteo admite a lo sumo 1000 productos distintos. No cambia saldos ni la `version` del conteo: las diferencias se aplican al completar ([API 14](#14-completar-el-conteo)). No genera evento de auditoría.

Antes necesita: el `count_id` de un conteo `IN_PROGRESS` ([API 12](#12-iniciar-el-conteo)) y el `company_product_id`; la lista de productos de la sucursal sale de la [API 5](#5-consultar-los-saldos-de-una-sucursal).

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/details/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "counted_quantity": "797",
    "unit_cost": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del conteo | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `count_id` | UUID | Sí | Conteo en curso | `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) o `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) |
| `company_product_id` | UUID | Sí | Producto contado | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 5](#5-consultar-los-saldos-de-una-sucursal) (lista los saldos de la sucursal; errores en §5) o `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "counted_quantity": "797",
  "unit_cost": null
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `counted_quantity` | number \| string | Sí | Unidades base contadas; mayor o igual que cero (`0` es válido), hasta 4 decimales | `"797"` | Formulario de conteo (en unidad base) |
| `unit_cost` | number \| string \| null | No | Costo unitario para un **sobrante** (contado mayor que el sistema); si se omite se usa el de la capa más reciente. Se ignora en faltantes | `"500.00"` | Formulario; sugerir `average_unit_cost` de la [API 6](#6-consultar-el-saldo-de-un-producto-en-una-sucursal) |

### Respuesta exitosa

`200 OK` (`InventoryCountDetailResponse`):

```json
{
  "id": "0a9b8c7d-6e5f-4a3b-9c2d-1e0f9a8b7c6d",
  "inventory_count_id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "system_quantity_snapshot": "799.0000",
  "counted_quantity": "797.0000",
  "difference_quantity": "-2.0000",
  "unit_cost": null,
  "inventory_adjustment_id": null,
  "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "counted_at": "2026-10-20T09:15:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `system_quantity_snapshot` | string | Saldo del sistema al registrar |
| `counted_quantity` | string | Cantidad contada |
| `difference_quantity` | string | Contado − sistema: negativo es faltante, positivo es sobrante, `"0.0000"` no genera ajuste |
| `inventory_adjustment_id` | UUID \| null | `null` hasta completar; luego, el ajuste generado por la diferencia |
| `counted_by_user_id`, `counted_at` | UUID, date-time | Quién y cuándo registró la cantidad |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `404` | `INVENTORY.NOT_FOUND` | El conteo no existe en la empresa | Volver a la lista de conteos |
| `409` | `INVENTORY.COUNT_NOT_IN_PROGRESS` | El conteo no está en `IN_PROGRESS` | Refrescar el conteo; si está en `DRAFT`, iniciarlo con la [API 12](#12-iniciar-el-conteo) |
| `422` | `INVENTORY.VALIDATION_ERROR` | `errors[].code`: `QUANTITY_NOT_POSITIVE` (cantidad negativa o con más de 4 decimales), `UNIT_COST_NEGATIVE`, `COUNT_DETAILS_LIMIT` (más de 1000 productos), `COMPANY_PRODUCT_NOT_FOUND`, `COMPANY_PRODUCT_INACTIVE`, `INVENTORY_CONTROL_DISABLED`, `UNKNOWN_FIELD` | Corregir la cantidad o elegir otro producto |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/inventory/count-not-in-progress",
  "title": "Conteo no en curso",
  "status": 409,
  "detail": "El conteo no está en curso.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/details/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "code": "INVENTORY.COUNT_NOT_IN_PROGRESS",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 14. Completar el conteo

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/complete`
**Permiso requerido:** `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Cierra el conteo y aplica **todas** las diferencias registradas como ajustes, de una sola vez y todo o nada. Cada faltante genera un `NEGATIVE_ADJUSTMENT` y cada sobrante un `POSITIVE_ADJUSTMENT`, con el motivo «Diferencia del conteo físico»; los productos sin diferencia no generan movimiento.

Efectos verificados en el código, en este orden: (1) idempotencia por `completion_key`: si la clave ya completó este conteo con la misma `version`, devuelve el conteo completado sin aplicar nada; si la clave pertenece a otra operación, `409 OPERATION_KEY_CONFLICT`; (2) acceso a la sucursal del conteo y moneda de la empresa; (3) bloqueo del conteo: `version` vigente (`409 VERSION_CONFLICT`) y estado `IN_PROGRESS` (`409 COUNT_NOT_IN_PROGRESS`); (4) el conteo debe tener al menos un producto (`422 COUNT_WITHOUT_DETAILS`); (5) aplica una operación de inventario de tipo `ADJUSTMENT` con origen `COUNT` y una línea por cada diferencia distinta de cero. Si algún faltante deja un saldo por debajo de cero (porque hubo ventas después de registrar la cantidad), responde `409 INSUFFICIENT_STOCK` y no aplica ninguna línea. Un sobrante sin `unit_cost` y sin capa previa con costo responde `422 UNIT_COST_REQUIRED` en el campo `details[<company_product_id>].unit_cost`. Si no hay diferencias, completa el conteo sin operación (`operation_id` `null`). Pasa a `COMPLETED`, incrementa `version` y registra `COMPLETE_INVENTORY_COUNT` en Audit sobre la entidad `InventoryCount`.

Antes necesita: un conteo `IN_PROGRESS` con productos registrados ([API 13](#13-registrar-la-cantidad-contada-de-un-producto)) y su `version` vigente. El frontend genera un UUID nuevo para `completion_key` al pulsar «Completar» y lo reutiliza solo si reintenta.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/complete' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "completion_key": "4b5c6d7e-8f9a-4b0c-9d1e-2f3a4b5c6d7e",
    "version": 2
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del conteo | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `count_id` | UUID | Sí | Conteo que se completa | `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) o `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "completion_key": "4b5c6d7e-8f9a-4b0c-9d1e-2f3a4b5c6d7e",
  "version": 2
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `completion_key` | UUID | Sí | Clave de idempotencia de la finalización | `4b5c6d7e-8f9a-4b0c-9d1e-2f3a4b5c6d7e` | Generada por el frontend (UUID v4) al pulsar «Completar» |
| `version` | integer | Sí | Versión vigente del conteo | `2` | `version` de la [API 12](#12-iniciar-el-conteo) (inicia el conteo; errores en §12) o de la [API 17](#17-consultar-un-conteo) (consulta el conteo; errores en §17) |

### Respuesta exitosa

`200 OK` (`InventoryCountResponse`, con `details[]` y los `adjustments[]` generados):

```json
{
  "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "COMPLETED",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-20T08:05:00Z",
  "completed_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "completed_at": "2026-10-20T11:00:00Z",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": "5d6e7f80-91a2-4b3c-8d4e-5f6a7b8c9d0e",
  "observations": "Conteo de cierre de octubre",
  "version": 3,
  "created_at": "2026-10-20T08:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T11:00:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [
    {
      "id": "0a9b8c7d-6e5f-4a3b-9c2d-1e0f9a8b7c6d",
      "inventory_count_id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "system_quantity_snapshot": "799.0000",
      "counted_quantity": "797.0000",
      "difference_quantity": "-2.0000",
      "unit_cost": null,
      "inventory_adjustment_id": "6e7f8091-a2b3-4c4d-9e5f-6a7b8c9d0e1f",
      "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "counted_at": "2026-10-20T09:15:00Z"
    }
  ],
  "adjustments": [
    {
      "id": "6e7f8091-a2b3-4c4d-9e5f-6a7b8c9d0e1f",
      "operation_id": "5d6e7f80-91a2-4b3c-8d4e-5f6a7b8c9d0e",
      "movement_id": "7f8091a2-b3c4-4d5e-8f6a-7b8c9d0e1f2a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "adjustment_type": "NEGATIVE",
      "quantity": "2.0000",
      "reason": "Diferencia del conteo físico",
      "previous_balance": "799.0000",
      "new_balance": "797.0000",
      "unit_cost": "595.0000",
      "adjustment_value": "1190.00",
      "inventory_count_id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "created_at": "2026-10-20T11:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "movement": {
        "id": "7f8091a2-b3c4-4d5e-8f6a-7b8c9d0e1f2a",
        "line_index": 0,
        "origin_detail_id": "0a9b8c7d-6e5f-4a3b-9c2d-1e0f9a8b7c6d",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "movement_type": "NEGATIVE_ADJUSTMENT",
        "quantity": "2.0000",
        "previous_balance": "799.0000",
        "new_balance": "797.0000",
        "balance_sequence": 100,
        "unit_cost": "595.0000",
        "movement_value": "1190.00",
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `COMPLETED` | Estado final; el conteo ya no admite cambios |
| `operation_id` | UUID \| null | Operación de inventario con todos los ajustes; `null` si no hubo diferencias |
| `completed_by_user_id`, `completed_at` | UUID, date-time | Quién y cuándo completó |
| `details[].inventory_adjustment_id` | UUID \| null | Ajuste generado por cada diferencia; `null` en productos sin diferencia |
| `adjustments[]` | lista | Ajustes generados, con la forma de la [API 9](#9-registrar-un-ajuste-manual) y `inventory_count_id` igual al conteo; en el kardex aparecen con `origin_type` `COUNT` y `origin_id` igual al `count_id` |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `404` | `INVENTORY.NOT_FOUND` | El conteo no existe en la empresa | Volver a la lista de conteos |
| `409` | `INVENTORY.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 17](#17-consultar-un-conteo) y repetir con una `completion_key` nueva |
| `409` | `INVENTORY.COUNT_NOT_IN_PROGRESS` | El conteo no está en `IN_PROGRESS` | Refrescar el conteo |
| `409` | `INVENTORY.INSUFFICIENT_STOCK` | Algún faltante deja el saldo por debajo de cero; `shortages` indica producto, disponible y pedido | Volver a registrar ese producto con la [API 13](#13-registrar-la-cantidad-contada-de-un-producto) (toma una foto nueva del saldo) y completar con una clave nueva; nada se aplicó |
| `409` | `INVENTORY.OPERATION_KEY_CONFLICT` | La `completion_key` ya se usó en otra operación | Generar una clave nueva |
| `422` | `INVENTORY.VALIDATION_ERROR` | `errors[].code`: `COUNT_WITHOUT_DETAILS` (sin productos registrados), `UNIT_COST_REQUIRED` (sobrante sin costo), `REQUIRED`, `INVALID_FORMAT`, `UNKNOWN_FIELD` | Registrar productos o el costo del sobrante y repetir |

Ejemplo de `409` por versión:

```json
{
  "type": "https://sio/errors/inventory/version-conflict",
  "title": "Conflicto de versión",
  "status": 409,
  "detail": "El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/complete",
  "code": "INVENTORY.VERSION_CONFLICT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 15. Cancelar el conteo

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}/cancel`
**Permiso requerido:** `perm:inventory:counts:create` + asignación `ACTIVE` a la sucursal

### ¿Qué hace esta API?

Cancela un conteo en `DRAFT` o `IN_PROGRESS` dejando el motivo. Las cantidades registradas se conservan como historia, pero **no** se aplica ningún ajuste ni cambia ningún saldo. Cancelar un conteo en curso libera la sucursal para iniciar otro.

Efectos verificados en el código: comprueba la `version` (`409 VERSION_CONFLICT`) y luego el estado; desde `COMPLETED` o `CANCELLED` responde `409 INVALID_COUNT_TRANSITION`. Guarda `cancel_reason`, `cancelled_by_user_id` y `cancelled_at`, incrementa `version` y registra `CANCEL_INVENTORY_COUNT` en Audit sobre la entidad `InventoryCount`.

Antes necesita: el `count_id` y su `version` vigente.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9/cancel' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "reason": "Se repetirá el conteo con más personal",
    "version": 2
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del conteo | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `count_id` | UUID | Sí | Conteo que se cancela | `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) o `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "reason": "Se repetirá el conteo con más personal",
  "version": 2
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `reason` | string (1–2000) | Sí | Motivo de la cancelación | `Se repetirá el conteo con más personal` | Formulario |
| `version` | integer | Sí | Versión vigente del conteo | `2` | `version` de la [API 17](#17-consultar-un-conteo) (consulta el conteo; errores en §17) |

### Respuesta exitosa

`200 OK` (`InventoryCountResponse`; conteo cancelado antes de registrar productos):

```json
{
  "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "CANCELLED",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-20T08:05:00Z",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_at": "2026-10-20T10:00:00Z",
  "cancel_reason": "Se repetirá el conteo con más personal",
  "operation_id": null,
  "observations": "Conteo de cierre de octubre",
  "version": 3,
  "created_at": "2026-10-20T08:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T10:00:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [],
  "adjustments": []
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `CANCELLED` | Estado final; sin efectos en saldos |
| `cancel_reason`, `cancelled_by_user_id`, `cancelled_at` | string, UUID, date-time | Motivo, autor y momento de la cancelación |
| `details` | lista | Cantidades registradas antes de cancelar (vacía si no se registró ninguna) |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | El usuario no es miembro activo de la empresa o la sucursal es de otra empresa | Volver a leer el contexto operativo |
| `403` | `INVENTORY.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación con la [API 12 de Administración empresarial](administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal) (asigna un usuario a una sucursal; errores en esa sección) |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio: estas operaciones solo las ejecuta un usuario humano | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `404` | `INVENTORY.NOT_FOUND` | El conteo no existe en la empresa | Volver a la lista de conteos |
| `409` | `INVENTORY.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 17](#17-consultar-un-conteo) y repetir |
| `409` | `INVENTORY.INVALID_COUNT_TRANSITION` | El conteo ya está `COMPLETED` o `CANCELLED` | Refrescar el conteo |
| `422` | `INVENTORY.VALIDATION_ERROR` | `reason` vacío o > 2000 (`REASON_REQUIRED`), `version` ausente o campo desconocido | Corregir el formulario |

## 16. Consultar los conteos

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts`
**Permiso requerido:** `perm:inventory:counts:read`

### ¿Qué hace esta API?

Lista los conteos físicos de la empresa, con filtros por sucursal y estado. Sirve para encontrar el conteo en curso de una sucursal o revisar los conteos anteriores.

Efectos verificados en el código: ordena del más reciente al más antiguo. Los elementos de la lista **no** traen productos ni ajustes: `details` y `adjustments` vienen en `null`; el detalle completo se obtiene con la [API 17](#17-consultar-un-conteo). No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&status=IN_PROGRESS&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa consultada | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `branch_id` | UUID | No | Solo conteos de esa sucursal | UUID de una sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `status` | `DRAFT` \| `IN_PROGRESS` \| `COMPLETED` \| `CANCELLED` | No | Estado del conteo | Uno de: `DRAFT`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`; p. ej. `IN_PROGRESS` | `&status=IN_PROGRESS` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&status=IN_PROGRESS&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CountPage`):

```json
{
  "items": [
    {
      "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "status": "IN_PROGRESS",
      "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "started_at": "2026-10-20T08:05:00Z",
      "completed_by_user_id": null,
      "completed_at": null,
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancel_reason": null,
      "operation_id": null,
      "observations": "Conteo de cierre de octubre",
      "version": 2,
      "created_at": "2026-10-20T08:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_at": "2026-10-20T08:05:00Z",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "details": null,
      "adjustments": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | `count_id` para las API 12 a 15 y 17 |
| `items[].status`, `version` | string, integer | Estado actual y versión para la siguiente transición |
| `items[].details`, `adjustments` | null | Siempre `null` en la lista |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | `status` fuera de la enumeración, UUID inválido, `page` o `page_size` fuera de rango | Corregir los filtros |

## 17. Consultar un conteo

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-counts/{count_id}`
**Permiso requerido:** `perm:inventory:counts:read`

### ¿Qué hace esta API?

Devuelve un conteo con todos los productos registrados y, si está `COMPLETED`, los ajustes que generó. Es la pantalla de trabajo del conteo y la fuente de la `version` vigente para iniciar, completar o cancelar.

Efectos verificados en el código: `details[]` se ordena por `company_product_id`; `adjustments[]` solo trae elementos cuando el conteo está `COMPLETED` (vacío en los demás estados). No escribe nada.

Antes necesita: el `count_id` y membresía `ACTIVE` en la empresa.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-counts/f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña del conteo | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `count_id` | UUID | Sí | Conteo consultado | `f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9` | `items[].id` de la [API 16](#16-consultar-los-conteos) (lista los conteos; errores en §16) o `id` de la [API 11](#11-crear-un-conteo-físico) (crea el conteo; errores en §11) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`InventoryCountResponse`). Conteo en curso con un producto registrado:

```json
{
  "id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "IN_PROGRESS",
  "started_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "started_at": "2026-10-20T08:05:00Z",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Conteo de cierre de octubre",
  "version": 2,
  "created_at": "2026-10-20T08:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T08:05:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "details": [
    {
      "id": "0a9b8c7d-6e5f-4a3b-9c2d-1e0f9a8b7c6d",
      "inventory_count_id": "f1e2d3c4-b5a6-4978-8695-a4b3c2d1e0f9",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "system_quantity_snapshot": "799.0000",
      "counted_quantity": "797.0000",
      "difference_quantity": "-2.0000",
      "unit_cost": null,
      "inventory_adjustment_id": null,
      "counted_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "counted_at": "2026-10-20T09:15:00Z"
    }
  ],
  "adjustments": []
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status`, `version` | string, integer | Estado y versión vigente para la siguiente transición |
| `details[]` | lista | Productos registrados con foto del sistema, cantidad contada y diferencia ([API 13](#13-registrar-la-cantidad-contada-de-un-producto)) |
| `adjustments[]` | lista | Ajustes generados al completar ([API 14](#14-completar-el-conteo)); vacía si el conteo no está `COMPLETED` |
| `operation_id` | UUID \| null | Operación de inventario de la finalización |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `404` | `INVENTORY.NOT_FOUND` | El conteo no existe en la empresa | Volver a la lista de conteos |
| `422` | `INVENTORY.VALIDATION_ERROR` | Algún identificador de la ruta no es un UUID válido | Corregir la URL |

## 18. Consultar las políticas de mínimo

**Método:** `GET`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies`
**Permiso requerido:** `perm:inventory:product-policies:read`

### ¿Qué hace esta API?

Lista las políticas de inventario por producto y sucursal de la empresa: mínimo, objetivo, método de stock de seguridad y modo de reposición. Sirve para mostrar el mínimo vigente de un producto y para saber si ya existe una política activa antes de crear otra con la [API 19](#19-definir-el-mínimo-de-un-producto-en-una-sucursal).

Efectos verificados en el código: ordena por sucursal, producto y fecha de creación (la más reciente primero); devuelve políticas activas e inactivas salvo que se filtre `is_active`. No escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_active=true&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa consultada | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `branch_id` | UUID | No | Solo políticas de esa sucursal | UUID de una sucursal; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | No | Solo políticas de ese producto | UUID de un producto; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |
| `is_active` | boolean | No | Solo activas (`true`) o solo inactivas (`false`); sin el filtro, ambas | `true` o `false`; p. ej. `true` | `&is_active=true` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_active=true&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`ProductPolicyPage`):

```json
{
  "items": [
    {
      "id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6e",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "minimum_stock": "300.0000",
      "target_stock": "600.0000",
      "service_level": null,
      "safety_stock_method": "BASIC",
      "calculation_window_days": 90,
      "replenishment_mode": "MANUAL",
      "auto_purchase_enabled": false,
      "is_active": true,
      "version": 1,
      "created_at": "2026-10-20T12:00:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_at": "2026-10-20T12:00:00Z",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | Identificador de la política (`policy_id` de las operaciones no principales Inv 31–33) |
| `items[].minimum_stock` | string | Mínimo en unidad base; por debajo de él el producto aparece en la [API 3](#3-consultar-productos-bajo-el-mínimo) |
| `items[].target_stock` | string \| null | Existencia objetivo; informativa |
| `items[].service_level`, `safety_stock_method`, `calculation_window_days` | string \| null, string, integer | Parámetros de stock de seguridad guardados en la política |
| `items[].replenishment_mode`, `auto_purchase_enabled` | string, boolean | Configuración de reposición; solo se guarda, no genera compras |
| `items[].is_active`, `version` | boolean, integer | Estado y versión de la política |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo; no distinguir entre «no existe» y «sin acceso» |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `422` | `INVENTORY.VALIDATION_ERROR` | UUID o booleano inválidos, `page` o `page_size` fuera de rango | Corregir los filtros |

## 19. Definir el mínimo de un producto en una sucursal

**Método:** `POST`
**URL:** `https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies`
**Permiso requerido:** `perm:inventory:product-policies:update`

### ¿Qué hace esta API?

Crea la política de inventario de un producto en una sucursal, con su mínimo (`minimum_stock`) y, opcionalmente, su existencia objetivo. Con la política activa, el producto aparece en la [API 3](#3-consultar-productos-bajo-el-mínimo) cuando su existencia baja de `minimum_stock`, y los indicadores de la [API 4](#4-consultar-los-indicadores-de-inventario) lo cuentan.

Efectos verificados en el código, en este orden: (1) usuario humano con membresía en la empresa (no exige asignación a la sucursal); (2) rangos: `minimum_stock` ≥ 0, `target_stock` ≥ 0 y no menor que el mínimo, `service_level` mayor que 0 y menor que 1, `calculation_window_days` de 1 a 3650; (3) la sucursal debe existir, pertenecer a la empresa y estar activa, la empresa debe estar activa y el producto debe estar `ACTIVE` con control de inventario; (4) una sola política **activa** por producto y sucursal (`409 ACTIVE_POLICY_EXISTS`). Crea la política con `is_active` `true` y `version` `1` y registra `CREATE_INVENTORY_POLICY` en Audit sobre la entidad `InventoryPolicy`. `replenishment_mode` `AUTO_DRAFT` y `auto_purchase_enabled` son **solo configuración**: se guardan en la política sin cambiar el motor de inventario ni generar compras; ninguna de las 411 operaciones crea compras automáticamente.

Antes necesita: el `branch_id` y el `company_product_id`; comprobar con la [API 18](#18-consultar-las-políticas-de-mínimo) que no exista ya una política activa. Para cambiar una política existente se usa la modificación o la inactivación (Inv 32, 33; no principales).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-inventory-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "minimum_stock": "300",
    "target_stock": "600",
    "service_level": null,
    "safety_stock_method": "BASIC",
    "calculation_window_days": 90,
    "replenishment_mode": "MANUAL",
    "auto_purchase_enabled": false
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la sucursal | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "300",
  "target_stock": "600",
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 90,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": false
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal activa de la empresa | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `memberships[].branches[].branch_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 6 de Administración empresarial](administracion-empresarial.md#6-consultar-las-sucursales-de-una-empresa) (lista las sucursales de la empresa; errores en esa sección) · guía [branch_id](../parametros/branch-id.md) |
| `company_product_id` | UUID | Sí | Producto `ACTIVE` con control de inventario | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].company_product_id` de la [API 1](#1-buscar-productos-con-precio-y-existencias) (busca los productos de la empresa con sus existencias; errores en §1) o el producto adoptado en [Productos y precios](productos-y-precios.md) · guía [company_product_id](../parametros/company-product-id.md) |
| `minimum_stock` | number \| string | No; por defecto `0` | Mínimo en unidad base; ≥ 0 | `"300"` | Formulario |
| `target_stock` | number \| string \| null | No; por defecto `null` | Existencia objetivo en unidad base; ≥ 0 y no menor que `minimum_stock` | `"600"` | Formulario |
| `service_level` | number \| string \| null | No; por defecto `null` | Nivel de servicio, mayor que 0 y menor que 1 | `"0.95"` | Formulario |
| `safety_stock_method` | `BASIC` \| `STATISTICAL` | Sí | Método de stock de seguridad que se guarda en la política | `BASIC` | Formulario |
| `calculation_window_days` | integer 1–3650 | No; por defecto `90` | Días de la ventana de cálculo | `90` | Formulario |
| `replenishment_mode` | `MANUAL` \| `AUTO_DRAFT` | Sí | Modo de reposición; solo configuración | `MANUAL` | Formulario |
| `auto_purchase_enabled` | boolean | No; por defecto `false` | Marca de compra automática; solo configuración | `false` | Formulario |

### Respuesta exitosa

`201 Created` (`ProductPolicyResponse`):

```json
{
  "id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "minimum_stock": "300.0000",
  "target_stock": "600.0000",
  "service_level": null,
  "safety_stock_method": "BASIC",
  "calculation_window_days": 90,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": false,
  "is_active": true,
  "version": 1,
  "created_at": "2026-10-20T12:00:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_at": "2026-10-20T12:00:00Z",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | Identificador de la política |
| `minimum_stock`, `target_stock` | string, string \| null | Niveles guardados con 4 decimales |
| `is_active`, `version` | boolean, integer | `true` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `INVENTORY.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía en ella | Volver a leer el contexto operativo |
| `403` | `INVENTORY.FORBIDDEN` | El token es de una cuenta de servicio | Usar el token del usuario |
| `403` | `INVENTORY.OPERATIONAL_ACCESS_DENIED` | El usuario no tiene permiso en Operational Context para consultar su acceso operativo | Pedir acceso al administrador indicando el `trace_id` |
| `409` | `INVENTORY.ACTIVE_POLICY_EXISTS` | Ya hay una política activa para el producto en la sucursal | Mostrarla con la [API 18](#18-consultar-las-políticas-de-mínimo); para cambiarla, modificarla o inactivarla (Inv 32, 33) |
| `422` | `INVENTORY.VALIDATION_ERROR` | `errors[].code`: `INVALID_LEVELS`, `INVALID_SERVICE_LEVEL`, `INVALID_WINDOW`, `BRANCH_NOT_FOUND`, `BRANCH_NOT_IN_COMPANY`, `BRANCH_INACTIVE`, `COMPANY_INACTIVE`, `COMPANY_PRODUCT_NOT_FOUND`, `COMPANY_PRODUCT_INACTIVE`, `INVENTORY_CONTROL_DISABLED`, `REQUIRED`, `UNKNOWN_FIELD` | Corregir el campo indicado en `errors[].field`; nada se guardó |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/inventory/active-policy-exists",
  "title": "Política activa existente",
  "status": 409,
  "detail": "Ya existe una política activa para el producto en la sucursal; inactívela primero.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies",
  "code": "INVENTORY.ACTIVE_POLICY_EXISTS",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

Ejemplo de `422` por niveles:

```json
{
  "type": "https://sio/errors/inventory/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-policies",
  "code": "INVENTORY.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "target_stock",
      "message": "El stock objetivo no puede ser menor que el mínimo.",
      "code": "INVALID_LEVELS"
    }
  ]
}
```

---

## Dependencias con otros módulos

- [Compras](compras.md): la recepción de una compra crea las entradas (`PURCHASE_ENTRY`) y las capas de costo FIFO; la anulación crea los reversos (`ENTRY_REVERSAL`). Purchase llama a Inventory con su cuenta técnica (Inv 3, 4). La [API 3](#3-consultar-productos-bajo-el-mínimo) es la lista de trabajo para preparar compras.
- [Ventas](ventas.md): la confirmación de una venta crea las salidas (`SALE_OUTPUT`) y la anulación los reversos (`OUTPUT_REVERSAL`), con la cuenta técnica de Sales (Inv 5, 6); la disponibilidad que valida Sales se calcula sobre los saldos de la [API 5](#5-consultar-los-saldos-de-una-sucursal).
- [Productos y precios](productos-y-precios.md): `inventory_control_enabled` al adoptar el producto decide si admite saldos, ajustes, conteos y políticas; el precio que muestra la [API 1](#1-buscar-productos-con-precio-y-existencias) sale de las listas de precios de Commercial Relationship.
- [Administración empresarial](administracion-empresarial.md): la asignación del usuario a la sucursal habilita los ajustes y conteos; la trazabilidad de ajustes, conteos y políticas se consulta en su [API 16](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría).
- [Reportes](reportes.md): la evolución de existencias por período (Inv 37, 38).

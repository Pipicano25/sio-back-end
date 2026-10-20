# Commercial Relationship API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Commercial Relationship guarda **lo que cada empresa decide comercialmente**: qué productos del catálogo global adopta (productos y presentaciones empresariales), con qué clientes y proveedores se relaciona, qué productos le suministra cada proveedor y con qué condiciones de pago, y a qué precio vende (listas de precios, precios por presentación, políticas de ganancia y actualización automática de precios tras cada compra). Ventas, Compras, Inventario y Product Inventory Query dependen de este servicio.

## Responsabilidad

- Productos empresariales y presentaciones empresariales (adopción de productos y presentaciones globales de Product Catalog) con su tasa de impuesto de compra.
- Clientes y proveedores de la empresa (sobre identidades de Party Identity); bloqueo de proveedores.
- Productos de proveedor y condiciones de pago de proveedor (tipos de Payment Reference).
- Listas de precios, precios por presentación con vigencia, resolución del precio aplicable a una venta.
- Políticas de ganancia por lista y aplicaciones automáticas de precio a partir de los costos de cada recepción de compra.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-commercial-relationship-dev.onrender.com/api/v1` |
| Salud | `https://sio-commercial-relationship-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-commercial-relationship-dev.onrender.com/docs) · [/openapi.json](https://sio-commercial-relationship-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `COMMERCIAL_RELATIONSHIP.*` y `trace_id` |
| Operaciones en el contrato desplegado | 76 (74 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/commercial-relationship-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos `perm:commercial-relationship:{recurso}:{accion}`; acciones `read`, `create`, `update` (modificar, reactivar, desbloquear) y `delete` (inactivar, bloquear), salvo las indicadas:

| Recurso | Operaciones | Grupos con lectura (plantilla) | Grupos con escritura |
|---|---|---|---|
| `company_products` | 3–10, resumen de empresas (25) | Todos los grupos | `administradores`, `supervisores` (salvo `delete`) |
| `company_product_purchase_taxes` (`update`) | Tasa de impuesto de compra (11, 12) | — | `administradores` (`perm:all:all:all`), `supervisores` (`perm:all:all:update`) |
| `company_customers` | 13–18 | Todos | `administradores`, `supervisores` (salvo `delete`) |
| `company_suppliers` | 19–24 | Todos | Ídem (`block` usa `delete`: solo `administradores`) |
| `company_product_presentations` | 26–33 | Todos | `administradores`, `supervisores` (salvo `delete`) |
| `supplier_products` | 34–39 | Todos | Ídem |
| `supplier_payment_conditions` | 40–45 | Todos | Ídem |
| `price_lists` | 46–51 | Todos | Ídem |
| `price_list_items` | 52–58, resolución de precio (59) | Todos | Ídem |
| `pricing_policy_coverage` (`read`) | Cobertura (60) | `administradores`, `supervisores` (comodines) | — |
| `pricing_policies` | 61–70 | `administradores`, `supervisores` | `administradores`; `supervisores` (incluye `delete` explícito) |
| `automatic_price_update_requests` (`submit`) | 71 | — | Solo identidad técnica de Purchase |
| `automatic_price_applications` (`read`, `resolve`) | 72–74 | `administradores`, `supervisores` | `resolve`: `administradores`, `supervisores` |
| `platform:lookup` | Lecturas por UUID sin membresía | Cuentas técnicas | — |

Los grupos `compras`, `ventas`, `reportes` y `consulta` solo leen; `inventario` lee productos empresariales.

## Alcance de datos

| Regla | Detalle |
|---|---|
| Empresa | Toda ruta `/companies/{company_id}/…` exige membresía `ACTIVE` del usuario, evaluada en Operational Context (`operational-access`) con su token; sin ella, `404 NOT_FOUND` aunque el cuerpo sea inválido. Operational Context con `403` → `403 OPERATIONAL_ACCESS_DENIED` |
| Recursos por UUID (`/company-products/{id}`, …) | Si no existe → `404` sin consultar Operational Context; si existe, se evalúa la membresía en su `company_id` |
| Lecturas técnicas | Una cuenta de servicio con `platform:lookup` lee por UUID sin membresía (nunca escribe) |
| Escrituras | Exigen empresa `ACTIVE` (`422 COMPANY_INACTIVE`), salvo inactivar |
| Party Identity con `403` | `403 PARTY_IDENTITY_ACCESS_DENIED` |

## Convenciones comunes

- Listas paginadas (`page` ≥ 1, `page_size` 1–100, por defecto 20) con `items`, `page`, `page_size`, `total_records`, `total_pages`. Filtro `status`: `ACTIVE`, `INACTIVE`, `ALL` (proveedores también `BLOCKED`); sin filtro, todas las listas aplican `ACTIVE` por defecto (verificado en el repositorio base del servicio: `status` nulo se sustituye por `ACTIVE`).
- Escrituras con `version` (≥ 1): `409 VERSION_CONFLICT`. Inactivar/reactivar reciben `{"version": n}` (`VersionRequest`); transición inválida → `409 INVALID_STATUS_TRANSITION`.
- `PUT` es reemplazo completo «en cualquier estado» y nunca cambia `status`.
- Todos los modelos rechazan campos adicionales (`422`); `422 IMMUTABLE_FIELD` para campos inmutables.
- Importes y porcentajes son cadenas decimales en las respuestas; en las solicitudes se aceptan número o texto.
- Referencias a otros servicios: inexistentes o de otra empresa → `422` (`GLOBAL_PRODUCT_NOT_FOUND`, `PERSON_IDENTITY_NOT_FOUND`, `ORGANIZATION_IDENTITY_NOT_FOUND`, `COMPANY_PRODUCT_NOT_FOUND`, `COMPANY_SUPPLIER_NOT_FOUND`, `PRESENTATION_NOT_FOUND`, `PAYMENT_CONDITION_TYPE_NOT_FOUND`, `PRICE_LIST_NOT_FOUND`…); existentes pero inactivas o no elegibles → `422` (`*_INACTIVE`, `GLOBAL_PRODUCT_NOT_ELIGIBLE`, `COMPANY_SUPPLIER_BLOCKED`, `PRESENTATION_OF_OTHER_PRODUCT`, `PRESENTATION_NOT_PURCHASABLE`, `PRESENTATION_NOT_SELLABLE`, `CURRENCY_NOT_SUPPORTED`…).
- `503 DEPENDENCY_UNAVAILABLE` con `dependency` (`operational-context`, `product-catalog`, `party-identity`, `payment-reference`, `database`).

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso (`perm:commercial-relationship:…`) | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Base de datos lista | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/companies/{company_id}/company-products` | Listar productos empresariales | `company_products:read` | `READ` | [Ver](#3-get-companiescompany_idcompany-products) |
| 4 | `POST` | `/companies/{company_id}/company-products` | Adoptar producto global | `company_products:create` | `WRITE` | [Ver](#4-post-companiescompany_idcompany-products) |
| 5 | `POST` | `/companies/{company_id}/company-products/search` | Buscar con continuación por posición | `company_products:read` | `READ` | [Ver](#5-post-companiescompany_idcompany-productssearch) |
| 6 | `POST` | `/company-products/batch-lookup` | Productos por lotes | `company_products:read` | `READ` | [Ver](#6-post-company-productsbatch-lookup) |
| 7 | `GET` | `/company-products/{company_product_id}` | Consultar producto | `company_products:read` | `READ` | [Ver](#7-get-company-productscompany_product_id) |
| 8 | `PUT` | `/company-products/{company_product_id}` | Modificar producto | `company_products:update` | `WRITE` | [Ver](#8-put-company-productscompany_product_id) |
| 9 | `POST` | `/company-products/{company_product_id}/deactivate` | Inactivar producto | `company_products:delete` | `HIGH_RISK` | [Ver](#9-post-company-productscompany_product_iddeactivate) |
| 10 | `POST` | `/company-products/{company_product_id}/reactivate` | Reactivar producto | `company_products:update` | `WRITE` | [Ver](#10-post-company-productscompany_product_idreactivate) |
| 11 | `PUT` | `/company-products/{company_product_id}/purchase-tax` | Tasa de impuesto de compra | `company_product_purchase_taxes:update` | `WRITE` | [Ver](#11-put-company-productscompany_product_idpurchase-tax) |
| 12 | `POST` | `/companies/{company_id}/company-products/purchase-taxes/batch` | Tasas de hasta 100 productos | `company_product_purchase_taxes:update` | `WRITE` | [Ver](#12-post-companiescompany_idcompany-productspurchase-taxesbatch) |
| 13 | `GET` | `/companies/{company_id}/company-customers` | Listar clientes | `company_customers:read` | `READ` | [Ver](#13-get-companiescompany_idcompany-customers) |
| 14 | `POST` | `/companies/{company_id}/company-customers` | Incorporar cliente | `company_customers:create` | `WRITE` | [Ver](#14-post-companiescompany_idcompany-customers) |
| 15 | `GET` | `/company-customers/{company_customer_id}` | Consultar cliente | `company_customers:read` | `READ` | [Ver](#15-get-company-customerscompany_customer_id) |
| 16 | `PUT` | `/company-customers/{company_customer_id}` | Modificar cliente | `company_customers:update` | `WRITE` | [Ver](#16-put-company-customerscompany_customer_id) |
| 17 | `POST` | `/company-customers/{company_customer_id}/deactivate` | Inactivar cliente | `company_customers:delete` | `HIGH_RISK` | [Ver](#17-post-company-customerscompany_customer_iddeactivate) |
| 18 | `POST` | `/company-customers/{company_customer_id}/reactivate` | Reactivar cliente | `company_customers:update` | `WRITE` | [Ver](#18-post-company-customerscompany_customer_idreactivate) |
| 19 | `GET` | `/companies/{company_id}/company-suppliers` | Listar proveedores | `company_suppliers:read` | `READ` | [Ver](#19-get-companiescompany_idcompany-suppliers) |
| 20 | `POST` | `/companies/{company_id}/company-suppliers` | Seleccionar proveedor | `company_suppliers:create` | `WRITE` | [Ver](#20-post-companiescompany_idcompany-suppliers) |
| 21 | `GET` | `/company-suppliers/{company_supplier_id}` | Consultar proveedor | `company_suppliers:read` | `READ` | [Ver](#21-get-company-supplierscompany_supplier_id) |
| 22 | `PUT` | `/company-suppliers/{company_supplier_id}` | Modificar proveedor | `company_suppliers:update` | `WRITE` | [Ver](#22-put-company-supplierscompany_supplier_id) |
| 23 | `POST` | `/company-suppliers/{company_supplier_id}/deactivate` | Inactivar proveedor | `company_suppliers:delete` | `HIGH_RISK` | [Ver](#23-post-company-supplierscompany_supplier_iddeactivate) |
| 24 | `POST` | `/company-suppliers/{company_supplier_id}/reactivate` | Reactivar proveedor | `company_suppliers:update` | `WRITE` | [Ver](#24-post-company-supplierscompany_supplier_idreactivate) |
| 25 | `GET` | `/company-summaries` | Resumen de mis empresas | `company_products:read` | `READ` | [Ver](#25-get-company-summaries) |
| 26 | `GET` | `/companies/{company_id}/company-product-presentations` | Listar presentaciones empresariales | `company_product_presentations:read` | `READ` | [Ver](#26-get-companiescompany_idcompany-product-presentations) |
| 27 | `POST` | `/companies/{company_id}/company-product-presentations` | Adoptar presentación | `company_product_presentations:create` | `WRITE` | [Ver](#27-post-companiescompany_idcompany-product-presentations) |
| 28 | `POST` | `/companies/{company_id}/company-product-presentations/by-products` | Presentaciones de varios productos | `company_product_presentations:read` | `READ` | [Ver](#28-post-companiescompany_idcompany-product-presentationsby-products) |
| 29 | `POST` | `/company-product-presentations/batch-lookup` | Presentaciones por lotes | `company_product_presentations:read` | `READ` | [Ver](#29-post-company-product-presentationsbatch-lookup) |
| 30 | `GET` | `/company-product-presentations/{presentation_id}` | Consultar presentación | `company_product_presentations:read` | `READ` | [Ver](#30-get-company-product-presentationspresentation_id) |
| 31 | `PUT` | `/company-product-presentations/{presentation_id}` | Modificar presentación | `company_product_presentations:update` | `WRITE` | [Ver](#31-put-company-product-presentationspresentation_id) |
| 32 | `POST` | `/company-product-presentations/{presentation_id}/deactivate` | Inactivar presentación | `company_product_presentations:delete` | `HIGH_RISK` | [Ver](#32-post-company-product-presentationspresentation_iddeactivate) |
| 33 | `POST` | `/company-product-presentations/{presentation_id}/reactivate` | Reactivar presentación | `company_product_presentations:update` | `WRITE` | [Ver](#33-post-company-product-presentationspresentation_idreactivate) |
| 34 | `GET` | `/companies/{company_id}/supplier-products` | Listar productos de proveedor | `supplier_products:read` | `READ` | [Ver](#34-get-companiescompany_idsupplier-products) |
| 35 | `POST` | `/companies/{company_id}/supplier-products` | Registrar producto de proveedor | `supplier_products:create` | `WRITE` | [Ver](#35-post-companiescompany_idsupplier-products) |
| 36 | `GET` | `/supplier-products/{supplier_product_id}` | Consultar producto de proveedor | `supplier_products:read` | `READ` | [Ver](#36-get-supplier-productssupplier_product_id) |
| 37 | `PUT` | `/supplier-products/{supplier_product_id}` | Modificar producto de proveedor | `supplier_products:update` | `WRITE` | [Ver](#37-put-supplier-productssupplier_product_id) |
| 38 | `POST` | `/supplier-products/{supplier_product_id}/deactivate` | Inactivar | `supplier_products:delete` | `WRITE` | [Ver](#38-post-supplier-productssupplier_product_iddeactivate) |
| 39 | `POST` | `/supplier-products/{supplier_product_id}/reactivate` | Reactivar | `supplier_products:update` | `WRITE` | [Ver](#39-post-supplier-productssupplier_product_idreactivate) |
| 40 | `GET` | `/companies/{company_id}/supplier-payment-conditions` | Listar condiciones de pago | `supplier_payment_conditions:read` | `READ` | [Ver](#40-get-companiescompany_idsupplier-payment-conditions) |
| 41 | `POST` | `/companies/{company_id}/supplier-payment-conditions` | Registrar condición | `supplier_payment_conditions:create` | `WRITE` | [Ver](#41-post-companiescompany_idsupplier-payment-conditions) |
| 42 | `GET` | `/supplier-payment-conditions/{condition_id}` | Consultar condición | `supplier_payment_conditions:read` | `READ` | [Ver](#42-get-supplier-payment-conditionscondition_id) |
| 43 | `PUT` | `/supplier-payment-conditions/{condition_id}` | Modificar condición | `supplier_payment_conditions:update` | `WRITE` | [Ver](#43-put-supplier-payment-conditionscondition_id) |
| 44 | `POST` | `/supplier-payment-conditions/{condition_id}/deactivate` | Inactivar | `supplier_payment_conditions:delete` | `WRITE` | [Ver](#44-post-supplier-payment-conditionscondition_iddeactivate) |
| 45 | `POST` | `/supplier-payment-conditions/{condition_id}/reactivate` | Reactivar | `supplier_payment_conditions:update` | `WRITE` | [Ver](#45-post-supplier-payment-conditionscondition_idreactivate) |
| 46 | `GET` | `/companies/{company_id}/price-lists` | Listar listas de precios | `price_lists:read` | `READ` | [Ver](#46-get-companiescompany_idprice-lists) |
| 47 | `POST` | `/companies/{company_id}/price-lists` | Crear lista | `price_lists:create` | `WRITE` | [Ver](#47-post-companiescompany_idprice-lists) |
| 48 | `GET` | `/price-lists/{price_list_id}` | Consultar lista | `price_lists:read` | `READ` | [Ver](#48-get-price-listsprice_list_id) |
| 49 | `PUT` | `/price-lists/{price_list_id}` | Modificar lista | `price_lists:update` | `WRITE` | [Ver](#49-put-price-listsprice_list_id) |
| 50 | `POST` | `/price-lists/{price_list_id}/deactivate` | Inactivar lista | `price_lists:delete` | `HIGH_RISK` | [Ver](#50-post-price-listsprice_list_iddeactivate) |
| 51 | `POST` | `/price-lists/{price_list_id}/reactivate` | Reactivar lista | `price_lists:update` | `WRITE` | [Ver](#51-post-price-listsprice_list_idreactivate) |
| 52 | `GET` | `/companies/{company_id}/price-list-items` | Listar precios | `price_list_items:read` | `READ` | [Ver](#52-get-companiescompany_idprice-list-items) |
| 53 | `POST` | `/companies/{company_id}/price-list-items` | Registrar precio | `price_list_items:create` | `WRITE` | [Ver](#53-post-companiescompany_idprice-list-items) |
| 54 | `GET` | `/price-list-items/{price_list_item_id}` | Consultar precio | `price_list_items:read` | `READ` | [Ver](#54-get-price-list-itemsprice_list_item_id) |
| 55 | `PUT` | `/price-list-items/{price_list_item_id}` | Modificar precio | `price_list_items:update` | `WRITE` | [Ver](#55-put-price-list-itemsprice_list_item_id) |
| 56 | `POST` | `/price-list-items/{price_list_item_id}/change-price` | Cambiar precio (cierra y crea) | `price_list_items:update` | `HIGH_RISK` | [Ver](#56-post-price-list-itemsprice_list_item_idchange-price) |
| 57 | `POST` | `/price-list-items/{price_list_item_id}/deactivate` | Inactivar precio | `price_list_items:delete` | `HIGH_RISK` | [Ver](#57-post-price-list-itemsprice_list_item_iddeactivate) |
| 58 | `POST` | `/price-list-items/{price_list_item_id}/reactivate` | Reactivar precio | `price_list_items:update` | `WRITE` | [Ver](#58-post-price-list-itemsprice_list_item_idreactivate) |
| 59 | `POST` | `/companies/{company_id}/applicable-prices/resolve` | Resolver precio aplicable | `price_list_items:read` | `READ` | [Ver](#59-post-companiescompany_idapplicable-pricesresolve) |
| 60 | `POST` | `/companies/{company_id}/pricing-policies/coverage` | Cobertura de políticas de ganancia | `pricing_policy_coverage:read` | `READ` | [Ver](#60-post-companiescompany_idpricing-policiescoverage) |
| 61 | `GET` | `/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` | Listar políticas de una lista | `pricing_policies:read` | `READ` | [Ver](#61-get-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 62 | `POST` | `/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` | Crear política | `pricing_policies:create` | `WRITE` | [Ver](#62-post-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 63 | `GET` | `/pricing-policies/{policy_id}` | Consultar política | `pricing_policies:read` | `READ` | [Ver](#63-get-pricing-policiespolicy_id) |
| 64 | `PUT` | `/pricing-policies/{policy_id}` | Renombrar política | `pricing_policies:update` | `WRITE` | [Ver](#64-put-pricing-policiespolicy_id) |
| 65 | `GET` | `/pricing-policies/{policy_id}/terms` | Historial de porcentajes | `pricing_policies:read` | `READ` | [Ver](#65-get-pricing-policiespolicy_idterms) |
| 66 | `GET` | `/pricing-policies/{policy_id}/presentations` | Presentaciones de la política | `pricing_policies:read` | `READ` | [Ver](#66-get-pricing-policiespolicy_idpresentations) |
| 67 | `POST` | `/pricing-policies/{policy_id}/presentations` | Asignar presentaciones | `pricing_policies:update` | `WRITE` | [Ver](#67-post-pricing-policiespolicy_idpresentations) |
| 68 | `POST` | `/pricing-policies/{policy_id}/percentage` | Cambiar porcentaje | `pricing_policies:update` | `HIGH_RISK` | [Ver](#68-post-pricing-policiespolicy_idpercentage) |
| 69 | `POST` | `/pricing-policies/{policy_id}/presentations/remove` | Retirar presentaciones | `pricing_policies:update` | `WRITE` | [Ver](#69-post-pricing-policiespolicy_idpresentationsremove) |
| 70 | `POST` | `/pricing-policies/{policy_id}/deactivate` | Inactivar política (final) | `pricing_policies:delete` | `HIGH_RISK` | [Ver](#70-post-pricing-policiespolicy_iddeactivate) |
| 71 | `POST` | `/companies/{company_id}/automatic-price-update-requests` | Solicitud de actualización (Purchase) | `automatic_price_update_requests:submit` + identidad técnica | `WRITE` | [Ver](#71-post-companiescompany_idautomatic-price-update-requests) |
| 72 | `GET` | `/companies/{company_id}/automatic-price-applications` | Listar aplicaciones automáticas | `automatic_price_applications:read` | `READ` | [Ver](#72-get-companiescompany_idautomatic-price-applications) |
| 73 | `GET` | `/companies/{company_id}/automatic-price-applications/{application_id}` | Consultar aplicación | `automatic_price_applications:read` | `READ` | [Ver](#73-get-companiescompany_idautomatic-price-applicationsapplication_id) |
| 74 | `POST` | `/companies/{company_id}/automatic-price-applications/{application_id}/resolution` | Resolver administrativamente | `automatic_price_applications:resolve` | `WRITE` | [Ver](#74-post-companiescompany_idautomatic-price-applicationsapplication_idresolution) |
| 75 | `POST` | `/company-suppliers/{company_supplier_id}/block` | Bloquear proveedor | `company_suppliers:delete` | `HIGH_RISK` | [Ver](#75-post-company-supplierscompany_supplier_idblock) |
| 76 | `POST` | `/company-suppliers/{company_supplier_id}/unblock` | Desbloquear proveedor | `company_suppliers:update` | `WRITE` | [Ver](#76-post-company-supplierscompany_supplier_idunblock) |

Las operaciones 75 y 76 (bloqueo y desbloqueo del proveedor) se numeran al final para no alterar las referencias a las demás; con las dos de salud la tabla cubre las 76 operaciones del contrato.

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-commercial-relationship-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-commercial-relationship-dev.onrender.com/health/ready` → `200`; `503` si la base de datos no responde.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/health/ready'
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
"texto ilustrativo"
```

### 3. `GET /companies/{company_id}/company-products`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products`; permiso `company_products:read`. Parámetros: `page`, `page_size`, `search` (≤ 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `is_purchasable`, `is_sellable`, `inventory_control_enabled` (boolean), `global_product_id` (UUID). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[CompanyProductResponse]`. Ejemplo completo y campos en [company_product_id](../parametros/company-product-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_CompanyProductResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "reference_code": "REF-0001",
      "display_name": "Acetaminofén 500 mg tableta",
      "short_name": null,
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": false,
      "expiration_tracking_enabled": false,
      "is_purchasable": true,
      "is_sellable": true,
      "purchase_tax_percentage": "19"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

`CompanyProductResponse`: `id`, `company_id`, `status`, `version`, trazabilidad, `global_product_id`, `internal_code`, `reference_code`, `display_name`, `short_name`, `currency_code`, `inventory_control_enabled`, `lot_tracking_enabled`, `expiration_tracking_enabled`, `is_purchasable`, `is_sellable`, `purchase_tax_percentage` (string \| null; `null` = sin configurar).

### 4. `POST /companies/{company_id}/company-products`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products`; permiso `company_products:create`. Cuerpo `CompanyProductCreate` y ejemplo en [company_product_id](../parametros/company-product-id.md) (`global_product_id`, `internal_code` 1–60 único por empresa, `display_name` 1–200, `currency_code` 1–10, banderas de inventario y comerciales). Reglas: el producto global debe existir, estar activo y ser elegible (`422 GLOBAL_PRODUCT_NOT_FOUND` / `_INACTIVE` / `_NOT_ELIGIBLE`); una adopción por producto global y empresa (`409 DUPLICATE_ADOPTION`); `409 DUPLICATE_INTERNAL_CODE`; moneda admitida (`422 CURRENCY_NOT_SUPPORTED`); banderas de inventario coherentes (`422 INVENTORY_FLAGS_INVALID`). Al adoptar, el servicio registra el «primer uso» del producto global en Product Catalog con su cuenta técnica. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "internal_code": "PRD-0001",
    "reference_code": "REF-0001",
    "display_name": "Acetaminofén 500 mg tableta",
    "currency_code": "COP",
    "inventory_control_enabled": true,
    "lot_tracking_enabled": false,
    "expiration_tracking_enabled": false,
    "is_purchasable": true,
    "is_sellable": true
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`CompanyProductResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": "REF-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": null,
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": false,
  "expiration_tracking_enabled": false,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19"
}
```

### 5. `POST /companies/{company_id}/company-products/search`

`READ` (consulta por `POST`, para paginar sin conteo; la usa Product Inventory Query). URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products/search`; permiso `company_products:read`. Cuerpo (`CompanyProductSearchRequest`): `search` (≤ 200; también SKU de presentaciones), `internal_code` (exacto, ≤ 60), `sku` (exacto, ≤ 80), `status` (`ACTIVE` por defecto), `is_purchasable`, `is_sellable`, `inventory_control_enabled`, `company_product_ids` / `global_product_ids` (modo evaluador, hasta 100), `sort` (`{"key": "display_name"|"internal_code"|"created_at", "direction": "asc"|"desc"}`), `after` (posición `{"k": ["…"], "id": "…"}` devuelta en el elemento anterior), `limit` (1–100, obligatorio). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products/search' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "search": "acetaminofén",
    "internal_code": "PRD-0001",
    "sku": "ACET-500-TAB",
    "status": "ACTIVE",
    "is_purchasable": true,
    "is_sellable": true,
    "inventory_control_enabled": true,
    "company_product_ids": [
      "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
    ],
    "sort": {
      "key": "display_name",
      "direction": "asc"
    },
    "after": {
      "k": [
        "display_name"
      ],
      "id": "30edd025-4af1-4849-8bce-cd240d55cdbb"
    },
    "limit": 20
  }'
```
Respuesta `200`: `items[]` (`CompanyProductSearchItem` = producto + `position`) y `has_more`.

Ejemplo de respuesta `200` (`CompanyProductSearchResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "reference_code": "REF-0001",
      "display_name": "Acetaminofén 500 mg tableta",
      "short_name": null,
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": false,
      "expiration_tracking_enabled": false,
      "is_purchasable": true,
      "is_sellable": true,
      "purchase_tax_percentage": "19",
      "position": {
        "k": [
          "display_name"
        ],
        "id": "6bc29f47-1f6c-4e62-84b4-5f482cd9ba49"
      }
    }
  ],
  "has_more": false
}
```

### 6. `POST /company-products/batch-lookup`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/batch-lookup`; permiso `company_products:read`. Cuerpo `{"ids": [...]}` (≥ 1). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```
Respuesta `200`: `items[]` con `id`, `found` y, si existe y está en el alcance, los datos principales del producto. Pensado para consumidores técnicos.

Ejemplo de respuesta `200` (`BatchLookupResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "display_name": "Acetaminofén 500 mg tableta",
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": false,
      "expiration_tracking_enabled": false,
      "is_purchasable": true,
      "is_sellable": true,
      "purchase_tax_percentage": "19",
      "status": "ACTIVE",
      "version": 1
    }
  ]
}
```

### 7. `GET /company-products/{company_product_id}`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}`. `200`; `404` si no existe o no hay membresía en su empresa.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompanyProductResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": "REF-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": null,
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": false,
  "expiration_tracking_enabled": false,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19"
}
```

### 8. `PUT /company-products/{company_product_id}`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}`; permiso `company_products:update`. Cuerpo (`CompanyProductUpdate`): `version`, `internal_code`, `display_name`, `currency_code` y las cinco banderas **obligatorias**; `reference_code`, `short_name` opcionales. `global_product_id` no se modifica. Cambiar la moneda afecta la resolución de precios (la lista predeterminada se busca por la moneda del producto).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "PRD-0001",
    "reference_code": "REF-0001",
    "display_name": "Acetaminofén 500 mg tableta",
    "currency_code": "COP",
    "inventory_control_enabled": true,
    "lot_tracking_enabled": false,
    "expiration_tracking_enabled": false,
    "is_purchasable": true,
    "is_sellable": true
  }'
```

Ejemplo de respuesta `200` (`CompanyProductResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": "REF-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": null,
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": false,
  "expiration_tracking_enabled": false,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19"
}
```

### 9. `POST /company-products/{company_product_id}/deactivate`

`HIGH_RISK`: el producto deja de ser elegible en ventas y compras (`409 REFERENCES_NOT_ELIGIBLE`) y desaparece de los listados `ACTIVE`; las existencias se conservan. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/deactivate`; permiso `company_products:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyProductResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": "REF-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": null,
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": false,
  "expiration_tracking_enabled": false,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19"
}
```

### 10. `POST /company-products/{company_product_id}/reactivate`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/reactivate`; permiso `company_products:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyProductResponse`; valores ilustrativos):

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": "REF-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": null,
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": false,
  "expiration_tracking_enabled": false,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19"
}
```

### 11. `PUT /company-products/{company_product_id}/purchase-tax`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/purchase-tax`; permiso `company_product_purchase_taxes:update` (propio, distinto del `PUT` del producto). Cuerpo (`PurchaseTaxUpdate`): `version` y `purchase_tax_percentage` (0 a 100, hasta 4 decimales; `422 TAX_PERCENTAGE_OUT_OF_RANGE`; `null` no se admite una vez configurada: `422 PURCHASE_TAX_REQUIRED`). `0` es válido. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/purchase-tax' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "purchase_tax_percentage": "19"
  }'
```
Respuesta `200` con el producto. Efecto: Purchase usa esta tasa por defecto en las líneas nuevas; las compras ya confirmadas no cambian.

```json
{
  "version": 2,
  "purchase_tax_percentage": "19"
}
```

### 12. `POST /companies/{company_id}/company-products/purchase-taxes/batch`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products/purchase-taxes/batch`; mismo permiso. Cuerpo (`PurchaseTaxBatch`): `items[]` (1 a 100) de `{"company_product_id", "version", "purchase_tax_percentage"}`. **Todo o nada**: valida todo, bloquea en orden y confirma en una transacción. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products/purchase-taxes/batch' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "items": [
      {
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "version": 1,
        "purchase_tax_percentage": "19"
      }
    ]
  }'
```
Respuesta `200`: `{"items": [CompanyProductResponse, …]}`.

### 13. `GET /companies/{company_id}/company-customers`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`; permiso `company_customers:read`. Parámetros y ejemplo en [company_customer_id](../parametros/customer-id.md).

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CompanyCustomerResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "customer_kind": "PERSON",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "CLI-0001",
      "display_name": "Ana Pérez",
      "preferred_contact_person_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 14. `POST /companies/{company_id}/company-customers`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-customers`; permiso `company_customers:create`. Cuerpo `CompanyCustomerCreate` (ver [company_customer_id](../parametros/customer-id.md)). Reglas: `customer_kind` coherente con el identificador enviado (`422 CUSTOMER_IDENTITY_MISMATCH`); identidad existente y activa en Party Identity; `preferred_contact_person_id` solo para organizaciones y debe ser un contacto de esa organización (`422 CONTACT_PERSON_NOT_ALLOWED` / `CONTACT_PERSON_INVALID`); la empresa no puede ser cliente de sí misma (`422 SELF_RELATIONSHIP_NOT_ALLOWED`); `409 DUPLICATE_CUSTOMER` (misma identidad) y `409 DUPLICATE_INTERNAL_CODE`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-customers' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_kind": "PERSON",
    "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
    "internal_code": "CLI-0001",
    "display_name": "Ana Pérez"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`CompanyCustomerResponse`; valores ilustrativos):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

### 15. `GET /company-customers/{company_customer_id}`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompanyCustomerResponse`; valores ilustrativos):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

### 16. `PUT /company-customers/{company_customer_id}`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}`; permiso `company_customers:update`. Cuerpo (`CompanyCustomerUpdate`): `version`, `internal_code`, `display_name`, `preferred_contact_person_id`. La identidad y el tipo no cambian.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "CLI-0001",
    "display_name": "Ana Pérez"
  }'
```

Ejemplo de respuesta `200` (`CompanyCustomerResponse`; valores ilustrativos):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

### 17. `POST /company-customers/{company_customer_id}/deactivate`

`HIGH_RISK` (el cliente deja de ser elegible para ventas nuevas). URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/deactivate`; permiso `company_customers:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyCustomerResponse`; valores ilustrativos):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

### 18. `POST /company-customers/{company_customer_id}/reactivate`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/{company_customer_id}/reactivate`; permiso `company_customers:update`; cuerpo `{"version": n}`. Revalida la identidad en Party Identity.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-customers/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyCustomerResponse`; valores ilustrativos):

```json
{
  "id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "customer_kind": "PERSON",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "CLI-0001",
  "display_name": "Ana Pérez",
  "preferred_contact_person_id": null
}
```

### 19. `GET /companies/{company_id}/company-suppliers`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`; permiso `company_suppliers:read`. Parámetros (`status` admite `BLOCKED`) y ejemplo en [company_supplier_id](../parametros/supplier-id.md).

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CompanySupplierResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "internal_code": "PRV-0001",
      "display_name": "Distribuidora Farma S.A.S.",
      "preferred_contact_person_id": null,
      "block_reason": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 20. `POST /companies/{company_id}/company-suppliers`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-suppliers`; permiso `company_suppliers:create`. Cuerpo `CompanySupplierCreate` (ver [company_supplier_id](../parametros/supplier-id.md)). Reglas: organización activa en Party Identity; no la propia empresa (`422 SELF_RELATIONSHIP_NOT_ALLOWED`); `409 DUPLICATE_SUPPLIER`, `409 DUPLICATE_INTERNAL_CODE`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-suppliers' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "internal_code": "PRV-0001",
    "display_name": "Distribuidora Farma S.A.S."
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

### 21. `GET /company-suppliers/{company_supplier_id}`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

### 22. `PUT /company-suppliers/{company_supplier_id}`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}`; permiso `company_suppliers:update`. Cuerpo (`CompanySupplierUpdate`): `version`, `internal_code`, `display_name`, `preferred_contact_person_id`. Nunca cambia `status` ni `block_reason`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "PRV-0001",
    "display_name": "Distribuidora Farma S.A.S."
  }'
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

### 23. `POST /company-suppliers/{company_supplier_id}/deactivate`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · Inactivar proveedor |
| URL | `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/deactivate` |
| Permiso | `perm:commercial-relationship:company_suppliers:delete` |
| Alcance | Empresa (la del proveedor; membresía `ACTIVE` evaluada en Operational Context) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

| Nombre | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_supplier_id` | ruta | UUID | Sí | [company_supplier_id](../parametros/supplier-id.md) |

Cuerpo (`VersionRequest`; rechaza campos adicionales): `version` (integer ≥ 1, obligatorio).

Efecto: `INACTIVE`: no elegible en compras nuevas. Transición no permitida desde el estado actual → `409 COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION`; `version` distinta → `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT`; proveedor inexistente o de una empresa sin membresía → `404`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

### 24. `POST /company-suppliers/{company_supplier_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` · Reactivar proveedor |
| URL | `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/reactivate` |
| Permiso | `perm:commercial-relationship:company_suppliers:update` |
| Alcance | Empresa (la del proveedor; membresía `ACTIVE` evaluada en Operational Context) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

| Nombre | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_supplier_id` | ruta | UUID | Sí | [company_supplier_id](../parametros/supplier-id.md) |

Cuerpo (`VersionRequest`; rechaza campos adicionales): `version` (integer ≥ 1, obligatorio).

Efecto: Vuelve a `ACTIVE`; revalida la organización en Party Identity. Transición no permitida desde el estado actual → `409 COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION`; `version` distinta → `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT`; proveedor inexistente o de una empresa sin membresía → `404`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

Las operaciones de bloqueo y desbloqueo del proveedor son la [75](#75-post-company-supplierscompany_supplier_idblock) y la [76](#76-post-company-supplierscompany_supplier_idunblock).

### 25. `GET /company-summaries`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-summaries`; permiso `company_products:read`. Sin `company_id`: devuelve las **empresas con membresía del usuario**. Parámetros: `page`, `page_size` (1–100, por defecto **1**). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-summaries?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`PaginatedResponse[CompanySummaryResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "legal_name": "Empresa Ejemplo S.A.S.",
      "company_products": {"total": 320, "ACTIVE": 300, "INACTIVE": 20},
      "company_customers": {"total": 1200, "ACTIVE": 1150, "INACTIVE": 50},
      "company_suppliers": {"total": 45, "ACTIVE": 40, "INACTIVE": 3, "BLOCKED": 2}
    }
  ],
  "page": 1,
  "page_size": 1,
  "total_records": 1,
  "total_pages": 1
}
```

`legal_name` proviene de Party Identity (puede ser `null` si no se resolvió); `company_customers` y `company_suppliers` son `null` si el usuario no tiene permiso de lectura sobre ellos. Útil para la pantalla de selección de empresa.

### 26. `GET /companies/{company_id}/company-product-presentations`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations`; permiso `company_product_presentations:read`. Parámetros y ejemplo en [company_product_presentation_id](../parametros/company-product-presentation-id.md).

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CompanyProductPresentationResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
      "internal_code": "PRD-0001-CJ100",
      "sku": "ACET-500-CJ100",
      "reference_code": "REF-0001",
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": true,
      "is_default_sale": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 27. `POST /companies/{company_id}/company-product-presentations`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations`; permiso `company_product_presentations:create`. Cuerpo `CompanyProductPresentationCreate` (ver la guía del parámetro). Reglas: producto empresarial de la empresa y activo (`422 COMPANY_PRODUCT_NOT_FOUND` / `_INACTIVE`); presentación global del mismo producto global, activa y elegible (`422 GLOBAL_PRESENTATION_NOT_FOUND` / `_INACTIVE` / `_NOT_ELIGIBLE` / `_OF_OTHER_PRODUCT`); una adopción por presentación global y empresa (`409 DUPLICATE_PRESENTATION_ADOPTION`); `sku` único por empresa (`409 DUPLICATE_SKU`); las banderas `is_default_purchase`/`is_default_sale` exigen que la presentación sea comprable/vendible y activa (`422 DEFAULT_FLAG_INVALID`, `DEFAULT_REQUIRES_ACTIVE`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "internal_code": "PRD-0001-CJ100",
    "sku": "ACET-500-CJ100",
    "is_purchasable": true,
    "is_sellable": true,
    "is_default_purchase": true,
    "is_default_sale": true
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`CompanyProductPresentationResponse`; valores ilustrativos):

```json
{
  "id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ100",
  "sku": "ACET-500-CJ100",
  "reference_code": "REF-0001",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

### 28. `POST /companies/{company_id}/company-product-presentations/by-products`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations/by-products`; permiso `company_product_presentations:read`. Cuerpo: `company_product_ids` (1–100) y `status` (`ALL` por defecto). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations/by-products' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_ids": [
      "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
    ],
    "status": "ACTIVE"
  }'
```
Respuesta `200`: `items[]` (`PresentationByProductItem`) en orden `company_product_id, id`; los productos de otra empresa no aparecen. Útil para cargar de una vez las presentaciones de los productos de una venta.

Ejemplo de respuesta `200` (`PresentationsByProductsResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
      "internal_code": "PRD-0001-CJ100",
      "sku": "ACET-500-TAB",
      "reference_code": "REF-0001",
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": true,
      "is_default_sale": true,
      "status": "ACTIVE",
      "version": 1
    }
  ]
}
```

### 29. `POST /company-product-presentations/batch-lookup`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/batch-lookup`; cuerpo `{"ids": [...]}`; respuesta `items[]` con `found` y datos principales.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```

Ejemplo de respuesta `200` (`PresentationBatchLookupResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": true,
      "is_default_sale": true,
      "status": "ACTIVE",
      "version": 1,
      "internal_code": "PRD-0001-CJ100",
      "sku": "ACET-500-TAB",
      "reference_code": "REF-0001"
    }
  ]
}
```

### 30. `GET /company-product-presentations/{presentation_id}`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/{presentation_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompanyProductPresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ100",
  "sku": "ACET-500-CJ100",
  "reference_code": "REF-0001",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

### 31. `PUT /company-product-presentations/{presentation_id}`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/{presentation_id}`; permiso `company_product_presentations:update`. Cuerpo (`CompanyProductPresentationUpdate`): `version`, `internal_code`, `sku`, `reference_code` (opcionales) y las cuatro banderas obligatorias. Producto y presentación global no cambian.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "internal_code": "PRD-0001-CJ100",
    "sku": "ACET-500-CJ100",
    "is_purchasable": true,
    "is_sellable": true,
    "is_default_purchase": true,
    "is_default_sale": true
  }'
```

Ejemplo de respuesta `200` (`CompanyProductPresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ100",
  "sku": "ACET-500-CJ100",
  "reference_code": "REF-0001",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

### 32. `POST /company-product-presentations/{presentation_id}/deactivate`

`HIGH_RISK` (las líneas nuevas de venta y compra con esa presentación fallan con `409 REFERENCES_NOT_ELIGIBLE`; las aplicaciones automáticas de precio la omiten). URL `…/company-product-presentations/{presentation_id}/deactivate`; permiso `company_product_presentations:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyProductPresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ100",
  "sku": "ACET-500-CJ100",
  "reference_code": "REF-0001",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

### 33. `POST /company-product-presentations/{presentation_id}/reactivate`

`WRITE`. URL `…/company-product-presentations/{presentation_id}/reactivate`; permiso `company_product_presentations:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanyProductPresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ100",
  "sku": "ACET-500-CJ100",
  "reference_code": "REF-0001",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

### 34. `GET /companies/{company_id}/supplier-products`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products`; permiso `supplier_products:read`. Parámetros: `page`, `page_size`, `search` (≤ 100), `status`, `company_supplier_id`, `company_product_id`, `company_product_presentation_id` (UUID), `is_preferred` (boolean). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[SupplierProductResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_SupplierProductResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_code": "DF-ACET-500",
      "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
      "minimum_order_quantity": "1",
      "pack_quantity": "1",
      "negotiated_unit_cost": null,
      "currency_code": "COP",
      "expected_supplier_lead_time_hours": null,
      "priority": 1,
      "is_preferred": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

`SupplierProductResponse`: `id` (`supplier_product_id`, el que acepta `lines[].supplier_product_id` en Purchase), `company_id`, `status`, `version`, trazabilidad, `company_supplier_id`, `company_product_id`, `company_product_presentation_id`, `supplier_product_code`, `purchase_unit_id` (unidad de compra de Product Catalog), `minimum_order_quantity`, `pack_quantity`, `negotiated_unit_cost`, `currency_code`, `expected_supplier_lead_time_hours`, `priority`, `is_preferred`.

### 35. `POST /companies/{company_id}/supplier-products`

`WRITE`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-products`; permiso `supplier_products:create`. Cuerpo (`SupplierProductCreate`):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` (no bloqueado) | [company_supplier_id](../parametros/supplier-id.md) |
| `company_product_id` | UUID | Sí | Producto activo y comprable | [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID \| null | No | Presentación comprable del mismo producto | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `supplier_product_code` | string \| null | No | ≤ 100 | — |
| `purchase_unit_id` | UUID | Sí | Unidad de medida de Product Catalog; debe ser la unidad base del producto (`422 PURCHASE_UNIT_NOT_BASE_UNIT`) | [Product Catalog](product-catalog.md), unidades de medida |
| `minimum_order_quantity` | number \| string | No (`0`) | ≥ 0 | — |
| `pack_quantity` | number \| string | No (`1`) | > 0 | — |
| `negotiated_unit_cost` | number \| string \| null | No | ≥ 0 | — |
| `currency_code` | string | Sí | 1–10 | — |
| `expected_supplier_lead_time_hours` | number \| string \| null | No | — | — |
| `priority` | integer \| null | No | 0–32767 | — |
| `is_preferred` | boolean | No (`false`) | — | — |

Reglas: una relación por proveedor, producto y presentación (`409 DUPLICATE_SUPPLIER_PRODUCT`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-products' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "supplier_product_code": "DF-ACET-500",
    "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
    "minimum_order_quantity": "1",
    "pack_quantity": "1",
    "currency_code": "COP",
    "priority": 1,
    "is_preferred": true,
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61"
  }'
```
Respuesta `201`.

Ejemplo de respuesta `201` (`SupplierProductResponse`; valores ilustrativos):

```json
{
  "id": "1d51dc80-b75a-4a4a-8a2d-a2dce0fe061e",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "1",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": null,
  "priority": 1,
  "is_preferred": true
}
```

### 36. `GET /supplier-products/{supplier_product_id}`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-products/{supplier_product_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-products/c4a2e71f-eb2e-4fd8-84fc-8226032f8738' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`SupplierProductResponse`; valores ilustrativos):

```json
{
  "id": "c4a2e71f-eb2e-4fd8-84fc-8226032f8738",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "1",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": null,
  "priority": 1,
  "is_preferred": true
}
```

### 37. `PUT /supplier-products/{supplier_product_id}`

`WRITE`. URL `…/supplier-products/{supplier_product_id}`; permiso `supplier_products:update`. Cuerpo (`SupplierProductUpdate`): `version`, `purchase_unit_id`, `minimum_order_quantity`, `pack_quantity`, `currency_code`, `is_preferred` (obligatorios); `company_product_presentation_id`, `supplier_product_code`, `negotiated_unit_cost`, `expected_supplier_lead_time_hours`, `priority` (opcionales). Proveedor y producto no cambian.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-products/c4a2e71f-eb2e-4fd8-84fc-8226032f8738' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "supplier_product_code": "DF-ACET-500",
    "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
    "minimum_order_quantity": "1",
    "pack_quantity": "1",
    "currency_code": "COP",
    "priority": 1,
    "is_preferred": true
  }'
```

Ejemplo de respuesta `200` (`SupplierProductResponse`; valores ilustrativos):

```json
{
  "id": "c4a2e71f-eb2e-4fd8-84fc-8226032f8738",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "1",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": null,
  "priority": 1,
  "is_preferred": true
}
```

### 38. `POST /supplier-products/{supplier_product_id}/deactivate`

`WRITE`. URL `…/supplier-products/{supplier_product_id}/deactivate`; permiso `supplier_products:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-products/c4a2e71f-eb2e-4fd8-84fc-8226032f8738/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SupplierProductResponse`; valores ilustrativos):

```json
{
  "id": "c4a2e71f-eb2e-4fd8-84fc-8226032f8738",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "1",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": null,
  "priority": 1,
  "is_preferred": true
}
```

### 39. `POST /supplier-products/{supplier_product_id}/reactivate`

`WRITE`. URL `…/supplier-products/{supplier_product_id}/reactivate`; permiso `supplier_products:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-products/c4a2e71f-eb2e-4fd8-84fc-8226032f8738/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SupplierProductResponse`; valores ilustrativos):

```json
{
  "id": "c4a2e71f-eb2e-4fd8-84fc-8226032f8738",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "supplier_product_code": "DF-ACET-500",
  "purchase_unit_id": "0e747814-44f0-4d53-86bd-831b90fb587e",
  "minimum_order_quantity": "1",
  "pack_quantity": "1",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "expected_supplier_lead_time_hours": null,
  "priority": 1,
  "is_preferred": true
}
```

### 40. `GET /companies/{company_id}/supplier-payment-conditions`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/supplier-payment-conditions`; permiso `supplier_payment_conditions:read`. Parámetros: `page`, `page_size`, `status`, `company_supplier_id`, `payment_condition_type_id` (UUID de Payment Reference), `currency_code` (3 letras), `is_default`, `applicable_at` (date-time; vigentes en ese instante). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[SupplierPaymentConditionResponse]` (`id` = `supplier_payment_condition_id` que acepta Purchase; `company_supplier_id`, `payment_condition_type_id`, `currency_code`, `payment_terms_days`, `credit_limit`, `interest_rate_percentage`, `cash_discount_percentage`, `is_default`, `valid_from`, `valid_to`, `status`, `version`, trazabilidad). Ejemplo parcial en [company_supplier_id](../parametros/supplier-id.md).

Ejemplo de respuesta `200` (`PaginatedResponse_SupplierPaymentConditionResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
      "currency_code": "COP",
      "payment_terms_days": 30,
      "credit_limit": null,
      "interest_rate_percentage": null,
      "cash_discount_percentage": null,
      "is_default": true,
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 41. `POST /companies/{company_id}/supplier-payment-conditions`

`WRITE`. URL `…/companies/{company_id}/supplier-payment-conditions`; permiso `supplier_payment_conditions:create`. Cuerpo (`SupplierPaymentConditionCreate`): `company_supplier_id` (proveedor `ACTIVE`), `payment_condition_type_id` (tipo activo en [Payment Reference](payment-reference.md); `422 PAYMENT_CONDITION_TYPE_NOT_FOUND` / `_INACTIVE`), `currency_code` (1–10), `payment_terms_days` (0–3650; coherente con el tipo: `422 PAYMENT_TERMS_INCONSISTENT`), `credit_limit`, `interest_rate_percentage`, `cash_discount_percentage` (opcionales), `is_default` (`false`), `valid_from`, `valid_to` (`422 VALIDITY_INVALID`). El `code` del tipo se lee de Payment Reference en cada validación. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/supplier-payment-conditions' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
    "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
    "currency_code": "COP",
    "payment_terms_days": 30,
    "is_default": true,
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```
Respuesta `201`. Purchase solo acepta en el MVP condiciones cuyo tipo sea de contado.

Ejemplo de respuesta `201` (`SupplierPaymentConditionResponse`; valores ilustrativos):

```json
{
  "id": "6c87690b-4ca7-4c9d-8752-ca37a23afd94",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": null,
  "interest_rate_percentage": null,
  "cash_discount_percentage": null,
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

### 42. `GET /supplier-payment-conditions/{condition_id}`

`READ`. URL `…/supplier-payment-conditions/{condition_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-payment-conditions/bb531585-1d44-4e53-8a15-cec37597d4fb' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`SupplierPaymentConditionResponse`; valores ilustrativos):

```json
{
  "id": "bb531585-1d44-4e53-8a15-cec37597d4fb",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": null,
  "interest_rate_percentage": null,
  "cash_discount_percentage": null,
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

### 43. `PUT /supplier-payment-conditions/{condition_id}`

`WRITE`. URL `…/supplier-payment-conditions/{condition_id}`; permiso `supplier_payment_conditions:update`. Cuerpo (`SupplierPaymentConditionUpdate`): `version`, `payment_condition_type_id`, `currency_code`, `payment_terms_days`, `is_default`, `valid_from` obligatorios; `credit_limit`, `interest_rate_percentage`, `cash_discount_percentage`, `valid_to` opcionales. El proveedor no cambia.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-payment-conditions/bb531585-1d44-4e53-8a15-cec37597d4fb' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
    "currency_code": "COP",
    "payment_terms_days": 30,
    "is_default": true,
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```

Ejemplo de respuesta `200` (`SupplierPaymentConditionResponse`; valores ilustrativos):

```json
{
  "id": "bb531585-1d44-4e53-8a15-cec37597d4fb",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": null,
  "interest_rate_percentage": null,
  "cash_discount_percentage": null,
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

### 44. `POST /supplier-payment-conditions/{condition_id}/deactivate`

`WRITE`. URL `…/supplier-payment-conditions/{condition_id}/deactivate`; permiso `supplier_payment_conditions:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-payment-conditions/bb531585-1d44-4e53-8a15-cec37597d4fb/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SupplierPaymentConditionResponse`; valores ilustrativos):

```json
{
  "id": "bb531585-1d44-4e53-8a15-cec37597d4fb",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": null,
  "interest_rate_percentage": null,
  "cash_discount_percentage": null,
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

### 45. `POST /supplier-payment-conditions/{condition_id}/reactivate`

`WRITE`. URL `…/supplier-payment-conditions/{condition_id}/reactivate`; permiso `supplier_payment_conditions:update`; cuerpo `{"version": n}`; exige proveedor `ACTIVE`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/supplier-payment-conditions/bb531585-1d44-4e53-8a15-cec37597d4fb/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`SupplierPaymentConditionResponse`; valores ilustrativos):

```json
{
  "id": "bb531585-1d44-4e53-8a15-cec37597d4fb",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "payment_condition_type_id": "83fa1b9b-46a4-4c7b-8ed0-5eebeb926cfd",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": null,
  "interest_rate_percentage": null,
  "cash_discount_percentage": null,
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

### 46. `GET /companies/{company_id}/price-lists`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists`; permiso `price_lists:read`. Parámetros: `page`, `page_size`, `search` (≤ 100), `status`, `currency_code` (3 letras), `is_default` (boolean). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PriceListResponse]`.

`PriceListResponse`: `id` (`price_list_id`), `company_id`, `status`, `version`, trazabilidad, `code`, `name`, `description`, `currency_code`, `is_default`, `valid_from`, `valid_to`.

```json
{
  "items": [
    {
      "id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-10T10:00:00Z",
      "code": "GENERAL",
      "name": "Lista general",
      "description": null,
      "currency_code": "COP",
      "is_default": true,
      "valid_from": "2026-02-10T10:00:00Z",
      "valid_to": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 47. `POST /companies/{company_id}/price-lists`

`WRITE`. URL `…/companies/{company_id}/price-lists`; permiso `price_lists:create`. Cuerpo (`PriceListCreate`): `code` (1–50; único por empresa: `409 DUPLICATE_PRICE_LIST_CODE`), `name` (1–120), `currency_code` (1–10; **inmutable** después), `description`, `valid_from`, `valid_to`, `is_default` (`false`). Regla: la lista predeterminada es **única por empresa y moneda** entre las `ACTIVE`; crear otra predeterminada en la misma moneda **reemplaza** a la anterior (le retira `is_default`; verificado en el código), y desactivar la predeterminada le retira también esa marca. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "MOSTRADOR",
    "name": "Precio de mostrador",
    "currency_code": "COP",
    "description": "Descripción ilustrativa",
    "valid_from": "2026-10-01T00:00:00Z",
    "is_default": true
  }'
```
Respuesta `201`. Sin una lista predeterminada activa y vigente en la moneda del producto, las ventas sin `price_list_id` fallan (`NO_APPLICABLE_PRICE_LIST`).

Ejemplo de respuesta `201` (`PriceListResponse`; valores ilustrativos):

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

### 48. `GET /price-lists/{price_list_id}`

`READ`. URL `…/price-lists/{price_list_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PriceListResponse`; valores ilustrativos):

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

### 49. `PUT /price-lists/{price_list_id}`

`WRITE`. URL `…/price-lists/{price_list_id}`; permiso `price_lists:update`. Cuerpo (`PriceListUpdate`): `version`, `code`, `name`, `is_default` obligatorios; `description`, `valid_from`, `valid_to` opcionales. La moneda no se envía (inmutable).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "code": "MOSTRADOR",
    "name": "Precio de mostrador",
    "description": "Descripción ilustrativa",
    "valid_from": "2026-10-01T00:00:00Z",
    "is_default": true
  }'
```

Ejemplo de respuesta `200` (`PriceListResponse`; valores ilustrativos):

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

### 50. `POST /price-lists/{price_list_id}/deactivate`

`HIGH_RISK`: una lista inactiva deja de resolver precios (las ventas que la pidan fallan con `PRICE_LIST_NOT_APPLICABLE`; si era la predeterminada, con `NO_APPLICABLE_PRICE_LIST`). URL `…/price-lists/{price_list_id}/deactivate`; permiso `price_lists:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PriceListResponse`; valores ilustrativos):

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

### 51. `POST /price-lists/{price_list_id}/reactivate`

`WRITE`. URL `…/price-lists/{price_list_id}/reactivate`; permiso `price_lists:update`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PriceListResponse`; valores ilustrativos):

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

### 52. `GET /companies/{company_id}/price-list-items`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items`; permiso `price_list_items:read`. Parámetros: `page`, `page_size`, `status`, `price_list_id`, `company_product_id`, `company_product_presentation_id` (UUID), `applicable_at` (date-time; vigentes en ese instante). 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PriceListItemResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_PriceListItemResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
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
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

`PriceListItemResponse`: `id` (`price_list_item_id`), `company_id`, `status`, `version`, trazabilidad, `price_list_id`, `company_product_id`, `company_product_presentation_id`, `unit_price` (precio **por presentación**), `currency_code` (de la lista), `valid_from`, `valid_to`, `origin` (`MANUAL` para los creados por esta operación, `AUTOMATIC` cuando lo creó una aplicación automática; verificado en el código), `closure_reason` (p. ej. `AUTOMATIC_SUPERSEDED`), `automatic_application_id`.

### 53. `POST /companies/{company_id}/price-list-items`

`WRITE`. URL `…/companies/{company_id}/price-list-items`; permiso `price_list_items:create`. Cuerpo (`PriceListItemCreate`):

| Campo | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|
| `price_list_id` | UUID | Sí | Lista de la empresa, activa (`422 PRICE_LIST_NOT_FOUND` / `_INACTIVE`) | Operación 46 |
| `company_product_id` | UUID | Sí | Producto de la empresa | [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID | Sí | Presentación del mismo producto (`422 PRICE_ITEM_WITHOUT_PRESENTATION`, `PRESENTATION_OF_OTHER_PRODUCT`) | [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `unit_price` | number \| string | Sí | ≥ 0; escala admitida (`422 PRICE_SCALE_NOT_ALLOWED`) | — |
| `valid_from`, `valid_to` | date-time \| null | No | Sin solapar otro precio de la misma lista y presentación (`409 PRICE_PERIOD_OVERLAP`) | — |

```json
{
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "unit_price": "800.00",
  "valid_from": "2026-10-20T00:00:00Z"
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "unit_price": "800.00",
    "valid_from": "2026-10-20T00:00:00Z"
  }'
```

Respuesta `201`. La moneda del precio es la de la lista.

Ejemplo de respuesta `201` (`PriceListItemResponse`; valores ilustrativos):

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

### 54. `GET /price-list-items/{price_list_item_id}`

`READ`. URL `…/price-list-items/{price_list_item_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PriceListItemResponse`; valores ilustrativos):

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

### 55. `PUT /price-list-items/{price_list_item_id}`

`WRITE`. URL `…/price-list-items/{price_list_item_id}`; permiso `price_list_items:update`. Cuerpo (`PriceListItemUpdate`): `version`, `unit_price`, `valid_from` obligatorios; `valid_to` opcional. Regla: un precio **futuro** se puede cambiar en valor y vigencia; un precio **en vigencia** solo admite posponer o fijar su fin (`422 PRICE_IN_EFFECT_NOT_MODIFIABLE`, `422 PRICE_CHANGE_OUT_OF_PERIOD`). Para cambiar el valor vigente use la operación 56.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "unit_price": "800.00",
    "valid_from": "2026-10-01T00:00:00Z"
  }'
```

Ejemplo de respuesta `200` (`PriceListItemResponse`; valores ilustrativos):

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

### 56. `POST /price-list-items/{price_list_item_id}/change-price`

`HIGH_RISK` (cambia el precio de venta vigente). URL `…/price-list-items/{price_list_item_id}/change-price`; permiso `price_list_items:update`. Cuerpo (`PriceChangeRequest`): `unit_price` (obligatorio), `effective_from` (date-time; por defecto ahora), `version`. Cierra el precio vigente en `effective_from` y crea el nuevo en una sola transacción. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c/change-price' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "unit_price": "800.00",
    "version": 1
  }'
```
Respuesta `201` (`PriceChangeResponse`): `{"item": <nuevo PriceListItemResponse>, "previous": <anterior cerrado>}`. `409 PRICE_CLOSED_BY_AUTOMATIC_UPDATE` si una aplicación automática lo cerró entre tanto.

### 57. `POST /price-list-items/{price_list_item_id}/deactivate`

`HIGH_RISK` (la presentación queda sin precio en esa lista: `NO_PRICE_IN_LIST`). URL `…/price-list-items/{price_list_item_id}/deactivate`; permiso `price_list_items:delete`; cuerpo `{"version": n}`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PriceListItemResponse`; valores ilustrativos):

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

### 58. `POST /price-list-items/{price_list_item_id}/reactivate`

`WRITE`. URL `…/price-list-items/{price_list_item_id}/reactivate`; permiso `price_list_items:update`; cuerpo `{"version": n}`; `409 PRICE_PERIOD_OVERLAP` si otro precio ocupa la vigencia.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PriceListItemResponse`; valores ilustrativos):

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

### 59. `POST /companies/{company_id}/applicable-prices/resolve`

| | |
|---|---|
| Clasificación | `READ` (consulta por `POST`; la usa Sales al crear y confirmar ventas) |
| URL | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/applicable-prices/resolve` |
| Permiso | `price_list_items:read` |

Cuerpo (`ApplicablePriceRequest`): `at` (date-time; por defecto ahora) y `lines[]` (1–100) con `line_id` (≤ 64, eco opcional), `company_product_id`, `company_product_presentation_id` (obligatorios) y `price_list_id` (opcional).

```json
{
  "lines": [
    {
      "line_id": "1",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    }
  ]
}
```

Ejemplo de solicitud con el cuerpo anterior:

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/applicable-prices/resolve' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "lines": [
      {
        "line_id": "1",
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
      }
    ]
  }'
```

Respuesta `200` (`ApplicablePriceResponse`):

```json
{
  "at": "2026-10-19T18:00:00Z",
  "items": [
    {
      "line_id": "1",
      "found": true,
      "resolution": "PRICE_LIST_ITEM",
      "basis": "PRESENTATION",
      "unit_price": "800.00",
      "currency_code": "COP",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "company_product_status": "ACTIVE",
      "presentation_status": "ACTIVE"
    }
  ]
}
```

Orden de resolución (verificado): (1) lista: la indicada si es de la empresa, `ACTIVE` y vigente en `at` (si no, `resolution: PRICE_LIST_NOT_APPLICABLE`), o la **predeterminada** activa y vigente en la moneda del producto (si no la hay, `NO_APPLICABLE_PRICE_LIST`); (2) en la lista, **solo** el precio explícito de la presentación (`basis: PRESENTATION`); sin él, `NO_PRICE_IN_LIST`. No hay precios por producto ni conversiones. No juzga la aptitud: informa `company_product_status` y `presentation_status` para que el consumidor decida.

### 60. `POST /companies/{company_id}/pricing-policies/coverage`

`READ`. URL `…/companies/{company_id}/pricing-policies/coverage`; permiso `pricing_policy_coverage:read`. Cuerpo (`CoverageRequest`): `currency_code` (1–10) y `company_product_presentation_ids` (≥ 1). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/pricing-policies/coverage' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "currency_code": "COP",
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    ]
  }'
```
Respuesta `200`: `items[]` con `company_product_presentation_id`, `found`, `covered` (tiene política de ganancia aplicable en alguna lista activa y vigente de esa moneda) y `price_list_ids`. Sin porcentajes. Lo usa Purchase antes de confirmar (`PRICING_POLICY_NOT_CONFIGURED`).

Ejemplo de respuesta `200` (`CoverageResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "found": true,
      "covered": true,
      "price_list_ids": [
        "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b"
      ]
    }
  ]
}
```

### 61. `GET /companies/{company_id}/price-lists/{price_list_id}/pricing-policies`

`READ`. URL `…/companies/{company_id}/price-lists/{price_list_id}/pricing-policies`; permiso `pricing_policies:read`. Parámetros: `status` (`ACTIVE`, `INACTIVE`, `ALL`), `search` (≤ 100), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PricingPolicyResponse]` (`id` = `policy_id`, `company_id`, `price_list_id`, `name`, `markup_percentage` (vigente), `presentation_count`, `status`, `deactivated_at`, `deactivation_reason`, `version`, trazabilidad).

Ejemplo de respuesta `200` (`PaginatedResponse_PricingPolicyResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
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
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 62. `POST /companies/{company_id}/price-lists/{price_list_id}/pricing-policies`

`WRITE` (no modifica precios). URL `…/companies/{company_id}/price-lists/{price_list_id}/pricing-policies`; permiso `pricing_policies:create`. Cuerpo (`PricingPolicyCreate`): `name` (1–120; único en la lista: `409 POLICY_NAME_DUPLICATE`), `markup_percentage` (0 a 1000; `422 MARKUP_PERCENTAGE_OUT_OF_RANGE`), `company_product_presentation_ids` (hasta 1000; cada presentación pertenece a lo sumo a una política de la misma lista: `409 PRESENTATION_ALREADY_IN_POLICY`). 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Margen general 30 %",
    "markup_percentage": "30",
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    ]
  }'
```
Respuesta `201`.

```json
{
  "name": "Margen estándar",
  "markup_percentage": "35",
  "company_product_presentation_ids": ["a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"]
}
```

### 63. `GET /pricing-policies/{policy_id}`

`READ`. URL `…/pricing-policies/{policy_id}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
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

### 64. `PUT /pricing-policies/{policy_id}`

`WRITE`. URL `…/pricing-policies/{policy_id}`; permiso `pricing_policies:update`. Cuerpo (`PricingPolicyRename`): `version`, `name`. Solo renombra.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Margen general 30 %"
  }'
```

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
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

### 65. `GET /pricing-policies/{policy_id}/terms`

`READ`. URL `…/pricing-policies/{policy_id}/terms`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/terms' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: **array** de `PolicyTermResponse` (`id`, `markup_percentage`, `valid_from`, `valid_to`, `created_by`, `closed_by`): historial inmutable de porcentajes.

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "markup_percentage": "30",
    "valid_from": "2026-10-01T00:00:00Z",
    "valid_to": null,
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "closed_by": null
  }
]
```

### 66. `GET /pricing-policies/{policy_id}/presentations`

`READ`. URL `…/pricing-policies/{policy_id}/presentations`; `include_closed` (boolean), `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[PolicyPresentationResponse]` (`id`, `company_product_presentation_id`, `valid_from`, `valid_to`, `created_by`, `closed_by`).

Ejemplo de respuesta `200` (`PaginatedResponse_PolicyPresentationResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "valid_from": "2026-10-01T00:00:00Z",
      "valid_to": null,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "closed_by": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

### 67. `POST /pricing-policies/{policy_id}/presentations`

`WRITE`. URL `…/pricing-policies/{policy_id}/presentations`; permiso `pricing_policies:update`. Cuerpo (`PresentationsChange`): `version`, `company_product_presentation_ids` (límite efectivo **1000** por solicitud, `max_length=1000` en el modelo, verificado en el código; el resumen del contrato de creación dice «hasta 100», que es el límite al crear la política). Abre una vigencia por presentación; `409 PRESENTATION_ALREADY_IN_POLICY`, `409 POLICY_INACTIVE`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    ]
  }'
```
Respuesta `200` con la política.

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
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

### 68. `POST /pricing-policies/{policy_id}/percentage`

`HIGH_RISK` (desde la siguiente recepción cambian los precios de venta calculados). URL `…/pricing-policies/{policy_id}/percentage`; permiso `pricing_policies:update`. Cuerpo (`PercentageChange`): `version`, `markup_percentage` (0–1000). Cierra el término vigente y abre otro; no modifica precios existentes.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/percentage' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "markup_percentage": "30"
  }'
```

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
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

### 69. `POST /pricing-policies/{policy_id}/presentations/remove`

`WRITE`. URL `…/pricing-policies/{policy_id}/presentations/remove`; permiso `pricing_policies:update`. Cuerpo `PresentationsChange`. Cierra la vigencia de las presentaciones (`409 PRESENTATION_NOT_IN_POLICY`).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations/remove' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    ]
  }'
```

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "812fee6b-c24f-4c11-8c03-87e9fe93c0ae",
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

### 70. `POST /pricing-policies/{policy_id}/deactivate`

`HIGH_RISK` · estado final (no se reactiva); las presentaciones quedan sin política y las recepciones posteriores se omiten (`SKIPPED_NO_POLICY`). URL `…/pricing-policies/{policy_id}/deactivate`; permiso `pricing_policies:delete`. Cuerpo (`PolicyDeactivation`): `version`, `reason` (1–500). Cierra el término y las asignaciones.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "reason": "Solicitud del cliente"
  }'
```

Ejemplo de respuesta `200` (`PricingPolicyResponse`; valores ilustrativos):

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
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

### 71. `POST /companies/{company_id}/automatic-price-update-requests`

`WRITE`. URL `…/companies/{company_id}/automatic-price-update-requests`; permiso `automatic_price_update_requests:submit` **y** identidad técnica (cuenta de servicio de Purchase). **No usar desde el frontend.** Cuerpo (`PriceUpdateRequestIn`): `contract_version` (1), `purchase_detail_id`, `purchase_id`, `branch_id`, `company_product_id`, `company_product_presentation_id`, `sequence` (> 0), `previous_sequence`, `currency_code`, `line_total` (≥ 0), `quantity` (> 0), `previous_purchase_detail_id`, `previous_line_total`, `previous_quantity`, `received_at`, `received_by_user_id`. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-update-requests' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "contract_version": 1,
    "purchase_detail_id": "77cd1afa-2a02-454d-8b23-7a29331aab97",
    "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "sequence": 1,
    "currency_code": "COP",
    "line_total": "1600.00",
    "quantity": "2",
    "received_at": "2026-10-19T15:04:05Z",
    "received_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
  }'
```
Respuesta `202` (`PriceUpdateRequestAccepted`): `request_id` y `applications[]` (`id`, `price_list_id`, `status`), una por lista con política aplicable. `409 REQUEST_CONFLICT` / `SEQUENCE_CONFLICT` si la solicitud es incoherente con la serie.

Ejemplo de respuesta `202` (`PriceUpdateRequestAccepted`; valores ilustrativos):

```json
{
  "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
  "applications": [
    {
      "id": "07d5d6fb-52f6-4f2b-8370-1318d5d4a00f",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "status": "APPLIED"
    }
  ]
}
```

### 72. `GET /companies/{company_id}/automatic-price-applications`

`READ`. URL `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/automatic-price-applications`; permiso `automatic_price_applications:read` (administradores y supervisores). Parámetros: `status` (`PENDING`, `FAILED`, `APPLIED`, `UNCHANGED`, `SKIPPED_NO_POLICY`, `SKIPPED_LIST_NOT_EFFECTIVE`, `SKIPPED_CURRENCY_MISMATCH`, `SKIPPED_PRESENTATION_INACTIVE`, `SKIPPED_ZERO_COST`, `RESOLVED`), `price_list_id`, `company_product_presentation_id`, `purchase_id`, `page`, `page_size`. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-applications?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200`: `PaginatedResponse[AutomaticPriceApplicationResponse]`.

Ejemplo de respuesta `200` (`PaginatedResponse_AutomaticPriceApplicationResponse_`; valores ilustrativos):

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

`AutomaticPriceApplicationResponse`: `id`, `company_id`, `request_id`, `purchase_id`, `purchase_detail_id`, `price_list_id`, `company_product_id`, `company_product_presentation_id`, `sequence`, `received_at`, `received_by_user_id`, `policy_id`, `markup_percentage`, `current_unit_cost`, `previous_unit_cost`, `reference_cost`, `previous_price`, `new_price`, `previous_price_item_id`, `new_price_item_id`, `cancelled_future_item_ids[]`, `status`, `attempts`, `next_attempt_at`, `last_error_code`, `first_attempt_at`, `completed_at`, `resolved_by`, `resolution_reason`, `version`, `created_at`, `updated_at`.

Reglas (verificadas): cada aplicación se procesa por un *worker* en su propia transacción, en orden de `sequence`. Orden de decisión: lista no vigente → moneda distinta → presentación inactiva → costo ≤ 0 → sin política (`SKIPPED_NO_POLICY`) → precio igual (`UNCHANGED`) → `APPLIED`. Con política se cancelan **siempre** los precios futuros de esa lista y presentación (`closure_reason: AUTOMATIC_SUPERSEDED`); `APPLIED` cierra el precio vigente y crea el nuevo con `origin: AUTOMATIC` a partir del costo de referencia × (1 + `markup_percentage`/100). Un fallo deja `FAILED` con reintentos (`attempts`, `next_attempt_at`).

### 73. `GET /companies/{company_id}/automatic-price-applications/{application_id}`

`READ`. URL `…/companies/{company_id}/automatic-price-applications/{application_id}`; permiso `automatic_price_applications:read`. `200`; `404`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-applications/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`AutomaticPriceApplicationResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
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
```

### 74. `POST /companies/{company_id}/automatic-price-applications/{application_id}/resolution`

`WRITE` (no modifica precios). URL `…/companies/{company_id}/automatic-price-applications/{application_id}/resolution`; permiso `automatic_price_applications:resolve` (administradores y supervisores). Cuerpo (`ApplicationResolution`): `version`, `reason` (10–500). Marca como `RESOLVED` una aplicación `PENDING` o `FAILED` para que deje de reintentarse; `409 APPLICATION_ALREADY_FINAL` si ya terminó. 

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-applications/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/resolution' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "reason": "Solicitud del cliente"
  }'
```
Respuesta `200`.

Ejemplo de respuesta `200` (`AutomaticPriceApplicationResponse`; valores ilustrativos):

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
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
```

### 75. `POST /company-suppliers/{company_supplier_id}/block`

| | |
|---|---|
| Clasificación | `HIGH_RISK` · Bloquear proveedor |
| URL | `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/block` |
| Permiso | `perm:commercial-relationship:company_suppliers:delete` |
| Alcance | Empresa (la del proveedor; membresía `ACTIVE` evaluada en Operational Context) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

| Nombre | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_supplier_id` | ruta | UUID | Sí | [company_supplier_id](../parametros/supplier-id.md) |

Cuerpo (`SupplierBlockRequest`; rechaza campos adicionales): `block_reason` (string 1–500, obligatorio) y `version` (integer ≥ 1, obligatorio).

Efecto: `BLOCKED` con motivo; no elegible en compras (`422 COMPANY_SUPPLIER_BLOCKED` al registrar condiciones o productos del proveedor). Transición no permitida desde el estado actual → `409 COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION`; `version` distinta → `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT`; proveedor inexistente o de una empresa sin membresía → `404`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/block' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "block_reason": "Incumplimiento de pago",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "BLOCKED",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": "Incumplimiento de pago"
}
```

### 76. `POST /company-suppliers/{company_supplier_id}/unblock`

| | |
|---|---|
| Clasificación | `WRITE` · Desbloquear proveedor |
| URL | `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/{company_supplier_id}/unblock` |
| Permiso | `perm:commercial-relationship:company_suppliers:update` |
| Alcance | Empresa (la del proveedor; membresía `ACTIVE` evaluada en Operational Context) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

| Nombre | Dónde | Tipo | Obligatorio | Cómo obtenerlo |
|---|---|---|---|---|
| `company_supplier_id` | ruta | UUID | Sí | [company_supplier_id](../parametros/supplier-id.md) |

Cuerpo (`VersionRequest`; rechaza campos adicionales): `version` (integer ≥ 1, obligatorio).

Efecto: Vuelve a `ACTIVE`; revalida la organización en Party Identity. Transición no permitida desde el estado actual → `409 COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION`; `version` distinta → `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT`; proveedor inexistente o de una empresa sin membresía → `404`.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-suppliers/d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60/unblock' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CompanySupplierResponse`; valores ilustrativos):

```json
{
  "id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 1,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "internal_code": "PRV-0001",
  "display_name": "Distribuidora Farma S.A.S.",
  "preferred_contact_person_id": null,
  "block_reason": null
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía, recurso de otra empresa o inexistente | Revisar `company_id` en `/me/operational-context` |
| `403 …OPERATIONAL_ACCESS_DENIED` / `PARTY_IDENTITY_ACCESS_DENIED` | Un proveedor respondió `403` | Revisar permisos de lectura de Operational Context y Party Identity |
| `409 …DUPLICATE_INTERNAL_CODE` / `DUPLICATE_SKU` / `DUPLICATE_ADOPTION` / `DUPLICATE_CUSTOMER` / `DUPLICATE_SUPPLIER` | Unicidad | Buscar el registro existente |
| `422 …GLOBAL_PRODUCT_NOT_ELIGIBLE` | El producto global no está completo para adoptarse | Revisar `completeness` en Product Catalog |
| `422 …PRESENTATION_OF_OTHER_PRODUCT` | Presentación que no pertenece al producto indicado | Listar presentaciones con `company_product_id` |
| `409 …PRICE_PERIOD_OVERLAP` | Dos precios vigentes a la vez en la misma lista y presentación | Usar `change-price` o ajustar vigencias |
| `422 …PRICE_IN_EFFECT_NOT_MODIFIABLE` | Intento de editar el valor de un precio vigente | Usar `change-price` |
| `409 …PRESENTATION_ALREADY_IN_POLICY` | La presentación ya está en otra política de la lista | Retirarla primero |
| `422 …MARKUP_PERCENTAGE_OUT_OF_RANGE` / `TAX_PERCENTAGE_OUT_OF_RANGE` | Porcentaje fuera de 0–1000 / 0–100 | Corregir |
| `409 …VERSION_CONFLICT` / `INVALID_STATUS_TRANSITION` | Concurrencia o estado | Recargar |
| `503` con `dependency` | Operational Context, Product Catalog, Party Identity o Payment Reference caídos | Reintentar |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía (`operational-access`, token del usuario); datos de empresa para el resumen |
| Product Catalog | Productos y presentaciones globales (existencia, elegibilidad, unidad base); registro del primer uso (cuenta técnica) |
| Party Identity | Identidades de clientes, proveedores y contactos (token del usuario); razón social en el resumen |
| Payment Reference | Tipos de condición de pago (cuenta técnica) |
| Purchase | Envía las solicitudes de actualización automática de precio tras cada recepción |
| Sales, Product Inventory Query, Inventory, Purchase, Business Reporting | Consumidores de productos, presentaciones, clientes, proveedores y precios |
| Audit | Eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 76 |
| Operaciones documentadas | 76 (74 de negocio en las fichas 3–74, con las cuatro de estado del proveedor agrupadas en la 23, más las 2 de salud) |
| Permisos contrastados con el código | Sí (`api/company_products.py`, `company_product_taxes.py`, `company_customers.py`, `company_suppliers.py`, `company_summaries.py`, `company_product_presentations.py`, `supplier_products.py`, `supplier_payment_conditions.py`, `price_lists.py`, `price_list_items.py`, `applicable_prices.py`, `pricing_policies.py`, `automatic_prices.py`, `company_scope.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado; `api/errors.py`; docstrings de `application/*_service.py`; `domain/pricing_policy.py`, `domain/purchase_tax.py`) |
| Verificado | Las listas aplican `status=ACTIVE` por defecto; una segunda lista predeterminada en la misma moneda reemplaza a la anterior; `origin: MANUAL` en precios manuales; hasta 1000 presentaciones por cambio de política (100 al crearla) |

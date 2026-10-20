# 6.5 Productos y precios

[← API principales](README.md) · [← Índice](../index.md)

Cómo una empresa llega a tener productos vendibles con precio. El modelo de SIO tiene tres capas:

| Capa | Servicio | Qué es | Identificador |
|---|---|---|---|
| **Catálogo global** | [Product Catalog](../servicios/product-catalog.md) | Productos y presentaciones compartidos por todas las empresas (nombre canónico, marca, unidad base, códigos de barras) | [global_product_id](../parametros/global-product-id.md), [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| **Adopción por la empresa** | [Commercial Relationship](../servicios/commercial-relationship.md) | El producto y las presentaciones que la empresa decide manejar, con su código interno, moneda, impuesto de compra y banderas de compra/venta | [company_product_id](../parametros/company-product-id.md), [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| **Precios de la empresa** | [Commercial Relationship](../servicios/commercial-relationship.md) | Varias listas de precios propias por moneda, precios por presentación con vigencia y políticas de porcentaje de ganancia que los actualizan automáticamente | [price_list_id](../parametros/price-list-id.md), `price_list_item_id`, [policy_id](../parametros/pricing-policy-id.md) |

Ventas, Compras e Inventario trabajan siempre con la capa de empresa. Flujo completo con JSON: [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar productos globales | `GET /api/v1/products` (PC) | `perm:product-catalog:products:read` | [PC 49](../servicios/product-catalog.md#49-get-products) |
| 2 | Crear un producto global | `POST /api/v1/products` (PC) | `perm:product-catalog:products:create` | [PC 50](../servicios/product-catalog.md#50-post-products) |
| 3 | Consultar y crear presentaciones globales | `GET` · `POST /api/v1/products/{product_id}/presentations` (PC) | `perm:product-catalog:products:read` · `…:update` | [PC 67](../servicios/product-catalog.md#67-get-productsproduct_idpresentations) · [PC 68](../servicios/product-catalog.md#68-post-productsproduct_idpresentations) |
| 4 | Registrar códigos de barras | `POST /api/v1/products/{product_id}/identifiers` (PC) | `perm:product-catalog:products:update` | [PC 74](../servicios/product-catalog.md#74-post-productsproduct_ididentifiers) |
| 5 | Adoptar un producto global en la empresa | `POST /api/v1/companies/{company_id}/company-products` (CR) | `perm:commercial-relationship:company_products:create` | [CR 4](../servicios/commercial-relationship.md#4-post-companiescompany_idcompany-products) |
| 6 | Consultar los productos de la empresa | `GET /api/v1/companies/{company_id}/company-products` (CR) | `perm:commercial-relationship:company_products:read` | [CR 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products) |
| 7 | Adoptar y consultar presentaciones de la empresa | `POST` · `GET /api/v1/companies/{company_id}/company-product-presentations` (CR) | `perm:commercial-relationship:company_product_presentations:create` · `…:read` | [CR 27](../servicios/commercial-relationship.md#27-post-companiescompany_idcompany-product-presentations) · [CR 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations) |
| 8 | Configurar el impuesto de compra del producto | `PUT /api/v1/company-products/{company_product_id}/purchase-tax` (CR) | `perm:commercial-relationship:company_product_purchase_taxes:update` | [CR 11](../servicios/commercial-relationship.md#11-put-company-productscompany_product_idpurchase-tax) |
| 9 | Crear una lista de precios | `POST /api/v1/companies/{company_id}/price-lists` (CR) | `perm:commercial-relationship:price_lists:create` | [CR 47](../servicios/commercial-relationship.md#47-post-companiescompany_idprice-lists) |
| 10 | Consultar las listas de la empresa | `GET /api/v1/companies/{company_id}/price-lists` (CR) | `perm:commercial-relationship:price_lists:read` | [CR 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists) |
| 11 | Modificar una lista (vigencia, predeterminada) | `PUT /api/v1/price-lists/{price_list_id}` (CR) | `perm:commercial-relationship:price_lists:update` | [CR 49](../servicios/commercial-relationship.md#49-put-price-listsprice_list_id) |
| 12 | Registrar un precio manual por presentación | `POST /api/v1/companies/{company_id}/price-list-items` (CR) | `perm:commercial-relationship:price_list_items:create` | [CR 53](../servicios/commercial-relationship.md#53-post-companiescompany_idprice-list-items) |
| 13 | Consultar precios vigentes (por lista o por presentación) | `GET /api/v1/companies/{company_id}/price-list-items` (CR) | `perm:commercial-relationship:price_list_items:read` | [CR 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items) |
| 14 | Cambiar un precio vigente | `POST /api/v1/price-list-items/{price_list_item_id}/change-price` (CR) | `perm:commercial-relationship:price_list_items:update` | [CR 56](../servicios/commercial-relationship.md#56-post-price-list-itemsprice_list_item_idchange-price) |
| 15 | Corregir un precio futuro o cerrar uno vigente | `PUT /api/v1/price-list-items/{price_list_item_id}` (CR) | `perm:commercial-relationship:price_list_items:update` | [CR 55](../servicios/commercial-relationship.md#55-put-price-list-itemsprice_list_item_id) |
| 16 | Crear una política de porcentaje de ganancia | `POST /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` (CR) | `perm:commercial-relationship:pricing_policies:create` | [CR 62](../servicios/commercial-relationship.md#62-post-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 17 | Consultar las políticas de una lista | `GET /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` (CR) | `perm:commercial-relationship:pricing_policies:read` | [CR 61](../servicios/commercial-relationship.md#61-get-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 18 | Asociar o retirar presentaciones de una política | `POST /api/v1/pricing-policies/{policy_id}/presentations` · `…/presentations/remove` (CR) | `perm:commercial-relationship:pricing_policies:update` | [CR 67](../servicios/commercial-relationship.md#67-post-pricing-policiespolicy_idpresentations) · [CR 69](../servicios/commercial-relationship.md#69-post-pricing-policiespolicy_idpresentationsremove) |
| 19 | Cambiar el porcentaje de una política | `POST /api/v1/pricing-policies/{policy_id}/percentage` (CR) | `perm:commercial-relationship:pricing_policies:update` | [CR 68](../servicios/commercial-relationship.md#68-post-pricing-policiespolicy_idpercentage) |
| 20 | Verificar cobertura y ver precios automáticos aplicados | `POST /api/v1/companies/{company_id}/pricing-policies/coverage` · `GET /api/v1/companies/{company_id}/automatic-price-applications` (CR) | `perm:commercial-relationship:pricing_policy_coverage:read` · `…automatic_price_applications:read` | [CR 60](../servicios/commercial-relationship.md#60-post-companiescompany_idpricing-policiescoverage) · [CR 72](../servicios/commercial-relationship.md#72-get-companiescompany_idautomatic-price-applications) |

Bases: Product Catalog `https://sio-product-catalog-dev.onrender.com/api/v1`; Commercial Relationship `https://sio-commercial-relationship-dev.onrender.com/api/v1`. La vista consolidada de productos con precio y existencias para el frontend está en [Inventario §1](inventario.md#1-buscar-productos-con-precio-y-existencias) (Product Inventory Query).

---

## Catálogo global

### 1. Buscar productos globales

**¿Qué puede hacer el usuario?** Encontrar en el catálogo compartido el producto que quiere incorporar a su empresa, por nombre, código de barras, marca o categoría.

**¿Qué API debe consumir el frontend?** `GET https://sio-product-catalog-dev.onrender.com/api/v1/products`. Permiso `perm:product-catalog:products:read`. Consulta: `search` (≤ 200), `identifier` (código de barras exacto), `brand_id`, `category_id` + `include_descendants`, `manufacturer_organization_id`, `group_id`, `attribute_filters` (`CODIGO:valor`, repetible), `status`, `page`, `page_size` (1–100).

**¿Qué necesita antes?** Solo el token: el catálogo es global y no exige membresía.

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[ProductResponse]`; `items[].id` es el [global_product_id](../parametros/global-product-id.md). Cada producto trae `canonical_name`, `product_type`, `brand`, `base_unit`, `status` y un bloque `completeness` con lo que le falta para ser adoptable.

### 2. Crear un producto global

**¿Qué puede hacer el usuario?** Dar de alta un producto que no existe en el catálogo.

**¿Qué API debe consumir el frontend?** `POST https://sio-product-catalog-dev.onrender.com/api/v1/products`. Permiso `perm:product-catalog:products:create`. Cuerpo `ProductCreate`: `product_type` (`GOOD`), `canonical_name` (≤ 400), `base_unit_id` (obligatorios); `description`, `global_brand_id`, `manufacturer_organization_id`.

**¿Qué necesita antes?** La unidad base (`GET …/units-of-measure`, PC 4) y, opcionalmente, la marca (`GET …/brands`, PC 16) y la categoría (`GET …/categories`, PC 30). Antes de crear, busca con la funcionalidad 1 e `identifier=<código de barras>` para no duplicar.

**¿Cómo sabe que funcionó?** `201` con `ProductResponse` (`id`, `status: "ACTIVE"`, `version: 1`). Un producto recién creado **no tiene presentaciones**: sin al menos una presentación global, la empresa no podrá adoptar nada vendible (funcionalidad 3). Errores: `409` nombre canónico duplicado, `422 VALIDATION_ERROR`.

### 3. Consultar y crear presentaciones globales

**¿Qué puede hacer el usuario?** Definir cómo se presenta el producto (unidad, caja por 100, blíster por 10) y cuántas unidades base contiene cada una.

**¿Qué API debe consumir el frontend?** `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations?status=ACTIVE` y `POST` a la misma ruta (permiso `perm:product-catalog:products:update`) con `code`, `name`, `base_quantity` (unidades base que contiene; por defecto `1`), `is_base` (una sola por producto), `packaging_type_id`, `content_quantity`, `content_unit_id`, `display_order`.

**¿Cómo sabe que funcionó?** `200` con un arreglo de `PresentationResponse` o `201` con la nueva; `id` es el [global_product_presentation_id](../parametros/global-product-presentation-id.md). Errores: `409` código repetido o segunda presentación base.

### 4. Registrar códigos de barras

`POST https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers` (permiso `perm:product-catalog:products:update`) con `identifier_type` (`GTIN`, `EAN`, `UPC`, `BARCODE`, `OTHER`, `IUM`), `value` (≤ 200), `global_product_presentation_id` (opcional: a qué presentación pertenece el código) e `is_primary`. Responde `201`. Después, la búsqueda por `identifier` de la funcionalidad 1 y la de Product Inventory Query (`barcode=`) encuentran el producto con el lector.

## Adopción por la empresa

### 5. Adoptar un producto global en la empresa

**¿Qué puede hacer el usuario?** Incorporar un producto del catálogo a su empresa, con código interno propio, moneda y configuración de inventario.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products`. Permiso `perm:commercial-relationship:company_products:create`. Cuerpo `CompanyProductCreate`: `global_product_id`, `internal_code` (único en la empresa), `display_name`, `currency_code` (obligatorios); `reference_code`, `short_name`, `inventory_control_enabled` (por defecto `true`), `lot_tracking_enabled`, `expiration_tracking_enabled`, `is_purchasable`, `is_sellable` (por defecto `true`).

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "display_name": "Acetaminofén 500 mg tableta",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "is_purchasable": true,
  "is_sellable": true
}
```

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) y un [global_product_id](../parametros/global-product-id.md) `ACTIVE` y elegible (`422 GLOBAL_PRODUCT_NOT_ELIGIBLE` si el catálogo lo marca incompleto).

**¿Cómo sabe que funcionó?** `201` con `CompanyProductResponse`: `id` ([company_product_id](../parametros/company-product-id.md)), `status: "ACTIVE"`, `purchase_tax_percentage: null` (todavía sin impuesto: funcionalidad 8). Efecto verificado: adoptar el producto **no adopta sus presentaciones**; hay que hacerlo con la funcionalidad 7. Errores: `409 DUPLICATE_ADOPTION` (ya adoptado), `409 DUPLICATE_INTERNAL_CODE`, `422 GLOBAL_PRODUCT_NOT_FOUND` / `GLOBAL_PRODUCT_INACTIVE`, `503 DEPENDENCY_UNAVAILABLE`.

### 6. Consultar los productos de la empresa

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` (permiso `perm:commercial-relationship:company_products:read`). Consulta: `search` (código y nombre), `status`, `is_purchasable`, `is_sellable`, `inventory_control_enabled`, `global_product_id`, `page`, `page_size`. Responde `200` con `PaginatedResponse[CompanyProductResponse]`, incluido `purchase_tax_percentage`. Para el catálogo de venta con precio y existencias usa Product Inventory Query ([Inventario §1](inventario.md#1-buscar-productos-con-precio-y-existencias)).

### 7. Adoptar y consultar presentaciones de la empresa

**¿Qué puede hacer el usuario?** Elegir cuáles presentaciones del producto compra y vende la empresa, y cuál es la predeterminada en cada caso.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` (permiso `perm:commercial-relationship:company_product_presentations:create`) con `company_product_id`, `global_product_presentation_id` (obligatorios), `internal_code`, `sku`, `reference_code`, `is_purchasable`, `is_sellable`, `is_default_purchase`, `is_default_sale`. Consulta: `GET` a la misma ruta con `company_product_id=`, `status`, `is_sellable`, `is_purchasable`, `search`, `global_product_presentation_id`.

**¿Qué necesita antes?** El [company_product_id](../parametros/company-product-id.md) de la funcionalidad 5 y el [global_product_presentation_id](../parametros/global-product-presentation-id.md) **del mismo producto global** (`422 GLOBAL_PRESENTATION_OF_OTHER_PRODUCT`).

**¿Cómo sabe que funcionó?** `201` con `CompanyProductPresentationResponse`: `id` ([company_product_presentation_id](../parametros/company-product-presentation-id.md)), `base_quantity_factor`, `is_sellable`, `is_purchasable`, `status: "ACTIVE"`. Este es el identificador que piden las líneas de venta y compra, los precios y las políticas. Errores: `409 DUPLICATE_PRESENTATION_ADOPTION`, `409 DUPLICATE_SKU`, `422 GLOBAL_PRESENTATION_NOT_FOUND` / `_INACTIVE` / `_NOT_ELIGIBLE`, `422 COMPANY_PRODUCT_INACTIVE`.

### 8. Configurar el impuesto de compra del producto

**¿Qué puede hacer el usuario?** Fijar el porcentaje de impuesto que se aplica por defecto a las compras del producto (IVA 19 %, 5 %, 0 %).

**¿Qué API debe consumir el frontend?** `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/purchase-tax` (permiso `perm:commercial-relationship:company_product_purchase_taxes:update`) con `{"version": n, "purchase_tax_percentage": "19"}` (0–100; `0` es válido; `null` lo deja sin configurar). Hasta 100 productos a la vez: `POST …/companies/{company_id}/company-products/purchase-taxes/batch` (CR 12).

**¿Cómo sabe que funcionó?** `200` con el producto y `purchase_tax_percentage` actualizado. Efecto en Compras: cada línea toma este porcentaje salvo que envíe `tax_percentage` propio; si no está configurado y la línea no lo envía, la confirmación falla con `409 PURCHASE_TAX_NOT_CONFIGURED` ([Compras](compras.md)).

## Precios de la empresa

### Cómo funcionan las listas, los precios y las políticas (reglas verificadas en el código)

- **Varias listas por empresa.** Cada lista tiene `currency_code` (inmutable), `valid_from`/`valid_to` opcionales, `status` (`ACTIVE`/`INACTIVE`) e `is_default`. Solo puede haber **una lista predeterminada por moneda**: marcar otra como `is_default: true` quita la marca a la anterior; inactivar una lista también la quita.
- **Una lista está vigente** en un instante `t` cuando está `ACTIVE`, `valid_from` es `null` o ≤ `t`, y `valid_to` es `null` o > `t`. Las fechas se guardan en UTC y `valid_to` debe ser posterior a `valid_from`.
- **Un precio (`price_list_item`)** pertenece a una lista y a una presentación de la empresa, tiene `unit_price`, `valid_from` (si se omite, se toma el instante de creación) y `valid_to` opcional. Dentro de la misma lista y presentación los periodos **no pueden solaparse** (`409 PRICE_PERIOD_OVERLAP`): el precio vigente es el que cubre el instante consultado.
- **Un precio está vigente** cuando su lista está vigente, su `status` es `ACTIVE` y su periodo cubre el instante. El filtro `applicable_at` de la funcionalidad 13 aplica exactamente esta regla.
- **Precios manuales y automáticos.** Un precio creado por la funcionalidad 12 o 14 tiene `origin: "MANUAL"`. Un precio creado por una política tras una recepción de compra tiene `origin: "AUTOMATIC"` y `automatic_application_id`. Ambos conviven en la misma lista; el automático cierra al vigente (`closure_reason`) y cancela los futuros de esa lista y presentación.
- **Una política de ganancia** pertenece a una lista `ACTIVE`, tiene un `markup_percentage` (recargo porcentual sobre el **costo de compra**) y un conjunto de presentaciones; cada presentación puede estar en **una sola política por lista**. El porcentaje vigente se guarda como un término con `valid_from`; cambiarlo abre un término nuevo y **no recalcula** los precios existentes.
- **El precio automático** se calcula al **recibir** una compra (no al confirmarla): `precio = costo_de_referencia × (1 + markup/100)`, redondeado a los decimales de la moneda. El costo de referencia es el costo unitario de la compra; si bajó respecto al anterior, se usa el promedio de ambos. Lo ejecuta un proceso interno de Commercial Relationship (el *worker* de precios), de forma asíncrona: el precio nuevo puede tardar unos segundos en aparecer tras la recepción. El resultado de cada presentación queda en la funcionalidad 20 (`APPLIED`, `UNCHANGED`, `SKIPPED_NO_POLICY`, `SKIPPED_LIST_NOT_EFFECTIVE`, `SKIPPED_CURRENCY_MISMATCH`, `SKIPPED_PRESENTATION_INACTIVE`, `SKIPPED_ZERO_COST`, `PENDING`, `FAILED`, `RESOLVED`).
- **Compras exige cobertura.** Confirmar una compra valida que cada presentación tenga una política en alguna lista vigente de la moneda de la compra, aunque el porcentaje sea `0`; si no, `409 PRICING_POLICY_NOT_CONFIGURED`.
- **Ventas resuelve el precio en Commercial Relationship.** La línea de venta lleva `price_list_id`; Sales obtiene el precio vigente de esa lista para la presentación y lo congela en la línea. El frontend nunca envía el precio ([Ventas](ventas.md)).

### 9. Crear una lista de precios

**¿Qué puede hacer el usuario?** Crear listas distintas para mostrador, mayoristas, convenios o campañas con fecha de inicio y fin.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` (permiso `perm:commercial-relationship:price_lists:create`) con `code` (único), `name`, `currency_code`, `description`, `valid_from`, `valid_to`, `is_default`.

```json
{
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "currency_code": "COP",
  "description": "Lista general de venta al público",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null,
  "is_default": true
}
```

**¿Cómo sabe que funcionó?** `201` con `PriceListResponse` (`id` = [price_list_id](../parametros/price-list-id.md), `status: "ACTIVE"`). Errores: `409 DUPLICATE_PRICE_LIST_CODE`, `422` si `valid_to` no es posterior a `valid_from`.

### 10. Consultar las listas de la empresa

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists?status=ACTIVE&currency_code=COP` (permiso `perm:commercial-relationship:price_lists:read`; también `search`, `is_default`, `page`, `page_size`). Responde `200` con `PaginatedResponse[PriceListResponse]`. El frontend determina la vigencia con `valid_from`/`valid_to` y la hora actual, como se explicó arriba.

### 11. Modificar una lista

`PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/{price_list_id}` (permiso `perm:commercial-relationship:price_lists:update`) con `version`, `code`, `name`, `description`, `valid_from`, `valid_to`, `is_default`. La moneda no cambia. Sirve para cerrar una lista de campaña (`valid_to`) o cambiar la predeterminada. Inactivar: `POST …/price-lists/{price_list_id}/deactivate` (CR 50, `HIGH_RISK`): sus precios dejan de ser aplicables y pierde `is_default`.

### 12. Registrar un precio manual por presentación

**¿Qué puede hacer el usuario?** Fijar a mano el precio de venta de una presentación en una lista, con vigencia opcional.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` (permiso `perm:commercial-relationship:price_list_items:create`) con `price_list_id`, `company_product_id`, `company_product_presentation_id`, `unit_price` (obligatorios), `valid_from`, `valid_to`.

```json
{
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "unit_price": "800.00",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

**¿Qué necesita antes?** Lista `ACTIVE` ([price_list_id](../parametros/price-list-id.md)), presentación `ACTIVE` y vendible de un producto en la misma moneda ([company_product_presentation_id](../parametros/company-product-presentation-id.md)).

**¿Cómo sabe que funcionó?** `201` con `PriceListItemResponse`: `id` (`price_list_item_id`), `unit_price`, `currency_code`, `valid_from`, `valid_to`, `origin: "MANUAL"`, `status: "ACTIVE"`. Errores: `409 PRICE_PERIOD_OVERLAP` (ya hay un precio que cubre ese periodo: usa la funcionalidad 14), `409 PRICE_LIST_INACTIVE`, `422 PRESENTATION_NOT_SELLABLE`, `422` moneda distinta a la de la lista.

### 13. Consultar precios vigentes

**¿Qué puede hacer el usuario?** Ver el precio de una presentación en todas las listas vigentes (lo que necesita el vendedor para elegir lista) o todos los precios de una lista (lo que necesita el administrador).

**¿Qué API debe consumir el frontend?** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` (permiso `perm:commercial-relationship:price_list_items:read`). Consulta: `status`, `price_list_id`, `company_product_id`, `company_product_presentation_id`, `applicable_at` (instante ISO 8601: solo precios vigentes en ese momento, con su lista vigente), `page`, `page_size`.

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-19T15:00:00Z' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Cómo sabe que funcionó?** `200` con `PaginatedResponse[PriceListItemResponse]`; cada elemento trae `price_list_id`, `unit_price`, `currency_code`, `valid_from`, `valid_to`, `origin`. Con el filtro por presentación y `applicable_at`, el resultado es **la lista de opciones de precio** de esa presentación: una por lista vigente. Para mostrar el nombre de cada lista, cruza `price_list_id` con la funcionalidad 10. `POST …/applicable-prices/resolve` (CR 59) resuelve **un** precio por línea (el de la lista indicada o la predeterminada) y es lo que usa Sales internamente; no enumera alternativas.

### 14. Cambiar un precio vigente

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}/change-price` (permiso `perm:commercial-relationship:price_list_items:update`, `HIGH_RISK`) con `{"unit_price": "850.00", "effective_from": null, "version": n}`. Cierra el precio vigente (`valid_to` = `effective_from` o ahora) y crea el nuevo en una sola operación; responde `200` con el nuevo `PriceListItemResponse` (`origin: "MANUAL"`). Si el precio vigente fue cerrado por una actualización automática, responde `409 PRICE_CLOSED_BY_AUTOMATIC_UPDATE`: consulta el precio actual con la funcionalidad 13.

### 15. Corregir un precio futuro o cerrar uno vigente

`PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}` (permiso `perm:commercial-relationship:price_list_items:update`) con `version`, `unit_price`, `valid_from`, `valid_to`. Regla verificada: un precio **futuro** admite cambiar valor y vigencia; un precio **en vigencia** solo admite fijar su `valid_to` (cierre). Responde `200`; `409 VERSION_CONFLICT`, `409 PRICE_PERIOD_OVERLAP`, `422 VALIDATION_ERROR` si se intenta cambiar el valor de un precio vigente.

### 16. Crear una política de porcentaje de ganancia

**¿Qué puede hacer el usuario?** Definir que un grupo de presentaciones de una lista se venda al costo de compra más un porcentaje, y que el precio se actualice solo cuando llegue mercancía nueva.

**¿Qué API debe consumir el frontend?** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` (permiso `perm:commercial-relationship:pricing_policies:create`) con `name`, `markup_percentage`, `company_product_presentation_ids[]`.

```json
{
  "name": "Margen general 30 %",
  "markup_percentage": "30",
  "company_product_presentation_ids": ["a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"]
}
```

**¿Qué necesita antes?** Lista `ACTIVE` y presentaciones `ACTIVE` y vendibles que **no estén ya en otra política de la misma lista**.

**¿Cómo sabe que funcionó?** `201` con `PricingPolicyResponse` (`id` = [policy_id](../parametros/pricing-policy-id.md), `markup_percentage`, `presentation_count`, `status: "ACTIVE"`, `version`). Errores: `409 POLICY_NAME_DUPLICATE`, `409 PRESENTATION_ALREADY_IN_POLICY`, `409 PRICE_LIST_INACTIVE`, `422 PRESENTATION_NOT_SELLABLE`.

### 17. Consultar las políticas de una lista

`GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies?status=ACTIVE` (permiso `perm:commercial-relationship:pricing_policies:read`; también `search`, `page`, `page_size`). Responde `200` con `PaginatedResponse[PricingPolicyResponse]`. Presentaciones de una política: `GET …/pricing-policies/{policy_id}/presentations` (CR 66). Historial de porcentajes: `GET …/pricing-policies/{policy_id}/terms` (CR 65).

### 18. Asociar o retirar presentaciones de una política

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations` y `…/presentations/remove` (permiso `perm:commercial-relationship:pricing_policies:update`) con `{"version": n, "company_product_presentation_ids": ["…"]}` (hasta 100 por llamada). Responden `200` con la política actualizada. Errores: `409 PRESENTATION_ALREADY_IN_POLICY`, `409 PRESENTATION_NOT_IN_POLICY`, `409 POLICY_INACTIVE`.

### 19. Cambiar el porcentaje de una política

`POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/percentage` (permiso `perm:commercial-relationship:pricing_policies:update`, `HIGH_RISK`) con `{"version": n, "markup_percentage": "35"}`. Responde `200` con la política y abre un término nuevo (`valid_from` = ahora). **No recalcula ningún precio**: los precios actuales se conservan y el porcentaje nuevo se usa en la próxima recepción de compra de cada presentación. Si se necesita el precio nuevo de inmediato, hay que registrarlo a mano (funcionalidad 14).

### 20. Verificar cobertura y ver precios automáticos aplicados

- **Antes de confirmar una compra:** `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage` (permiso `perm:commercial-relationship:pricing_policy_coverage:read`) con `{"currency_code": "COP", "company_product_presentation_ids": ["…"]}`. Responde `200` con `items[]` (`company_product_presentation_id`, `found`, `covered`, `price_list_ids[]`). Las presentaciones con `covered: false` harán fallar la confirmación con `PRICING_POLICY_NOT_CONFIGURED`.
- **Después de recibir una compra:** `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/automatic-price-applications?purchase_id=…` (permiso `perm:commercial-relationship:automatic_price_applications:read`; también `status`, `price_list_id`, `company_product_presentation_id`). Cada elemento muestra `status`, `current_unit_cost`, `previous_unit_cost`, `reference_cost`, `markup_percentage`, `previous_price`, `new_price` y `new_price_item_id`. Un `status: PENDING` significa que el *worker* aún no la procesó; `FAILED` que reintentará (`attempts`, `next_attempt_at`); un administrador puede cerrarla con `POST …/automatic-price-applications/{application_id}/resolution` (CR 74).

## Dependencias con otros módulos

- [Compras](compras.md): necesita productos y presentaciones compradas (`is_purchasable`), impuesto de compra (funcionalidad 8) y cobertura de políticas (funcionalidad 20); sus recepciones disparan los precios automáticos.
- [Ventas](ventas.md): necesita presentaciones vendibles con precio vigente en al menos una lista; el vendedor elige la lista entre las opciones de la funcionalidad 13.
- [Inventario](inventario.md): Product Inventory Query muestra los productos de la empresa con el precio de la lista indicada (`price_list_id`) o de la predeterminada, junto con las existencias.
- [Gestión de proveedores](gestion-de-proveedores.md): los productos de proveedor se asocian a los productos empresariales creados aquí.

# 6.5 Productos y precios

[← API principales](README.md) · [← Índice](../index.md)

Operaciones con las que una empresa llega a tener productos que puede comprar y vender con precio. El modelo de SIO tiene tres capas:

| Capa | Servicio | Qué guarda | Identificador | Alcance |
|---|---|---|---|---|
| **Catálogo global** | [Product Catalog](../servicios/product-catalog.md) | Producto canónico (nombre, marca, unidad base, categorías), presentaciones globales y códigos de barras | [global_product_id](../parametros/global-product-id.md), [global_product_presentation_id](../parametros/global-product-presentation-id.md) | Global: compartido por todas las empresas, sin membresía |
| **Adopción por la empresa** | [Commercial Relationship](../servicios/commercial-relationship.md) | El producto y las presentaciones que la empresa maneja, con su código interno, moneda, impuesto de compra y banderas de compra y venta | [company_product_id](../parametros/company-product-id.md), [company_product_presentation_id](../parametros/company-product-presentation-id.md) | Empresa: solo existe dentro de un `company_id` |
| **Precios de la empresa** | [Commercial Relationship](../servicios/commercial-relationship.md) | Listas de precios por moneda con vigencia, precios por presentación y políticas de porcentaje de ganancia | [price_list_id](../parametros/price-list-id.md), `price_list_item_id`, [policy_id](../parametros/pricing-policy-id.md) | Empresa |

Ventas, Compras e Inventario trabajan **siempre** con la capa de empresa (`company_product_id` + `company_product_presentation_id`); nunca con el producto global. Flujo completo: [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Buscar productos globales | `GET https://sio-product-catalog-dev.onrender.com/api/v1/products` | `perm:product-catalog:products:read` | [PC 49](../servicios/product-catalog.md#49-get-products) |
| 2 | Consultar las unidades de medida | `GET https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | [PC 4](../servicios/product-catalog.md#4-get-units-of-measure) |
| 3 | Crear un producto global | `POST https://sio-product-catalog-dev.onrender.com/api/v1/products` | `perm:product-catalog:products:create` | [PC 50](../servicios/product-catalog.md#50-post-products) |
| 4 | Asignar una categoría al producto global | `POST https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories` | `perm:product-catalog:products:update` | [PC 60](../servicios/product-catalog.md#60-post-productsproduct_idcategories) |
| 5 | Consultar las presentaciones globales de un producto | `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` | `perm:product-catalog:products:read` | [PC 67](../servicios/product-catalog.md#67-get-productsproduct_idpresentations) |
| 6 | Crear una presentación global | `POST https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` | `perm:product-catalog:products:update` | [PC 68](../servicios/product-catalog.md#68-post-productsproduct_idpresentations) |
| 7 | Registrar un código de barras del producto global | `POST https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers` | `perm:product-catalog:products:update` | [PC 74](../servicios/product-catalog.md#74-post-productsproduct_ididentifiers) |
| 8 | Adoptar un producto global en la empresa | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` | `perm:commercial-relationship:company_products:create` | [CR 4](../servicios/commercial-relationship.md#4-post-companiescompany_idcompany-products) |
| 9 | Buscar y listar los productos de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` | `perm:commercial-relationship:company_products:read` | [CR 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products) |
| 10 | Consultar un producto de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}` | `perm:commercial-relationship:company_products:read` | [CR 7](../servicios/commercial-relationship.md#7-get-company-productscompany_product_id) |
| 11 | Adoptar una presentación en la empresa | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:create` | [CR 27](../servicios/commercial-relationship.md#27-post-companiescompany_idcompany-product-presentations) |
| 12 | Consultar las presentaciones de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:read` | [CR 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations) |
| 13 | Configurar el impuesto de compra del producto | `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/purchase-tax` | `perm:commercial-relationship:company_product_purchase_taxes:update` | [CR 11](../servicios/commercial-relationship.md#11-put-company-productscompany_product_idpurchase-tax) |
| 14 | Crear una lista de precios | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` | `perm:commercial-relationship:price_lists:create` | [CR 47](../servicios/commercial-relationship.md#47-post-companiescompany_idprice-lists) |
| 15 | Consultar las listas de precios de la empresa | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` | `perm:commercial-relationship:price_lists:read` | [CR 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists) |
| 16 | Modificar una lista de precios | `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/{price_list_id}` | `perm:commercial-relationship:price_lists:update` | [CR 49](../servicios/commercial-relationship.md#49-put-price-listsprice_list_id) |
| 17 | Registrar un precio de venta | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` | `perm:commercial-relationship:price_list_items:create` | [CR 53](../servicios/commercial-relationship.md#53-post-companiescompany_idprice-list-items) |
| 18 | Consultar los precios vigentes | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` | `perm:commercial-relationship:price_list_items:read` | [CR 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items) |
| 19 | Cambiar un precio vigente | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}/change-price` | `perm:commercial-relationship:price_list_items:update` | [CR 56](../servicios/commercial-relationship.md#56-post-price-list-itemsprice_list_item_idchange-price) |
| 20 | Corregir un precio futuro o cerrar uno vigente | `PUT https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}` | `perm:commercial-relationship:price_list_items:update` | [CR 55](../servicios/commercial-relationship.md#55-put-price-list-itemsprice_list_item_id) |
| 21 | Crear una política de ganancia | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` | `perm:commercial-relationship:pricing_policies:create` | [CR 62](../servicios/commercial-relationship.md#62-post-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 22 | Consultar las políticas de una lista | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` | `perm:commercial-relationship:pricing_policies:read` | [CR 61](../servicios/commercial-relationship.md#61-get-companiescompany_idprice-listsprice_list_idpricing-policies) |
| 23 | Asignar presentaciones a una política | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations` | `perm:commercial-relationship:pricing_policies:update` | [CR 67](../servicios/commercial-relationship.md#67-post-pricing-policiespolicy_idpresentations) |
| 24 | Retirar presentaciones de una política | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations/remove` | `perm:commercial-relationship:pricing_policies:update` | [CR 69](../servicios/commercial-relationship.md#69-post-pricing-policiespolicy_idpresentationsremove) |
| 25 | Cambiar el porcentaje de una política | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/percentage` | `perm:commercial-relationship:pricing_policies:update` | [CR 68](../servicios/commercial-relationship.md#68-post-pricing-policiespolicy_idpercentage) |
| 26 | Verificar la cobertura de políticas | `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage` | `perm:commercial-relationship:pricing_policy_coverage:read` | [CR 60](../servicios/commercial-relationship.md#60-post-companiescompany_idpricing-policiescoverage) |
| 27 | Consultar las actualizaciones automáticas de precio | `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/automatic-price-applications` | `perm:commercial-relationship:automatic_price_applications:read` | [CR 72](../servicios/commercial-relationship.md#72-get-companiescompany_idautomatic-price-applications) |

Operaciones relacionadas que no se consideran principales (ver las fichas): modificar, inactivar o reactivar productos, presentaciones e identificadores globales (PC 54, 57, 58, 70–72, 75–77); consultar marcas, categorías y tipos de empaque (PC 16, 30, 10, citados donde se usan); atributos, grupos y archivos del producto (PC 63–65, 78–102; spec 024: las imágenes pasan a las rutas por presentación); la búsqueda progresiva y las consultas por lotes de productos y presentaciones de la empresa (CR 5, 6, 28, 29); modificar, inactivar o reactivar productos y presentaciones de la empresa (CR 8–10, 31–33); el impuesto de compra por lotes (CR 12); consultar, inactivar o reactivar una lista o un precio (CR 48, 50, 51, 54, 57, 58); la resolución del precio que usa Sales internamente (CR 59); consultar, renombrar e inactivar una política y su historial (CR 63–66, 70); el detalle y la resolución administrativa de una actualización automática (CR 73, 74). La solicitud de actualización automática (CR 71) es exclusiva de la cuenta técnica de Purchase.

Orden habitual para dejar un producto listo para vender: [API 1](#1-buscar-productos-globales) (¿ya existe en el catálogo?) → si no existe, [API 2](#2-consultar-las-unidades-de-medida), [API 3](#3-crear-un-producto-global), [API 4](#4-asignar-una-categoría-al-producto-global), [API 6](#6-crear-una-presentación-global) y [API 7](#7-registrar-un-código-de-barras-del-producto-global) → [API 8](#8-adoptar-un-producto-global-en-la-empresa) (adoptar el producto) → [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) y [API 11](#11-adoptar-una-presentación-en-la-empresa) (adoptar sus presentaciones) → [API 13](#13-configurar-el-impuesto-de-compra-del-producto) (impuesto de compra) → [API 14](#14-crear-una-lista-de-precios) (lista) → [API 17](#17-registrar-un-precio-de-venta) (precio manual) y [API 21](#21-crear-una-política-de-ganancia) (política de ganancia, exigida por Compras).

Convenciones de todo el módulo:

- `TU_ACCESS_TOKEN` es el Access Token de [Acceso y contexto operativo](acceso-y-contexto-operativo.md); los UUID son ficticios.
- Todas las API de escritura con cuerpo JSON de Product Catalog y de Commercial Relationship **rechazan campos desconocidos** con `422 …VALIDATION_ERROR` (modelos estrictos).
- Errores comunes a todas las API de este módulo (no se repiten en cada tabla): `401` con `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` cuando el token falta, venció o no es válido (renovar una vez y reintentar; si falla, volver al login); `403` con `code` `PRODUCT_CATALOG.FORBIDDEN` o `COMMERCIAL_RELATIONSHIP.FORBIDDEN` cuando el token no tiene el permiso indicado (mostrar que faltan permisos y el `trace_id`); `503` con `code` `…DEPENDENCY_UNAVAILABLE` cuando la base de datos u otro servicio no responde (`dependency` indica cuál; reintentar más tarde; nada se guarda). Los demás errores llegan en Problem Details (`application/problem+json`) con `code` `PRODUCT_CATALOG.…` o `COMMERCIAL_RELATIONSHIP.…` y `trace_id`; ver la [guía de errores](../guias/errores.md).
- **Parámetros mal formados.** Product Catalog responde `400 PRODUCT_CATALOG.MALFORMED_REQUEST` (con `errors[]`) cuando un parámetro de ruta o de consulta no se puede interpretar (UUID inválido, enumeración, rango) o el cuerpo no es JSON; los errores del cuerpo son `422 PRODUCT_CATALOG.VALIDATION_ERROR`. Commercial Relationship responde `422 COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` para ruta, consulta y cuerpo, y `400 MALFORMED_REQUEST` solo si el cuerpo no es JSON.
- **Alcance.** El catálogo de Product Catalog es global: cualquier usuario con el permiso lo ve y no exige membresía. Los recursos de Commercial Relationship solo se ven y modifican con membresía `ACTIVE` en la empresa, que el servicio verifica en Operational Context; fuera de ese alcance la respuesta es `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND`, igual que si no existieran. Si Operational Context rechaza la consulta de membresía la respuesta es `403 COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` (pedir `perm:operational-context:application_users:read`) y si no responde, `503 COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE`; estos dos casos aplican a todas las API de Commercial Relationship y no se repiten.
- **Empresa inactiva.** Si la empresa está `INACTIVE`, Commercial Relationship solo permite consultar e inactivar; crear, modificar o reactivar responde `422 COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE`.
- **Producto global inactivo.** Sobre un producto global `INACTIVE` solo se consultan o inactivan sus elementos: crear categorías, presentaciones o identificadores responde `422 PRODUCT_CATALOG.PRODUCT_INACTIVE`.
- **Control de versión.** Toda modificación envía la `version` actual del recurso; si otra persona lo cambió antes, la API responde `409 …VERSION_CONFLICT` y el frontend debe volver a leer el recurso y repetir con la nueva `version`.
- **Importes y porcentajes.** Commercial Relationship devuelve los importes como texto decimal con los decimales de la moneda (`"8500.00"` en COP, `"8500"` en CLP) y los porcentajes con 4 decimales (`"19.0000"`). Las monedas admitidas son una lista cerrada ISO 4217 (por ejemplo `COP`, `USD`, `EUR`, `MXN`, `PEN`, `CLP`); otra responde `422 CURRENCY_NOT_SUPPORTED`. Las fechas con hora deben llevar zona horaria (`2026-10-19T15:04:05Z`); sin zona responden `422 VALIDATION_ERROR`.
- Las respuestas traen siempre `created_by`, `updated_by` (el `sub` de Keycloak de quien actuó), `created_at` y `updated_at`.
- Toda escritura queda registrada en [Audit](../servicios/audit.md). Acciones de Product Catalog: `CREATE_PRODUCT`, `ADD_PRODUCT_CATEGORY`, `CREATE_PRODUCT_PRESENTATION`, `CREATE_PRODUCT_IDENTIFIER`. Acciones de Commercial Relationship: `ADOPT_COMPANY_PRODUCT`, `CREATE_COMPANY_PRODUCT_PRESENTATION`, `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX` (entidad `CompanyProduct`), `CREATE_PRICE_LIST`, `UPDATE_PRICE_LIST`, `CREATE_PRICE_LIST_ITEM`, `UPDATE_PRICE_LIST_ITEM`, `CHANGE_PRICE_LIST_ITEM_PRICE`, `CREATE_PRICING_POLICY`, `CHANGE_PRICING_POLICY_PERCENTAGE`, `ASSIGN_PRICING_POLICY_PRESENTATION`, `UNASSIGN_PRICING_POLICY_PRESENTATION` y, en las operaciones no principales, `DEACTIVATE_PRICING_POLICY`. Los eventos de la empresa se consultan con la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) (lista los eventos de auditoría de la empresa; sus errores están en esa sección).

Reglas de precios verificadas en el código:

- **Varias listas por empresa.** Cada lista tiene una moneda (inmutable), vigencia opcional `[valid_from, valid_to)` y `is_default`. Hay **una sola lista predeterminada por empresa y moneda**: marcar otra quita la marca a la anterior; inactivar una lista también la quita.
- **Un precio** pertenece a una lista, un producto y una presentación de la empresa, con `unit_price` y vigencia `[valid_from, valid_to)`. En la misma lista, producto y presentación los periodos de precios `ACTIVE` **no pueden cruzarse** (`409 PRICE_PERIOD_OVERLAP`). Un precio cuyo `valid_from` ya llegó está **en vigencia**: no se reescribe su valor; se cambia con la [API 19](#19-cambiar-un-precio-vigente) o se cierra con la [API 20](#20-corregir-un-precio-futuro-o-cerrar-uno-vigente).
- **Precios manuales y automáticos.** Un precio registrado a mano tiene `origin: null`; uno creado por una política tras una recepción de compra tiene `origin: "AUTOMATIC"` y `automatic_application_id`. El automático cierra el precio vigente (`closure_reason`) y cancela los futuros de esa lista y presentación; un precio cerrado o cancelado así no vuelve a regir (`409 PRICE_CLOSED_BY_AUTOMATIC_UPDATE` al modificarlo o reactivarlo).
- **Políticas de ganancia.** Una política pertenece a una lista `ACTIVE`, tiene un `markup_percentage` (0 a 1000 %, `0` es válido) y un conjunto de presentaciones vendibles; en cada instante una presentación pertenece **a lo sumo a una política de la misma lista** (`409 PRESENTATION_ALREADY_IN_POLICY`). Ninguna operación de políticas modifica precios: los cambios rigen desde la siguiente recepción de compra. El precio automático lo calcula un proceso asíncrono de Commercial Relationship al **recibir** la compra; su resultado se consulta en la [API 27](#27-consultar-las-actualizaciones-automáticas-de-precio).
- **Compras exige impuesto y política.** Al confirmar una compra, Purchase exige que cada línea tenga tasa de impuesto (la del producto, [API 13](#13-configurar-el-impuesto-de-compra-del-producto), o la propia de la línea; si no, `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED`) y que cada presentación tenga política en una lista activa y vigente de la moneda de la compra, aunque el porcentaje sea `0` (si no, `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED`); ver [Compras](compras.md).
- **Ventas usa la lista que elige el vendedor.** La interfaz muestra los precios vigentes de la presentación ([API 18](#18-consultar-los-precios-vigentes)) ordenados **de mayor a menor**, el vendedor elige uno y la línea de venta envía su `price_list_id` **explícito**; Sales resuelve y congela el precio en Commercial Relationship. El frontend nunca envía `unit_price` en la venta ([Ventas](ventas.md)).

---

## 1. Buscar productos globales

**Método:** `GET`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products`
**Permiso requerido:** `perm:product-catalog:products:read`

### ¿Qué hace esta API?

Busca productos en el catálogo global compartido por nombre, código de barras, marca, categoría, fabricante, grupo o atributos, con paginación. Es el primer paso antes de crear o adoptar un producto: si el producto ya existe (otra empresa lo creó) se reutiliza su `id` y **no** se crea de nuevo. Ordena por nombre normalizado.

Efectos verificados en el código: `search` busca coincidencias parciales en el nombre canónico normalizado (sin distinguir mayúsculas ni tildes); `identifier` busca el código exacto tras quitar espacios y guiones, en GTIN, EAN y UPC por su forma canónica y en `BARCODE`, `IUM` y `OTHER` por valor; sin `status` devuelve productos de cualquier estado. Cada producto trae el bloque `completeness` y `eligible_for_adoption`: solo un producto `ACTIVE` y completo puede adoptarse en la [API 8](#8-adoptar-un-producto-global-en-la-empresa).

Antes necesita: solo el token; el catálogo no exige membresía.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products?search=acetaminofen&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 200) | No | Búsqueda parcial en el nombre canónico, sin distinguir mayúsculas ni tildes | Texto libre: parte del nombre; p. ej. `acetaminofen` o `500 mg` | `&search=acetaminofen` | Interfaz (nombre que escribe el usuario) |
| `identifier` | string (≤ 120) | No | Código de barras u otro identificador exacto; se ignoran espacios y guiones | Texto: GTIN, EAN, UPC, código interno de barras o IUM; p. ej. `7702001023456` | `&identifier=7702001023456` | Lector de códigos o Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; sin valor devuelve todos | Estado del producto | Uno de: `ACTIVE`, `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `brand_id` | UUID | No | Solo productos de esa marca | UUID de una marca; p. ej. `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `&brand_id=b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/brands` (lista las marcas del catálogo; permiso `perm:product-catalog:brands:read`; errores `400 MALFORMED_REQUEST` por filtros inválidos; ficha [PC 16](../servicios/product-catalog.md#16-get-brands)) |
| `category_id` | UUID | No | Solo productos con esa categoría vigente | UUID de una categoría; p. ej. `0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3` | `&category_id=0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/categories` (lista las categorías; permiso `perm:product-catalog:categories:read`; errores `400 MALFORMED_REQUEST` por filtros inválidos; ficha [PC 30](../servicios/product-catalog.md#30-get-categories)) |
| `include_descendants` | boolean | No; por defecto `false` | Con `category_id`, incluye también las subcategorías | `true` o `false`; p. ej. `true` | `&include_descendants=true` | Interfaz |
| `manufacturer_organization_id` | UUID | No | Solo productos de ese fabricante | UUID de una organización; p. ej. `0f1e2d3c-4b5a-4968-8776-655443322111` | `&manufacturer_organization_id=0f1e2d3c-4b5a-4968-8776-655443322111` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; sus errores están en esa sección) |
| `group_id` | UUID | No | Solo productos asignados a ese grupo | UUID de un grupo de productos; p. ej. `2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e` | `&group_id=2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{group_type_id}/groups` (lista los grupos de un tipo; permiso `perm:product-catalog:group-types:read`; errores `404 NOT_FOUND` si el tipo no existe; ficha [PC 82](../servicios/product-catalog.md#82-get-group-typesgroup_type_idgroups)) |
| `attribute_filters` | string, repetible | No | Filtro `CODIGO:valor` sobre atributos filtrables; se repite el parámetro por cada atributo | Texto `CODIGO:valor`; p. ej. `CONCENTRACION:500` | `&attribute_filters=CONCENTRACION:500` | Interfaz; códigos en `GET https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions` (ficha [PC 41](../servicios/product-catalog.md#41-get-attribute-definitions)) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-catalog-dev.onrender.com/api/v1/products?search=acetaminofen&status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[ProductResponse]`):

```json
{
  "items": [
    {
      "id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "version": 3,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "product_type": "GOOD",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "description": null,
      "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "manufacturer_organization_id": null,
      "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "first_used_at": "2026-10-19T15:04:05Z",
      "first_use_source": "ADOPTION",
      "completeness": {
        "is_complete": true,
        "issues": [],
        "missing_attribute_definition_ids": [],
        "out_of_classification_value_ids": []
      },
      "eligible_for_adoption": true,
      "warnings": [],
      "detail": null
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
| `items[].id` | UUID | El [global_product_id](../parametros/global-product-id.md) que se envía en la [API 8](#8-adoptar-un-producto-global-en-la-empresa) y que es el `product_id` de las API 4 a 7 |
| `items[].canonical_name` | string | Nombre canónico para mostrar |
| `items[].global_brand_id`, `base_unit_id`, `manufacturer_organization_id` | UUID \| null | Marca, unidad base y fabricante; la unidad base se describe con la [API 2](#2-consultar-las-unidades-de-medida) |
| `items[].completeness.issues[]` | string[] | Lo que le falta para estar completo: `MISSING_MINIMUM_DATA`, `BASE_UNIT_NOT_FOUND`, `NO_ACTIVE_CATEGORY`, `NO_PRIMARY_CATEGORY`, `MISSING_REQUIRED_ATTRIBUTE`, `INCONSISTENT_REQUIRED_VALUE`, `NO_ACTIVE_PRESENTATION` |
| `items[].eligible_for_adoption` | boolean | `true` solo si el producto está `ACTIVE` y completo; solo esos se adoptan |
| `items[].first_used_at`, `first_use_source` | fecha, string \| null | Primer uso del producto por una empresa; desde entonces la unidad base queda bloqueada |
| `items[].detail` | null | Siempre `null` en la lista; el detalle completo se pide en la consulta individual con `expand=detail` (PC 53) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `search` > 200, `identifier` > 120, `status` fuera de la enumeración, UUID o booleano inválido, paginación fuera de rango | Corregir los filtros; `errors[]` trae `field` |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | `attribute_filters` sin el formato `CODIGO:valor` o con un atributo no filtrable | Corregir el filtro de atributos |

## 2. Consultar las unidades de medida

**Método:** `GET`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure`
**Permiso requerido:** `perm:product-catalog:units-of-measure:read`

### ¿Qué hace esta API?

Lista las unidades de medida del catálogo global (unidad, tableta, gramo, mililitro…). Se usa para elegir la `base_unit_id` al crear un producto ([API 3](#3-crear-un-producto-global)) y la `content_unit_id` de una presentación ([API 6](#6-crear-una-presentación-global)), y para mostrar el nombre de la unidad base de un producto. Solo se pueden asignar unidades `ACTIVE`.

Antes necesita: solo el token.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure?status=ACTIVE&measurement_type=UNIT&page=1&page_size=50' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `50` | `&page_size=50` | Interfaz |
| `status` | `ACTIVE` \| `INACTIVE` | No; sin valor devuelve todas | Estado de la unidad | Uno de: `ACTIVE`, `INACTIVE`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `code` | string (≤ 100) | No | Código exacto; se compara en mayúsculas | Texto; p. ej. `UND` | `&code=UND` | Interfaz |
| `search` | string (≤ 200) | No | Búsqueda parcial en el nombre | Texto libre; p. ej. `tableta` | `&search=tableta` | Interfaz |
| `measurement_type` | `UNIT` \| `MASS` \| `VOLUME` \| `LENGTH` \| `AREA` | No | Magnitud de la unidad | Uno de: `UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA`; p. ej. `UNIT` | `&measurement_type=UNIT` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure?status=ACTIVE&measurement_type=UNIT&page=1&page_size=50`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[UnitOfMeasureResponse]`):

```json
{
  "items": [
    {
      "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "TAB",
      "name": "Tableta",
      "symbol": "tab",
      "measurement_type": "UNIT",
      "allows_decimals": false
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
| `items[].id` | UUID | Valor de `base_unit_id` en la [API 3](#3-crear-un-producto-global) o de `content_unit_id` en la [API 6](#6-crear-una-presentación-global) |
| `items[].code`, `name`, `symbol` | string | Textos para mostrar en el selector |
| `items[].measurement_type` | enum | Magnitud (`UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA`) |
| `items[].allows_decimals` | boolean | Si las cantidades en esta unidad admiten decimales |
| `items[].status` | `ACTIVE` \| `INACTIVE` | Solo las `ACTIVE` se pueden asignar |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `code` > 100, `search` > 200, `status` o `measurement_type` fuera de la enumeración, paginación fuera de rango | Corregir los filtros |

## 3. Crear un producto global

**Método:** `POST`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products`
**Permiso requerido:** `perm:product-catalog:products:create`

### ¿Qué hace esta API?

Da de alta en el catálogo global un producto que la [API 1](#1-buscar-productos-globales) no encontró. El producto queda disponible para todas las empresas. Es una operación de catálogo compartido que normalmente hacen administradores o supervisores, no el flujo de venta.

Efectos verificados en el código: normaliza el nombre (recorta y une espacios; máximo efectivo 200 caracteres aunque el esquema admita 400); valida que la marca y la unidad base existan y estén `ACTIVE`; si se envía fabricante, lo valida en Party Identity con el token del usuario; crea el producto `ACTIVE` con `version` `1`, devuelve `Location: /api/v1/products/{id}` y registra `CREATE_PRODUCT` en Audit. Si existe otro producto con el mismo nombre normalizado y la misma marca **no** falla: lo crea y devuelve una advertencia `POSSIBLE_DUPLICATE` en `warnings[]`. El producto recién creado **no es adoptable**: le faltan categoría y presentación (`eligible_for_adoption: false`) hasta completar la [API 4](#4-asignar-una-categoría-al-producto-global) y la [API 6](#6-crear-una-presentación-global), y los atributos obligatorios de su categoría si los hay.

Antes necesita: la unidad base ([API 2](#2-consultar-las-unidades-de-medida)) y, si se quiere, la marca (`GET https://sio-product-catalog-dev.onrender.com/api/v1/brands`, ficha [PC 16](../servicios/product-catalog.md#16-get-brands)). Buscar antes con la [API 1](#1-buscar-productos-globales) por nombre y por `identifier` para no duplicar.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "product_type": "GOOD",
    "canonical_name": "Acetaminofén 500 mg tableta",
    "description": null,
    "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "manufacturer_organization_id": null,
    "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "product_type": "GOOD",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "description": null,
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": null,
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `product_type` | `GOOD` | Sí | Tipo de producto; el único valor admitido es `GOOD` (bien físico) | `GOOD` | Fijo |
| `canonical_name` | string (1–200 efectivos) | Sí | Nombre canónico; se recortan y unen espacios | `Acetaminofén 500 mg tableta` | Formulario |
| `description` | string \| null | No | Descripción libre | `null` | Formulario |
| `global_brand_id` | UUID \| null | No | Marca `ACTIVE` del catálogo | `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/brands?status=ACTIVE` (lista las marcas; permiso `perm:product-catalog:brands:read`; errores `400 MALFORMED_REQUEST` por filtros inválidos; ficha [PC 16](../servicios/product-catalog.md#16-get-brands)) |
| `manufacturer_organization_id` | UUID \| null | No | Organización fabricante registrada en Party Identity | `null` | `items[].id` de la [API 3 de Gestión de clientes](gestion-de-clientes.md#3-buscar-la-identidad-de-una-organización) (busca organizaciones por NIT o nombre; sus errores están en esa sección) |
| `base_unit_id` | UUID | Sí | Unidad base `ACTIVE` en la que se cuentan las existencias | `d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` | `items[].id` de la [API 2](#2-consultar-las-unidades-de-medida) (lista las unidades de medida; errores en §2) |

### Respuesta exitosa

`201 Created` (`ProductResponse`), con cabecera `Location: /api/v1/products/{id}`:

```json
{
  "id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "product_type": "GOOD",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "description": null,
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": null,
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": null,
  "first_use_source": null,
  "completeness": {
    "is_complete": false,
    "issues": ["NO_ACTIVE_CATEGORY", "NO_ACTIVE_PRESENTATION"],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": false,
  "warnings": [],
  "detail": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [global_product_id](../parametros/global-product-id.md): es el `product_id` de las API 4 a 7 |
| `completeness.issues[]` | string[] | Pasos pendientes antes de poder adoptarlo (categoría, presentación, atributos obligatorios) |
| `eligible_for_adoption` | boolean | `false` al crear; pasa a `true` cuando el producto queda completo |
| `warnings[]` | objeto[] | `code` `POSSIBLE_DUPLICATE`, `message` y `matching_product_ids[]` si hay otro producto con el mismo nombre y marca; mostrar al usuario para que decida si inactiva el duplicado |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `422` | `PRODUCT_CATALOG.REFERENCE_NOT_FOUND` | La marca o la unidad base no existen | Volver a cargar el selector |
| `422` | `PRODUCT_CATALOG.REFERENCE_INACTIVE` | La marca o la unidad base están `INACTIVE` | Elegir otra |
| `422` | `PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND` | El fabricante no existe en Party Identity | Volver a buscar la organización |
| `403` | `PRODUCT_CATALOG.MANUFACTURER_ACCESS_DENIED` | El usuario no tiene permiso para consultar organizaciones en Party Identity | Pedir `perm:party-identity:organization_identities:read` o no enviar fabricante |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | `product_type` distinto de `GOOD`, nombre vacío o > 200, UUID inválido, campo obligatorio ausente o desconocido | Corregir el formulario; `errors[]` trae `field` |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | El cuerpo no es JSON válido | Error de programación del cliente |
| `503` | `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | Party Identity no responde al validar el fabricante | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por unidad inexistente:

```json
{
  "type": "https://sio/errors/product-catalog/reference-not-found",
  "title": "Referencia inexistente",
  "status": 422,
  "detail": "La unidad base d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e no existe.",
  "instance": "/api/v1/products",
  "code": "PRODUCT_CATALOG.REFERENCE_NOT_FOUND",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 4. Asignar una categoría al producto global

**Método:** `POST`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories`
**Permiso requerido:** `perm:product-catalog:products:update`

### ¿Qué hace esta API?

Clasifica el producto global en una categoría del catálogo. Sin al menos una categoría vigente y principal el producto no está completo y no se puede adoptar (`NO_ACTIVE_CATEGORY`, `NO_PRIMARY_CATEGORY`).

Efectos verificados en el código: la primera categoría asignada queda como principal (`is_primary: true`); si la pareja producto + categoría existía inactiva la reactiva y responde `200` en lugar de `201`; registra `ADD_PRODUCT_CATEGORY` en Audit. La categoría debe existir y estar `ACTIVE`; el producto debe estar `ACTIVE`.

Antes necesita: el `product_id` ([API 1](#1-buscar-productos-globales) o [API 3](#3-crear-un-producto-global)) y el `global_category_id` de la lista de categorías (PC 30).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/categories' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `product_id` | UUID | Sí | Producto global a clasificar | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales; errores en §1) o `id` de la [API 3](#3-crear-un-producto-global) (crea el producto; errores en §3) · guía [global_product_id](../parametros/global-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `global_category_id` | UUID | Sí | Categoría `ACTIVE` del catálogo | `0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/categories?status=ACTIVE` (lista las categorías; filtros `code`, `search`, `parent_category_id`, `root_only`; permiso `perm:product-catalog:categories:read`; errores `400 MALFORMED_REQUEST` por filtros inválidos; ficha [PC 30](../servicios/product-catalog.md#30-get-categories)) |

### Respuesta exitosa

`201 Created` (`ProductCategoryResponse`); `200 OK` con el mismo objeto si se reactivó una asignación anterior:

```json
{
  "id": "37c09a60-cfa3-4c4e-8c17-f073b9e7e0d1",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
  "is_primary": true
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | Identificador de la asignación (`association_id`), usado para cambiar la principal o retirarla (PC 61, 62) |
| `is_primary` | boolean | `true` si es la primera categoría del producto |
| `status` | `ACTIVE` | La asignación queda vigente |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto no existe | Volver a buscarlo con la [API 1](#1-buscar-productos-globales) |
| `409` | `PRODUCT_CATALOG.DUPLICATE_ASSOCIATION` | La categoría ya está asignada y vigente | Nada que hacer; refrescar las categorías del producto |
| `422` | `PRODUCT_CATALOG.REFERENCE_NOT_FOUND` | La categoría no existe | Volver a cargar el selector |
| `422` | `PRODUCT_CATALOG.REFERENCE_INACTIVE` | La categoría está `INACTIVE` | Elegir otra |
| `422` | `PRODUCT_CATALOG.PRODUCT_INACTIVE` | El producto está `INACTIVE` | Informar; reactivarlo es una operación no principal (PC 58) |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | `global_category_id` ausente, inválido o campo desconocido | Corregir la solicitud |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o el cuerpo no es JSON | Error de programación del cliente |

## 5. Consultar las presentaciones globales de un producto

**Método:** `GET`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations`
**Permiso requerido:** `perm:product-catalog:products:read`

### ¿Qué hace esta API?

Devuelve, **sin paginación**, las presentaciones definidas en el catálogo global para un producto (unidad, blíster, caja × 100…), ordenadas por `display_order` y código. Se usa para elegir qué presentación adopta la empresa en la [API 11](#11-adoptar-una-presentación-en-la-empresa) y para mostrar el nombre y la cantidad de una presentación de la empresa, que no viajan en Commercial Relationship.

Antes necesita: el `product_id` (el `global_product_id` del producto).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations?status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `product_id` | UUID | Sí | Producto global | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales; errores en §1) o `global_product_id` de la [API 10](#10-consultar-un-producto-de-la-empresa) (devuelve el producto de la empresa; errores en §10) · guía [global_product_id](../parametros/global-product-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | No; sin valor devuelve todas | Estado de la presentación | Uno de: `ACTIVE`, `INACTIVE`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations?status=ACTIVE`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (arreglo de `PresentationResponse`, sin paginación):

```json
[
  {
    "id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "code": "CJ100",
    "name": "Caja x 100 tabletas",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false,
    "first_used_at": null,
    "first_use_source": null,
    "eligible_for_adoption": true
  }
]
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `[].id` | UUID | El [global_product_presentation_id](../parametros/global-product-presentation-id.md) que se envía en la [API 11](#11-adoptar-una-presentación-en-la-empresa) |
| `[].code`, `name` | string | Código (en mayúsculas) y nombre para mostrar |
| `[].base_quantity` | decimal (texto) | Cuántas unidades base contiene la presentación |
| `[].is_base` | boolean | Marca la presentación base (una vigente por producto, con `base_quantity` 1) |
| `[].eligible_for_adoption` | boolean | `true` si la presentación está `ACTIVE` y el producto es adoptable |
| `[].first_used_at` | fecha \| null | Desde su primer uso la cantidad base queda bloqueada |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto no existe | Volver a buscarlo con la [API 1](#1-buscar-productos-globales) |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o `status` fuera de la enumeración | Corregir la solicitud |

## 6. Crear una presentación global

**Método:** `POST`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations`
**Permiso requerido:** `perm:product-catalog:products:update`

### ¿Qué hace esta API?

Define en el catálogo global una forma de presentar el producto (unidad, blíster × 10, caja × 100) y cuántas unidades base contiene. Sin al menos una presentación vigente el producto no es adoptable (`NO_ACTIVE_PRESENTATION`).

Efectos verificados en el código, en este orden: el producto debe existir y estar `ACTIVE`; el `code` se normaliza a mayúsculas (máximo efectivo 60) y debe ser único en el producto; `base_quantity` > 0 (hasta 10 enteros y 8 decimales); `content_quantity` y `content_unit_id` van juntos; el tipo de empaque y la unidad de contenido deben existir y estar `ACTIVE`; una presentación base exige `base_quantity` 1 y solo puede haber una base vigente; el nombre se normaliza (máximo efectivo 160). Crea la presentación `ACTIVE`, devuelve `Location: /api/v1/presentations/{id}` y registra `CREATE_PRODUCT_PRESENTATION` en Audit.

Antes necesita: el `product_id` y, si se usan, el tipo de empaque (`GET https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types`, ficha [PC 10](../servicios/product-catalog.md#10-get-packaging-types)) y la unidad de contenido ([API 2](#2-consultar-las-unidades-de-medida)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CJ100",
    "name": "Caja x 100 tabletas",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `product_id` | UUID | Sí | Producto global al que pertenece la presentación | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales; errores en §1) o `id` de la [API 3](#3-crear-un-producto-global) (crea el producto; errores en §3) · guía [global_product_id](../parametros/global-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "code": "CJ100",
  "name": "Caja x 100 tabletas",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `code` | string (1–60 efectivos) | Sí | Código de la presentación; se convierte a mayúsculas; único en el producto | `CJ100` | Formulario |
| `name` | string (1–160 efectivos) | Sí | Nombre para mostrar | `Caja x 100 tabletas` | Formulario |
| `packaging_type_id` | UUID \| null | No | Tipo de empaque `ACTIVE` | `e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b` | `items[].id` de `GET https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types?status=ACTIVE` (lista los tipos de empaque; permiso `perm:product-catalog:packaging-types:read`; errores `400 MALFORMED_REQUEST` por filtros inválidos; ficha [PC 10](../servicios/product-catalog.md#10-get-packaging-types)) |
| `base_quantity` | decimal > 0 | No; por defecto `1` | Unidades base que contiene; `1` obligatorio si `is_base` es `true` | `100` | Formulario |
| `content_quantity` | decimal > 0 \| null | No; obligatorio junto con `content_unit_id` | Contenido neto informativo (por ejemplo 120 ml) | `null` | Formulario |
| `content_unit_id` | UUID \| null | No; obligatorio junto con `content_quantity` | Unidad `ACTIVE` del contenido | `null` | `items[].id` de la [API 2](#2-consultar-las-unidades-de-medida) (lista las unidades de medida; errores en §2) |
| `display_order` | integer 0–32767 | No; por defecto `0` | Orden de aparición | `1` | Interfaz |
| `is_base` | boolean | No; por defecto `false` | Si es la presentación base del producto | `false` | Formulario |

### Respuesta exitosa

`201 Created` (`PresentationResponse`), con cabecera `Location: /api/v1/presentations/{id}`. Mismo objeto que un elemento de la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto):

```json
{
  "id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100 tabletas",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": null,
  "first_use_source": null,
  "eligible_for_adoption": false
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| `code` | string | El código ya normalizado a mayúsculas |
| `eligible_for_adoption` | boolean | `true` solo si el producto ya está completo; si faltaba la categoría sigue en `false` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto no existe | Volver a buscarlo |
| `409` | `PRODUCT_CATALOG.DUPLICATE_CODE` | El producto ya tiene una presentación con ese código | Pedir otro código |
| `409` | `PRODUCT_CATALOG.BASE_PRESENTATION_EXISTS` | Ya hay una presentación base vigente | Enviar `is_base: false` |
| `422` | `PRODUCT_CATALOG.BASE_QUANTITY_MUST_BE_ONE` | `is_base: true` con `base_quantity` distinto de 1 | Corregir la cantidad |
| `422` | `PRODUCT_CATALOG.REFERENCE_NOT_FOUND` / `REFERENCE_INACTIVE` | El tipo de empaque o la unidad de contenido no existen o están inactivos | Volver a cargar los selectores |
| `422` | `PRODUCT_CATALOG.PRODUCT_INACTIVE` | El producto está `INACTIVE` | Informar |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | Código o nombre vacíos o largos, `base_quantity` ≤ 0, contenido sin unidad, `display_order` fuera de rango, campo desconocido | Corregir el formulario; `errors[]` trae `field` |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o el cuerpo no es JSON | Error de programación del cliente |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/product-catalog/duplicate-code",
  "title": "Código duplicado",
  "status": 409,
  "detail": "El producto ya tiene una presentación con el código CJ100.",
  "instance": "/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations",
  "code": "PRODUCT_CATALOG.DUPLICATE_CODE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

### Imagen de la presentación (spec 024; pendiente de despliegue)

Desde la spec 024 la imagen es de **cada presentación global**, no del producto. Después de crear la presentación, el frontend carga su imagen con un archivo del equipo del usuario: Product Catalog valida el contenido (JPEG, PNG o WebP, hasta 5 MiB y 40 megapíxeles), lo guarda en el almacenamiento de SIO y lo deja como imagen principal de la presentación. Permiso `perm:product-catalog:products:update`. **Aún no está desplegado en Render**; la ficha completa (listar, cambiar el nombre, cambiar la principal, eliminar y reactivar) está en [Product Catalog, imágenes por presentación](../servicios/product-catalog.md#imágenes-por-presentación-spec-024-operaciones-i-1-a-i-8).

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations/e6d7d0c7-a0be-4f4b-8bca-631867ff85c8/assets/upload' \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -F 'file=@caja-x-100-frente.jpg'
```

| Respuesta | Qué significa | Qué hacer en la interfaz |
|---|---|---|
| `201` | Imagen nueva, ya principal; `image_url` sirve para `<img src>` sin token | Mostrar la imagen |
| `200` | Era la misma imagen, que estaba eliminada: se reactivó con el mismo `id` | Mostrar la imagen |
| `409 PRODUCT_CATALOG.DUPLICATE_ASSET_CONTENT` | La presentación ya tiene esa imagen (`existing_asset_id`) | Informar que ya está cargada |
| `413 …FILE_TOO_LARGE` / `415 …UNSUPPORTED_MEDIA_TYPE` | Más de 5 MiB, o no es JPEG, PNG ni WebP | Pedir otra imagen |
| `422 …INVALID_IMAGE` / `IMAGE_DIMENSIONS_EXCEEDED` | Archivo dañado o de más de 40 megapíxeles | Pedir otra imagen |
| `422 …PRESENTATION_INACTIVE` / `PRODUCT_INACTIVE` | La presentación o el producto están inactivos | Reactivarlos primero |

En las consultas de [Product Inventory Query](../servicios/product-inventory-query.md#imágenes-por-presentación-spec-024-pendiente-de-despliegue), cada presentación trae `has_image`, `asset_id` e `image_url`, y todas sus imágenes con `include_images=true`.

## 7. Registrar un código de barras del producto global

**Método:** `POST`
**URL:** `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers`
**Permiso requerido:** `perm:product-catalog:products:update`

### ¿Qué hace esta API?

Registra un código de barras u otro identificador del producto, opcionalmente ligado a una presentación. Después, la búsqueda por `identifier` de la [API 1](#1-buscar-productos-globales) y el lector de códigos del punto de venta encuentran el producto.

Reglas verificadas en el código, en este orden: el producto debe estar `ACTIVE`; el valor se normaliza quitando espacios y guiones (máximo 100); `GTIN`, `EAN` y `UPC` deben ser numéricos de 8, 12, 13 o 14 dígitos con dígito de control GS1 válido; `IUM` debe tener 15 caracteres (un dígito, una letra mayúscula y 13 dígitos) y exige presentación; un `BARCODE` que cumple el estándar GTIN debe registrarse con su tipo específico; la presentación, si se envía, debe ser del mismo producto; el código no puede identificar otro registro (GTIN, EAN y UPC únicos por su forma canónica en todo el catálogo; `BARCODE` e `IUM` únicos en todo el catálogo, incluidos los inactivos; `OTHER` único dentro del producto). Devuelve `Location: /api/v1/products/{product_id}/identifiers/{id}` y registra `CREATE_PRODUCT_IDENTIFIER` en Audit.

Antes necesita: el `product_id` y, para ligarlo a una presentación, su `global_product_presentation_id` ([API 5](#5-consultar-las-presentaciones-globales-de-un-producto)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "identifier_type": "EAN",
    "value": "7702001023456",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "is_primary": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `product_id` | UUID | Sí | Producto global | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales; errores en §1) o `id` de la [API 3](#3-crear-un-producto-global) (crea el producto; errores en §3) · guía [global_product_id](../parametros/global-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "identifier_type": "EAN",
  "value": "7702001023456",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "is_primary": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `identifier_type` | `GTIN` \| `EAN` \| `UPC` \| `BARCODE` \| `OTHER` \| `IUM` | Sí | Tipo de identificador | `EAN` | Formulario |
| `value` | string (≤ 200; ≤ 100 sin espacios ni guiones) | Sí | Código tal como se lee; se quitan espacios y guiones | `7702001023456` | Lector de códigos o Formulario |
| `global_product_presentation_id` | UUID \| null | Obligatorio con `IUM`; opcional en los demás | Presentación del mismo producto a la que pertenece el código | `8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | `[].id` de la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) (lista las presentaciones del producto; errores en §5) · guía [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| `is_primary` | boolean | No; por defecto `false` | Marcarlo como principal de su tipo y contexto | `true` | Formulario |

### Respuesta exitosa

`201 Created` (`IdentifierResponse`), con cabecera `Location: /api/v1/products/{product_id}/identifiers/{id}`:

```json
{
  "id": "fe58314b-a470-4849-8dec-09ac92f93089",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "identifier_type": "EAN",
  "value": "7702001023456",
  "canonical_value": "07702001023456",
  "is_primary": true
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | Identificador del código, usado para marcarlo principal o inactivarlo (PC 75, 76) |
| `value` | string | Valor normalizado (sin espacios ni guiones) |
| `canonical_value` | string | Forma canónica con la que se compara la familia GTIN |
| `is_primary` | boolean | Si es el principal de su tipo y contexto |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto no existe | Volver a buscarlo |
| `409` | `PRODUCT_CATALOG.IDENTIFIER_COLLISION` | El código ya identifica otro registro; la extensión `conflict` trae `global_product_id`, `global_product_presentation_id`, `identifier_id`, `identifier_type` y `status` del existente | Mostrar el producto en conflicto y no registrar el código otra vez |
| `422` | `PRODUCT_CATALOG.INVALID_GTIN_FORMAT` | GTIN, EAN o UPC no numérico o con longitud distinta de 8, 12, 13 o 14 | Corregir el código |
| `422` | `PRODUCT_CATALOG.INVALID_CHECK_DIGIT` | El dígito de control GS1 no es válido | Volver a leer el código |
| `422` | `PRODUCT_CATALOG.BARCODE_IS_GTIN` | Se envió como `BARCODE` un código que cumple GTIN | Registrarlo como `GTIN`, `EAN` o `UPC` |
| `422` | `PRODUCT_CATALOG.INVALID_IUM_FORMAT` | IUM sin el formato de 15 caracteres | Corregir el código |
| `422` | `PRODUCT_CATALOG.IUM_REQUIRES_PRESENTATION` | IUM sin `global_product_presentation_id` | Elegir la presentación |
| `422` | `PRODUCT_CATALOG.PRESENTATION_OF_OTHER_PRODUCT` | La presentación no existe o es de otro producto | Volver a cargar las presentaciones con la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) |
| `422` | `PRODUCT_CATALOG.PRODUCT_INACTIVE` | El producto está `INACTIVE` | Informar |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | Tipo fuera de la enumeración, valor vacío o largo, campo desconocido | Corregir el formulario |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o el cuerpo no es JSON | Error de programación del cliente |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/product-catalog/identifier-collision",
  "title": "Colisión de identificador",
  "status": 409,
  "detail": "El código 7702001023456 ya identifica otro registro del catálogo; revise la inconsistencia.",
  "instance": "/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers",
  "code": "PRODUCT_CATALOG.IDENTIFIER_COLLISION",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "conflict": {
    "global_product_id": "1c2d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f",
    "global_product_presentation_id": null,
    "identifier_id": "2d3e4f5a-6b7c-4d8e-9f0a-1b2c3d4e5f6a",
    "identifier_type": "EAN",
    "status": "ACTIVE"
  }
}
```

## 8. Adoptar un producto global en la empresa

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products`
**Permiso requerido:** `perm:commercial-relationship:company_products:create`

### ¿Qué hace esta API?

Incorpora un producto del catálogo global a la empresa, con el código interno, el nombre, la moneda y la configuración de inventario con que la empresa lo maneja. El resultado es el producto empresarial cuyo `id` ([company_product_id](../parametros/company-product-id.md)) exigen las líneas de venta y de compra, los precios y las existencias.

Reglas verificadas en el código, en este orden: (1) la moneda debe estar en la lista admitida y se normaliza a mayúsculas; (2) las banderas de inventario deben ser coherentes: control por lotes exige control de inventario y control de vencimiento exige control por lotes; (3) la empresa no puede haber adoptado ya ese producto global, en ningún estado (`409 DUPLICATE_ADOPTION`); (4) `internal_code` único en la empresa (`409 DUPLICATE_INTERNAL_CODE`); (5) el producto global debe existir, estar `ACTIVE` y ser elegible en Product Catalog; (6) registra el primer uso del producto en Product Catalog. Nada se guarda si alguna regla falla. Crea el producto `ACTIVE` con `version` `1` y `purchase_tax_percentage: null`, devuelve `Location: /api/v1/company-products/{id}` y registra `ADOPT_COMPANY_PRODUCT` en Audit. Adoptar el producto **no adopta sus presentaciones**: se hace con la [API 11](#11-adoptar-una-presentación-en-la-empresa).

Antes necesita: `company_id` con membresía `ACTIVE` y empresa `ACTIVE`; un `global_product_id` con `eligible_for_adoption: true` ([API 1](#1-buscar-productos-globales)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "internal_code": "PRD-0001",
    "reference_code": null,
    "display_name": "Acetaminofén 500 mg tableta",
    "short_name": "Acetaminofén 500",
    "currency_code": "COP",
    "inventory_control_enabled": true,
    "lot_tracking_enabled": true,
    "expiration_tracking_enabled": true,
    "is_purchasable": true,
    "is_sellable": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa que adopta el producto | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": null,
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": "Acetaminofén 500",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `global_product_id` | UUID | Sí | Producto global `ACTIVE` y elegible; inmutable después de adoptar | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales; errores en §1), solo con `eligible_for_adoption: true` · guía [global_product_id](../parametros/global-product-id.md) |
| `internal_code` | string (1–60) | Sí | Código con que la empresa identifica el producto; se recortan espacios; único en la empresa | `PRD-0001` | Formulario (numeración propia de la empresa) |
| `reference_code` | string (≤ 100) \| null | No | Código de referencia adicional; vacío equivale a `null` | `null` | Formulario |
| `display_name` | string (1–200) | Sí | Nombre con que la empresa muestra el producto | `Acetaminofén 500 mg tableta` | Formulario; sugerir `canonical_name` de la [API 1](#1-buscar-productos-globales) |
| `short_name` | string (≤ 160) \| null | No | Nombre corto para tiquetes y pantallas pequeñas | `Acetaminofén 500` | Formulario |
| `currency_code` | string (código ISO 4217) | Sí | Moneda del producto; debe estar en la lista admitida | `COP` | Formulario (moneda de operación de la empresa) |
| `inventory_control_enabled` | boolean | No; por defecto `true` | Si Inventory controla existencias del producto | `true` | Formulario |
| `lot_tracking_enabled` | boolean | No; por defecto `false` | Control por lotes; exige `inventory_control_enabled: true` | `true` | Formulario |
| `expiration_tracking_enabled` | boolean | No; por defecto `false` | Control de vencimiento; exige `lot_tracking_enabled: true` | `true` | Formulario |
| `is_purchasable` | boolean | No; por defecto `true` | Si se puede comprar | `true` | Formulario |
| `is_sellable` | boolean | No; por defecto `true` | Si se puede vender | `true` | Formulario |

### Respuesta exitosa

`201 Created` (`CompanyProductResponse`), con cabecera `Location: /api/v1/company-products/{id}`:

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
  "reference_code": null,
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": "Acetaminofén 500",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [company_product_id](../parametros/company-product-id.md) que se envía en la [API 11](#11-adoptar-una-presentación-en-la-empresa), en los precios y en las líneas de venta y compra |
| `currency_code` | string | Moneda ya normalizada a mayúsculas |
| `purchase_tax_percentage` | string \| null | `null` al adoptar: el impuesto de compra está **sin configurar** hasta la [API 13](#13-configurar-el-impuesto-de-compra-del-producto) |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION` | La empresa ya adoptó ese producto global (activo o inactivo) | Buscarlo con la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) con `global_product_id` y `status=ALL`; si está inactivo, reactivarlo (CR 10) |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un producto con ese `internal_code` en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | La moneda no está en la lista admitida | Elegir una moneda admitida |
| `422` | `COMMERCIAL_RELATIONSHIP.INVENTORY_FLAGS_INVALID` | Lotes sin control de inventario o vencimiento sin lotes; `errors[].field` indica la bandera | Corregir las banderas |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_FOUND` | El producto global no existe en Product Catalog | Volver a buscarlo con la [API 1](#1-buscar-productos-globales) |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_INACTIVE` | El producto global está `INACTIVE` | Elegir otro producto |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_ELIGIBLE` | El producto global no está completo | Completar categoría y presentación con las API 4 y 6 |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden adoptar productos en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, UUID inválido o campo desconocido | Corregir el formulario; `errors[]` trae `field` y `message` |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Product Catalog no responde al validar el producto o registrar su primer uso | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por producto incompleto:

```json
{
  "type": "https://sio/errors/commercial-relationship/global-product-not-eligible",
  "title": "Producto global no elegible",
  "status": 422,
  "detail": "El producto global no está completo y no se puede adoptar.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products",
  "code": "COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_ELIGIBLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "global_product_id",
      "message": "El producto global no está completo y no se puede adoptar.",
      "code": "GLOBAL_PRODUCT_NOT_ELIGIBLE"
    }
  ]
}
```

## 9. Buscar y listar los productos de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products`
**Permiso requerido:** `perm:commercial-relationship:company_products:read`

### ¿Qué hace esta API?

Lista, con paginación y búsqueda, los productos que la empresa adoptó. Es la fuente de `company_product_id` para precios, presentaciones y líneas de venta y compra. La búsqueda es sobre los datos de la empresa (`internal_code`, `reference_code` y `display_name`), no sobre el código de barras: para buscar por código se usa la [API 1](#1-buscar-productos-globales) y se filtra aquí por `global_product_id`. Por defecto solo devuelve productos `ACTIVE`. Para un catálogo de venta con precio y existencias en una sola llamada existe Product Inventory Query ([Inventario](inventario.md)).

Antes necesita: `company_id` con membresía `ACTIVE`. Funciona también con la empresa `INACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products?search=acetaminofen&status=ACTIVE&is_sellable=true&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `?page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial, sin distinguir mayúsculas, en `internal_code`, `reference_code` y `display_name` | Texto libre: parte del código o del nombre; p. ej. `PRD-0001` o `acetaminofen` | `&search=acetaminofen` | Interfaz (código o nombre que escribe el usuario) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de los productos | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `is_purchasable` | boolean | No | Solo productos comprables (`true`) o no comprables (`false`) | `true` o `false`; p. ej. `true` | `&is_purchasable=true` | Interfaz (pantallas de compra) |
| `is_sellable` | boolean | No | Solo productos vendibles (`true`) o no vendibles (`false`) | `true` o `false`; p. ej. `true` | `&is_sellable=true` | Interfaz (pantallas de venta) |
| `inventory_control_enabled` | boolean | No | Solo productos con o sin control de inventario | `true` o `false`; p. ej. `true` | `&inventory_control_enabled=true` | Interfaz |
| `global_product_id` | UUID | No | Solo la adopción de ese producto global | UUID de un producto global; p. ej. `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `&global_product_id=f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` | `items[].id` de la [API 1](#1-buscar-productos-globales) (busca productos globales, también por código de barras; errores en §1) · guía [global_product_id](../parametros/global-product-id.md) |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products?search=acetaminofen&status=ACTIVE&is_sellable=true&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyProductResponse]`):

```json
{
  "items": [
    {
      "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 2,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:10:00Z",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "display_name": "Acetaminofén 500 mg tableta",
      "short_name": "Acetaminofén 500",
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": true,
      "expiration_tracking_enabled": true,
      "is_purchasable": true,
      "is_sellable": true,
      "purchase_tax_percentage": "19.0000"
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
| `items[].id` | UUID | El [company_product_id](../parametros/company-product-id.md) |
| `items[].global_product_id` | UUID | Producto global de origen; con él se consultan sus presentaciones globales en la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) |
| `items[].internal_code`, `display_name`, `short_name` | string | Textos para el buscador de productos |
| `items[].is_purchasable`, `is_sellable` | boolean | Si el producto puede usarse en compras o ventas |
| `items[].purchase_tax_percentage` | string \| null | Tasa de impuesto de compra con 4 decimales; `null` si está sin configurar |
| `items[].version` | integer | Valor que debe enviarse en la [API 13](#13-configurar-el-impuesto-de-compra-del-producto) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío cuando no hay coincidencias (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, booleano o UUID inválido, paginación fuera de rango | Corregir los filtros |

## 10. Consultar un producto de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}`
**Permiso requerido:** `perm:commercial-relationship:company_products:read`

### ¿Qué hace esta API?

Devuelve un producto de la empresa en cualquier estado, si pertenece a una empresa en la que el usuario tiene membresía `ACTIVE`. Se usa para abrir su detalle y para leer la `version` vigente antes de configurar el impuesto de compra ([API 13](#13-configurar-el-impuesto-de-compra-del-producto)).

Antes necesita: el `company_product_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto de la empresa | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos de la empresa; errores en §9) o `id` de la [API 8](#8-adoptar-un-producto-global-en-la-empresa) (adopta el producto; errores en §8) · guía [company_product_id](../parametros/company-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`CompanyProductResponse`), mismo objeto y campos que un elemento de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa):

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
  "reference_code": null,
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": "Acetaminofén 500",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` | Un producto `INACTIVE` se consulta pero no admite nuevas presentaciones ni precios |
| `version` | integer | Valor que debe enviarse en la [API 13](#13-configurar-el-impuesto-de-compra-del-producto) |
| `purchase_tax_percentage` | string \| null | `null` indica impuesto sin configurar; Compras no confirmará líneas de este producto sin tasa |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El producto no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista; no distinguir entre «no existe» y «sin acceso» |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `company_product_id` no es un UUID | Corregir el identificador |

## 11. Adoptar una presentación en la empresa

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations`
**Permiso requerido:** `perm:commercial-relationship:company_product_presentations:create`

### ¿Qué hace esta API?

Habilita en la empresa una presentación global de un producto ya adoptado, con sus banderas de compra y venta y si es la predeterminada. El resultado es la presentación empresarial cuyo `id` ([company_product_presentation_id](../parametros/company-product-presentation-id.md)) piden las líneas de venta y compra, los precios y las políticas.

Reglas verificadas en el código, en este orden: (1) una predeterminada de compra debe ser comprable y una de venta, vendible; (2) el producto empresarial debe ser de la empresa y estar `ACTIVE`; (3) la presentación global no puede estar ya adoptada para ese producto, en ningún estado; (4) `sku` e `internal_code`, si se envían, únicos en la empresa; (5) la presentación global debe existir, estar `ACTIVE`, pertenecer al mismo producto global y ser elegible; (6) registra el primer uso en Product Catalog. Si se marca como predeterminada de compra o de venta, quita esa marca a las demás presentaciones del producto. Crea la presentación `ACTIVE`, devuelve `Location: /api/v1/company-product-presentations/{id}` y registra `CREATE_COMPANY_PRODUCT_PRESENTATION` en Audit.

Antes necesita: el `company_product_id` ([API 8](#8-adoptar-un-producto-global-en-la-empresa) o [API 9](#9-buscar-y-listar-los-productos-de-la-empresa)) y un `global_product_presentation_id` **del mismo producto global** ([API 5](#5-consultar-las-presentaciones-globales-de-un-producto)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "internal_code": "PRD-0001-CJ",
    "sku": "7702001023456",
    "reference_code": null,
    "is_purchasable": true,
    "is_sellable": true,
    "is_default_purchase": true,
    "is_default_sale": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ",
  "sku": "7702001023456",
  "reference_code": null,
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto de la empresa, `ACTIVE` | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `id` de la [API 8](#8-adoptar-un-producto-global-en-la-empresa) (adopta el producto; errores en §8) o `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos de la empresa; errores en §9) · guía [company_product_id](../parametros/company-product-id.md) |
| `global_product_presentation_id` | UUID | Sí | Presentación global `ACTIVE` y elegible del mismo producto global | `8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | `[].id` de la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) con el `global_product_id` del producto (lista sus presentaciones; errores en §5) · guía [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| `internal_code` | string (≤ 80) \| null | No | Código interno de la presentación; único en la empresa | `PRD-0001-CJ` | Formulario |
| `sku` | string (≤ 80) \| null | No | SKU; único en la empresa | `7702001023456` | Formulario o Lector de códigos |
| `reference_code` | string (≤ 100) \| null | No | Referencia adicional | `null` | Formulario |
| `is_purchasable` | boolean | No; por defecto `true` | Si se compra en esta presentación | `true` | Formulario |
| `is_sellable` | boolean | No; por defecto `true` | Si se vende en esta presentación | `true` | Formulario |
| `is_default_purchase` | boolean | No; por defecto `false` | Predeterminada para compras; exige `is_purchasable: true` | `true` | Formulario |
| `is_default_sale` | boolean | No; por defecto `false` | Predeterminada para ventas; exige `is_sellable: true` | `true` | Formulario |

### Respuesta exitosa

`201 Created` (`CompanyProductPresentationResponse`), con cabecera `Location: /api/v1/company-product-presentations/{id}`:

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
  "internal_code": "PRD-0001-CJ",
  "sku": "7702001023456",
  "reference_code": null,
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": true
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `global_product_presentation_id` | UUID | Presentación global de origen; su nombre y cantidad base se leen en la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto), porque no viajan en este objeto |
| `is_default_purchase`, `is_default_sale` | boolean | Si es la preseleccionada en compras o ventas |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION` | La presentación global ya está adoptada para ese producto (activa o inactiva) | Buscarla con la [API 12](#12-consultar-las-presentaciones-de-la-empresa) con `status=ALL`; si está inactiva, reactivarla (CR 33) |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_SKU` | Otra presentación de la empresa ya usa ese `sku` | Pedir otro SKU |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Otra presentación de la empresa ya usa ese `internal_code` | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.DEFAULT_FLAG_INVALID` | Predeterminada de compra no comprable o de venta no vendible | Corregir las banderas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_NOT_FOUND` | El producto empresarial no existe en la empresa | Volver a elegir el producto |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_INACTIVE` | El producto empresarial está `INACTIVE` | Reactivarlo antes (CR 10) |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_NOT_FOUND` / `GLOBAL_PRESENTATION_INACTIVE` / `GLOBAL_PRESENTATION_NOT_ELIGIBLE` | La presentación global no existe, está inactiva o no es elegible para adopción | Elegir otra presentación de la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_OF_OTHER_PRODUCT` | La presentación global no pertenece al producto global adoptado | Listar las presentaciones del producto correcto |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden adoptar presentaciones en ella |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, UUID inválido o campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Product Catalog no responde | Reintentar más tarde; nada se guardó |

Ejemplo de `422` por presentación de otro producto:

```json
{
  "type": "https://sio/errors/commercial-relationship/global-presentation-of-other-product",
  "title": "Presentación global de otro producto",
  "status": 422,
  "detail": "La presentación global no pertenece al producto global adoptado.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations",
  "code": "COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_OF_OTHER_PRODUCT",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "global_product_presentation_id",
      "message": "La presentación global no pertenece al producto global adoptado.",
      "code": "GLOBAL_PRESENTATION_OF_OTHER_PRODUCT"
    }
  ]
}
```

## 12. Consultar las presentaciones de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations`
**Permiso requerido:** `perm:commercial-relationship:company_product_presentations:read`

### ¿Qué hace esta API?

Lista, con paginación, las presentaciones que la empresa adoptó, normalmente filtradas por `company_product_id` para ver solo las del producto elegido. Es la fuente de `company_product_presentation_id` para precios, políticas y líneas de venta y compra. Por defecto solo devuelve presentaciones `ACTIVE`. El nombre y la cantidad base («Caja x 100») no están en este objeto: se leen en la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) con `global_product_presentation_id`.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_sellable=true&status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `company_product_id` | UUID | No | Solo las presentaciones de ese producto | UUID de un producto de la empresa; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `?company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos de la empresa; errores en §9) · guía [company_product_id](../parametros/company-product-id.md) |
| `global_product_presentation_id` | UUID | No | Solo la adopción de esa presentación global | UUID de una presentación global; p. ej. `8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | `&global_product_presentation_id=8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` | `[].id` de la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) (lista las presentaciones globales; errores en §5) · guía [global_product_presentation_id](../parametros/global-product-presentation-id.md) |
| `search` | string (≤ 100) | No | Búsqueda parcial en `internal_code`, `sku` y `reference_code` | Texto libre; p. ej. `7702001023456` | `&search=7702001023456` | Interfaz o Lector de códigos |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las presentaciones | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `is_purchasable` | boolean | No | Solo comprables o no comprables | `true` o `false`; p. ej. `true` | `&is_purchasable=true` | Interfaz (pantallas de compra) |
| `is_sellable` | boolean | No | Solo vendibles o no vendibles | `true` o `false`; p. ej. `true` | `&is_sellable=true` | Interfaz (pantallas de venta y precios) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_sellable=true&status=ACTIVE`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[CompanyProductPresentationResponse]`):

```json
{
  "items": [
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
      "internal_code": "PRD-0001-CJ",
      "sku": "7702001023456",
      "reference_code": null,
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [company_product_presentation_id](../parametros/company-product-presentation-id.md) que se envía en precios, políticas y líneas de venta y compra |
| `items[].company_product_id` | UUID | Producto al que pertenece; las líneas envían ambos |
| `items[].global_product_presentation_id` | UUID | Con él se leen nombre y cantidad base en la [API 5](#5-consultar-las-presentaciones-globales-de-un-producto) |
| `items[].is_sellable`, `is_purchasable` | boolean | Solo las vendibles admiten precios y políticas |
| `items[].is_default_sale`, `is_default_purchase` | boolean | Cuál preseleccionar en ventas o compras |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `search` > 100, `status` fuera de la enumeración, booleano o UUID inválido, paginación fuera de rango | Corregir los filtros |

## 13. Configurar el impuesto de compra del producto

**Método:** `PUT`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/{company_product_id}/purchase-tax`
**Permiso requerido:** `perm:commercial-relationship:company_product_purchase_taxes:update`

### ¿Qué hace esta API?

Fija la tasa de impuesto de compra del producto (por ejemplo IVA 19 %, 5 % o 0 %). Compras la toma para cada línea del producto salvo que la línea envíe su propia tasa; sin tasa configurada ni tasa en la línea, la compra no se confirma (`409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED`, ver [Compras](compras.md)).

Reglas verificadas en el código: la tasa va de 0 a 100 con hasta 4 decimales y **no se redondea** (se rechaza); `0` es una tasa válida y distinta de «sin configurar»; una tasa configurada no puede volver a `null` (`422 PURCHASE_TAX_REQUIRED`); si la tasa enviada es igual a la vigente no escribe ni incrementa `version`. Registra `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX` sobre la entidad `CompanyProduct` en Audit. Para configurar hasta 100 productos en una sola operación (todo o nada) existe CR 12.

Antes necesita: la `version` actual del producto ([API 10](#10-consultar-un-producto-de-la-empresa)) y empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/purchase-tax' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "purchase_tax_percentage": "19"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto de la empresa | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `id` de la [API 10](#10-consultar-un-producto-de-la-empresa) (devuelve el producto de la empresa; errores en §10) o `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos; errores en §9) · guía [company_product_id](../parametros/company-product-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "purchase_tax_percentage": "19"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del producto | `1` | `version` de la [API 10](#10-consultar-un-producto-de-la-empresa) (devuelve el producto de la empresa; errores en §10) |
| `purchase_tax_percentage` | número o texto decimal (0–100, hasta 4 decimales) | Sí; no admite `null` | Tasa de impuesto de compra; `0` es válido | `19` | Formulario (tasa tributaria del producto) |

### Respuesta exitosa

`200 OK` (`CompanyProductResponse`) con la tasa actualizada y `version` incrementada si hubo cambio:

```json
{
  "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:10:00Z",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "reference_code": null,
  "display_name": "Acetaminofén 500 mg tableta",
  "short_name": "Acetaminofén 500",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "purchase_tax_percentage": "19.0000"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `purchase_tax_percentage` | string | Tasa configurada con 4 decimales |
| `version` | integer | Nueva versión; se mantiene si la tasa no cambió |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El producto no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 10](#10-consultar-un-producto-de-la-empresa) y repetir |
| `422` | `COMMERCIAL_RELATIONSHIP.PURCHASE_TAX_REQUIRED` | Se envió `null` | Enviar una tasa; `0` es válido |
| `422` | `COMMERCIAL_RELATIONSHIP.TAX_PERCENTAGE_OUT_OF_RANGE` | Tasa negativa, mayor que 100, con más de 4 decimales, no numérica o booleana | Corregir la tasa |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se puede configurar |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente o < 1, campo desconocido | Corregir la solicitud |

Ejemplo de `422`:

```json
{
  "type": "https://sio/errors/commercial-relationship/tax-percentage-out-of-range",
  "title": "Tasa de impuesto inválida",
  "status": 422,
  "detail": "La tasa de impuesto de compra debe estar entre 0 y 100, con hasta 4 decimales.",
  "instance": "/api/v1/company-products/e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61/purchase-tax",
  "code": "COMMERCIAL_RELATIONSHIP.TAX_PERCENTAGE_OUT_OF_RANGE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "purchase_tax_percentage",
      "message": "La tasa de impuesto de compra debe estar entre 0 y 100, con hasta 4 decimales.",
      "code": "TAX_PERCENTAGE_OUT_OF_RANGE"
    }
  ]
}
```

## 14. Crear una lista de precios

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists`
**Permiso requerido:** `perm:commercial-relationship:price_lists:create`

### ¿Qué hace esta API?

Crea una lista de precios de la empresa en una moneda: mostrador, mayoristas, convenios o campañas con fecha de inicio y fin. Una empresa puede tener varias listas en la misma moneda; el vendedor elige entre ellas en cada línea de venta.

Reglas verificadas en el código: la moneda debe estar en la lista admitida y queda **inmutable**; si se envían ambas, `valid_to` debe ser posterior a `valid_from`; el `code` es único en la empresa sin distinguir mayúsculas; si `is_default` es `true`, la lista pasa a ser la predeterminada de esa moneda y la anterior pierde la marca. Crea la lista `ACTIVE` con `version` `1`, devuelve `Location: /api/v1/price-lists/{id}` y registra `CREATE_PRICE_LIST` en Audit. Crear la lista no crea precios: se registran con la [API 17](#17-registrar-un-precio-de-venta) o los genera una política ([API 21](#21-crear-una-política-de-ganancia)).

Antes necesita: `company_id` con membresía `ACTIVE` y empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "MOSTRADOR",
    "name": "Precio de mostrador",
    "currency_code": "COP",
    "description": "Lista general de venta al público",
    "valid_from": "2026-10-01T00:00:00Z",
    "valid_to": null,
    "is_default": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa dueña de la lista | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

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

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `code` | string (1–50) | Sí | Código de la lista; único en la empresa sin distinguir mayúsculas | `MOSTRADOR` | Formulario |
| `name` | string (1–120) | Sí | Nombre que verá el vendedor | `Precio de mostrador` | Formulario |
| `currency_code` | string (código ISO 4217) | Sí | Moneda de la lista; inmutable | `COP` | Formulario; normalmente la `currency_code` de los productos ([API 9](#9-buscar-y-listar-los-productos-de-la-empresa)) |
| `description` | string \| null | No | Descripción libre; vacía equivale a `null` | `Lista general de venta al público` | Formulario |
| `valid_from` | date-time con zona \| null | No | Inicio de vigencia; `null` es «sin inicio» | `2026-10-01T00:00:00Z` | Formulario |
| `valid_to` | date-time con zona \| null | No | Fin de vigencia (exclusivo); `null` es «sin fin»; posterior a `valid_from` | `null` | Formulario |
| `is_default` | boolean | No; por defecto `false` | Predeterminada de la empresa para esa moneda | `true` | Formulario |

### Respuesta exitosa

`201 Created` (`PriceListResponse`), con cabecera `Location: /api/v1/price-lists/{id}`:

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
  "description": "Lista general de venta al público",
  "currency_code": "COP",
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [price_list_id](../parametros/price-list-id.md) que se envía en precios, políticas y líneas de venta |
| `currency_code` | string | Moneda normalizada a mayúsculas; no cambia |
| `is_default` | boolean | Si es la predeterminada de su moneda |
| `valid_from`, `valid_to` | date-time \| null | Vigencia `[valid_from, valid_to)` en UTC |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_PRICE_LIST_CODE` | Ya existe una lista con ese código en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | Moneda fuera de la lista admitida | Elegir una moneda admitida |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no es posterior a `valid_from` | Corregir las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear listas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Código o nombre vacíos o largos, fecha sin zona horaria, campo desconocido | Corregir el formulario |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/duplicate-price-list-code",
  "title": "Código de lista duplicado",
  "status": 409,
  "detail": "Ya existe una lista de precios con ese código en la empresa.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists",
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_PRICE_LIST_CODE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "code",
      "message": "Ya existe una lista de precios con ese código en la empresa.",
      "code": "DUPLICATE_PRICE_LIST_CODE"
    }
  ]
}
```

## 15. Consultar las listas de precios de la empresa

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists`
**Permiso requerido:** `perm:commercial-relationship:price_lists:read`

### ¿Qué hace esta API?

Lista, con paginación, las listas de precios de la empresa ordenadas por código. Sirve para administrar las listas, para mostrar el nombre de cada lista junto a sus precios ([API 18](#18-consultar-los-precios-vigentes)) y para obtener el `price_list_id`. Por defecto solo devuelve listas `ACTIVE`. Una lista está **vigente** en un instante cuando su `status` es `ACTIVE`, `valid_from` es `null` o ya llegó, y `valid_to` es `null` o aún no llega; el frontend lo calcula con estos campos.

Antes necesita: `company_id` con membresía `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&currency_code=COP&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las listas | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz |
| `currency_code` | string (exactamente 3) | No | Solo listas de esa moneda; se convierte a mayúsculas | Código ISO 4217; p. ej. `COP` | `&currency_code=COP` | `currency_code` del producto ([API 9](#9-buscar-y-listar-los-productos-de-la-empresa)) o Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial en `code` y `name` | Texto libre; p. ej. `mostrador` | `&search=mostrador` | Interfaz |
| `is_default` | boolean | No | Solo la predeterminada (`true`) o las demás (`false`) | `true` o `false`; p. ej. `true` | `&is_default=true` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&currency_code=COP&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PriceListResponse]`):

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
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "code": "MOSTRADOR",
      "name": "Precio de mostrador",
      "description": "Lista general de venta al público",
      "currency_code": "COP",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [price_list_id](../parametros/price-list-id.md) |
| `items[].name`, `code` | string | Textos para mostrar junto a cada precio |
| `items[].currency_code` | string | Moneda de la lista |
| `items[].is_default` | boolean | Predeterminada de su moneda |
| `items[].valid_from`, `valid_to` | date-time \| null | Con la hora actual determinan si la lista está vigente |
| `items[].version` | integer | Valor que debe enviarse en la [API 16](#16-modificar-una-lista-de-precios) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `currency_code` distinto de 3 caracteres, `search` > 100, `status` o booleano inválido, paginación fuera de rango | Corregir los filtros |

## 16. Modificar una lista de precios

**Método:** `PUT`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/{price_list_id}`
**Permiso requerido:** `perm:commercial-relationship:price_lists:update`

### ¿Qué hace esta API?

Modifica código, nombre, descripción, vigencia y marca de predeterminada de una lista. Es un reemplazo completo: se envían todos los campos con su valor final; `description`, `valid_from` y `valid_to` omitidos quedan en `null`. Sirve para cerrar una lista de campaña (`valid_to`) o para cambiar la predeterminada. La moneda, la empresa y el `status` son **inmutables**.

Efectos verificados en el código: funciona sobre listas en cualquier estado, pero solo una lista `ACTIVE` puede marcarse predeterminada; al marcarla quita la marca a la anterior de la misma moneda; si no hay cambios no escribe ni incrementa `version`; no modifica los precios de la lista; registra `UPDATE_PRICE_LIST` en Audit.

Antes necesita: la `version` actual ([API 15](#15-consultar-las-listas-de-precios-de-la-empresa)) y empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X PUT \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "code": "MOSTRADOR",
    "name": "Precio de mostrador",
    "description": "Lista general de venta al público",
    "valid_from": "2026-10-01T00:00:00Z",
    "valid_to": "2027-01-01T00:00:00Z",
    "is_default": true
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `price_list_id` | UUID | Sí | Lista a modificar | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) o `id` de la [API 14](#14-crear-una-lista-de-precios) (crea la lista; errores en §14) · guía [price_list_id](../parametros/price-list-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "description": "Lista general de venta al público",
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": "2027-01-01T00:00:00Z",
  "is_default": true
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la lista | `1` | `items[].version` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) |
| `code` | string (1–50) | Sí | Código final; único en la empresa | `MOSTRADOR` | Formulario (repetir el actual si no cambia) |
| `name` | string (1–120) | Sí | Nombre final | `Precio de mostrador` | Formulario |
| `description` | string \| null | No; omitirla la deja en `null` | Descripción final | `Lista general de venta al público` | Formulario |
| `valid_from` | date-time con zona \| null | No; omitirla la deja en `null` | Inicio de vigencia final | `2026-10-01T00:00:00Z` | Formulario |
| `valid_to` | date-time con zona \| null | No; omitirla la deja en `null` | Fin de vigencia final; posterior a `valid_from` | `2027-01-01T00:00:00Z` | Formulario |
| `is_default` | boolean | Sí | Predeterminada de su moneda; `true` solo en listas `ACTIVE` | `true` | Formulario |

No se admiten en el cuerpo `currency_code`, `company_id` ni `status`: su presencia responde `422 IMMUTABLE_FIELD`.

### Respuesta exitosa

`200 OK` (`PriceListResponse`) con `version` incrementada si hubo cambios:

```json
{
  "id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z",
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "description": "Lista general de venta al público",
  "currency_code": "COP",
  "is_default": true,
  "valid_from": "2026-10-01T00:00:00Z",
  "valid_to": "2027-01-01T00:00:00Z"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `version` | integer | Nueva versión; se mantiene si no hubo cambios |
| `valid_to` | date-time \| null | Desde ese instante la lista deja de estar vigente y Ventas no la acepta |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La lista no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de listas |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_PRICE_LIST_CODE` | Otra lista de la empresa ya usa ese código | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.IMMUTABLE_FIELD` | El cuerpo incluye `currency_code`, `company_id` o `status` | Error de programación: no enviar esos campos |
| `422` | `COMMERCIAL_RELATIONSHIP.DEFAULT_REQUIRES_ACTIVE` | `is_default: true` en una lista `INACTIVE` | Reactivar la lista antes (CR 51) o enviar `false` |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no es posterior a `valid_from` | Corregir las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar listas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, fecha sin zona, campo desconocido | Corregir el formulario |

## 17. Registrar un precio de venta

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items`
**Permiso requerido:** `perm:commercial-relationship:price_list_items:create`

### ¿Qué hace esta API?

Fija a mano el precio de venta de una presentación en una lista, con vigencia opcional. Es el precio que verá el vendedor en la [API 18](#18-consultar-los-precios-vigentes) y que Sales congela en la venta.

Reglas verificadas en el código, en este orden: (1) la lista debe ser de la empresa y estar `ACTIVE`; (2) el producto debe ser de la empresa y estar `ACTIVE`; (3) la presentación debe ser de la empresa, del mismo producto, `ACTIVE` y vendible; (4) `unit_price` ≥ 0 y sin más decimales que la moneda de la lista (sin redondeo); (5) si `valid_from` se omite toma el instante del servidor; (6) `valid_to` posterior a `valid_from`; (7) la vigencia no puede cruzarse con otro precio `ACTIVE` de la misma lista, producto y presentación. Crea el precio `ACTIVE` con `origin: null` (manual), devuelve `Location: /api/v1/price-list-items/{id}` y registra `CREATE_PRICE_LIST_ITEM` en Audit. El código no compara la moneda del producto con la de la lista.

Antes necesita: la lista ([API 14](#14-crear-una-lista-de-precios) o [API 15](#15-consultar-las-listas-de-precios-de-la-empresa)), el producto ([API 9](#9-buscar-y-listar-los-productos-de-la-empresa)) y la presentación vendible ([API 12](#12-consultar-las-presentaciones-de-la-empresa)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "unit_price": "8500.00",
    "valid_from": "2026-10-20T00:00:00Z",
    "valid_to": null
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "unit_price": "8500.00",
  "valid_from": "2026-10-20T00:00:00Z",
  "valid_to": null
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `price_list_id` | UUID | Sí | Lista `ACTIVE` de la empresa | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) o `id` de la [API 14](#14-crear-una-lista-de-precios) (crea la lista; errores en §14) · guía [price_list_id](../parametros/price-list-id.md) |
| `company_product_id` | UUID | Sí | Producto `ACTIVE` de la empresa | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos de la empresa; errores en §9) · guía [company_product_id](../parametros/company-product-id.md) |
| `company_product_presentation_id` | UUID | Sí | Presentación `ACTIVE` y vendible de ese producto | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) con `company_product_id` e `is_sellable=true` (lista las presentaciones; errores en §12) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `unit_price` | número o texto decimal ≥ 0 | Sí | Precio de venta por presentación; como máximo los decimales de la moneda de la lista | `8500.00` | Formulario |
| `valid_from` | date-time con zona \| null | No; por defecto el instante del servidor | Inicio de vigencia | `2026-10-20T00:00:00Z` | Formulario |
| `valid_to` | date-time con zona \| null | No | Fin de vigencia (exclusivo); `null` es «sin fin» | `null` | Formulario |

### Respuesta exitosa

`201 Created` (`PriceListItemResponse`), con cabecera `Location: /api/v1/price-list-items/{id}`:

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
  "unit_price": "8500.00",
  "currency_code": "COP",
  "valid_from": "2026-10-20T00:00:00Z",
  "valid_to": null,
  "origin": null,
  "closure_reason": null,
  "automatic_application_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El `price_list_item_id` que usan las API 19 y 20 |
| `unit_price` | string | Precio con los decimales de la moneda |
| `currency_code` | string | Moneda de la lista (solo lectura) |
| `valid_from`, `valid_to` | date-time | Vigencia del precio |
| `origin` | `null` \| `AUTOMATIC` | `null` para precios manuales; `AUTOMATIC` si lo creó una política |
| `closure_reason`, `automatic_application_id` | string \| null, UUID \| null | Se informan cuando una actualización automática cerró o creó el precio |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.PRICE_PERIOD_OVERLAP` | La vigencia se cruza con otro precio activo de la misma lista, producto y presentación | Cambiar el precio vigente con la [API 19](#19-cambiar-un-precio-vigente) o ajustar las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_LIST_NOT_FOUND` | La lista no existe en la empresa | Volver a cargar las listas |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | La lista está `INACTIVE` | Elegir otra lista o reactivarla (CR 51) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_NOT_FOUND` / `COMPANY_PRODUCT_INACTIVE` | El producto no es de la empresa o está inactivo | Elegir otro producto |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_FOUND` / `PRESENTATION_OF_OTHER_PRODUCT` / `PRESENTATION_INACTIVE` / `PRESENTATION_NOT_SELLABLE` | La presentación no es de la empresa, es de otro producto, está inactiva o no es vendible | Volver a cargar las presentaciones vendibles con la [API 12](#12-consultar-las-presentaciones-de-la-empresa) |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_SCALE_NOT_ALLOWED` | El precio tiene más decimales que la moneda | Redondear en la interfaz antes de enviar |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no es posterior a `valid_from` | Corregir las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden registrar precios |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, precio negativo o no numérico, fecha sin zona, campo desconocido | Corregir el formulario |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/price-period-overlap",
  "title": "Vigencia solapada",
  "status": 409,
  "detail": "La vigencia se cruza con otro precio activo de la misma lista, producto y presentación.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items",
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_PERIOD_OVERLAP",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 18. Consultar los precios vigentes

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items`
**Permiso requerido:** `perm:commercial-relationship:price_list_items:read`

### ¿Qué hace esta API?

Lista los precios de la empresa con paginación, ordenados por lista, producto e inicio de vigencia. Con el filtro por presentación y `applicable_at` (el instante actual) devuelve **las opciones de precio** de esa presentación: una por cada lista que tiene un precio vigente en ese instante. Es la consulta con la que la pantalla de venta muestra los precios ordenados de mayor a menor para que el vendedor elija la lista; con `price_list_id` sirve para administrar todos los precios de una lista.

Efectos verificados en el código: sin `status` devuelve solo precios `ACTIVE`; `applicable_at` filtra por la vigencia **del precio** (`valid_from` ≤ instante y `valid_to` vacío o posterior), **no** por la vigencia de su lista: el frontend debe descartar los precios cuya lista no esté `ACTIVE` y vigente, cruzando `price_list_id` con la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa), que además da el nombre de cada lista. La venta solo acepta listas vigentes ([Ventas](ventas.md)).

Antes necesita: `company_id` con membresía `ACTIVE` y la presentación ([API 12](#12-consultar-las-presentaciones-de-la-empresa)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-20T15:00:00Z' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `company_product_presentation_id` | UUID | No | Solo precios de esa presentación | UUID de una presentación de la empresa; p. ej. `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) (lista las presentaciones de la empresa; errores en §12) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de los precios | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `&status=ACTIVE` | Interfaz |
| `applicable_at` | date-time con zona | No | Solo precios cuya vigencia cubre ese instante | Fecha y hora ISO 8601 con zona; p. ej. `2026-10-20T15:00:00Z` (la hora actual) | `&applicable_at=2026-10-20T15:00:00Z` | Interfaz (hora actual en UTC) |
| `price_list_id` | UUID | No | Solo precios de esa lista | UUID de una lista; p. ej. `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) · guía [price_list_id](../parametros/price-list-id.md) |
| `company_product_id` | UUID | No | Solo precios de ese producto | UUID de un producto de la empresa; p. ej. `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `&company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` | `items[].id` de la [API 9](#9-buscar-y-listar-los-productos-de-la-empresa) (lista los productos de la empresa; errores en §9) · guía [company_product_id](../parametros/company-product-id.md) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-list-items?company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83&status=ACTIVE&applicable_at=2026-10-20T15:00:00Z`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PriceListItemResponse]`):

```json
{
  "items": [
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
      "unit_price": "8500.00",
      "currency_code": "COP",
      "valid_from": "2026-10-20T00:00:00Z",
      "valid_to": null,
      "origin": null,
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].price_list_id` | UUID | Lista del precio; es el valor que la línea de venta envía como `price_list_id` cuando el vendedor elige este precio |
| `items[].unit_price` | string | Precio para mostrar; ordenar las opciones de mayor a menor |
| `items[].currency_code` | string | Moneda de la lista |
| `items[].valid_from`, `valid_to` | date-time | Vigencia del precio |
| `items[].origin` | `null` \| `AUTOMATIC` | Manual o calculado por una política |
| `items[].id`, `version` | UUID, integer | Valores para la [API 19](#19-cambiar-un-precio-vigente) y la [API 20](#20-corregir-un-precio-futuro-o-cerrar-uno-vigente) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación; `items` vacío si la presentación no tiene precio vigente (no es error) |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `applicable_at` sin zona horaria o mal formado, UUID inválido, `status` fuera de la enumeración, paginación fuera de rango | Corregir los filtros |

## 19. Cambiar un precio vigente

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}/change-price`
**Permiso requerido:** `perm:commercial-relationship:price_list_items:update`

### ¿Qué hace esta API?

Cambia el valor de un precio que ya está en vigencia: en una sola transacción cierra el precio actual en `effective_from` y crea el precio nuevo desde ese instante hasta el `valid_to` que tenía el anterior. Es la única forma de cambiar el valor de un precio en vigencia; el precio futuro se corrige con la [API 20](#20-corregir-un-precio-futuro-o-cerrar-uno-vigente).

Reglas verificadas en el código, en este orden: (1) la `version` debe ser la vigente; (2) el precio debe estar `ACTIVE`; (3) debe pertenecer a una presentación; (4) la lista, el producto y la presentación deben seguir `ACTIVE`; (5) el nuevo `unit_price` no puede tener más decimales que la moneda; (6) `effective_from` (por defecto el instante del servidor) debe ser actual o futuro, posterior al inicio del precio y anterior a su fin. Devuelve `201` con el precio nuevo y el anterior ya cerrado, la cabecera `Location: /api/v1/price-list-items/{id del nuevo}`, y registra `CHANGE_PRICE_LIST_ITEM_PRICE` en Audit. El precio nuevo es manual (`origin: null`).

Antes necesita: el `price_list_item_id` y su `version` ([API 18](#18-consultar-los-precios-vigentes)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c/change-price' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "unit_price": "9000.00",
    "effective_from": null,
    "version": 1
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `price_list_item_id` | UUID | Sí | Precio vigente que se cambia | `6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c` | `items[].id` de la [API 18](#18-consultar-los-precios-vigentes) (lista los precios vigentes; errores en §18) o `id` de la [API 17](#17-registrar-un-precio-de-venta) (registra el precio; errores en §17) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "unit_price": "9000.00",
  "effective_from": null,
  "version": 1
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `unit_price` | número o texto decimal ≥ 0 | Sí | Nuevo precio; como máximo los decimales de la moneda | `9000.00` | Formulario |
| `effective_from` | date-time con zona \| null | No; por defecto el instante del servidor | Desde cuándo rige el nuevo precio; actual o futuro, dentro de la vigencia del actual | `null` | Formulario |
| `version` | integer ≥ 1 | Sí | Versión vigente del precio actual | `1` | `items[].version` de la [API 18](#18-consultar-los-precios-vigentes) (lista los precios vigentes; errores en §18) |

### Respuesta exitosa

`201 Created` (`PriceChangeResponse`), con cabecera `Location: /api/v1/price-list-items/{id del precio nuevo}`:

```json
{
  "item": {
    "id": "8b9c0d1e-2f3a-4b4c-9d5e-6f7a8b9c0d1e",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "ACTIVE",
    "version": 1,
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "created_at": "2026-10-20T15:00:00Z",
    "updated_at": "2026-10-20T15:00:00Z",
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "unit_price": "9000.00",
    "currency_code": "COP",
    "valid_from": "2026-10-20T15:00:00Z",
    "valid_to": null,
    "origin": null,
    "closure_reason": null,
    "automatic_application_id": null
  },
  "previous": {
    "id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "ACTIVE",
    "version": 2,
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-20T15:00:00Z",
    "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
    "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
    "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "unit_price": "8500.00",
    "currency_code": "COP",
    "valid_from": "2026-10-20T00:00:00Z",
    "valid_to": "2026-10-20T15:00:00Z",
    "origin": null,
    "closure_reason": null,
    "automatic_application_id": null
  }
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `item` | `PriceListItemResponse` | El precio nuevo; su `id` es el que se usa desde ahora |
| `previous` | `PriceListItemResponse` | El precio anterior con `valid_to` igual al inicio del nuevo y `version` incrementada |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El precio no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de precios |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente (por ejemplo, otra persona o una actualización automática lo cambió) | Releer con la [API 18](#18-consultar-los-precios-vigentes) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION` | El precio está `INACTIVE` | Registrar un precio nuevo con la [API 17](#17-registrar-un-precio-de-venta) |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_CHANGE_OUT_OF_PERIOD` | `effective_from` pasado, no posterior al inicio del precio (precio aún futuro) o no anterior a su fin | Para un precio futuro usar la [API 20](#20-corregir-un-precio-futuro-o-cerrar-uno-vigente); si no, corregir la fecha |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_ITEM_WITHOUT_PRESENTATION` | Precio antiguo sin presentación | Registrar el precio de la presentación con la [API 17](#17-registrar-un-precio-de-venta) |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_LIST_NOT_FOUND` / `PRICE_LIST_INACTIVE` | La lista ya no existe o está inactiva | Informar; no se puede cambiar el precio |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_NOT_FOUND` / `COMPANY_PRODUCT_INACTIVE` | El producto ya no está activo | Informar |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_INACTIVE` | La presentación está inactiva | Informar |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_SCALE_NOT_ALLOWED` | El nuevo precio tiene más decimales que la moneda | Redondear en la interfaz |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden cambiar precios |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `unit_price` ausente o negativo, `version` < 1, fecha sin zona, campo desconocido | Corregir la solicitud |

Ejemplo de `422`:

```json
{
  "type": "https://sio/errors/commercial-relationship/price-change-out-of-period",
  "title": "Cambio de precio fuera de vigencia",
  "status": 422,
  "detail": "El instante de efecto debe ser actual o futuro y estar dentro de la vigencia del precio actual.",
  "instance": "/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c/change-price",
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_CHANGE_OUT_OF_PERIOD",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "effective_from",
      "message": "El instante de efecto debe ser actual o futuro y estar dentro de la vigencia del precio actual.",
      "code": "PRICE_CHANGE_OUT_OF_PERIOD"
    }
  ]
}
```

## 20. Corregir un precio futuro o cerrar uno vigente

**Método:** `PUT`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/{price_list_item_id}`
**Permiso requerido:** `perm:commercial-relationship:price_list_items:update`

### ¿Qué hace esta API?

Modifica un precio. Un precio **futuro** (su `valid_from` aún no llega) admite cambiar valor e inicio y fin de vigencia. Un precio **en vigencia** solo admite cambiar su `valid_to`: adelantarlo o posponerlo a un instante futuro, o dejarlo sin fin; su valor y su inicio no cambian (para eso, [API 19](#19-cambiar-un-precio-vigente)). La lista, el producto, la presentación, la empresa y el `status` son inmutables.

Reglas verificadas en el código, en este orden: (1) la `version` debe ser la vigente; (2) un precio cerrado o cancelado por una actualización automática no se modifica; (3) el precio no puede tener más decimales que la moneda; (4) en vigencia, cambiar `unit_price` o `valid_from` responde `422 PRICE_IN_EFFECT_NOT_MODIFIABLE` y el nuevo `valid_to` debe ser futuro y posterior al inicio; en un precio futuro, `valid_to` posterior a `valid_from`; (5) la nueva vigencia no puede cruzarse con otro precio activo. Si no hay cambios no escribe; si los hay registra `UPDATE_PRICE_LIST_ITEM` en Audit.

Antes necesita: el `price_list_item_id` y su `version` ([API 18](#18-consultar-los-precios-vigentes)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

Cerrar un precio en vigencia (se repiten su valor e inicio):

```bash
curl -X PUT \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "unit_price": "8500.00",
    "valid_from": "2026-10-20T00:00:00Z",
    "valid_to": "2026-12-31T23:59:59Z"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `price_list_item_id` | UUID | Sí | Precio a modificar | `6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c` | `items[].id` de la [API 18](#18-consultar-los-precios-vigentes) (lista los precios; errores en §18) o `id` de la [API 17](#17-registrar-un-precio-de-venta) (registra el precio; errores en §17) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "unit_price": "8500.00",
  "valid_from": "2026-10-20T00:00:00Z",
  "valid_to": "2026-12-31T23:59:59Z"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente del precio | `1` | `items[].version` de la [API 18](#18-consultar-los-precios-vigentes) (lista los precios; errores en §18) |
| `unit_price` | número o texto decimal ≥ 0 | Sí | Valor final; en un precio en vigencia debe ser igual al actual | `8500.00` | Formulario (repetir `unit_price` de la [API 18](#18-consultar-los-precios-vigentes) si el precio está en vigencia) |
| `valid_from` | date-time con zona | Sí | Inicio final; en un precio en vigencia debe ser igual al actual | `2026-10-20T00:00:00Z` | Formulario (repetir `valid_from` de la [API 18](#18-consultar-los-precios-vigentes) si el precio está en vigencia) |
| `valid_to` | date-time con zona \| null | No; omitirlo lo deja sin fin | Fin final; en un precio en vigencia, futuro | `2026-12-31T23:59:59Z` | Formulario |

No se admiten en el cuerpo `price_list_id`, `company_product_id`, `company_product_presentation_id`, `company_id` ni `status`: su presencia responde `422 IMMUTABLE_FIELD`.

### Respuesta exitosa

`200 OK` (`PriceListItemResponse`), mismo objeto que la [API 17](#17-registrar-un-precio-de-venta), con los valores finales y `version` incrementada si hubo cambios:

```json
{
  "id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T15:00:00Z",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "unit_price": "8500.00",
  "currency_code": "COP",
  "valid_from": "2026-10-20T00:00:00Z",
  "valid_to": "2026-12-31T23:59:59Z",
  "origin": null,
  "closure_reason": null,
  "automatic_application_id": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `valid_to` | date-time \| null | Nuevo fin de la vigencia |
| `version` | integer | Nueva versión; se mantiene si no hubo cambios |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El precio no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de precios |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 18](#18-consultar-los-precios-vigentes) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.PRICE_CLOSED_BY_AUTOMATIC_UPDATE` | El precio fue cerrado o cancelado por una actualización automática | Registrar un precio nuevo con la [API 17](#17-registrar-un-precio-de-venta) si corresponde |
| `409` | `COMMERCIAL_RELATIONSHIP.PRICE_PERIOD_OVERLAP` | La nueva vigencia se cruza con otro precio activo | Ajustar las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_IN_EFFECT_NOT_MODIFIABLE` | Se intentó cambiar `unit_price` o `valid_from` de un precio en vigencia | Usar la [API 19](#19-cambiar-un-precio-vigente) |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no posterior a `valid_from` o, en un precio en vigencia, no futuro | Corregir la fecha |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_SCALE_NOT_ALLOWED` | El precio tiene más decimales que la moneda | Redondear en la interfaz |
| `422` | `COMMERCIAL_RELATIONSHIP.IMMUTABLE_FIELD` | El cuerpo incluye un campo inmutable | Error de programación: no enviarlo |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar precios |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, precio negativo, fecha sin zona, campo desconocido | Corregir la solicitud |

Ejemplo de `422`:

```json
{
  "type": "https://sio/errors/commercial-relationship/price-in-effect-not-modifiable",
  "title": "Precio en vigencia",
  "status": 422,
  "detail": "El precio ya está en vigencia: solo puede cerrarse o cambiarse con la acción change-price.",
  "instance": "/api/v1/price-list-items/6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_IN_EFFECT_NOT_MODIFIABLE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "unit_price",
      "message": "El precio ya está en vigencia: solo puede cerrarse o cambiarse con la acción change-price.",
      "code": "PRICE_IN_EFFECT_NOT_MODIFIABLE"
    }
  ]
}
```

## 21. Crear una política de ganancia

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies`
**Permiso requerido:** `perm:commercial-relationship:pricing_policies:create`

### ¿Qué hace esta API?

Define que un grupo de presentaciones de una lista se venda al costo de compra más un porcentaje. Cuando se recibe una compra de esas presentaciones, Commercial Relationship calcula y registra el precio nuevo en la lista de forma automática. Compras exige que cada presentación comprada tenga política en una lista vigente de su moneda, aunque el porcentaje sea `0`.

Reglas verificadas en el código, en este orden: (1) `markup_percentage` de 0 a 1000 con hasta 4 decimales, sin redondeo; (2) las presentaciones (sin repetir, máximo 100) deben ser de la empresa, `ACTIVE` y vendibles; (3) la lista debe ser de la empresa (`404` si no) y estar `ACTIVE`; (4) el nombre no puede repetir el de otra política activa de la lista; (5) ninguna presentación puede pertenecer ya a otra política de la misma lista. Crea la política `ACTIVE`, abre su primer término de porcentaje y las asignaciones, devuelve `Location: /api/v1/pricing-policies/{id}` y registra `CREATE_PRICING_POLICY` en Audit. **No modifica ningún precio**: rige desde la siguiente recepción de compra.

Antes necesita: la lista `ACTIVE` ([API 15](#15-consultar-las-listas-de-precios-de-la-empresa)) y las presentaciones vendibles ([API 12](#12-consultar-las-presentaciones-de-la-empresa)); empresa `ACTIVE`. Se puede crear sin presentaciones y asignarlas después con la [API 23](#23-asignar-presentaciones-a-una-política).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Margen general 30 %",
    "markup_percentage": "30",
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `price_list_id` | UUID | Sí | Lista `ACTIVE` de la empresa a la que pertenece la política | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) · guía [price_list_id](../parametros/price-list-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "name": "Margen general 30 %",
  "markup_percentage": "30",
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `name` | string (1–120) | Sí | Nombre de la política; único entre las políticas activas de la lista | `Margen general 30 %` | Formulario |
| `markup_percentage` | número o texto decimal (0–1000, hasta 4 decimales) | Sí | Recargo porcentual sobre el costo de compra; `0` es válido | `30` | Formulario |
| `company_product_presentation_ids` | UUID[] (0–100 distintos) | No; por defecto `[]` | Presentaciones `ACTIVE` y vendibles que no estén en otra política de la lista | `["a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"]` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) con `is_sellable=true` (lista las presentaciones; errores en §12) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |

### Respuesta exitosa

`201 Created` (`PricingPolicyResponse`), con cabecera `Location: /api/v1/pricing-policies/{id}`:

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
  "markup_percentage": "30.0000",
  "presentation_count": 1,
  "deactivated_at": null,
  "deactivation_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `id` | UUID | El nuevo [policy_id](../parametros/pricing-policy-id.md) que usan las API 23, 24 y 25 |
| `markup_percentage` | string | Porcentaje vigente con 4 decimales |
| `presentation_count` | integer | Presentaciones asignadas vigentes |
| `deactivated_at`, `deactivation_reason` | fecha, string \| null | Se informan al inactivar la política (CR 70, estado final) |
| `status`, `version` | — | `ACTIVE` y `1` al crear |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe, el usuario no tiene membresía `ACTIVE` o la lista no es de la empresa | Volver a cargar las listas |
| `409` | `COMMERCIAL_RELATIONSHIP.POLICY_NAME_DUPLICATE` | Ya existe una política activa con ese nombre en la lista | Pedir otro nombre |
| `409` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY` | Alguna presentación ya pertenece a otra política de la misma lista | Retirarla de la otra política con la [API 24](#24-retirar-presentaciones-de-una-política) o no incluirla |
| `422` | `COMMERCIAL_RELATIONSHIP.MARKUP_PERCENTAGE_OUT_OF_RANGE` | Porcentaje negativo, mayor que 1000, con más de 4 decimales o no numérico | Corregir el porcentaje |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | La lista está `INACTIVE` | Elegir una lista activa |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_FOUND` / `PRESENTATION_INACTIVE` / `PRESENTATION_NOT_SELLABLE` | Alguna presentación no es de la empresa, está inactiva o no es vendible | Volver a cargar las presentaciones vendibles |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Dividir en varias llamadas a la [API 23](#23-asignar-presentaciones-a-una-política) |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear políticas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Nombre vacío o > 120, UUID inválido, campo desconocido | Corregir el formulario |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/presentation-already-in-policy",
  "title": "Presentación ya asignada",
  "status": 409,
  "detail": "La presentación ya pertenece a otra política de la misma lista de precios.",
  "instance": "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies",
  "code": "COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 22. Consultar las políticas de una lista

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies`
**Permiso requerido:** `perm:commercial-relationship:pricing_policies:read`

### ¿Qué hace esta API?

Lista, con paginación, las políticas de ganancia de una lista con su porcentaje vigente y cuántas presentaciones cubren. Es la fuente de `policy_id`. Las presentaciones de una política se consultan con CR 66 y el historial de porcentajes con CR 65. Solo la ven administradores y supervisores: expone porcentajes internos y no admite la exención técnica.

Antes necesita: `company_id` con membresía `ACTIVE` y el `price_list_id`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies?status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |
| `price_list_id` | UUID | Sí | Lista cuyas políticas se consultan | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) · guía [price_list_id](../parametros/price-list-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | No; por defecto `ACTIVE` | Estado de las políticas | Uno de: `ACTIVE` (por defecto), `INACTIVE`, `ALL`; p. ej. `ACTIVE` | `?status=ACTIVE` | Interfaz |
| `search` | string (≤ 100) | No | Búsqueda parcial en el nombre | Texto libre; p. ej. `margen` | `&search=margen` | Interfaz |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies?status=ACTIVE&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[PricingPolicyResponse]`):

```json
{
  "items": [
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
      "markup_percentage": "30.0000",
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

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].id` | UUID | El [policy_id](../parametros/pricing-policy-id.md) |
| `items[].markup_percentage` | string \| null | Porcentaje vigente; en una política inactiva, el último que tuvo |
| `items[].presentation_count` | integer | Presentaciones vigentes de la política |
| `items[].version` | integer | Valor que deben enviar las API 23, 24 y 25 |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `price_list_id` no es UUID, `status` fuera de la enumeración, `search` > 100, paginación fuera de rango | Corregir los filtros |

## 23. Asignar presentaciones a una política

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations`
**Permiso requerido:** `perm:commercial-relationship:pricing_policies:update`

### ¿Qué hace esta API?

Incorpora hasta 100 presentaciones a una política. Las que ya pertenecen a la política se ignoran; si ninguna es nueva no escribe ni incrementa `version`. No modifica precios: desde la siguiente recepción de compra el precio de esas presentaciones en la lista se calcula con el porcentaje de la política.

Reglas verificadas en el código: las presentaciones (sin repetir) deben ser de la empresa, `ACTIVE` y vendibles; la `version` debe ser la vigente; la política debe estar `ACTIVE` (una inactiva es final); ninguna presentación puede estar en otra política de la misma lista. Registra `ASSIGN_PRICING_POLICY_PRESENTATION` en Audit con las presentaciones asignadas.

Antes necesita: el `policy_id` y su `version` ([API 22](#22-consultar-las-políticas-de-una-lista)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "company_product_presentation_ids": [
      "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `policy_id` | UUID | Sí | Política `ACTIVE` | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas de la lista; errores en §22) o `id` de la [API 21](#21-crear-una-política-de-ganancia) (crea la política; errores en §21) · guía [policy_id](../parametros/pricing-policy-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 1,
  "company_product_presentation_ids": [
    "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la política | `1` | `items[].version` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas; errores en §22) |
| `company_product_presentation_ids` | UUID[] (hasta 100 distintos) | Sí | Presentaciones `ACTIVE` y vendibles de la empresa | `["b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"]` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) con `is_sellable=true` (lista las presentaciones; errores en §12) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |

### Respuesta exitosa

`200 OK` (`PricingPolicyResponse`) con `presentation_count` y `version` actualizados:

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 2,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T09:30:00Z",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "name": "Margen general 30 %",
  "markup_percentage": "30.0000",
  "presentation_count": 2,
  "deactivated_at": null,
  "deactivation_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `presentation_count` | integer | Presentaciones vigentes después de asignar |
| `version` | integer | Nueva versión; se mantiene si todas ya estaban asignadas |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La política no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de políticas |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer con la [API 22](#22-consultar-las-políticas-de-una-lista) y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE` | La política está inactiva (estado final) | Crear otra política con la [API 21](#21-crear-una-política-de-ganancia) |
| `409` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY` | Alguna presentación ya está en otra política de la misma lista | Retirarla primero con la [API 24](#24-retirar-presentaciones-de-una-política) |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_FOUND` / `PRESENTATION_INACTIVE` / `PRESENTATION_NOT_SELLABLE` | Alguna presentación no es de la empresa, está inactiva o no es vendible | Volver a cargar las presentaciones vendibles |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Dividir en varias llamadas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar políticas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente o < 1, UUID inválido, campo desconocido | Corregir la solicitud |

## 24. Retirar presentaciones de una política

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations/remove`
**Permiso requerido:** `perm:commercial-relationship:pricing_policies:update`

### ¿Qué hace esta API?

Retira hasta 100 presentaciones de una política cerrando su vigencia en ella. No toca los precios actuales: desde la siguiente recepción de compra esas presentaciones quedan sin política en la lista (resultado `SKIPPED_NO_POLICY` en la [API 27](#27-consultar-las-actualizaciones-automáticas-de-precio)) y, si no tienen política en otra lista vigente de la moneda, Compras no confirmará compras de ellas. Se usa también para mover una presentación a otra política de la misma lista: retirarla aquí y asignarla allá con la [API 23](#23-asignar-presentaciones-a-una-política).

Reglas verificadas en el código: la lista no puede estar vacía y **todas** las presentaciones enviadas deben pertenecer hoy a la política; si alguna no, no retira ninguna (`409 PRESENTATION_NOT_IN_POLICY`); la política debe estar `ACTIVE` y la `version` ser la vigente. Registra `UNASSIGN_PRICING_POLICY_PRESENTATION` en Audit.

Antes necesita: el `policy_id`, su `version` ([API 22](#22-consultar-las-políticas-de-una-lista)) y las presentaciones vigentes de la política (CR 66); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations/remove' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 2,
    "company_product_presentation_ids": [
      "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `policy_id` | UUID | Sí | Política `ACTIVE` | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas de la lista; errores en §22) · guía [policy_id](../parametros/pricing-policy-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 2,
  "company_product_presentation_ids": [
    "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la política | `2` | `items[].version` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas; errores en §22) |
| `company_product_presentation_ids` | UUID[] (1–100 distintos) | Sí | Presentaciones que hoy pertenecen a la política | `["b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"]` | `items[].company_product_presentation_id` de `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/presentations` (lista las presentaciones vigentes de la política; permiso `perm:commercial-relationship:pricing_policies:read`; errores `404 NOT_FOUND` si la política no es accesible y `422 VALIDATION_ERROR` por paginación inválida; ficha [CR 66](../servicios/commercial-relationship.md#66-get-pricing-policiespolicy_idpresentations)) |

### Respuesta exitosa

`200 OK` (`PricingPolicyResponse`) con `presentation_count` y `version` actualizados:

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 3,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T10:00:00Z",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "name": "Margen general 30 %",
  "markup_percentage": "30.0000",
  "presentation_count": 1,
  "deactivated_at": null,
  "deactivation_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `presentation_count` | integer | Presentaciones vigentes después de retirar |
| `version` | integer | Nueva versión |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La política no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de políticas |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE` | La política está inactiva | Nada que retirar |
| `409` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_IN_POLICY` | La lista está vacía o alguna presentación no pertenece a la política | Volver a cargar las presentaciones de la política (CR 66) |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Dividir en varias llamadas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar políticas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente o < 1, UUID inválido, campo desconocido | Corregir la solicitud |

Ejemplo de `409`:

```json
{
  "type": "https://sio/errors/commercial-relationship/presentation-not-in-policy",
  "title": "Presentación no asignada",
  "status": 409,
  "detail": "La presentación no pertenece a la política.",
  "instance": "/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/presentations/remove",
  "code": "COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_IN_POLICY",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "company_product_presentation_ids",
      "message": "La presentación no pertenece a la política.",
      "code": "PRESENTATION_NOT_IN_POLICY"
    }
  ]
}
```

## 25. Cambiar el porcentaje de una política

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/{policy_id}/percentage`
**Permiso requerido:** `perm:commercial-relationship:pricing_policies:update`

### ¿Qué hace esta API?

Cambia el porcentaje de ganancia de una política. Cierra el término vigente y abre uno nuevo desde el instante del servidor; el historial se consulta con CR 65. **No recalcula ningún precio**: los precios actuales se conservan y el porcentaje nuevo se aplica en la siguiente recepción de compra de cada presentación. Si se necesita el precio nuevo de inmediato hay que cambiarlo a mano con la [API 19](#19-cambiar-un-precio-vigente).

Reglas verificadas en el código: porcentaje de 0 a 1000 con hasta 4 decimales; la política debe estar `ACTIVE` y la `version` ser la vigente; si el porcentaje es igual al vigente no escribe ni incrementa `version`. Registra `CHANGE_PRICING_POLICY_PERCENTAGE` en Audit con el porcentaje anterior y el nuevo.

Antes necesita: el `policy_id` y su `version` ([API 22](#22-consultar-las-políticas-de-una-lista)); empresa `ACTIVE`.

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/percentage' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 3,
    "markup_percentage": "35"
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `policy_id` | UUID | Sí | Política `ACTIVE` | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` | `items[].id` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas de la lista; errores en §22) · guía [policy_id](../parametros/pricing-policy-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "version": 3,
  "markup_percentage": "35"
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `version` | integer ≥ 1 | Sí | Versión vigente de la política | `3` | `items[].version` de la [API 22](#22-consultar-las-políticas-de-una-lista) (lista las políticas; errores en §22) |
| `markup_percentage` | número o texto decimal (0–1000, hasta 4 decimales) | Sí | Nuevo porcentaje; `0` es válido | `35` | Formulario |

### Respuesta exitosa

`200 OK` (`PricingPolicyResponse`) con el porcentaje nuevo:

```json
{
  "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "version": 4,
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-20T11:00:00Z",
  "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
  "name": "Margen general 30 %",
  "markup_percentage": "35.0000",
  "presentation_count": 1,
  "deactivated_at": null,
  "deactivation_reason": null
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `markup_percentage` | string | Porcentaje vigente desde ahora |
| `version` | integer | Nueva versión; se mantiene si el porcentaje no cambió |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La política no existe o es de una empresa sin membresía `ACTIVE` | Volver a la lista de políticas |
| `409` | `COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente | Releer y repetir |
| `409` | `COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE` | La política está inactiva | Crear otra política |
| `422` | `COMMERCIAL_RELATIONSHIP.MARKUP_PERCENTAGE_OUT_OF_RANGE` | Porcentaje negativo, mayor que 1000, con más de 4 decimales o no numérico | Corregir el porcentaje |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden modificar políticas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `version` ausente o < 1, campo desconocido | Corregir la solicitud |

Ejemplo de `422`:

```json
{
  "type": "https://sio/errors/commercial-relationship/markup-percentage-out-of-range",
  "title": "Porcentaje de ganancia inválido",
  "status": 422,
  "detail": "El porcentaje de ganancia debe estar entre 0 y 1000, con hasta 4 decimales.",
  "instance": "/api/v1/pricing-policies/7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d/percentage",
  "code": "COMMERCIAL_RELATIONSHIP.MARKUP_PERCENTAGE_OUT_OF_RANGE",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "markup_percentage",
      "message": "El porcentaje de ganancia debe estar entre 0 y 1000, con hasta 4 decimales.",
      "code": "MARKUP_PERCENTAGE_OUT_OF_RANGE"
    }
  ]
}
```

## 26. Verificar la cobertura de políticas

**Método:** `POST`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/pricing-policies/coverage`
**Permiso requerido:** `perm:commercial-relationship:pricing_policy_coverage:read`

### ¿Qué hace esta API?

Indica, para hasta 100 presentaciones y una moneda, si cada una tiene una política de ganancia aplicable en ese instante (en una lista activa y vigente de esa moneda) y en qué listas. Es la misma comprobación que hace Purchase al confirmar una compra: una presentación con `covered: false` hará fallar la confirmación con `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED`. Solo informa cobertura: **nunca** porcentajes, costos ni políticas.

Efectos verificados en el código: quita los identificadores repetidos y responde en el mismo orden; una presentación que no existe o es de otra empresa responde `found: false` (sin error); exige membresía `ACTIVE` pero no empresa activa; no escribe nada.

Antes necesita: `company_id` con membresía `ACTIVE`, la moneda de la compra y las presentaciones ([API 12](#12-consultar-las-presentaciones-de-la-empresa)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/pricing-policies/coverage' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "currency_code": "COP",
    "company_product_presentation_ids": [
      "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
    ]
  }'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:** `Authorization` (obligatorio) y `Content-Type: application/json` (obligatorio).

**Cuerpo de la solicitud:** ver la sección siguiente.

### Cuerpo de la solicitud (Body)

```json
{
  "currency_code": "COP",
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
    "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94"
  ]
}
```

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `currency_code` | string (código ISO 4217) | Sí | Moneda de la compra; se normaliza a mayúsculas | `COP` | `currency_code` de la compra en [Compras](compras.md) o del producto ([API 9](#9-buscar-y-listar-los-productos-de-la-empresa)) |
| `company_product_presentation_ids` | UUID[] (1–100 distintos) | Sí | Presentaciones a verificar | `["a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"]` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) (lista las presentaciones; errores en §12) o `lines[].company_product_presentation_id` de la compra · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |

### Respuesta exitosa

`200 OK` (`CoverageResponse`):

```json
{
  "items": [
    {
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "found": true,
      "covered": true,
      "price_list_ids": ["5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b"]
    },
    {
      "company_product_presentation_id": "b6c7d8e9-f0a1-4b2c-8d3e-4f5a6b7c8d94",
      "found": true,
      "covered": false,
      "price_list_ids": []
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `items[].found` | boolean | `false` si la presentación no existe en la empresa |
| `items[].covered` | boolean | `true` si tiene política aplicable en alguna lista vigente de la moneda |
| `items[].price_list_ids[]` | UUID[] | Listas donde está cubierta; vacío si no lo está |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | Moneda fuera de la lista admitida | Corregir la moneda |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Dividir la consulta |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Lista vacía, UUID inválido, campo desconocido | Corregir la solicitud |

## 27. Consultar las actualizaciones automáticas de precio

**Método:** `GET`
**URL:** `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/automatic-price-applications`
**Permiso requerido:** `perm:commercial-relationship:automatic_price_applications:read`

### ¿Qué hace esta API?

Lista, con paginación, el resultado de cada actualización automática de precio: una por línea de compra recibida y lista de precios. Muestra el costo usado, el porcentaje aplicado, el precio anterior y el nuevo. El cálculo lo hace un proceso asíncrono de Commercial Relationship después de la recepción, por lo que el precio nuevo puede tardar unos segundos en aparecer. Solo la ven administradores y supervisores porque expone costos y porcentajes.

Estados posibles: `PENDING` (aún no procesada), `FAILED` (falló y se reintentará; ver `attempts`, `next_attempt_at` y `last_error_code`) y los finales `APPLIED`, `UNCHANGED`, `SKIPPED_NO_POLICY`, `SKIPPED_LIST_NOT_EFFECTIVE`, `SKIPPED_CURRENCY_MISMATCH`, `SKIPPED_PRESENTATION_INACTIVE`, `SKIPPED_ZERO_COST` y `RESOLVED`. Una `PENDING` o `FAILED` puede cerrarse administrativamente con CR 74, sin modificar precios.

Antes necesita: `company_id` con membresía `ACTIVE`; normalmente el `purchase_id` de la compra recibida ([Compras](compras.md)).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-applications?purchase_id=4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:**

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `company_id` | UUID | Sí | Empresa | `550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la [API 5 de Acceso y contexto operativo](acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario) (devuelve las empresas y sucursales del usuario; sus errores están en esa sección) o `items[].id` de la [API 2 de Administración empresarial](administracion-empresarial.md#2-consultar-las-empresas-del-usuario) (lista las empresas del usuario; errores en esa sección) · guía [company_id](../parametros/company-id.md) |

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `purchase_id` | UUID | No | Solo las de esa compra | UUID de una compra; p. ej. `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `?purchase_id=4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` | `id` de la compra recibida en [Compras](compras.md) · guía [purchase_id](../parametros/purchase-id.md) |
| `status` | enum | No; sin valor devuelve todas | Estado de la aplicación | Uno de: `PENDING`, `FAILED`, `APPLIED`, `UNCHANGED`, `SKIPPED_NO_POLICY`, `SKIPPED_LIST_NOT_EFFECTIVE`, `SKIPPED_CURRENCY_MISMATCH`, `SKIPPED_PRESENTATION_INACTIVE`, `SKIPPED_ZERO_COST`, `RESOLVED`; p. ej. `FAILED` | `&status=FAILED` | Interfaz |
| `price_list_id` | UUID | No | Solo las de esa lista | UUID de una lista; p. ej. `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `&price_list_id=5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` | `items[].id` de la [API 15](#15-consultar-las-listas-de-precios-de-la-empresa) (lista las listas de precios; errores en §15) · guía [price_list_id](../parametros/price-list-id.md) |
| `company_product_presentation_id` | UUID | No | Solo las de esa presentación | UUID de una presentación; p. ej. `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `&company_product_presentation_id=a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` | `items[].id` de la [API 12](#12-consultar-las-presentaciones-de-la-empresa) (lista las presentaciones; errores en §12) · guía [company_product_presentation_id](../parametros/company-product-presentation-id.md) |
| `page` | integer ≥ 1 | No; por defecto `1` | Página | Entero desde `1`; p. ej. `1` | `&page=1` | Interfaz |
| `page_size` | integer 1–100 | No; por defecto `20` | Registros por página | Entero de `1` a `100`; p. ej. `20` | `&page_size=20` | Interfaz |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/automatic-price-applications?purchase_id=4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e&page=1&page_size=20`

**Encabezados:** `Authorization` (obligatorio) y `Accept: application/json` (opcional).

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`PaginatedResponse[AutomaticPriceApplicationResponse]`):

```json
{
  "items": [
    {
      "id": "9d0e1f2a-3b4c-4d5e-8f6a-7b8c9d0e1f2a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "request_id": "f68d2c36-58a2-4018-8437-29b214bc84c9",
      "purchase_id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "purchase_detail_id": "5c6d7e8f-9a0b-4c1d-8e2f-3a4b5c6d7e8f",
      "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "sequence": 2,
      "received_at": "2026-10-20T14:00:00Z",
      "received_by_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "policy_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
      "markup_percentage": "30.0000",
      "current_unit_cost": "7000",
      "previous_unit_cost": "6500",
      "reference_cost": "7000",
      "previous_price": "8500.00",
      "new_price": "9100.00",
      "previous_price_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
      "new_price_item_id": "8b9c0d1e-2f3a-4b4c-9d5e-6f7a8b9c0d1e",
      "cancelled_future_item_ids": [],
      "status": "APPLIED",
      "attempts": 1,
      "next_attempt_at": null,
      "last_error_code": null,
      "first_attempt_at": "2026-10-20T14:00:05Z",
      "completed_at": "2026-10-20T14:00:05Z",
      "resolved_by": null,
      "resolution_reason": null,
      "version": 2,
      "created_at": "2026-10-20T14:00:01Z",
      "updated_at": "2026-10-20T14:00:05Z"
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
| `items[].status` | enum | Resultado de la actualización (ver la lista de estados arriba) |
| `items[].price_list_id`, `company_product_presentation_id` | UUID | Lista y presentación cuyo precio se evaluó |
| `items[].markup_percentage`, `policy_id` | string, UUID \| null | Porcentaje y política vigentes en `received_at`; `null` si no había política |
| `items[].current_unit_cost`, `previous_unit_cost`, `reference_cost` | string \| null | Costo de esta recepción, costo de la anterior y costo usado para calcular |
| `items[].previous_price`, `new_price` | string \| null | Precio antes y después, con los decimales de la moneda |
| `items[].new_price_item_id`, `previous_price_item_id`, `cancelled_future_item_ids[]` | UUID \| null, UUID[] | Precio creado, precio cerrado y precios futuros cancelados |
| `items[].attempts`, `next_attempt_at`, `last_error_code` | integer, fecha, string \| null | Seguimiento de reintentos en `FAILED` |
| `items[].version` | integer | Valor que pide la resolución administrativa (CR 74) |
| `page`, `page_size`, `total_records`, `total_pages` | integer | Paginación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `status` fuera de la enumeración, UUID inválido, paginación fuera de rango | Corregir los filtros |

## Dependencias con otros módulos

- [Compras](compras.md) necesita productos y presentaciones comprables, la tasa de impuesto de compra de cada producto ([API 13](#13-configurar-el-impuesto-de-compra-del-producto)) y política de ganancia para cada presentación comprada ([API 21](#21-crear-una-política-de-ganancia), comprobable con la [API 26](#26-verificar-la-cobertura-de-políticas)); sin ellas la confirmación responde `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` o `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED`. Sus recepciones disparan los precios automáticos ([API 27](#27-consultar-las-actualizaciones-automáticas-de-precio)).
- [Ventas](ventas.md) necesita presentaciones vendibles con precio vigente en al menos una lista vigente. La interfaz lista los precios con la [API 18](#18-consultar-los-precios-vigentes) ordenados de mayor a menor, el vendedor elige uno y la línea envía su `price_list_id` explícito; nunca `unit_price`.
- [Inventario](inventario.md): Product Inventory Query muestra los productos de la empresa con el precio de la lista indicada o de la predeterminada, junto con las existencias; Inventory controla existencias solo de productos con `inventory_control_enabled: true` y lotes y vencimientos según las banderas de la [API 8](#8-adoptar-un-producto-global-en-la-empresa).
- [Gestión de proveedores](gestion-de-proveedores.md): los productos de proveedor se asocian a los productos y presentaciones de la empresa creados aquí.
- La trazabilidad de las escrituras de este módulo se consulta en la [API 16 de Administración empresarial](administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría) y el historial de un producto en la [API 17 de Administración empresarial](administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto) con `entity_type=CompanyProduct`.

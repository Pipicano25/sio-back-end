# Product Catalog API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Product Catalog es el **catálogo global de productos** de SIO, compartido por todas las empresas: productos con su nombre canónico, marca, unidad base, categorías, atributos, presentaciones (unidades de venta y compra), identificadores (códigos de barras), grupos e imágenes. Una empresa no vende productos globales directamente: los **adopta** en Commercial Relationship ([company_product_id](../parametros/company-product-id.md)). El frontend usa este servicio para buscar en el catálogo, leer datos descriptivos, escanear códigos de barras y, con perfil de administración, mantener los catálogos.

## Responsabilidad

- Catálogos auxiliares globales: unidades de medida, tipos de empaque, marcas, categorías jerárquicas con atributos asociados, definiciones de atributo con opciones, tipos de grupo y grupos.
- Productos globales y sus subrecursos: categorías, valores de atributo, presentaciones, identificadores, grupos y activos (imágenes y documentos).
- Completitud y elegibilidad para adopción; marca irreversible de **primer uso** cuando una empresa adopta un producto.
- Entrega de imágenes: contenido del activo con autenticación y, si está habilitada, una ruta pública firmada para `<img src>`.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-product-catalog-dev.onrender.com/api/v1` |
| Salud | `https://sio-product-catalog-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-product-catalog-dev.onrender.com/docs) · [/openapi.json](https://sio-product-catalog-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `PRODUCT_CATALOG.*` y `trace_id`; `400 MALFORMED_REQUEST` también para parámetros de ruta o consulta no interpretables; `409 CONFLICT` genérico además de `VERSION_CONFLICT` |
| Operaciones en el contrato desplegado | 104 (102 de negocio + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/product-catalog-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`. Permisos `perm:product-catalog:{recurso}:{accion}`. Este servicio usa la acción **`deactivate`** (no `delete`) para inactivar y reactivar; los comodines `perm:all:all:read|create|update` de `supervisores` **no** la cubren.

| Recurso | Operaciones | Acciones usadas | Grupos con lectura (plantilla) | Grupos con escritura |
|---|---|---|---|---|
| `units-of-measure` | 3–9 | `read`, `create`, `update`, `deactivate` | Todos (`compras`, `ventas`, `inventario` vía `perm:product-catalog:all:read`; `reportes`, `consulta` por recurso) | `administradores`; `supervisores` solo `create` y `update` |
| `packaging-types` | 10–15 | ídem | Todos | ídem |
| `brands` | 16–21 | ídem | Todos | ídem |
| `categories` | 22–35 | `read`, `update` (crear, modificar, asociar atributos), `deactivate` | Todos | ídem |
| `attribute-definitions` | 36–46 | `read`, `update` (crear, opciones), `deactivate` | Todos | ídem |
| `products` | 47–58, 59–62, 63–65, 66–72, 73–77, 78–81, 92–98 (subrecursos) | `read`, `create`, `update`, `deactivate`, `delete` (solo borrar un valor de atributo) | Todos | `administradores`; `supervisores` sin `deactivate` ni `delete` |
| `group-types` | 82–91 (tipos y grupos) | `read`, `create`, `update`, `deactivate` | Todos | ídem |
| `first-use` | 99–100 | `register` (cuentas técnicas), `register-manual` (administradores) | — | Cuenta técnica de Commercial Relationship (`register`); `administradores` (`register-manual` vía `perm:all:all:all`) |

Los subrecursos de producto (categorías, atributos, presentaciones, identificadores, grupos, activos) usan el recurso `products`: crear o modificar exige `products:update`; inactivar o reactivar, `products:deactivate`.

## Alcance de datos

Global: cualquier usuario con el permiso ve todo el catálogo; no hay membresía. Las escrituras afectan a **todas las empresas**. El fabricante (`manufacturer_organization_id`) se valida en Party Identity con el token del usuario (`422 MANUFACTURER_NOT_FOUND`, `403 MANUFACTURER_ACCESS_DENIED`).

## Convenciones comunes

- Listas paginadas (`page` ≥ 1, `page_size` 1–100, por defecto 20) con `items`, `page`, `page_size`, `total_records`, `total_pages`. Filtros comunes: `status` (`ACTIVE` o `INACTIVE`; sin filtro, ambos), `code` (exacto, ≤ 100), `search` (≤ 200).
- Todos los registros tienen `id`, `status`, `version`, `created_at`, `updated_at`, `created_by`, `updated_by`.
- Escrituras con `version` (≥ 1) → `409 PRODUCT_CATALOG.VERSION_CONFLICT`. `deactivate`/`reactivate` reciben `{"version": n}` (`VersionRequest`).
- `code` se normaliza y es único por catálogo (`409 DUPLICATE_CODE`); además, los códigos de unidades de medida y tipos de empaque no pueden coincidir entre sí (`409 CODE_USED_BY_PACKAGING_TYPE` / `CODE_USED_BY_UNIT_OF_MEASURE`). `code` es inmutable en los `PUT` (no se envía).
- Jerarquías (categorías, grupos): el padre debe existir y estar activo (`422 PARENT_INACTIVE`), no formar ciclos (`422 HIERARCHY_CYCLE`); inactivar con hijos activos → `409 HAS_ACTIVE_CHILDREN`; los grupos deben ser del mismo tipo que su padre (`422 PARENT_OF_OTHER_TYPE`).
- Referencias a otros registros: `422 REFERENCE_NOT_FOUND` / `REFERENCE_INACTIVE`; producto inactivo → `422 PRODUCT_INACTIVE`.
- Todos los modelos rechazan campos adicionales; `422 IMMUTABLE_FIELD` para campos inmutables.
- `503 DEPENDENCY_UNAVAILABLE` con `dependency` (`database`, `party-identity`, almacenamiento de objetos).

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso (`perm:product-catalog:…`) | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | PostgreSQL disponible | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `POST` | `/units-of-measure/batch-lookup` | Hasta 100 unidades por id | `units-of-measure:read` | `READ` | [Ver](#3-post-units-of-measurebatch-lookup) |
| 4 | `GET` | `/units-of-measure` | Listar unidades | `units-of-measure:read` | `READ` | [Ver](#4-get-units-of-measure) |
| 5 | `POST` | `/units-of-measure` | Crear unidad | `units-of-measure:create` | `WRITE` | [Ver](#5-post-units-of-measure) |
| 6 | `GET` | `/units-of-measure/{item_id}` | Consultar unidad | `units-of-measure:read` | `READ` | [Ver](#6-get-units-of-measureitem_id) |
| 7 | `PUT` | `/units-of-measure/{item_id}` | Modificar unidad | `units-of-measure:update` | `WRITE` | [Ver](#7-put-units-of-measureitem_id) |
| 8 | `POST` | `/units-of-measure/{item_id}/deactivate` | Inactivar unidad | `units-of-measure:deactivate` | `HIGH_RISK` | [Ver](#8-post-units-of-measureitem_iddeactivate) |
| 9 | `POST` | `/units-of-measure/{item_id}/reactivate` | Reactivar unidad | `units-of-measure:deactivate` | `WRITE` | [Ver](#9-post-units-of-measureitem_idreactivate) |
| 10 | `GET` | `/packaging-types` | Listar tipos de empaque | `packaging-types:read` | `READ` | [Ver](#10-get-packaging-types) |
| 11 | `POST` | `/packaging-types` | Crear tipo de empaque | `packaging-types:create` | `WRITE` | [Ver](#11-post-packaging-types) |
| 12 | `GET` | `/packaging-types/{item_id}` | Consultar | `packaging-types:read` | `READ` | [Ver](#12-get-packaging-typesitem_id) |
| 13 | `PUT` | `/packaging-types/{item_id}` | Modificar | `packaging-types:update` | `WRITE` | [Ver](#13-put-packaging-typesitem_id) |
| 14 | `POST` | `/packaging-types/{item_id}/deactivate` | Inactivar | `packaging-types:deactivate` | `WRITE` | [Ver](#14-post-packaging-typesitem_iddeactivate) |
| 15 | `POST` | `/packaging-types/{item_id}/reactivate` | Reactivar | `packaging-types:deactivate` | `WRITE` | [Ver](#15-post-packaging-typesitem_idreactivate) |
| 16 | `GET` | `/brands` | Listar marcas | `brands:read` | `READ` | [Ver](#16-get-brands) |
| 17 | `POST` | `/brands` | Crear marca | `brands:create` | `WRITE` | [Ver](#17-post-brands) |
| 18 | `GET` | `/brands/{item_id}` | Consultar | `brands:read` | `READ` | [Ver](#18-get-brandsitem_id) |
| 19 | `PUT` | `/brands/{item_id}` | Modificar | `brands:update` | `WRITE` | [Ver](#19-put-brandsitem_id) |
| 20 | `POST` | `/brands/{item_id}/deactivate` | Inactivar | `brands:deactivate` | `WRITE` | [Ver](#20-post-brandsitem_iddeactivate) |
| 21 | `POST` | `/brands/{item_id}/reactivate` | Reactivar | `brands:deactivate` | `WRITE` | [Ver](#21-post-brandsitem_idreactivate) |
| 22 | `GET` | `/categories/{category_id}/children` | Hijas directas | `categories:read` | `READ` | [Ver](#22-get-categoriescategory_idchildren) |
| 23 | `GET` | `/categories/{category_id}/descendants` | Descendientes | `categories:read` | `READ` | [Ver](#23-get-categoriescategory_iddescendants) |
| 24 | `GET` | `/categories/{category_id}/ancestors` | Ancestros (raíz → categoría) | `categories:read` | `READ` | [Ver](#24-get-categoriescategory_idancestors) |
| 25 | `GET` | `/categories/{category_id}/attributes` | Atributos asociados | `categories:read` | `READ` | [Ver](#25-get-categoriescategory_idattributes) |
| 26 | `POST` | `/categories/{category_id}/attributes` | Asociar atributo | `categories:update` | `WRITE` | [Ver](#26-post-categoriescategory_idattributes) |
| 27 | `PUT` | `/categories/{category_id}/attributes/{association_id}` | Modificar asociación | `categories:update` | `WRITE` | [Ver](#27-put-categoriescategory_idattributesassociation_id) |
| 28 | `POST` | `/categories/{category_id}/attributes/{association_id}/deactivate` | Inactivar asociación | `categories:deactivate` | `WRITE` | [Ver](#28-post-categoriescategory_idattributesassociation_iddeactivate) |
| 29 | `POST` | `/categories/{category_id}/attributes/{association_id}/reactivate` | Reactivar asociación | `categories:deactivate` | `WRITE` | [Ver](#29-post-categoriescategory_idattributesassociation_idreactivate) |
| 30 | `GET` | `/categories` | Listar categorías | `categories:read` | `READ` | [Ver](#30-get-categories) |
| 31 | `POST` | `/categories` | Crear categoría | `categories:update` | `WRITE` | [Ver](#31-post-categories) |
| 32 | `GET` | `/categories/{item_id}` | Consultar | `categories:read` | `READ` | [Ver](#32-get-categoriesitem_id) |
| 33 | `PUT` | `/categories/{item_id}` | Modificar | `categories:update` | `WRITE` | [Ver](#33-put-categoriesitem_id) |
| 34 | `POST` | `/categories/{item_id}/deactivate` | Inactivar | `categories:deactivate` | `WRITE` | [Ver](#34-post-categoriesitem_iddeactivate) |
| 35 | `POST` | `/categories/{item_id}/reactivate` | Reactivar | `categories:deactivate` | `WRITE` | [Ver](#35-post-categoriesitem_idreactivate) |
| 36 | `GET` | `/attribute-definitions/{definition_id}/options` | Opciones de una definición | `attribute-definitions:read` | `READ` | [Ver](#36-get-attribute-definitionsdefinition_idoptions) |
| 37 | `POST` | `/attribute-definitions/{definition_id}/options` | Crear opción | `attribute-definitions:update` | `WRITE` | [Ver](#37-post-attribute-definitionsdefinition_idoptions) |
| 38 | `PUT` | `/attribute-definitions/{definition_id}/options/{option_id}` | Modificar opción | `attribute-definitions:update` | `WRITE` | [Ver](#38-put-attribute-definitionsdefinition_idoptionsoption_id) |
| 39 | `POST` | `/attribute-definitions/{definition_id}/options/{option_id}/deactivate` | Inactivar opción | `attribute-definitions:deactivate` | `WRITE` | [Ver](#39-post-attribute-definitionsdefinition_idoptionsoption_iddeactivate) |
| 40 | `POST` | `/attribute-definitions/{definition_id}/options/{option_id}/reactivate` | Reactivar opción | `attribute-definitions:deactivate` | `WRITE` | [Ver](#40-post-attribute-definitionsdefinition_idoptionsoption_idreactivate) |
| 41 | `GET` | `/attribute-definitions` | Listar atributos | `attribute-definitions:read` | `READ` | [Ver](#41-get-attribute-definitions) |
| 42 | `POST` | `/attribute-definitions` | Crear atributo | `attribute-definitions:create` | `WRITE` | [Ver](#42-post-attribute-definitions) |
| 43 | `GET` | `/attribute-definitions/{item_id}` | Consultar | `attribute-definitions:read` | `READ` | [Ver](#43-get-attribute-definitionsitem_id) |
| 44 | `PUT` | `/attribute-definitions/{item_id}` | Modificar | `attribute-definitions:update` | `WRITE` | [Ver](#44-put-attribute-definitionsitem_id) |
| 45 | `POST` | `/attribute-definitions/{item_id}/deactivate` | Inactivar | `attribute-definitions:deactivate` | `WRITE` | [Ver](#45-post-attribute-definitionsitem_iddeactivate) |
| 46 | `POST` | `/attribute-definitions/{item_id}/reactivate` | Reactivar | `attribute-definitions:deactivate` | `WRITE` | [Ver](#46-post-attribute-definitionsitem_idreactivate) |
| 47 | `POST` | `/products/summaries/batch-lookup` | Resumen de hasta 100 productos | `products:read` | `READ` | [Ver](#47-post-productssummariesbatch-lookup) |
| 48 | `POST` | `/products/match` | Productos que cumplen filtros | `products:read` | `READ` | [Ver](#48-post-productsmatch) |
| 49 | `GET` | `/products` | Listar y buscar productos | `products:read` | `READ` | [Ver](#49-get-products) |
| 50 | `POST` | `/products` | Crear producto | `products:create` | `WRITE` | [Ver](#50-post-products) |
| 51 | `POST` | `/products/batch-lookup` | Hasta 100 productos por id | `products:read` | `READ` | [Ver](#51-post-productsbatch-lookup) |
| 52 | `GET` | `/products/by-identifier/{value}` | Buscar por código escaneado | `products:read` | `READ` | [Ver](#52-get-productsby-identifiervalue) |
| 53 | `GET` | `/products/{product_id}` | Consultar producto | `products:read` | `READ` | [Ver](#53-get-productsproduct_id) |
| 54 | `PUT` | `/products/{product_id}` | Modificar producto | `products:update` | `WRITE` | [Ver](#54-put-productsproduct_id) |
| 55 | `GET` | `/products/{product_id}/applicable-attributes` | Atributos aplicables | `products:read` | `READ` | [Ver](#55-get-productsproduct_idapplicable-attributes) |
| 56 | `GET` | `/products/{product_id}/completeness` | Completitud | `products:read` | `READ` | [Ver](#56-get-productsproduct_idcompleteness) |
| 57 | `POST` | `/products/{product_id}/deactivate` | Inactivar producto | `products:deactivate` | `HIGH_RISK` | [Ver](#57-post-productsproduct_iddeactivate) |
| 58 | `POST` | `/products/{product_id}/reactivate` | Reactivar producto | `products:deactivate` | `WRITE` | [Ver](#58-post-productsproduct_idreactivate) |
| 59 | `GET` | `/products/{product_id}/categories` | Categorías del producto | `products:read` | `READ` | [Ver](#59-get-productsproduct_idcategories) |
| 60 | `POST` | `/products/{product_id}/categories` | Asignar categoría | `products:update` | `WRITE` | [Ver](#60-post-productsproduct_idcategories) |
| 61 | `POST` | `/products/{product_id}/categories/{association_id}/set-primary` | Categoría principal | `products:update` | `WRITE` | [Ver](#61-post-productsproduct_idcategoriesassociation_idset-primary) |
| 62 | `POST` | `/products/{product_id}/categories/{association_id}/deactivate` | Retirar categoría | `products:deactivate` | `WRITE` | [Ver](#62-post-productsproduct_idcategoriesassociation_iddeactivate) |
| 63 | `GET` | `/products/{product_id}/attribute-values` | Valores de atributo | `products:read` | `READ` | [Ver](#63-get-productsproduct_idattribute-values) |
| 64 | `PUT` | `/products/{product_id}/attribute-values/{definition_id}` | Registrar o reemplazar valor | `products:update` | `WRITE` | [Ver](#64-put-productsproduct_idattribute-valuesdefinition_id) |
| 65 | `DELETE` | `/products/{product_id}/attribute-values/{definition_id}` | Retirar valor (borrado físico) | `products:delete` | `HIGH_RISK` | [Ver](#65-delete-productsproduct_idattribute-valuesdefinition_id) |
| 66 | `POST` | `/presentations/batch-lookup` | Hasta 100 presentaciones por id | `products:read` | `READ` | [Ver](#66-post-presentationsbatch-lookup) |
| 67 | `GET` | `/products/{product_id}/presentations` | Presentaciones del producto | `products:read` | `READ` | [Ver](#67-get-productsproduct_idpresentations) |
| 68 | `POST` | `/products/{product_id}/presentations` | Crear presentación | `products:update` | `WRITE` | [Ver](#68-post-productsproduct_idpresentations) |
| 69 | `GET` | `/presentations/{presentation_id}` | Consultar presentación | `products:read` | `READ` | [Ver](#69-get-presentationspresentation_id) |
| 70 | `PUT` | `/presentations/{presentation_id}` | Modificar presentación | `products:update` | `WRITE` | [Ver](#70-put-presentationspresentation_id) |
| 71 | `POST` | `/presentations/{presentation_id}/deactivate` | Inactivar presentación | `products:deactivate` | `HIGH_RISK` | [Ver](#71-post-presentationspresentation_iddeactivate) |
| 72 | `POST` | `/presentations/{presentation_id}/reactivate` | Reactivar presentación | `products:deactivate` | `WRITE` | [Ver](#72-post-presentationspresentation_idreactivate) |
| 73 | `GET` | `/products/{product_id}/identifiers` | Identificadores | `products:read` | `READ` | [Ver](#73-get-productsproduct_ididentifiers) |
| 74 | `POST` | `/products/{product_id}/identifiers` | Registrar identificador | `products:update` | `WRITE` | [Ver](#74-post-productsproduct_ididentifiers) |
| 75 | `POST` | `/products/{product_id}/identifiers/{identifier_id}/set-primary` | Identificador principal | `products:update` | `WRITE` | [Ver](#75-post-productsproduct_ididentifiersidentifier_idset-primary) |
| 76 | `POST` | `/products/{product_id}/identifiers/{identifier_id}/deactivate` | Inactivar identificador | `products:deactivate` | `WRITE` | [Ver](#76-post-productsproduct_ididentifiersidentifier_iddeactivate) |
| 77 | `POST` | `/products/{product_id}/identifiers/{identifier_id}/reactivate` | Reactivar identificador | `products:deactivate` | `WRITE` | [Ver](#77-post-productsproduct_ididentifiersidentifier_idreactivate) |
| 78 | `GET` | `/products/{product_id}/group-assignments` | Grupos del producto | `products:read` | `READ` | [Ver](#78-get-productsproduct_idgroup-assignments) |
| 79 | `POST` | `/products/{product_id}/group-assignments` | Asignar grupo | `products:update` | `WRITE` | [Ver](#79-post-productsproduct_idgroup-assignments) |
| 80 | `POST` | `/products/{product_id}/group-assignments/{assignment_id}/deactivate` | Retirar grupo | `products:deactivate` | `WRITE` | [Ver](#80-post-productsproduct_idgroup-assignmentsassignment_iddeactivate) |
| 81 | `POST` | `/products/{product_id}/group-assignments/{assignment_id}/reactivate` | Reactivar grupo | `products:deactivate` | `WRITE` | [Ver](#81-post-productsproduct_idgroup-assignmentsassignment_idreactivate) |
| 82 | `GET` | `/group-types/{group_type_id}/groups` | Grupos de un tipo | `group-types:read` | `READ` | [Ver](#82-get-group-typesgroup_type_idgroups) |
| 83 | `POST` | `/group-types/{group_type_id}/groups` | Crear grupo | `group-types:create` | `WRITE` | [Ver](#83-post-group-typesgroup_type_idgroups) |
| 84 | `GET` | `/groups/{group_id}` | Consultar grupo | `group-types:read` | `READ` | [Ver](#84-get-groupsgroup_id) |
| 85 | `PUT` | `/groups/{group_id}` | Modificar grupo | `group-types:update` | `WRITE` | [Ver](#85-put-groupsgroup_id) |
| 86 | `GET` | `/groups/{group_id}/children` | Hijos directos | `group-types:read` | `READ` | [Ver](#86-get-groupsgroup_idchildren) |
| 87 | `GET` | `/groups/{group_id}/ancestors` | Ancestros | `group-types:read` | `READ` | [Ver](#87-get-groupsgroup_idancestors) |
| 88 | `POST` | `/groups/{group_id}/deactivate` | Inactivar grupo | `group-types:deactivate` | `WRITE` | [Ver](#88-post-groupsgroup_iddeactivate) |
| 89 | `POST` | `/groups/{group_id}/reactivate` | Reactivar grupo | `group-types:deactivate` | `WRITE` | [Ver](#89-post-groupsgroup_idreactivate) |
| 90 | `GET` | `/group-types` | Listar tipos de grupo | `group-types:read` | `READ` | [Ver](#90-get-group-types) |
| 91 | `POST` | `/group-types` | Crear tipo de grupo | `group-types:create` | `WRITE` | [Ver](#91-post-group-types) |
| 92 | `GET` | `/group-types/{item_id}` | Consultar tipo | `group-types:read` | `READ` | [Ver](#92-get-group-typesitem_id) |
| 93 | `PUT` | `/group-types/{item_id}` | Modificar tipo | `group-types:update` | `WRITE` | [Ver](#93-put-group-typesitem_id) |
| 94 | `POST` | `/group-types/{item_id}/deactivate` | Inactivar tipo | `group-types:deactivate` | `WRITE` | [Ver](#94-post-group-typesitem_iddeactivate) |
| 95 | `POST` | `/group-types/{item_id}/reactivate` | Reactivar tipo | `group-types:deactivate` | `WRITE` | [Ver](#95-post-group-typesitem_idreactivate) |
| 96 | `GET` | `/products/{product_id}/assets` | Activos del producto | `products:read` | `READ` | [Ver](#96-get-productsproduct_idassets) |
| 97 | `POST` | `/products/{product_id}/assets` | Registrar activo | `products:update` | `WRITE` | [Ver](#97-post-productsproduct_idassets) |
| 98 | `GET` | `/products/{product_id}/assets/{asset_id}/content` | Descargar contenido | `products:read` | `READ` | [Ver](#98-get-productsproduct_idassetsasset_idcontent) |
| 99 | `PUT` | `/products/{product_id}/assets/{asset_id}` | Modificar metadatos | `products:update` | `WRITE` | [Ver](#99-put-productsproduct_idassetsasset_id) |
| 100 | `POST` | `/products/{product_id}/assets/{asset_id}/set-primary` | Activo principal | `products:update` | `WRITE` | [Ver](#100-post-productsproduct_idassetsasset_idset-primary) |
| 101 | `POST` | `/products/{product_id}/assets/{asset_id}/deactivate` | Inactivar activo | `products:deactivate` | `WRITE` | [Ver](#101-post-productsproduct_idassetsasset_iddeactivate) |
| 102 | `POST` | `/products/{product_id}/assets/{asset_id}/reactivate` | Reactivar activo | `products:deactivate` | `WRITE` | [Ver](#102-post-productsproduct_idassetsasset_idreactivate) |
| 103 | `POST` | `/products/{product_id}/first-use` | Primer uso por adopción | `first-use:register` (cuenta técnica) | `HIGH_RISK` | [Ver](#103-post-productsproduct_idfirst-use) |
| 104 | `POST` | `/products/{product_id}/first-use/manual` | Primer uso manual | `first-use:register-manual` | `HIGH_RISK` | [Ver](#104-post-productsproduct_idfirst-usemanual) |

La numeración de esta tabla es la de las fichas siguientes (las referencias de la tabla de permisos usan estos mismos números).

## Operaciones

Una ficha por operación, agrupadas por recurso. Cada ficha incluye la URL completa de Render, el permiso, los parámetros, el cuerpo (cuando aplica), un ejemplo de solicitud con `curl` y un ejemplo de respuesta con valores ilustrativos validados contra el contrato OpenAPI y los modelos del servicio.

### Salud (operaciones 1–2)

`GET https://sio-product-catalog-dev.onrender.com/health/live` → `200` `{"status": "ok"}`. `GET …/health/ready` → `200`; `503` sin cuerpo si PostgreSQL no responde. Sin autenticación.

### 1. `GET /health/live`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Proceso vivo |
| URL | `https://sio-product-catalog-dev.onrender.com/health/live` |
| Permiso | Ninguno (ruta pública) |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | Ninguna |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/health/live'
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
{
  "status": "CONFIRMED"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |

### 2. `GET /health/ready`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | PostgreSQL disponible |
| URL | `https://sio-product-catalog-dev.onrender.com/health/ready` |
| Permiso | Ninguno (ruta pública) |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | Ninguna |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/health/ready'
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
"texto ilustrativo"
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `503` | Base de datos no disponible |

### Unidades de medida (operaciones 3–9)

Base: `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure`. Objeto `UnitOfMeasureResponse`: `id`, `code`, `name`, `symbol`, `measurement_type` (`UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA`), `allows_decimals`, `status`, `version`, trazabilidad. Son la `base_unit_id` de los productos y la `purchase_unit_id` de los productos de proveedor.

### 3. `POST /units-of-measure/batch-lookup`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Hasta 100 unidades por id |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/batch-lookup` |
| Permiso | `perm:product-catalog:units-of-measure:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo `{"ids": [...]}` (1–100; repetidos se ignoran; `422 BATCH_LIMIT_EXCEEDED`). Respuesta `200` `{"items": [{"id", "found", "status", "measurement_type", "allows_decimals", "code", "name"}]}`

Cuerpo (`BatchLookupRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `ids` | array<UUID> | Sí | — — Entre 1 y 100 identificadores; los repetidos se ignoran. |

Cómo obtener los identificadores del cuerpo: `ids`: Identificadores obtenidos en listados previos.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```

Ejemplo de respuesta `200` (`UnitLookupResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "status": "ACTIVE",
      "measurement_type": "UNIT",
      "allows_decimals": false,
      "code": "UN",
      "name": "Unidad"
    }
  ]
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `UnitLookupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 4. `GET /units-of-measure`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar unidades |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure` |
| Permiso | `perm:product-catalog:units-of-measure:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros: `status`, `code`, `search`, `measurement_type`, `page`, `page_size`. Respuesta paginada

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |
| `measurement_type` | query | enum \| null | No | `UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_UnitOfMeasureResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "UN",
      "name": "Unidad",
      "symbol": "un",
      "measurement_type": "UNIT",
      "allows_decimals": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_UnitOfMeasureResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 5. `POST /units-of-measure`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear unidad |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure` |
| Permiso | `perm:product-catalog:units-of-measure:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`UnitOfMeasureCreate`): `code` (≤ 40), `name` (≤ 160), `symbol` (≤ 32), `measurement_type` (enum), `allows_decimals` (boolean), todos obligatorios. `201`

Cuerpo (`UnitOfMeasureCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 40 car. |
| `name` | string | Sí | ≤ 160 car. |
| `symbol` | string | Sí | ≤ 32 car. |
| `measurement_type` | enum | Sí | `UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA` |
| `allows_decimals` | boolean | Sí | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "UN",
    "name": "Unidad",
    "symbol": "un",
    "measurement_type": "UNIT",
    "allows_decimals": false
  }'
```

Ejemplo de respuesta `201` (`UnitOfMeasureResponse`; valores ilustrativos):

```json
{
  "id": "348985d5-9050-4473-868e-3d6323f9e6aa",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "UN",
  "name": "Unidad",
  "symbol": "un",
  "measurement_type": "UNIT",
  "allows_decimals": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `UnitOfMeasureResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 6. `GET /units-of-measure/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar unidad |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/{item_id}` |
| Permiso | `perm:product-catalog:units-of-measure:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: `200`; `404`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 4 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`UnitOfMeasureResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "UN",
  "name": "Unidad",
  "symbol": "un",
  "measurement_type": "UNIT",
  "allows_decimals": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `UnitOfMeasureResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 7. `PUT /units-of-measure/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar unidad |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/{item_id}` |
| Permiso | `perm:product-catalog:units-of-measure:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo: `version`, `name`, `symbol`. `code`, `measurement_type` y `allows_decimals` son inmutables

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 4 |

Cuerpo (`UnitOfMeasureUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 160 car. |
| `symbol` | string | Sí | ≤ 32 car. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "symbol": "un"
  }'
```

Ejemplo de respuesta `200` (`UnitOfMeasureResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "UN",
  "name": "Acetaminofén 500 mg",
  "symbol": "un",
  "measurement_type": "UNIT",
  "allows_decimals": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `UnitOfMeasureResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 8. `POST /units-of-measure/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Inactivar unidad |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:units-of-measure:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: los productos que la usan como unidad base no pueden actualizarse ni adoptarse (`422 REFERENCE_INACTIVE`). Cuerpo `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 4 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`UnitOfMeasureResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "UN",
  "name": "Unidad",
  "symbol": "un",
  "measurement_type": "UNIT",
  "allows_decimals": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `UnitOfMeasureResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 9. `POST /units-of-measure/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar unidad |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:units-of-measure:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 4 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/units-of-measure/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`UnitOfMeasureResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "UN",
  "name": "Unidad",
  "symbol": "un",
  "measurement_type": "UNIT",
  "allows_decimals": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `UnitOfMeasureResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Tipos de empaque (operaciones 10–15)

Base `…/api/v1/packaging-types`. Objeto `PackagingTypeResponse`: `id`, `code`, `name`, `description`, `status`, `version`, trazabilidad. Se usan en `packaging_type_id` de las presentaciones.

### 10. `GET /packaging-types`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar tipos de empaque |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types` |
| Permiso | `perm:product-catalog:packaging-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, paginación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_PackagingTypeResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "CAJA",
      "name": "Caja",
      "description": "Descripción ilustrativa"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_PackagingTypeResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 11. `POST /packaging-types`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear tipo de empaque |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types` |
| Permiso | `perm:product-catalog:packaging-types:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`PackagingTypeCreate`): `code` (≤ 100), `name` (≤ 240) obligatorios; `description` opcional. El código no puede coincidir con una unidad de medida (`409 CODE_USED_BY_UNIT_OF_MEASURE`)

Cuerpo (`PackagingTypeCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 100 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CAJA",
    "name": "Caja",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `201` (`PackagingTypeResponse`; valores ilustrativos):

```json
{
  "id": "506f78f6-2b41-4f34-89a8-40495bdf0bff",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CAJA",
  "name": "Caja",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `PackagingTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 12. `GET /packaging-types/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/{item_id}` |
| Permiso | `perm:product-catalog:packaging-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 10 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PackagingTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CAJA",
  "name": "Caja",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PackagingTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 13. `PUT /packaging-types/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/{item_id}` |
| Permiso | `perm:product-catalog:packaging-types:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo: `version`, `name`, `description`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 10 |

Cuerpo (`PackagingTypeUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `200` (`PackagingTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CAJA",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PackagingTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 14. `POST /packaging-types/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:packaging-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 10 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PackagingTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CAJA",
  "name": "Caja",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PackagingTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 15. `POST /packaging-types/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:packaging-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 10 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/packaging-types/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PackagingTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CAJA",
  "name": "Caja",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PackagingTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Marcas (operaciones 16–21)

Base `…/api/v1/brands`. Objeto `BrandResponse`: `id`, `code`, `name`, `description`, `status`, `version`, trazabilidad. Se usan en `global_brand_id` de los productos y como filtro `brand_id`.

### 16. `GET /brands`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar marcas |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands` |
| Permiso | `perm:product-catalog:brands:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, paginación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/brands?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_BrandResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "GENFAR",
      "name": "Genfar",
      "description": "Descripción ilustrativa"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_BrandResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 17. `POST /brands`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear marca |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands` |
| Permiso | `perm:product-catalog:brands:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`BrandCreate`): `code` (≤ 100), `name` (≤ 240), `description` (opcional)

Cuerpo (`BrandCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 100 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/brands' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "GENFAR",
    "name": "Genfar",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `201` (`BrandResponse`; valores ilustrativos):

```json
{
  "id": "baf6df2d-2bdc-4911-813b-37274509bc95",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "GENFAR",
  "name": "Genfar",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `BrandResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 18. `GET /brands/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands/{item_id}` |
| Permiso | `perm:product-catalog:brands:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 16 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/brands/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`BrandResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "GENFAR",
  "name": "Genfar",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `BrandResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 19. `PUT /brands/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands/{item_id}` |
| Permiso | `perm:product-catalog:brands:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 16 |

Cuerpo (`BrandUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/brands/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `200` (`BrandResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "GENFAR",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `BrandResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 20. `POST /brands/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:brands:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 16 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/brands/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BrandResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "GENFAR",
  "name": "Genfar",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `BrandResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 21. `POST /brands/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/brands/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:brands:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 16 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/brands/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`BrandResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "GENFAR",
  "name": "Genfar",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `BrandResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Categorías (operaciones 22–35)

Base `…/api/v1/categories`. Objeto `CategoryResponse`: `id`, `code`, `name`, `description`, `parent_category_id`, `status`, `version`, trazabilidad. Jerarquía de profundidad libre; las categorías determinan qué atributos aplican a un producto (sin herencia entre niveles).

### 22. `GET /categories/{category_id}/children`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Hijas directas |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/children` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Hijas directas, paginado

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/children?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CategoryResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "ANALGESICOS",
      "name": "Analgésicos",
      "description": "Descripción ilustrativa",
      "parent_category_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_CategoryResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 23. `GET /categories/{category_id}/descendants`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Descendientes |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/descendants` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Todos los descendientes, paginado

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/descendants?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CategoryResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "ANALGESICOS",
      "name": "Analgésicos",
      "description": "Descripción ilustrativa",
      "parent_category_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_CategoryResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 24. `GET /categories/{category_id}/ancestors`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Ancestros (raíz → categoría) |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/ancestors` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array** ordenado de la raíz a la categoría

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/ancestors' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "code": "ANALGESICOS",
    "name": "Analgésicos",
    "description": "Descripción ilustrativa",
    "parent_category_id": null
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 25. `GET /categories/{category_id}/attributes`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Atributos asociados |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/attributes` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array** de `CategoryAttributeResponse` (`id`, `global_category_id`, `attribute_definition_id`, `is_required`, `is_filterable`, `display_order`, `status`, `version`); filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/attributes' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
    "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
    "is_required": true,
    "is_filterable": true,
    "display_order": 1
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 26. `POST /categories/{category_id}/attributes`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Asociar atributo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/attributes` |
| Permiso | `perm:product-catalog:categories:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`CategoryAttributeCreate`): `attribute_definition_id` (obligatorio), `is_required` (`false`), `is_filterable` (`false`), `display_order` (0–32767). `409 DUPLICATE_ASSOCIATION`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |

Cuerpo (`CategoryAttributeCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `attribute_definition_id` | UUID | Sí | — |
| `is_required` | boolean | No | por defecto `false` |
| `is_filterable` | boolean | No | por defecto `false` |
| `display_order` | integer | No | ≥ 0; ≤ 32767; por defecto `0` |

Cómo obtener los identificadores del cuerpo: `attribute_definition_id`: Operación 41.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/attributes' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
    "is_required": true,
    "is_filterable": true,
    "display_order": 1
  }'
```

Ejemplo de respuesta `201` (`CategoryAttributeResponse`; valores ilustrativos):

```json
{
  "id": "be7140d8-db8a-4ea2-8194-729d32436e2e",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "is_required": true,
  "is_filterable": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `CategoryAttributeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 27. `PUT /categories/{category_id}/attributes/{association_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar asociación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/attributes/{association_id}` |
| Permiso | `perm:product-catalog:categories:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `is_required`, `is_filterable`, `display_order` obligatorios

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `association_id` | ruta | UUID | Sí | — | Campo `id` de la asociación (operación 25) |

Cuerpo (`CategoryAttributeUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `is_required` | boolean | Sí | — |
| `is_filterable` | boolean | Sí | — |
| `display_order` | integer | Sí | ≥ 0; ≤ 32767 |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/attributes/da6195d4-1082-43d8-8a1d-d8ea15ed6d17' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "is_required": true,
    "is_filterable": true,
    "display_order": 1
  }'
```

Ejemplo de respuesta `200` (`CategoryAttributeResponse`; valores ilustrativos):

```json
{
  "id": "da6195d4-1082-43d8-8a1d-d8ea15ed6d17",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "is_required": true,
  "is_filterable": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryAttributeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 28. `POST /categories/{category_id}/attributes/{association_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar asociación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/attributes/{association_id}/deactivate` |
| Permiso | `perm:product-catalog:categories:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `association_id` | ruta | UUID | Sí | — | Campo `id` de la asociación (operación 25) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/attributes/da6195d4-1082-43d8-8a1d-d8ea15ed6d17/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CategoryAttributeResponse`; valores ilustrativos):

```json
{
  "id": "da6195d4-1082-43d8-8a1d-d8ea15ed6d17",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "is_required": true,
  "is_filterable": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryAttributeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 29. `POST /categories/{category_id}/attributes/{association_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar asociación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{category_id}/attributes/{association_id}/reactivate` |
| Permiso | `perm:product-catalog:categories:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `category_id` | ruta | UUID | Sí | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `association_id` | ruta | UUID | Sí | — | Campo `id` de la asociación (operación 25) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/b583a629-3fe1-4575-8ba1-7314e10419cc/attributes/da6195d4-1082-43d8-8a1d-d8ea15ed6d17/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CategoryAttributeResponse`; valores ilustrativos):

```json
{
  "id": "da6195d4-1082-43d8-8a1d-d8ea15ed6d17",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "is_required": true,
  "is_filterable": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryAttributeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 30. `GET /categories`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar categorías |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, `parent_category_id`, `root_only` (boolean), paginación. Para un árbol: `root_only=true` y después la operación 22

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |
| `parent_category_id` | query | UUID \| null | No | — | Operación 30 |
| `root_only` | query | boolean | No | por defecto `false` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_CategoryResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "ANALGESICOS",
      "name": "Analgésicos",
      "description": "Descripción ilustrativa",
      "parent_category_id": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_CategoryResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 31. `POST /categories`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear categoría |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories` |
| Permiso | `perm:product-catalog:categories:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`CategoryCreate`): `code` (≤ 100), `name` (≤ 240), `description`, `parent_category_id`

Cuerpo (`CategoryCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 100 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `parent_category_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `parent_category_id`: Operación 30.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "ANALGESICOS",
    "name": "Analgésicos",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `201` (`CategoryResponse`; valores ilustrativos):

```json
{
  "id": "84bb601e-4183-4771-88ff-6cf674d90174",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "ANALGESICOS",
  "name": "Analgésicos",
  "description": "Descripción ilustrativa",
  "parent_category_id": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `CategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 32. `GET /categories/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{item_id}` |
| Permiso | `perm:product-catalog:categories:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 30 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CategoryResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "ANALGESICOS",
  "name": "Analgésicos",
  "description": "Descripción ilustrativa",
  "parent_category_id": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 33. `PUT /categories/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{item_id}` |
| Permiso | `perm:product-catalog:categories:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`, `parent_category_id` (cambiar el padre valida ciclos)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 30 |

Cuerpo (`CategoryUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `parent_category_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `parent_category_id`: Operación 30.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `200` (`CategoryResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "ANALGESICOS",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa",
  "parent_category_id": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 34. `POST /categories/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:categories:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `409 HAS_ACTIVE_CHILDREN` si tiene hijas activas

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 30 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CategoryResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "ANALGESICOS",
  "name": "Analgésicos",
  "description": "Descripción ilustrativa",
  "parent_category_id": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 35. `POST /categories/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/categories/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:categories:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `422 PARENT_INACTIVE` si su padre está inactivo

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 30 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/categories/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`CategoryResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "ANALGESICOS",
  "name": "Analgésicos",
  "description": "Descripción ilustrativa",
  "parent_category_id": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Definiciones de atributo y opciones (operaciones 36–46)

Base `…/api/v1/attribute-definitions`. Objeto `AttributeDefinitionResponse`: `id`, `code`, `name`, `description`, `data_type` (`TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `OPTION`), `unit_of_measure_id`, `status`, `version`, trazabilidad. `OptionResponse`: `id`, `attribute_definition_id`, `code`, `name`, `description`, `display_order`, `status`, `version`.

### 36. `GET /attribute-definitions/{definition_id}/options`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Opciones de una definición |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{definition_id}/options` |
| Permiso | `perm:product-catalog:attribute-definitions:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/28094980-356b-4592-8e9c-6d9fea57645d/options' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
    "code": "TABLETA",
    "name": "Tableta",
    "description": "Descripción ilustrativa",
    "display_order": 1
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 37. `POST /attribute-definitions/{definition_id}/options`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear opción |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{definition_id}/options` |
| Permiso | `perm:product-catalog:attribute-definitions:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Solo definiciones `OPTION` activas (`422 DEFINITION_NOT_OPTION`). Cuerpo (`OptionCreate`): `code` (≤ 160), `name` (≤ 240), `description`, `display_order` (0–32767)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |

Cuerpo (`OptionCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 160 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `display_order` | integer | No | ≥ 0; ≤ 32767; por defecto `0` |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/28094980-356b-4592-8e9c-6d9fea57645d/options' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "TABLETA",
    "name": "Tableta",
    "description": "Descripción ilustrativa",
    "display_order": 1
  }'
```

Ejemplo de respuesta `201` (`OptionResponse`; valores ilustrativos):

```json
{
  "id": "89b65b94-e224-46b1-8918-35ee3689fe8e",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "code": "TABLETA",
  "name": "Tableta",
  "description": "Descripción ilustrativa",
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `OptionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 38. `PUT /attribute-definitions/{definition_id}/options/{option_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar opción |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{definition_id}/options/{option_id}` |
| Permiso | `perm:product-catalog:attribute-definitions:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`, `display_order`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |
| `option_id` | ruta | UUID | Sí | — | Campo `id` de una opción (operación 36) |

Cuerpo (`OptionUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `display_order` | integer | Sí | ≥ 0; ≤ 32767 |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/28094980-356b-4592-8e9c-6d9fea57645d/options/28df3725-890b-4c91-8775-545375b769c8' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa",
    "display_order": 1
  }'
```

Ejemplo de respuesta `200` (`OptionResponse`; valores ilustrativos):

```json
{
  "id": "28df3725-890b-4c91-8775-545375b769c8",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "code": "TABLETA",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa",
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `OptionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 39. `POST /attribute-definitions/{definition_id}/options/{option_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar opción |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{definition_id}/options/{option_id}/deactivate` |
| Permiso | `perm:product-catalog:attribute-definitions:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |
| `option_id` | ruta | UUID | Sí | — | Campo `id` de una opción (operación 36) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/28094980-356b-4592-8e9c-6d9fea57645d/options/28df3725-890b-4c91-8775-545375b769c8/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OptionResponse`; valores ilustrativos):

```json
{
  "id": "28df3725-890b-4c91-8775-545375b769c8",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "code": "TABLETA",
  "name": "Tableta",
  "description": "Descripción ilustrativa",
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `OptionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 40. `POST /attribute-definitions/{definition_id}/options/{option_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar opción |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{definition_id}/options/{option_id}/reactivate` |
| Permiso | `perm:product-catalog:attribute-definitions:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |
| `option_id` | ruta | UUID | Sí | — | Campo `id` de una opción (operación 36) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/28094980-356b-4592-8e9c-6d9fea57645d/options/28df3725-890b-4c91-8775-545375b769c8/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`OptionResponse`; valores ilustrativos):

```json
{
  "id": "28df3725-890b-4c91-8775-545375b769c8",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "code": "TABLETA",
  "name": "Tableta",
  "description": "Descripción ilustrativa",
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `OptionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 41. `GET /attribute-definitions`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar atributos |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions` |
| Permiso | `perm:product-catalog:attribute-definitions:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, `data_type`, paginación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |
| `data_type` | query | enum \| null | No | `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `OPTION` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_AttributeDefinitionResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "CONCENTRACION",
      "name": "Concentración",
      "description": "Descripción ilustrativa",
      "data_type": "TEXT",
      "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_AttributeDefinitionResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 42. `POST /attribute-definitions`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear atributo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions` |
| Permiso | `perm:product-catalog:attribute-definitions:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`AttributeDefinitionCreate`): `code` (≤ 160), `name` (≤ 240), `description` (obligatoria), `data_type` (enum), `unit_of_measure_id` (solo para `INTEGER`/`DECIMAL`: `422 UNIT_NOT_ALLOWED_FOR_DATA_TYPE`)

Cuerpo (`AttributeDefinitionCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 160 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string | Sí | — |
| `data_type` | enum | Sí | `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `OPTION` |
| `unit_of_measure_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `unit_of_measure_id`: Operación 4.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CONCENTRACION",
    "name": "Concentración",
    "description": "Concentración del principio activo",
    "data_type": "TEXT",
    "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
  }'
```

Ejemplo de respuesta `201` (`AttributeDefinitionResponse`; valores ilustrativos):

```json
{
  "id": "a7124844-3c5d-4fb1-82bf-f70401d33128",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CONCENTRACION",
  "name": "Concentración",
  "description": "Concentración del principio activo",
  "data_type": "TEXT",
  "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `AttributeDefinitionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 43. `GET /attribute-definitions/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{item_id}` |
| Permiso | `perm:product-catalog:attribute-definitions:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 41 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`AttributeDefinitionResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CONCENTRACION",
  "name": "Concentración",
  "description": "Descripción ilustrativa",
  "data_type": "TEXT",
  "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AttributeDefinitionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 44. `PUT /attribute-definitions/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{item_id}` |
| Permiso | `perm:product-catalog:attribute-definitions:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`. `data_type` y unidad son inmutables

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 41 |

Cuerpo (`AttributeDefinitionUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string | Sí | — |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `200` (`AttributeDefinitionResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CONCENTRACION",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa",
  "data_type": "TEXT",
  "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AttributeDefinitionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 45. `POST /attribute-definitions/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:attribute-definitions:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 41 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AttributeDefinitionResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CONCENTRACION",
  "name": "Concentración",
  "description": "Descripción ilustrativa",
  "data_type": "TEXT",
  "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AttributeDefinitionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 46. `POST /attribute-definitions/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:attribute-definitions:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 41 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/attribute-definitions/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AttributeDefinitionResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "CONCENTRACION",
  "name": "Concentración",
  "description": "Descripción ilustrativa",
  "data_type": "TEXT",
  "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AttributeDefinitionResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Productos (operaciones 47–58)

Base `…/api/v1/products`. Objeto `ProductResponse`:

| Campo | Tipo | Significado |
|---|---|---|
| `id` | UUID | [global_product_id](../parametros/global-product-id.md) (`product_id` en las rutas) |
| `product_type` | string | Solo `GOOD` en la creación actual |
| `canonical_name` | string (≤ 400) | Nombre canónico global |
| `description` | string \| null | — |
| `global_brand_id`, `manufacturer_organization_id` | UUID \| null | Marca (operación 16) y fabricante (identidad de organización en Party Identity) |
| `base_unit_id` | UUID | Unidad base (operación 4). **Inmutable tras el primer uso** (`422 BASE_UNIT_LOCKED_BY_FIRST_USE`) |
| `first_used_at`, `first_use_source` | — | Marca irreversible de primer uso (adopción o manual) |
| `completeness` | objeto | `is_complete`, `issues[]` (códigos), `missing_attribute_definition_ids[]`, `out_of_classification_value_ids[]` |
| `eligible_for_adoption` | boolean | Si una empresa puede adoptarlo en Commercial Relationship |
| `warnings[]` | `{code, message, matching_product_ids[]}` | Avisos no bloqueantes, por ejemplo posibles duplicados |
| `detail` | objeto \| null | Solo con `expand=detail`: `categories[]`, `presentations[]`, `identifiers[]`, `attribute_values[]`, `group_assignments[]`, `assets[]` |
| `status`, `version`, trazabilidad | — | — |

### 47. `POST /products/summaries/batch-lookup`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Resumen de hasta 100 productos |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/summaries/batch-lookup` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo `{"ids": [...]}` (1–100). Respuesta `items[]` con `id`, `found`, `canonical_name`, `product_type`, `status`, `brand` y `base_unit` (`{id, code, name}`), `categories[]`, `identifiers[]` activos, `has_image`, `image_url` (URL absoluta y firmada de la ruta pública, o `null`). Lo usa Product Inventory Query

Cuerpo (`BatchLookupRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `ids` | array<UUID> | Sí | — — Entre 1 y 100 identificadores; los repetidos se ignoran. |

Cómo obtener los identificadores del cuerpo: `ids`: Identificadores obtenidos en listados previos.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/summaries/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```

Ejemplo de respuesta `200` (`ProductSummaryResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "canonical_name": "Acetaminofén 500 mg tableta",
      "product_type": "GOOD",
      "status": "ACTIVE",
      "brand": {
        "id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "GENFAR",
        "name": "Genfar"
      },
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "categories": [
        {
          "id": "3af5ffc6-f94e-4d7e-8271-b22e87afa664",
          "code": "ANALGESICOS",
          "name": "Analgésicos",
          "is_primary": true
        }
      ],
      "identifiers": [
        {
          "type": "GTIN",
          "value": "7702001234567",
          "is_primary": true,
          "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d"
        }
      ],
      "has_image": false,
      "image_url": null
    }
  ]
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductSummaryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 48. `POST /products/match`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Productos que cumplen filtros |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/match` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`ProductMatchRequest`): `brand_ids`, `category_ids` (≤ 100 cada uno), `include_descendants`, `identifier` (1–120), `product_type` (≤ 20), `status` (`ACTIVE` por defecto, `INACTIVE`, `ALL`), `has_image`, `candidate_ids` (modo evaluador, ≤ 100: devuelve cuáles cumplen, en el orden recibido) o `after` + `limit` (modo conductor: recorre por nombre canónico normalizado e `id`). Respuesta `items[]` (`id`, `position`) y `has_more`

Cuerpo (`ProductMatchRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `brand_ids` | array<UUID> | No | ≤ 100 elementos |
| `category_ids` | array<UUID> | No | ≤ 100 elementos |
| `include_descendants` | boolean | No | por defecto `false` |
| `identifier` | string \| null | No | ≥ 1 car.; ≤ 120 car. |
| `product_type` | string \| null | No | ≤ 20 car. |
| `status` | enum | No | `ACTIVE`, `INACTIVE`, `ALL`; por defecto `"ACTIVE"` |
| `has_image` | boolean \| null | No | — |
| `candidate_ids` | array<UUID> \| null | No | ≥ 1 elementos |
| `after` | MatchPosition \| null | No | — |
| `limit` | integer \| null | No | ≥ 1; ≤ 100 |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/match' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "brand_ids": [
      "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
    ],
    "category_ids": [
      "b583a629-3fe1-4575-8ba1-7314e10419cc"
    ],
    "include_descendants": false,
    "product_type": "GOOD",
    "status": "ACTIVE",
    "has_image": false,
    "after": {
      "k": [
        "display_name"
      ],
      "id": "30edd025-4af1-4849-8bce-cd240d55cdbb"
    },
    "limit": 20
  }'
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
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

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 49. `GET /products`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar y buscar productos |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros: `status`, `search` (≤ 200), `category_id` + `include_descendants`, `brand_id`, `manufacturer_organization_id`, `group_id`, `identifier` (≤ 120; código de barras), `attribute_filters` (repetible, `CODIGO:valor`, solo atributos filtrables: `422 ATTRIBUTE_NOT_FILTERABLE`), paginación. Ejemplo completo en [global_product_id](../parametros/global-product-id.md)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `category_id` | query | UUID \| null | No | — | Campo `id` de una categoría (operaciones 30 o 32) |
| `include_descendants` | query | boolean | No | por defecto `false` | — |
| `brand_id` | query | UUID \| null | No | — | Operación 16 |
| `manufacturer_organization_id` | query | UUID \| null | No | — | [organization_identity_id](../parametros/organization-identity-id.md) |
| `group_id` | query | UUID \| null | No | — | Campo `id` de un grupo (operaciones 82 u 84) |
| `identifier` | query | string \| null | No | ≤ 120 car. | — |
| `attribute_filters` | query | array<string> | No | por defecto `[]` — Filtros `CODIGO:valor` sobre atributos filtrables; repetible. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_ProductResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "product_type": "GOOD",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "description": "Analgésico y antipirético",
      "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "first_used_at": "2026-10-19T15:04:05Z",
      "first_use_source": "MANUAL",
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

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_ProductResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 50. `POST /products`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products` |
| Permiso | `perm:product-catalog:products:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: (catálogo global). Cuerpo (`ProductCreate`): `product_type` (`GOOD`), `canonical_name` (≤ 400), `base_unit_id` obligatorios; `description`, `global_brand_id`, `manufacturer_organization_id` opcionales. `201`; `warnings[]` puede avisar de productos parecidos

Cuerpo (`ProductCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `product_type` | string | Sí | — |
| `canonical_name` | string | Sí | ≤ 400 car. |
| `description` | string \| null | No | — |
| `global_brand_id` | UUID \| null | No | — |
| `manufacturer_organization_id` | UUID \| null | No | — |
| `base_unit_id` | UUID | Sí | — |

Cómo obtener los identificadores del cuerpo: `global_brand_id`: Operación 16; `manufacturer_organization_id`: [organization_identity_id](../parametros/organization-identity-id.md); `base_unit_id`: Operación 4.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "product_type": "GOOD",
    "canonical_name": "Acetaminofén 500 mg tableta",
    "description": "Analgésico y antipirético",
    "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
  }'
```

Ejemplo de respuesta `201` (`ProductResponse`; valores ilustrativos):

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
  "description": "Analgésico y antipirético",
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
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
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `ProductResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 51. `POST /products/batch-lookup`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Hasta 100 productos por id |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/batch-lookup` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"ids": [...]}` → `items[]` con `id`, `found`, `status`, `is_complete`, `eligible_for_adoption`, `first_used_at`

Cuerpo (`BatchLookupRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `ids` | array<UUID> | Sí | — — Entre 1 y 100 identificadores; los repetidos se ignoran. |

Cómo obtener los identificadores del cuerpo: `ids`: Identificadores obtenidos en listados previos.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```

Ejemplo de respuesta `200` (`ProductLookupResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "status": "ACTIVE",
      "is_complete": true,
      "eligible_for_adoption": true,
      "first_used_at": "2026-10-19T15:04:05Z"
    }
  ]
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductLookupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 52. `GET /products/by-identifier/{value}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Buscar por código escaneado |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/by-identifier/{value}` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Busca un código escaneado (GTIN, EAN, UPC, código de barras, IUM). Respuesta (`IdentifierLookupResponse`): `product` (ProductResponse), `presentation` (si el código es de una presentación), `identifier`, `is_current` (si el identificador está activo). `404` si no existe. Es la operación para el lector de códigos de barras del punto de venta

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `value` | ruta | string | Sí | — | Código leído por el lector de barras (GTIN, EAN, UPC, código interno o IUM) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/by-identifier/7702001234567' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`IdentifierLookupResponse`; valores ilustrativos):

```json
{
  "product": {
    "id": "b26a9b75-c56d-49ed-885d-6de55609a4c8",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "product_type": "GOOD",
    "canonical_name": "Acetaminofén 500 mg tableta",
    "description": "Analgésico y antipirético",
    "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "first_used_at": "2026-10-19T15:04:05Z",
    "first_use_source": "MANUAL",
    "completeness": {
      "is_complete": true,
      "issues": [],
      "missing_attribute_definition_ids": [],
      "out_of_classification_value_ids": []
    },
    "eligible_for_adoption": true,
    "warnings": [],
    "detail": null
  },
  "presentation": {
    "id": "92ebdac6-0502-44f7-8a34-472a07983702",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "code": "CJ100",
    "name": "Caja x 100",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false,
    "first_used_at": "2026-10-19T15:04:05Z",
    "first_use_source": "MANUAL",
    "eligible_for_adoption": true
  },
  "identifier": {
    "id": "276b9611-9ac8-42d7-8c71-ae5eb02a642a",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "identifier_type": "GTIN",
    "value": "7702001234567",
    "canonical_value": "7702001234567",
    "is_primary": true
  },
  "is_current": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `IdentifierLookupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 53. `GET /products/{product_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: `expand=detail` incluye todos los subrecursos

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `expand` | query | string \| null | No | — | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`ProductResponse`; valores ilustrativos):

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
  "description": "Analgésico y antipirético",
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
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
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 54. `PUT /products/{product_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`ProductUpdate`): `version`, `canonical_name`, `base_unit_id` obligatorios; `description`, `global_brand_id`, `manufacturer_organization_id`. `product_type` inmutable; `base_unit_id` bloqueada tras el primer uso

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`ProductUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `canonical_name` | string | Sí | ≤ 400 car. |
| `description` | string \| null | No | — |
| `global_brand_id` | UUID \| null | No | — |
| `manufacturer_organization_id` | UUID \| null | No | — |
| `base_unit_id` | UUID | Sí | — |

Cómo obtener los identificadores del cuerpo: `global_brand_id`: Operación 16; `manufacturer_organization_id`: [organization_identity_id](../parametros/organization-identity-id.md); `base_unit_id`: Operación 4.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "canonical_name": "Acetaminofén 500 mg tableta",
    "description": "Analgésico y antipirético",
    "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
    "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
  }'
```

Ejemplo de respuesta `200` (`ProductResponse`; valores ilustrativos):

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
  "description": "Analgésico y antipirético",
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
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
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 55. `GET /products/{product_id}/applicable-attributes`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Atributos aplicables |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/applicable-attributes` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array** de atributos aplicables según sus categorías (sin herencia): `attribute_definition_id`, `code`, `name`, `data_type`, `unit_of_measure_id`, `is_required`, `is_filterable`, `display_order`, `category_ids[]`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/applicable-attributes' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
    "code": "CONCENTRACION",
    "name": "Concentración",
    "data_type": "TEXT",
    "unit_of_measure_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "is_required": true,
    "is_filterable": true,
    "display_order": 1,
    "category_ids": [
      "b583a629-3fe1-4575-8ba1-7314e10419cc"
    ]
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 56. `GET /products/{product_id}/completeness`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Completitud |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/completeness` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: `CompletenessResponse`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/completeness' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CompletenessResponse`; valores ilustrativos):

```json
{
  "is_complete": true,
  "issues": [],
  "missing_attribute_definition_ids": [],
  "out_of_classification_value_ids": []
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `CompletenessResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 57. `POST /products/{product_id}/deactivate`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Inactivar producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: las empresas no podrán adoptarlo ni operar presentaciones nuevas; los productos empresariales ya adoptados muestran `global_status: INACTIVE`. Sin cascada sobre subrecursos. `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ProductResponse`; valores ilustrativos):

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
  "description": "Analgésico y antipirético",
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
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
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 58. `POST /products/{product_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/reactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ProductResponse`; valores ilustrativos):

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
  "description": "Analgésico y antipirético",
  "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "manufacturer_organization_id": "0f1e2d3c-4b5a-4968-8776-655443322111",
  "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
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
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Categorías del producto (operaciones 59–62)

Base `…/api/v1/products/{product_id}/categories`. Objeto `ProductCategoryResponse`: `id` (`association_id`), `global_product_id`, `global_category_id`, `is_primary`, `status`, `version`, trazabilidad.

### 59. `GET /products/{product_id}/categories`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Categorías del producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/categories' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
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
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 60. `POST /products/{product_id}/categories`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Asignar categoría |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo `{"global_category_id": "…"}`. La primera asignación queda como principal. `409 DUPLICATE_ASSOCIATION`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`ProductCategoryAssign`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `global_category_id` | UUID | Sí | — |

Cómo obtener los identificadores del cuerpo: `global_category_id`: Operación 30.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/categories' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_category_id": "0a1a164d-b834-4ea1-8413-d5b6fc5b5ef3"
  }'
```

Ejemplo de respuesta `201` (`ProductCategoryResponse`; valores ilustrativos):

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

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `ProductCategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 61. `POST /products/{product_id}/categories/{association_id}/set-primary`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Categoría principal |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories/{association_id}/set-primary` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`. Respuesta: **array** con todas las categorías del producto

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `association_id` | ruta | UUID | Sí | — | Campo `id` de la asociación (operación 59) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/categories/da6195d4-1082-43d8-8a1d-d8ea15ed6d17/set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
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
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 62. `POST /products/{product_id}/categories/{association_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Retirar categoría |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/categories/{association_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`ProductCategoryDeactivate`): `version` y `new_primary_association_id` (obligatorio si se retira la principal y quedan otras: `422 NEW_PRIMARY_REQUIRED`)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `association_id` | ruta | UUID | Sí | — | Campo `id` de la asociación (operación 59) |

Cuerpo (`ProductCategoryDeactivate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `new_primary_association_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `new_primary_association_id`: Operación 59.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/categories/da6195d4-1082-43d8-8a1d-d8ea15ed6d17/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`ProductCategoryResponse`; valores ilustrativos):

```json
{
  "id": "da6195d4-1082-43d8-8a1d-d8ea15ed6d17",
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

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `ProductCategoryResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Valores de atributo (operaciones 63–65)

Base `…/api/v1/products/{product_id}/attribute-values`. Objeto `AttributeValueResponse`: `id`, `global_product_id`, `attribute_definition_id`, `option_id`, `text_value`, `integer_value`, `decimal_value`, `boolean_value`, `date_value`, `out_of_classification` (el atributo ya no aplica por las categorías actuales), `version`, trazabilidad.

### 63. `GET /products/{product_id}/attribute-values`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Valores de atributo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/attribute-values` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/attribute-values' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
    "option_id": null,
    "text_value": "500 mg",
    "integer_value": null,
    "decimal_value": null,
    "boolean_value": null,
    "date_value": null,
    "out_of_classification": false
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 64. `PUT /products/{product_id}/attribute-values/{definition_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Registrar o reemplazar valor |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/attribute-values/{definition_id}` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`AttributeValuePut`): exactamente el campo de valor que corresponde al `data_type` (`option_id` para `OPTION`, `text_value`, `integer_value`, `decimal_value`, `boolean_value` o `date_value`; `422 VALUE_TYPE_MISMATCH`, `OPTION_NOT_IN_DEFINITION`) y `version` (obligatoria si el valor ya existe). El atributo debe aplicar al producto (`422 ATTRIBUTE_NOT_APPLICABLE`). `201` al crear, `200` al reemplazar

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |

Cuerpo (`AttributeValuePut`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `option_id` | UUID \| null | No | — |
| `text_value` | string \| null | No | — |
| `integer_value` | integer \| null | No | — |
| `decimal_value` | number \| string \| null | No | — |
| `boolean_value` | boolean \| null | No | — |
| `date_value` | date \| null | No | — |
| `version` | integer \| null | No | ≥ 1 |

Cómo obtener los identificadores del cuerpo: `option_id`: Campo `id` de una opción (operación 36).

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/attribute-values/28094980-356b-4592-8e9c-6d9fea57645d' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "text_value": "500 mg",
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AttributeValueResponse`; valores ilustrativos):

```json
{
  "id": "28094980-356b-4592-8e9c-6d9fea57645d",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "attribute_definition_id": "a3111396-177a-4ee4-89c9-912fc733af0e",
  "option_id": null,
  "text_value": "500 mg",
  "integer_value": null,
  "decimal_value": null,
  "boolean_value": null,
  "date_value": null,
  "out_of_classification": false
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AttributeValueResponse` |
| `201` | `AttributeValueResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 65. `DELETE /products/{product_id}/attribute-values/{definition_id}`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Retirar valor (borrado físico) |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/attribute-values/{definition_id}` |
| Permiso | `perm:product-catalog:products:delete` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: (borrado físico). `204`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `definition_id` | ruta | UUID | Sí | — | Campo `id` de una definición de atributo (operación 41) |
| `version` | query | integer | Sí | ≥ 1 | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS -X DELETE 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/attribute-values/28094980-356b-4592-8e9c-6d9fea57645d?version=1' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `204 No Content`: sin cuerpo.

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `204` | Sin cuerpo |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Presentaciones (operaciones 66–72)

Base `…/api/v1`. Objeto `PresentationResponse`: `id` (`global_product_presentation_id`), `global_product_id`, `code`, `name`, `packaging_type_id`, `base_quantity` (unidades base por presentación), `content_quantity`, `content_unit_id`, `display_order`, `is_base`, `first_used_at`, `first_use_source`, `eligible_for_adoption`, `status`, `version`, trazabilidad. Son las que una empresa adopta como [company_product_presentation_id](../parametros/company-product-presentation-id.md).

### 66. `POST /presentations/batch-lookup`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Hasta 100 presentaciones por id |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/presentations/batch-lookup` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"ids": [...]}` → `items[]` (`PresentationLookupItem`: `id`, `found`, `global_product_id`, `code`, `name`, `status`, `eligible_for_adoption`, `base_quantity`, `first_used_at`; todos nulos salvo `id` y `found: false` cuando no existe; verificado en el código)

Cuerpo (`BatchLookupRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `ids` | array<UUID> | Sí | — — Entre 1 y 100 identificadores; los repetidos se ignoran. |

Cómo obtener los identificadores del cuerpo: `ids`: Identificadores obtenidos en listados previos.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/presentations/batch-lookup' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      "ee206c92-4e16-41f4-8bc4-e37773a197f8"
    ]
  }'
```

Ejemplo de respuesta `200` (`PresentationLookupResponse`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "found": true,
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "code": "CJ100",
      "name": "Caja x 100",
      "status": "ACTIVE",
      "eligible_for_adoption": true,
      "base_quantity": "100",
      "first_used_at": "2026-10-19T15:04:05Z"
    }
  ]
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PresentationLookupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 67. `GET /products/{product_id}/presentations`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Presentaciones del producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "code": "CJ100",
    "name": "Caja x 100",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false,
    "first_used_at": "2026-10-19T15:04:05Z",
    "first_use_source": "MANUAL",
    "eligible_for_adoption": true
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 68. `POST /products/{product_id}/presentations`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear presentación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`PresentationCreate`): `code` (≤ 120), `name` (≤ 320) obligatorios; `packaging_type_id`, `base_quantity` (por defecto `1`; > 0), `content_quantity`, `content_unit_id`, `display_order`, `is_base` (`false`). Reglas: una sola presentación base por producto (`409 BASE_PRESENTATION_EXISTS`) y la base debe tener `base_quantity` 1 (`422 BASE_QUANTITY_MUST_BE_ONE`); `code` único por producto

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`PresentationCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 120 car. |
| `name` | string | Sí | ≤ 320 car. |
| `packaging_type_id` | UUID \| null | No | — |
| `base_quantity` | number \| string | No | por defecto `"1"` |
| `content_quantity` | number \| string \| null | No | — |
| `content_unit_id` | UUID \| null | No | — |
| `display_order` | integer | No | ≥ 0; ≤ 32767; por defecto `0` |
| `is_base` | boolean | No | por defecto `false` |

Cómo obtener los identificadores del cuerpo: `packaging_type_id`: Operación 10; `content_unit_id`: Operación 4.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CJ100",
    "name": "Caja x 100",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "display_order": 1,
    "is_base": false
  }'
```

Ejemplo de respuesta `201` (`PresentationResponse`; valores ilustrativos):

```json
{
  "id": "6f4c7add-bb72-425c-8eb1-a0d29a622b2f",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
  "eligible_for_adoption": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `PresentationResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 69. `GET /presentations/{presentation_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar presentación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/presentations/{presentation_id}` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `presentation_id` | ruta | UUID | Sí | — | Campo `id` de una presentación del producto (operación 67); es el `global_product_presentation_id` de otros servicios |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
  "eligible_for_adoption": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PresentationResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 70. `PUT /presentations/{presentation_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar presentación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/presentations/{presentation_id}` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `display_order`, `base_quantity` obligatorios; `packaging_type_id`, `content_quantity`, `content_unit_id`, `is_base`. Tras el primer uso la presentación queda bloqueada en sus campos de cantidad (`422 PRESENTATION_LOCKED_BY_FIRST_USE`)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `presentation_id` | ruta | UUID | Sí | — | Campo `id` de una presentación del producto (operación 67); es el `global_product_presentation_id` de otros servicios |

Cuerpo (`PresentationUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 320 car. |
| `display_order` | integer | Sí | ≥ 0; ≤ 32767 |
| `packaging_type_id` | UUID \| null | No | — |
| `base_quantity` | number \| string | Sí | — |
| `content_quantity` | number \| string \| null | No | — |
| `content_unit_id` | UUID \| null | No | — |
| `is_base` | boolean | No | por defecto `false` |

Cómo obtener los identificadores del cuerpo: `packaging_type_id`: Operación 10; `content_unit_id`: Operación 4.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Caja x 100",
    "display_order": 1,
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "is_base": false
  }'
```

Ejemplo de respuesta `200` (`PresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
  "eligible_for_adoption": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PresentationResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 71. `POST /presentations/{presentation_id}/deactivate`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Inactivar presentación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/presentations/{presentation_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: las presentaciones empresariales derivadas dejan de ser elegibles para líneas nuevas. `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `presentation_id` | ruta | UUID | Sí | — | Campo `id` de una presentación del producto (operación 67); es el `global_product_presentation_id` de otros servicios |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
  "eligible_for_adoption": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PresentationResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 72. `POST /presentations/{presentation_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar presentación |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/presentations/{presentation_id}/reactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `presentation_id` | ruta | UUID | Sí | — | Campo `id` de una presentación del producto (operación 67); es el `global_product_presentation_id` de otros servicios |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/presentations/1b62e4f0-de38-42da-8531-ee9fe6cf0d07/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`PresentationResponse`; valores ilustrativos):

```json
{
  "id": "1b62e4f0-de38-42da-8531-ee9fe6cf0d07",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "content_quantity": null,
  "content_unit_id": null,
  "display_order": 1,
  "is_base": false,
  "first_used_at": "2026-10-19T15:04:05Z",
  "first_use_source": "MANUAL",
  "eligible_for_adoption": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PresentationResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Identificadores (operaciones 73–77)

Base `…/api/v1/products/{product_id}/identifiers`. Objeto `IdentifierResponse`: `id`, `global_product_id`, `global_product_presentation_id`, `identifier_type` (`GTIN`, `EAN`, `UPC`, `BARCODE`, `OTHER`, `IUM`), `value`, `canonical_value`, `is_primary`, `status`, `version`, trazabilidad.

### 73. `GET /products/{product_id}/identifiers`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Identificadores |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "identifier_type": "GTIN",
    "value": "7702001234567",
    "canonical_value": "7702001234567",
    "is_primary": true
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 74. `POST /products/{product_id}/identifiers`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Registrar identificador |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`IdentifierCreate`): `identifier_type`, `value` (≤ 200) obligatorios; `global_product_presentation_id` (obligatorio para `IUM`: `422 IUM_REQUIRES_PRESENTATION`; debe ser del producto: `422 PRESENTATION_OF_OTHER_PRODUCT`), `is_primary`. Validaciones: formato y dígito de control GTIN/EAN/UPC (`422 INVALID_GTIN_FORMAT`, `INVALID_CHECK_DIGIT`), un `BARCODE` que es un GTIN válido se rechaza (`422 BARCODE_IS_GTIN`), formato IUM (`422 INVALID_IUM_FORMAT`); el valor canónico es único en todo el catálogo (`409 IDENTIFIER_COLLISION`)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`IdentifierCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `identifier_type` | enum | Sí | `GTIN`, `EAN`, `UPC`, `BARCODE`, `OTHER`, `IUM` |
| `value` | string | Sí | ≤ 200 car. |
| `global_product_presentation_id` | UUID \| null | No | — |
| `is_primary` | boolean | No | por defecto `false` |

Cómo obtener los identificadores del cuerpo: `global_product_presentation_id`: Operación 67.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "identifier_type": "GTIN",
    "value": "7702001234567",
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "is_primary": true
  }'
```

Ejemplo de respuesta `201` (`IdentifierResponse`; valores ilustrativos):

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
  "identifier_type": "GTIN",
  "value": "7702001234567",
  "canonical_value": "7702001234567",
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `IdentifierResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 75. `POST /products/{product_id}/identifiers/{identifier_id}/set-primary`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Identificador principal |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers/{identifier_id}/set-primary` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Principal de su tipo y contexto (producto o presentación). `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `identifier_id` | ruta | UUID | Sí | — | Campo `id` de un identificador (operación 73) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers/82bc7e72-1f3a-4a09-86de-bc5dfb158a91/set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`IdentifierResponse`; valores ilustrativos):

```json
{
  "id": "82bc7e72-1f3a-4a09-86de-bc5dfb158a91",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "identifier_type": "GTIN",
  "value": "7702001234567",
  "canonical_value": "7702001234567",
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `IdentifierResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 76. `POST /products/{product_id}/identifiers/{identifier_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar identificador |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers/{identifier_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: El código no se libera para otros productos. `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `identifier_id` | ruta | UUID | Sí | — | Campo `id` de un identificador (operación 73) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers/82bc7e72-1f3a-4a09-86de-bc5dfb158a91/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`IdentifierResponse`; valores ilustrativos):

```json
{
  "id": "82bc7e72-1f3a-4a09-86de-bc5dfb158a91",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "identifier_type": "GTIN",
  "value": "7702001234567",
  "canonical_value": "7702001234567",
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `IdentifierResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 77. `POST /products/{product_id}/identifiers/{identifier_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar identificador |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/identifiers/{identifier_id}/reactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `identifier_id` | ruta | UUID | Sí | — | Campo `id` de un identificador (operación 73) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/identifiers/82bc7e72-1f3a-4a09-86de-bc5dfb158a91/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`IdentifierResponse`; valores ilustrativos):

```json
{
  "id": "82bc7e72-1f3a-4a09-86de-bc5dfb158a91",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "identifier_type": "GTIN",
  "value": "7702001234567",
  "canonical_value": "7702001234567",
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `IdentifierResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Grupos del producto (operaciones 78–81)

Base `…/api/v1/products/{product_id}/group-assignments`. Objeto `GroupAssignmentResponse`: `id`, `global_product_id`, `global_product_group_id`, `group_type_id`, `status`, `version`, trazabilidad.

### 78. `GET /products/{product_id}/group-assignments`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Grupos del producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/group-assignments` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtro `status`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/group-assignments' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "global_product_group_id": "ca9b1358-6de2-47f7-8da8-f735f6dc74fc",
    "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2"
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 79. `POST /products/{product_id}/group-assignments`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Asignar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/group-assignments` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo `{"global_product_group_id": "…"}`. Si el tipo de grupo no admite múltiples (`allows_multiple: false`), un segundo grupo del mismo tipo → `409 GROUP_TYPE_SINGLE_VALUE`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`GroupAssignmentCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `global_product_group_id` | UUID | Sí | — |

Cómo obtener los identificadores del cuerpo: `global_product_group_id`: Operación 82.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/group-assignments' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_product_group_id": "ca9b1358-6de2-47f7-8da8-f735f6dc74fc"
  }'
```

Ejemplo de respuesta `201` (`GroupAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "6aa81857-522f-412e-8425-bf4e4306ed6a",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_group_id": "ca9b1358-6de2-47f7-8da8-f735f6dc74fc",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `GroupAssignmentResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 80. `POST /products/{product_id}/group-assignments/{assignment_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Retirar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/group-assignments/{assignment_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `assignment_id` | ruta | UUID | Sí | — | Campo `id` de una asignación (operación 78) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/group-assignments/93c4899b-7130-4feb-878a-e72c2e3b9d97/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_group_id": "ca9b1358-6de2-47f7-8da8-f735f6dc74fc",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupAssignmentResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 81. `POST /products/{product_id}/group-assignments/{assignment_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/group-assignments/{assignment_id}/reactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`; `409 MULTIPLE_ASSIGNMENTS_EXIST` si violaría la unicidad del tipo

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `assignment_id` | ruta | UUID | Sí | — | Campo `id` de una asignación (operación 78) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/group-assignments/93c4899b-7130-4feb-878a-e72c2e3b9d97/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupAssignmentResponse`; valores ilustrativos):

```json
{
  "id": "93c4899b-7130-4feb-878a-e72c2e3b9d97",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "global_product_group_id": "ca9b1358-6de2-47f7-8da8-f735f6dc74fc",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupAssignmentResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Tipos de grupo y grupos (operaciones 82–95)

Base `…/api/v1`. `GroupTypeResponse`: `id`, `code`, `name`, `description`, `allows_multiple`, `display_order`, `status`, `version`. `GroupResponse`: `id`, `group_type_id`, `parent_group_id`, `code`, `name`, `description`, `status`, `version`. Agrupaciones libres de productos (líneas, colecciones, familias…).

### 82. `GET /group-types/{group_type_id}/groups`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Grupos de un tipo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{group_type_id}/groups` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, `parent_group_id`, `root_only`, paginación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_type_id` | ruta | UUID | Sí | — | Campo `id` de un tipo de grupo (operación 90) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `parent_group_id` | query | UUID \| null | No | — | Operación 82 |
| `root_only` | query | boolean | No | por defecto `false` | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/be6163f9-76dc-48c4-892f-c4bf749904f2/groups?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_GroupResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
      "parent_group_id": null,
      "code": "OTC",
      "name": "Venta libre",
      "description": "Descripción ilustrativa"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_GroupResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 83. `POST /group-types/{group_type_id}/groups`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{group_type_id}/groups` |
| Permiso | `perm:product-catalog:group-types:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`GroupCreate`): `code` (≤ 100), `name` (≤ 320), `description`, `parent_group_id` (del mismo tipo)

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_type_id` | ruta | UUID | Sí | — | Campo `id` de un tipo de grupo (operación 90) |

Cuerpo (`GroupCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 100 car. |
| `name` | string | Sí | ≤ 320 car. |
| `description` | string \| null | No | — |
| `parent_group_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `parent_group_id`: Operación 82.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/be6163f9-76dc-48c4-892f-c4bf749904f2/groups' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "OTC",
    "name": "Venta libre",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `201` (`GroupResponse`; valores ilustrativos):

```json
{
  "id": "8b16ae73-5e62-4fa4-88a2-b9398035f7a3",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
  "parent_group_id": null,
  "code": "OTC",
  "name": "Venta libre",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `GroupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 84. `GET /groups/{group_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GroupResponse`; valores ilustrativos):

```json
{
  "id": "0e939a4f-fd3a-4cd7-84dd-3b50147b4353",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
  "parent_group_id": null,
  "code": "OTC",
  "name": "Venta libre",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 85. `PUT /groups/{group_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}` |
| Permiso | `perm:product-catalog:group-types:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`, `parent_group_id`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Cuerpo (`GroupUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 320 car. |
| `description` | string \| null | No | — |
| `parent_group_id` | UUID \| null | No | — |

Cómo obtener los identificadores del cuerpo: `parent_group_id`: Operación 82.

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa"
  }'
```

Ejemplo de respuesta `200` (`GroupResponse`; valores ilustrativos):

```json
{
  "id": "0e939a4f-fd3a-4cd7-84dd-3b50147b4353",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
  "parent_group_id": null,
  "code": "OTC",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 86. `GET /groups/{group_id}/children`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Hijos directos |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}/children` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353/children' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
    "parent_group_id": null,
    "code": "OTC",
    "name": "Venta libre",
    "description": "Descripción ilustrativa"
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 87. `GET /groups/{group_id}/ancestors`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Ancestros |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}/ancestors` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353/ancestors' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
    "parent_group_id": null,
    "code": "OTC",
    "name": "Venta libre",
    "description": "Descripción ilustrativa"
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 88. `POST /groups/{group_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}/deactivate` |
| Permiso | `perm:product-catalog:group-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `409 HAS_ACTIVE_CHILDREN`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupResponse`; valores ilustrativos):

```json
{
  "id": "0e939a4f-fd3a-4cd7-84dd-3b50147b4353",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
  "parent_group_id": null,
  "code": "OTC",
  "name": "Venta libre",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 89. `POST /groups/{group_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/groups/{group_id}/reactivate` |
| Permiso | `perm:product-catalog:group-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `group_id` | ruta | UUID | Sí | — | Campo `id` de un grupo (operaciones 82 u 84) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/groups/0e939a4f-fd3a-4cd7-84dd-3b50147b4353/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupResponse`; valores ilustrativos):

```json
{
  "id": "0e939a4f-fd3a-4cd7-84dd-3b50147b4353",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "group_type_id": "be6163f9-76dc-48c4-892f-c4bf749904f2",
  "parent_group_id": null,
  "code": "OTC",
  "name": "Venta libre",
  "description": "Descripción ilustrativa"
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 90. `GET /group-types`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Listar tipos de grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: Filtros `status`, `code`, `search`, paginación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `code` | query | string \| null | No | ≤ 100 car. | — |
| `search` | query | string \| null | No | ≤ 200 car. | — |
| `page` | query | integer | No | ≥ 1; por defecto `1` — Número de página solicitado. | — |
| `page_size` | query | integer | No | ≥ 1; ≤ 100; por defecto `20` — Cantidad de registros por página. | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`PaginatedResponse_GroupTypeResponse_`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "code": "LINEA",
      "name": "Línea comercial",
      "description": "Descripción ilustrativa",
      "allows_multiple": true,
      "display_order": 1
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `PaginatedResponse_GroupTypeResponse_` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 91. `POST /group-types`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Crear tipo de grupo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types` |
| Permiso | `perm:product-catalog:group-types:create` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`GroupTypeCreate`): `code` (≤ 100), `name` (≤ 240), `description`, `allows_multiple` (`false`), `display_order` (0–32767)

Cuerpo (`GroupTypeCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | Sí | ≤ 100 car. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `allows_multiple` | boolean | No | por defecto `false` |
| `display_order` | integer | No | ≥ 0; ≤ 32767; por defecto `0` |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "LINEA",
    "name": "Línea comercial",
    "description": "Descripción ilustrativa",
    "allows_multiple": true,
    "display_order": 1
  }'
```

Ejemplo de respuesta `201` (`GroupTypeResponse`; valores ilustrativos):

```json
{
  "id": "3b99ec64-d818-4fad-854a-5325d0b5cb5c",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "LINEA",
  "name": "Línea comercial",
  "description": "Descripción ilustrativa",
  "allows_multiple": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `GroupTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 92. `GET /group-types/{item_id}`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Consultar tipo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{item_id}` |
| Permiso | `perm:product-catalog:group-types:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 90 |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`GroupTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "LINEA",
  "name": "Línea comercial",
  "description": "Descripción ilustrativa",
  "allows_multiple": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 93. `PUT /group-types/{item_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar tipo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{item_id}` |
| Permiso | `perm:product-catalog:group-types:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `name`, `description`, `allows_multiple`, `display_order`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 90 |

Cuerpo (`GroupTypeUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `name` | string | Sí | ≤ 240 car. |
| `description` | string \| null | No | — |
| `allows_multiple` | boolean | Sí | — |
| `display_order` | integer | Sí | ≥ 0; ≤ 32767 |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/82bfda79-62fd-42f5-8163-ae45886c4c62' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "name": "Acetaminofén 500 mg",
    "description": "Descripción ilustrativa",
    "allows_multiple": true,
    "display_order": 1
  }'
```

Ejemplo de respuesta `200` (`GroupTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "LINEA",
  "name": "Acetaminofén 500 mg",
  "description": "Descripción ilustrativa",
  "allows_multiple": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 94. `POST /group-types/{item_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar tipo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{item_id}/deactivate` |
| Permiso | `perm:product-catalog:group-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 90 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/82bfda79-62fd-42f5-8163-ae45886c4c62/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "LINEA",
  "name": "Línea comercial",
  "description": "Descripción ilustrativa",
  "allows_multiple": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 95. `POST /group-types/{item_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar tipo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/group-types/{item_id}/reactivate` |
| Permiso | `perm:product-catalog:group-types:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `item_id` | ruta | UUID | Sí | — | Campo `id` de un elemento de la operación 90 |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/group-types/82bfda79-62fd-42f5-8163-ae45886c4c62/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`GroupTypeResponse`; valores ilustrativos):

```json
{
  "id": "82bfda79-62fd-42f5-8163-ae45886c4c62",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "code": "LINEA",
  "name": "Línea comercial",
  "description": "Descripción ilustrativa",
  "allows_multiple": true,
  "display_order": 1
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `GroupTypeResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Activos (imágenes y documentos) (operaciones 96–102)

Base `…/api/v1/products/{product_id}/assets`. Objeto `AssetResponse`: `id`, `global_product_id`, `asset_type` (`IMAGE`, `TECHNICAL_SHEET`, `MANUAL`, `CERTIFICATE`, `OTHER`), `file_name`, `storage_uri`, `mime_type`, `is_primary`, `status`, `version`, trazabilidad. Product Catalog guarda **solo la referencia** al archivo, nunca el binario: la carga al almacenamiento de objetos de SIO se hace por fuera de esta API (**NO VERIFICADO** el mecanismo disponible en Render para el frontend).

**Imagen principal pública.** El código incluye una ruta pública sin token, `GET /api/v1/public/product-images?ref=<referencia firmada>`, que entrega la imagen principal (`IMAGE`, `ACTIVE`, JPEG/PNG/WebP almacenada en SIO) con caché inmutable y `ETag`; cualquier referencia inválida responde el mismo `404` vacío. Es la URL que Product Inventory Query devuelve en `image_url`. Solo existe cuando el servicio tiene configurados el secreto de firma y la URL pública base; **no aparece en el contrato desplegado en Render el 2026-10-19**, por lo que en ese entorno `image_url` llega `null` y hay que usar la operación 98 con token (**NO VERIFICADO** si se habilitará).

### 96. `GET /products/{product_id}/assets`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Activos del producto |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization` |

Notas: **Array**; filtros `status`, `asset_type`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `status` | query | string \| null | No | patrón `^(ACTIVE|INACTIVE)$` | — |
| `asset_type` | query | enum \| null | No | `IMAGE`, `TECHNICAL_SHEET`, `MANUAL`, `CERTIFICATE`, `OTHER` | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`None`; valores ilustrativos):

```json
[
  {
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "asset_type": "IMAGE",
    "file_name": "acetaminofen-500.png",
    "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
    "mime_type": null,
    "is_primary": true
  }
]
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Successful Response |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 97. `POST /products/{product_id}/assets`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Registrar activo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Cuerpo (`AssetCreate`): `asset_type`, `file_name` (≤ 510), `storage_uri` (≤ 4000; URI absoluto, por ejemplo `s3://<bucket>/<clave>` en el almacenamiento de SIO o una URL externa; `422 INVALID_STORAGE_URI`), `mime_type` (≤ 240), `is_primary` (`false`). `201`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`AssetCreate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `asset_type` | enum | Sí | `IMAGE`, `TECHNICAL_SHEET`, `MANUAL`, `CERTIFICATE`, `OTHER` |
| `file_name` | string | Sí | ≤ 510 car. |
| `storage_uri` | string | Sí | ≤ 4000 car. |
| `mime_type` | string \| null | No | ≤ 240 car. |
| `is_primary` | boolean | No | por defecto `false` |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_type": "IMAGE",
    "file_name": "acetaminofen-500.png",
    "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
    "is_primary": true
  }'
```

Ejemplo de respuesta `201` (`AssetResponse`; valores ilustrativos):

```json
{
  "id": "4c8291aa-edb7-46e7-8e38-83d456610944",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "asset_type": "IMAGE",
  "file_name": "acetaminofen-500.png",
  "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
  "mime_type": null,
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `201` | `AssetResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 98. `GET /products/{product_id}/assets/{asset_id}/content`

| | |
|---|---|
| Clasificación | `READ` |
| Descripción | Descargar contenido |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets/{asset_id}/content` |
| Permiso | `perm:product-catalog:products:read` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `if-none-match` (opcional) |

Notas: Descarga en *streaming* el contenido **solo si** el activo está en el almacenamiento de SIO. Cabecera opcional `If-None-Match` con el `ETag` previo → `304`. Respuesta `200` `image/*` o `application/octet-stream`; `404` si no existe o no tiene contenido; `409 ASSET_CONTENT_NOT_STORED` si referencia un recurso externo; `503` si el almacenamiento no responde

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `asset_id` | ruta | UUID | Sí | — | Campo `id` de un activo (operación 96) |
| `if-none-match` | cabecera | string \| null | No | — | — |

Esta operación no recibe cuerpo.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets/51c6d5db-c2de-4c51-8679-1d3108bd0af3/content' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200`: contenido binario (`image/*`), no JSON.

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | Contenido del activo |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 99. `PUT /products/{product_id}/assets/{asset_id}`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Modificar metadatos |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets/{asset_id}` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `version`, `file_name`, `storage_uri`, `mime_type`. `asset_type` inmutable

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `asset_id` | ruta | UUID | Sí | — | Campo `id` de un activo (operación 96) |

Cuerpo (`AssetUpdate`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |
| `file_name` | string | Sí | ≤ 510 car. |
| `storage_uri` | string | Sí | ≤ 4000 car. |
| `mime_type` | string \| null | No | ≤ 240 car. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X PUT 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets/51c6d5db-c2de-4c51-8679-1d3108bd0af3' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1,
    "file_name": "acetaminofen-500.png",
    "storage_uri": "s3://sio-product-assets/acetaminofen-500.png"
  }'
```

Ejemplo de respuesta `200` (`AssetResponse`; valores ilustrativos):

```json
{
  "id": "51c6d5db-c2de-4c51-8679-1d3108bd0af3",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "asset_type": "IMAGE",
  "file_name": "acetaminofen-500.png",
  "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
  "mime_type": null,
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AssetResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 100. `POST /products/{product_id}/assets/{asset_id}/set-primary`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Activo principal |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets/{asset_id}/set-primary` |
| Permiso | `perm:product-catalog:products:update` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Principal de su tipo. `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `asset_id` | ruta | UUID | Sí | — | Campo `id` de un activo (operación 96) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets/51c6d5db-c2de-4c51-8679-1d3108bd0af3/set-primary' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AssetResponse`; valores ilustrativos):

```json
{
  "id": "51c6d5db-c2de-4c51-8679-1d3108bd0af3",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "asset_type": "IMAGE",
  "file_name": "acetaminofen-500.png",
  "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
  "mime_type": null,
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AssetResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 101. `POST /products/{product_id}/assets/{asset_id}/deactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Inactivar activo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets/{asset_id}/deactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: El archivo externo no se borra. `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `asset_id` | ruta | UUID | Sí | — | Campo `id` de un activo (operación 96) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets/51c6d5db-c2de-4c51-8679-1d3108bd0af3/deactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AssetResponse`; valores ilustrativos):

```json
{
  "id": "51c6d5db-c2de-4c51-8679-1d3108bd0af3",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "asset_type": "IMAGE",
  "file_name": "acetaminofen-500.png",
  "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
  "mime_type": null,
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AssetResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 102. `POST /products/{product_id}/assets/{asset_id}/reactivate`

| | |
|---|---|
| Clasificación | `WRITE` |
| Descripción | Reactivar activo |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/assets/{asset_id}/reactivate` |
| Permiso | `perm:product-catalog:products:deactivate` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: `{"version": n}`

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |
| `asset_id` | ruta | UUID | Sí | — | Campo `id` de un activo (operación 96) |

Cuerpo (`VersionRequest`; rechaza campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `version` | integer | Sí | ≥ 1 — Versión esperada del registro. |

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/assets/51c6d5db-c2de-4c51-8679-1d3108bd0af3/reactivate' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "version": 1
  }'
```

Ejemplo de respuesta `200` (`AssetResponse`; valores ilustrativos):

```json
{
  "id": "51c6d5db-c2de-4c51-8679-1d3108bd0af3",
  "version": 1,
  "created_at": "2026-10-19T15:04:05Z",
  "updated_at": "2026-10-19T15:04:05Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "status": "ACTIVE",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "asset_type": "IMAGE",
  "file_name": "acetaminofen-500.png",
  "storage_uri": "s3://sio-product-assets/acetaminofen-500.png",
  "mime_type": null,
  "is_primary": true
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `AssetResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `409 PRODUCT_CATALOG.VERSION_CONFLICT` | `version` distinta de la actual |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### Primer uso (operaciones 103–104)

Base `…/api/v1/products/{product_id}/first-use`. Respuesta (`FirstUseResponse`): `global_product_id`, `product_first_used_at`, `product_first_use_source`, `global_product_presentation_id`, `presentation_first_used_at`, `presentation_first_use_source`.

### 103. `POST /products/{product_id}/first-use`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Primer uso por adopción |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/first-use` |
| Permiso | `perm:product-catalog:first-use:register` (cuenta técnica)` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: (marca irreversible). Permiso `first-use:register`; lo invoca Commercial Relationship con su cuenta técnica al adoptar un producto o presentación. Cuerpo opcional `{"global_product_presentation_id": "…"}`. Exige elegibilidad si falta alguna marca (`422 NOT_ELIGIBLE_FOR_FIRST_USE`). Idempotente. **No usar desde el frontend**

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`JSON`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/first-use' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d"
  }'
```

Ejemplo de respuesta `200` (`FirstUseResponse`; valores ilustrativos):

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "product_first_used_at": "2026-10-19T15:04:05Z",
  "product_first_use_source": "MANUAL",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "presentation_first_used_at": null,
  "presentation_first_use_source": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `FirstUseResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

### 104. `POST /products/{product_id}/first-use/manual`

| | |
|---|---|
| Clasificación | `HIGH_RISK` |
| Descripción | Primer uso manual |
| URL | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/first-use/manual` |
| Permiso | `perm:product-catalog:first-use:register-manual` |
| Alcance | Global (catálogo compartido por todas las empresas) |
| Cabeceras | `Authorization`, `Content-Type: application/json` |

Notas: Permiso `first-use:register-manual` (administradores). Mismo cuerpo; no exige elegibilidad. Tras el primer uso quedan bloqueadas la unidad base del producto y las cantidades de la presentación

Parámetros:

| Nombre | Dónde | Tipo | Obligatorio | Validación | Cómo obtenerlo |
|---|---|---|---|---|---|
| `product_id` | ruta | UUID | Sí | — | [global_product_id](../parametros/global-product-id.md) |

Cuerpo (`JSON`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|

Ejemplo de solicitud (valores ilustrativos):

```bash
curl -sS -X POST 'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/first-use/manual' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d"
  }'
```

Ejemplo de respuesta `200` (`FirstUseResponse`; valores ilustrativos):

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "product_first_used_at": "2026-10-19T15:04:05Z",
  "product_first_use_source": "MANUAL",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "presentation_first_used_at": null,
  "presentation_first_use_source": null
}
```

Códigos HTTP:

| HTTP | Significado |
|---|---|
| `200` | `FirstUseResponse` |
| `401` | Token ausente o inválido ([Autenticación](../guias/autenticacion.md)) |
| `403 PRODUCT_CATALOG.FORBIDDEN` | Sin el permiso indicado |
| `404 PRODUCT_CATALOG.NOT_FOUND` | El recurso de la ruta no existe |
| `422 PRODUCT_CATALOG.VALIDATION_ERROR` | Datos inválidos; `errors[]` indica el campo. Otros códigos `422`/`409` propios en las notas |
| `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | `dependency`: `database`, `party-identity` o almacenamiento |

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 PRODUCT_CATALOG.FORBIDDEN` en inactivar/reactivar | Falta la acción `deactivate` (los supervisores no la tienen por comodín) | Solo administradores |
| `409 PRODUCT_CATALOG.DUPLICATE_CODE` / `CODE_USED_BY_*` | Código repetido | Elegir otro código |
| `409 …IDENTIFIER_COLLISION` | El código de barras ya pertenece a otro producto o presentación | Buscar con la operación 52 |
| `422 …INVALID_GTIN_FORMAT` / `INVALID_CHECK_DIGIT` | GTIN/EAN/UPC inválido | Verificar el dígito de control |
| `422 …ATTRIBUTE_NOT_APPLICABLE` / `VALUE_TYPE_MISMATCH` | Atributo fuera de las categorías del producto o valor de tipo incorrecto | Usar la operación 55 para saber qué atributos aplican |
| `422 …BASE_UNIT_LOCKED_BY_FIRST_USE` / `PRESENTATION_LOCKED_BY_FIRST_USE` | El producto ya fue adoptado | Crear una presentación nueva en lugar de modificar |
| `409 …BASE_PRESENTATION_EXISTS` / `422 BASE_QUANTITY_MUST_BE_ONE` | Reglas de la presentación base | Una sola base con cantidad 1 |
| `409 …HAS_ACTIVE_CHILDREN` / `422 HIERARCHY_CYCLE` / `PARENT_INACTIVE` | Jerarquías | Revisar padre e hijos |
| `409 …VERSION_CONFLICT` | Versión desactualizada | Recargar |
| `400 …MALFORMED_REQUEST` | Parámetro de ruta o consulta no interpretable (por ejemplo UUID mal formado) | Corregir la URL |

## Dependencias

| Servicio | Uso |
|---|---|
| Party Identity | Validar el fabricante (`manufacturer_organization_id`) con el token del usuario |
| Almacenamiento de objetos de SIO | Contenido de los activos e imágenes públicas |
| Commercial Relationship | Adopta productos y presentaciones y registra el primer uso (cuenta técnica) |
| Product Inventory Query, Sales, Purchase, Inventory, Business Reporting | Consumidores de datos globales (resúmenes, presentaciones, unidades) |
| Audit | Eventos de auditoría |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 104 |
| Operaciones documentadas | 104 |
| Permisos contrastados con el código | Sí (`api/simple_catalog_router.py`, `units_of_measure.py`, `categories.py`, `attribute_definitions.py`, `group_types.py`, `products.py`, `product_summaries.py`, `product_categories.py`, `product_attribute_values.py`, `presentations.py`, `identifiers.py`, `product_group_assignments.py`, `assets.py`, `first_use.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado; `application/exceptions.py`; docstrings de los servicios) |
| Pendiente | Mecanismo de carga de archivos al almacenamiento; disponibilidad de la ruta pública de imágenes en Render; códigos exactos de `completeness.issues[]` (NO VERIFICADO) |
| Verificado | Estructura de `PresentationLookupItem` (operación 66) |

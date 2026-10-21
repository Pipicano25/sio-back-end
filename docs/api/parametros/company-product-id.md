# Parámetro `company_product_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **producto adoptado por una empresa**: la versión empresarial (código interno, nombre comercial, moneda, control de inventario) de un producto del catálogo global. Ventas, compras y existencias trabajan con este identificador, no con el producto global |
| Nombre en las rutas y cuerpos | `company_product_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí en cada línea de venta y de compra, y en consultas de existencias por producto |
| Ejemplo (ficticio) | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` |
| Quién lo genera | Commercial Relationship, al adoptar el producto global (`id` de la respuesta) |
| Alcance | Empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación y búsqueda, los productos que la empresa ha adoptado del catálogo global, con su código interno, nombre, moneda, banderas de inventario y de compra/venta y estado. Por defecto solo `ACTIVE`. Es la fuente de `company_product_id` para líneas de venta y compra, inventario y precios. Ficha técnica: [Commercial Relationship 3](../servicios/commercial-relationship.md#3-get-companiescompany_idcompany-products); guía principal: [Productos y precios, API 9](../principales/productos-y-precios.md#9-buscar-y-listar-los-productos-de-la-empresa).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-products` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `is_purchasable`, `is_sellable`, `inventory_control_enabled` (boolean), `global_product_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_products:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products?is_sellable=true&status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[CompanyProductResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-05T08:00:00Z",
      "updated_at": "2026-02-05T08:00:00Z",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "display_name": "Acetaminofén 500 mg",
      "short_name": "Acetaminofén",
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": false,
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

**Campo exacto:** `items[].id`. Para vender, filtra `is_sellable=true`; para comprar, `is_purchasable=true`. `global_product_id` enlaza con el [producto del catálogo global](global-product-id.md). `purchase_tax_percentage` es la tasa de impuesto de compra con 4 decimales; `null` significa sin configurar y Compras no confirmará compras del producto hasta configurarla con la [API 13 de Productos y precios](../principales/productos-y-precios.md#13-configurar-el-impuesto-de-compra-del-producto). Un producto concreto se consulta con la [API 10](../principales/productos-y-precios.md#10-consultar-un-producto-de-la-empresa).

**Alternativa para pantallas de consulta:** [Product Inventory Query](../servicios/product-inventory-query.md) devuelve en una sola llamada el producto empresarial con precios y existencias (`GET /companies/{company_id}/product-overviews`); allí el identificador aparece también como `company_product_id`.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_products:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 100, `status` o un booleano inválido, UUID mal formado | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden (`dependency` lo indica) | Reintentar más tarde |

## Si el producto no está adoptado todavía (operación `WRITE`)

1. Localiza el producto en el catálogo global: [global_product_id](global-product-id.md).
2. Adóptalo en la empresa:

**¿Qué hace la API de adopción?** Crea el producto empresarial a partir de un producto del catálogo global elegible, con código interno único, nombre propio, moneda y banderas de inventario y comerciales. Devuelve `201` con el producto empresarial; su `id` es el `company_product_id`. No adopta sus presentaciones y deja el impuesto de compra sin configurar. Ficha técnica: [Commercial Relationship 4](../servicios/commercial-relationship.md#4-post-companiescompany_idcompany-products); guía principal: [Productos y precios, API 8](../principales/productos-y-precios.md#8-adoptar-un-producto-global-en-la-empresa).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-products` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` |
| Permiso | `perm:commercial-relationship:company_products:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanyProductCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `global_product_id` | UUID | Sí | Debe existir en Product Catalog, estar `ACTIVE` y ser elegible para adopción; no adoptado antes por la empresa |
| `internal_code` | string | Sí | 1 a 60 caracteres; se recortan espacios; único por empresa |
| `reference_code` | string \| null | No | máx. 100 |
| `display_name` | string | Sí | 1 a 200 |
| `short_name` | string \| null | No | máx. 160 |
| `currency_code` | string | Sí | Código ISO 4217 de la lista admitida (por ejemplo `COP`); se normaliza a mayúsculas |
| `inventory_control_enabled` | boolean | No | `true` |
| `lot_tracking_enabled` | boolean | No | `false`; exige `inventory_control_enabled: true` |
| `expiration_tracking_enabled` | boolean | No | `false`; exige `lot_tracking_enabled: true` |
| `is_purchasable` | boolean | No | `true` |
| `is_sellable` | boolean | No | `true` |

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "display_name": "Acetaminofén 500 mg",
  "short_name": "Acetaminofén",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true
}
```

La respuesta `201` devuelve el producto empresarial con cabecera `Location: /api/v1/company-products/{id}`. **Campo exacto:** `id`, que es el `company_product_id`. Después hay que adoptar al menos una [presentación empresarial](company-product-presentation-id.md), porque las líneas de venta y compra exigen ambas cosas.

**Posibles errores al adoptar:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_products:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION` | La empresa ya adoptó ese producto global (activo o inactivo) | Buscarlo con `?global_product_id=` y `status=ALL` |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe un producto con ese `internal_code` | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | La moneda no está en la lista admitida | Elegir una moneda admitida |
| `422` | `COMMERCIAL_RELATIONSHIP.INVENTORY_FLAGS_INVALID` | Lotes sin control de inventario o vencimiento sin lotes | Corregir las banderas |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_FOUND` | El producto global no existe en Product Catalog | Volver a buscarlo ([global_product_id](global-product-id.md)) |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_INACTIVE` | El producto global está `INACTIVE` | Elegir otro producto |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_ELIGIBLE` | El producto global no está completo | Revisar `completeness` en Product Catalog |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden adoptar productos |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, UUID inválido o campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde; nada se guardó |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=CompanyProduct`.
- Líneas de venta y compra: `lines[].company_product_id` junto con `lines[].company_product_presentation_id`.
- Existencias: filtro `?company_product_id=` en Inventory y ruta de políticas por producto ([Inventario](../principales/inventario.md)).
- Adoptar sus presentaciones: campo `company_product_id` del cuerpo de la [API 11 de Productos y precios](../principales/productos-y-precios.md#11-adoptar-una-presentación-en-la-empresa) y filtro `?company_product_id=` de la [API 12](../principales/productos-y-precios.md#12-consultar-las-presentaciones-de-la-empresa).
- Impuesto de compra: `{company_product_id}` de la ruta de la [API 13](../principales/productos-y-precios.md#13-configurar-el-impuesto-de-compra-del-producto).
- Precios: campo `company_product_id` del cuerpo de la [API 17](../principales/productos-y-precios.md#17-registrar-un-precio-de-venta) y filtro `?company_product_id=` de la [API 18](../principales/productos-y-precios.md#18-consultar-los-precios-vigentes).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El producto no pertenece a la empresa o el usuario no tiene membresía |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` / `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Producto `INACTIVE`, no vendible o no comprable, o la presentación no pertenece a ese producto |
| `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` al confirmar una compra | El producto tiene `purchase_tax_percentage: null` y la línea no trae tasa propia |

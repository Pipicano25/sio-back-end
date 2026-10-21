# Parámetro `price_list_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **lista de precios de la empresa**: agrupa precios de venta por presentación en una moneda (inmutable), con vigencia opcional `[valid_from, valid_to)` y una marca `is_default` única por empresa y moneda. Una empresa puede tener varias listas en la misma moneda |
| Nombre en las rutas y cuerpos | `price_list_id` (Commercial Relationship: ruta `/price-lists/{price_list_id}`, filtro `?price_list_id=`, campo del cuerpo al registrar precios; Sales: campo `lines[].price_list_id`; Product Inventory Query: filtro `?price_list_id=`) |
| Tipo | UUID (texto) |
| Obligatorio | En el flujo operacional de ventas de esta documentación, **sí**: el vendedor elige un precio y el frontend envía su lista en cada línea ([Ventas](../principales/ventas.md)). El contrato de Sales la declara opcional |
| Ejemplo (ficticio) | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` |
| Quién lo genera | Commercial Relationship, al crear la lista (`id` de la respuesta `201`) |
| Alcance | Empresa: solo lo ven los miembros de la empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación, las listas de precios de la empresa ordenadas por código. Por defecto solo `ACTIVE`. Sirve para administrar las listas, para mostrar el nombre de cada lista junto a sus precios y para obtener el `price_list_id`. Ficha técnica: [Commercial Relationship 46](../servicios/commercial-relationship.md#46-get-companiescompany_idprice-lists); guía principal: [Productos y precios, API 15](../principales/productos-y-precios.md#15-consultar-las-listas-de-precios-de-la-empresa).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/price-lists` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100, en código y nombre), `status` (`ACTIVE`, `INACTIVE`, `ALL`; por defecto `ACTIVE`), `currency_code` (exactamente 3 caracteres, por ejemplo `COP`), `is_default` (boolean) |
| Permiso | `perm:commercial-relationship:price_lists:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&currency_code=COP&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[PriceListResponse]`; valores ilustrativos):

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

**Campo exacto:** `items[].id`. Para mostrar las listas usa `name`, `code`, `currency_code` e `is_default`. Una lista está **vigente** cuando su `status` es `ACTIVE`, `valid_from` es `null` o ya llegó, y `valid_to` es `null` o aún no llega; las fechas van en UTC. Cada precio de la [API 18](../principales/productos-y-precios.md#18-consultar-los-precios-vigentes) también trae su `price_list_id`.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:price_lists:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `currency_code` distinto de 3 caracteres, `search` > 100, `status` o booleano inválido, paginación fuera de rango | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden (`dependency` lo indica) | Reintentar más tarde |

## Si la lista no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** Crea una lista `ACTIVE` en una moneda admitida, que queda inmutable. El `code` es único en la empresa sin distinguir mayúsculas. Si `is_default` es `true`, la lista pasa a ser la predeterminada de esa moneda y la anterior pierde la marca. No crea precios. Registra `CREATE_PRICE_LIST` en Audit. Ficha técnica: [Commercial Relationship 47](../servicios/commercial-relationship.md#47-post-companiescompany_idprice-lists); guía principal: [Productos y precios, API 14](../principales/productos-y-precios.md#14-crear-una-lista-de-precios).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/price-lists` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` |
| Permiso | `perm:commercial-relationship:price_lists:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `PriceListCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `code` | string | Sí | 1 a 50 caracteres; único en la empresa |
| `name` | string | Sí | 1 a 120 caracteres |
| `currency_code` | string | Sí | Código ISO 4217 de la lista admitida; inmutable |
| `description` | string \| null | No | Vacía equivale a `null` |
| `valid_from` | date-time con zona \| null | No | `null` es «sin inicio» |
| `valid_to` | date-time con zona \| null | No | Posterior a `valid_from`; `null` es «sin fin» |
| `is_default` | boolean | No | `false` |

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

La respuesta `201` devuelve `PriceListResponse` con cabecera `Location: /api/v1/price-lists/{id}`. **Campo exacto:** `id`, que es el `price_list_id`. El paso a paso completo está en [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:price_lists:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_PRICE_LIST_CODE` | Ya existe una lista con ese código en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.CURRENCY_NOT_SUPPORTED` | Moneda fuera de la lista admitida | Elegir una moneda admitida |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDITY_INVALID` | `valid_to` no es posterior a `valid_from` | Corregir las fechas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear listas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Código o nombre vacíos o largos, fecha sin zona horaria, campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden | Reintentar más tarde |

## Cómo usarlo después

- Registrar un precio de la lista: campo `price_list_id` del cuerpo de la [API 17 de Productos y precios](../principales/productos-y-precios.md#17-registrar-un-precio-de-venta).
- Consultar los precios vigentes de una presentación en todas las listas: cada elemento de la [API 18](../principales/productos-y-precios.md#18-consultar-los-precios-vigentes) trae su `price_list_id`; también sirve como filtro `?price_list_id=`.
- Modificar la lista (nombre, vigencia, predeterminada): `{price_list_id}` de la ruta de la [API 16](../principales/productos-y-precios.md#16-modificar-una-lista-de-precios).
- Crear y consultar sus políticas de ganancia: `{price_list_id}` de la ruta de la [API 21](../principales/productos-y-precios.md#21-crear-una-política-de-ganancia) y de la [API 22](../principales/productos-y-precios.md#22-consultar-las-políticas-de-una-lista) ([policy_id](pricing-policy-id.md)).
- Revisar las actualizaciones automáticas de la lista: filtro `?price_list_id=` de la [API 27](../principales/productos-y-precios.md#27-consultar-las-actualizaciones-automáticas-de-precio).
- Venta: `lines[].price_list_id` al crear la venta o agregar una línea en Sales ([Ventas](../principales/ventas.md)).
- Consulta consolidada: `?price_list_id=` en `product-overviews` de Product Inventory Query ([Inventario](../principales/inventario.md)).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La lista no pertenece a la empresa o el usuario no tiene membresía |
| `422 COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | Se intentó registrar o cambiar precios, o crear políticas, en una lista `INACTIVE` |
| `422 COMMERCIAL_RELATIONSHIP.PRICE_LIST_NOT_FOUND` al registrar un precio | El `price_list_id` del cuerpo no es una lista de la empresa |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` | La lista enviada en una línea no está vigente, es de otra moneda o no tiene precio para la presentación |

# Parámetro `price_list_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **lista de precios de la empresa**: agrupa precios de venta por presentación en una moneda, con vigencia (`valid_from`, `valid_to`) y una marca `is_default` por moneda |
| Nombre en las rutas y cuerpos | `price_list_id` (Commercial Relationship: ruta `/price-lists/{price_list_id}`, filtro `?price_list_id=`, campo del cuerpo al registrar precios y políticas; Sales: campo `lines[].price_list_id`; Product Inventory Query: filtro `?price_list_id=`) |
| Tipo | UUID (texto) |
| Obligatorio | En el flujo operacional de ventas de esta documentación, **sí**: el vendedor elige la lista y el frontend la envía en cada línea ([Ventas](../principales/ventas.md)). El contrato de Sales la declara opcional |
| Ejemplo (ficticio) | `5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b` |
| Quién lo genera | Commercial Relationship, al crear la lista (`id` de la respuesta `201`) |
| Alcance | Empresa |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/price-lists` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥ 1), `page_size` (1–100, por defecto 20), `search` (≤ 100, por código o nombre), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `currency_code` (3 letras, por ejemplo `COP`), `is_default` (boolean) |
| Permiso | `perm:commercial-relationship:price_lists:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists?status=ACTIVE&currency_code=COP' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (`PaginatedResponse[PriceListResponse]`; valores ilustrativos):

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
      "code": "MOSTRADOR",
      "name": "Precio de mostrador",
      "description": "Descripción ilustrativa",
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

**Campo exacto:** `items[].id`. Para mostrar las listas al vendedor usa `name`, `currency_code`, `valid_from`/`valid_to` e `is_default`. Una lista está **vigente** cuando su `status` es `ACTIVE`, `valid_from` ya pasó (o es `null`) y `valid_to` no ha llegado (o es `null`). Las fechas van en UTC.

## Si la lista no existe todavía (operación `WRITE`)

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/price-lists` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists` |
| Permiso | `perm:commercial-relationship:price_lists:create` |
| Clasificación | `WRITE` |

Cuerpo (`PriceListCreate`; rechaza campos adicionales): `code` (único por empresa, `409 DUPLICATE_PRICE_LIST_CODE`), `name`, `currency_code` (inmutable), `description`, `valid_from`, `valid_to` (`valid_to` posterior a `valid_from`), `is_default` (si es `true`, la lista pasa a ser la predeterminada de esa moneda y la anterior deja de serlo).

```json
{
  "code": "MOSTRADOR",
  "name": "Precio de mostrador",
  "currency_code": "COP",
  "description": "Descripción ilustrativa",
  "valid_from": "2026-10-01T00:00:00Z",
  "is_default": true
}
```

La respuesta `201` devuelve `PriceListResponse`; el `price_list_id` es su campo `id`. El paso a paso completo está en [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

## Cómo usarlo después

- Registrar precios de la lista: `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-list-items` → campo `price_list_id` ([operación 53](../servicios/commercial-relationship.md#53-post-companiescompany_idprice-list-items)).
- Consultar los precios vigentes de una presentación en todas las listas: `GET …/companies/{company_id}/price-list-items?company_product_presentation_id=…&status=ACTIVE&applicable_at=<ahora>` ([operación 52](../servicios/commercial-relationship.md#52-get-companiescompany_idprice-list-items)); cada elemento trae su `price_list_id`.
- Crear políticas de ganancia de la lista: `POST …/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` ([pricing_policy_id](pricing-policy-id.md)).
- Venta: `lines[].price_list_id` al crear la venta o agregar una línea en Sales ([Ventas](../principales/ventas.md)).
- Consulta consolidada: `?price_list_id=` en `product-overviews` de Product Inventory Query para ver los precios de esa lista.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La lista no pertenece a la empresa o el usuario no tiene membresía |
| `409 COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | Se intentó registrar precios o políticas en una lista inactiva |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` | La lista enviada en una línea no está vigente, es de otra moneda o no tiene precio para la presentación (`resolution: PRICE_LIST_NOT_APPLICABLE` o `NO_PRICE_IN_LIST`) |

# Parámetro `policy_id` (política de ganancia)

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

> En las rutas el parámetro se llama **`policy_id`**; en las respuestas es el campo `id` de `PricingPolicyResponse`. El archivo se llama `pricing-policy-id` para distinguirlo de las políticas de inventario.

| Propiedad | Valor |
|---|---|
| Qué representa | Una **política de porcentaje de ganancia** de una lista de precios: un recargo (`markup_percentage`) sobre el costo de compra que se aplica automáticamente a las presentaciones asociadas cuando se recibe una compra |
| Nombre en las rutas | `policy_id` (`/pricing-policies/{policy_id}/…`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí para asignar o retirar presentaciones, cambiar el porcentaje o inactivar la política |
| Ejemplo (ficticio) | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` |
| Quién lo genera | Commercial Relationship, al crear la política (`id` de la respuesta `201`) |
| Alcance | Empresa (la de la lista de precios) |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| Parámetros de ruta | `company_id` ([cómo obtenerlo](company-id.md)), `price_list_id` ([cómo obtenerlo](price-list-id.md)) |
| Parámetros de consulta | `status` (`ACTIVE`, `INACTIVE`, `ALL`; por defecto `ACTIVE`), `search` (≤ 100, por nombre), `page`, `page_size` |
| Permiso | `perm:commercial-relationship:pricing_policies:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies?status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PaginatedResponse[PricingPolicyResponse]`; valores ilustrativos):

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

**Campo exacto:** `items[].id`. `markup_percentage` es el porcentaje vigente y `presentation_count` cuántas presentaciones cubre.

Otra forma de llegar a la política desde una presentación: `POST …/companies/{company_id}/pricing-policies/coverage` ([operación 60](../servicios/commercial-relationship.md#60-post-companiescompany_idpricing-policiescoverage)) indica, por presentación y moneda, si está cubierta y en qué listas; después se consulta la política de cada lista con la operación anterior.

## Si la política no existe todavía (operación `WRITE`)

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| Permiso | `perm:commercial-relationship:pricing_policies:create` |
| Clasificación | `WRITE` |

Cuerpo (`PricingPolicyCreate`): `name` (único en la lista, `409 POLICY_NAME_DUPLICATE`), `markup_percentage` (porcentaje de recargo sobre el costo; `0` es válido) y `company_product_presentation_ids` (presentaciones activas y vendibles de la empresa; una presentación solo puede estar en **una** política por lista: `409 PRESENTATION_ALREADY_IN_POLICY`). La lista debe estar `ACTIVE` (`409 PRICE_LIST_INACTIVE`).

```json
{
  "name": "Margen general 30 %",
  "markup_percentage": "30",
  "company_product_presentation_ids": [
    "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83"
  ]
}
```

La respuesta `201` devuelve `PricingPolicyResponse`; el `policy_id` es su campo `id`. El flujo completo está en [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

## Cómo usarlo después

- Asignar presentaciones: `POST …/pricing-policies/{policy_id}/presentations` ([operación 67](../servicios/commercial-relationship.md#67-post-pricing-policiespolicy_idpresentations)).
- Retirar presentaciones: `POST …/pricing-policies/{policy_id}/presentations/remove` (operación 69).
- Cambiar el porcentaje: `POST …/pricing-policies/{policy_id}/percentage` (operación 68). Abre un nuevo término (`GET …/pricing-policies/{policy_id}/terms`); **no recalcula** precios de inmediato: el nuevo porcentaje se aplica en la siguiente recepción de compra.
- Inactivar: `POST …/pricing-policies/{policy_id}/deactivate` (operación 70, definitiva).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La política o la lista no pertenece a la empresa, o el usuario no tiene membresía |
| `409 COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE` | La política ya fue inactivada |
| `422 COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_SELLABLE` | Se intentó asociar una presentación no vendible |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` al confirmar una compra | Alguna presentación de la compra no tiene política en ninguna lista vigente de esa moneda |

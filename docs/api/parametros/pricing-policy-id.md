# Parámetro `policy_id` (política de ganancia)

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

> En las rutas el parámetro se llama **`policy_id`**; en las respuestas es el campo `id` de `PricingPolicyResponse` y en las actualizaciones automáticas, `policy_id`. El archivo se llama `pricing-policy-id` para distinguirlo de las políticas de inventario.

| Propiedad | Valor |
|---|---|
| Qué representa | Una **política de porcentaje de ganancia** de una lista de precios: un recargo (`markup_percentage`, de 0 a 1000 % con hasta 4 decimales) sobre el costo de compra, que Commercial Relationship aplica a sus presentaciones cuando se recibe una compra. En cada instante una presentación pertenece a lo sumo a una política de la misma lista |
| Nombre en las rutas | `policy_id` (`/pricing-policies/{policy_id}/…`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí para asignar o retirar presentaciones, cambiar el porcentaje o inactivar la política |
| Ejemplo (ficticio) | `7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d` |
| Quién lo genera | Commercial Relationship, al crear la política (`id` de la respuesta `201`) |
| Alcance | Empresa (la de la lista de precios); solo la consultan administradores y supervisores |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación, las políticas de ganancia de una lista con su porcentaje vigente y cuántas presentaciones cubren. Por defecto solo `ACTIVE`. Es la fuente de `policy_id` y de la `version` que piden las modificaciones. Ficha técnica: [Commercial Relationship 61](../servicios/commercial-relationship.md#61-get-companiescompany_idprice-listsprice_list_idpricing-policies); guía principal: [Productos y precios, API 22](../principales/productos-y-precios.md#22-consultar-las-políticas-de-una-lista).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| Parámetros de ruta | `company_id` ([cómo obtenerlo](company-id.md)), `price_list_id` ([cómo obtenerlo](price-list-id.md)) |
| Parámetros de consulta | `status` (`ACTIVE`, `INACTIVE`, `ALL`; por defecto `ACTIVE`), `search` (máx. 100, por nombre), `page` (≥1), `page_size` (1–100, por defecto 20) |
| Permiso | `perm:commercial-relationship:pricing_policies:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/price-lists/5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b/pricing-policies?status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[PricingPolicyResponse]`; valores ilustrativos):

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

**Campo exacto:** `items[].id`. `markup_percentage` es el porcentaje vigente con 4 decimales, `presentation_count` cuántas presentaciones cubre y `version` el valor que deben enviar las modificaciones.

Para saber si una presentación tiene política, la [API 26 de Productos y precios](../principales/productos-y-precios.md#26-verificar-la-cobertura-de-políticas) indica por presentación y moneda si está cubierta y en qué listas, sin exponer el porcentaje. Después se consulta la política de cada lista con esta API.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:pricing_policies:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | `price_list_id` no es UUID, `status` fuera de la enumeración, `search` > 100, paginación fuera de rango | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden (`dependency` lo indica) | Reintentar más tarde |

## Si la política no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** Crea una política `ACTIVE` en una lista `ACTIVE` de la empresa, con su porcentaje y, opcionalmente, hasta 100 presentaciones `ACTIVE` y vendibles. Abre el primer término de porcentaje. **No modifica precios**: rige desde la siguiente recepción de compra. Registra `CREATE_PRICING_POLICY` en Audit. Ficha técnica: [Commercial Relationship 62](../servicios/commercial-relationship.md#62-post-companiescompany_idprice-listsprice_list_idpricing-policies); guía principal: [Productos y precios, API 21](../principales/productos-y-precios.md#21-crear-una-política-de-ganancia).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/price-lists/{price_list_id}/pricing-policies` |
| Permiso | `perm:commercial-relationship:pricing_policies:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `PricingPolicyCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `name` | string | Sí | 1 a 120 caracteres; único entre las políticas activas de la lista |
| `markup_percentage` | número o texto decimal | Sí | 0 a 1000, hasta 4 decimales; `0` es válido |
| `company_product_presentation_ids` | UUID[] | No | `[]`; hasta 100 distintas, `ACTIVE`, vendibles y sin otra política en la misma lista |

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

La respuesta `201` devuelve `PricingPolicyResponse` con cabecera `Location: /api/v1/pricing-policies/{id}`. **Campo exacto:** `id`, que es el `policy_id`. El flujo completo está en [Configurar una lista de precios](../ejemplos/configurar-lista-precios.md).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:pricing_policies:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE`, empresa inexistente o lista que no es de la empresa | Volver a cargar las listas |
| `409` | `COMMERCIAL_RELATIONSHIP.POLICY_NAME_DUPLICATE` | Ya existe una política activa con ese nombre en la lista | Pedir otro nombre |
| `409` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY` | Alguna presentación ya pertenece a otra política de la misma lista | Retirarla de la otra política o no incluirla |
| `422` | `COMMERCIAL_RELATIONSHIP.MARKUP_PERCENTAGE_OUT_OF_RANGE` | Porcentaje negativo, mayor que 1000, con más de 4 decimales o no numérico | Corregir el porcentaje |
| `422` | `COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | La lista está `INACTIVE` | Elegir una lista activa |
| `422` | `COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_FOUND` / `PRESENTATION_INACTIVE` / `PRESENTATION_NOT_SELLABLE` | Alguna presentación no es de la empresa, está inactiva o no es vendible | Volver a cargar las presentaciones vendibles |
| `422` | `COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED` | Más de 100 presentaciones distintas | Crear la política y asignar el resto por lotes |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear políticas |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Nombre vacío o > 120, UUID inválido, campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden | Reintentar más tarde |

## Cómo usarlo después

- Asignar presentaciones: `{policy_id}` de la ruta de la [API 23 de Productos y precios](../principales/productos-y-precios.md#23-asignar-presentaciones-a-una-política).
- Retirar presentaciones: `{policy_id}` de la ruta de la [API 24](../principales/productos-y-precios.md#24-retirar-presentaciones-de-una-política).
- Cambiar el porcentaje: `{policy_id}` de la ruta de la [API 25](../principales/productos-y-precios.md#25-cambiar-el-porcentaje-de-una-política). Abre un término nuevo y **no recalcula** precios: el porcentaje nuevo se aplica en la siguiente recepción de compra.
- Ver qué política se aplicó en cada actualización automática: campo `policy_id` de la [API 27](../principales/productos-y-precios.md#27-consultar-las-actualizaciones-automáticas-de-precio).
- Operaciones no principales con el mismo identificador: historial de porcentajes ([Commercial Relationship 65](../servicios/commercial-relationship.md#65-get-pricing-policiespolicy_idterms)), presentaciones vigentes ([Commercial Relationship 66](../servicios/commercial-relationship.md#66-get-pricing-policiespolicy_idpresentations)) e inactivación definitiva ([Commercial Relationship 70](../servicios/commercial-relationship.md#70-post-pricing-policiespolicy_iddeactivate)).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | La política o la lista no pertenece a la empresa, o el usuario no tiene membresía |
| `409 COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE` | La política ya fue inactivada; es un estado final |
| `409 COMMERCIAL_RELATIONSHIP.VERSION_CONFLICT` | La `version` enviada no es la vigente; releer con la [API 22](../principales/productos-y-precios.md#22-consultar-las-políticas-de-una-lista) |
| `422 COMMERCIAL_RELATIONSHIP.PRICE_LIST_INACTIVE` | Se intentó crear la política en una lista `INACTIVE` |
| `422 COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_SELLABLE` | Se intentó asociar una presentación no vendible |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` al confirmar una compra | Alguna presentación de la compra no tiene política en ninguna lista activa y vigente de esa moneda |

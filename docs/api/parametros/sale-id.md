# Parámetro `sale_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Sales](../servicios/sales.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **venta** de la empresa, desde que se crea en borrador (`DRAFT`) hasta que se confirma (`CONFIRMED`) o se cancela (`CANCELLED`). Todas las operaciones sobre líneas, totales, confirmación, cancelación y disponibilidad cuelgan de este identificador |
| Nombre en las rutas y cuerpos | `sale_id` (Sales: `/companies/{company_id}/sales/{sale_id}/…`; Inventory y Audit lo reciben como `origin_id` / `entity_id`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí en todas las operaciones de una venta existente |
| Ejemplo (ficticio) | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` |
| Quién lo genera | Sales, al crear el borrador (`id` de la respuesta `201`) |
| Alcance | Empresa y sucursal: la venta pertenece a la `branch_id` indicada al crearla |

## Cómo obtenerlo

**Al crear la venta:** `POST https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` crea el borrador (`DRAFT`) de una venta en una sucursal, para un cliente y un método de pago, opcionalmente con líneas; la respuesta `201` trae el campo `id`, que es el `sale_id`. Guárdalo junto con `version` para las operaciones siguientes. Qué hace, cuerpo y errores (`403 BRANCH_ACCESS_DENIED`, `409 REFERENCES_NOT_ELIGIBLE`, `422 VALIDATION_ERROR`, entre otros) en [Ventas](../principales/ventas.md) y en la [ficha de Sales, operación 3](../servicios/sales.md#3-post-companiescompany_idsales).

**Para buscar una venta existente:**

**¿Qué hace?** Lista, con paginación, las ventas de la empresa ordenadas de la más reciente a la más antigua, con filtros por estado, sucursal, cliente, rango de fechas y número de documento. Devuelve el encabezado de cada venta (sin líneas). Ficha técnica: [Sales 4](../servicios/sales.md#4-get-companiescompany_idsales).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/sales` |
| URL completa | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page`, `page_size`, `status` (`DRAFT`, `CONFIRMED`, `CANCELLED`), `branch_id`, `company_customer_id`, `operation_date_from`, `operation_date_to` (fecha `YYYY-MM-DD`), `number` (número de documento, por ejemplo `V-000123`) |
| Permiso | `perm:sales:sales:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (`PaginatedResponse[SaleResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
      "customer_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "CASH",
      "payment_method_name_snapshot": "Efectivo",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-19",
      "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
      "number": "V-000123",
      "sequence_value": 123,
      "status": "CONFIRMED",
      "operation_date": "2026-10-19",
      "customer_name_snapshot": "Ana Pérez",
      "customer_identification_snapshot": "CC 1012345678",
      "currency_code": "COP",
      "observations": "Entrega en mostrador",
      "subtotal": "1600.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "1600.00",
      "has_unknown_cost": false,
      "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 1,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "lines": [
        {
          "id": "ce488045-ed3f-4b6c-81d2-68ee8c3fe7a0",
          "sale_id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
          "line_number": 1,
          "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
          "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
          "price_list_requested": false,
          "price_source": "PRICE_LIST_ITEM",
          "product_code_snapshot": "PRD-0001",
          "product_name_snapshot": "Acetaminofén 500 mg",
          "presentation_code_snapshot": "UN",
          "presentation_name_snapshot": "Unidad",
          "base_quantity_factor_snapshot": "1.00000000",
          "unit_code_snapshot": "UN",
          "quantity": "2",
          "base_quantity": "2.0000",
          "unit_price": "800.00",
          "discount_amount": "0",
          "tax_amount": "0",
          "subtotal": "1600.00",
          "total": "1600.00",
          "unit_cost_snapshot": "500.00",
          "cost_total": null,
          "cost_known": true,
          "gross_margin_amount": "600.00",
          "gross_margin_percentage": "37.50",
          "created_at": "2026-10-19T15:04:05Z",
          "updated_at": "2026-10-19T15:04:05Z",
          "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
          "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. `number` es el consecutivo legible (vacío mientras la venta está en `DRAFT`), `version` el valor que debe enviarse en la siguiente operación de escritura y `status` el estado actual.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `SALES.FORBIDDEN` | Falta `perm:sales:sales:read` o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `404` | `SALES.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa o la empresa no existe | Volver a leer el contexto operativo |
| `422` | `SALES.VALIDATION_ERROR` | Paginación fuera de rango, `status` inválido, fecha mal formada o UUID mal formado (`errors[].field` lo indica) | Corregir los parámetros |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles | Reintentar más tarde |

## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=Sale`, para ver el historial de la venta.
- Consultar la venta con líneas y totales: `GET …/companies/{company_id}/sales/{sale_id}` ([operación 5](../servicios/sales.md#5-get-companiescompany_idsalessale_id)).
- Agregar, modificar o eliminar líneas: `POST`/`PUT`/`DELETE …/sales/{sale_id}/details[/{detail_id}]` (operaciones 7, 9 y 10; siempre con `version`).
- Verificar existencias antes de confirmar: `GET …/sales/{sale_id}/availability` (operación 15).
- Confirmar: `POST …/sales/{sale_id}/confirmation` con `{"version": n}` y cabecera `Idempotency-Key` (operación 11). Cancelar: `…/cancellation` (operación 12).
- Rastrear la salida de inventario: `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/kardex?origin_type=SALE&origin_id={sale_id}`.

Los pasos completos están en [Crear una venta](../ejemplos/crear-venta.md) y en [Ventas](../principales/ventas.md).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 SALES.NOT_FOUND` | La venta no pertenece a la empresa o el usuario no tiene membresía |
| `409 SALES.VERSION_CONFLICT` | El `version` enviado no es el actual; vuelve a consultar la venta |
| `409 SALES.INVALID_STATE` | Se intentó modificar o confirmar una venta que ya no está en `DRAFT` |

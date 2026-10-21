# Parámetro `sale_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Sales](../servicios/sales.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **venta** de la empresa, desde que se crea en borrador (`DRAFT`) hasta que se confirma (`CONFIRMED`) o se anula (`CANCELLED`). Todas las operaciones sobre líneas, totales, disponibilidad, confirmación y anulación cuelgan de este identificador |
| Nombre en las rutas y cuerpos | `sale_id` (Sales: `/companies/{company_id}/sales/{sale_id}/…`; Inventory lo recibe como `origin_id` con `origin_type=SALE` y Audit como `entity_id` con `entity_type=Sale`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí en todas las operaciones de una venta existente |
| Ejemplo (ficticio) | `9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a` |
| Quién lo genera | Sales, al crear el borrador (`id` de la respuesta `201`) |
| Alcance | Empresa: se consulta con membresía `ACTIVE`; para escribir se necesita además asignación `ACTIVE` a la sucursal de la venta |

## Cómo obtenerlo

### Al crear la venta (operación `WRITE`)

**¿Qué hace?** Crea la venta en estado `DRAFT` en una sucursal, para un cliente y un método de pago, opcionalmente con sus primeras líneas; Sales resuelve el precio de cada línea y no descuenta existencias hasta confirmar. La respuesta `201` trae la venta completa; su `id` es el `sale_id`. Guía principal: [API 6 de Ventas](../principales/ventas.md#6-crear-la-venta-en-borrador); ficha técnica: [Sales 3](../servicios/sales.md#3-post-companiescompany_idsales).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/sales` |
| URL completa | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | Ninguno |
| Permiso | `perm:sales:sales:create` (+ `perm:sales:sale_details:create` si se envían líneas) |
| Clasificación | `WRITE` (crea un borrador; no toca Inventory) |

```bash
curl -X POST \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
    "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
    "observations": "Venta mostrador",
    "lines": [
      {
        "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
        "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
        "price_list_id": null,
        "quantity": "2"
      }
    ]
  }'
```

Respuesta `201` (`SaleResponse` con `lines`; valores ilustrativos):

```json
{
  "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-10-20",
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-10-20",
  "customer_name_snapshot": "Ana Pérez",
  "customer_identification_snapshot": "CC 1012345678",
  "currency_code": "COP",
  "observations": "Venta mostrador",
  "subtotal": "1600.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "1600.00",
  "inventory_operation_id": null,
  "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "2026-10-20T15:50:00Z",
  "updated_at": "2026-10-20T15:50:00Z",
  "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "lines": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
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
      "quantity": "2.0000",
      "base_quantity": "2.0000",
      "unit_price": "800.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "1600.00",
      "total": "1600.00",
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T15:50:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ]
}
```

**Campo exacto:** `id`. Guárdalo junto con `version` (`1` al crear), que es el valor que se envía en la siguiente escritura.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `SALES.FORBIDDEN` | Falta `perm:sales:sales:create`, o se enviaron líneas sin `perm:sales:sale_details:create`, o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `403` | `SALES.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa están inactivas | Pedir la asignación al administrador de la empresa |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `404` | `SALES.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, empresa inexistente o sucursal de otra empresa | Volver a leer el contexto operativo |
| `409` | `SALES.REFERENCES_NOT_ELIGIBLE` | Cliente, método de pago, producto, presentación o lista de precios existen pero no se pueden usar (`errors[].code` lo indica, p. ej. `CUSTOMER_NOT_ELIGIBLE`, `PRICE_NOT_IN_LIST`) | Mostrar cada `errors[].message` y corregir la referencia |
| `422` | `SALES.VALIDATION_ERROR` | Campo obligatorio ausente, formato inválido, campo desconocido, `unit_price` enviado (`UNIT_PRICE_NOT_ALLOWED`), condición de pago o fecha enviadas, cantidad inválida o referencia inexistente (`errors[]` lo indica) | Corregir el formulario |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Un servicio requerido no responde (`dependency` lo indica) | Reintentar más tarde; no se guardó nada |

### Para buscar una venta existente (operación `READ`)

**¿Qué hace?** Lista, con paginación, las ventas de la empresa ordenadas de la más reciente a la más antigua (`operation_date` y `created_at` descendentes), con filtros por estado, sucursal, cliente, rango de fechas y número de documento exacto. Devuelve el encabezado de cada venta, **sin** líneas. Guía principal: [API 13 de Ventas](../principales/ventas.md#13-listar-y-buscar-las-ventas); ficha técnica: [Sales 4](../servicios/sales.md#4-get-companiescompany_idsales).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/sales` |
| URL completa | `https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `status` (`DRAFT`, `CONFIRMED`, `CANCELLED`), `branch_id` ([cómo obtenerlo](branch-id.md)), `company_customer_id` ([cómo obtenerlo](customer-id.md)), `operation_date_from`, `operation_date_to` (fecha `AAAA-MM-DD`, ambas incluidas), `number` (1–80, número exacto, p. ej. `V-000123`) |
| Permiso | `perm:sales:sales:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-sales-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/sales?status=CONFIRMED&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&operation_date_from=2026-10-01&operation_date_to=2026-10-31' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (`SalePage`; cada elemento es un `SaleResponse` sin `lines`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_customer_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
      "customer_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "CASH",
      "payment_method_name_snapshot": "Efectivo",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-20",
      "sale_sequence_id": "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
      "number": "V-000123",
      "sequence_value": 123,
      "status": "CONFIRMED",
      "operation_date": "2026-10-20",
      "customer_name_snapshot": "Ana Pérez",
      "customer_identification_snapshot": "CC 1012345678",
      "currency_code": "COP",
      "observations": "Venta mostrador",
      "subtotal": "1600.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "1600.00",
      "inventory_operation_id": "3d4e5f6a-7b8c-4d9e-8f0a-1b2c3d4e5f6a",
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 6,
      "created_at": "2026-10-20T15:50:00Z",
      "updated_at": "2026-10-20T16:10:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. `number` es el número legible del documento (`null` mientras la venta está en `DRAFT`), `version` el valor que debe enviarse en la siguiente escritura y `status` el estado actual.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `SALES.FORBIDDEN` | Falta `perm:sales:sales:read` o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `403` | `SALES.OPERATIONAL_ACCESS_DENIED` | Operational Context no permite al usuario consultar su acceso operativo | Pedir `perm:operational-context:application_users:read` |
| `404` | `SALES.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa o la empresa no existe | Volver a leer el contexto operativo |
| `422` | `SALES.VALIDATION_ERROR` | Paginación fuera de rango, `status` inválido, fecha o UUID mal formados, filtro desconocido o `operation_date_to` anterior a `operation_date_from` (`INVALID_DATE_RANGE`) | Corregir los parámetros |
| `503` | `SALES.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles | Reintentar más tarde |

## Cómo usarlo después

- Consultar la venta con líneas y totales: [API 10 de Ventas](../principales/ventas.md#10-consultar-la-venta-con-sus-líneas-y-totales).
- Agregar, modificar o eliminar líneas, siempre con `version`: [API 7](../principales/ventas.md#7-agregar-una-línea-a-la-venta), [API 8](../principales/ventas.md#8-modificar-una-línea-de-la-venta) y [API 9 de Ventas](../principales/ventas.md#9-eliminar-una-línea-de-la-venta).
- Verificar existencias antes de confirmar: [API 11 de Ventas](../principales/ventas.md#11-verificar-la-disponibilidad-antes-de-confirmar).
- Confirmar con `{"version": n}` y el encabezado `Idempotency-Key`: [API 12 de Ventas](../principales/ventas.md#12-confirmar-la-venta). Anular con `version` y `reason`: [API 14 de Ventas](../principales/ventas.md#14-anular-una-venta).
- Historial de la venta: `{entity_id}` de la [API 17 de Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto) con `entity_type=Sale`.
- Movimientos de inventario de la venta: filtro `origin_id` (con `origin_type=SALE`) del kardex de un producto en la sucursal de la venta, `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}?origin_type=SALE&origin_id={sale_id}` (permiso `perm:inventory:movements:read`; ficha [Inventory 10](../servicios/inventory.md#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id); guía principal [Inventario](../principales/inventario.md)).

Los pasos completos están en [Crear una venta](../ejemplos/crear-venta.md) y en [Ventas](../principales/ventas.md).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 SALES.NOT_FOUND` | La venta no pertenece a la empresa de la ruta o el usuario no tiene membresía `ACTIVE` |
| `409 SALES.VERSION_CONFLICT` | La `version` enviada no es la actual; volver a consultar la venta |
| `409 SALES.INVALID_STATUS` | Se intentó editar o confirmar una venta que ya no está en `DRAFT`, o anular una ya `CANCELLED`; el campo `status` del cuerpo trae el estado de la venta |
| `409 SALES.OPERATION_IN_PROGRESS` | La venta tiene una confirmación o anulación en curso (`pending_operation_id`) |
| `403 SALES.BRANCH_ACCESS_DENIED` al escribir | El usuario puede ver la venta pero no tiene asignación `ACTIVE` a su sucursal |

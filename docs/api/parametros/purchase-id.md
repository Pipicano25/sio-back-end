# Parámetro `purchase_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Purchase](../servicios/purchase.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **compra** de la empresa a un proveedor, desde el borrador (`DRAFT`) hasta la confirmación (`CONFIRMED`) y la recepción física (`receipt_status` `PENDING` → `RECEIVED`), o su anulación (`CANCELLED`) |
| Nombre en las rutas y cuerpos | `purchase_id` (Purchase: `/companies/{company_id}/purchases/{purchase_id}/…`; Inventory y Audit lo reciben como `origin_id` / `entity_id`; Commercial Relationship lo muestra en las aplicaciones automáticas de precio) |
| Tipo | UUID (texto) |
| Obligatorio | Sí en todas las operaciones de una compra existente |
| Ejemplo (ficticio) | `4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e` |
| Quién lo genera | Purchase, al crear el borrador (`id` de la respuesta `201`) |
| Alcance | Empresa y sucursal: la compra pertenece a la `branch_id` que recibirá la mercancía; la consultan los miembros de la empresa y la modifican solo los usuarios asignados a esa sucursal |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación, las compras de la empresa ordenadas por fecha de compra descendente (luego por fecha de creación descendente y por `id`), con filtros por estado, sucursal, proveedor, rango de fechas y número exacto. Cada ítem trae la cabecera y los totales, incluido `receipt_status`, pero **no** las líneas (`"lines": null`). Ficha técnica: [Purchase 4](../servicios/purchase.md#4-get-companiescompany_idpurchases); guía principal: [Compras, API 12](../principales/compras.md#12-listar-compras).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/purchases` |
| URL completa | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `status` (`DRAFT`, `CONFIRMED`, `CANCELLED`), `branch_id` (UUID), `company_supplier_id` (UUID), `operation_date_from` y `operation_date_to` (fecha `AAAA-MM-DD`; la final no puede ser anterior a la inicial), `number` (1–80, coincidencia exacta, por ejemplo `C-000045`) |
| Permiso | `perm:purchase:purchases:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-purchase-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/purchases?status=CONFIRMED&company_supplier_id=d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PurchasePage`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "4b5c6d7e-8f9a-4b0c-8d1e-2f3a4b5c6d7e",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
      "supplier_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-10-19",
      "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "payment_method_code_snapshot": "TRANSFER",
      "payment_method_name_snapshot": "Transferencia bancaria",
      "purchase_sequence_id": "4e5f6a7b-8c9d-4e0f-9a1b-2c3d4e5f6a7b",
      "number": "C-000045",
      "sequence_value": 45,
      "status": "CONFIRMED",
      "operation_date": "2026-10-19",
      "promised_delivery_at": null,
      "supplier_document_number": "FV-8891",
      "supplier_name_snapshot": "Distribuidora Farma S.A.S.",
      "supplier_identification_snapshot": "NIT 900123456",
      "currency_code": "COP",
      "observations": null,
      "subtotal": "500000.00",
      "discount_total": "0.00",
      "tax_total": "95000.00",
      "total": "595000.00",
      "inventory_operation_id": null,
      "receipt_status": "PENDING",
      "received_at": null,
      "received_by_user_id": null,
      "created_by_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 5,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:30:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "lines": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Observa también `status`, `receipt_status` (una compra `CONFIRMED` con `receipt_status: PENDING` todavía no ha entrado al inventario), `number` y `version`.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PURCHASE.FORBIDDEN` | Falta `perm:purchase:purchases:read` o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `403` | `PURCHASE.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación del acceso operativo del usuario | Revisar los permisos del usuario |
| `404` | `PURCHASE.NOT_FOUND` | El usuario no tiene membresía `ACTIVE` en la empresa o la empresa no existe | Volver a leer el contexto operativo |
| `422` | `PURCHASE.VALIDATION_ERROR` | Paginación fuera de rango, `status` inválido, fecha o UUID mal formados, rango de fechas invertido (`INVALID_DATE_RANGE`) o parámetro desconocido (`UNKNOWN_FIELD`) | Corregir los parámetros |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Base de datos u Operational Context no disponibles (`dependency` lo indica) | Reintentar más tarde |

## Si la compra no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** Crea una compra en `DRAFT` en una sucursal asignada al usuario, a un proveedor `ACTIVE`, con método de pago y, opcionalmente, hasta 100 líneas. Calcula impuestos, totales, cantidad en unidad base y costo por unidad base; no numera la compra ni mueve inventario. Devuelve `201` con la compra completa; su `id` es el `purchase_id`. Ficha técnica: [Purchase 3](../servicios/purchase.md#3-post-companiescompany_idpurchases); guía principal con todos los campos y ejemplos: [Compras, API 4](../principales/compras.md#4-crear-la-compra-en-borrador).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/purchases` |
| URL completa | `https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases` |
| Permiso | `perm:purchase:purchases:create`; además `perm:purchase:purchase_details:create` si se envían líneas y `perm:purchase:purchase_line_taxes:override` si alguna línea trae `tax_percentage` |
| Clasificación | `WRITE` (crea un borrador editable) |

Cuerpo (modelo `PurchaseCreateIn`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `branch_id` | UUID | Sí | Sucursal `ACTIVE` asignada al usuario ([branch_id](branch-id.md)) |
| `company_supplier_id` | UUID | Sí | Proveedor `ACTIVE` de la empresa con identificación en Party Identity ([company_supplier_id](supplier-id.md)) |
| `operation_date` | date | Sí | No futura en la zona horaria de la sucursal |
| `supplier_payment_condition_id` | UUID \| null | No | Condición del mismo proveedor, activa, vigente, en la moneda de la empresa y de contado |
| `payment_method_id` | UUID | Sí | Método de pago `ACTIVE` ([payment_method_id](payment-method-id.md)) |
| `promised_delivery_at` | date-time con zona \| null | No | — |
| `supplier_document_number` | string \| null | No | 1 a 100 caracteres |
| `observations` | string \| null | No | Hasta 2000 caracteres |
| `lines` | array | No | Hasta 100 líneas; una presentación a lo sumo en una línea; cada línea con `company_product_id`, `company_product_presentation_id`, `supplier_product_id` opcional, `quantity` y `unit_cost` > 0 (hasta 4 decimales), `discount_amount` opcional (hasta 2 decimales) y `tax_percentage` opcional (0 a 100) |

```json
{
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_supplier_id": "d2e3f4a5-b6c7-4d8e-9f0a-1b2c3d4e5f60",
  "operation_date": "2026-10-19",
  "supplier_payment_condition_id": null,
  "payment_method_id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
  "promised_delivery_at": null,
  "supplier_document_number": "FV-8891",
  "observations": null,
  "lines": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "supplier_product_id": null,
      "quantity": "10",
      "unit_cost": "50000",
      "discount_amount": "0"
    }
  ]
}
```

La respuesta `201` devuelve la compra con sus líneas (`status` `DRAFT`, `version` `1`, `number` `null`).

**Campo exacto:** `id`. Guárdalo junto con `version`, que se exige en cada escritura posterior.

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PURCHASE.FORBIDDEN` | Falta alguno de los permisos indicados o el token es de una cuenta de servicio | Mostrar que faltan permisos y el `trace_id` |
| `403` | `PURCHASE.BRANCH_ACCESS_DENIED` | El usuario no tiene asignación `ACTIVE` a la sucursal, o la sucursal o la empresa no están activas | Pedir la asignación al administrador de la empresa |
| `404` | `PURCHASE.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, empresa inexistente o sucursal de otra empresa | Volver a leer el contexto operativo |
| `409` | `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La misma presentación aparece en más de una línea | Agrupar la cantidad en una sola línea |
| `409` | `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Una referencia existe pero no es apta (proveedor no activo, producto no comprable, condición de pago no vigente…); el detalle va en `errors[]` | Mostrar cada error junto a su campo |
| `422` | `PURCHASE.VALIDATION_ERROR` | Campo obligatorio ausente, formato o importe inválido, referencia inexistente, fecha futura o campo desconocido | Corregir el formulario según `errors[]` |
| `503` | `PURCHASE.DEPENDENCY_UNAVAILABLE` | Operational Context, Commercial Relationship, Party Identity, Payment Reference o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde |

## Cómo usarlo después

- [Compras, API 5, 6 y 7](../principales/compras.md#5-agregar-una-línea): agregar, modificar o eliminar líneas del borrador (`…/purchases/{purchase_id}/details[/{detail_id}]`, siempre con `version`).
- [Compras, API 8](../principales/compras.md#8-consultar-la-compra-con-impuestos-y-totales): consultar la compra con sus líneas, impuestos y totales, y obtener la `version` vigente.
- [Compras, API 9](../principales/compras.md#9-confirmar-la-compra): confirmar la compra (asigna el número; no mueve inventario), con `{"version": n}` e `Idempotency-Key`.
- [Compras, API 10](../principales/compras.md#10-registrar-la-recepción-física-completa): registrar la recepción física completa, que ingresa la mercancía al inventario, con `{"version": n, "full_receipt_confirmed": true}` e `Idempotency-Key`.
- [Compras, API 11](../principales/compras.md#11-consultar-el-estado-de-las-operaciones): ver el estado de las operaciones de confirmación, recepción y anulación (`…/purchases/{purchase_id}/operations`).
- [Compras, API 13](../principales/compras.md#13-anular-una-compra): anular la compra con un motivo e `Idempotency-Key`; si estaba recibida, revierte la entrada en Inventory.
- Hitos logísticos de la compra: `GET https://sio-purchase-dev.onrender.com/api/v1/companies/{company_id}/purchases/{purchase_id}/lifecycle-events` (línea de tiempo; ficha [Purchase 17](../servicios/purchase.md#17-get-companiescompany_idpurchasespurchase_idlifecycle-events)).
- Rastrear la entrada de inventario: con el campo `inventory_operation_id` de la compra recibida, `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-operations/{operation_id}` (permiso `perm:inventory:movements:read`; ficha [Inventory 11](../servicios/inventory.md#11-get-companiescompany_idinventory-operationsoperation_id)). En el kardex de cada producto (ficha [Inventory 10](../servicios/inventory.md#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id)) la entrada aparece con `origin_type` `PURCHASE` y este `purchase_id` como `origin_id`.
- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=Purchase`, para ver el historial de la compra.

Los pasos completos están en [Registrar una compra](../ejemplos/registrar-compra.md) y en [Compras](../principales/compras.md).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PURCHASE.NOT_FOUND` | La compra no pertenece a la empresa o el usuario no tiene membresía |
| `403 PURCHASE.BRANCH_ACCESS_DENIED` | El usuario no está asignado a la sucursal de la compra |
| `409 PURCHASE.VERSION_CONFLICT` | El `version` enviado no es el actual |
| `409 PURCHASE.INVALID_STATUS` | La acción no está permitida en el estado actual (por ejemplo, editar líneas de una compra confirmada) |
| `409 PURCHASE.PURCHASE_TAX_NOT_CONFIGURED` | Al confirmar, alguna línea no tiene tasa de impuesto de compra |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` | Al confirmar, alguna presentación no tiene política de ganancia en una lista vigente ([pricing-policy-id](pricing-policy-id.md)) |

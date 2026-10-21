# Parámetro `payment_method_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Payment Reference](../servicios/payment-reference.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **método global de pago** (efectivo, transferencia, tarjeta…) del catálogo compartido de SIO, igual para todas las empresas |
| Nombre en las rutas y cuerpos | `payment_method_id` (campo del cuerpo al crear una venta o una compra; en Payment Reference, ruta `/global-payment-methods/{payment_method_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear una venta y al crear una compra |
| Ejemplo (ficticio) | `b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05` |
| Quién lo genera | Payment Reference, al crear el método (`id`) |
| Alcance | Global: no depende de la empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación, el catálogo global de métodos de pago con su código, nombre, tipo funcional, si exige referencia y estado; admite búsqueda por código o nombre y filtros por estado, tipo y `requires_reference`. Es la fuente del selector de método de pago en ventas y compras. Guía principal: [API 5 de Ventas](../principales/ventas.md#5-consultar-los-métodos-de-pago); ficha técnica: [Payment Reference 9](../servicios/payment-reference.md#9-get-global-payment-methods).

| | |
|---|---|
| Método y ruta | `GET /global-payment-methods` (**sin** prefijo `/api/v1`) |
| URL completa | `https://sio-payment-reference-dev.onrender.com/global-payment-methods` |
| Parámetros de ruta | Ninguno |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (código o nombre), `status` (`ACTIVE`, `INACTIVE`; sin filtro devuelve ambos), `method_type` (`CASH`, `BANK`, `CARD`, `WALLET`, `CHECK`, `OTHER`), `requires_reference` (`true` o `false`) |
| Permiso | `perm:payment-reference:global_payment_methods:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (`PaginatedResponse[GlobalPaymentMethodResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05",
      "code": "CASH",
      "name": "Efectivo",
      "method_type": "CASH",
      "requires_reference": false,
      "status": "ACTIVE",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T12:00:00Z",
      "updated_at": "2026-01-15T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. `code` y `name` son los textos del selector; Sales y Purchase los copian a `payment_method_code_snapshot` y `payment_method_name_snapshot`. `requires_reference: true` indica que el método normalmente exige un número de referencia externo; en las ventas del MVP Sales no pide ni guarda esa referencia.

**Posibles errores de esta API** (Payment Reference responde con el formato básico `{"detail": …}`, sin `code`):

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | sin `code` (`{"detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta."}`) | Falta `perm:payment-reference:global_payment_methods:read` | Mostrar que faltan permisos |
| `422` | sin `code` (`{"detail": [...]}` de FastAPI) | `status` o `method_type` fuera de la enumeración, `requires_reference` no booleano o paginación fuera de rango | Corregir los parámetros |
| `503` | sin `code` (`{"detail": "Payment Reference no puede atender la solicitud porque su base de datos no está disponible. Intente de nuevo en unos momentos."}`) | La base de datos de Payment Reference no está disponible | Reintentar más tarde |

## Cómo usarlo después

- Crear la venta: campo `payment_method_id` del cuerpo de la [API 6 de Ventas](../principales/ventas.md#6-crear-la-venta-en-borrador); debe estar `ACTIVE`.
- Crear la compra: campo `payment_method_id` del cuerpo al crear la compra en [Compras](../principales/compras.md).
- La respuesta de la venta o de la compra guarda `payment_method_code_snapshot` y `payment_method_name_snapshot` tal como estaban al crearla.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `409 SALES.REFERENCES_NOT_ELIGIBLE` con `errors[].code` `PAYMENT_METHOD_INACTIVE` | El método está `INACTIVE` |
| `422 SALES.VALIDATION_ERROR` con `errors[].code` `PAYMENT_METHOD_NOT_FOUND` o `PAYMENT_METHOD_REQUIRED` | El UUID no existe en el catálogo o no se envió |
| `404` `{"detail": "..."}` en `/global-payment-methods/{payment_method_id}` | El UUID no existe (Payment Reference usa el formato básico de error) |

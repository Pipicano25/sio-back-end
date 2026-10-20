# Parámetro `payment_method_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Payment Reference](../servicios/payment-reference.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **método global de pago** (efectivo, transferencia, tarjeta…) del catálogo compartido de SIO |
| Nombre en las rutas y cuerpos | `payment_method_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear una venta y al crear una compra |
| Ejemplo (ficticio) | `b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d05` |
| Quién lo genera | Payment Reference, al crear el método (`id`) |
| Alcance | Global |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /global-payment-methods` (**sin** prefijo `/api/v1`) |
| URL completa | `https://sio-payment-reference-dev.onrender.com/global-payment-methods` |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (código o nombre), `status` (`ACTIVE`, `INACTIVE`), `method_type` (`CASH`, `BANK`, `CARD`, `WALLET`, `CHECK`, `OTHER`), `requires_reference` (boolean) |
| Permiso | `perm:payment-reference:global_payment_methods:read` (cubierto por `perm:payment-reference:all:read`, que tienen compras y ventas) |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-payment-reference-dev.onrender.com/global-payment-methods?status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[GlobalPaymentMethodResponse]`; valores ilustrativos):

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
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. `requires_reference: true` indica que el pago necesita una referencia externa (por ejemplo número de transferencia); cómo se captura en la venta se detalla en la ficha de Sales.

## Cómo usarlo después

- `POST /companies/{company_id}/sales` → `payment_method_id`.
- `POST /companies/{company_id}/purchases` → `payment_method_id`.
- La respuesta de la venta o compra guarda `payment_method_code_snapshot` y `payment_method_name_snapshot` tal como estaban al crearla.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `409 …REFERENCES_NOT_ELIGIBLE` | El método está `INACTIVE` |
| `404` `{"detail": "..."}` en `/global-payment-methods/{payment_method_id}` | El UUID no existe (Payment Reference usa el formato básico de error) |

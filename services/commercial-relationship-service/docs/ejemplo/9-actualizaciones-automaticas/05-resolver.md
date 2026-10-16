# Paso 05 de 05 — Resolver la actualización fallida

Ejercicio 9 — Actualizaciones automáticas de precio · [← Paso anterior](04-consultar-actualizaciones.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Cerrarla con un motivo, sin cambiar precios.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<FALLIDA>`, `<LISTA>` — pasos [01](01-consultar-datos.md), [02](02-preparar-la-politica.md), [04](04-consultar-actualizaciones.md)

---

## 1. Resolver la actualización fallida

```http
POST /api/v1/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>/resolution
```

```json
{
  "version": 2,
  "reason": "Se revisó la compra: el costo de la segunda recepción no debe cambiar el precio (ficticio)."
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:automatic_price_applications:resolve`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:automatic_price_applications:resolve`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `automatic_price_applications` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Solo desde `PENDING` o `FAILED`, con un motivo de 10 a 500 caracteres y la `version` vigente. Queda `RESOLVED` (final) y se audita como `RESOLVE_AUTOMATIC_PRICE`.
- No crea ni cierra precios: rige el de la recepción 1.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "sequence": 2,
  "status": "RESOLVED",
  "markup_percentage": "30.0000",
  "current_unit_cost": null,
  "previous_unit_cost": null,
  "reference_cost": null,
  "previous_price": null,
  "new_price": null,
  "attempts": 1,
  "last_error_code": "RuntimeError",
  "resolved_by": "admin.test",
  "resolution_reason": "Se revisó la compra: el costo de la segunda recepción no debe cambiar el precio (ficticio).",
  "version": 3
}
```

## 2. Resolverla otra vez (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>/resolution
```

```json
{
  "version": 3,
  "reason": "Se revisó la compra: el costo de la segunda recepción no debe cambiar el precio (ficticio)."
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:automatic_price_applications:resolve`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:automatic_price_applications:resolve`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `automatic_price_applications` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una actualización terminada no cambia: `409 APPLICATION_ALREADY_FINAL`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.APPLICATION_ALREADY_FINAL",
  "detail": "La actualización automática ya terminó y no admite resolución."
}
```

## 3. Consultar el precio de la caja en la lista

```http
GET /api/v1/companies/<EMPRESA>/price-list-items?price_list_id=<LISTA>
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:price_list_items:read`), `ventas.test` (por `perm:commercial-relationship:price_list_items:read`), `reportes.test` (por `perm:commercial-relationship:price_list_items:read`), `consulta.test` (por `perm:commercial-relationship:price_list_items:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Los precios muestran `origin` y `closure_reason`, nunca costos ni porcentajes (los ve cualquier usuario con lectura de precios).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "unit_price": "3094.00",
      "origin": "AUTOMATIC",
      "closure_reason": null,
      "valid_to": null
    }
  ]
}
```

---

[← Paso anterior](04-consultar-actualizaciones.md) · [Orden del ejercicio](ORDEN.md)

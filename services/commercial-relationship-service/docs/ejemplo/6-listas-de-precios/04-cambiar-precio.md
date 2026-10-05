# Paso 04 de 05 — Cambiar el precio

Ejercicio 6 — Listas de precios y precio aplicable · [← Paso anterior](03-lista-y-precio.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-precio-aplicable.md)

**Objetivo:** Un precio en vigencia no se reescribe; se usa change-price.

**Necesita (de pasos anteriores):** `<PRECIO>` — pasos [03](03-lista-y-precio.md)

**Deja guardado para los siguientes pasos:** `<PRECIO_NUEVO>`

---

## 1. Modificar el valor del precio en vigencia (rechazado)

```http
PUT /api/v1/price-list-items/<PRECIO>
```

```json
{
  "unit_price": "31500",
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_to": null,
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_list_items` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `422 PRICE_IN_EFFECT_NOT_MODIFIABLE`: el precio ya entró en vigencia (DS-08).

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_IN_EFFECT_NOT_MODIFIABLE",
  "detail": "El precio ya está en vigencia: solo puede cerrarse o cambiarse con la acción change-price.",
  "errors": [
    {
      "field": "unit_price",
      "message": "El precio ya está en vigencia: solo puede cerrarse o cambiarse con la acción change-price.",
      "code": "PRICE_IN_EFFECT_NOT_MODIFIABLE"
    }
  ]
}
```

## 2. Cambiar el precio desde 2099 (ficticio)

```http
POST /api/v1/price-list-items/<PRECIO>/change-price
```

```json
{
  "unit_price": "31500",
  "effective_from": "2099-01-01T00:00:00Z",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_list_items` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- En una sola operación cierra el precio vigente en el instante de efecto y crea el nuevo desde ese instante (FR-054a). Exige `update`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "item": {
    "unit_price": "31500.00",
    "status": "ACTIVE",
    "version": 1
  },
  "previous": {
    "unit_price": "30420.00",
    "version": 2
  }
}
```

**Guardar:** `item.id` → `<PRECIO_NUEVO>`

---

[← Paso anterior](03-lista-y-precio.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-precio-aplicable.md)

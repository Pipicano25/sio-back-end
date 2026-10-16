# Paso 04 de 05 — Consultar las actualizaciones

Ejercicio 9 — Actualizaciones automáticas de precio · [← Paso anterior](03-recepciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-resolver.md)

**Objetivo:** Ver el cálculo de cada actualización y encontrar la que falló.

**Necesita (de pasos anteriores):** `<EMPRESA>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<FALLIDA>`

---

## 1. Listar las actualizaciones de la empresa

```http
GET /api/v1/companies/<EMPRESA>/automatic-price-applications
```

**Permiso que exige la URL:** `perm:commercial-relationship:automatic_price_applications:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `automatic_price_applications` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Paginado. Filtros: `status`, `price_list_id`, `company_product_presentation_id` y `purchase_id`.
- Solo administradores y supervisores: la respuesta incluye costos y porcentajes.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "sequence": 1,
      "status": "APPLIED",
      "new_price": "3094.00",
      "last_error_code": null
    },
    {
      "sequence": 2,
      "status": "FAILED",
      "new_price": null,
      "last_error_code": "RuntimeError"
    }
  ],
  "total_records": 2
}
```

## 2. Listar solo las fallidas

```http
GET /api/v1/companies/<EMPRESA>/automatic-price-applications?status=FAILED
```

**Permiso que exige la URL:** `perm:commercial-relationship:automatic_price_applications:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `automatic_price_applications` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "sequence": 2,
      "status": "FAILED",
      "new_price": null,
      "last_error_code": "RuntimeError"
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<FALLIDA>`

## 3. Ver el detalle de la fallida

```http
GET /api/v1/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>
```

**Permiso que exige la URL:** `perm:commercial-relationship:automatic_price_applications:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `automatic_price_applications` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una actualización fallida todavía no tiene cálculo: los costos y el precio se calculan cuando se procesa. Al reintentarla, el costo actual (2.000) sería menor que el anterior (2.380), así que el costo de referencia sería el promedio simple (2.190) y el precio 2.847.
- `attempts` y `last_error_code` muestran el intento fallido; el detalle técnico del error solo queda en el log y en la auditoría.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "sequence": 2,
  "status": "FAILED",
  "markup_percentage": "30.0000",
  "current_unit_cost": null,
  "previous_unit_cost": null,
  "reference_cost": null,
  "previous_price": null,
  "new_price": null,
  "attempts": 1,
  "last_error_code": "RuntimeError",
  "resolved_by": null,
  "resolution_reason": null,
  "version": 2
}
```

---

[← Paso anterior](03-recepciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-resolver.md)

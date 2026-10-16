# Paso 04 de 04 — Cambiar el porcentaje, retirar e inactivar

Ejercicio 7 — Políticas de ganancia de una lista de precios · [← Paso anterior](03-crear-politicas.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Historial de porcentajes y presentaciones; inactivación final.

**Necesita (de pasos anteriores):** `<ALIMENTOS>`, `<SOBRE>`, `<ESPECIALES>` — pasos [02](02-preparar-la-lista.md), [03](03-crear-politicas.md)

---

## 1. Cambiar Alimentos a 20 %

```http
POST /api/v1/pricing-policies/<ALIMENTOS>/percentage
```

```json
{
  "version": 1,
  "markup_percentage": "20"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Cierra el término del 15 % y abre el del 20 %. Una recepción anterior que aún esté pendiente usará el 15 % con el que se recibió (RC-021-5).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ALIMENTOS>",
  "price_list_id": "<LISTA>",
  "name": "Alimentos",
  "markup_percentage": "20.0000",
  "presentation_count": 2,
  "status": "ACTIVE",
  "version": 2
}
```

## 2. Consultar el historial de porcentajes

```http
GET /api/v1/pricing-policies/<ALIMENTOS>/terms
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El historial no se borra ni se reescribe.

**Respuesta esperada — `200 OK`** (abreviada)

```json
[
  {
    "markup_percentage": "15.0000",
    "valid_to": "<fecha y hora del cambio>"
  },
  {
    "markup_percentage": "20.0000",
    "valid_to": null
  }
]
```

## 3. Retirar el sobre de Alimentos

```http
POST /api/v1/pricing-policies/<ALIMENTOS>/presentations/remove
```

```json
{
  "version": 2,
  "company_product_presentation_ids": [
    "<SOBRE>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- En esta lista con políticas, la siguiente recepción del sobre **finalizará su precio** en `PUBLICO` hasta que alguien registre uno manual o lo asigne a otra política.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ALIMENTOS>",
  "price_list_id": "<LISTA>",
  "name": "Alimentos",
  "markup_percentage": "20.0000",
  "presentation_count": 1,
  "status": "ACTIVE",
  "version": 3
}
```

## 4. Inactivar Especiales

```http
POST /api/v1/pricing-policies/<ESPECIALES>/deactivate
```

```json
{
  "version": 1,
  "reason": "Fin de la temporada de ofertas"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:pricing_policies:delete`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Estado final: cierra su porcentaje y sus presentaciones. No hay reactivación: se crea otra.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ESPECIALES>",
  "price_list_id": "<LISTA>",
  "name": "Especiales",
  "markup_percentage": "50.0000",
  "presentation_count": 0,
  "status": "INACTIVE",
  "version": 2
}
```

## 5. Cambiar el porcentaje de la política inactiva (rechazado)

```http
POST /api/v1/pricing-policies/<ESPECIALES>/percentage
```

```json
{
  "version": 2,
  "markup_percentage": "40"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `409 POLICY_INACTIVE`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.POLICY_INACTIVE",
  "detail": "La política está inactiva y no admite cambios."
}
```

---

[← Paso anterior](03-crear-politicas.md) · [Orden del ejercicio](ORDEN.md)

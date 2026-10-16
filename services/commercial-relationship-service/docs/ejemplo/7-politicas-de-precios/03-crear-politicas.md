# Paso 03 de 04 — Crear las políticas

Ejercicio 7 — Políticas de ganancia de una lista de precios · [← Paso anterior](02-preparar-la-lista.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-modificar-politicas.md)

**Objetivo:** Dos políticas con porcentajes distintos y el rechazo de una presentación repetida.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<LISTA>`, `<CAJA>`, `<SOBRE>`, `<IRBE>` — pasos [01](01-consultar-datos.md), [02](02-preparar-la-lista.md)

**Deja guardado para los siguientes pasos:** `<ALIMENTOS>`, `<ESPECIALES>`

---

## 1. Crear la política Alimentos (15 %) con la caja y el sobre

```http
POST /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

```json
{
  "name": "Alimentos",
  "markup_percentage": "15",
  "company_product_presentation_ids": [
    "<CAJA>",
    "<SOBRE>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El porcentaje va de 0 a 1000 con hasta 4 decimales. **No cambia ningún precio**: se usará en la siguiente recepción de estas presentaciones.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ALIMENTOS>",
  "price_list_id": "<LISTA>",
  "name": "Alimentos",
  "markup_percentage": "15.0000",
  "presentation_count": 2,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<ALIMENTOS>`

## 2. Crear la política Especiales (50 %) con la caja (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

```json
{
  "name": "Especiales",
  "markup_percentage": "50",
  "company_product_presentation_ids": [
    "<CAJA>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- La caja ya está en Alimentos de esta lista: `409 PRESENTATION_ALREADY_IN_POLICY`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY",
  "detail": "La presentación ya pertenece a otra política de la misma lista de precios.",
  "errors": [
    {
      "field": "company_product_presentation_ids",
      "message": "La presentación ya pertenece a otra política de la misma lista de precios.",
      "code": "PRESENTATION_ALREADY_IN_POLICY"
    }
  ]
}
```

## 3. Crear la política Especiales (50 %) con el irbesartán

```http
POST /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

```json
{
  "name": "Especiales",
  "markup_percentage": "50",
  "company_product_presentation_ids": [
    "<IRBE>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Cada presentación usa el porcentaje de su propia política.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ESPECIALES>",
  "price_list_id": "<LISTA>",
  "name": "Especiales",
  "markup_percentage": "50.0000",
  "presentation_count": 1,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<ESPECIALES>`

## 4. Crear una política con 1000,0001 % (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

```json
{
  "name": "Excesiva",
  "markup_percentage": "1000.0001",
  "company_product_presentation_ids": []
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Fuera de 0 a 1000: `422 MARKUP_PERCENTAGE_OUT_OF_RANGE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.MARKUP_PERCENTAGE_OUT_OF_RANGE",
  "detail": "El porcentaje de ganancia debe estar entre 0 y 1000, con hasta 4 decimales.",
  "errors": [
    {
      "field": "markup_percentage",
      "message": "El porcentaje de ganancia debe estar entre 0 y 1000, con hasta 4 decimales.",
      "code": "MARKUP_PERCENTAGE_OUT_OF_RANGE"
    }
  ]
}
```

## 5. Listar las políticas de la lista

```http
GET /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Solo administradores y supervisores: las políticas exponen porcentajes internos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "name": "Alimentos",
      "markup_percentage": "15.0000",
      "presentation_count": 2
    },
    {
      "name": "Especiales",
      "markup_percentage": "50.0000",
      "presentation_count": 1
    }
  ],
  "total_records": 2
}
```

---

[← Paso anterior](02-preparar-la-lista.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-modificar-politicas.md)

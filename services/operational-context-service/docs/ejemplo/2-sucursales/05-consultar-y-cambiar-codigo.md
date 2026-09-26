# Paso 05 de 05 — Consultar las sucursales y cambiar un código

Ejercicio 2 — Sucursales de una empresa · [← Paso anterior](04-registrar-sucursales.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Listar las sucursales de la empresa y cambiar el código de la bodega.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<SUC_BOG>`, `<PAIS_CO>`, `<DIV_CUN>`, `<CIU_BOG>` — pasos [02](02-consultar-ubicacion.md), [03](03-registrar-empresa.md), [04](04-registrar-sucursales.md)

---

## 1. Listar las sucursales activas de la empresa

```http
GET /api/v1/companies/<EMPRESA>/branches
```

**Permiso que exige la URL:** `perm:operational-context:branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ℹ️ Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Por defecto solo aparecen las sucursales `ACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "code": "MED-01",
      "effective_timezone": "America/Bogota"
    },
    {
      "code": "BOG-01",
      "effective_timezone": "America/Bogota"
    }
  ],
  "total_records": 2
}
```

## 2. Cambiar el código de la bodega

```http
PUT /api/v1/branches/<SUC_BOG>
```

```json
{
  "code": "BOD-NORTE",
  "name": "Bodega Norte (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_CUN>",
  "city_id": "<CIU_BOG>",
  "timezone": "America/Bogota",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- El código puede cambiar respetando la unicidad; el `id` no cambia (DS-10).
- No cambia la ubicación: no se consulta Geography.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<SUC_BOG>",
  "code": "BOD-NORTE",
  "version": 2
}
```

## 3. Consultar la bodega por su `id`

```http
GET /api/v1/branches/<SUC_BOG>
```

**Permiso que exige la URL:** `perm:operational-context:branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ℹ️ Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Es la consulta que usan Inventory, Purchase y Sales (contrato Provider).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<SUC_BOG>",
  "company_id": "<EMPRESA>",
  "company_status": "ACTIVE",
  "code": "BOD-NORTE",
  "name": "Bodega Norte (ficticia)",
  "city_id": "<CIU_BOG>",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 2
}
```

---

[← Paso anterior](04-registrar-sucursales.md) · [Orden del ejercicio](ORDEN.md)

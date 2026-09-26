# Paso 04 de 04 — Reactivar la empresa

Ejercicio 3 — Inactivar y reactivar una empresa · [← Paso anterior](03-inactivar-empresa.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Reactivar la empresa y comprobar la transición repetida.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<SUCURSAL>` — pasos [02](02-registrar-empresa-y-sucursal.md)

---

## 1. Reactivar la empresa

```http
POST /api/v1/companies/<EMPRESA>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:operational-context:companies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`

**Por qué se hace así**

- Exige el permiso `update`; por eso `supervisor.test` puede reactivar.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "ACTIVE",
  "version": 3
}
```

## 2. Intentar reactivarla otra vez (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/reactivate
```

```json
{
  "version": 3
}
```

**Permiso que exige la URL:** `perm:operational-context:companies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`

**Por qué se hace así**

- Ya está `ACTIVE`: `409 INVALID_STATUS_TRANSITION`, sin cambiar la versión.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION",
  "detail": "La empresa ya se encuentra en estado ACTIVE."
}
```

## 3. Consultar la sucursal otra vez

```http
GET /api/v1/branches/<SUCURSAL>
```

**Permiso que exige la URL:** `perm:operational-context:branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ℹ️ Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.

**Por qué se hace así**

- Con la empresa activa, la sucursal vuelve a estar disponible sin haberla modificado.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "ACTIVE",
  "company_status": "ACTIVE",
  "version": 1
}
```

---

[← Paso anterior](03-inactivar-empresa.md) · [Orden del ejercicio](ORDEN.md)

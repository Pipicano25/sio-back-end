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

**Permisos que exige la URL (todos):** `perm:operational-context:companies:update` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Exige el permiso `update` y, desde la Fase B, `platform:administer`: solo `admin.test` puede reactivar empresas.

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

**Permisos que exige la URL (todos):** `perm:operational-context:companies:update` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:branches:read`), `consulta.test` (por `perm:operational-context:branches:read`)
- ℹ️ Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

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

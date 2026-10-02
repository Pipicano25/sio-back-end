# Paso 03 de 04 — Inactivar la empresa

Ejercicio 3 — Inactivar y reactivar una empresa · [← Paso anterior](02-registrar-empresa-y-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-reactivar-empresa.md)

**Objetivo:** Inactivar la empresa y ver el efecto en su sucursal.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<SUCURSAL>` — pasos [02](02-registrar-empresa-y-sucursal.md)

---

## 1. Inactivar la empresa con la versión vigente

```http
POST /api/v1/companies/<EMPRESA>/deactivate
```

```json
{
  "version": 1
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:delete` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `delete`
- ℹ️ Inactivar una empresa (`POST .../deactivate`) exige `delete`, aunque no la elimina; reactivar (`POST .../reactivate`) exige `update`. Desde la Fase B ambas exigen además `perm:operational-context:platform:administer`: `supervisor.test` no puede ninguna de las dos.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Exige el permiso `delete` aunque no elimina: cambia `status` a `INACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "INACTIVE",
  "version": 2
}
```

## 2. Consultar la sucursal

```http
GET /api/v1/branches/<SUCURSAL>
```

**Permiso que exige la URL:** `perm:operational-context:branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:branches:read`), `consulta.test` (por `perm:operational-context:branches:read`)
- ℹ️ Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- La sucursal sigue `ACTIVE`, pero informa `company_status: INACTIVE`: los consumidores no deben usarla para nuevas operaciones.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "ACTIVE",
  "company_status": "INACTIVE",
  "version": 1
}
```

## 3. Intentar crear otra sucursal (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "CEN-02",
  "name": "Oficina Norte (ficticia)"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- No se crean sucursales bajo una empresa inactiva: `422 COMPANY_INACTIVE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "OPERATIONAL_CONTEXT.COMPANY_INACTIVE",
  "detail": "La empresa está inactiva: no se pueden crear ni reactivar sus sucursales."
}
```

---

[← Paso anterior](02-registrar-empresa-y-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-reactivar-empresa.md)

# Paso 05 de 05 — Efecto de inactivar la asignación y la sucursal

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](04-comprobar-acceso.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Retirar la asignación, inactivar la sucursal y volver a comprobar.

**Necesita (de pasos anteriores):** `<ASIGNACION>`, `<SUC_PRINCIPAL>` — pasos [02](02-empresa-y-sucursales.md), [03](03-asignar-sucursal.md)

---

## 1. Retirar la asignación

```http
POST /api/v1/user-branches/<ASIGNACION>/deactivate
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:delete`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `delete`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- No se elimina: queda `INACTIVE` con su fecha de retiro.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "INACTIVE",
  "version": 2,
  "operational_access": {
    "allowed": false,
    "reason": "USER_BRANCH_INACTIVE"
  }
}
```

## 2. Acceso tras retirar la asignación (denegado)

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=operario.dao
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `lookup`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `lookup`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `superadmin` (por `perm:all:all:all`).

**Por qué se hace así**

- La asignación existe pero está inactiva: `USER_BRANCH_INACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": false,
  "reason": "USER_BRANCH_INACTIVE",
  "keycloak_user_id": "operario.dao",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": null
}
```

## 3. Inactivar la sucursal principal

```http
POST /api/v1/branches/<SUC_PRINCIPAL>/deactivate
```

**Permiso que exige la URL:** `perm:operational-context:branches:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:delete`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `delete`
- ℹ️ Inactivar una sucursal exige `delete`; reactivarla exige `update`.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Inactivar la sucursal no modifica las asignaciones (DS-11).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "INACTIVE",
  "version": 2
}
```

## 4. Acceso a la sucursal inactiva (denegado)

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=operario.dao
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `lookup`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `lookup`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `superadmin` (por `perm:all:all:all`).

**Por qué se hace así**

- En la vía técnica se evalúa primero la empresa y luego la sucursal: `BRANCH_INACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": false,
  "reason": "BRANCH_INACTIVE",
  "keycloak_user_id": "operario.dao",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": null
}
```

---

[← Paso anterior](04-comprobar-acceso.md) · [Orden del ejercicio](ORDEN.md)

# Paso 03 de 05 — Asignar la sucursal principal

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](02-empresa-y-sucursales.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-comprobar-acceso.md)

**Objetivo:** Asignar `PRI-01` al usuario y ver su acceso calculado.

**Necesita (de pasos anteriores):** `<USR_COMPRADOR>`, `<SUC_PRINCIPAL>` — pasos [02](02-empresa-y-sucursales.md)

**Deja guardado para los siguientes pasos:** `<ASIGNACION>`

---

## 1. Asignar la sucursal principal

```http
POST /api/v1/application-users/<USR_COMPRADOR>/user-branches
```

```json
{
  "branch_id": "<SUC_PRINCIPAL>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- El cuerpo solo lleva la sucursal; el usuario viene de la ruta y el autor del token.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIGNACION>",
  "branch_id": "<SUC_PRINCIPAL>",
  "status": "ACTIVE",
  "assigned_by": "user-admin",
  "operational_access": {
    "allowed": true,
    "reason": null
  }
}
```

**Guardar:** `id` → `<ASIGNACION>`

## 2. Intentar asignarla otra vez (rechazado)

```http
POST /api/v1/application-users/<USR_COMPRADOR>/user-branches
```

```json
{
  "branch_id": "<SUC_PRINCIPAL>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- La pareja usuario + sucursal es única: `409 DUPLICATE_USER_BRANCH` (se reactiva, no se duplica).

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.DUPLICATE_USER_BRANCH",
  "detail": "El usuario ya tiene una asignación a esa sucursal; si está inactiva, reactívela."
}
```

## 3. Listar las sucursales asignadas al usuario

```http
GET /api/v1/application-users/<USR_COMPRADOR>/user-branches
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:user_branches:read`), `consulta.test` (por `perm:operational-context:user_branches:read`)
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Cada asignación informa su acceso operativo calculado (sin permiso concreto).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "branch_id": "<SUC_PRINCIPAL>",
      "status": "ACTIVE",
      "operational_access": {
        "allowed": true,
        "reason": null
      }
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](02-empresa-y-sucursales.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-comprobar-acceso.md)

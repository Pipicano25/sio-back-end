# Paso 04 de 05 — Comprobar el acceso operativo (vía técnica)

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](03-asignar-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-efecto-de-inactivar.md)

**Objetivo:** Consultar el acceso de `compras.test` como lo haría Purchase con su identidad técnica.

**Necesita (de pasos anteriores):** `<SUC_PRINCIPAL>`, `<SUC_SECUNDARIA>` — pasos [02](02-empresa-y-sucursales.md)

---

## 1. Acceso a la sucursal principal para crear compras

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test&permission=perm:purchase:purchases:create
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `lookup`; `compras.test`, `ventas.test`, `inventario.test` — sobre `operational-context` solo tienen `read`; les falta `lookup`; `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `operational-context`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `administradores` (por `perm:all:all:all`).

**Por qué se hace así**

- `compras.test` es miembro, tiene la sucursal asignada y su grupo tiene `perm:purchase:all:all`: `allowed: true`.
- El permiso se evalúa con los roles de `compras.test` leídos de Keycloak, no con los del token que consulta.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": true,
  "reason": null,
  "keycloak_user_id": "compras.test",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": "perm:purchase:purchases:create"
}
```

## 2. Acceso para crear ventas (denegado)

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=compras.test&permission=perm:sales:sales:create
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `lookup`; `compras.test`, `ventas.test`, `inventario.test` — sobre `operational-context` solo tienen `read`; les falta `lookup`; `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `operational-context`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `administradores` (por `perm:all:all:all`).

**Por qué se hace así**

- El grupo `compras` no tiene permisos de ventas: `allowed: false`, `PERMISSION_DENIED`, con `200` (no es un error del contrato).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": false,
  "reason": "PERMISSION_DENIED",
  "keycloak_user_id": "compras.test",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": "perm:sales:sales:create"
}
```

## 3. Acceso a la sucursal secundaria (denegado)

```http
GET /api/v1/operational-access?branch_id=<SUC_SECUNDARIA>&keycloak_user_id=compras.test
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `lookup`; `compras.test`, `ventas.test`, `inventario.test` — sobre `operational-context` solo tienen `read`; les falta `lookup`; `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `operational-context`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `administradores` (por `perm:all:all:all`).

**Por qué se hace así**

- Sin asignación a esa sucursal: `BRANCH_NOT_ASSIGNED`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": false,
  "reason": "BRANCH_NOT_ASSIGNED",
  "keycloak_user_id": "compras.test",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": null
}
```

---

[← Paso anterior](03-asignar-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-efecto-de-inactivar.md)

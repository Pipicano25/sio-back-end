# Paso 04 de 05 — Comprobar el acceso operativo (vía técnica)

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](03-asignar-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-efecto-de-inactivar.md)

**Objetivo:** Consultar el acceso de `operario.dao` como lo haría Purchase con su identidad técnica.

**Necesita (de pasos anteriores):** `<SUC_PRINCIPAL>`, `<SUC_SECUNDARIA>` — pasos [02](02-empresa-y-sucursales.md)

---

## 1. Acceso a la sucursal principal para crear compras

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=operario.dao&permission=perm:purchase:purchases:create
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `lookup`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `lookup`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `superadmin` (por `perm:all:all:all`).

**Por qué se hace así**

- `operario.dao` es miembro activo de la empresa y su grupo `Compras` tiene `perm:purchase:purchases:create`: `allowed: true`.
- El permiso se evalúa con los roles de `operario.dao` leídos de Keycloak, no con los del token que consulta.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": true,
  "reason": null,
  "keycloak_user_id": "operario.dao",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": "perm:purchase:purchases:create"
}
```

## 2. Acceso para ver la rentabilidad de ventas (denegado)

```http
GET /api/v1/operational-access?branch_id=<SUC_PRINCIPAL>&keycloak_user_id=operario.dao&permission=perm:sales:sales:read-profitability
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `lookup`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `lookup`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `superadmin` (por `perm:all:all:all`).

**Por qué se hace así**

- El operario (`Compras`, `Ventas` e `Inventario`) no tiene `perm:sales:sales:read-profitability`: `allowed: false`, `PERMISSION_DENIED`, con `200` (no es un error del contrato).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": false,
  "reason": "PERMISSION_DENIED",
  "keycloak_user_id": "operario.dao",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": "perm:sales:sales:read-profitability"
}
```

## 3. Acceso a la sucursal secundaria (permitido sin asignación)

```http
GET /api/v1/operational-access?branch_id=<SUC_SECUNDARIA>&keycloak_user_id=operario.dao
```

**Permisos que exige la URL (todos):** `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `lookup`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `lookup`
- ℹ️ Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `superadmin` (por `perm:all:all:all`).

**Por qué se hace así**

- La membresía da acceso a todas las sucursales activas de la empresa: `allowed: true` aunque no tenga asignación ahí (enmienda 2026-11-19). Los límites los ponen los permisos de Keycloak.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "allowed": true,
  "reason": null,
  "keycloak_user_id": "operario.dao",
  "application_user_id": "<USR_COMPRADOR>",
  "permission": null
}
```

---

[← Paso anterior](03-asignar-sucursal.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-efecto-de-inactivar.md)

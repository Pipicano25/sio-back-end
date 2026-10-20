# Parámetro `user_branch_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Operational Context](../servicios/operational-context.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **asignación de un usuario a una sucursal**: el registro que autoriza a una membresía ([application_user_id](application-user-id.md)) a operar en una sucursal ([branch_id](branch-id.md)) concreta. Un usuario tiene una asignación por cada sucursal |
| Nombre en las rutas | `user_branch_id` (`/user-branches/{user_branch_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí para consultar, retirar (`deactivate`) o reactivar una asignación |
| Ejemplo (ficticio) | `e8c5f9de-8af8-4aa7-8f96-536c03dc33ac` |
| Quién lo genera | Operational Context, al asignar la sucursal (`id` de la respuesta `201`) |
| Alcance | Empresa: solo lo ven los miembros de la empresa o quien tiene `platform:administer` |

## Cómo obtenerlo

**Desde el usuario** (las sucursales de una membresía):

**¿Qué hace?** Lista, con paginación, las asignaciones de sucursal de una membresía, con el estado de la asignación, de la membresía, de la sucursal y de la empresa, y el acceso efectivo calculado (`operational_access`). Por defecto solo asignaciones `ACTIVE`; con `status=INACTIVE` muestra las retiradas, que pueden reactivarse. Descrita en [Administración empresarial, API 11](../principales/administracion-empresarial.md#11-consultar-las-sucursales-asignadas-a-un-usuario).

| | |
|---|---|
| Método y ruta | `GET /api/v1/application-users/{application_user_id}/user-branches` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` |
| Parámetros de ruta | `application_user_id` (UUID) — [cómo obtenerlo](application-user-id.md) |
| Parámetros de consulta | `status` (`ACTIVE` por defecto o `INACTIVE`), `page` (≥ 1), `page_size` (1–100, por defecto 20) |
| Permiso | `perm:operational-context:user_branches:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/application-users/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/user-branches?status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

**Desde la sucursal** (los usuarios asignados a ella): `GET https://sio-operational-context-dev.onrender.com/api/v1/branches/{branch_id}/user-branches` lista las asignaciones de una sucursal, es decir, qué miembros pueden operar en ella; mismos parámetros de consulta, mismo permiso, misma respuesta y mismos errores que la anterior ([Administración empresarial, API 13](../principales/administracion-empresarial.md#13-consultar-los-usuarios-asignados-a-una-sucursal)).

Respuesta `200` (modelo `PaginatedResponse[UserBranchResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e8c5f9de-8af8-4aa7-8f96-536c03dc33ac",
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "assigned_at": "2026-10-19T15:04:05Z",
      "assigned_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "deactivated_at": null,
      "membership_status": "ACTIVE",
      "branch_status": "ACTIVE",
      "company_status": "ACTIVE",
      "operational_access": {
        "allowed": true,
        "reason": null
      },
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. No confundir con `items[].branch_id` (la sucursal) ni con `items[].application_user_id` (la membresía). Guarda `items[].version` para retirar o reactivar la asignación. Para ver asignaciones retiradas, consulta con `status=INACTIVE`.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `perm:operational-context:user_branches:read` | Mostrar que faltan permisos y el `trace_id` |
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La membresía (o la sucursal) no existe o su empresa está fuera del alcance del usuario | Volver a leer la lista de usuarios o de sucursales |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `status` inválido, paginación fuera de rango o UUID mal formado | Corregir los parámetros |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde |

## Si la asignación no existe todavía (operación `HIGH_RISK`)

**¿Qué hace la API de creación?** `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` con `{"branch_id": "…"}` (permiso `perm:operational-context:user_branches:create`) autoriza a una membresía `ACTIVE` a operar en una sucursal `ACTIVE` de la misma empresa. Devuelve `201` con la asignación; el `user_branch_id` es su campo `id`. Desde ese momento el usuario ve la sucursal con `allowed: true` en su contexto operativo. Cuerpo y respuesta completos en [Administración empresarial, API 12](../principales/administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `perm:operational-context:user_branches:create` | Mostrar que faltan permisos |
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La membresía o la sucursal no existen o están fuera del alcance | Volver a leer las listas |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_USER_BRANCH` | Ya existe una asignación (activa o inactiva) de ese usuario a esa sucursal | Si está inactiva, localizarla con `status=INACTIVE` y reactivarla |
| `422` | `OPERATIONAL_CONTEXT.BRANCH_COMPANY_MISMATCH` | La sucursal es de otra empresa | Elegir una sucursal de la empresa de la membresía |
| `422` | `OPERATIONAL_CONTEXT.MEMBERSHIP_INACTIVE` / `COMPANY_INACTIVE` / `BRANCH_INACTIVE` | Membresía, empresa o sucursal inactivas | Reactivar el que corresponda |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Falta `branch_id`, no es UUID o hay campos desconocidos | Corregir el cuerpo |


## Cómo usarlo después

- Consultar una asignación: `GET https://sio-operational-context-dev.onrender.com/api/v1/user-branches/{user_branch_id}` devuelve el mismo objeto `UserBranchResponse` de la lista, con el acceso efectivo actualizado ([Operational Context 24](../servicios/operational-context.md#24-get-user-branchesuser_branch_id), permiso `perm:operational-context:user_branches:read`). Errores: `401`; `403 OPERATIONAL_CONTEXT.FORBIDDEN`; `404 OPERATIONAL_CONTEXT.NOT_FOUND` si no existe o está fuera del alcance; `422 OPERATIONAL_CONTEXT.VALIDATION_ERROR` si el UUID está mal formado.
- Retirar el acceso a la sucursal: `POST …/user-branches/{user_branch_id}/deactivate` con `{"version": n}` pasa la asignación a `INACTIVE` sin borrarla; el usuario deja de poder operar en esa sucursal (`allowed: false`, `reason: USER_BRANCH_INACTIVE`) y las API de negocio le responden `403 BRANCH_ACCESS_DENIED` ([operación 25](../servicios/operational-context.md#25-post-user-branchesuser_branch_iddeactivate), permiso `perm:operational-context:user_branches:delete`, `HIGH_RISK`). Errores: `401`; `403 FORBIDDEN`; `404 NOT_FOUND`; `409 VERSION_CONFLICT` (`version` desactualizada); `409 INVALID_STATUS_TRANSITION` («La asignación ya se encuentra en estado INACTIVE.»); `422 VALIDATION_ERROR` si falta `version` o hay campos desconocidos.
- Devolver el acceso: `POST …/user-branches/{user_branch_id}/reactivate` con `{"version": n}` vuelve a dejar la asignación `ACTIVE`; el acceso efectivo dependerá además de que membresía, sucursal y empresa sigan activas ([operación 26](../servicios/operational-context.md#26-post-user-branchesuser_branch_idreactivate), permiso `perm:operational-context:user_branches:update`). Errores: los mismos que al retirar, con `409 INVALID_STATUS_TRANSITION` («La asignación ya se encuentra en estado ACTIVE.») si ya estaba activa.
- Las API de negocio nunca lo piden: Sales, Purchase e Inventory comprueban el acceso con `branch_id` y el token del usuario.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` | La asignación no existe o su empresa está fuera del alcance del usuario |
| `409 OPERATIONAL_CONTEXT.VERSION_CONFLICT` | La `version` enviada no es la actual |
| `409 OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION` | Ya estaba en el estado solicitado |
| `operational_access.allowed: false` | La asignación, la membresía, la sucursal o la empresa están inactivas; `reason` indica cuál |

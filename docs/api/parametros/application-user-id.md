# Parámetro `application_user_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Operational Context](../servicios/operational-context.md)

| Propiedad | Valor |
|---|---|
| Qué representa | La **membresía de un usuario en una empresa** (usuario operativo). Un mismo usuario de Keycloak tiene un `application_user_id` distinto por cada empresa a la que pertenece. Es el registro sobre el que se asignan sucursales y se activa o inactiva el acceso |
| Nombre en las rutas y cuerpos | `application_user_id` (Operational Context: `/application-users/{application_user_id}`; filtro `?application_user_id=` en Audit; campo `application_user_id` en respuestas de Sales, Purchase e Inventory) |
| Tipo | UUID (texto) |
| Obligatorio | Sí para asignar sucursales, consultar o cambiar el estado de una membresía |
| Ejemplo (ficticio) | `a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d` |
| Quién lo genera | Operational Context, al registrar el usuario en la empresa (`id` de la respuesta `201`) |
| Alcance | Empresa |

## Cómo obtenerlo

**El propio usuario:** `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` ([Acceso y contexto operativo, API 5](../principales/acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario)) devuelve las membresías del usuario del token; el campo exacto es `memberships[].application_user_id`, uno por empresa. Sus errores son `401`, `403 OPERATIONAL_CONTEXT.FORBIDDEN` (falta `perm:operational-context:application_users:read`) y `503 OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE`; la llamada completa está en [company_id](company-id.md).

**Otros usuarios de la empresa (administración):**

**¿Qué hace?** Lista, con paginación y búsqueda por nombre o correo, las membresías de la empresa: quién tiene acceso, su nombre para mostrar, su cuenta de Keycloak, su persona en Party Identity y su estado. Por defecto solo `ACTIVE`. Es la pantalla de usuarios de la empresa y la fuente de `application_user_id` para asignar sucursales o cambiar el estado. Descrita en [Administración empresarial, API 9](../principales/administracion-empresarial.md#9-consultar-los-usuarios-de-una-empresa).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/application-users` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page`, `page_size` (1–100), `status` (`ACTIVE` por defecto, `INACTIVE`), `search` (≤ 160, en nombre y correo de referencia), `keycloak_user_id`, `person_identity_id` |
| Permiso | `perm:operational-context:application_users:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users?search=ana&status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (`PaginatedResponse[ApplicationUserResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "display_name": "Ana Pérez",
      "reference_email": "compras@ejemplo.com",
      "status": "ACTIVE",
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

**Campo exacto:** `items[].id`. `keycloak_user_id` enlaza con la cuenta de Keycloak ([keycloak_user_id](keycloak-user-id.md)) y `person_identity_id` con la persona en Party Identity ([person_identity_id](person-identity-id.md)).

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | El token no tiene `perm:operational-context:application_users:read` | Mostrar que faltan permisos y el `trace_id` |
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella (ni `platform:administer`) | Volver a leer el contexto operativo |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 160, `keycloak_user_id` > 255, `status` inválido o UUID mal formado | Corregir los parámetros |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde |

## Si la membresía no existe todavía (operación `HIGH_RISK`)

**¿Qué hace la API de creación?** Da acceso a la empresa a una persona que ya tiene cuenta en Keycloak, creando su membresía `ACTIVE`. El servicio verifica la cuenta en Keycloak (por `sub` o por `username`) y la persona en Party Identity. La nueva membresía no tiene sucursales: hay que asignarlas después ([user_branch_id](user-branch-id.md)). Descrita paso a paso en [Administración empresarial, API 10](../principales/administracion-empresarial.md#10-asociar-un-usuario-a-una-empresa-crear-membresía).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/application-users` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` |
| Permiso | `perm:operational-context:application_users:create` |
| Clasificación | `HIGH_RISK` (otorga acceso a los datos de la empresa) |

Cuerpo (`ApplicationUserCreate`; rechaza campos adicionales): **exactamente uno** de `keycloak_user_id` (el `sub` de Keycloak) o `username` (Operational Context lo resuelve en Keycloak), más `person_identity_id` ([cómo obtenerlo](person-identity-id.md)), `display_name` y `reference_email` opcional. El usuario debe existir en Keycloak; la misma persona o cuenta no puede tener dos membresías en la misma empresa.

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "person_identity_id": "a0e1d2c3-b4a5-4968-8776-655443322110",
  "display_name": "Ana Pérez",
  "reference_email": "ana.perez@ejemplo.com"
}
```

La respuesta `201` devuelve `ApplicationUserResponse`; el `application_user_id` es su campo `id`. El flujo completo está en [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | El token no tiene `perm:operational-context:application_users:create` | Mostrar que faltan permisos y el `trace_id` |
| `404` | `OPERATIONAL_CONTEXT.NOT_FOUND` | La empresa no existe o el usuario no tiene membresía `ACTIVE` en ella (ni `platform:administer`) | Volver a leer el contexto operativo |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP` | La persona o la cuenta ya tiene membresía activa en la empresa | Buscarla en la lista; si está inactiva, reactivarla |
| `422` | `OPERATIONAL_CONTEXT.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden crear membresías |
| `422` | `OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND` / `KEYCLOAK_USER_DISABLED` / `TECHNICAL_ACCOUNT_NOT_ALLOWED` | La cuenta no existe, está deshabilitada o es una cuenta de servicio | Corregir en Keycloak |
| `422` | `OPERATIONAL_CONTEXT.PERSON_IDENTITY_NOT_FOUND` / `PERSON_IDENTITY_INACTIVE` | La persona no existe o está inactiva en Party Identity | Registrarla o reactivarla |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Ninguno o ambos de `keycloak_user_id`/`username`, `display_name` vacío o > 160, correo inválido, campo desconocido | Corregir el formulario |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Keycloak o Party Identity no responden | Reintentar más tarde |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): `{application_user_id}` de la ruta de las API 11, 12, 14 y 15; filtro `application_user_id` de la API 16. Lo devuelve la [API 10 (crear membresía)](../principales/administracion-empresarial.md#10-asociar-un-usuario-a-una-empresa-crear-membresía) en el campo `id` y la API 9 en `items[].id`.
- Asignar una sucursal (autoriza al usuario a operar en ella): `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` con `{"branch_id": "…"}`; qué hace y sus errores en [Administración empresarial, API 12](../principales/administracion-empresarial.md#12-asignar-un-usuario-a-una-sucursal).
- Ver sus sucursales y el acceso efectivo en cada una: `GET …/application-users/{application_user_id}/user-branches`; [API 11](../principales/administracion-empresarial.md#11-consultar-las-sucursales-asignadas-a-un-usuario).
- Retirar o devolver el acceso a la empresa: `POST …/application-users/{application_user_id}/deactivate` o `/reactivate` con `{"version": n}`; [API 14](../principales/administracion-empresarial.md#14-inactivar-una-membresía) y [API 15](../principales/administracion-empresarial.md#15-reactivar-una-membresía).
- Filtrar la trazabilidad de la empresa por actor: `?application_user_id=` en la [API 16 (auditoría)](../principales/administracion-empresarial.md#16-consultar-la-trazabilidad-de-la-empresa-auditoría).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` | La empresa no está en el alcance del usuario (sin membresía `ACTIVE` ni `platform:administer`) |
| `422` al crear | Se enviaron ambos o ninguno de `keycloak_user_id`/`username`, el usuario no existe en Keycloak o la persona no existe en Party Identity |
| `409` al crear | La cuenta o la persona ya tiene membresía en esa empresa |

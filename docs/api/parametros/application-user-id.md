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

**El propio usuario:** `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` devuelve `memberships[].application_user_id` por cada empresa ([company_id](company-id.md) explica la llamada).

**Otros usuarios de la empresa (administración):**

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/application-users` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/application-users` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page`, `page_size` (1–100), `status` (`ACTIVE` por defecto, `INACTIVE`), `search` (≤ 160, en nombre y correo de referencia), `keycloak_user_id`, `person_identity_id` |
| Permiso | `perm:operational-context:application_users:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/application-users?search=ana&status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`PaginatedResponse[ApplicationUserResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
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

**Campo exacto:** `items[].id`. `keycloak_user_id` enlaza con la cuenta de Keycloak y `person_identity_id` con la persona en Party Identity.

## Si la membresía no existe todavía (operación `HIGH_RISK`)

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

## Cómo usarlo después

- Asignar una sucursal: `POST https://sio-operational-context-dev.onrender.com/api/v1/application-users/{application_user_id}/user-branches` con `{"branch_id": "…"}` ([operación 22](../servicios/operational-context.md#22-post-application-usersapplication_user_iduser-branches)).
- Ver sus sucursales: `GET …/application-users/{application_user_id}/user-branches` (operación 21).
- Inactivar o reactivar la membresía: `POST …/application-users/{application_user_id}/deactivate` o `/reactivate` con `{"version": n}` (operaciones 19 y 20).
- Filtrar la auditoría de la empresa por actor: `?application_user_id=` en Audit.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` | La empresa no está en el alcance del usuario (sin membresía `ACTIVE` ni `platform:administer`) |
| `422` al crear | Se enviaron ambos o ninguno de `keycloak_user_id`/`username`, el usuario no existe en Keycloak o la persona no existe en Party Identity |
| `409` al crear | La cuenta o la persona ya tiene membresía en esa empresa |

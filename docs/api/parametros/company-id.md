# Parámetro `company_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Operational Context](../servicios/operational-context.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Identificador de una **empresa** cliente de SIO. Casi todas las operaciones de negocio cuelgan de `/companies/{company_id}/…` y solo son visibles para usuarios con membresía `ACTIVE` en esa empresa |
| Nombre en las rutas y cuerpos | `company_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí, en todas las rutas de empresa y sucursal |
| Ejemplo (ficticio) | `550e8400-e29b-41d4-a716-446655440000` |
| Quién lo genera | Operational Context, al crear la empresa (`id` de la respuesta) |
| Quién lo entrega al frontend | Operational Context |

## Opción recomendada: contexto operativo del usuario

**¿Qué hace?** Devuelve, para el usuario del token, sus membresías (una por empresa), el estado de cada una y las sucursales que tiene asignadas con el acceso efectivo (`allowed`). No pagina ni filtra. Es la consulta que debe hacerse justo después del login y la forma recomendada de obtener `company_id`; está descrita paso a paso en [Acceso y contexto operativo, API 5](../principales/acceso-y-contexto-operativo.md#5-consultar-las-empresas-y-sucursales-del-usuario).

| | |
|---|---|
| Método y ruta | `GET /api/v1/me/operational-context` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Parámetros | Ninguno |
| Permiso | `perm:operational-context:application_users:read` (lo incluyen todos los grupos de la plantilla del realm) |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `MeOperationalContextResponse`; identificadores ilustrativos):

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "memberships": [
    {
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": [
        {
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "user_branch_status": "ACTIVE",
          "branch_status": "ACTIVE",
          "allowed": true,
          "reason": null
        }
      ]
    }
  ]
}
```

**Campo exacto:** `memberships[].company_id`. Usa solo las membresías con `status` y `company_status` en `ACTIVE`. Si `memberships` está vacío, el usuario no pertenece a ninguna empresa y recibirá `404` en todas las rutas de empresa: pide al administrador que cree su usuario de aplicación.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `perm:operational-context:application_users:read` | Mostrar que faltan permisos y el `trace_id` |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde |

## Opción alternativa: listar empresas

**¿Qué hace?** Lista, con paginación, las empresas en las que el usuario tiene membresía `ACTIVE` (todas, para un administrador de plataforma), con sus datos de contacto, dirección, zona horaria y moneda. Por defecto solo empresas `ACTIVE`. Útil para la administración de empresas; para la sesión del usuario basta el contexto operativo. Descrita en [Administración empresarial, API 2](../principales/administracion-empresarial.md#2-consultar-las-empresas-del-usuario).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies` |
| Parámetros de consulta | `page` (≥1, por defecto 1), `page_size` (1–100, por defecto 20), `status` (`ACTIVE` por defecto o `INACTIVE`), `organization_identity_id`, `country_id`, `city_id` (UUID, opcionales) |
| Permiso | `perm:operational-context:companies:read` |
| Alcance | Un usuario normal solo ve las empresas en las que tiene membresía `ACTIVE`; quien tiene `perm:operational-context:platform:administer` ve todas |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/companies?page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[CompanyResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "organization_identity_id": "0f1e2d3c-4b5a-4968-8776-655443322110",
      "email": "contacto@empresa-ejemplo.test",
      "phone": "+57 601 000 0000",
      "address_line": "Calle 1 # 2-3",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": "110111",
      "latitude": "4.7110",
      "longitude": "-74.0721",
      "timezone": "America/Bogota",
      "default_currency": "COP",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T14:30:00Z",
      "updated_at": "2026-01-15T14:30:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. La empresa **no tiene campo `name`**: su razón social está en la identidad de organización (`organization_identity_id`) de [Party Identity](organization-identity-id.md), campo `legal_name`. Para mostrar el nombre de la empresa hay que consultar `GET https://sio-party-identity-dev.onrender.com/api/v1/organization-identities/{organization_identity_id}` (permiso `perm:party-identity:organization_identities:read`) y leer `legal_name`.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | El token no tiene `perm:operational-context:companies:read` | Mostrar que faltan permisos y el `trace_id` |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | `page` < 1, `page_size` fuera de 1–100, `status` distinto de `ACTIVE`/`INACTIVE` o un filtro UUID mal formado | Corregir los parámetros |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde |

## Si la empresa no existe todavía

**¿Qué hace la API de creación?** `POST https://sio-operational-context-dev.onrender.com/api/v1/companies` da de alta la empresa vinculándola a una identidad de organización de Party Identity. Es una operación de plataforma: exige `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer`. No crea sucursales ni membresías. El `company_id` es el campo `id` de la respuesta `201`. Cuerpo, respuesta y errores completos en [Administración empresarial, API 1](../principales/administracion-empresarial.md#1-crear-empresa).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | Falta `companies:create` o `platform:administer` | Mostrar que faltan permisos y el `trace_id` |
| `409` | `OPERATIONAL_CONTEXT.DUPLICATE_ORGANIZATION_IDENTITY` | La organización ya tiene una empresa | Buscar la empresa existente |
| `422` | `OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND` / `_INACTIVE` | La identidad no existe o está inactiva en Party Identity | Registrarla o reactivarla |
| `422` | `OPERATIONAL_CONTEXT.COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND`, `CITY_NOT_FOUND`, `LOCATION_INACTIVE`, `GEOGRAPHY_INCOHERENT` | Ubicación inválida | Corregir la ubicación |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Formato inválido o campo desconocido | Corregir el formulario |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Party Identity o Geography no responden | Reintentar más tarde |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): es el `{company_id}` de la ruta de las API 3 a 6, 9, 10 y 16 a 21; nunca va en el cuerpo. Lo devuelve la API 1 (crear empresa) en el campo `id`.
- En la ruta: `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales`.
- Como filtro de alcance en `GET /api/v1/operational-access?company_id=…` ([Permisos §6](../guias/permisos.md#6-comprobar-el-acceso-antes-de-actuar)).
- Nunca lo guardes fijo en el código: cambia por usuario y por entorno.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` en `/companies/{company_id}` | El UUID no existe **o** el usuario no tiene membresía `ACTIVE` en esa empresa |
| `403` en cualquier ruta de empresa de Purchase, Sales, Inventory, Commercial Relationship o Audit con `code` `OPERATIONAL_ACCESS_DENIED` | El token no cubre `perm:operational-context:application_users:read`, necesario para que el servicio consulte el acceso operativo |
| `memberships: []` | El usuario existe en Keycloak pero no tiene usuario de aplicación en ninguna empresa |

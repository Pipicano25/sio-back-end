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

Devuelve solo las empresas en las que el usuario autenticado tiene membresía, con sus sucursales. Es la consulta que debe hacerse justo después del login.

| | |
|---|---|
| Método y ruta | `GET /api/v1/me/operational-context` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Parámetros | Ninguno |
| Permiso | `perm:operational-context:application_users:read` (lo incluyen todos los grupos de la plantilla del realm) |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Accept: application/json'
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

## Opción alternativa: listar empresas

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies` |
| Parámetros de consulta | `page` (≥1, por defecto 1), `page_size` (1–100, por defecto 20), `status` (`ACTIVE` por defecto o `INACTIVE`), `organization_identity_id`, `country_id`, `city_id` (UUID, opcionales) |
| Permiso | `perm:operational-context:companies:read` |
| Alcance | Un usuario normal solo ve las empresas en las que tiene membresía `ACTIVE`; quien tiene `perm:operational-context:platform:administer` ve todas |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies?page=1&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
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

**Campo exacto:** `items[].id`. La empresa **no tiene campo `name`**: su razón social está en la identidad de organización (`organization_identity_id`) de [Party Identity](organization-identity-id.md), campo `legal_name`. Para mostrar el nombre de la empresa hay que consultar `GET /api/v1/organization-identities/{organization_identity_id}` en Party Identity.

## Si la empresa no existe todavía

Crear una empresa es una operación de plataforma (`WRITE`): `POST /api/v1/companies` en Operational Context exige `perm:operational-context:companies:create` **y** `perm:operational-context:platform:administer`. El `company_id` es el campo `id` de la respuesta `201`. Detalle en la ficha de [Operational Context](../servicios/operational-context.md).

## Cómo usarlo después

- En la ruta: `GET https://sio-sales-dev.onrender.com/api/v1/companies/{company_id}/sales`.
- Como filtro de alcance en `GET /api/v1/operational-access?company_id=…` ([Permisos §6](../guias/permisos.md#6-comprobar-el-acceso-antes-de-actuar)).
- Nunca lo guardes fijo en el código: cambia por usuario y por entorno.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 OPERATIONAL_CONTEXT.NOT_FOUND` en `/companies/{company_id}` | El UUID no existe **o** el usuario no tiene membresía `ACTIVE` en esa empresa |
| `403` en cualquier ruta de empresa de Purchase, Sales, Inventory, Commercial Relationship o Audit con `code` `OPERATIONAL_ACCESS_DENIED` | El token no cubre `perm:operational-context:application_users:read`, necesario para que el servicio consulte el acceso operativo |
| `memberships: []` | El usuario existe en Keycloak pero no tiene usuario de aplicación en ninguna empresa |

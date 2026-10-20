# Parámetro `organization_identity_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Party Identity](../servicios/party-identity.md)

| Propiedad | Valor |
|---|---|
| Qué representa | La **identidad de una organización** (NIT u otro identificador, razón social) en el registro compartido de SIO. Es la base de los proveedores, de los clientes organización y de las propias empresas de la plataforma |
| Nombre en las rutas y cuerpos | `organization_identity_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear un proveedor; sí al crear un cliente con `customer_kind = ORGANIZATION`; sí al crear una empresa |
| Ejemplo (ficticio) | `0f1e2d3c-4b5a-4968-8776-655443322111` |
| Quién lo genera | Party Identity, al crear la identidad (`id`) |
| Alcance | Global |

## Cómo obtenerlo

**¿Qué hace?** Busca en el registro compartido de organizaciones de SIO (todas las empresas lo comparten) por identificación o nombre, con paginación. Devuelve la razón social, el nombre comercial, el tipo y número de identificación y el estado. Es el paso previo a crear una empresa, un proveedor o un cliente organización: primero se busca y solo si no existe se crea. Ficha técnica: [Party Identity 9](../servicios/party-identity.md#9-get-organization-identities).

| | |
|---|---|
| Método y ruta | `GET /api/v1/organization-identities` |
| URL completa | `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` |
| Parámetros de consulta | `search` (máx. 120; identificación o nombre), `country_id` (UUID), `identification_type` (string), `registration_status` (máx. 30), `status` (`ACTIVE` por defecto, `INACTIVE`), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:party-identity:organization_identities:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=distribuidora' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[OrganizationIdentityResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "0f1e2d3c-4b5a-4968-8776-655443322111",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "NIT",
      "identification_number": "900123456-7",
      "legal_name": "Distribuidora Ejemplo S.A.S.",
      "trade_name": "DistriEjemplo",
      "organization_type": null,
      "registration_status": null,
      "website": null,
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-01T09:55:00Z",
      "updated_at": "2026-02-01T09:55:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. `legal_name` es la razón social; úsala también para mostrar el nombre de una empresa de la plataforma (ver [company_id](company-id.md)).

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PARTY_IDENTITY.FORBIDDEN` | El token no tiene `perm:party-identity:organization_identities:read` | Mostrar que faltan permisos y el `trace_id` |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `search` > 120, paginación fuera de rango, `status` inválido o UUID mal formado | Corregir los parámetros |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Base de datos o Geography no disponibles | Reintentar más tarde |

## Si la organización no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** `POST https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` (permiso `perm:party-identity:organization_identities:create`) registra la identidad legal de una organización: país, tipo y número de identificación (validados con la regla del país), razón social y nombre comercial. Devuelve `201` con la identidad creada; el `organization_identity_id` es su campo `id`. Es un registro global compartido por todas las empresas: busca antes de crear. Cuerpo y ejemplo en [Party Identity 10](../servicios/party-identity.md#10-post-organization-identities).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PARTY_IDENTITY.FORBIDDEN` | El token no tiene `perm:party-identity:organization_identities:create` | Mostrar que faltan permisos y el `trace_id` |
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | Ya existe una identidad con ese país, tipo y número | Buscarla con `search` y reutilizar su `id` |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple la regla activa del tipo de identificación | Mostrar la regla (`identification-type-rules`) y corregir |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | `country_id` no existe o está inactivo en Geography | Corregir el país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente, formato inválido o campo desconocido | Corregir el formulario |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Base de datos o Geography no disponibles | Reintentar más tarde |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): campo `organization_identity_id` del cuerpo de la [API 1 (crear empresa)](../principales/administracion-empresarial.md#1-crear-empresa) y de la API 4; filtro de la API 2.
- `POST /companies/{company_id}/company-suppliers` → `organization_identity_id` ([company_supplier_id](supplier-id.md)).
- `POST /companies/{company_id}/company-customers` con `customer_kind: "ORGANIZATION"` → `organization_identity_id` ([company_customer_id](customer-id.md)).
- Crear la empresa en Operational Context (vincula la identidad a una empresa de SIO): campo `organization_identity_id` del cuerpo; qué hace y sus errores en [Administración empresarial, API 1](../principales/administracion-empresarial.md#1-crear-empresa).
- Filtros `?organization_identity_id=` al listar empresas, clientes y proveedores.

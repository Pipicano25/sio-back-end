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

| | |
|---|---|
| Método y ruta | `GET /api/v1/organization-identities` |
| URL completa | `https://sio-party-identity-dev.onrender.com/api/v1/organization-identities` |
| Parámetros de consulta | `search` (máx. 120; identificación o nombre), `country_id` (UUID), `identification_type` (string), `registration_status` (máx. 30), `status` (`ACTIVE` por defecto, `INACTIVE`), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:party-identity:organization_identities:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/organization-identities?search=distribuidora' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
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

## Si la organización no existe todavía (operación `WRITE`)

`POST /api/v1/organization-identities` (permiso `perm:party-identity:organization_identities:create`) crea la identidad y devuelve `201` con su `id`. Campos, reglas por país y duplicados (`409`) en la ficha de [Party Identity](../servicios/party-identity.md). Busca antes de crear: el registro es compartido por todas las empresas.

## Cómo usarlo después

- `POST /companies/{company_id}/company-suppliers` → `organization_identity_id` ([company_supplier_id](supplier-id.md)).
- `POST /companies/{company_id}/company-customers` con `customer_kind: "ORGANIZATION"` → `organization_identity_id` ([company_customer_id](customer-id.md)).
- `POST /api/v1/companies` en Operational Context → `organization_identity_id` de la nueva empresa.
- Filtros `?organization_identity_id=` al listar empresas, clientes y proveedores.

# Parámetro `person_identity_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Party Identity](../servicios/party-identity.md)

| Propiedad | Valor |
|---|---|
| Qué representa | La **identidad de una persona natural** (tipo y número de identificación, nombres) en el registro compartido de SIO. Se usa para incorporar clientes personas y para vincular usuarios de aplicación |
| Nombre en las rutas y cuerpos | `person_identity_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear un cliente con `customer_kind = PERSON`; según la operación en Operational Context |
| Ejemplo (ficticio) | `a0e1d2c3-b4a5-4968-8776-655443322110` |
| Quién lo genera | Party Identity, al crear la identidad (`id`) |
| Alcance | Global (registro compartido); la lectura exige permiso, no membresía |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/person-identities` |
| URL completa | `https://sio-party-identity-dev.onrender.com/api/v1/person-identities` |
| Parámetros de consulta | `search` (máx. 120; identificación o nombres), `identification_country_id` (UUID), `identification_type` (string), `verification_status` (`UNVERIFIED`, `VERIFIED`, `SUSPENDED`), `status` (`ACTIVE` por defecto, `INACTIVE`), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:party-identity:person_identities:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=1012345678' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[PersonIdentityResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "a0e1d2c3-b4a5-4968-8776-655443322110",
      "identification_country_id": "c0a80101-0000-4000-8000-000000000001",
      "identification_type": "CC",
      "identification_number": "1012345678",
      "first_name": "Ana",
      "middle_name": null,
      "last_name": "Pérez",
      "second_last_name": null,
      "birth_date": "1990-05-20",
      "verification_status": "UNVERIFIED",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-01T09:50:00Z",
      "updated_at": "2026-02-01T09:50:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Los valores de `identification_type` dependen de las reglas por país (`identification-type-rules`) documentadas en la ficha de Party Identity.

## Si la persona no existe todavía (operación `WRITE`)

`POST /api/v1/person-identities` (permiso `perm:party-identity:person_identities:create`) crea la identidad y devuelve `201` con su `id`. Los campos obligatorios, las reglas de identificación por país y la detección de duplicados (`409`) están en la ficha de [Party Identity](../servicios/party-identity.md). Es `WRITE` sobre un registro compartido por todas las empresas: verifica antes con `search` que no exista.

## Cómo usarlo después

- `POST /companies/{company_id}/company-customers` con `customer_kind: "PERSON"` → `person_identity_id` ([company_customer_id](customer-id.md)).
- Filtro `?person_identity_id=` al listar clientes y usuarios de aplicación.

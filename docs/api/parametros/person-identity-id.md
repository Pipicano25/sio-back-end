# Parámetro `person_identity_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Party Identity](../servicios/party-identity.md)

| Propiedad | Valor |
|---|---|
| Qué representa | La **identidad de una persona natural** (tipo y número de identificación, nombres) en el registro compartido de SIO. Se usa para incorporar clientes personas y para vincular usuarios de aplicación |
| Nombre en las rutas y cuerpos | `person_identity_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí al crear un cliente con `customer_kind = PERSON`; sí al crear la membresía de un usuario en una empresa (Operational Context) |
| Ejemplo (ficticio) | `a0e1d2c3-b4a5-4968-8776-655443322110` |
| Quién lo genera | Party Identity, al crear la identidad (`id`) |
| Alcance | Global (registro compartido); la lectura exige permiso, no membresía |

## Cómo obtenerlo

**¿Qué hace?** Busca en el registro compartido de personas de SIO por número de identificación o nombres, con paginación. Devuelve tipo y número de identificación, nombres, fecha de nacimiento, estado de verificación y estado. Es el paso previo a crear un cliente persona o la membresía de un usuario: primero se busca y solo si no existe se crea. Ficha técnica: [Party Identity 3](../servicios/party-identity.md#3-get-person-identities).

| | |
|---|---|
| Método y ruta | `GET /api/v1/person-identities` |
| URL completa | `https://sio-party-identity-dev.onrender.com/api/v1/person-identities` |
| Parámetros de consulta | `search` (máx. 120; identificación o nombres), `identification_country_id` (UUID), `identification_type` (string), `verification_status` (`UNVERIFIED`, `VERIFIED`, `SUSPENDED`), `status` (`ACTIVE` por defecto, `INACTIVE`), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:party-identity:person_identities:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-party-identity-dev.onrender.com/api/v1/person-identities?search=1012345678' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
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

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PARTY_IDENTITY.FORBIDDEN` | El token no tiene `perm:party-identity:person_identities:read` | Mostrar que faltan permisos y el `trace_id` |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | `search` > 120, paginación fuera de rango, `verification_status` o `status` inválidos, UUID mal formado | Corregir los parámetros |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Base de datos o Geography no disponibles | Reintentar más tarde |

## Si la persona no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** `POST https://sio-party-identity-dev.onrender.com/api/v1/person-identities` (permiso `perm:party-identity:person_identities:create`) registra la identidad de una persona natural: país, tipo y número de identificación (validados con la regla del país, que puede exigir fecha de nacimiento), nombres y apellidos. Devuelve `201` con la identidad creada; el `person_identity_id` es su campo `id`. Es un registro global compartido por todas las empresas: busca antes de crear. Cuerpo y ejemplo en [Party Identity 4](../servicios/party-identity.md#4-post-person-identities).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PARTY_IDENTITY.FORBIDDEN` | El token no tiene `perm:party-identity:person_identities:create` | Mostrar que faltan permisos y el `trace_id` |
| `409` | `PARTY_IDENTITY.DUPLICATE_IDENTIFICATION` | Ya existe una identidad con ese país, tipo y número | Buscarla con `search` y reutilizar su `id` |
| `422` | `PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER` | El número no cumple la regla activa del tipo de identificación | Mostrar la regla (`identification-type-rules`) y corregir |
| `422` | `PARTY_IDENTITY.BIRTH_DATE_REQUIRED` / `AGE_OUT_OF_RANGE` / `BIRTH_DATE_IN_FUTURE` | La regla exige fecha de nacimiento válida | Pedir o corregir la fecha |
| `422` | `PARTY_IDENTITY.COUNTRY_NOT_FOUND` | `identification_country_id` no existe o está inactivo | Corregir el país |
| `422` | `PARTY_IDENTITY.VALIDATION_ERROR` | Campo obligatorio ausente, formato inválido o campo desconocido | Corregir el formulario |
| `503` | `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` | Base de datos o Geography no disponibles | Reintentar más tarde |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md): campo `person_identity_id` del cuerpo de la [API 10 (crear membresía)](../principales/administracion-empresarial.md#10-asociar-un-usuario-a-una-empresa-crear-membresía); filtro de la API 9.
- `POST /companies/{company_id}/company-customers` con `customer_kind: "PERSON"` → `person_identity_id` ([company_customer_id](customer-id.md)).
- Filtro `?person_identity_id=` al listar clientes y usuarios de aplicación.

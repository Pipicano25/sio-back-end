# Parámetros geográficos: `country_id`, `administrative_division_id`, `city_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Geography](../servicios/geography.md)

Los tres identificadores forman una jerarquía global (país → división administrativa → ciudad) que piden Operational Context (dirección de empresas y sucursales), Party Identity (país de identificación o de registro) y Commercial Relationship (direcciones de clientes y proveedores).

| Propiedad | `country_id` | `administrative_division_id` | `city_id` |
|---|---|---|---|
| Qué representa | País (ISO 3166-1) | Departamento, estado o provincia del país | Ciudad o municipio de una división |
| Nombre en las rutas | `country_id` (`/global-countries/{country_id}`) | `division_id` en Geography; `administrative_division_id` o `parent_division_id` como filtro y en los cuerpos de otros servicios | `city_id` |
| Tipo | UUID (texto) | UUID (texto) | UUID (texto) |
| Ejemplo (ficticio) | `c0a80101-0000-4000-8000-000000000001` | `c0a80101-0000-4000-8000-000000000002` | `c0a80101-0000-4000-8000-000000000003` |
| Quién lo genera | Geography (catálogo global; las altas las hace la administración de la plataforma) | | |
| Alcance | Global: solo requiere el permiso de lectura | | |

> Geography **no usa el prefijo `/api/v1`**: las rutas cuelgan directamente de `https://sio-geography-dev.onrender.com`.

## Cómo obtener `country_id`

| | |
|---|---|
| Método y ruta | `GET /global-countries` |
| URL completa | `https://sio-geography-dev.onrender.com/global-countries` |
| Parámetros de consulta | `page`, `page_size` (1–100), `search` (≤ 120; nombre, ISO2 o ISO3), `iso2_code` (2 caracteres), `iso3_code` (3 caracteres), `status` (`ACTIVE`, `INACTIVE`) |
| Permiso | `perm:geography:global_countries:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-countries?iso2_code=CO' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "iso2_code": "CO",
      "iso3_code": "COL",
      "name": "Colombia",
      "phone_prefix": "+57",
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

**Campo exacto:** `items[].id`.

## Cómo obtener `administrative_division_id`

| | |
|---|---|
| Método y ruta | `GET /global-administrative-divisions` |
| URL completa | `https://sio-geography-dev.onrender.com/global-administrative-divisions` |
| Parámetros de consulta | `page`, `page_size`, `search`, `country_id` (UUID; filtra por país), `parent_division_id` (UUID; subdivisiones), `division_type`, `code`, `status` |
| Permiso | `perm:geography:global_administrative_divisions:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-administrative-divisions?country_id=c0a80101-0000-4000-8000-000000000001&page_size=100' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "parent_division_id": "c0a80101-0000-4000-8000-000000000002",
      "code": "CUN",
      "name": "Cundinamarca",
      "division_type": "DEPARTMENT",
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

**Campo exacto:** `items[].id`. Comprueba que `country_id` del elemento coincida con el país elegido.

## Cómo obtener `city_id`

| | |
|---|---|
| Método y ruta | `GET /global-cities` |
| URL completa | `https://sio-geography-dev.onrender.com/global-cities` |
| Parámetros de consulta | `page`, `page_size`, `search`, `country_id`, `administrative_division_id`, `code`, `status` |
| Permiso | `perm:geography:global_cities:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=c0a80101-0000-4000-8000-000000000002&search=bogot' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e6d7d0c7-a0be-4f4b-8bca-631867ff85c8",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "code": "BOG",
      "name": "Bogotá",
      "latitude": "4.6097",
      "longitude": "-74.0817",
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

**Campo exacto:** `items[].id`. La ciudad trae `administrative_division_id` y `country_id`; los tres deben ser coherentes entre sí cuando se envían juntos.

## Cómo usarlos después

- Crear o actualizar una empresa o sucursal en Operational Context: campos `country_id`, `administrative_division_id` y `city_id` de la dirección ([Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md)). Operational Context valida la jerarquía contra Geography y responde `422` si la ciudad no pertenece a la división o al país.
- Registrar identidades en Party Identity: `identification_country_id` (personas) y `country_id` de registro (organizaciones) ([person_identity_id](person-identity-id.md), [organization_identity_id](organization-identity-id.md)).
- Direcciones de clientes y proveedores en Commercial Relationship.
- Filtrar empresas: `GET https://sio-operational-context-dev.onrender.com/api/v1/companies?country_id=…&city_id=…`.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 GEOGRAPHY.NOT_FOUND` | El identificador no existe |
| `422` en Operational Context o Party Identity | La ciudad no pertenece a la división o al país enviados, o el registro está `INACTIVE` |
| `503 DEPENDENCY_UNAVAILABLE` | El servicio que valida la dirección no pudo consultar Geography |

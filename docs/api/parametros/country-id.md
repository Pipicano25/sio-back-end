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

**¿Qué hace?** Lista los países del catálogo global, con paginación y búsqueda por nombre o código ISO. Es el primer selector en cascada de una dirección y la fuente del país de identificación en Party Identity. Ficha técnica: [Geography 3](../servicios/geography.md#3-get-global-countries).

| | |
|---|---|
| Método y ruta | `GET /global-countries` |
| URL completa | `https://sio-geography-dev.onrender.com/global-countries` |
| Parámetros de consulta | `page`, `page_size` (1–100), `search` (≤ 120; nombre, ISO2 o ISO3), `iso2_code` (2 caracteres), `iso3_code` (3 caracteres), `status` (`ACTIVE`, `INACTIVE`) |
| Permiso | `perm:geography:global_countries:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-geography-dev.onrender.com/global-countries?iso2_code=CO' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000001",
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

**Campo exacto:** `items[].id` → se envía como `country_id`.

**Posibles errores de esta API** (Geography responde errores planos de FastAPI, sin Problem Details):

| HTTP | Cuerpo | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar |
| `403` | `{"detail": …}` | Falta `perm:geography:global_countries:read` | Mostrar que faltan permisos |
| `422` | `{"detail": [ {"loc": …, "msg": …} ]}` | `page_size` fuera de 1–100, `search` > 120, código ISO con longitud distinta de la exigida, `status` inválido o UUID mal formado | Leer `loc` y `msg` y corregir el parámetro |
| `503` | `{"detail": "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."}` | Base de datos caída | Reintentar más tarde |

## Cómo obtener `administrative_division_id`

**¿Qué hace?** Lista las divisiones administrativas (departamentos, estados, provincias) del catálogo global; con `country_id` devuelve solo las del país elegido, que es el uso habitual en el segundo selector en cascada. Ficha técnica: [Geography 8](../servicios/geography.md#8-get-global-administrative-divisions).

| | |
|---|---|
| Método y ruta | `GET /global-administrative-divisions` |
| URL completa | `https://sio-geography-dev.onrender.com/global-administrative-divisions` |
| Parámetros de consulta | `page`, `page_size`, `search`, `country_id` (UUID; filtra por país), `parent_division_id` (UUID; subdivisiones), `division_type`, `code`, `status` |
| Permiso | `perm:geography:global_administrative_divisions:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-geography-dev.onrender.com/global-administrative-divisions?country_id=c0a80101-0000-4000-8000-000000000001&page_size=100' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000002",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "parent_division_id": null,
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

**Campo exacto:** `items[].id` → se envía como `administrative_division_id`. Comprueba que `country_id` del elemento coincida con el país elegido.

**Posibles errores de esta API** (Geography responde errores planos de FastAPI, sin Problem Details):

| HTTP | Cuerpo | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar |
| `403` | `{"detail": …}` | Falta `perm:geography:global_administrative_divisions:read` | Mostrar que faltan permisos |
| `422` | `{"detail": [ {"loc": …, "msg": …} ]}` | `page_size` fuera de 1–100, `search` > 120, código ISO con longitud distinta de la exigida, `status` inválido o UUID mal formado | Leer `loc` y `msg` y corregir el parámetro |
| `503` | `{"detail": "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."}` | Base de datos caída | Reintentar más tarde |

## Cómo obtener `city_id`

**¿Qué hace?** Lista las ciudades o municipios del catálogo global; con `administrative_division_id` devuelve solo las de la división elegida (tercer selector en cascada). Cada ciudad trae su división y su país, con lo que se puede comprobar la coherencia antes de enviar los tres. Ficha técnica: [Geography 13](../servicios/geography.md#13-get-global-cities).

| | |
|---|---|
| Método y ruta | `GET /global-cities` |
| URL completa | `https://sio-geography-dev.onrender.com/global-cities` |
| Parámetros de consulta | `page`, `page_size`, `search`, `country_id`, `administrative_division_id`, `code`, `status` |
| Permiso | `perm:geography:global_cities:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-geography-dev.onrender.com/global-cities?administrative_division_id=c0a80101-0000-4000-8000-000000000002&search=bogot' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (valores ilustrativos):

```json
{
  "items": [
    {
      "id": "c0a80101-0000-4000-8000-000000000003",
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

**Campo exacto:** `items[].id` → se envía como `city_id`. La ciudad trae `administrative_division_id` y `country_id`; los tres deben ser coherentes entre sí cuando se envían juntos.

**Posibles errores de esta API** (Geography responde errores planos de FastAPI, sin Problem Details):

| HTTP | Cuerpo | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar |
| `403` | `{"detail": …}` | Falta `perm:geography:global_cities:read` | Mostrar que faltan permisos |
| `422` | `{"detail": [ {"loc": …, "msg": …} ]}` | `page_size` fuera de 1–100, `search` > 120, código ISO con longitud distinta de la exigida, `status` inválido o UUID mal formado | Leer `loc` y `msg` y corregir el parámetro |
| `503` | `{"detail": "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."}` | Base de datos caída | Reintentar más tarde |

## Cómo usarlos después

- En [Administración empresarial](../principales/administracion-empresarial.md): campos `country_id`, `administrative_division_id` y `city_id` del cuerpo de las API 1, 4, 5 y 8; filtros `country_id` y `city_id` de la API 2 y `city_id` de la API 6.
- Crear o actualizar una empresa o sucursal en Operational Context: campos `country_id`, `administrative_division_id` y `city_id` de la dirección. Operational Context valida la jerarquía contra Geography y responde `422 GEOGRAPHY_INCOHERENT`, `LOCATION_INACTIVE` o `*_NOT_FOUND`; qué hace cada API y sus errores en [Administración empresarial](../principales/administracion-empresarial.md), API 1, 4, 5 y 8, y el flujo en [Crear una empresa y una sucursal](../ejemplos/crear-empresa-y-sucursal.md).
- Registrar identidades en Party Identity: `identification_country_id` (personas) y `country_id` de registro (organizaciones) ([person_identity_id](person-identity-id.md), [organization_identity_id](organization-identity-id.md)).
- Direcciones de clientes y proveedores en Commercial Relationship.
- Filtrar empresas: `GET https://sio-operational-context-dev.onrender.com/api/v1/companies?country_id=…&city_id=…`.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 GEOGRAPHY.NOT_FOUND` | El identificador no existe |
| `422` en Operational Context o Party Identity | La ciudad no pertenece a la división o al país enviados, o el registro está `INACTIVE` |
| `503 DEPENDENCY_UNAVAILABLE` | El servicio que valida la dirección no pudo consultar Geography |

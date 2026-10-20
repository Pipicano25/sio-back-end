# Parámetro `branch_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Operational Context](../servicios/operational-context.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Identificador de una **sucursal** de una empresa. Las existencias, ventas, compras y reportes por sucursal dependen de él |
| Nombre en las rutas y cuerpos | `branch_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí en las rutas `/companies/{company_id}/branches/{branch_id}/…` y en los cuerpos de creación de ventas y compras; opcional como filtro en varias listas |
| Ejemplo (ficticio) | `7c9e6679-7425-40de-944b-e07fc1f90ae7` |
| Quién lo genera | Operational Context, al crear la sucursal (`id` de la respuesta) |
| Quién lo entrega al frontend | Operational Context |

## Opción recomendada: contexto operativo del usuario

Devuelve, dentro de cada membresía, las sucursales asignadas al usuario y si puede operar en ellas ahora (`allowed`).

| | |
|---|---|
| Método y ruta | `GET /api/v1/me/operational-context` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Parámetros | Ninguno |
| Permiso | `perm:operational-context:application_users:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (fragmento; el documento completo está en [company_id](company-id.md)):

```json
{
  "memberships": [
    {
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "branches": [
        {
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "user_branch_status": "ACTIVE",
          "branch_status": "ACTIVE",
          "allowed": true,
          "reason": null
        },
        {
          "branch_id": "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f",
          "user_branch_status": "INACTIVE",
          "branch_status": "ACTIVE",
          "allowed": false,
          "reason": "USER_BRANCH_INACTIVE"
        }
      ]
    }
  ]
}
```

**Campo exacto:** `memberships[].branches[].branch_id`. Ofrece al usuario solo las sucursales con `allowed: true`. El valor de `reason` sigue el catálogo de [Permisos §6](../guias/permisos.md#6-comprobar-el-acceso-antes-de-actuar).

Esta respuesta no incluye el nombre de la sucursal; para mostrarlo usa la lista siguiente y cruza por `id`.

## Opción alternativa: listar las sucursales de la empresa

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/branches` |
| URL completa | `https://sio-operational-context-dev.onrender.com/api/v1/companies/{company_id}/branches` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 160 caracteres; busca en código y nombre), `status` (`ACTIVE` por defecto o `INACTIVE`), `city_id` (UUID) |
| Permiso | `perm:operational-context:branches:read` |
| Alcance | Empresa: el usuario debe tener membresía `ACTIVE`; si no, `404` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches?status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[BranchResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "code": "SUC-001",
      "name": "Sucursal Centro",
      "email": "centro@empresa-ejemplo.test",
      "phone": "+57 601 000 0001",
      "address_line": "Carrera 7 # 10-20",
      "country_id": "c0a80101-0000-4000-8000-000000000001",
      "administrative_division_id": "c0a80101-0000-4000-8000-000000000002",
      "city_id": "c0a80101-0000-4000-8000-000000000003",
      "postal_code": "110111",
      "latitude": null,
      "longitude": null,
      "timezone": null,
      "effective_timezone": "America/Bogota",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-01-15T14:35:00Z",
      "updated_at": "2026-01-15T14:35:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Esta lista muestra todas las sucursales de la empresa, tenga o no el usuario acceso a cada una; para saber en cuáles puede operar, cruza con `/me/operational-context`.

## Si la sucursal no existe todavía

`POST /api/v1/companies/{company_id}/branches` (`WRITE`, permiso `perm:operational-context:branches:create`) devuelve `201` con el `id` de la nueva sucursal. Para que un usuario pueda operar en ella, además hay que asignársela (`user_branches`). Detalle en la ficha de [Operational Context](../servicios/operational-context.md).

## Cómo usarlo después

- En cuerpos de creación: `"branch_id"` de `POST /companies/{company_id}/sales` y `POST /companies/{company_id}/purchases`.
- En rutas por sucursal: `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-overviews`.
- Como filtro: `?branch_id=` en Inventory, Sales, Purchase y Business Reporting.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `403 SALES.BRANCH_ACCESS_DENIED` / `PURCHASE.BRANCH_ACCESS_DENIED` | El usuario no tiene asignada la sucursal o la asignación está `INACTIVE` |
| `404` en una ruta de sucursal | La sucursal no pertenece a esa empresa, no existe o el usuario no tiene membresía en la empresa |
| `allowed: false` con `BRANCH_INACTIVE` | La sucursal fue desactivada; no puede operarse |

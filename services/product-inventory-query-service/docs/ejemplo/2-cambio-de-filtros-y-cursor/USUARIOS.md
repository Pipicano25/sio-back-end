# Usuarios del ejercicio 2

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 |
| --- | --- | --- | --- | --- | --- |
| `admin.sio` | `200` | `200` | `200` | `200` | `422` |
| `admin.dao` | `200` | `200` | `200` | `200` | `422` |
| `operario.dao` | `200` | `200` | `200` | `200` | `422` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2` | `perm:product-inventory-query:product_overviews:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=3&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 4 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 5 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada` | `perm:product-inventory-query:product_overviews:read` |

## Ejemplos

- Puede: `operario.dao` (grupos `Compras`, `Ventas` e `Inventario`) consulta las cuatro rutas con precios, existencias y mínimos; `admin.dao` (grupo `admin`) y `admin.sio` (grupo `superadmin`) también.
- No puede: un usuario sin los permisos de estas consultas recibe `403` (ningún usuario de prueba del realm está en ese caso desde la spec 026).

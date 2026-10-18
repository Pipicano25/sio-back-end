# Usuarios del ejercicio 2

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 |
| --- | --- | --- | --- | --- | --- |
| `admin.test` | `200` | `200` | `200` | `200` | `422` |
| `supervisor.test` | `200` | `200` | `200` | `200` | `422` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `200` | `200` | `200` | `200` | `422` |
| `inventario.test` | `200` | `200` | `200` | `200` | `422` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2` | `perm:product-inventory-query:product_overviews:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=3&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 4 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 5 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada` | `perm:product-inventory-query:product_overviews:read` |

## Ejemplos

- Puede: `ventas.test` consulta productos e inventario (con precios y existencias, sin mínimos); `inventario.test` consulta las cuatro (con existencias y mínimos, sin precios); `supervisor.test` y `admin.test` ven todos los bloques.
- No puede: `compras.test`, `reportes.test` y `consulta.test` reciben `403` en las cuatro consultas.

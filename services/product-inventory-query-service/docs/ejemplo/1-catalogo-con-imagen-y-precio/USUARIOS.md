# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 |
| --- | --- | --- |
| `admin.test` | `200` | `200` |
| `supervisor.test` | `200` | `200` |
| `compras.test` | `403` | `403` |
| `ventas.test` | `200` | `200` |
| `inventario.test` | `200` | `200` |
| `reportes.test` | `403` | `403` |
| `consulta.test` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2` | `perm:product-inventory-query:product_overviews:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |

## Ejemplos

- Puede: `ventas.test` consulta productos e inventario (con precios y existencias, sin mínimos); `inventario.test` consulta las cuatro (con existencias y mínimos, sin precios); `supervisor.test` y `admin.test` ven todos los bloques.
- No puede: `compras.test`, `reportes.test` y `consulta.test` reciben `403` en las cuatro consultas.

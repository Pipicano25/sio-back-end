# Usuarios y permisos de product-inventory-query-service

Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

## Cómo se evalúan los permisos

- Cada consulta exige su permiso funcional `perm:product-inventory-query:{recurso}:read` (`sio-auth`). El `403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.
- Antes de consultar cualquier otro servicio, Operational Context verifica con el token del usuario la membresía `ACTIVE` en la empresa. Con ella se lee cualquier sucursal de la empresa, sin asignación.
- Cada bloque de la respuesta exige su permiso; si falta, el bloque no aparece (no se envía con `null`) y un filtro que dependa de él responde `403`:

| Bloque | Permiso |
| --- | --- |
| Precios | `perm:commercial-relationship:price_list_items:read` |
| Existencias | `perm:product-inventory-query:stock:read` |
| Mínimos | `perm:inventory:product-policies:read` |

- `low-stock-products` exige además los permisos de existencias y de mínimos.
- Ningún usuario recibe costos unitarios, promedio ni FIFO, márgenes ni valoración económica: no existen en las respuestas. La valoración está fuera del alcance de la spec 022; sigue disponible en Inventory con sus propios permisos.
- Los precios de venta y su moneda vienen de Commercial Relationship; las existencias, de Inventory, y las imágenes, de Product Catalog.
- `ventas` ve existencias sin tener `perm:inventory:balances:read`: las ve por `perm:product-inventory-query:stock:read` (D-022-1).

## Usuarios de prueba

| Usuario | Grupo | Productos | Inventario | Bajo stock | Resumen | Precios | Existencias | Mínimos |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `administradores` | Sí | Sí | Sí | Sí | Sí | Sí | Sí |
| `supervisor.test` | `supervisores` | Sí | Sí | Sí | Sí | Sí | Sí | Sí |
| `compras.test` | `compras` | No | No | No | No | Sí | No | No |
| `ventas.test` | `ventas` | Sí | Sí | No | No | Sí | Sí | No |
| `inventario.test` | `inventario` | Sí | Sí | Sí | Sí | No | Sí | Sí |
| `reportes.test` | `reportes` | No | No | No | No | Sí | No | No |
| `consulta.test` | `consulta` | No | No | No | No | Sí | No | No |

## Cómo obtener los tokens

Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=ventas.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

## Matriz de URL

| Ejercicio | Paso | URL | Permiso |
| --- | --- | --- | --- |
| 1 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2` | `perm:product-inventory-query:product_overviews:read` |
| 1 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 2 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2` | `perm:product-inventory-query:product_overviews:read` |
| 2 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 2 | 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=3&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 2 | 4 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>` | `perm:product-inventory-query:product_overviews:read` |
| 2 | 5 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada` | `perm:product-inventory-query:product_overviews:read` |
| 3 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina` | `perm:product-inventory-query:inventory_overviews:read` |
| 3 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina&branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:inventory_overviews:read` |
| 3 | 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?branch_id=d22b0000-0000-4000-8000-000000000099` | `perm:product-inventory-query:inventory_overviews:read` |
| 4 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products` | `perm:product-inventory-query:low_stock_products:read` |
| 4 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products?branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:low_stock_products:read` |
| 5 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `perm:product-inventory-query:inventory_summary:read` |
| 5 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary?branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:inventory_summary:read` |
| 6 | 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `perm:product-inventory-query:product_overviews:read` |
| 6 | 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `perm:product-inventory-query:product_overviews:read` |
| 6 | 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?minimum_state=BELOW_MINIMUM` | `perm:product-inventory-query:inventory_overviews:read` |
| 6 | 4 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `perm:product-inventory-query:inventory_summary:read` |

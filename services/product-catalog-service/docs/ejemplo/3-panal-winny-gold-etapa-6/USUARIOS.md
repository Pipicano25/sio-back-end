# Usuarios y permisos — Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: puede ejecutar **todo el ejercicio**.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `WINNY`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `WINNY`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Buscar el fabricante Tecnoquímicas en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `WINNY`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `WINNY`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` también sirve para crear y modificar, pero no para inactivar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos-base.md) | 1. Consultar la unidad `UND` | `GET /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 2. Consultar el tipo de empaque `PACK` | `GET /api/v1/packaging-types` | `perm:product-catalog:packaging-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 3. Consultar el tipo de grupo `GROUP_1` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 4. Consultar el tipo de grupo `GROUP_2` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 5. Consultar el tipo de grupo `GROUP_4` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 6. Buscar el fabricante Tecnoquímicas en Party Identity Service | `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 7. Consultar el país Colombia en Geography Service (solo si el fabricante no existe) | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 8. Crear el fabricante Tecnoquímicas (solo si no existe) | `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-marca.md) | 1. Crear la marca `WINNY` | `POST /api/v1/brands` | `perm:product-catalog:brands:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 1. Crear la categoría raíz `CUIDADO_BEBE` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 2. Crear la subcategoría `PANALES_BEBE` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 1. Crear el atributo `TALLA_PANAL` (lista de opciones) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 2. Opción `RN` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 3. Opción `P` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 4. Opción `M` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 5. Opción `G` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 6. Opción `XG` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 7. Opción `XXG` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 8. Opción `XXXG` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 9. Crear el atributo `ETAPA_PANAL` (entero) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 1. Asociar `TALLA_PANAL` (obligatorio y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 2. Asociar `ETAPA_PANAL` (opcional y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-crear-producto.md) | 1. Crear el producto | `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-clasificar-producto.md) | 1. Asignar la categoría `PANALES_BEBE` | `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-registrar-valores-de-atributos.md) | 1. Talla = XXXG | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-registrar-valores-de-atributos.md) | 2. Etapa = 6 | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-crear-presentacion.md) | 1. Presentación `PAQUETE_X30` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-registrar-codigos-de-barras.md) | 1. EAN `7701021118264` (principal) | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-registrar-codigos-de-barras.md) | 2. EAN `7701021118912` | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 1. Grupo 1 `0113` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 2. Grupo 1 `0113` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 3. Grupo 1 `0113` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 4. Grupo 2 `0691` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 5. Grupo 2 `0691` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 6. Grupo 2 `0691` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 7. Grupo 4 `0125` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 8. Grupo 4 `0125` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 9. Grupo 4 `0125` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-verificar-y-buscar-por-atributos.md) | 1. Consultar el producto | `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-verificar-y-buscar-por-atributos.md) | 2. Buscar pañales talla XXXG | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-verificar-y-buscar-por-atributos.md) | 3. Buscar pañales talla XXXG de etapa 6 en la categoría | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-verificar-y-buscar-por-atributos.md) | 4. Error esperado: filtrar por un atributo no filtrable | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 06 (*Crear el producto*):

```bash
curl -s -X POST "http://localhost:8003/api/v1/products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"product_type": "GOOD", "canonical_name": "Winny Gold pañal etapa 6 talla XXXG", "global_brand_id": "<MARCA_WINNY>", "manufacturer_organization_id": "<FABRICANTE_TECNOQUIMICAS>", "base_unit_id": "<UND>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:product-catalog:products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la marca Winny*), llamada 1:

```bash
curl -s -X POST "http://localhost:8003/api/v1/brands" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"code": "WINNY", "name": "Winny", "description": "Marca de pañales de Tecnoquímicas."}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/product-catalog/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:product-catalog:brands:create",
  "instance": "/api/v1/brands",
  "code": "PRODUCT_CATALOG.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene lecturas explícitas (en el catálogo: `perm:product-catalog:attribute-definitions:read`, `perm:product-catalog:brands:read`, `perm:product-catalog:categories:read`, `perm:product-catalog:global_categories:read`, `perm:product-catalog:global_category_attributes:read`, `perm:product-catalog:global_product_attribute_values:read`, `perm:product-catalog:global_products:read`, `perm:product-catalog:global_units_of_measure:read`, `perm:product-catalog:group-types:read`, `perm:product-catalog:packaging-types:read`, `perm:product-catalog:product_assets:read`, `perm:product-catalog:product_attribute_definitions:read`, `perm:product-catalog:products:read`, `perm:product-catalog:units-of-measure:read`): puede **leer**, pero la URL exige `perm:product-catalog:brands:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta el resultado (permitido)

```bash
curl -s -X GET "http://localhost:8003/api/v1/products/<PRODUCTO>" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 12: `perm:product-catalog:products:read` cubre `perm:product-catalog:products:read`. Lo mismo pasa con `supervisor.test`, `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, que tienen lectura sobre `product-catalog`.

### 4. `inventario.test` busca el fabricante (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/organization-identities?search=TECNOQUIMICAS" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Respuesta `403 Forbidden` (formato de Party Identity Service):

```json
{
  "detail": "Falta el permiso requerido: perm:party-identity:organization_identities:read"
}
```

`inventario.test` lee el catálogo (`perm:product-catalog:all:read`) y Geography, pero **no** tiene ningún permiso sobre `party-identity`. Sí pueden hacer esta búsqueda: `supervisor.test`, `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` (lectura explícita de `perm:party-identity:organization_identities:read`).

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

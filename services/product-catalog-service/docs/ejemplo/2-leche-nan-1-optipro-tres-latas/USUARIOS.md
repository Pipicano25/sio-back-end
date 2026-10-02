# Usuarios y permisos — Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: puede ejecutar **todo el ejercicio**.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `NAN`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `NAN`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Buscar el fabricante Nestlé en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `NAN`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `NAN`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 11, 12.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` también sirve para crear y modificar, pero no para inactivar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos-base.md) | 1. Consultar la unidad `G` | `GET /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 2. Consultar el tipo de empaque `CAN` | `GET /api/v1/packaging-types` | `perm:product-catalog:packaging-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 3. Consultar el tipo de grupo `GROUP_1` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 4. Consultar el tipo de grupo `GROUP_2` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 5. Consultar el tipo de grupo `GROUP_4` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 6. Buscar el fabricante Nestlé en Party Identity Service | `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 7. Consultar el país Colombia en Geography Service (solo si el fabricante no existe) | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 8. Crear el fabricante Nestlé (solo si no existe) | `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-marca.md) | 1. Crear la marca `NAN` | `POST /api/v1/brands` | `perm:product-catalog:brands:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 1. Crear la categoría raíz `ALIMENTOS` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 2. Crear la subcategoría `LECHES` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 1. Crear el atributo `ETAPA_FORMULA` (entero) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 2. Crear el atributo `FORMULA_INFANTIL` (sí/no) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 1. Asociar `FORMULA_INFANTIL` (obligatorio y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 2. Asociar `ETAPA_FORMULA` (opcional y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-crear-producto.md) | 1. Crear el producto | `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-clasificar-producto.md) | 1. Asignar la categoría `LECHES` | `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-registrar-valores-de-atributos.md) | 1. Fórmula infantil = sí | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-registrar-valores-de-atributos.md) | 2. Etapa = 1 | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-crear-presentaciones.md) | 1. Presentación `LATA_400G` (fila 7334) | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-crear-presentaciones.md) | 2. Presentación `LATA_900G` (fila 6138) | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-crear-presentaciones.md) | 3. Presentación `LATA_1100G` (fila 7333) | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-registrar-codigos-de-barras.md) | 1. EAN `7501059227453` → lata 400 g | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-registrar-codigos-de-barras.md) | 2. EAN `7501059227644` → lata 900 g | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-registrar-codigos-de-barras.md) | 3. EAN `7501059279124` → lata 1100 g | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 1. Grupo 1 `0687` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 2. Grupo 1 `0687` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 3. Grupo 1 `0687` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 4. Grupo 2 `0689` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 5. Grupo 2 `0689` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 6. Grupo 2 `0689` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 7. Grupo 4 `0336` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 8. Grupo 4 `0336` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 9. Grupo 4 `0336` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-verificar-resultado.md) | 1. Consultar el producto con su detalle | `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-verificar-resultado.md) | 2. Escanear el código de la lata de 900 g | `GET /api/v1/products/by-identifier/{codigo}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-verificar-resultado.md) | 3. Listar las fórmulas infantiles de etapa 1 | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 06 (*Crear el producto (uno solo para las tres filas)*):

```bash
curl -s -X POST "http://localhost:8003/api/v1/products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"product_type": "GOOD", "canonical_name": "NAN 1 Optipro leche en polvo", "description": "Fórmula láctea infantil en polvo, etapa 1.", "global_brand_id": "<MARCA_NAN>", "manufacturer_organization_id": "<FABRICANTE_NESTLE>", "base_unit_id": "<G>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:product-catalog:products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la marca NAN*), llamada 1:

```bash
curl -s -X POST "http://localhost:8003/api/v1/brands" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"code": "NAN", "name": "NAN", "description": "Línea de fórmulas infantiles de Nestlé."}'
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
curl -s -X GET "http://localhost:8003/api/v1/products/<PRODUCTO>?expand=detail" \
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
curl -s -X GET "http://localhost:8002/organization-identities?search=NESTLE" \
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

# Usuarios y permisos — Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo)

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 12 (*Inactivar*): sobre `product-catalog` solo tiene `create`, `read`, `update`; le falta `deactivate`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `COLGATE`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `COLGATE`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Buscar el fabricante Colgate-Palmolive en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `COLGATE`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la marca `COLGATE`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 09, 11, 12, 13.

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
| [01](01-consultar-datos-base.md) | 6. Buscar el fabricante Colgate-Palmolive en Party Identity Service | `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 7. Consultar el país Colombia en Geography Service (solo si el fabricante no existe) | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 8. Crear el fabricante Colgate-Palmolive (solo si no existe) | `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-marca.md) | 1. Crear la marca `COLGATE` | `POST /api/v1/brands` | `perm:product-catalog:brands:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 1. Crear la categoría raíz `CUIDADO_ORAL` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-categorias.md) | 2. Crear la subcategoría `CEPILLOS_DENTALES` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 1. Crear el atributo `DUREZA_CERDAS` (lista de opciones) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 2. Opción `EXTRA_SUAVE` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 3. Opción `SUAVE` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 4. Opción `MEDIO` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 5. Opción `DURO` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-atributos.md) | 6. Crear el atributo `RANGO_EDAD` (texto) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 1. Asociar `DUREZA_CERDAS` | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 2. Asociar `RANGO_EDAD` | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-crear-producto.md) | 1. Crear el producto | `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-clasificar-y-registrar-atributos.md) | 1. Asignar la categoría `CEPILLOS_DENTALES` | `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-clasificar-y-registrar-atributos.md) | 2. Dureza = Extra suave | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-clasificar-y-registrar-atributos.md) | 3. Rango de edad = 2 a 5 años | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-crear-presentacion.md) | 1. Presentación `PACK_X2` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-codigo-interno-no-es-codigo-de-barras.md) | 1. Error esperado: registrarlo como EAN | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-codigo-interno-no-es-codigo-de-barras.md) | 2. Confirmar que el producto no tiene identificadores | `GET /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [10](10-agregar-imagen.md) | 1. Registrar la imagen principal | `POST /api/v1/products/{id}/assets` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 1. Grupo 1 `0005` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 2. Grupo 1 `0005` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 3. Grupo 1 `0005` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 4. Grupo 2 `0016` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 5. Grupo 2 `0016` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 6. Grupo 2 `0016` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 7. Grupo 4 `0213` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [11](11-crear-y-asignar-grupos.md) | 8. Grupo 4 `0213` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-crear-y-asignar-grupos.md) | 9. Grupo 4 `0213` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-inactivar-producto.md) | 1. Consultar el producto antes de inactivar | `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-inactivar-producto.md) | 2. Inactivar | `POST /api/v1/products/{id}/deactivate` | `perm:product-catalog:products:deactivate` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [13](13-verificar-producto-inactivo.md) | 1. Error esperado: agregar una presentación | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [13](13-verificar-producto-inactivo.md) | 2. Buscar productos inactivos | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [13](13-verificar-producto-inactivo.md) | 3. Consultar el detalle | `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

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
  -d '{"product_type": "GOOD", "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña", "global_brand_id": "<MARCA_COLGATE>", "manufacturer_organization_id": "<FABRICANTE_COLGATE>", "base_unit_id": "<UND>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:product-catalog:products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la marca Colgate*), llamada 1:

```bash
curl -s -X POST "http://localhost:8003/api/v1/brands" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"code": "COLGATE", "name": "Colgate"}'
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

`consulta.test` solo tiene `perm:all:all:read`: puede **leer** en todos los servicios, pero la URL exige `perm:product-catalog:brands:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta el resultado (permitido)

```bash
curl -s -X GET "http://localhost:8003/api/v1/products?status=INACTIVE&search=cepillo" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 13: `perm:all:all:read` cubre `perm:product-catalog:products:read`. Lo mismo pasa con `reportes.test`, `compras.test`, `ventas.test` e `inventario.test`, que tienen lectura sobre `product-catalog`.

### 4. `supervisor.test` intenta inactivar (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8003/api/v1/products/<PRODUCTO>/deactivate" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/product-catalog/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:product-catalog:products:deactivate",
  "instance": "/api/v1/products/{id}/deactivate",
  "code": "PRODUCT_CATALOG.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `deactivate`. Por eso pudo cargar todo el producto y no puede inactivarlo: esa acción queda para `admin.test`.

### 5. `inventario.test` busca el fabricante (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/organization-identities?search=COLGATE" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Respuesta `403 Forbidden` (formato de Party Identity Service):

```json
{
  "detail": "Falta el permiso requerido: perm:party-identity:organization_identities:read"
}
```

`inventario.test` lee el catálogo (`perm:product-catalog:all:read`) y Geography, pero **no** tiene ningún permiso sobre `party-identity`. `compras.test` y `ventas.test` sí pueden hacer esta búsqueda (`perm:party-identity:all:read`).

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

# Usuarios y permisos — Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: puede ejecutar **todo el ejercicio**.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la unidad `MG`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 08, 12, 13.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la unidad `MG`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 08, 12, 13.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Buscar el fabricante Siegfried en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 01, 08, 12, 13.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la unidad `MG`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 08, 12, 13.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la unidad `MG`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 08, 12, 13.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` también sirve para crear y modificar, pero no para inactivar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos-base.md) | 1. Consultar la unidad `UND` | `GET /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 2. Consultar el tipo de empaque `BOX` | `GET /api/v1/packaging-types` | `perm:product-catalog:packaging-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 3. Consultar el tipo de grupo `GROUP_1` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 4. Consultar el tipo de grupo `GROUP_2` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 5. Consultar el tipo de grupo `GROUP_3` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 6. Consultar el tipo de grupo `GROUP_4` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 7. Buscar el fabricante Siegfried en Party Identity Service | `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 8. Consultar el país Colombia en Geography Service (solo si el fabricante no existe) | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 9. Crear el fabricante Siegfried (solo si no existe) | `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-unidad-mg.md) | 1. Crear la unidad `MG` | `POST /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-marca.md) | 1. Crear la marca `ADOREM` | `POST /api/v1/brands` | `perm:product-catalog:brands:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-categorias.md) | 1. Crear la categoría raíz `MEDICAMENTOS` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-crear-categorias.md) | 2. Crear la subcategoría `MEDICAMENTOS_ETICOS` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 1. Crear el atributo `PRINCIPIO_ACTIVO` (texto) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 2. Crear el atributo `CONCENTRACION_MG` (decimal en mg) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 3. Crear el atributo `FORMA_FARMACEUTICA` (lista de opciones) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 4. Crear la opción `TABLETA` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 5. Crear la opción `CAPSULA` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-crear-atributos.md) | 6. Crear la opción `JARABE` | `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-asociar-atributos-a-la-categoria.md) | 1. Asociar `PRINCIPIO_ACTIVO` (obligatorio) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-asociar-atributos-a-la-categoria.md) | 2. Asociar `CONCENTRACION_MG` (obligatorio y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-asociar-atributos-a-la-categoria.md) | 3. Asociar `FORMA_FARMACEUTICA` (obligatorio y filtrable) | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-crear-producto.md) | 1. Crear el producto | `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-clasificar-producto.md) | 1. Asignar la categoría `MEDICAMENTOS_ETICOS` | `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [08](08-clasificar-producto.md) | 2. Consultar los atributos que ahora aplican | `GET /api/v1/products/{id}/applicable-attributes` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [08](08-clasificar-producto.md) | 3. Consultar la completitud | `GET /api/v1/products/{id}/completeness` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [09](09-registrar-valores-de-atributos.md) | 1. Principio activo = Acetaminofén | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-registrar-valores-de-atributos.md) | 2. Concentración = 500 mg | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [09](09-registrar-valores-de-atributos.md) | 3. Forma farmacéutica = Tableta | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-crear-presentaciones.md) | 1. Presentación base `TABLETA` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [10](10-crear-presentaciones.md) | 2. Presentación `CAJA_X100` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-registrar-codigos-de-barras.md) | 1. EAN `7707355056876` (principal de la caja) | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [11](11-registrar-codigos-de-barras.md) | 2. EAN `7707355052038` (segundo código de la caja) | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 1. Grupo 1 `0001` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-crear-y-asignar-grupos.md) | 2. Grupo 1 `0001` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 3. Grupo 1 `0001` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 4. Grupo 2 `0012` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-crear-y-asignar-grupos.md) | 5. Grupo 2 `0012` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 6. Grupo 2 `0012` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 7. Grupo 3 `0085` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-crear-y-asignar-grupos.md) | 8. Grupo 3 `0085` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 9. Grupo 3 `0085` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 10. Grupo 4 `0170` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [12](12-crear-y-asignar-grupos.md) | 11. Grupo 4 `0170` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-crear-y-asignar-grupos.md) | 12. Grupo 4 `0170` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [13](13-verificar-resultado.md) | 1. Consultar el producto con todo su detalle | `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [13](13-verificar-resultado.md) | 2. Buscar por el segundo código de barras | `GET /api/v1/products/by-identifier/{codigo}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [13](13-verificar-resultado.md) | 3. Buscar por atributos filtrables | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 07 (*Crear el producto*):

```bash
curl -s -X POST "http://localhost:8003/api/v1/products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"product_type": "GOOD", "canonical_name": "Acetaminofén 500 mg tableta", "description": "Analgésico y antipirético.", "global_brand_id": "<MARCA_ADOREM>", "manufacturer_organization_id": "<FABRICANTE_SIEGFRIED>", "base_unit_id": "<UND>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:product-catalog:products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la unidad de medida miligramo (`MG`)*), llamada 1:

```bash
curl -s -X POST "http://localhost:8003/api/v1/units-of-measure" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"code": "MG", "name": "Miligramo", "symbol": "mg", "measurement_type": "MASS", "allows_decimals": true}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/product-catalog/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:product-catalog:units-of-measure:create",
  "instance": "/api/v1/units-of-measure",
  "code": "PRODUCT_CATALOG.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene `perm:all:all:read`: puede **leer** en todos los servicios, pero la URL exige `perm:product-catalog:units-of-measure:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta el resultado (permitido)

```bash
curl -s -X GET "http://localhost:8003/api/v1/products/<PRODUCTO>?expand=detail" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 13: `perm:all:all:read` cubre `perm:product-catalog:products:read`. Lo mismo pasa con `reportes.test`, `compras.test`, `ventas.test` e `inventario.test`, que tienen lectura sobre `product-catalog`.

### 4. `inventario.test` busca el fabricante (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/organization-identities?search=SIEGFRIED" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Respuesta `403 Forbidden` (formato de Party Identity Service):

```json
{
  "detail": "Falta el permiso requerido: perm:party-identity:organization_identities:read"
}
```

`inventario.test` lee el catálogo (`perm:product-catalog:all:read`) y Geography, pero **no** tiene ningún permiso sobre `party-identity`. `compras.test` y `ventas.test` sí pueden hacer esta búsqueda (`perm:party-identity:all:read`).

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

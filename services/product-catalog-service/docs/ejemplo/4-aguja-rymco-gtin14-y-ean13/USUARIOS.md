# Usuarios y permisos — Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios de solo lectura obtuvieron `200` en las consultas.

## Resumen por usuario

- **`admin.sio`**: puede ejecutar **todo el ejercicio**.
- **`admin.dao`**: puede ejecutar **todo el ejercicio**.
- **`operario.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la unidad `PULG`*): sobre `product-catalog` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 10, 11.

**Para hacer el ejercicio completo use `admin.sio`** (grupo `superadmin`). `admin.dao` (grupo `admin`) también sirve para crear y modificar, pero no para inactivar ni eliminar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin.sio | admin.dao | operario.dao |
| --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos-base.md) | 1. Consultar la unidad `UND` | `GET /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 2. Consultar el tipo de empaque `BOX` | `GET /api/v1/packaging-types` | `perm:product-catalog:packaging-types:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 3. Consultar el tipo de grupo `GROUP_1` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 4. Consultar el tipo de grupo `GROUP_2` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 5. Consultar el tipo de grupo `GROUP_4` | `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 6. Buscar el fabricante Rymco en Party Identity Service | `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 7. Consultar el país Colombia en Geography Service (solo si el fabricante no existe) | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 8. Crear el fabricante Rymco (solo si no existe) | `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ |
| [02](02-crear-unidad-pulgada.md) | 1. Crear la unidad `PULG` | `POST /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:create` | ✅ | ✅ | ❌ |
| [03](03-crear-categorias.md) | 1. Crear la categoría raíz `DISPOSITIVOS_MEDICOS` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ |
| [03](03-crear-categorias.md) | 2. Crear la subcategoría `AGUJAS_HIPODERMICAS` | `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ |
| [04](04-crear-atributos.md) | 1. Crear el atributo `CALIBRE_AGUJA` (entero, sin unidad) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ |
| [04](04-crear-atributos.md) | 2. Crear el atributo `LONGITUD_AGUJA` (decimal en pulgadas) | `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 1. Asociar `CALIBRE_AGUJA` | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ |
| [05](05-asociar-atributos-a-la-categoria.md) | 2. Asociar `LONGITUD_AGUJA` | `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ |
| [06](06-crear-producto.md) | 1. Crear el producto | `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ |
| [07](07-clasificar-producto.md) | 1. Asignar la categoría | `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [08](08-registrar-valores-y-presentaciones.md) | 1. Calibre = 18 | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [08](08-registrar-valores-y-presentaciones.md) | 2. Longitud = 1.5 pulgadas | `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [08](08-registrar-valores-y-presentaciones.md) | 3. Presentación base `UNIDAD` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [08](08-registrar-valores-y-presentaciones.md) | 4. Presentación `CAJA_X100` | `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [09](09-registrar-identificadores.md) | 1. EAN-13 `7706634002856` → unidad | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [09](09-registrar-identificadores.md) | 2. GTIN-14 `27706634002850` → caja | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [09](09-registrar-identificadores.md) | 3. Referencia del fabricante `RFZC18B` → `OTHER` | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [09](09-registrar-identificadores.md) | 4. Error esperado: el mismo código como GTIN | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [09](09-registrar-identificadores.md) | 5. Error esperado: un GTIN registrado como `BARCODE` | `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 1. Grupo 1 `0005` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [10](10-crear-y-asignar-grupos.md) | 2. Grupo 1 `0005` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 3. Grupo 1 `0005` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 4. Grupo 2 `0016` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [10](10-crear-y-asignar-grupos.md) | 5. Grupo 2 `0016` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 6. Grupo 2 `0016` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 7. Grupo 4 `0278` — consultar si ya existe | `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ |
| [10](10-crear-y-asignar-grupos.md) | 8. Grupo 4 `0278` — crearlo (solo si la consulta vino vacía) | `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ |
| [10](10-crear-y-asignar-grupos.md) | 9. Grupo 4 `0278` — asignarlo al producto | `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ |
| [11](11-verificar-resultado.md) | 1. Escanear el GTIN-14 (caja) | `GET /api/v1/products/by-identifier/{codigo}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ |
| [11](11-verificar-resultado.md) | 2. Escanear el EAN-13 (unidad) | `GET /api/v1/products/by-identifier/{codigo}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ |
| [11](11-verificar-resultado.md) | 3. Buscar por la referencia del fabricante | `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.sio`

```bash
TOKEN_ADMIN_SIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.sio -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 06 (*Crear el producto (sin marca)*):

```bash
curl -s -X POST "http://localhost:8003/api/v1/products" \
  -H "Authorization: Bearer $TOKEN_ADMIN_SIO" \
  -H "Content-Type: application/json" \
  -d '{"product_type": "GOOD", "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas", "description": "Aguja hipodérmica estéril de un solo uso.", "manufacturer_organization_id": "<FABRICANTE_RYMCO>", "base_unit_id": "<UND>"}'
```

Responde `201 Created`: `admin.sio` tiene `perm:all:all:all`, que cubre `perm:product-catalog:products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `operario.dao` (Empleado) intenta crear (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la unidad pulgada (`PULG`)*), llamada 1:

```bash
curl -s -X POST "http://localhost:8003/api/v1/units-of-measure" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"code": "PULG", "name": "Pulgada", "symbol": "in", "measurement_type": "LENGTH", "allows_decimals": true}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/product-catalog/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/units-of-measure",
  "code": "PRODUCT_CATALOG.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

El grupo `empleado` solo lee el catálogo (`perm:product-catalog:all:read`): puede **leer**, pero la URL exige `perm:product-catalog:units-of-measure:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `operario.dao` (Empleado) consulta el resultado (permitido)

```bash
curl -s -X GET "http://localhost:8003/api/v1/products/by-identifier/27706634002850" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.sio` en el paso 11: `perm:product-catalog:all:read` cubre `perm:product-catalog:products:read`. Lo mismo pasa con `admin.dao`, que tienen lectura sobre `product-catalog`.

### 4. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

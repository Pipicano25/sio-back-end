# Usuarios y permisos en los ejercicios

[← Todos los ejercicios](README.md)

Este documento explica qué usuarios de prueba trae el realm de Keycloak (`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.

## Cómo funcionan los permisos

1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.
2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el **grupo** al que pertenece el usuario (el usuario no tiene roles propios).
3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, `all` vale como comodín en cualquier parte:
   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.
   - `perm:all:all:read` → solo `read`, pero en todos los servicios (en el realm vigente solo lo tiene `supervisores`; `reportes` y `consulta` tienen lecturas **explícitas** de todos los servicios, salvo los datos de contacto y representantes legales de Party Identity).
   - `perm:product-catalog:all:read` → solo `read`, solo en el catálogo.
4. Cada URL exige **un** permiso concreto (por ejemplo `perm:product-catalog:brands:create`). Si ninguno de los permisos del usuario lo cubre, el servicio responde `403 Forbidden` e indica cuál falta. Sin token, o con un token vencido, responde `401 Unauthorized`.
5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.

## Usuarios de prueba

Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).

| Usuario | Grupo | Permisos del grupo | En el catálogo puede |
| --- | --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` | Todo, incluido inactivar |
| `supervisor.test` | `supervisores` | `perm:all:all:read`<br>`perm:all:all:create`<br>`perm:all:all:update`<br>`perm:sales:sales:read-profitability` | Consultar, crear y modificar. **No** inactivar |
| `compras.test` | `compras` | 14 permisos explícitos; en el catálogo: `perm:purchase:all:all`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar |
| `ventas.test` | `ventas` | 17 permisos explícitos; en el catálogo: `perm:sales:all:create`<br>`perm:sales:all:read`<br>`perm:sales:all:update`<br>`perm:sales:all:delete`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar |
| `inventario.test` | `inventario` | 13 permisos explícitos; en el catálogo: `perm:geography:all:read`<br>`perm:product-catalog:all:read`<br>`perm:operational-context:all:read` | Solo consultar (y no puede consultar fabricantes en Party Identity) |
| `reportes.test` | `reportes` | 54 permisos explícitos; en el catálogo: `perm:product-catalog:attribute-definitions:read`<br>`perm:product-catalog:brands:read`<br>`perm:product-catalog:categories:read`<br>`perm:product-catalog:global_categories:read`<br>`perm:product-catalog:global_category_attributes:read`<br>`perm:product-catalog:global_product_attribute_values:read`<br>`perm:product-catalog:global_products:read`<br>`perm:product-catalog:global_units_of_measure:read`<br>`perm:product-catalog:group-types:read`<br>`perm:product-catalog:packaging-types:read`<br>`perm:product-catalog:product_assets:read`<br>`perm:product-catalog:product_attribute_definitions:read`<br>`perm:product-catalog:products:read`<br>`perm:product-catalog:units-of-measure:read` | Solo consultar |
| `consulta.test` | `consulta` | 54 permisos explícitos; en el catálogo: `perm:product-catalog:attribute-definitions:read`<br>`perm:product-catalog:brands:read`<br>`perm:product-catalog:categories:read`<br>`perm:product-catalog:global_categories:read`<br>`perm:product-catalog:global_category_attributes:read`<br>`perm:product-catalog:global_product_attribute_values:read`<br>`perm:product-catalog:global_products:read`<br>`perm:product-catalog:global_units_of_measure:read`<br>`perm:product-catalog:group-types:read`<br>`perm:product-catalog:packaging-types:read`<br>`perm:product-catalog:product_assets:read`<br>`perm:product-catalog:product_attribute_definitions:read`<br>`perm:product-catalog:products:read`<br>`perm:product-catalog:units-of-measure:read` | Solo consultar |

## Cómo obtener el token de cada usuario

Cambie `username` por el usuario que quiera probar:

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

En **PowerShell** (Windows), donde `curl` no es el curl real:

```powershell
$body = @{ grant_type = 'password'; client_id = 'sio-web'; scope = 'openid'
           username = 'consulta.test'; password = $env:KEYCLOAK_TEST_USER_PASSWORD }
$TOKEN = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8081/realms/sio/protocol/openid-connect/token' -Body $body).access_token
Invoke-RestMethod -Uri 'http://localhost:8003/api/v1/units-of-measure?code=UND' `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

En Postman: pestaña *Authorization* → tipo *OAuth 2.0* → *Password Credentials*, con la URL del token de arriba, cliente `sio-web` y el usuario y contraseña.

Luego envíe el token en cada llamada:

```http
Authorization: Bearer <TOKEN>
```

Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) obtiene el token de `<rol>.test`; sin argumento muestra un menú. Lee la contraseña de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.

## Permiso de cada URL de los ejercicios

✅ = puede · ❌ = recibe `403`. Columna *Ejercicios*: en cuáles se usa la URL.

| Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta | Ejercicios |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `GET /api/v1/packaging-types` | `perm:product-catalog:packaging-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `GET /api/v1/group-types` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `GET http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `POST http://localhost:8002/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/units-of-measure` | `perm:product-catalog:units-of-measure:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 4 |
| `POST /api/v1/brands` | `perm:product-catalog:brands:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 5 |
| `POST /api/v1/categories` | `perm:product-catalog:categories:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/attribute-definitions` | `perm:product-catalog:attribute-definitions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/attribute-definitions/{id}/options` | `perm:product-catalog:attribute-definitions:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 3, 5 |
| `POST /api/v1/categories/{id}/attributes` | `perm:product-catalog:categories:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/products` | `perm:product-catalog:products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/products/{id}/categories` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `GET /api/v1/products/{id}/applicable-attributes` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `GET /api/v1/products/{id}/completeness` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `PUT /api/v1/products/{id}/attribute-values/{id}` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/products/{id}/presentations` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `GET /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `POST /api/v1/group-types/{id}/groups` | `perm:product-catalog:group-types:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `POST /api/v1/products/{id}/group-assignments` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5 |
| `GET /api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 5 |
| `GET /api/v1/products/by-identifier/{codigo}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 4 |
| `GET /api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5 |
| `GET /api/v1/products/{id}/identifiers` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| `POST /api/v1/products/{id}/assets` | `perm:product-catalog:products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/products/{id}/deactivate` | `perm:product-catalog:products:deactivate` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |

## Permisos que no son obvios

- `perm:product-catalog:attribute-definitions:update`: Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.
- `perm:product-catalog:categories:update`: Asociar un atributo a una categoría modifica la categoría: exige `update`.
- `perm:product-catalog:group-types:create`: Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.
- `perm:product-catalog:products:update`: Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.
- `perm:product-catalog:products:deactivate`: Inactivar es una acción propia (`deactivate`): no la cubren `create` ni `update`.
- Las URL de `http://localhost:8002` son de **Party Identity** y las de `http://localhost:8000` de **Geography**: exigen permisos de esos servicios, no del catálogo.

## Qué usuario usar

| Para… | Usuario |
| --- | --- |
| Hacer los ejercicios completos | `admin.test` |
| Cargar productos sin poder inactivarlos | `supervisor.test` (falla en el paso de inactivar del ejercicio 5) |
| Verificar lo cargado (pasos de consulta y verificación) | `consulta.test` o `reportes.test` |
| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` al buscar fabricantes |

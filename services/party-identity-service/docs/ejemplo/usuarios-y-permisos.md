# Usuarios y permisos en los ejercicios

[← Todos los ejercicios](README.md)

Este documento explica qué usuarios de prueba trae el realm de Keycloak (`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.

## Cómo funcionan los permisos

1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.
2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el **grupo** al que pertenece el usuario.
3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, `all` vale como comodín en cualquier parte:
   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.
   - `perm:all:all:read` → solo `read`, pero en todos los servicios.
   - `perm:party-identity:all:read` → solo `read`, solo en Party Identity.
4. Cada URL exige **un** permiso concreto (por ejemplo `perm:party-identity:person_identities:create`). Si ninguno de los permisos del usuario lo cubre, el servicio responde `403 Forbidden` e indica cuál falta. Sin token, o con un token vencido, responde `401 Unauthorized`.
5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.

## Usuarios de prueba

Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).

| Usuario | Grupo | Permisos del grupo | En Party Identity puede |
| --- | --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` | Todo, incluido inactivar y retirar |
| `supervisor.test` | `supervisores` | `perm:all:all:read`<br>`perm:all:all:create`<br>`perm:all:all:update` | Consultar, crear, modificar y reactivar. **No** inactivar ni retirar |
| `compras.test` | `compras` | `perm:purchase:all:all`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar |
| `ventas.test` | `ventas` | `perm:sales:all:all`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar |
| `inventario.test` | `inventario` | `perm:geography:all:read`<br>`perm:product-catalog:all:read`<br>`perm:operational-context:all:read` | Nada: no tiene permisos sobre `party-identity` |
| `reportes.test` | `reportes` | `perm:all:all:read` | Solo consultar |
| `consulta.test` | `consulta` | `perm:all:all:read` | Solo consultar |

## Cómo obtener el token de cada usuario

Cambie `username` por el usuario que quiera probar:

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

En **PowerShell** (Windows):

```powershell
$body = @{ grant_type = 'password'; client_id = 'sio-web'; scope = 'openid'
           username = 'consulta.test'; password = $env:KEYCLOAK_TEST_USER_PASSWORD }
$TOKEN = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8081/realms/sio/protocol/openid-connect/token' -Body $body).access_token
Invoke-RestMethod -Uri 'http://localhost:8002/api/v1/person-identities' `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

Luego envíe el token en cada llamada:

```http
Authorization: Bearer <TOKEN>
```

Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) obtiene el token de `<rol>.test`. Lee la contraseña de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.

## Permiso de cada URL de los ejercicios

✅ = puede · ❌ = recibe `403`. Columna *Ejercicios*: en cuáles se usa la URL.

| Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta | Ejercicios |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3 |
| `GET /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1 |
| `POST /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `PUT /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `POST /api/v1/identification-type-rules/{id}/versions` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `GET /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1 |
| `POST /api/v1/identification-type-rules/{id}/deactivate` | `perm:party-identity:identification_type_rules:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `PUT /api/v1/person-identities/{id}` | `perm:party-identity:person_identities:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `POST /api/v1/person-identities/{id}/deactivate` | `perm:party-identity:person_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `GET /api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 2 |
| `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/organization-identities/{id}/deactivate` | `perm:party-identity:organization_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/organization-identities/{id}/reactivate` | `perm:party-identity:organization_identities:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `GET /api/v1/organization-identities/{id}` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 3 |

## Permisos que no son obvios

- `perm:party-identity:identification_type_rules:create`: Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.
- `perm:party-identity:identification_type_rules:delete`: Retirar una regla (`POST .../deactivate`) exige `delete`, aunque no la elimina: queda histórica.
- `perm:party-identity:person_identities:delete`: Inactivar (`POST .../deactivate`) exige `delete`, aunque no elimina; reactivar (`POST .../reactivate`) exige `update`.
- `perm:party-identity:organization_identities:delete`: Inactivar exige `delete`; reactivar exige `update`. Por eso `supervisor.test` puede reactivar pero no inactivar.
- Las URL de `http://localhost:8000` son de **Geography**: exigen permisos de ese servicio.

## Qué usuario usar

| Para… | Usuario |
| --- | --- |
| Hacer los ejercicios completos | `admin.test` |
| Crear y modificar sin poder inactivar ni retirar | `supervisor.test` |
| Verificar lo cargado | `consulta.test` o `reportes.test` |
| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` en cualquier llamada |

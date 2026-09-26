# Usuarios y permisos en los ejercicios

[← Todos los ejercicios](README.md)

Este documento explica qué usuarios de prueba trae el realm de Keycloak (`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.

## Cómo funcionan los permisos

1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.
2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el **grupo** al que pertenece el usuario.
3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, `all` vale como comodín en cualquier parte:
   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.
   - `perm:all:all:read` → solo `read`, pero en todos los servicios.
   - `perm:operational-context:all:read` → solo `read`, solo en Operational Context.
4. Cada URL exige un permiso concreto (por ejemplo `perm:operational-context:companies:create`); registrar, inactivar y reactivar empresas exigen además `perm:operational-context:platform:administer`. Si falta alguno, el servicio responde `403 Forbidden` e indica cuál. Sin token, o con un token vencido, responde `401 Unauthorized`.
5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.
6. **Aislamiento por empresa (Fase B):** el permiso dice *qué* puede hacer el usuario; la membresía dice *dónde*. Un usuario sin `platform:administer` solo ve y opera las empresas donde tiene una membresía `ACTIVE`; el resto responde `404`, igual que un `id` inexistente (URL marcadas con 🔒).

## Usuarios de prueba

Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).

| Usuario | Grupo | Permisos del grupo | En Operational Context puede |
| --- | --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` | Todo, en todas las empresas (alcance de plataforma) |
| `supervisor.test` | `supervisores` | `perm:all:all:read`<br>`perm:all:all:create`<br>`perm:all:all:update` | En sus empresas: consultar, crear, modificar y reactivar sucursales, usuarios y asignaciones. **No** inactivar ni registrar, inactivar o reactivar empresas |
| `compras.test` | `compras` | `perm:purchase:all:all`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar, en sus empresas |
| `ventas.test` | `ventas` | `perm:sales:all:all`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:all:read`<br>`perm:commercial-relationship:all:read`<br>`perm:operational-context:all:read` | Solo consultar, en sus empresas |
| `inventario.test` | `inventario` | `perm:geography:all:read`<br>`perm:product-catalog:all:read`<br>`perm:operational-context:all:read` | Solo consultar, en sus empresas |
| `reportes.test` | `reportes` | `perm:all:all:read` | Solo consultar, en sus empresas |
| `consulta.test` | `consulta` | `perm:all:all:read` | Solo consultar, en sus empresas |

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
Invoke-RestMethod -Uri 'http://localhost:8004/api/v1/companies' `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

Luego envíe el token en cada llamada:

```http
Authorization: Bearer <TOKEN>
```

Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) obtiene el token de `<rol>.test`. Lee la contraseña de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.

## Permiso de cada URL de los ejercicios

✅ = tiene el permiso · ❌ = recibe `403`. 🔒 = además exige membresía en la empresa (si no, `404`). Columna *Ejercicios*: en cuáles se usa la URL.

| Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta | Ejercicios |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1, 2, 3, 4, 5, 6 |
| `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2 |
| `GET http://localhost:8000/global-administrative-divisions` | `perm:geography:global_administrative_divisions:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2 |
| `GET http://localhost:8000/global-cities` | `perm:geography:global_cities:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2 |
| `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 2, 3, 4, 5, 6 |
| `GET /api/v1/companies/{id}` 🔒 | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `PUT /api/v1/companies/{id}` 🔒 | `perm:operational-context:companies:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `GET /api/v1/companies` 🔒 | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `POST /api/v1/companies/{id}/branches` 🔒 | `perm:operational-context:branches:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2, 3, 5 |
| `GET /api/v1/companies/{id}/branches` 🔒 | `perm:operational-context:branches:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 2 |
| `PUT /api/v1/branches/{id}` 🔒 | `perm:operational-context:branches:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `GET /api/v1/branches/{id}` 🔒 | `perm:operational-context:branches:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 2, 3 |
| `POST /api/v1/companies/{id}/deactivate` 🔒 | `perm:operational-context:companies:delete` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/companies/{id}/reactivate` 🔒 | `perm:operational-context:companies:update` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 4, 5, 6 |
| `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 4, 5 |
| `GET /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4 |
| `GET /api/v1/application-users/{id}` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4 |
| `POST /api/v1/application-users/{id}/deactivate` 🔒 | `perm:operational-context:application_users:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 4 |
| `POST /api/v1/application-users/{id}/reactivate` 🔒 | `perm:operational-context:application_users:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 4 |
| `POST /api/v1/application-users/{id}/user-branches` 🔒 | `perm:operational-context:user_branches:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `GET /api/v1/application-users/{id}/user-branches` 🔒 | `perm:operational-context:user_branches:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| `GET /api/v1/operational-access` | `perm:operational-context:application_users:read` + `perm:operational-context:platform:lookup` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/user-branches/{id}/deactivate` 🔒 | `perm:operational-context:user_branches:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/branches/{id}/deactivate` 🔒 | `perm:operational-context:branches:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/companies/{id}/advisor-assignments/change-primary` 🔒 | `perm:operational-context:company_advisor_assignments:create` + `perm:operational-context:company_advisor_assignments:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `GET /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 6 |
| `POST /api/v1/advisor-assignments/{id}/close` 🔒 | `perm:operational-context:company_advisor_assignments:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |

## Permisos que no son obvios

- `perm:operational-context:companies:delete`: Inactivar una empresa (`POST .../deactivate`) exige `delete`, aunque no la elimina; reactivar (`POST .../reactivate`) exige `update`. Desde la Fase B ambas exigen además `perm:operational-context:platform:administer`: `supervisor.test` no puede ninguna de las dos.
- `perm:operational-context:platform:administer`: Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.
- `perm:operational-context:platform:lookup`: Consulta técnica entre servicios (Fase B, FR-045): leer por UUID sin membresía y comprobar el acceso de otro usuario. Es para identidades técnicas; ningún grupo de usuarios la tiene salvo `administradores` (por `perm:all:all:all`).
- `perm:operational-context:application_users:create`: Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- `perm:operational-context:branches:delete`: Inactivar una sucursal exige `delete`; reactivarla exige `update`.
- `perm:operational-context:companies:create`: Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- `perm:operational-context:branches:read`: Las rutas de sucursales exigen solo permisos de `branches`, aunque la colección y el alta estén bajo `/api/v1/companies/{id}/branches`.
- Las URL de `http://localhost:8000` son de **Geography** y las de `http://localhost:8002` de **Party Identity**: exigen permisos de esos servicios.

## Qué usuario usar

| Para… | Usuario |
| --- | --- |
| Hacer los ejercicios completos | `admin.test` |
| Crear y modificar sin poder inactivar, dentro de sus empresas | `supervisor.test` (con membresía) |
| Verificar lo cargado | `consulta.test` o `reportes.test` (con membresía en la empresa) |
| Probar rechazos por falta de permiso | `consulta.test` o `inventario.test` en cualquier `POST` o `PUT`; `supervisor.test` al inactivar |

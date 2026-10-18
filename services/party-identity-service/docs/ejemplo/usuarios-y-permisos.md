# Usuarios y permisos en los ejercicios

[← Todos los ejercicios](README.md)

Este documento explica qué usuarios de prueba trae el realm de Keycloak (`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.

## Cómo funcionan los permisos

1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.
2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el **grupo** al que pertenece el usuario.
3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, `all` vale como comodín en cualquier parte:
   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.
   - `perm:all:all:read` → solo `read`, pero en todos los servicios (en el realm vigente solo lo tiene `supervisores`).
   - `perm:party-identity:all:read` → solo `read`, solo en Party Identity (ya no lo tiene ningún grupo de solo lectura).
   - Mínimo privilegio (Q-C1): los perfiles de contacto, las personas de contacto y los representantes legales exigen su **permiso específico**. `compras` y `ventas` tienen lecturas explícitas de Party Identity que incluyen contactos pero **no** representantes legales; `reportes` y `consulta` tienen lecturas explícitas de todos los servicios **sin** esos cuatro recursos. Leer una persona u organización no da acceso a sus contactos.
4. Cada URL exige **un** permiso concreto (por ejemplo `perm:party-identity:person_identities:create`). Si ninguno de los permisos del usuario lo cubre, el servicio responde `403 Forbidden` e indica cuál falta. Sin token, o con un token vencido, responde `401 Unauthorized`.
5. El permiso se revisa **antes** que el cuerpo: un usuario sin permiso recibe `403` aunque el JSON esté mal.

## Usuarios de prueba

Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).

| Usuario | Grupo | Permisos del grupo | En Party Identity puede |
| --- | --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` | Todo, incluido inactivar, retirar y cerrar |
| `supervisor.test` | `supervisores` | `perm:all:all:read`<br>`perm:all:all:create`<br>`perm:all:all:update`<br>`perm:sales:sales:read-profitability`<br>`perm:commercial-relationship:pricing_policies:delete`<br>`perm:commercial-relationship:automatic_price_applications:resolve`<br>`perm:purchase:purchase_line_taxes:override` | Consultar, crear, modificar y reactivar. **No** inactivar, retirar ni cerrar |
| `compras.test` | `compras` | 46 permisos explícitos; en Party Identity: `perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:person_identities:read`<br>`perm:party-identity:organization_identities:read`<br>`perm:party-identity:person_contact_profiles:read`<br>`perm:party-identity:organization_contact_profiles:read`<br>`perm:party-identity:organization_contact_persons:read`<br>`perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:organization_business_sectors:read`<br>`perm:operational-context:all:read` | Consultar identidades, contactos y sectores. **No** representantes legales |
| `ventas.test` | `ventas` | 33 permisos explícitos; en Party Identity: `perm:sales:all:create`<br>`perm:sales:all:read`<br>`perm:sales:all:update`<br>`perm:sales:all:delete`<br>`perm:geography:all:read`<br>`perm:payment-reference:all:read`<br>`perm:product-catalog:all:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:person_identities:read`<br>`perm:party-identity:organization_identities:read`<br>`perm:party-identity:person_contact_profiles:read`<br>`perm:party-identity:organization_contact_profiles:read`<br>`perm:party-identity:organization_contact_persons:read`<br>`perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:organization_business_sectors:read`<br>`perm:operational-context:all:read` | Consultar identidades, contactos y sectores. **No** representantes legales |
| `inventario.test` | `inventario` | 18 permisos explícitos; en Party Identity: `perm:geography:all:read`<br>`perm:product-catalog:all:read`<br>`perm:operational-context:all:read` | Nada: no tiene permisos sobre `party-identity` |
| `reportes.test` | `reportes` | 54 permisos explícitos; en Party Identity: `perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:organization_business_sectors:read`<br>`perm:party-identity:organization_identities:read`<br>`perm:party-identity:person_identities:read` | Consultar identidades, reglas y sectores. **No** contactos ni representantes legales |
| `consulta.test` | `consulta` | 54 permisos explícitos; en Party Identity: `perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:organization_business_sectors:read`<br>`perm:party-identity:organization_identities:read`<br>`perm:party-identity:person_identities:read` | Consultar identidades, reglas y sectores. **No** contactos ni representantes legales |

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
| `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5, 6, 7, 8 |
| `GET /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1 |
| `POST /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `PUT /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `POST /api/v1/identification-type-rules/{id}/versions` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `GET /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 1 |
| `POST /api/v1/identification-type-rules/{id}/deactivate` | `perm:party-identity:identification_type_rules:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2, 5, 6, 8 |
| `PUT /api/v1/person-identities/{id}` | `perm:party-identity:person_identities:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `POST /api/v1/person-identities/{id}/deactivate` | `perm:party-identity:person_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 2, 5 |
| `GET /api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 2 |
| `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3, 4, 6, 7, 8 |
| `POST /api/v1/organization-identities/{id}/deactivate` | `perm:party-identity:organization_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/organization-identities/{id}/reactivate` | `perm:party-identity:organization_identities:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `GET /api/v1/organization-identities/{id}` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 3 |
| `GET http://localhost:8000/global-cities` | `perm:geography:global_cities:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4 |
| `GET http://localhost:8004/api/v1/companies` | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4, 5 |
| `POST /api/v1/organization-identities/{id}/contact-profile` | `perm:party-identity:organization_contact_profiles:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 4 |
| `GET /api/v1/organization-identities/{id}/contact-profile` | `perm:party-identity:organization_contact_profiles:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 4 |
| `GET /api/v1/organization-identities/{id}/contact-profile/versions` | `perm:party-identity:organization_contact_profiles:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 4 |
| `POST /api/v1/organization-identities/{id}/contact-profile:close` | `perm:party-identity:organization_contact_profiles:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 4 |
| `POST /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `GET /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/organization-contact-persons/{id}:set-primary` | `perm:party-identity:organization_contact_persons:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `GET /api/v1/organization-contact-persons/{id}` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/organization-contact-persons/{id}:deactivate` | `perm:party-identity:organization_contact_persons:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `GET /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 6 |
| `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7 |
| `GET /api/v1/global-business-sectors/{id}` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7 |
| `POST /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `PUT /api/v1/global-business-sectors/{id}` | `perm:party-identity:global_business_sectors:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `POST /api/v1/global-business-sectors/{id}:deactivate` | `perm:party-identity:global_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `POST /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `POST /api/v1/organization-business-sectors/{id}:set-primary` | `perm:party-identity:organization_business_sectors:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `POST /api/v1/organization-business-sectors/{id}:close` | `perm:party-identity:organization_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 7 |
| `GET /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7 |
| `POST /api/v1/organization-identities/{id}/legal-representatives:set-primary` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 8 |
| `POST /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 8 |
| `POST /api/v1/organization-legal-representatives/{id}:close` | `perm:party-identity:organization_legal_representatives:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 8 |
| `GET /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 8 |

## Permisos que no son obvios

- `perm:party-identity:identification_type_rules:create`: Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.
- `perm:party-identity:identification_type_rules:delete`: Retirar una regla (`POST .../deactivate`) exige `delete`, aunque no la elimina: queda histórica.
- `perm:party-identity:person_identities:delete`: Inactivar (`POST .../deactivate`) exige `delete`, aunque no elimina; reactivar (`POST .../reactivate`) exige `update`.
- `perm:party-identity:organization_identities:delete`: Inactivar exige `delete`; reactivar exige `update`. Por eso `supervisor.test` puede reactivar pero no inactivar.
- `perm:party-identity:organization_contact_profiles:create`: Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.
- `perm:party-identity:person_contact_profiles:create`: Igual que en organizaciones: se exige membresía `ACTIVE` en la empresa desde la que se confirma, sin permisos de Operational Context.
- `perm:party-identity:organization_contact_profiles:delete`: Cerrar el perfil (`POST .../contact-profile:close`) exige `delete`, aunque no elimina: la versión queda en el historial.
- `perm:party-identity:person_contact_profiles:delete`: Cerrar el perfil exige `delete`; no elimina.
- `perm:party-identity:organization_contact_persons:update`: `:set-primary` y `:reactivate` exigen `update`; `is_primary` no se cambia con `PUT`.
- `perm:party-identity:organization_legal_representatives:read`: Dato sensible: solo lo leen los grupos con necesidad explícita (`administradores`, `supervisores`); `compras`, `ventas`, `reportes` y `consulta` reciben `403`.
- `perm:party-identity:organization_legal_representatives:create`: `:set-primary` también exige `create`: crea el primer `PRIMARY` o sustituye el vigente cerrándolo.
- Las URL de `http://localhost:8000` son de **Geography** y las de `http://localhost:8004` de **Operational Context**: exigen permisos de esos servicios. Confirmar un perfil de contacto **no** exige permisos de Operational Context: la membresía la comprueba Party Identity con su cliente técnico.

## Qué usuario usar

| Para… | Usuario |
| --- | --- |
| Hacer los ejercicios completos | `admin.test` |
| Crear y modificar sin poder inactivar ni retirar | `supervisor.test` |
| Verificar lo cargado (sin datos de contacto) | `consulta.test` o `reportes.test` |
| Consultar contactos de clientes o proveedores | `compras.test` o `ventas.test` |
| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` en cualquier llamada |

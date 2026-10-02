# Usuarios y permisos — Ejercicio 4 — Usuarios operativos de una empresa

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`. Sí puede hacer las consultas (`GET`) de los pasos 04, 05.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04, 05.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 04, 05 responden `404` (aislamiento por empresa).
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la persona de la supervisora (ficticia) en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 04, 05 responden `404` (aislamiento por empresa).
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 04, 05 responden `404` (aislamiento por empresa).
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 04, 05 responden `404` (aislamiento por empresa).

**Para hacer el ejercicio completo use `admin.test`** (tiene `platform:administer` por `perm:all:all:all`). Los demás usuarios solo operan en las empresas donde tienen membresía `ACTIVE`; `supervisor.test` puede crear y modificar allí, pero no inactivar ni registrar, inactivar o reactivar empresas.

## Permiso por URL

✅ = el usuario tiene el permiso (o los permisos) de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: fuera de sus empresas el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-personas.md) | 1. Consultar la persona de la supervisora (ficticia) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-personas.md) | 2. Consultar la persona del comprador (ficticio) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 1. Consultar la organización COMERCIALIZADORA USUARIOS FICTICIA S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 2. Consultar la organización ALIADO USUARIOS FICTICIO S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 3. Registrar la empresa A | `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-registrar-empresas.md) | 4. Registrar la empresa B | `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-usuarios.md) | 1. Registrar a supervisor.test por nombre de usuario | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-usuarios.md) | 2. Intentar registrarla otra vez (rechazado) | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-usuarios.md) | 3. Intentar registrar una cuenta técnica (rechazado) | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-usuarios.md) | 4. Registrar a compras.test | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-consultar-usuarios.md) | 1. Listar los usuarios activos de la empresa A | `GET /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [04](04-consultar-usuarios.md) | 2. Consultar la supervisora por su `id` | `GET /api/v1/application-users/{id}` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-misma-persona-otra-empresa.md) | 1. Registrar a compras.test en la empresa B | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-misma-persona-otra-empresa.md) | 2. Inactivar la membresía de la empresa B | `POST /api/v1/application-users/{id}/deactivate` 🔒 | `perm:operational-context:application_users:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-misma-persona-otra-empresa.md) | 3. Consultar la membresía de la empresa A | `GET /api/v1/application-users/{id}` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-misma-persona-otra-empresa.md) | 4. Reactivar la membresía de la empresa B | `POST /api/v1/application-users/{id}/reactivate` 🔒 | `perm:operational-context:application_users:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar las dos empresas*):

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_A>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Registrar las dos empresas*), llamada 3:

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_A>"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:operational-context:companies:create",
  "instance": "/api/v1/companies",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene lecturas explícitas (sin `create`, `update` ni `delete`): puede **leer**, pero la URL exige `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA_A>/application-users" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `404 Not Found`: `perm:operational-context:application_users:read` cubre `perm:operational-context:application_users:read`, pero `consulta.test` **no es miembro** de la empresa del paso 04. Fuera de su alcance, el recurso se trata como inexistente (aislamiento por empresa, DS-06).

### 4. `inventario.test` consulta

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA_A>/application-users" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Responde `404 Not Found`: `inventario.test` tiene `perm:operational-context:all:read`, pero no es miembro de la empresa. Tener el permiso no basta: también se necesita la membresía.

### 5. `supervisor.test` intenta inactivar (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8004/api/v1/application-users/<USR_COMPRADOR_B>/deactivate" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:operational-context:application_users:delete",
  "instance": "/api/v1/application-users/{id}/deactivate",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

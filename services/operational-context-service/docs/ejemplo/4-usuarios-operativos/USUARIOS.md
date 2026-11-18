# Usuarios y permisos — Ejercicio 4 — Usuarios operativos de una empresa

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.sio`**: puede ejecutar **todo el ejercicio**.
- **`admin.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `administer`. Sí puede hacer las consultas (`GET`) de los pasos 04, 05.
- **`operario.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa A*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04, 05.

**Para hacer el ejercicio completo use `admin.sio`** (tiene `platform:administer` por `perm:all:all:all`). Los demás usuarios solo operan en las empresas donde tienen membresía `ACTIVE`; `admin.dao` (grupo `admin`) puede crear, modificar e inactivar allí, pero no registrar, inactivar o reactivar empresas; los usuarios del grupo `empleado` solo consultan.

## Permiso por URL

✅ = el usuario tiene el permiso (o los permisos) de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: fuera de sus empresas el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin.sio | admin.dao | operario.dao |
| --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-personas.md) | 1. Consultar la persona de la supervisora (ficticia) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-personas.md) | 2. Consultar la persona del comprador (ficticio) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 1. Consultar la organización COMERCIALIZADORA USUARIOS FICTICIA S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 2. Consultar la organización ALIADO USUARIOS FICTICIO S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-empresas.md) | 3. Registrar la empresa A | `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ |
| [02](02-registrar-empresas.md) | 4. Registrar la empresa B | `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ |
| [03](03-registrar-usuarios.md) | 1. Registrar a admin.dao por nombre de usuario | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ |
| [03](03-registrar-usuarios.md) | 2. Intentar registrarla otra vez (rechazado) | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ |
| [03](03-registrar-usuarios.md) | 3. Intentar registrar una cuenta técnica (rechazado) | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ |
| [03](03-registrar-usuarios.md) | 4. Registrar a operario.dao | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ |
| [04](04-consultar-usuarios.md) | 1. Listar los usuarios activos de la empresa A | `GET /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ |
| [04](04-consultar-usuarios.md) | 2. Consultar la supervisora por su `id` | `GET /api/v1/application-users/{id}` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ |
| [05](05-misma-persona-otra-empresa.md) | 1. Registrar a operario.dao en la empresa B | `POST /api/v1/companies/{id}/application-users` 🔒 | `perm:operational-context:application_users:create` | ✅ | ✅ | ❌ |
| [05](05-misma-persona-otra-empresa.md) | 2. Inactivar la membresía de la empresa B | `POST /api/v1/application-users/{id}/deactivate` 🔒 | `perm:operational-context:application_users:delete` | ✅ | ✅ | ❌ |
| [05](05-misma-persona-otra-empresa.md) | 3. Consultar la membresía de la empresa A | `GET /api/v1/application-users/{id}` 🔒 | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ |
| [05](05-misma-persona-otra-empresa.md) | 4. Reactivar la membresía de la empresa B | `POST /api/v1/application-users/{id}/reactivate` 🔒 | `perm:operational-context:application_users:update` | ✅ | ✅ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.sio`

```bash
TOKEN_ADMIN_SIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.sio -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar las dos empresas*):

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_ADMIN_SIO" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_A>"}'
```

Responde `201 Created`: `admin.sio` tiene `perm:all:all:all`, que cubre `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `operario.dao` (Empleado) intenta crear o modificar (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Registrar las dos empresas*), llamada 3:

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_A>"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

El grupo `empleado` solo tiene `perm:operational-context:all:read` en este servicio: puede **leer**, pero la URL exige `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `operario.dao` (Empleado) consulta

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA_A>/application-users" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.sio` en el paso 04: `perm:operational-context:all:read` cubre `perm:operational-context:application_users:read` y `operario.dao` es miembro de la empresa.

### 4. `admin.dao` (Admin) intenta una acción de plataforma (rechazado)

```bash
TOKEN_ADMIN_DAO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_ADMIN_DAO" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_A>"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

El grupo `admin` tiene `create`, `read`, `update` y `delete` de Operational Context, pero **no** `perm:operational-context:platform:administer`. Registrar, inactivar y reactivar empresas queda para `admin.sio` (grupo `superadmin`).

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

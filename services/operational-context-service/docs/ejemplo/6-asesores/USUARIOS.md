# Usuarios y permisos — Ejercicio 6 — Asesores de la empresa

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa*): sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `administer`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 05 responden `404` (aislamiento por empresa).
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 05 responden `404` (aislamiento por empresa).
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 05 responden `404` (aislamiento por empresa).
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la empresa*): sobre `operational-context` solo tiene `read`; le falta `create`. Con permiso de lectura pero **sin membresía** en la empresa, sus consultas de los pasos 05 responden `404` (aislamiento por empresa).

**Para hacer el ejercicio completo use `admin.test`** (tiene `platform:administer` por `perm:all:all:all`). Los demás usuarios solo operan en las empresas donde tienen membresía `ACTIVE`; `supervisor.test` (grupo `admin`) puede crear, modificar e inactivar allí, pero no registrar, inactivar o reactivar empresas; los usuarios del grupo `empleado` solo consultan.

## Permiso por URL

✅ = el usuario tiene el permiso (o los permisos) de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: fuera de sus empresas el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos.md) | 1. Consultar la organización ASESORADA EJEMPLO FICTICIA S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 2. Consultar la persona del primer asesor (ficticio) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 3. Consultar la persona del nuevo asesor (ficticio) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 4. Consultar la persona del asesor no principal (ficticio) en Party Identity Service | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-empresa.md) | 1. Registrar la empresa | `POST /api/v1/companies` | `perm:operational-context:companies:create` + `perm:operational-context:platform:administer` | ✅ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-asesores.md) | 1. Registrar el asesor principal | `POST /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:create` | ✅ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-asesores.md) | 2. Intentar un segundo asesor principal (rechazado) | `POST /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:create` | ✅ | ✅ | ❌ | ❌ | ❌ |
| [03](03-registrar-asesores.md) | 3. Registrar un asesor no principal | `POST /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:create` | ✅ | ✅ | ❌ | ❌ | ❌ |
| [04](04-cambiar-asesor-principal.md) | 1. Cambiar el asesor principal | `POST /api/v1/companies/{id}/advisor-assignments/change-primary` 🔒 | `perm:operational-context:company_advisor_assignments:create` + `perm:operational-context:company_advisor_assignments:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| [05](05-historial-y-cierre.md) | 1. Consultar el historial de asesores | `GET /api/v1/companies/{id}/advisor-assignments` 🔒 | `perm:operational-context:company_advisor_assignments:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-historial-y-cierre.md) | 2. Cerrar la asignación del asesor no principal | `POST /api/v1/advisor-assignments/{id}/close` 🔒 | `perm:operational-context:company_advisor_assignments:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| [05](05-historial-y-cierre.md) | 3. Intentar cerrarla otra vez (rechazado) | `POST /api/v1/advisor-assignments/{id}/close` 🔒 | `perm:operational-context:company_advisor_assignments:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la empresa*):

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_EMPRESA>"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `ventas.test` (Empleado) intenta crear o modificar (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=ventas.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Registrar la empresa*), llamada 1:

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_EMPRESA>"}'
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

### 3. `ventas.test` (Empleado) consulta

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA>/advisor-assignments" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `404 Not Found`: `perm:operational-context:all:read` cubre `perm:operational-context:company_advisor_assignments:read`, pero `ventas.test` **no es miembro** de la empresa del paso 05. Fuera de su alcance, el recurso se trata como inexistente (aislamiento por empresa, DS-06). Tener el permiso no basta: también se necesita la membresía.

### 4. `supervisor.test` (Admin) intenta una acción de plataforma (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_EMPRESA>"}'
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

El grupo `admin` tiene `create`, `read`, `update` y `delete` de Operational Context, pero **no** `perm:operational-context:platform:administer`. Registrar, inactivar y reactivar empresas queda para `admin.test` (grupo `superadmin`).

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

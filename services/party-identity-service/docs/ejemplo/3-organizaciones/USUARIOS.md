# Usuarios y permisos — Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la organización*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 03.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la organización*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 03.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la organización*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 03.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la organización*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 03.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-pais.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-organizacion.md) | 1. Registrar la organización con NIT | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-organizacion.md) | 2. Intentar registrar un NIT sin dígito de verificación (rechazado) | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-organizacion.md) | 3. Intentar registrar con un país inexistente (rechazado) | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [03](03-inactivar-y-reactivar.md) | 1. Inactivar la organización | `POST /api/v1/organization-identities/{id}/deactivate` | `perm:party-identity:organization_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ |
| [03](03-inactivar-y-reactivar.md) | 2. Intentar inactivarla otra vez (rechazado) | `POST /api/v1/organization-identities/{id}/deactivate` | `perm:party-identity:organization_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ |
| [03](03-inactivar-y-reactivar.md) | 3. Reactivar la organización | `POST /api/v1/organization-identities/{id}/reactivate` | `perm:party-identity:organization_identities:update` | ✅ | ✅ | ✅ | ✅ | ✅ |
| [03](03-inactivar-y-reactivar.md) | 4. Consultar la organización por `id` | `GET /api/v1/organization-identities/{id}` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la organización*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"country_id": "<PAIS_CO>", "identification_type": "NIT", "identification_number": "900000001-1", "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.", "trade_name": "EJEMPLO FICTICIO", "organization_type": "SAS", "registration_status": "ACTIVA"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:party-identity:organization_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `ventas.test` (Empleado) intenta una acción reservada (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=ventas.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 03 (*Inactivar y reactivar*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities/<ORG_EJEMPLO>/deactivate" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/organization-identities/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`ventas.test` sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`: el grupo `empleado` crea, consulta y modifica personas, organizaciones y sus contactos, pero la URL exige `perm:party-identity:organization_identities:delete`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `ventas.test` (Empleado) consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/organization-identities/<ORG_EJEMPLO>" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 03: `perm:party-identity:organization_identities:read` cubre `perm:party-identity:organization_identities:read`. También pueden: `supervisor.test`, `compras.test`, `inventario.test`.

### 4. `supervisor.test` intenta inactivar o retirar (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities/<ORG_EJEMPLO>/deactivate" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/organization-identities/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` (grupo `admin`) tiene `perm:party-identity:all:read`, `:all:create` y `:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.test` (grupo `superadmin`). El grupo `empleado` tampoco puede.

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

# Usuarios y permisos — Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.sio`**: puede ejecutar **todo el ejercicio**.
- **`admin.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 04 (*Cerrar la relación de suplente*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`operario.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Establecer el primer PRIMARY*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.

**Para hacer el ejercicio completo use `admin.sio`.** `admin.dao` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin.sio | admin.dao | operario.dao |
| --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-pais.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 1. Registrar la organización | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 2. Registrar la primera persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 3. Registrar la segunda persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ✅ |
| [03](03-establecer-primary.md) | 1. Establecer el primer PRIMARY | `POST /api/v1/organization-identities/{id}/legal-representatives:set-primary` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ |
| [03](03-establecer-primary.md) | 2. Intentar registrar otro PRIMARY por el alta ordinaria (rechazado) | `POST /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ |
| [03](03-establecer-primary.md) | 3. Sustituir el PRIMARY | `POST /api/v1/organization-identities/{id}/legal-representatives:set-primary` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ |
| [04](04-suplente-y-cierre.md) | 1. Registrar a JORGE como suplente | `POST /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ |
| [04](04-suplente-y-cierre.md) | 2. Cerrar la relación de suplente | `POST /api/v1/organization-legal-representatives/{id}:close` | `perm:party-identity:organization_legal_representatives:delete` | ✅ | ❌ | ❌ |
| [04](04-suplente-y-cierre.md) | 3. Consultar el historial | `GET /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:read` | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.sio`

```bash
TOKEN_ADMIN_SIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.sio -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la organización y las personas*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN_SIO" \
  -H "Content-Type: application/json" \
  -d '{"country_id": "<PAIS_CO>", "identification_type": "NIT", "identification_number": "900000008-8", "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S."}'
```

Responde `201 Created`: `admin.sio` tiene `perm:all:all:all`, que cubre `perm:party-identity:organization_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `operario.dao` (Empleado) intenta una acción reservada (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 03 (*Establecer y sustituir el PRIMARY*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities/<ORG_INV>/legal-representatives:set-primary" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"person_identity_id": "<PERSONA_JORGE>", "position": "Gerente general"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/organization-identities/{id}/legal-representatives:set-primary",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`operario.dao` sobre `party-identity` solo tiene `read`; le falta `create`: el operario (`Compras`, `Ventas` e `Inventario`) crea, consulta y modifica personas, organizaciones y sus contactos, pero la URL exige `perm:party-identity:organization_legal_representatives:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `operario.dao` (Empleado) consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/organization-identities/<ORG_INV>/legal-representatives?state=all" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.sio` en el paso 04: `perm:party-identity:organization_legal_representatives:read` cubre `perm:party-identity:organization_legal_representatives:read`. También pueden: `admin.dao`.

### 4. `admin.dao` intenta inactivar o retirar (rechazado)

```bash
TOKEN_ADMIN_DAO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-legal-representatives/<REP_JORGE_SUPLENTE>:close" \
  -H "Authorization: Bearer $TOKEN_ADMIN_DAO" \
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
  "instance": "/api/v1/organization-legal-representatives/{id}:close",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`admin.dao` (grupo `admin`) tiene `perm:party-identity:all:read`, `:all:create` y `:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.sio` (grupo `superadmin`). Ninguna de las áreas (`Compras`, `Ventas` e `Inventario`) puede.

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

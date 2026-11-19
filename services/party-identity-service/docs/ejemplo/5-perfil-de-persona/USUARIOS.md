# Usuarios y permisos — Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.sio`**: puede ejecutar **todo el ejercicio**.
- **`admin.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la persona*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 02, 03.
- **`operario.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la persona*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 02, 03.

**Para hacer el ejercicio completo use `admin.sio`.** `admin.dao` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin.sio | admin.dao | operario.dao |
| --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-referencias.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ |
| [01](01-consultar-referencias.md) | 2. Consultar la empresa desde la que se confirma en Operational Context | `GET http://localhost:8004/api/v1/companies` | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-persona-y-perfil.md) | 1. Registrar la persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ✅ |
| [02](02-registrar-persona-y-perfil.md) | 2. Registrar el perfil de contacto | `POST /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:create` | ✅ | ✅ | ✅ |
| [02](02-registrar-persona-y-perfil.md) | 3. Consultar el perfil vigente | `GET /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` | ✅ | ✅ | ✅ |
| [03](03-inactivar-persona.md) | 1. Inactivar la persona | `POST /api/v1/person-identities/{id}/deactivate` | `perm:party-identity:person_identities:delete` | ✅ | ❌ | ❌ |
| [03](03-inactivar-persona.md) | 2. Intentar una versión nueva del perfil (rechazado) | `POST /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:create` | ✅ | ✅ | ✅ |
| [03](03-inactivar-persona.md) | 3. Consultar el perfil (sigue vigente) | `GET /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.sio`

```bash
TOKEN_ADMIN_SIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.sio -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la persona y su perfil*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN_SIO" \
  -H "Content-Type: application/json" \
  -d '{"identification_country_id": "<PAIS_CO>", "identification_type": "CC", "identification_number": "1000000005", "first_name": "LUIS", "last_name": "CLIENTE", "second_last_name": "FICTICIO", "birth_date": "1985-03-20"}'
```

Responde `201 Created`: `admin.sio` tiene `perm:all:all:all`, que cubre `perm:party-identity:person_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `operario.dao` (Empleado) intenta una acción reservada (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 03 (*Inactivar la persona*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/deactivate" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/person-identities/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`operario.dao` sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`: el operario (`Compras`, `Ventas` e `Inventario`) crea, consulta y modifica personas, organizaciones y sus contactos, pero la URL exige `perm:party-identity:person_identities:delete`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `operario.dao` (Empleado) consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.sio` en el paso 02: `perm:party-identity:person_contact_profiles:read` cubre `perm:party-identity:person_contact_profiles:read`. También pueden: `admin.dao`.

### 4. `admin.dao` intenta inactivar o retirar (rechazado)

```bash
TOKEN_ADMIN_DAO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/deactivate" \
  -H "Authorization: Bearer $TOKEN_ADMIN_DAO"
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/person-identities/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`admin.dao` (grupo `admin`) tiene `perm:party-identity:all:read`, `:all:create` y `:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.sio` (grupo `superadmin`). Ninguna de las áreas (`Compras`, `Ventas` e `Inventario`) puede.

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

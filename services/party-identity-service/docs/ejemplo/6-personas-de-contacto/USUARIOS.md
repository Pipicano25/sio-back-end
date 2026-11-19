# Usuarios y permisos — Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.sio`**: puede ejecutar **todo el ejercicio**.
- **`admin.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 04 (*Inactivar el contacto de cartera*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`operario.dao`**: **no puede completar el ejercicio**. Se detiene en el paso 04 (*Inactivar el contacto de cartera*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.

**Para hacer el ejercicio completo use `admin.sio`.** `admin.dao` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin.sio | admin.dao | operario.dao |
| --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-pais.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 1. Registrar la organización | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 2. Registrar la persona de contacto | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ✅ |
| [03](03-registrar-contactos.md) | 1. Registrar el contacto comercial como principal | `POST /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:create` | ✅ | ✅ | ✅ |
| [03](03-registrar-contactos.md) | 2. Registrar el contacto de cartera | `POST /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:create` | ✅ | ✅ | ✅ |
| [03](03-registrar-contactos.md) | 3. Intentar crear un segundo principal (rechazado) | `POST /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:create` | ✅ | ✅ | ✅ |
| [04](04-set-primary-e-inactivar.md) | 1. Establecer el contacto de cartera como principal | `POST /api/v1/organization-contact-persons/{id}:set-primary` | `perm:party-identity:organization_contact_persons:update` | ✅ | ✅ | ✅ |
| [04](04-set-primary-e-inactivar.md) | 2. Consultar el contacto comercial por `id` (contrato Provider) | `GET /api/v1/organization-contact-persons/{id}` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ |
| [04](04-set-primary-e-inactivar.md) | 3. Inactivar el contacto de cartera | `POST /api/v1/organization-contact-persons/{id}:deactivate` | `perm:party-identity:organization_contact_persons:delete` | ✅ | ❌ | ❌ |
| [04](04-set-primary-e-inactivar.md) | 4. Listar los contactos vigentes | `GET /api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.sio`

```bash
TOKEN_ADMIN_SIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.sio -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la organización y la persona*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN_SIO" \
  -H "Content-Type: application/json" \
  -d '{"country_id": "<PAIS_CO>", "identification_type": "NIT", "identification_number": "900000006-9", "legal_name": "LABORATORIO CONTACTOS FICTICIO S.A.S."}'
```

Responde `201 Created`: `admin.sio` tiene `perm:all:all:all`, que cubre `perm:party-identity:organization_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `operario.dao` (Empleado) intenta una acción reservada (rechazado)

```bash
TOKEN_EMPLEADO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 04 (*Cambiar el principal e inactivar*), llamada 3:

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-contact-persons/<CONTACTO_CARTERA>:deactivate" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO" \
  -H "Content-Type: application/json" \
  -d '{"version": 2}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/organization-contact-persons/{id}:deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`operario.dao` sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`: el operario (`Compras`, `Ventas` e `Inventario`) crea, consulta y modifica personas, organizaciones y sus contactos, pero la URL exige `perm:party-identity:organization_contact_persons:delete`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `operario.dao` (Empleado) consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/organization-contact-persons/<CONTACTO_COMERCIAL>" \
  -H "Authorization: Bearer $TOKEN_EMPLEADO"
```

Responde `200 OK` con la misma información que ve `admin.sio` en el paso 04: `perm:party-identity:organization_contact_persons:read` cubre `perm:party-identity:organization_contact_persons:read`. También pueden: `admin.dao`.

### 4. `admin.dao` intenta inactivar o retirar (rechazado)

```bash
TOKEN_ADMIN_DAO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-contact-persons/<CONTACTO_CARTERA>:deactivate" \
  -H "Authorization: Bearer $TOKEN_ADMIN_DAO" \
  -H "Content-Type: application/json" \
  -d '{"version": 2}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/organization-contact-persons/{id}:deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`admin.dao` (grupo `admin`) tiene `perm:party-identity:all:read`, `:all:create` y `:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.sio` (grupo `superadmin`). Ninguna de las áreas (`Compras`, `Ventas` e `Inventario`) puede.

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

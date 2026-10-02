# Usuarios y permisos — Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Inactivar la persona*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 02, 03.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la persona*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 02, 03.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la persona*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 02, 03.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la persona*): no tiene ningún permiso sobre `party-identity`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la persona*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la persona*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-referencias.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-referencias.md) | 2. Consultar la empresa desde la que se confirma en Operational Context | `GET http://localhost:8004/api/v1/companies` | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-persona-y-perfil.md) | 1. Registrar la persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-registrar-persona-y-perfil.md) | 2. Registrar el perfil de contacto | `POST /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-registrar-persona-y-perfil.md) | 3. Consultar el perfil vigente | `GET /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [03](03-inactivar-persona.md) | 1. Inactivar la persona | `POST /api/v1/person-identities/{id}/deactivate` | `perm:party-identity:person_identities:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-inactivar-persona.md) | 2. Intentar una versión nueva del perfil (rechazado) | `POST /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-inactivar-persona.md) | 3. Consultar el perfil (sigue vigente) | `GET /api/v1/person-identities/{id}/contact-profile` | `perm:party-identity:person_contact_profiles:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la persona y su perfil*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"identification_country_id": "<PAIS_CO>", "identification_type": "CC", "identification_number": "1000000005", "first_name": "LUIS", "last_name": "CLIENTE", "second_last_name": "FICTICIO", "birth_date": "1985-03-20"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:party-identity:person_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Registrar la persona y su perfil*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"identification_country_id": "<PAIS_CO>", "identification_type": "CC", "identification_number": "1000000005", "first_name": "LUIS", "last_name": "CLIENTE", "second_last_name": "FICTICIO", "birth_date": "1985-03-20"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:party-identity:person_identities:create",
  "instance": "/api/v1/person-identities",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` sobre `party-identity` solo tiene `read`; le falta `create`: puede **leer**, pero la URL exige `perm:party-identity:person_identities:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta un dato sensible (rechazado)

```bash
curl -s -X GET "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `403 Forbidden`: `perm:party-identity:person_contact_profiles:read` es un recurso sensible con permiso específico; `consulta.test` tiene permisos sobre `party-identity`, pero ninguno sobre `person_contact_profiles`. Solo pueden leerlo: `admin.test`, `supervisor.test`, `compras.test`, `ventas.test`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Responde `403 Forbidden`: `inventario.test` no tiene ningún permiso sobre `party-identity`.

### 5. `supervisor.test` intenta inactivar o retirar (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8002/api/v1/person-identities/<PERSONA_CLIENTE>/deactivate" \
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
  "detail": "Falta el permiso requerido: perm:party-identity:person_identities:delete",
  "instance": "/api/v1/person-identities/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

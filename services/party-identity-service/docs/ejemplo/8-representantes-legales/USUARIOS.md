# Usuarios y permisos — Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 04 (*Cerrar la relación de suplente*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la organización*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la organización*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la organización*): no tiene ningún permiso sobre `party-identity`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la organización*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Registrar la organización*): sobre `party-identity` solo tiene `read`; le falta `create`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-pais.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-registrar-identidades.md) | 1. Registrar la organización | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-registrar-identidades.md) | 2. Registrar la primera persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-registrar-identidades.md) | 3. Registrar la segunda persona | `POST /api/v1/person-identities` | `perm:party-identity:person_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-establecer-primary.md) | 1. Establecer el primer PRIMARY | `POST /api/v1/organization-identities/{id}/legal-representatives:set-primary` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-establecer-primary.md) | 2. Intentar registrar otro PRIMARY por el alta ordinaria (rechazado) | `POST /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-establecer-primary.md) | 3. Sustituir el PRIMARY | `POST /api/v1/organization-identities/{id}/legal-representatives:set-primary` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-suplente-y-cierre.md) | 1. Registrar a JORGE como suplente | `POST /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-suplente-y-cierre.md) | 2. Cerrar la relación de suplente | `POST /api/v1/organization-legal-representatives/{id}:close` | `perm:party-identity:organization_legal_representatives:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-suplente-y-cierre.md) | 3. Consultar el historial | `GET /api/v1/organization-identities/{id}/legal-representatives` | `perm:party-identity:organization_legal_representatives:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Registrar la organización y las personas*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"country_id": "<PAIS_CO>", "identification_type": "NIT", "identification_number": "900000008-8", "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S."}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:party-identity:organization_identities:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Registrar la organización y las personas*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/organization-identities" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"country_id": "<PAIS_CO>", "identification_type": "NIT", "identification_number": "900000008-8", "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S."}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:party-identity:organization_identities:create",
  "instance": "/api/v1/organization-identities",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` sobre `party-identity` solo tiene `read`; le falta `create`: puede **leer**, pero la URL exige `perm:party-identity:organization_identities:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta un dato sensible (rechazado)

```bash
curl -s -X GET "http://localhost:8002/api/v1/organization-identities/<ORG_INV>/legal-representatives?state=all" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `403 Forbidden`: `perm:party-identity:organization_legal_representatives:read` es un recurso sensible con permiso específico; `consulta.test` tiene permisos sobre `party-identity`, pero ninguno sobre `organization_legal_representatives`. Solo pueden leerlo: `admin.test`, `supervisor.test`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/api/v1/organization-identities/<ORG_INV>/legal-representatives?state=all" \
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
curl -s -X POST "http://localhost:8002/api/v1/organization-legal-representatives/<REP_JORGE_SUPLENTE>:close" \
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
  "detail": "Falta el permiso requerido: perm:party-identity:organization_legal_representatives:delete",
  "instance": "/api/v1/organization-legal-representatives/{id}:close",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

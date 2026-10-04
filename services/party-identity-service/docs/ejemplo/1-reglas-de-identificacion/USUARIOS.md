# Usuarios y permisos — Ejercicio 1 — Reglas de identificación: crear, versionar y retirar

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 05 (*Retirar la versión vigente*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 01, 04.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la regla `PASSPORT` (`PA`)*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 04.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la regla `PASSPORT` (`PA`)*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 04.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar las reglas activas de cédula (`CC`) de Colombia*): no tiene ningún permiso sobre `party-identity`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la regla `PASSPORT` (`PA`)*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 04.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear la regla `PASSPORT` (`PA`)*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 04.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-pais-y-reglas.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-pais-y-reglas.md) | 2. Consultar las reglas activas de cédula (`CC`) de Colombia | `GET /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-crear-regla.md) | 1. Crear la regla `PASSPORT` (`PA`) | `POST /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-regla.md) | 2. Intentar crear otra regla activa igual (rechazado) | `POST /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-crear-regla.md) | 3. Intentar crear una regla con un patrón inválido (rechazado) | `POST /api/v1/identification-type-rules` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-corregir-descripcion.md) | 1. Corregir la descripción y el ejemplo | `PUT /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-corregir-descripcion.md) | 2. Intentar cambiar el patrón con `PUT` (rechazado) | `PUT /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-nueva-version.md) | 1. Crear la nueva versión con el patrón corregido | `POST /api/v1/identification-type-rules/{id}/versions` | `perm:party-identity:identification_type_rules:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-nueva-version.md) | 2. Consultar la regla anterior | `GET /api/v1/identification-type-rules/{id}` | `perm:party-identity:identification_type_rules:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [05](05-retirar-regla.md) | 1. Retirar la versión vigente | `POST /api/v1/identification-type-rules/{id}/deactivate` | `perm:party-identity:identification_type_rules:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-retirar-regla.md) | 2. Intentar retirarla otra vez (rechazado) | `POST /api/v1/identification-type-rules/{id}/deactivate` | `perm:party-identity:identification_type_rules:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Crear la regla de pasaporte*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/identification-type-rules" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"party_kind": "PERSON", "country_id": "<PAIS_CO>", "identification_type": "PASSPORT", "sigla": "PA", "number_pattern": "^[A-Z0-9]{6,9}$", "number_pattern_description": "Pasaporte: 6 a 9 letras o dígitos.", "example_value": "AB123456"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:party-identity:identification_type_rules:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear la regla de pasaporte*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/identification-type-rules" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"party_kind": "PERSON", "country_id": "<PAIS_CO>", "identification_type": "PASSPORT", "sigla": "PA", "number_pattern": "^[A-Z0-9]{6,9}$", "number_pattern_description": "Pasaporte: 6 a 9 letras o dígitos.", "example_value": "AB123456"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/identification-type-rules",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` sobre `party-identity` solo tiene `read`; le falta `create`: puede **leer**, pero la URL exige `perm:party-identity:identification_type_rules:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/identification-type-rules?country_id=<PAIS_CO>&sigla=CC&is_active=true" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 01: `perm:party-identity:identification_type_rules:read` cubre `perm:party-identity:identification_type_rules:read`. También pueden: `supervisor.test`, `compras.test`, `ventas.test`, `reportes.test`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/api/v1/identification-type-rules?country_id=<PAIS_CO>&sigla=CC&is_active=true" \
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
curl -s -X POST "http://localhost:8002/api/v1/identification-type-rules/<REGLA_PA_V2>/deactivate" \
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
  "instance": "/api/v1/identification-type-rules/{id}/deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

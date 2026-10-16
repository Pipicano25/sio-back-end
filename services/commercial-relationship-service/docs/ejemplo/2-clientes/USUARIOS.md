# Usuarios y permisos — Ejercicio 2 — Clientes persona y organización

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 04 (*Inactivar el cliente persona*): sobre `company_customers` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Incorporar el cliente persona*): sobre `company_customers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Incorporar el cliente persona*): sobre `company_customers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la organización COMERCIALIZADORA CLIENTES FICTICIA S.A.S. en Party Identity*): no tiene ningún permiso sobre `organization_identities` de `party-identity`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la persona de contacto del minimarket (ficticia) en Party Identity*): no tiene ningún permiso sobre `organization_contact_persons` de `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la persona de contacto del minimarket (ficticia) en Party Identity*): no tiene ningún permiso sobre `organization_contact_persons` de `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 04.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear (salvo políticas de ganancia, spec 021).

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-identidades.md) | 1. Consultar la empresa COMERCIALIZADORA CLIENTES FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-identidades.md) | 2. Consultar la organización COMERCIALIZADORA CLIENTES FICTICIA S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-identidades.md) | 3. Consultar la persona cliente (ficticia) en Party Identity | `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-identidades.md) | 4. Consultar la organización MINIMARKET EJEMPLO FICTICIO S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-identidades.md) | 5. Consultar la persona de contacto del minimarket (ficticia) en Party Identity | `GET http://localhost:8002/api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-consultar-identidades.md) | 6. Consultar la organización DISTRIBUIDORA AJENA FICTICIA S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-identidades.md) | 7. Consultar la persona de contacto de la distribuidora (ficticia) en Party Identity | `GET http://localhost:8002/api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [02](02-cliente-persona.md) | 1. Incorporar el cliente persona | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-cliente-persona.md) | 2. Indicar un contacto preferido para una persona (rechazado) | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-cliente-organizacion.md) | 1. Indicar el contacto de otra organización (rechazado) | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-cliente-organizacion.md) | 2. Incorporar el cliente organización con su contacto | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-cliente-organizacion.md) | 3. Incorporar la propia empresa como cliente (rechazado) | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-y-estados.md) | 1. Cambiar el nombre visible y quitar el contacto | `PUT /api/v1/company-customers/{id}` 🔒 | `perm:commercial-relationship:company_customers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-y-estados.md) | 2. Inactivar el cliente persona | `POST /api/v1/company-customers/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_customers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-y-estados.md) | 3. Reactivar el cliente persona | `POST /api/v1/company-customers/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_customers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-y-estados.md) | 4. Listar los clientes organización | `GET /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Incorporar un cliente persona*):

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-customers" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"customer_kind": "PERSON", "person_identity_id": "<PERSONA>", "internal_code": "CLI-0001", "display_name": "Cliente persona (ficticio)"}'
```

Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre `perm:commercial-relationship:company_customers:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta escribir (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Incorporar un cliente persona*), llamada 1:

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-customers" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"customer_kind": "PERSON", "person_identity_id": "<PERSONA>", "internal_code": "CLI-0001", "display_name": "Cliente persona (ficticio)"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/{id}/company-customers",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene lecturas: puede **leer**, pero la URL exige `perm:commercial-relationship:company_customers:create`. El servicio no ejecuta nada: ni siquiera consulta Operational Context ni valida el cuerpo.

### 3. `consulta.test` consulta

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-customers?customer_kind=ORGANIZATION" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 04: `perm:commercial-relationship:company_customers:read` cubre `perm:commercial-relationship:company_customers:read` y `consulta.test` es miembro de la empresa. Sin membresía respondería `404`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-customers?customer_kind=ORGANIZATION" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Responde `403 Forbidden`: `inventario.test` no tiene ningún permiso de Commercial Relationship en el realm vigente, aunque sea miembro de la empresa.

### 5. `supervisor.test` intenta inactivar (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8005/api/v1/company-customers/<CLIENTE_PERSONA>/deactivate" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/company-customers/{id}/deactivate",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

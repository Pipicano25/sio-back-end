# Usuarios y permisos — Ejercicio 3 — Proveedores, bloqueo y desbloqueo

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Bloquear el laboratorio*): sobre `company_suppliers` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Seleccionar el laboratorio como proveedor*): sobre `company_suppliers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Seleccionar el laboratorio como proveedor*): sobre `company_suppliers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la organización LABORATORIO EJEMPLO FICTICIO S.A.S. en Party Identity*): no tiene ningún permiso sobre `organization_identities` de `party-identity`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Seleccionar el laboratorio como proveedor*): sobre `company_suppliers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Seleccionar el laboratorio como proveedor*): sobre `company_suppliers` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear.

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-organizaciones.md) | 1. Consultar la empresa DISTRIBUIDORA PROVEEDORES FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-organizaciones.md) | 2. Consultar la organización LABORATORIO EJEMPLO FICTICIO S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-organizaciones.md) | 3. Consultar la organización IMPORTADORA EJEMPLO FICTICIA S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-seleccionar-proveedores.md) | 1. Seleccionar el laboratorio como proveedor | `POST /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-seleccionar-proveedores.md) | 2. Registrar la importadora como cliente | `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-seleccionar-proveedores.md) | 3. Seleccionar la importadora también como proveedor | `POST /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-seleccionar-proveedores.md) | 4. Seleccionar otra vez el laboratorio (rechazado) | `POST /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-bloquear.md) | 1. Bloquear el laboratorio | `POST /api/v1/company-suppliers/{id}/block` 🔒 | `perm:commercial-relationship:company_suppliers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-bloquear.md) | 2. Reactivar el proveedor bloqueado (rechazado) | `POST /api/v1/company-suppliers/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-bloquear.md) | 3. Corregir el nombre visible sin desbloquear | `PUT /api/v1/company-suppliers/{id}` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-desbloquear-y-consultar.md) | 1. Desbloquear el laboratorio | `POST /api/v1/company-suppliers/{id}/unblock` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-desbloquear-y-consultar.md) | 2. Inactivar la importadora como proveedor | `POST /api/v1/company-suppliers/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_suppliers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-desbloquear-y-consultar.md) | 3. Listar todos los proveedores | `GET /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Seleccionar los proveedores*):

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-suppliers" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_PROVEEDOR>", "internal_code": "PRV-0001", "display_name": "Laboratorio (ficticio)"}'
```

Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre `perm:commercial-relationship:company_suppliers:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta escribir (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Seleccionar los proveedores*), llamada 1:

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-suppliers" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_PROVEEDOR>", "internal_code": "PRV-0001", "display_name": "Laboratorio (ficticio)"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/{id}/company-suppliers",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene lecturas: puede **leer**, pero la URL exige `perm:commercial-relationship:company_suppliers:create`. El servicio no ejecuta nada: ni siquiera consulta Operational Context ni valida el cuerpo.

### 3. `consulta.test` consulta

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-suppliers?status=ALL" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 04: `perm:commercial-relationship:company_suppliers:read` cubre `perm:commercial-relationship:company_suppliers:read` y `consulta.test` es miembro de la empresa. Sin membresía respondería `404`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-suppliers?status=ALL" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Responde `403 Forbidden`: `inventario.test` no tiene ningún permiso de Commercial Relationship en el realm vigente, aunque sea miembro de la empresa.

### 5. `supervisor.test` intenta bloquear (rechazado)

```bash
TOKEN_SUPERVISOR=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X POST "http://localhost:8005/api/v1/company-suppliers/<PROVEEDOR>/block" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"block_reason": "Incumplimiento de entregas (ficticio)", "version": 1}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/company-suppliers/{id}/block",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Bloquear queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

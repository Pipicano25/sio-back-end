# Usuarios y permisos — Ejercicio 1 — Empresa con su sede operativa principal

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: puede ejecutar **todo el ejercicio**.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Registrar la empresa con su sede operativa principal*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Registrar la empresa con su sede operativa principal*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la organización COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. en Party Identity Service*): no tiene ningún permiso sobre `party-identity`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Registrar la empresa con su sede operativa principal*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 03 (*Registrar la empresa con su sede operativa principal*): sobre `operational-context` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 04.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-organizacion.md) | 1. Consultar la organización COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. en Party Identity Service | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-consultar-ubicacion.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-consultar-ubicacion.md) | 2. Consultar el departamento Antioquia en Geography Service | `GET http://localhost:8000/global-administrative-divisions` | `perm:geography:global_administrative_divisions:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-consultar-ubicacion.md) | 3. Consultar la ciudad Medellín en Geography Service | `GET http://localhost:8000/global-cities` | `perm:geography:global_cities:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [03](03-registrar-empresa.md) | 1. Registrar la empresa con su sede operativa principal | `POST /api/v1/companies` | `perm:operational-context:companies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-registrar-empresa.md) | 2. Intentar registrar una empresa con una organización inexistente (rechazado) | `POST /api/v1/companies` | `perm:operational-context:companies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-consultar-y-modificar.md) | 1. Consultar la empresa por su `id` | `GET /api/v1/companies/{id}` | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [04](04-consultar-y-modificar.md) | 2. Modificar el teléfono con la versión vigente | `PUT /api/v1/companies/{id}` | `perm:operational-context:companies:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-consultar-y-modificar.md) | 3. Buscar la empresa por su organización | `GET /api/v1/companies` | `perm:operational-context:companies:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 03 (*Registrar la empresa*):

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_EMPRESA>", "email": "contacto@comercializadora-ficticia.co", "phone": "+57 604 000 0001", "address_line": "Carrera Ficticia 43A # 1-50", "country_id": "<PAIS_CO>", "administrative_division_id": "<DIV_ANT>", "city_id": "<CIU_MED>", "postal_code": "050021", "latitude": "6.208000", "longitude": "-75.567000"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:operational-context:companies:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 03 (*Registrar la empresa*), llamada 1:

```bash
curl -s -X POST "http://localhost:8004/api/v1/companies" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"organization_identity_id": "<ORG_EMPRESA>", "email": "contacto@comercializadora-ficticia.co", "phone": "+57 604 000 0001", "address_line": "Carrera Ficticia 43A # 1-50", "country_id": "<PAIS_CO>", "administrative_division_id": "<DIV_ANT>", "city_id": "<CIU_MED>", "postal_code": "050021", "latitude": "6.208000", "longitude": "-75.567000"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Falta el permiso requerido: perm:operational-context:companies:create",
  "instance": "/api/v1/companies",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene `perm:all:all:read`: puede **leer**, pero la URL exige `perm:operational-context:companies:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta (permitido)

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA>" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 04: `perm:all:all:read` cubre `perm:operational-context:companies:read`. Lo mismo pasa con `reportes.test`, `compras.test`, `ventas.test` e `inventario.test`.

### 4. `inventario.test` consulta (permitido)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8004/api/v1/companies/<EMPRESA>" \
  -H "Authorization: Bearer $TOKEN_INVENTARIO"
```

Responde `200 OK`: `inventario.test` tiene `perm:operational-context:all:read`, porque Inventory trabaja por empresa y sucursal. No tiene lectura en Party Identity, así que no podría consultar allá la razón social de la empresa.

### 5. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

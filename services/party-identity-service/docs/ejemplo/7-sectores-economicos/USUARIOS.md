# Usuarios y permisos — Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio**.
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Intentar inactivar X con un hijo activo (rechazado)*): sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 01, 05.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear el sector raíz X*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 05.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear el sector raíz X*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 05.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Listar las secciones CIIU (raíces del árbol)*): no tiene ningún permiso sobre `party-identity`. No puede hacer ninguna de las consultas (`GET`) de Party Identity de este ejercicio.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear el sector raíz X*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 05.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Crear el sector raíz X*): sobre `party-identity` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 01, 05.

**Para hacer el ejercicio completo use `admin.test`.** `supervisor.test` puede crear, modificar y reactivar, pero no inactivar ni retirar.

## Permiso por URL

✅ = el usuario puede ejecutar la llamada · ❌ = recibe `403 Forbidden`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-recorrer-arbol-ciiu.md) | 1. Listar las secciones CIIU (raíces del árbol) | `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-recorrer-arbol-ciiu.md) | 2. Consultar la sección A | `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-recorrer-arbol-ciiu.md) | 3. Listar las divisiones de la sección A | `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-recorrer-arbol-ciiu.md) | 4. Consultar la clase 0123 (Cultivo de café) | `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-recorrer-arbol-ciiu.md) | 5. Consultar la clase 4711 por texto | `GET /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-recorrer-arbol-ciiu.md) | 6. Ver el detalle de la clase 0123 | `GET /api/v1/global-business-sectors/{id}` | `perm:party-identity:global_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-clasificacion-propia.md) | 1. Crear el sector raíz X | `POST /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-clasificacion-propia.md) | 2. Crear el sector X1, hijo de X | `POST /api/v1/global-business-sectors` | `perm:party-identity:global_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-clasificacion-propia.md) | 3. Intentar colgar X1 de un sector CIIU (rechazado) | `PUT /api/v1/global-business-sectors/{id}` | `perm:party-identity:global_business_sectors:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-clasificacion-propia.md) | 4. Intentar inactivar X con un hijo activo (rechazado) | `POST /api/v1/global-business-sectors/{id}:deactivate` | `perm:party-identity:global_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-clasificacion-propia.md) | 5. Inactivar X1 | `POST /api/v1/global-business-sectors/{id}:deactivate` | `perm:party-identity:global_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-clasificacion-propia.md) | 6. Inactivar X | `POST /api/v1/global-business-sectors/{id}:deactivate` | `perm:party-identity:global_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-consultar-pais.md) | 1. Consultar el país Colombia en Geography Service | `GET http://localhost:8000/global-countries` | `perm:geography:global_countries:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [04](04-asignar-sectores.md) | 1. Registrar la organización | `POST /api/v1/organization-identities` | `perm:party-identity:organization_identities:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-asignar-sectores.md) | 2. Asignar la clase 0123 como sector principal | `POST /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-asignar-sectores.md) | 3. Asignar la clase 4711 como sector secundario | `POST /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-asignar-sectores.md) | 4. Intentar asignar otra vez la clase 4711 (rechazado) | `POST /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-asignar-sectores.md) | 5. Cambiar el sector principal a 4711 | `POST /api/v1/organization-business-sectors/{id}:set-primary` | `perm:party-identity:organization_business_sectors:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-cerrar-asignacion.md) | 1. Cerrar la asignación de la clase 0123 | `POST /api/v1/organization-business-sectors/{id}:close` | `perm:party-identity:organization_business_sectors:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-cerrar-asignacion.md) | 2. Consultar los sectores vigentes | `GET /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [05](05-cerrar-asignacion.md) | 3. Consultar el historial completo | `GET /api/v1/organization-identities/{id}/business-sectors` | `perm:party-identity:organization_business_sectors:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Crear sectores en una clasificación propia*):

```bash
curl -s -X POST "http://localhost:8002/api/v1/global-business-sectors" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"classification_system": "ejemplo_interno", "code": " x ", "name": "Sector interno X"}'
```

Responde `201 Created`: `admin.test` tiene `perm:all:all:all`, que cubre `perm:party-identity:global_business_sectors:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta crear (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Crear sectores en una clasificación propia*), llamada 1:

```bash
curl -s -X POST "http://localhost:8002/api/v1/global-business-sectors" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"classification_system": "ejemplo_interno", "code": " x ", "name": "Sector interno X"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/party-identity/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/global-business-sectors",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` sobre `party-identity` solo tiene `read`; le falta `create`: puede **leer**, pero la URL exige `perm:party-identity:global_business_sectors:create`. El servicio no ejecuta nada: ni siquiera valida el cuerpo.

### 3. `consulta.test` consulta (permitido)

```bash
curl -s -X GET "http://localhost:8002/api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&level_root=true&page_size=5" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 01: `perm:party-identity:global_business_sectors:read` cubre `perm:party-identity:global_business_sectors:read`. También pueden: `supervisor.test`, `compras.test`, `ventas.test`, `reportes.test`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8002/api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&level_root=true&page_size=5" \
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
curl -s -X POST "http://localhost:8002/api/v1/global-business-sectors/<SECTOR_X>:deactivate" \
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
  "instance": "/api/v1/global-business-sectors/{id}:deactivate",
  "code": "PARTY_IDENTITY.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar o retirar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

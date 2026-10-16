# Usuarios y permisos — Ejercicio 1 — Adopción de productos del Excel

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: **no puede completar el ejercicio**. Se detiene en el paso 06 (*Inactivar el acetaminofén*): sobre `company_products` solo tiene `create`, `read`, `update`; le falta `delete`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén*): sobre `company_products` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén*): sobre `company_products` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén*): sobre `company_products` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén*): sobre `company_products` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén*): sobre `company_products` solo tiene `read`; le falta `create`. Sí puede hacer las consultas (`GET`) de los pasos 06, 07.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear (salvo políticas de ganancia, spec 021).

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos-base.md) | 1. Consultar la empresa DROGUERÍA EJEMPLO FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 2. Consultar el producto global Acetaminofén (Adorem) 500 mg tableta en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 3. Consultar el producto global Aguja 18G x 1 1/2 en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7706634002856` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 4. Consultar el producto global Winny Gold etapa 6 XXXG en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7701021118264` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 5. Consultar el producto global Cepillo Colgate infantil 2-5 años en Product Catalog | `GET http://localhost:8003/api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos-base.md) | 6. Consultar el producto global Producto incompleto (ficticio) en Product Catalog | `GET http://localhost:8003/api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-adoptar-acetaminofen.md) | 1. Adoptar el acetaminofén | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-adoptar-aguja.md) | 1. Adoptar la aguja | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-rechazos.md) | 1. Adoptar otra vez el acetaminofén (rechazado) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-rechazos.md) | 2. Adoptar el cepillo inactivo (rechazado) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-rechazos.md) | 3. Adoptar un producto incompleto (rechazado) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-rechazos.md) | 4. Adoptar los pañales con un código ya usado (rechazado) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-rechazos.md) | 5. Adoptar los pañales con su código del Excel | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-precio-y-moneda.md) | 1. Intentar fijar un precio en el producto (rechazado) | `PUT /api/v1/company-products/{id}` 🔒 | `perm:commercial-relationship:company_products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-precio-y-moneda.md) | 2. Cambiar la moneda | `PUT /api/v1/company-products/{id}` 🔒 | `perm:commercial-relationship:company_products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-consultar-y-estados.md) | 1. Listar los productos de la empresa | `GET /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [06](06-consultar-y-estados.md) | 2. Consultar varios productos por lotes | `POST /api/v1/company-products/batch-lookup` | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [06](06-consultar-y-estados.md) | 3. Inactivar el acetaminofén | `POST /api/v1/company-products/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_products:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-consultar-y-estados.md) | 4. Reactivar el acetaminofén | `POST /api/v1/company-products/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [07](07-resumen-de-empresas.md) | 1. Ver la primera empresa del resumen | `GET /api/v1/company-summaries` | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Adoptar el acetaminofén (fila 40)*):

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045", "reference_code": "48691", "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "short_name": "ACETAMINOFEN", "currency_code": "COP", "inventory_control_enabled": true, "lot_tracking_enabled": true, "expiration_tracking_enabled": true}'
```

Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre `perm:commercial-relationship:company_products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta escribir (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Adoptar el acetaminofén (fila 40)*), llamada 1:

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045", "reference_code": "48691", "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "short_name": "ACETAMINOFEN", "currency_code": "COP", "inventory_control_enabled": true, "lot_tracking_enabled": true, "expiration_tracking_enabled": true}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/{id}/company-products",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`consulta.test` solo tiene lecturas: puede **leer**, pero la URL exige `perm:commercial-relationship:company_products:create`. El servicio no ejecuta nada: ni siquiera consulta Operational Context ni valida el cuerpo.

### 3. `consulta.test` consulta

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products?search=0005" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 06: `perm:commercial-relationship:company_products:read` cubre `perm:commercial-relationship:company_products:read` y `consulta.test` es miembro de la empresa. Sin membresía respondería `404`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products?search=0005" \
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
curl -s -X POST "http://localhost:8005/api/v1/company-products/<CP_ACETAMINOFEN>/deactivate" \
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
  "instance": "/api/v1/company-products/{id}/deactivate",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

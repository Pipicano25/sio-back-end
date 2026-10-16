# Usuarios y permisos — Ejercicio 7 — Políticas de ganancia de una lista de precios

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear (salvo políticas de ganancia, spec 021).

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos.md) | 1. Consultar la empresa DROGUERÍA POLÍTICAS FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 2. Consultar el producto global ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 3. Consultar el producto global IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7702057716226` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 4. Consultar la presentación global caja x100 del acetaminofén en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 5. Consultar la presentación global sobre x10 del acetaminofén en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 6. Consultar la presentación global caja x30 del irbesartán en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-preparar-la-lista.md) | 1. Adoptar el acetaminofén (fila 40) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar-la-lista.md) | 2. Adoptar el irbesartán (fila 16577) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar-la-lista.md) | 3. Adoptar la caja x100 del acetaminofén | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar-la-lista.md) | 4. Adoptar el sobre x10 del acetaminofén | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar-la-lista.md) | 5. Adoptar la caja x30 del irbesartán | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar-la-lista.md) | 6. Crear la lista PUBLICO en COP | `POST /api/v1/companies/{id}/price-lists` 🔒 | `perm:commercial-relationship:price_lists:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-politicas.md) | 1. Crear la política Alimentos (15 %) con la caja y el sobre | `POST /api/v1/companies/{id}/price-lists/{id}/pricing-policies` 🔒 | `perm:commercial-relationship:pricing_policies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-politicas.md) | 2. Crear la política Especiales (50 %) con la caja (rechazado) | `POST /api/v1/companies/{id}/price-lists/{id}/pricing-policies` 🔒 | `perm:commercial-relationship:pricing_policies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-politicas.md) | 3. Crear la política Especiales (50 %) con el irbesartán | `POST /api/v1/companies/{id}/price-lists/{id}/pricing-policies` 🔒 | `perm:commercial-relationship:pricing_policies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-politicas.md) | 4. Crear una política con 1000,0001 % (rechazado) | `POST /api/v1/companies/{id}/price-lists/{id}/pricing-policies` 🔒 | `perm:commercial-relationship:pricing_policies:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-crear-politicas.md) | 5. Listar las políticas de la lista | `GET /api/v1/companies/{id}/price-lists/{id}/pricing-policies` 🔒 | `perm:commercial-relationship:pricing_policies:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-politicas.md) | 1. Cambiar Alimentos a 20 % | `POST /api/v1/pricing-policies/{id}/percentage` 🔒 | `perm:commercial-relationship:pricing_policies:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-politicas.md) | 2. Consultar el historial de porcentajes | `GET /api/v1/pricing-policies/{id}/terms` 🔒 | `perm:commercial-relationship:pricing_policies:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-politicas.md) | 3. Retirar el sobre de Alimentos | `POST /api/v1/pricing-policies/{id}/presentations/remove` 🔒 | `perm:commercial-relationship:pricing_policies:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-politicas.md) | 4. Inactivar Especiales | `POST /api/v1/pricing-policies/{id}/deactivate` 🔒 | `perm:commercial-relationship:pricing_policies:delete` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-modificar-politicas.md) | 5. Cambiar el porcentaje de la política inactiva (rechazado) | `POST /api/v1/pricing-policies/{id}/percentage` 🔒 | `perm:commercial-relationship:pricing_policies:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Adoptar los productos y crear la lista*):

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045", "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "currency_code": "COP"}'
```

Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre `perm:commercial-relationship:company_products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta escribir (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Adoptar los productos y crear la lista*), llamada 1:

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045", "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "currency_code": "COP"}'
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
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies" \
  -H "Authorization: Bearer $TOKEN_CONSULTA"
```

Responde `200 OK` con la misma información que ve `admin.test` en el paso 03: `None` cubre `perm:commercial-relationship:pricing_policies:read` y `consulta.test` es miembro de la empresa. Sin membresía respondería `404`.

### 4. `inventario.test` consulta (rechazado)

```bash
TOKEN_INVENTARIO=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

```bash
curl -s -X GET "http://localhost:8005/api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies" \
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
curl -s -X POST "http://localhost:8005/api/v1/pricing-policies/<ESPECIALES>/deactivate" \
  -H "Authorization: Bearer $TOKEN_SUPERVISOR" \
  -H "Content-Type: application/json" \
  -d '{"version": 1, "reason": "Fin de la temporada de ofertas"}'
```

Respuesta `403 Forbidden`:

```json
{
  "type": "https://sio/errors/commercial-relationship/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/pricing-policies/{id}/deactivate",
  "code": "COMMERCIAL_RELATIONSHIP.FORBIDDEN",
  "trace_id": "<trace_id>"
}
```

`supervisor.test` tiene `perm:all:all:read`, `perm:all:all:create` y `perm:all:all:update`, pero **no** `delete`. Inactivar queda para `admin.test`.

### 6. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

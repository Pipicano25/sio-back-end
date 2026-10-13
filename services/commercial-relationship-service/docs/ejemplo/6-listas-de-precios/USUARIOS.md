# Usuarios y permisos — Ejercicio 6 — Listas de precios y precio aplicable

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el irbesartán (fila 16577)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el irbesartán (fila 16577)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el irbesartán (fila 16577)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el irbesartán (fila 16577)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el irbesartán (fila 16577)*): sobre `company_products` solo tiene `read`; le falta `create`.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear.

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos.md) | 1. Consultar la empresa DROGUERÍA PRECIOS FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 2. Consultar el producto global IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7702057716226` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 3. Consultar el producto global ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 4. Consultar la presentación global caja x30 del irbesartán en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 5. Consultar la presentación global caja x100 del acetaminofén en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-adoptar-productos.md) | 1. Adoptar el irbesartán (fila 16577) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 2. Adoptar el acetaminofén | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 3. Adoptar la caja x30 del irbesartán | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 4. Adoptar la caja x100 del acetaminofén | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-lista-y-precio.md) | 1. Crear la lista 10 como predeterminada en COP | `POST /api/v1/companies/{id}/price-lists` 🔒 | `perm:commercial-relationship:price_lists:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-lista-y-precio.md) | 2. Registrar un precio sin presentación (rechazado) | `POST /api/v1/companies/{id}/price-list-items` 🔒 | `perm:commercial-relationship:price_list_items:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-lista-y-precio.md) | 3. Registrar el precio real de la caja x30 del irbesartán | `POST /api/v1/companies/{id}/price-list-items` 🔒 | `perm:commercial-relationship:price_list_items:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-lista-y-precio.md) | 4. Registrar otro precio que se cruza (rechazado) | `POST /api/v1/companies/{id}/price-list-items` 🔒 | `perm:commercial-relationship:price_list_items:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-cambiar-precio.md) | 1. Modificar el valor del precio en vigencia (rechazado) | `PUT /api/v1/price-list-items/{id}` 🔒 | `perm:commercial-relationship:price_list_items:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-cambiar-precio.md) | 2. Cambiar el precio desde 2099 (ficticio) | `POST /api/v1/price-list-items/{id}/change-price` 🔒 | `perm:commercial-relationship:price_list_items:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [05](05-precio-aplicable.md) | 1. Resolver hoy: irbesartán y acetaminofén con la lista predeterminada | `POST /api/v1/companies/{id}/applicable-prices/resolve` 🔒 | `perm:commercial-relationship:price_list_items:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [05](05-precio-aplicable.md) | 2. Resolver con la lista explícita para el acetaminofén | `POST /api/v1/companies/{id}/applicable-prices/resolve` 🔒 | `perm:commercial-relationship:price_list_items:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [05](05-precio-aplicable.md) | 3. Resolver en 2099: precio nuevo | `POST /api/v1/companies/{id}/applicable-prices/resolve` 🔒 | `perm:commercial-relationship:price_list_items:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Adoptar los productos*):

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_IRBESARTAN>", "internal_code": "022315", "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK", "currency_code": "COP"}'
```

Responde `201 Created` si `admin.test` es miembro de la empresa: `perm:all:all:all` cubre `perm:commercial-relationship:company_products:create`. Reemplace las variables `<…>` por los `id` guardados.

### 2. `consulta.test` intenta escribir (rechazado)

```bash
TOKEN_CONSULTA=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Intenta el paso 02 (*Adoptar los productos*), llamada 1:

```bash
curl -s -X POST "http://localhost:8005/api/v1/companies/<EMPRESA>/company-products" \
  -H "Authorization: Bearer $TOKEN_CONSULTA" \
  -H "Content-Type: application/json" \
  -d '{"global_product_id": "<GP_IRBESARTAN>", "internal_code": "022315", "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK", "currency_code": "COP"}'
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

### 3. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

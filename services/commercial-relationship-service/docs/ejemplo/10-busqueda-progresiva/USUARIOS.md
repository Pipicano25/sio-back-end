# Usuarios y permisos — Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear (salvo políticas de ganancia, spec 021).

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos.md) | 1. Consultar la empresa DROGUERÍA BÚSQUEDAS FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 2. Consultar el producto global ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 3. Consultar el producto global AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7706634002856` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 4. Consultar el producto global IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7702057716226` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 5. Consultar la presentación global Caja x100 en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 6. Consultar la presentación global Sobre x10 en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-adoptar-productos.md) | 1. Adoptar el acetaminofén (fila 40) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 2. Adoptar la aguja (fila 413) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 3. Adoptar el irbesartán (fila 16577) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 4. Adoptar la caja x100 del acetaminofén | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-adoptar-productos.md) | 5. Adoptar el sobre x10 del acetaminofén | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-buscar.md) | 1. Buscar «tableta» en el nombre | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [03](03-buscar.md) | 2. Buscar por una parte del SKU | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [03](03-buscar.md) | 3. Buscar por código interno exacto | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [04](04-continuar.md) | 1. Primeros dos productos | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [04](04-continuar.md) | 2. Continuar después del segundo | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-lotes-y-rechazos.md) | 1. ¿Cuáles de estos productos coinciden con «aguja»? | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-lotes-y-rechazos.md) | 2. Presentaciones del acetaminofén y la aguja | `POST /api/v1/companies/{id}/company-product-presentations/by-products` 🔒 | `perm:commercial-relationship:company_product_presentations:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [05](05-lotes-y-rechazos.md) | 3. Pedir 101 productos (rechazado) | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [05](05-lotes-y-rechazos.md) | 4. Enviar los dos tipos de ids a la vez (rechazado) | `POST /api/v1/companies/{id}/company-products/search` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Adoptar los productos y las presentaciones*):

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

Intenta el paso 02 (*Adoptar los productos y las presentaciones*), llamada 1:

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

### 3. Sin token (rechazado)

Cualquier URL de `/api/v1` sin el encabezado `Authorization` responde `401 Unauthorized`, antes de revisar permisos.

---

[← Orden del ejercicio](ORDEN.md)

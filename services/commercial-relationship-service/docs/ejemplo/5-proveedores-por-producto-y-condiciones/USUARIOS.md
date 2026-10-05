# Usuarios y permisos — Ejercicio 5 — Proveedores por producto y condiciones de pago

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

Qué usuario de prueba del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) puede ejecutar cada URL de este ejercicio y por qué. Todos los resultados se comprobaron contra la API: cada usuario sin permiso recibió `403`, y los usuarios con lectura (miembros de la empresa) obtuvieron la respuesta en las consultas.

## Resumen por usuario

- **`admin.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`supervisor.test`**: puede ejecutar **todo el ejercicio** (con membresía en la empresa).
- **`compras.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`ventas.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`inventario.test`**: **no puede completar el ejercicio**. Se detiene en el paso 01 (*Consultar la organización LABORATORIO PROVEEDOR FICTICIO S.A.S. en Party Identity*): no tiene ningún permiso sobre `organization_identities` de `party-identity`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`reportes.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.
- **`consulta.test`**: **no puede completar el ejercicio**. Se detiene en el paso 02 (*Adoptar el acetaminofén (fila 40)*): sobre `company_products` solo tiene `read`; le falta `create`. No tiene ningún permiso de Commercial Relationship: todas sus llamadas a este servicio responden `403`.

**Para hacer el ejercicio completo use `admin.test`**, siempre que tenga membresía `ACTIVE` en la empresa: en Commercial Relationship ni siquiera `perm:all:all:all` exime de la membresía (DS-03). `supervisor.test` puede crear y modificar, pero no inactivar ni bloquear.

## Permiso por URL

✅ = el usuario tiene el permiso de la llamada · ❌ = recibe `403 Forbidden`. Tener el permiso no basta en las URL con 🔒: sin membresía en la empresa el usuario recibe `404`.

| Paso | Llamada | Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-datos.md) | 1. Consultar la empresa DROGUERÍA COMPRAS FICTICIA S.A.S. en Operational Context | `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 2. Consultar el producto global ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED en Product Catalog | `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 3. Consultar la presentación global Caja x100 en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 4. Consultar la unidad base del producto global en Product Catalog | `GET http://localhost:8003/api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 5. Consultar la organización LABORATORIO PROVEEDOR FICTICIO S.A.S. en Party Identity | `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 6. Consultar el tipo de condición de pago CASH en Payment Reference | `GET http://localhost:8105/global-payment-condition-types` | `perm:payment-reference:global_payment_condition_types:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [01](01-consultar-datos.md) | 7. Consultar el tipo de condición de pago CREDIT en Payment Reference | `GET http://localhost:8105/global-payment-condition-types` | `perm:payment-reference:global_payment_condition_types:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| [02](02-preparar.md) | 1. Adoptar el acetaminofén (fila 40) | `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar.md) | 2. Adoptar la caja x100 | `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [02](02-preparar.md) | 3. Seleccionar el proveedor | `POST /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-productos-de-proveedor.md) | 1. Registrar la relación general | `POST /api/v1/companies/{id}/supplier-products` 🔒 | `perm:commercial-relationship:supplier_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-productos-de-proveedor.md) | 2. Registrar con otra unidad (rechazado) | `POST /api/v1/companies/{id}/supplier-products` 🔒 | `perm:commercial-relationship:supplier_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-productos-de-proveedor.md) | 3. Registrar la relación de la caja x100 | `POST /api/v1/companies/{id}/supplier-products` 🔒 | `perm:commercial-relationship:supplier_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-productos-de-proveedor.md) | 4. Repetir la relación general (rechazado) | `POST /api/v1/companies/{id}/supplier-products` 🔒 | `perm:commercial-relationship:supplier_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-condiciones-de-pago.md) | 1. Registrar contado con 15 días (rechazado) | `POST /api/v1/companies/{id}/supplier-payment-conditions` 🔒 | `perm:commercial-relationship:supplier_payment_conditions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-condiciones-de-pago.md) | 2. Registrar contado con descuento por pronto pago | `POST /api/v1/companies/{id}/supplier-payment-conditions` 🔒 | `perm:commercial-relationship:supplier_payment_conditions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [04](04-condiciones-de-pago.md) | 3. Registrar crédito a 30 días como predeterminado en COP | `POST /api/v1/companies/{id}/supplier-payment-conditions` 🔒 | `perm:commercial-relationship:supplier_payment_conditions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Ejemplos de uso con los usuarios

La contraseña de todos los usuarios de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`. Cárguela en la terminal antes de pedir tokens.

### 1. Ejecutar el ejercicio con `admin.test`

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=admin.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Por ejemplo, el paso 02 (*Adoptar el producto y la presentación y seleccionar el proveedor*):

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

Intenta el paso 02 (*Adoptar el producto y la presentación y seleccionar el proveedor*), llamada 1:

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

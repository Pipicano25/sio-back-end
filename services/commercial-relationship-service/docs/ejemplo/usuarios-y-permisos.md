# Usuarios y permisos en los ejercicios

[← Todos los ejercicios](README.md)

Este documento explica qué usuarios de prueba trae el realm de Keycloak (`infrastructure/keycloak/realm-template/sio-realm.template.json`), qué permiso exige cada URL que usan los ejercicios y qué usuarios pueden llamarla. Cada ejercicio tiene además su propio `USUARIOS.md`.

## Cómo funcionan los permisos

1. El usuario inicia sesión en Keycloak (`http://localhost:8081`, realm `sio`, cliente `sio-web`) y recibe un token.
2. Los permisos vienen en el token, en `resource_access.sio-api.roles`. Keycloak se los asigna por el **grupo** al que pertenece el usuario.
3. Cada permiso tiene la forma `perm:{servicio}:{recurso}:{acción}`. En los permisos del usuario, `all` vale como comodín en cualquier parte:
   - `perm:all:all:all` → cualquier acción, en cualquier recurso, de cualquier servicio.
   - `perm:all:all:read` → solo `read`, en todos los servicios (`supervisores`).
   - `perm:commercial-relationship:all:read` → solo `read`, solo en Commercial Relationship (`compras` y `ventas`).
4. Cada URL exige un permiso concreto (por ejemplo `perm:commercial-relationship:company_products:create`). Si falta, el servicio responde `403 Forbidden` e indica cuál. Sin token, o con un token vencido, responde `401 Unauthorized`.
5. El permiso se revisa **antes** que todo lo demás: un usuario sin permiso recibe `403` aunque el JSON esté mal, y el servicio ni siquiera consulta Operational Context.
6. **Aislamiento por empresa:** el permiso dice *qué* puede hacer el usuario; la membresía en Operational Context dice *dónde*. Sin membresía `ACTIVE` en la empresa, la URL responde `404`, igual que un `id` inexistente (URL con 🔒). **Ningún permiso de usuario exime de la membresía**, ni `perm:all:all:all` (DS-03).
7. **Consulta técnica:** solo una cuenta de servicio (`client_credentials`, con `client_id` y `preferred_username = service-account-{client_id}`) con `perm:commercial-relationship:platform:lookup` lee por UUID sin membresía. Es para Inventory, Purchase y Sales; ningún usuario de prueba la usa.

## Usuarios de prueba

Todos comparten la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`).

| Usuario | Grupo | Permisos del grupo en Commercial Relationship | Puede |
| --- | --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` | Todo, en las empresas donde es miembro |
| `supervisor.test` | `supervisores` | `perm:all:all:read`<br>`perm:all:all:create`<br>`perm:all:all:update` | Consultar, adoptar, incorporar, seleccionar, modificar, reactivar y desbloquear. **No** inactivar ni bloquear |
| `compras.test` | `compras` | `perm:commercial-relationship:all:read` | Solo consultar |
| `ventas.test` | `ventas` | `perm:commercial-relationship:all:read` | Solo consultar |
| `inventario.test` | `inventario` | `perm:commercial-relationship:company_products:read` | Nada (`403`) |
| `reportes.test` | `reportes` | `perm:commercial-relationship:company_customers:read`<br>`perm:commercial-relationship:company_products:read`<br>`perm:commercial-relationship:company_suppliers:read`<br>`perm:commercial-relationship:company_product_presentations:read`<br>`perm:commercial-relationship:price_lists:read`<br>`perm:commercial-relationship:price_list_items:read` | Solo consultar |
| `consulta.test` | `consulta` | `perm:commercial-relationship:company_customers:read`<br>`perm:commercial-relationship:company_products:read`<br>`perm:commercial-relationship:company_suppliers:read`<br>`perm:commercial-relationship:company_product_presentations:read`<br>`perm:commercial-relationship:price_lists:read`<br>`perm:commercial-relationship:price_list_items:read` | Solo consultar |

## Cómo obtener el token de cada usuario

Cambie `username` por el usuario que quiera probar:

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=consulta.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

En **PowerShell** (Windows):

```powershell
$body = @{ grant_type = 'password'; client_id = 'sio-web'; scope = 'openid'
           username = 'consulta.test'; password = $env:KEYCLOAK_TEST_USER_PASSWORD }
$TOKEN = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8081/realms/sio/protocol/openid-connect/token' -Body $body).access_token
Invoke-RestMethod -Uri 'http://localhost:8005/api/v1/companies/<EMPRESA>/company-products' `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

Luego envíe el token en cada llamada:

```http
Authorization: Bearer <TOKEN>
```

Atajo: `python services/get_token.py <rol>` (por ejemplo `TOKEN=$(python services/get_token.py consulta)`) obtiene el token de `<rol>.test`. Lee la contraseña de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`.

## Permiso de cada URL de los ejercicios

✅ = tiene el permiso · ❌ = recibe `403`. 🔒 = además exige membresía en la empresa (si no, `404`). Columna *Ejercicios*: en cuáles se usa la URL.

| Método y URL | Permiso requerido | admin | supervisor | compras | ventas | inventario | reportes | consulta | Ejercicios |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET http://localhost:8004/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 2, 3, 4, 5, 6 |
| `GET http://localhost:8003/api/v1/products/by-identifier/7707355056876` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 4, 5, 6 |
| `GET http://localhost:8003/api/v1/products/by-identifier/7706634002856` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1, 4 |
| `GET http://localhost:8003/api/v1/products/by-identifier/7701021118264` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `GET http://localhost:8003/api/v1/products` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `POST /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1, 4, 5, 6 |
| `PUT /api/v1/company-products/{id}` 🔒 | `perm:commercial-relationship:company_products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `GET /api/v1/companies/{id}/company-products` 🔒 | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `POST /api/v1/company-products/batch-lookup` | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `POST /api/v1/company-products/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_products:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `POST /api/v1/company-products/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_products:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1 |
| `GET /api/v1/company-summaries` | `perm:commercial-relationship:company_products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| `GET http://localhost:8002/api/v1/organization-identities` | `perm:party-identity:organization_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 2, 3, 5 |
| `GET http://localhost:8002/api/v1/person-identities` | `perm:party-identity:person_identities:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 2 |
| `GET http://localhost:8002/api/v1/organization-identities/{id}/contact-persons` | `perm:party-identity:organization_contact_persons:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 2 |
| `POST /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2, 3 |
| `PUT /api/v1/company-customers/{id}` 🔒 | `perm:commercial-relationship:company_customers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `POST /api/v1/company-customers/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_customers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `POST /api/v1/company-customers/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_customers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 2 |
| `GET /api/v1/companies/{id}/company-customers` 🔒 | `perm:commercial-relationship:company_customers:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 2 |
| `POST /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3, 5 |
| `POST /api/v1/company-suppliers/{id}/block` 🔒 | `perm:commercial-relationship:company_suppliers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/company-suppliers/{id}/reactivate` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `PUT /api/v1/company-suppliers/{id}` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/company-suppliers/{id}/unblock` 🔒 | `perm:commercial-relationship:company_suppliers:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `POST /api/v1/company-suppliers/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_suppliers:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 |
| `GET /api/v1/companies/{id}/company-suppliers` 🔒 | `perm:commercial-relationship:company_suppliers:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 3 |
| `GET http://localhost:8003/api/v1/products/{id}/presentations` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4, 5, 6 |
| `POST /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 4, 5, 6 |
| `GET /api/v1/company-product-presentations/{id}` 🔒 | `perm:commercial-relationship:company_product_presentations:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 4 |
| `POST /api/v1/company-product-presentations/{id}/deactivate` 🔒 | `perm:commercial-relationship:company_product_presentations:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 4 |
| `GET /api/v1/companies/{id}/company-product-presentations` 🔒 | `perm:commercial-relationship:company_product_presentations:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 4 |
| `GET http://localhost:8003/api/v1/products/{id}` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| `GET http://localhost:8105/global-payment-condition-types` | `perm:payment-reference:global_payment_condition_types:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 5 |
| `POST /api/v1/companies/{id}/supplier-products` 🔒 | `perm:commercial-relationship:supplier_products:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `POST /api/v1/companies/{id}/supplier-payment-conditions` 🔒 | `perm:commercial-relationship:supplier_payment_conditions:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 5 |
| `GET http://localhost:8003/api/v1/products/by-identifier/7702057716226` | `perm:product-catalog:products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 6 |
| `POST /api/v1/companies/{id}/price-lists` 🔒 | `perm:commercial-relationship:price_lists:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/companies/{id}/price-list-items` 🔒 | `perm:commercial-relationship:price_list_items:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `PUT /api/v1/price-list-items/{id}` 🔒 | `perm:commercial-relationship:price_list_items:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/price-list-items/{id}/change-price` 🔒 | `perm:commercial-relationship:price_list_items:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 |
| `POST /api/v1/companies/{id}/applicable-prices/resolve` 🔒 | `perm:commercial-relationship:price_list_items:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 6 |

## Permisos que no son obvios

- `perm:commercial-relationship:company_products:create`: Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- `perm:commercial-relationship:company_products:delete`: Inactivar exige `delete` aunque no borra nada; reactivar exige `update`. `supervisor.test` no tiene `delete`.
- `perm:commercial-relationship:company_customers:create`: Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- `perm:commercial-relationship:company_suppliers:create`: Igual que los clientes: el token debe poder leer organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.
- `perm:commercial-relationship:company_suppliers:delete`: Inactivar **y bloquear** un proveedor exigen `delete` (DS-16); reactivar y desbloquear exigen `update`. `supervisor.test` no puede bloquear.
- Las URL de `http://localhost:8004` son de **Operational Context**, las de `http://localhost:8003` de **Product Catalog** y las de `http://localhost:8002` de **Party Identity**: exigen permisos de esos servicios.

## Qué usuario usar

| Para… | Usuario |
| --- | --- |
| Hacer los ejercicios completos | `admin.test` (con membresía en la empresa) |
| Crear y modificar sin poder inactivar ni bloquear | `supervisor.test` (con membresía) |
| Verificar lo cargado | `consulta.test`, `reportes.test`, `compras.test` o `ventas.test` (con membresía) |
| Probar rechazos por falta de permiso | `consulta.test` en cualquier `POST` o `PUT`; `inventario.test` en cualquier URL; `supervisor.test` al inactivar o bloquear |

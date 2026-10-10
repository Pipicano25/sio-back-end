# Usuarios y permisos del recorrido

[← Recorrido completo](README.md)

Usuarios de prueba de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).
Los permisos tienen la forma `perm:{servicio}:{recurso}:{acción}`; `all` vale como comodín. El permiso dice
*qué* puede hacer el usuario; la membresía en una empresa (Operational Context) dice *dónde*: fuera de sus
empresas recibe `404`.

## Usuarios de prueba y empresas del recorrido

- Empresa A: `admin.test`, `compras.test`, `ventas.test`, `supervisor.test` (asignados a la sucursal A1) y `consulta.test` (sin sucursal).
- Empresa B: `reportes.test` e `inventario.test` (este último asignado a la sucursal B1). `admin.test` no se registra en B.
- El vendedor no ve costo ni margen; `supervisor.test` sí (`perm:sales:sales:read-profitability`).
- Las cuentas de servicio (`sales-service`, `purchase-service`) no compran ni venden: reciben `403`.

| Usuario | Grupo | Permisos del grupo |
| --- | --- | --- |
| `admin.test` | `administradores` | `perm:all:all:all` |
| `compras.test` | `compras` | `perm:commercial-relationship:all:read`<br>`perm:geography:all:read`<br>`perm:operational-context:all:read`<br>`perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:organization_business_sectors:read`<br>… (14 en total) |
| `ventas.test` | `ventas` | `perm:commercial-relationship:all:read`<br>`perm:geography:all:read`<br>`perm:operational-context:all:read`<br>`perm:party-identity:global_business_sectors:read`<br>`perm:party-identity:identification_type_rules:read`<br>`perm:party-identity:organization_business_sectors:read`<br>… (17 en total) |
| `supervisor.test` | `supervisores` | `perm:all:all:create`<br>`perm:all:all:read`<br>`perm:all:all:update`<br>`perm:sales:sales:read-profitability` |
| `consulta.test` | `consulta` | `perm:commercial-relationship:company_customers:read`<br>`perm:commercial-relationship:company_product_presentations:read`<br>`perm:commercial-relationship:company_products:read`<br>`perm:commercial-relationship:company_suppliers:read`<br>`perm:commercial-relationship:customer_credit_profiles:read`<br>`perm:commercial-relationship:customer_payment_conditions:read`<br>… (54 en total) |
| `reportes.test` | `reportes` | `perm:commercial-relationship:company_customers:read`<br>`perm:commercial-relationship:company_product_presentations:read`<br>`perm:commercial-relationship:company_products:read`<br>`perm:commercial-relationship:company_suppliers:read`<br>`perm:commercial-relationship:customer_credit_profiles:read`<br>`perm:commercial-relationship:customer_payment_conditions:read`<br>… (54 en total) |
| `inventario.test` | `inventario` | `perm:commercial-relationship:company_products:read`<br>`perm:geography:all:read`<br>`perm:inventory:adjustments:create`<br>`perm:inventory:adjustments:read`<br>`perm:inventory:balances:read`<br>`perm:inventory:company-policies:read`<br>… (13 en total) |

## Cómo obtener el token

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=compras.test -d "password=$KEYCLOAK_TEST_USER_PASSWORD" | jq -r .access_token)
```

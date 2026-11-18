# Usuarios y permisos del recorrido

[← Recorrido completo](README.md)

Usuarios de prueba de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).
Los permisos tienen la forma `perm:{servicio}:{recurso}:{acción}`; `all` vale como comodín. El permiso dice
*qué* puede hacer el usuario; la membresía en una empresa (Operational Context) dice *dónde*: fuera de sus
empresas recibe `404`.

## Usuarios de prueba y empresas del recorrido

- Empresa A: `admin.sio` (SuperAdmin) y `operario.dao` (Empleado), asignados a la sucursal A1.
- Empresa B: `admin.dao` (Admin), asignado a la sucursal B1. `admin.sio` no se registra en B.
- El Empleado (`operario.dao`) no ve costo ni margen; `admin.sio` sí (`perm:sales:sales:read-profitability`).
- Las cuentas de servicio (`sales-service`, `purchase-service`) no compran ni venden: reciben `403`.

| Usuario | Grupo | Permisos del grupo |
| --- | --- | --- |
| `admin.sio` | `superadmin` | `perm:all:all:all` |
| `admin.dao` | `admin` | `perm:audit:audit-events:read`<br>`perm:business-reporting:purchases:read`<br>`perm:business-reporting:sales_by_branch:read`<br>`perm:business-reporting:stock_evolution:read`<br>`perm:business-reporting:top_selling_products:read`<br>`perm:commercial-relationship:all:create`<br>… (49 en total) |
| `operario.dao` | `empleado` | `perm:business-reporting:purchases:read`<br>`perm:business-reporting:stock_evolution:read`<br>`perm:business-reporting:top_selling_products:read`<br>`perm:commercial-relationship:company_customers:create`<br>`perm:commercial-relationship:company_customers:read`<br>`perm:commercial-relationship:company_product_presentations:read`<br>… (80 en total) |

## Cómo obtener el token

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=operario.dao -d "password=$KEYCLOAK_TEST_USER_PASSWORD" | jq -r .access_token)
```

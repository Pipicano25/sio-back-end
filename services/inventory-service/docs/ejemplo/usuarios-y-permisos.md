# Usuarios y permisos de inventory-service

Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

## Cómo se evalúan los permisos

- Cada URL exige un permiso `perm:inventory:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.
- **Aplicar y revertir** (`perm:inventory:entries:create`, `perm:inventory:outputs:create`) exige además un token de **cuenta de servicio**: ningún usuario humano mueve inventario, aunque tenga el permiso por comodín. El reverso usa el permiso del tipo original y exige `company_id`.
- **Consultar** (`perm:inventory:balances:read`, `perm:inventory:movements:read`) exige además la membresía `ACTIVE` en la empresa y `perm:operational-context:application_users:read`, que pide Operational Context al resolver el acceso. No se exige asignación a la sucursal.
- **Lectura técnica** (`perm:inventory:platform:lookup`): una cuenta de servicio con lectura y esta capacidad consulta sin membresía (Sales antes de confirmar una venta).
- **Ajustes y conteos** (`perm:inventory:adjustments:create`, `perm:inventory:counts:create`, 013) exigen un **usuario humano** miembro `ACTIVE` y con asignación `ACTIVE` a la sucursal; una cuenta de servicio recibe `403` aunque tenga el permiso. Las **políticas** (`perm:inventory:company-policies:update`, `perm:inventory:product-policies:update`) exigen un usuario humano miembro de la empresa.
- **Lecturas de 013** (`adjustments:read`, `counts:read`, `company-policies:read`, `product-policies:read`, `valuation:read`): mismo alcance por empresa que las consultas de stock.
- El grupo `inventario` tiene las lecturas de inventario y registra ajustes y conteos; `administradores` y `supervisores` lo obtienen todo por comodín (las políticas solo ellos). Ningún grupo puede aplicar operaciones.

## Usuarios de prueba

| Usuario | Grupo | Stock y kardex | Ajustes y conteos | Políticas | Valoración | Aplicar operaciones |
| --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `administradores` | Sí | Sí | Sí | Sí | No (no es cuenta de servicio) |
| `supervisor.test` | `supervisores` | Sí | Sí | Sí | Sí | No (no es cuenta de servicio) |
| `compras.test` | `compras` | No | No | No | No | No (no es cuenta de servicio) |
| `ventas.test` | `ventas` | No | No | No | No | No (no es cuenta de servicio) |
| `inventario.test` | `inventario` | Sí | Sí | No | Sí | No (no es cuenta de servicio) |
| `reportes.test` | `reportes` | No | No | No | No | No (no es cuenta de servicio) |
| `consulta.test` | `consulta` | No | No | No | No | No (no es cuenta de servicio) |
| `inventory-test-operator` | cuenta de servicio | Sí (`platform:lookup`) | No (no es usuario humano) | No (no es usuario humano) | Sí (`platform:lookup`) | Sí (entradas y salidas) |

## Cómo obtener los tokens

Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=inventario.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

Cuenta de servicio de pruebas (secreto en `INVENTORY_TEST_OPERATOR_CLIENT_SECRET`):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=client_credentials -d client_id=inventory-test-operator \
  -d client_secret="$INVENTORY_TEST_OPERATOR_CLIENT_SECRET"
```

## Matriz de URL

| Ejercicio | Paso | URL | Permiso |
| --- | --- | --- | --- |
| 1 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 1 | 2 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 1 | 3 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 1 | 4 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | 2 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 2 | 3 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 2 | 4 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 3 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 3 | 2 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 3 | 3 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 3 | 4 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 3 | 5 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 3 | 6 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 3 | 7 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 4 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 4 | 2 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 4 | 3 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:balances:read` |
| 4 | 4 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances?in_stock_only=true` | `perm:inventory:balances:read` |
| 4 | 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/lookup` | `perm:inventory:balances:read` |
| 4 | 6 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/kardex/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:movements:read` |
| 4 | 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-operations/by-key/d44f0100-0000-4000-8000-000000000001` | `perm:inventory:movements:read` |
| 4 | 8 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances` | `perm:inventory:balances:read` |
| 5 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 5 | 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | 3 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | 4 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments/<AJUSTE>` | `perm:inventory:adjustments:read` |
| 6 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 6 | 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `perm:inventory:counts:create` |
| 6 | 3 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/start` | `perm:inventory:counts:create` |
| 6 | 4 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:counts:create` |
| 6 | 5 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000002` | `perm:inventory:counts:create` |
| 6 | 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/complete` | `perm:inventory:counts:create` |
| 6 | 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>` | `perm:inventory:counts:read` |
| 6 | 8 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `perm:inventory:counts:create` |
| 6 | 9 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/start` | `perm:inventory:counts:create` |
| 6 | 10 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/details/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:counts:create` |
| 6 | 11 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 6 | 12 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete` | `perm:inventory:counts:create` |
| 6 | 13 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/cancel` | `perm:inventory:counts:create` |
| 7 | 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 7 | 2 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 7 | 3 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 7 | 4 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation` | `perm:inventory:valuation:read` |
| 7 | 5 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation/d44d0000-0000-4000-8000-000000000001/layers?include_closed=true` | `perm:inventory:valuation:read` |
| 7 | 6 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-movements/<MOV_SALIDA>/cost-consumptions` | `perm:inventory:valuation:read` |
| 7 | 7 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 7 | 8 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 7 | 9 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 8 | 1 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:read` |
| 8 | 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 8 | 3 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 8 | 4 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 8 | 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `perm:inventory:product-policies:update` |
| 8 | 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `perm:inventory:product-policies:update` |
| 8 | 7 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies/<POLITICA>/deactivate` | `perm:inventory:product-policies:update` |
| 8 | 8 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies?branch_id=d44b0000-0000-4000-8000-000000000001` | `perm:inventory:product-policies:read` |

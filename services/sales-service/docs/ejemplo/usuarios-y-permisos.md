# Usuarios y permisos de sales-service

Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

## Cómo se evalúan los permisos

- Cada URL exige un permiso `perm:sales:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.
- **Todas** las rutas exigen un **usuario humano**: una cuenta de servicio recibe `403` aunque tenga el permiso por comodín (ni siquiera el cliente técnico `sales-service`, que solo consulta dependencias y opera Inventory).
- **Escribir** ventas y líneas, confirmar y anular exige además membresía `ACTIVE` en la empresa y asignación `ACTIVE` a la sucursal de la venta (Operational Context con el token del usuario). **No obvio**: tener `perm:sales:all:update` o `perm:all:all:all` no basta sin la asignación.
- **Secuencias** exigen membresía (no asignación). **Leer** exige permiso y membresía.
- Crear una venta con líneas exige además `perm:sales:sale_details:create`; anular exige `perm:sales:sales:delete` (`supervisor.test` no lo tiene).
- **Rentabilidad** (costo, `cost_known`, margen, porcentaje y `has_unknown_cost`): solo con `perm:sales:sales:read-profitability`, que no abre ninguna ruta por sí solo. **No obvio**: `perm:sales:all:read` no la incluye; el grupo `ventas` no la tiene (C-08); `supervisores` la tiene asignada explícitamente y `administradores` por `perm:all:all:all`. Sin el permiso, los campos se omiten.

## Usuarios de prueba

| Usuario | Grupo | Registrar y confirmar | Anular | Secuencias | Consultar | Ve rentabilidad |
| --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `administradores` | Sí | Sí | Sí | Sí | Sí |
| `supervisor.test` | `supervisores` | Sí | No | Sí | Sí | Sí |
| `compras.test` | `compras` | No | No | No | No | No |
| `ventas.test` | `ventas` | Sí | Sí | Sí | Sí | No |
| `inventario.test` | `inventario` | No | No | No | No | No |
| `reportes.test` | `reportes` | No | No | No | Sí | No |
| `consulta.test` | `consulta` | No | No | No | Sí | No |

Las escrituras requieren además la asignación a la sucursal.

## Cómo obtener los tokens

Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=ventas.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

## Matriz de URL

| Ejercicio | Paso | URL | Permiso |
| --- | --- | --- | --- |
| 1 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 1 | 2 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:read` |
| 1 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 2 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 2 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 4 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 5 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 7 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 2 | 8 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |
| 3 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 3 | 2 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/availability` | `perm:sales:sales:read` |
| 4 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 4 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 4 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 4 | 4 | `PUT /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details/<LINEA>` | `perm:sales:sale_details:update` |
| 4 | 5 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 4 | 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 4 | 7 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 4 | 8 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/operations` | `perm:sales:sale_operations:read` |
| 5 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 5 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 5 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 6 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 6 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 6 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 6 | 4 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |
| 6 | 5 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |
| 6 | 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 6 | 7 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>/confirmation` | `perm:sales:sales:update` |
| 6 | 8 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>` | `perm:sales:sales:read` |
| 7 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 7 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 7 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<BORRADOR>/cancellation` | `perm:sales:sales:delete` |
| 7 | 4 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 7 | 5 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 7 | 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/cancellation` | `perm:sales:sales:delete` |
| 8 | 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 8 | 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 8 | 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 8 | 4 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales?status=CONFIRMED&number=FV-202611-000001` | `perm:sales:sales:read` |
| 8 | 5 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000099/sales/<VENTA>` | `perm:sales:sales:read` |

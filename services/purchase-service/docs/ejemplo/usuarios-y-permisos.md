# Usuarios y permisos de purchase-service

Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

## Cómo se evalúan los permisos

- Cada URL exige un permiso `perm:purchase:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.
- **Todas** las rutas exigen un **usuario humano**: una cuenta de servicio recibe `403` aunque tenga el permiso por comodín (ni siquiera el cliente técnico `purchase-service`, que solo consulta dependencias y opera Inventory).
- **Escribir** compras, líneas, hitos, confirmar y anular exige además membresía `ACTIVE` en la empresa y asignación `ACTIVE` a la sucursal de la compra (Operational Context con el token del usuario). **No obvio**: tener `perm:purchase:all:all` o `perm:all:all:all` no basta sin la asignación.
- **Secuencias** exigen membresía (no asignación). **Leer** exige permiso y membresía.
- Crear una compra con líneas exige además `perm:purchase:purchase_details:create`; anular exige `perm:purchase:purchases:delete` (`supervisor.test` no lo tiene).

## Usuarios de prueba

| Usuario | Grupo | Registrar y confirmar | Anular | Hitos | Secuencias | Consultar |
| --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `administradores` | Sí | Sí | Sí | Sí | Sí |
| `supervisor.test` | `supervisores` | Sí | No | Sí | Sí | Sí |
| `compras.test` | `compras` | Sí | Sí | Sí | Sí | Sí |
| `ventas.test` | `ventas` | No | No | No | No | No |
| `inventario.test` | `inventario` | No | No | No | No | No |
| `reportes.test` | `reportes` | No | No | No | No | Sí |
| `consulta.test` | `consulta` | No | No | No | No | Sí |

Las escrituras requieren además la asignación a la sucursal.

## Cómo obtener los tokens

Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=compras.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

## Matriz de URL

| Ejercicio | Paso | URL | Permiso |
| --- | --- | --- | --- |
| 1 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 1 | 2 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:read` |
| 1 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 2 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 2 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 2 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 2 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 2 | 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 2 | 7 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 2 | 8 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 2 | 9 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>` | `perm:purchase:purchases:read` |
| 3 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 3 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 3 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 3 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 3 | 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 3 | 7 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations` | `perm:purchase:purchase_operations:read` |
| 4 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 4 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 4 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<NOVIEMBRE>/confirmation` | `perm:purchase:purchases:update` |
| 4 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 4 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<OCTUBRE>/confirmation` | `perm:purchase:purchases:update` |
| 5 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 5 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<BORRADOR>/cancellation` | `perm:purchase:purchases:delete` |
| 5 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/confirmation` | `perm:purchase:purchases:update` |
| 5 | 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/cancellation` | `perm:purchase:purchases:delete` |
| 5 | 7 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | 8 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 5 | 9 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 5 | 10 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/cancellation` | `perm:purchase:purchases:delete` |
| 5 | 11 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | 12 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/confirmation` | `perm:purchase:purchases:update` |
| 5 | 13 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/receipt` | `perm:purchase:purchases:update` |
| 5 | 14 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation` | `perm:purchase:purchases:delete` |
| 6 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 6 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 6 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 7 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 6 | 8 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 9 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 6 | 10 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 11 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | 12 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:read` |
| 7 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 7 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 7 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 7 | 4 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases?status=CONFIRMED&number=CP-202611-000001` | `perm:purchase:purchases:read` |
| 7 | 5 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000099/purchases/<COMPRA>` | `perm:purchase:purchases:read` |
| 8 | 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 8 | 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 8 | 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 8 | 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 8 | 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `perm:purchase:purchase_details:create` |
| 8 | 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |

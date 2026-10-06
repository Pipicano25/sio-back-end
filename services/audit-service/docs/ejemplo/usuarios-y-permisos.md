# Usuarios y permisos de audit-service

Generado por `tests/examples/test_examples.py` a partir de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

## Cómo se evalúan los permisos

- Cada URL exige un permiso `perm:audit:{recurso}:{accion}` (`sio-auth`). El `403` nunca revela el permiso exigido; queda solo en el log del servidor con el `trace_id`.
- **Registrar** (`perm:audit:audit-events:create`) exige además un token de **cuenta de servicio**: ningún usuario humano registra eventos, aunque tenga el permiso por comodín.
- **Auditoría de una empresa** (`perm:audit:audit-events:read`) exige además la membresía `ACTIVE` en la empresa y `perm:operational-context:application_users:read`, que pide Operational Context al resolver el acceso. Ser miembro de una empresa **no** da acceso a su auditoría (FR-037).
- **Eventos de plataforma** (`perm:audit:platform-events:read`): permiso independiente, sin membresía. El permiso de empresa no da acceso a estos eventos y viceversa.
- Ningún grupo recibe permisos de auditoría explícitos: `administradores` y `supervisores` los obtienen por comodín. Otro grupo se habilita asignándolos en Keycloak, sin cambios de código.

## Usuarios de prueba

| Usuario | Grupo | Lectura de empresa | Lectura de plataforma | Registro |
| --- | --- | --- | --- | --- |
| `admin.test` | `administradores` | Sí | Sí | No (no es cuenta de servicio) |
| `supervisor.test` | `supervisores` | Sí | Sí | No (no es cuenta de servicio) |
| `compras.test` | `compras` | No | No | No (no es cuenta de servicio) |
| `ventas.test` | `ventas` | No | No | No (no es cuenta de servicio) |
| `inventario.test` | `inventario` | No | No | No (no es cuenta de servicio) |
| `reportes.test` | `reportes` | No | No | No (no es cuenta de servicio) |
| `consulta.test` | `consulta` | No | No | No (no es cuenta de servicio) |
| `audit-test-emitter` | cuenta de servicio | No | No | Sí (`perm:audit:audit-events:create`) |

## Cómo obtener los tokens

Usuarios (contraseña en la variable `KEYCLOAK_TEST_USER_PASSWORD`, nunca en estos documentos):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=password -d client_id=sio-web -d scope=openid \
  -d username=supervisor.test -d password="$KEYCLOAK_TEST_USER_PASSWORD"
```

Cuenta de servicio de pruebas (secreto en `AUDIT_TEST_EMITTER_CLIENT_SECRET`):

```bash
curl -s -X POST http://localhost:8081/realms/sio/protocol/openid-connect/token \
  -d grant_type=client_credentials -d client_id=audit-test-emitter \
  -d client_secret="$AUDIT_TEST_EMITTER_CLIENT_SECRET"
```

## Matriz de URL

| Ejercicio | Paso | URL | Permiso |
| --- | --- | --- | --- |
| 1 | 1 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 1 | 2 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 1 | 3 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 1 | 4 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 1 | 5 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 1 | 6 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 1 | 7 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 2 | 1 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 2 | 2 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events` | `perm:audit:audit-events:read` |
| 2 | 3 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events?result=FAILURE&entity_type=PriceListItem` | `perm:audit:audit-events:read` |
| 2 | 4 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_CREACION>` | `perm:audit:audit-events:read` |
| 2 | 5 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/entity-history/PriceListItem/b22e0000-0000-4000-8000-000000000010` | `perm:audit:audit-events:read` |
| 2 | 6 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events` | `perm:audit:audit-events:read` |
| 3 | 1 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 3 | 2 | `GET /api/v1/platform-audit-events` | `perm:audit:platform-events:read` |
| 3 | 3 | `GET /api/v1/platform-entity-history/GlobalProduct/b22e0000-0000-4000-8000-000000000030` | `perm:audit:platform-events:read` |
| 3 | 4 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_PLATAFORMA>` | `perm:audit:audit-events:read` |

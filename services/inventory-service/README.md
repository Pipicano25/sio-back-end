# inventory-service

Microservicio de inventario de SIO, **Fase A: motor central** (`specs/012-inventory-core/`). Es la
única fuente de verdad de cuánto hay de cada producto empresarial en cada sucursal y de cómo se llegó
a ese saldo.

## Responsabilidad y entidades propias

| Tabla | Qué guarda |
| --- | --- |
| `inventory_balances` | Saldo vigente por empresa, sucursal y producto (en unidad base). Nunca negativo; nunca se elimina. `version` = número de movimientos aplicados |
| `inventory_movements` | Kardex **inmutable**: cada cambio de saldo con saldo anterior, cantidad, saldo nuevo, `balance_sequence` (correlativo por saldo, sin huecos), documento y línea de origen, usuario operativo y flujo |
| `inventory_operations` | Una fila por operación aplicada o reverso: clave de idempotencia, cliente que la usó, huella `request_hash` y enlace al reverso. Inmutable |
| `audit_outbox` | Outbox de auditoría de `libs/sio-audit` |

Fuera de esta fase (bloque 13 del roadmap): ajustes, conteos, políticas, valoración (FIFO / promedio
ponderado) y lotes. Las entradas aceptan un `unit_cost` opcional que solo se guarda.

## Dependencias

| Servicio | Uso | Identidad |
| --- | --- | --- |
| Keycloak (B) | Validación de tokens (`sio-auth`) y token `client_credentials` propio | Cliente `inventory-service` |
| Operational Context (C) | Al aplicar: sucursal (`branches/{id}`) y usuario operativo (`application-users/{id}`). Al consultar: `operational-access?company_id=` | Técnica con `platform:lookup` / token del usuario |
| Commercial Relationship (C) | Al aplicar: productos por lote (`company-products/batch-lookup`): de la empresa, `ACTIVE` y con `inventory_control_enabled` | Técnica con `platform:lookup` |
| Audit | Eventos por `inventory-audit-outbox-worker` (sin llamada síncrona; Audit caído no bloquea) | Cliente `inventory-service` con `perm:audit:audit-events:create` |

Cualquier dependencia no disponible responde `503` con `dependency` (`operational-context`,
`commercial-relationship`, `database`) **sin aplicar nada**. Contratos:
`specs/012-inventory-core/contracts/` (`rest-api.md`, `errors.md`, `inventory-provider.md`,
`dependencies.md`).

## Reglas principales

- **Solo cuentas de servicio aplican operaciones** (Purchase, Sales y el cliente de pruebas
  `inventory-test-operator`); un usuario humano recibe `403` aunque tenga el permiso por comodín.
- **Todo o nada**: una operación de 1 a 100 líneas se aplica completa o no se aplica.
- **Saldo nunca negativo**: una salida (o el reverso de una entrada) sin saldo suficiente se rechaza
  con `409 INSUFFICIENT_STOCK` y `shortages[{index, company_product_id, available, requested}]`.
- **Concurrencia**: los saldos se bloquean con `SELECT … FOR UPDATE` en orden de `company_product_id`;
  `balance_sequence = version + 1` se asigna con la fila bloqueada y en la misma transacción. No se usa
  ninguna `SEQUENCE` de PostgreSQL (dejaría huecos tras un `ROLLBACK`). `lock_timeout`
  (`INVENTORY_LOCK_TIMEOUT_SECONDS`) agotado → `503 database` reintentable.
- **Idempotencia**: la clave de operación es única y queda ligada al cliente que la usó. Misma clave,
  mismo cliente y misma solicitud (misma `request_hash`) → `200` con el resultado original **sin
  consultar dependencias**; cualquier diferencia → `409 OPERATION_KEY_CONFLICT`. Un rechazo no queda
  registrado y se puede reintentar.
- **Reversos**: de la operación completa, una sola vez, con clave propia, motivo y **`company_id`
  obligatorio**; la operación se busca solo dentro de esa empresa (`404` si no existe ahí). No se
  revalidan sucursal ni producto; el usuario operativo sí (existe y es de la empresa, aunque esté
  inactivo). Un reverso no se revierte.
- **Inmutabilidad en la base**: triggers rechazan `UPDATE`, `DELETE` y `TRUNCATE` sobre movimientos y
  operaciones, y `DELETE`/`TRUNCATE` sobre saldos, también en sesiones manuales.
- **Auditoría**: un evento por operación aplicada o revertida (`APPLY_INVENTORY_ENTRY`,
  `APPLY_INVENTORY_OUTPUT`, `REVERSE_INVENTORY_ENTRY`, `REVERSE_INVENTORY_OUTPUT`) escrito en
  `audit_outbox` en la misma transacción. Los rechazos solo quedan en el log (clave, código,
  `trace_id`).

## Permisos

| Permiso | Uso | Quién |
| --- | --- | --- |
| `perm:inventory:entries:create` | Entradas de compra y sus reversos | Cuentas de servicio (Purchase, `inventory-test-operator`) |
| `perm:inventory:outputs:create` | Salidas de venta y sus reversos | Cuentas de servicio (Sales, `inventory-test-operator`) |
| `perm:inventory:balances:read` | Saldo, stock de sucursal, saldos por lote | `inventario`, `administradores` y `supervisores` (comodín) |
| `perm:inventory:movements:read` | Kardex y operaciones | Igual que el anterior |
| `perm:inventory:platform:lookup` | Lectura técnica sin membresía | Solo cuentas de servicio consumidoras |

Consultar exige además membresía `ACTIVE` en la empresa (y `perm:operational-context:application_users:read`,
que pide Operational Context); no exige asignación a la sucursal. Ejercicios y matriz de permisos:
[`docs/ejemplo/`](docs/ejemplo/README.md).

## Configuración

Variables en [`.env.example`](.env.example) (copiar a `.env`, que no se versiona). Sin modos de
entorno: las pruebas inyectan dobles por DI.

## Arranque

Entorno integrado (desde la raíz del repositorio; el proyecto `sio` y sus dependencias levantados):

```bash
docker compose -p inventory-service -f infrastructure/services/inventory-service.yaml --env-file infrastructure/.env up -d --build
docker exec sio-inventory-service alembic upgrade head
curl -s localhost:8109/health/ready
```

El contenedor `inventory-audit-outbox-worker` usa la misma imagen y base (`python -m sio_audit.worker`);
si arranca antes de la migración registra un error y se recupera solo en el ciclo siguiente.

Entorno independiente (desde `services/inventory-service/`):

```bash
docker compose --file ../../infrastructure/services/inventory-service.yaml --env-file ../../infrastructure/.env --profile test up -d inventory-test-db
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[test]" -e ../../libs/sio-auth -e ../../libs/sio-audit
alembic upgrade head
```

## Pruebas

```bash
pytest                                       # unitarias, contrato, API, concurrencia, ejemplos
pytest -m performance -o addopts=""          # 1 000 000 de movimientos (SC-007)
pytest -m integration -o addopts=""          # Keycloak, OC, CR, Audit y base reales
INVENTORY_EXAMPLES_WRITE=1 pytest tests/examples   # regenera docs/ejemplo/
```

Las pruebas de integración leen `KEYCLOAK_TEST_USER_PASSWORD` e `INVENTORY_TEST_OPERATOR_CLIENT_SECRET`
del entorno o de `infrastructure/.env`, crean datos ficticios con los servicios reales y detienen y
vuelven a iniciar temporalmente Operational Context, Commercial Relationship, Audit y la base.

## Datos iniciales y entorno

No hay datos iniciales (`seed`): los saldos nacen de las entradas. El servicio sigue la práctica
vigente del repositorio de un único proyecto Compose en `infrastructure/services/`; la reconciliación
del Principio IV ("`docker-compose.yml` propio") está pendiente por separado (G1).

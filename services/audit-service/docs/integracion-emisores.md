# Guía normativa: integrar un servicio emisor con Audit

**Única fuente normativa vigente** para incorporar auditoría en un microservicio de SIO (FR-075,
FR-078 de `specs/011-audit-core`). Las palabras DEBE / NO DEBE tienen el sentido de la Constitución.
La política de redacción reutilizable es la del [`README.md` de `libs/sio-audit`](../../../libs/sio-audit/README.md).

**Aplica a**: todo microservicio construido después de `AUDIT-CORE READY` y a la feature transversal
"Auditoría de servicios existentes". Party Identity, Product Catalog, Operational Context y Commercial
Relationship **no** están auditados hasta completar esa feature.

## 1. Qué DEBE definir la Spec del emisor desde el inicio

1. Las acciones que generan eventos (`action` + `entity_type`) y cuándo se emite `FAILURE`.
2. Qué valores van en `previous_values` / `new_values` (solo lo que el contrato admite; E-01 no
   autoriza replicar datos arbitrarios entre servicios).
3. Su tabla `audit_outbox` (categoría Outbox, metadatos citando D26) y su migración.
4. Su `audit-outbox-worker` como contenedor propio en su archivo de compose.
5. Su configuración por ambiente (sección 5) en su `.env.example`.
6. Su cliente técnico en la plantilla del realm con `perm:audit:audit-events:create`.
7. Sus pruebas de entrega, reintento, idempotencia y redacción (sección 7).

## 2. Registrar el evento (Transactional Outbox)

- DEBE usarse `sio_audit.outbox.record_audit_event(session, event)` dentro de la **misma
  transacción** que la operación de negocio cuando la acción modifica datos: el evento existe si y
  solo si la operación se confirmó. Para un `FAILURE` (la operación se revierte) se registra en una
  transacción propia.
- `record_audit_event` redacta, valida el contrato, asigna `event_id` si falta y escribe en la outbox.
  Un evento inválido lanza `InvalidAuditEventError`: es un error de programación del emisor y DEBE
  detectarse en sus pruebas.
- El emisor NO DEBE llamar a Audit dentro de la solicitud del usuario y su operación NO DEBE fallar
  porque Audit no esté disponible.
- Los valores sensibles NO DEBEN llegar a la outbox, a Audit ni a los logs.

## 3. Entregar (`audit-outbox-worker`)

- Proceso independiente `python -m sio_audit.worker`, en un contenedor propio con **la misma imagen,
  configuración y base** que la API del emisor.
- `restart: unless-stopped`, `healthcheck` con `python -m sio_audit.worker --check`, dependencia de la
  salud de su base.
- Reintenta **indefinidamente**; marca `SENT` solo con confirmación de Audit; retoma los pendientes
  tras cualquier reinicio; nunca borra filas. La outbox en PostgreSQL es la **única** fuente de
  recuperación (logs y latido son solo diagnóstico).
- Rechazo permanente (`409`, `422`, `401` tras renovar el token, `403`): queda en logs con el
  `event_id` y el `code`, se reintenta con el intervalo máximo y no bloquea a los demás eventos.

## 4. Compose

Plantilla: [`libs/sio-audit/compose/audit-outbox-worker.example.yaml`](../../../libs/sio-audit/compose/audit-outbox-worker.example.yaml).

## 5. Variables de entorno

| Variable | Defecto | Uso |
| --- | --- | --- |
| `DATABASE_URL` | — | Base del emisor |
| `AUDIT_SERVICE_BASE_URL` | — | `http://audit-service:8000/api/v1` |
| `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM` | — | Token `client_credentials` |
| `AUDIT_CLIENT_ID`, `AUDIT_CLIENT_SECRET` | — | Cliente técnico del emisor; secreto solo en `.env` |
| `AUDIT_OUTBOX_POLL_INTERVAL_SECONDS` | `2` | Sondeo |
| `AUDIT_OUTBOX_HTTP_TIMEOUT_SECONDS` | `5` | Tiempo de espera HTTP |
| `AUDIT_OUTBOX_BACKOFF_INITIAL_SECONDS` | `1` | Primer reintento |
| `AUDIT_OUTBOX_BACKOFF_FACTOR` | `2` | Factor exponencial |
| `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` | `300` | Tope y espera de rechazos permanentes |
| `AUDIT_OUTBOX_BATCH_SIZE` | `100` | 1–100 |

## 6. Identidad técnica

El cliente del emisor usa `client_credentials` (D5) con `perm:audit:audit-events:create`. Audit fija
`source_service` = `client_id` del token y `created_by` = `sub`: el cuerpo NO DEBE incluirlos (`422`).
Un token de usuario humano no puede registrar eventos (`403`).

## 7. Ejemplo de integración completo (ejecutado automáticamente)

Este ejemplo lo ejecuta la prueba de integración de la librería
(`libs/sio-audit/tests/integration/test_worker_against_audit.py::test_integration_guide_example`)
contra Audit y Keycloak reales (SC-008):

```python
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sio_audit.worker import Worker, WorkerSettings, run_once

company_id = uuid4()
purchase_id = uuid4()

with Session(engine) as session:                      # transacción de negocio del emisor
    # ... confirmar la compra ...
    event_id = record_audit_event(session, AuditEvent(
        event_id=None,
        company_id=company_id,
        action="CONFIRM",
        entity_type="Purchase",
        entity_id=purchase_id,
        result="SUCCESS",
        occurred_at=datetime.now(UTC),
        previous_values={"status": "DRAFT"},
        new_values={"status": "CONFIRMED", "api_key": "nunca-se-guarda"},
    ))
    session.commit()

settings = WorkerSettings.from_env()                   # variables de la sección 5
worker = Worker(settings, engine=engine)
run_once(worker.engine, worker.client, settings)       # el contenedor lo hace en bucle
# Resultado: la fila de audit_outbox queda SENT y Audit tiene el evento con
# new_values.api_key = "***" y redacted_paths = ["new_values.api_key"].
```

## 8. Pruebas mínimas del emisor

- La operación de negocio y el evento se confirman o revierten juntos.
- La operación termina bien con Audit detenido; al volver, el evento se entrega una sola vez.
- Un valor sensible no aparece en la outbox ni en los logs.
- Reenvío tras respuesta perdida → `ALREADY_EXISTS`, sin duplicado.
- Un evento rechazado no bloquea a los demás.

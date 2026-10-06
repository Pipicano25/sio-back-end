# sio-audit

Librería compartida de auditoría de SIO (versión **0.1.0**; feature `011-audit-core`). No contiene
lógica de dominio de ningún microservicio (Constitución, Principio I).

| Módulo | Uso |
| --- | --- |
| `sio_audit.redaction` | **Política única de redacción** de valores sensibles (fuente normativa, ver abajo). |
| `sio_audit.event` | Contrato del evento v1, validación, forma canónica y huella de idempotencia. |
| `sio_audit.outbox` | Tabla `audit_outbox` del emisor y `record_audit_event` dentro de su transacción. |
| `sio_audit.worker` | Proceso `audit-outbox-worker` (`python -m sio_audit.worker`). |

La usan **audit-service** (redacción y contrato al recibir) y **todo servicio emisor** (outbox y
worker). La guía normativa para integrar un servicio emisor es
[`services/audit-service/docs/integracion-emisores.md`](../../services/audit-service/docs/integracion-emisores.md).

## Política de redacción — versión 1 (normativa, FR-017a)

- Una clave es **sensible** si su nombre, en minúsculas y sin `-` ni `_`, es **exactamente** uno de:
  `password`, `passwd`, `secret`, `clientsecret`, `token`, `accesstoken`, `refreshtoken`,
  `idtoken`, `authorization`, `apikey`, `credential`, `credentials`, `privatekey`.
  (Ejemplos que coinciden: `Password`, `client_secret`, `api-key`, `accessToken`. Ejemplos que **no**:
  `token_count`, `password_policy_id`.)
- Se busca en `previous_values` y `new_values`, en objetos y listas, hasta 10 niveles.
- El valor completo (escalar, objeto o lista) se reemplaza por `"***"`.
- Cada ruta ocultada se agrega a `redacted_paths` (`.` para objetos, `[i]` para listas, p. ej.
  `new_values.contacts[0].api_key`), ordenadas y sin duplicados.
- Se aplica **en el emisor** antes de escribir en la outbox y **otra vez en Audit** al recibir.
- Nunca rechaza el evento. Los valores originales no se guardan en la outbox ni en Audit, no viajan
  a Audit y no se escriben en logs.
- Validación de tamaño, idempotencia y persistencia usan siempre el contenido ya redactado.
- Ampliar la lista es un cambio de versión de esta librería (`POLICY_VERSION`) y del contrato del
  evento; los emisores no mantienen listas propias.

## Contrato del evento v1

Campos que envía el emisor: `event_id` (UUID, obligatorio), `company_id`, `branch_id` (exige
`company_id`), `application_user_id`, `keycloak_user_id`, `username_snapshot` (≤ 160),
`action` (obligatorio, `^[A-Z][A-Z0-9_]{0,49}$`), `entity_type` (obligatorio, `PascalCase` ≤ 60),
`entity_id`, `previous_values` / `new_values` (objetos JSON ≤ 64 KB y ≤ 10 niveles tras la
redacción), `redacted_paths`, `result` (`SUCCESS` / `FAILURE`, obligatorio), `reason` (≤ 2000,
opcional también con `FAILURE`), `request_id`, `correlation_id`, `occurred_at` (con zona horaria,
obligatorio). Audit agrega `id`, `source_service` (cliente del token), `recorded_at` y `created_by`.
El formato es independiente del transporte (hoy HTTP).

## Adopción en un servicio emisor

1. Dependencia en el `pyproject.toml` del emisor: `"sio-audit @ file:../../libs/sio-audit"` (≥ 0.1.0)
   y copia de `libs/sio-audit` en su `Dockerfile`.
2. Migración Alembic del emisor:

   ```python
   from sio_audit.outbox import create_audit_outbox_table, drop_audit_outbox_table

   def upgrade() -> None:
       create_audit_outbox_table(op)

   def downgrade() -> None:
       drop_audit_outbox_table(op)
   ```

3. En el caso de uso, dentro de la misma transacción de negocio:

   ```python
   from sio_audit.event import AuditEvent
   from sio_audit.outbox import record_audit_event

   record_audit_event(session, AuditEvent(event_id=None, company_id=..., action="CONFIRM",
       entity_type="Purchase", entity_id=purchase.id, result="SUCCESS",
       occurred_at=now, previous_values=..., new_values=...))
   session.commit()   # el evento existe si y solo si la operación se confirmó
   ```

4. Contenedor del worker: [`compose/audit-outbox-worker.example.yaml`](compose/audit-outbox-worker.example.yaml).

## Worker

`python -m sio_audit.worker` sondea la outbox, envía lotes a `POST {AUDIT}/audit-events/batch`, marca
`SENT` solo con confirmación (`CREATED` / `ALREADY_EXISTS`), reintenta indefinidamente con backoff
exponencial con tope y jitter ±10 %, retoma los pendientes tras cualquier reinicio
(`FOR UPDATE SKIP LOCKED` permite varias réplicas) y nunca borra filas. Un rechazo permanente
(`409`, `422`, `401` tras renovar el token, `403`) se registra en logs con el `event_id` y se
reintenta con el intervalo máximo sin bloquear a los demás. `python -m sio_audit.worker --check`
devuelve `0` si el latido es reciente (healthcheck). Configuración inválida → código `2`.

| Variable | Defecto | Uso |
| --- | --- | --- |
| `DATABASE_URL` | — | Base del emisor con `audit_outbox` |
| `AUDIT_SERVICE_BASE_URL` | — | p. ej. `http://audit-service:8000/api/v1` |
| `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM` | — | Token `client_credentials` |
| `AUDIT_CLIENT_ID`, `AUDIT_CLIENT_SECRET` | — | Cliente técnico del emisor (secreto solo en `.env`) |
| `AUDIT_OUTBOX_POLL_INTERVAL_SECONDS` | `2` | Sondeo |
| `AUDIT_OUTBOX_HTTP_TIMEOUT_SECONDS` | `5` | Tiempo de espera HTTP |
| `AUDIT_OUTBOX_BACKOFF_INITIAL_SECONDS` | `1` | Primer reintento |
| `AUDIT_OUTBOX_BACKOFF_FACTOR` | `2` | Factor exponencial (≥ 1) |
| `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` | `300` | Tope y espera de rechazos permanentes |
| `AUDIT_OUTBOX_BATCH_SIZE` | `100` | 1–100 |
| `AUDIT_OUTBOX_HEARTBEAT_FILE` | `<tmp>/sio-audit-worker.heartbeat` | Latido del healthcheck |

Logger `sio_audit`: registra `event_id`, estado HTTP, `code`, intentos; nunca valores ni el token.

## Pruebas

```bash
cd libs/sio-audit
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[test]"
# base de pruebas (la de audit-service, perfil test):
docker compose --file ../../infrastructure/services/audit-service.yaml --env-file ../../infrastructure/.env --profile test up -d audit-test-db
pytest                      # unitarias y de contrato (outbox y worker con httpx.MockTransport)
pytest -m integration       # contra audit-service y Keycloak reales (cliente audit-test-emitter)
```

`SIO_AUDIT_TEST_DATABASE_URL` cambia la base de pruebas (debe contener `test` en su nombre). Las
pruebas de integración leen `AUDIT_TEST_EMITTER_CLIENT_SECRET` del entorno o de
`infrastructure/.env`.

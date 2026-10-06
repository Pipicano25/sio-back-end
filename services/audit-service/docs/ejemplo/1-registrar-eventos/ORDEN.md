# Ejercicio 1: Registrar eventos de auditoría

Un microservicio emisor registra eventos con su identidad técnica: un evento, su reenvío idempotente, un conflicto de `event_id`, la redacción de un secreto, un lote atómico y los rechazos de validación.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-registrar-un-evento.md](01-registrar-un-evento.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `201` |
| 2 | [02-reenviar-el-mismo-evento.md](02-reenviar-el-mismo-evento.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `200` |
| 3 | [03-conflicto-de-event-id.md](03-conflicto-de-event-id.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `409` |
| 4 | [04-redaccion-de-secretos.md](04-redaccion-de-secretos.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `201` |
| 5 | [05-registrar-un-lote.md](05-registrar-un-lote.md) | `POST /api/v1/audit-events/batch` | `audit-test-emitter` (cuenta de servicio) | `200` |
| 6 | [06-lote-con-un-evento-invalido.md](06-lote-con-un-evento-invalido.md) | `POST /api/v1/audit-events/batch` | `audit-test-emitter` (cuenta de servicio) | `422` |
| 7 | [07-campos-que-fija-audit.md](07-campos-que-fija-audit.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `422` |

## Por qué este orden

- Las consultas necesitan eventos registrados: los pasos de registro van primero.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<AUDIT_ID_CAMBIO>` | paso 1 (`id`) | pasos — |

# Ejercicio 2: Consultar la auditoría de una empresa

Un supervisor consulta qué se hizo en su empresa: listado con filtros, un evento por `id` e historial de una entidad. La consulta exige el permiso de lectura de auditoría y la membresía `ACTIVE` en la empresa (Operational Context).

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-registrar-historial.md](01-registrar-historial.md) | `POST /api/v1/audit-events/batch` | `audit-test-emitter` (cuenta de servicio) | `200` |
| 2 | [02-listar-eventos-de-la-empresa.md](02-listar-eventos-de-la-empresa.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events` | `supervisor.test` | `200` |
| 3 | [03-filtrar-intentos-fallidos.md](03-filtrar-intentos-fallidos.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events?result=FAILURE&entity_type=PriceListItem` | `supervisor.test` | `200` |
| 4 | [04-consultar-un-evento.md](04-consultar-un-evento.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_CREACION>` | `supervisor.test` | `200` |
| 5 | [05-historial-de-la-entidad.md](05-historial-de-la-entidad.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/entity-history/PriceListItem/b22e0000-0000-4000-8000-000000000010` | `supervisor.test` | `200` |
| 6 | [06-empresa-sin-membresia.md](06-empresa-sin-membresia.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events` | `supervisor.test` | `404` |

## Por qué este orden

- Las consultas necesitan eventos registrados: los pasos de registro van primero.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<AUDIT_ID_CREACION>` | paso 1 (`items[0].id`) | pasos 4 |

# Ejercicio 3: Eventos de plataforma (sin empresa)

Un cambio en un catálogo global no pertenece a ninguna empresa: se consulta con el permiso independiente `perm:audit:platform-events:read`, sin membresía. El permiso de auditoría de empresa no da acceso a estos eventos.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-registrar-evento-de-plataforma.md](01-registrar-evento-de-plataforma.md) | `POST /api/v1/audit-events` | `audit-test-emitter` (cuenta de servicio) | `201` |
| 2 | [02-listar-eventos-de-plataforma.md](02-listar-eventos-de-plataforma.md) | `GET /api/v1/platform-audit-events` | `supervisor.test` | `200` |
| 3 | [03-historial-del-producto-global.md](03-historial-del-producto-global.md) | `GET /api/v1/platform-entity-history/GlobalProduct/b22e0000-0000-4000-8000-000000000030` | `supervisor.test` | `200` |
| 4 | [04-evento-de-plataforma-por-ruta-de-empresa.md](04-evento-de-plataforma-por-ruta-de-empresa.md) | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_PLATAFORMA>` | `supervisor.test` | `404` |

## Por qué este orden

- Las consultas necesitan eventos registrados: los pasos de registro van primero.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<AUDIT_ID_PLATAFORMA>` | paso 1 (`id`) | pasos 4 |

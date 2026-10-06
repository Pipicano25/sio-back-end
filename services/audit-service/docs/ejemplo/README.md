# Ejercicios de uso de audit-service

Ejercicios paso a paso, ejecutables y validados automáticamente por
`tests/examples/test_examples.py` (Constitución, Principio XXII). Todo lo que hay en estas carpetas,
salvo este archivo, lo genera esa prueba: si cambia un ejercicio, un contrato o la plantilla del
realm, se regenera con `AUDIT_EXAMPLES_WRITE=1 pytest tests/examples`.

| Ejercicio | Qué muestra |
| --- | --- |
| [1-registrar-eventos](1-registrar-eventos/ORDEN.md) | Registro con identidad técnica, reenvío idempotente, conflicto de `event_id`, redacción de secretos, lote atómico y rechazos |
| [2-consultar-auditoria-de-empresa](2-consultar-auditoria-de-empresa/ORDEN.md) | Listado con filtros, evento por `id`, historial de una entidad y aislamiento por empresa |
| [3-eventos-de-plataforma](3-eventos-de-plataforma/ORDEN.md) | Eventos sin empresa con su permiso independiente y separación de alcances |

Permisos, usuarios y cómo obtener los tokens: [usuarios-y-permisos.md](usuarios-y-permisos.md).

## Requisitos para ejecutarlos a mano

- Entorno integrado levantado: Keycloak (reconstruido desde la plantilla del realm), Operational
  Context y audit-service (`http://localhost:8110`).
- Token del usuario de prueba con la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD`, o de la
  cuenta de servicio `audit-test-emitter` con el secreto de `AUDIT_TEST_EMITTER_CLIENT_SECRET`. Nunca
  se escriben contraseñas ni tokens en estos documentos.
- Para las consultas de empresa, el usuario debe ser miembro `ACTIVE` de la empresa en Operational
  Context. En la prueba automática Operational Context se simula (llamada externa, Principio IV) y
  todos los usuarios de prueba son miembros de la empresa ficticia de los ejercicios.
- Ningún servicio emisor real registra eventos todavía: los registros los hace la cuenta de servicio
  de pruebas. Los servicios emisores usan el `audit-outbox-worker` (ver
  [`../integracion-emisores.md`](../integracion-emisores.md)).

## Convenciones

- Datos **ficticios**: no existe una fuente del sistema anterior para eventos de auditoría.
- `<VARIABLE>`: valor guardado de la respuesta de un paso anterior (ver `ORDEN.md`).
- `<asignado por Audit>`: valor que Audit genera en cada ejecución (`id`, `recorded_at`, `trace_id`).
- Cada archivo de paso indica el método y la URL, el JSON de la solicitud, el permiso, qué usuarios
  pueden y cuáles no (y por qué), la justificación de cada decisión y la respuesta esperada.

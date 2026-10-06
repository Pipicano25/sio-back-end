# Audit Service — Domain Map

## Responsabilidad

Conservar el registro oficial e inmutable de las acciones importantes realizadas en SIO: quién hizo
qué, sobre qué entidad, en qué empresa y sucursal, con qué resultado, cuándo y cómo cambiaron los
valores (`specs/011-audit-core/`).

## Entidades propietarias

- `AuditEvent` (`audit_events`): inmutable; eventos **de empresa** (con `company_id`) y **de
  plataforma** (sin `company_id`).

## Referencias externas (`UUID REF`, sin FK; no se validan al registrar)

- `company_id`, `branch_id`, `application_user_id` → Operational Context Service.
- `keycloak_user_id` → Keycloak (actor que originó la acción, informado por el emisor).
- `entity_id` → entidad del servicio emisor (tipo en `entity_type`).
- `source_service` y `created_by` provienen del token de la cuenta de servicio emisora.

## Instantáneas históricas (excepción E-01)

`username_snapshot`, `previous_values` y `new_values` son evidencia del estado observado al momento del
evento: nunca se sincronizan con su fuente ni se usan para conocer el estado actual.

## Dependencias

- Keycloak (validación de tokens).
- Operational Context: `operational-access` (vía propia, token del usuario) solo para consultar
  eventos de empresa.

## Consumidores

- Servicios emisores con `audit-outbox-worker` (`libs/sio-audit`). Inventory, Purchase y Sales desde su
  Spec; los servicios ya cerrados en la feature transversal "Auditoría de servicios existentes".
- Usuarios con `perm:audit:audit-events:read` (empresa) o `perm:audit:platform-events:read`
  (plataforma).

## Ubicación

`services/audit-service/docs/domain-map.md`

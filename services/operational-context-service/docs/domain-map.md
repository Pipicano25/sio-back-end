# Operational Context Service — Domain Map

## Responsabilidad
Administrar el contexto operativo de las empresas, sus sucursales, las personas que operan en ellas
(usuarios operativos) y sus asesores dentro de SIO, y aislar los datos por empresa.

## Entidades propietarias

### Fase A — implementadas (bloque 7 del roadmap, `specs/004-operational-context-core/`)
- `Company` (`companies`): empresa cliente de la plataforma y su sede operativa principal.
- `Branch` (`branches`): sucursales de una empresa.

### Fase B — implementadas (bloque 8 del roadmap, `specs/005-operational-context-users/`)
- `ApplicationUser` (`application_users`): membresía de una persona humana (cuenta de Keycloak +
  `PersonIdentity`) en una empresa. Como máximo una `ACTIVE` por empresa y persona y por empresa y
  cuenta; historial conservado; sin unicidad global de `sub` ni de persona.
- `UserBranch` (`user_branches`): asignación de un usuario operativo a una sucursal de su misma
  empresa (FK compuestas con `company_id`); autor `assigned_by` obligatorio.
- `CompanyAdvisorAssignment` (`company_advisor_assignments`): asesores con vigencia; un solo principal
  vigente; cambio de principal atómico; asignaciones cerradas inmutables.

## Referencias externas principales
- `companies.organization_identity_id` → Party Identity Service (`OrganizationIdentity`): identidad
  legal; la razón social, el nombre comercial y la identificación se consultan allá, no se copian.
- `application_users.person_identity_id` y `company_advisor_assignments.person_identity_id` → Party
  Identity Service (`PersonIdentity`): nombres, documentos y contacto se consultan allá.
- `application_users.keycloak_user_id` → Keycloak (`sub`, texto opaco). Credenciales, sesiones,
  roles y permisos pertenecen a Keycloak; SIO solo lee la cuenta (Admin API) con su cliente técnico.
- `country_id`, `administrative_division_id`, `city_id` (empresa y sucursal) → Geography Service.

Todas son `UUID REF` o `sub` sin FK física. Las FK son internas: `branches.company_id`,
`application_users.company_id`, las FK compuestas de `user_branches` y
`company_advisor_assignments.company_id`.

## Aislamiento por empresa
- El permiso de Keycloak decide **qué** hace el usuario; la membresía `ACTIVE` decide **en qué
  empresas**. Fuera de su alcance, todo recurso responde `404` como si no existiera (DS-06).
- `perm:operational-context:platform:administer`: ver y administrar todas las empresas; registrar,
  inactivar y reactivar empresas (solo `perm:all:all:all` en el realm vigente).
- `perm:operational-context:platform:lookup`: identidades técnicas; lectura por UUID sin membresía y
  acceso operativo de otro usuario; nunca escrituras.

## Consumidores (contratos Provider)
- Commercial Relationship (`company_id`), Inventory (`company_id`, `branch_id`), Purchase y Sales:
  `GET /api/v1/companies/{id}` y `GET /api/v1/branches/{id}`.
- Inventory, Purchase y Sales: `GET /api/v1/operational-access` (acceso operativo con causa estable) y
  `GET /api/v1/application-users/{id}` (usuario operativo de sus documentos).
- Audit: `GET /api/v1/application-users/{id}`.
- Aplicación web: `GET /api/v1/me/operational-context`.
- Party Identity (Fase B, `specs/006-party-identity-complementary/`): `GET /api/v1/operational-access`
  por la vía técnica (cliente `party-identity-service` con `platform:lookup` y `application_users:read`)
  para confirmar perfiles de contacto: guarda `confirmed_by_company_id` y el `application_user_id`.
  Sin recursión: `operational-access` no llama a Party Identity.

## Auditoría

Emisor de Audit desde la feature 016: Eventos de empresa (`company_id`; `branch_id` en sucursales y asignaciones a sucursal). Tabla `audit_outbox` (Outbox, D26) y
contenedor `operational-context-audit-outbox-worker` con el cliente `operational-context-service`. Acciones en
`specs/016-existing-services-audit/contracts/audit-actions.md`.

## Ubicación
`services/operational-context-service/docs/domain-map.md`

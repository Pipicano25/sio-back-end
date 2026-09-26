# Party Identity Service — Domain Map

## Responsabilidad
Administrar la identidad global de personas naturales y organizaciones (quién es cada una),
independientemente del rol que tengan para cada empresa, y las reglas que validan sus números de
identificación.

## Entidades propietarias

### Fase A — implementadas (`specs/003-party-identity-core/`)
- `IdentificationTypeRule` (`identification_type_rules`): activa / histórica; se versiona y se retira, no se elimina.
- `PersonIdentity` (`person_identities`)
- `OrganizationIdentity` (`organization_identities`)

### Fase B — pendientes (bloque 4 del roadmap)
- `PersonContactProfile`
- `OrganizationContactProfile`
- `OrganizationContactPerson`
- `GlobalBusinessSector`
- `OrganizationBusinessSector`
- `OrganizationLegalRepresentative`

## Estados
- `status` = **estado de uso** de personas y organizaciones: `ACTIVE` / `INACTIVE`. Las listas
  muestran solo `ACTIVE` salvo filtro explícito; la consulta por `id` devuelve cualquier estado.
- `verification_status` (personas: `UNVERIFIED` / `VERIFIED` / `SUSPENDED`) y
  `registration_status` (organizaciones, estado legal informativo) son independientes y no
  controlan el uso.

## Referencias externas principales
- País (`country_id`, `identification_country_id`) → Geography Service (`UUID REF`, validado al
  crear o al cambiar país/tipo/número; sin copia de datos).
- `created_by` / `updated_by` → `sub` de Keycloak (texto, sin FK).

## Contrato para consumidores
Consulta por `id` (`GET /api/v1/organization-identities/{id}`, `GET /api/v1/person-identities/{id}`):
`200` con `status`, `404` si no existe
(`specs/003-party-identity-core/contracts/identity-lookup-provider.md`).

## Consumidores principales
- Product Catalog Service (fabricante, en uso)
- Operational Context Service (empresas; asesores en su Fase B)
- Commercial Relationship Service (clientes y proveedores)

Las referencias desde otros servicios son `REF`, nunca FK físicas entre bases de datos.

## Ubicación
`services/party-identity-service/docs/domain-map.md`

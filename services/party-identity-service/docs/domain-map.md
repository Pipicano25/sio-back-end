# Party Identity Service — Domain Map

## Responsabilidad
Administrar la identidad global de personas naturales y organizaciones (quién es cada una),
independientemente del rol que tengan para cada empresa, las reglas que validan sus números de
identificación y la información compartida que los demás servicios consultan sin copiar: contactos,
sector económico y representantes legales.

## Entidades propietarias

### Fase A — implementadas (`specs/003-party-identity-core/`)
- `IdentificationTypeRule` (`identification_type_rules`): activa / histórica; se versiona y se retira, no se elimina.
- `PersonIdentity` (`person_identities`)
- `OrganizationIdentity` (`organization_identities`)

### Fase B — implementadas (`specs/006-party-identity-complementary/`)
- `PersonContactProfile` (`person_contact_profiles`): versionado; una versión vigente por persona.
- `OrganizationContactProfile` (`organization_contact_profiles`): versionado; una vigente por organización.
- `OrganizationContactPerson` (`organization_contact_persons`): activo / inactivo; un principal como máximo.
- `GlobalBusinessSector` (`global_business_sectors`): catálogo jerárquico; CIIU Rev. 4 A.C. (`CIIU_REV4_AC`)
  por `seed` (snapshot oficial pendiente, tarea manual T005).
- `OrganizationBusinessSector` (`organization_business_sectors`): vigencia `[valid_from, valid_to)`; un principal.
- `OrganizationLegalRepresentative` (`organization_legal_representatives`): vigencia; un `PRIMARY` vigente.

## Estados
- `status` = **estado de uso** de personas y organizaciones: `ACTIVE` / `INACTIVE`. Las listas
  muestran solo `ACTIVE` salvo filtro explícito; la consulta por `id` devuelve cualquier estado.
- `verification_status` (personas: `UNVERIFIED` / `VERIFIED` / `SUSPENDED`) y
  `registration_status` (organizaciones, estado legal informativo) son independientes y no
  controlan el uso.
- Perfiles, sectores de organización y representantes: **vigente** → **cerrada** (sin regreso).
  Personas de contacto y sectores del catálogo: `ACTIVE` ↔ `INACTIVE`. Sin cascadas.

## Referencias externas principales
- País (`country_id`, `identification_country_id`) → Geography Service (`UUID REF`, validado al
  crear o al cambiar país/tipo/número; sin copia de datos).
- Dirección de los perfiles (`country_id`, `administrative_division_id`, `city_id`) → Geography
  Service (existencia, `ACTIVE` y coherencia; solo si cambia algún nivel).
- `confirmed_by_company_id` → `Company` y `confirmed_by_user_id` → `ApplicationUser` de Operational
  Context (`UUID REF`, resueltos con la vía técnica de `operational-access`; nunca del cuerpo).
- `created_by` / `updated_by` → `sub` de Keycloak (texto, sin FK).

## Contratos para consumidores
- Identidades por `id` (`GET /api/v1/organization-identities/{id}`, `GET /api/v1/person-identities/{id}`):
  `200` con `status`, `404` si no existe
  (`specs/003-party-identity-core/contracts/identity-lookup-provider.md`).
- Persona de contacto por `id`, perfil vigente, sectores y representantes vigentes, con permiso
  específico por recurso (`specs/006-party-identity-complementary/contracts/contact-lookup-provider.md`).

## Consumidores principales
- Product Catalog Service (fabricante, en uso)
- Operational Context Service (empresas, usuarios operativos y asesores; sector y representante, futuro)
- Commercial Relationship Service (clientes, proveedores y contacto preferido; futuro)
- Sales y Purchase (datos de contacto; futuro)

## Dependencias salientes
- Geography Service (token del usuario propagado).
- Operational Context Service: `GET /api/v1/operational-access` (vía técnica, cliente
  `party-identity-service`) solo al confirmar un perfil de contacto. **Sin recursión (C-07):**
  ninguna lectura de Party Identity llama a Operational Context y `operational-access` no llama a
  Party Identity.

Las referencias desde otros servicios son `REF`, nunca FK físicas entre bases de datos.

## Ubicación
`services/party-identity-service/docs/domain-map.md`

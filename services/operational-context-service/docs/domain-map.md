# Operational Context Service — Domain Map

## Responsabilidad
Administrar el contexto operativo de las empresas, sucursales y usuarios dentro de SIO.

## Entidades propietarias

### Fase A — implementadas (bloque 7 del roadmap, `specs/004-operational-context-core/`)
- `Company` (`companies`): empresa cliente de la plataforma y su sede operativa principal.
- `Branch` (`branches`): sucursales de una empresa.

### Fase B — pendientes (bloque 8 del roadmap)
- `ApplicationUser`
- `UserBranch`
- `CompanyAdvisorAssignment`

## Referencias externas principales
- `companies.organization_identity_id` → Party Identity Service (`OrganizationIdentity`): identidad
  legal; la razón social, el nombre comercial y la identificación se consultan allá, no se copian.
- `country_id`, `administrative_division_id`, `city_id` (empresa y sucursal) → Geography Service.
- Autenticación, credenciales, sesiones y roles → Keycloak.

Todas son `UUID REF` sin FK física. La única FK es interna: `branches.company_id → companies.id`.

## Consumidores (contrato Provider)
- Commercial Relationship (`company_id`), Inventory (`company_id`, `branch_id`), Purchase y Sales
  (empresa y sucursal): `GET /api/v1/companies/{id}` y `GET /api/v1/branches/{id}`.
- Party Identity Fase B podrá validar `confirmed_by_company_id` de los perfiles de contacto.

## Requisitos registrados para la Fase B
- **Aislamiento por empresa (DS-02)**: la Fase B DEBE filtrar empresas y sucursales por el usuario
  autenticado; en la Fase A la autorización es solo por permiso.
- **Membresía persona/usuario–empresa (DS-03)**:
  - una misma identidad autenticada (`sub`) PUEDE participar en varias empresas, simultánea o
    históricamente; por lo tanto `sub` NO DEBE tener una restricción de unicidad **global**;
  - la Fase B decide la estructura concreta de membresía; si `ApplicationUser` representa la
    pertenencia de un usuario a una empresa, PUEDE existir una unicidad compuesta como
    `(company_id, keycloak_sub)`, y una misma combinación empresa + identidad no debe duplicarse
    activamente;
  - terminar la relación con una empresa cierra o inactiva únicamente esa membresía; nunca elimina
    ni inactiva la `PersonIdentity` ni impide relaciones con otras empresas.
- La Fase A no guarda personas: la única unicidad externa es organización → empresa.

## Ubicación
`services/operational-context-service/docs/domain-map.md`

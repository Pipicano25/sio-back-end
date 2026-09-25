# Operational Context Service — Domain Map

## Responsabilidad
Administrar el contexto operativo de las empresas, sucursales y usuarios dentro de SIO.

## Entidades propietarias
- `Company`
- `Branch`
- `ApplicationUser`
- `UserBranch`
- `CompanyAdvisorAssignment`

## Referencias externas principales
- identidad legal y personas → Party Identity Service
- país, división y ciudad → Geography Service
- autenticación, credenciales, sesiones y roles → Keycloak

## Ubicación
`services/operational-context-service/docs/domain-map.md`

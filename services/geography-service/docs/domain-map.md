# Geography Service — Domain Map

## Responsabilidad
Administrar el catálogo geográfico global reutilizado por los demás microservicios.

## Entidades propietarias
- `GlobalCountry`
- `GlobalAdministrativeDivision`
- `GlobalCity`

## Consumidores principales
- Party Identity Service
- Operational Context Service

Las referencias desde otros servicios son `REF`, nunca FK físicas entre bases de datos.

## Ubicación
`services/geography-service/docs/domain-map.md`

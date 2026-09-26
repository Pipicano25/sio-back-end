# SIO — Mapas de dominio por microservicio

Cada microservicio conserva su mapa en:

`services/<microservicio>/docs/domain-map.md`

Estos archivos son una referencia rápida. La fuente detallada del modelo continúa siendo `docs/SIO Database.md` (o la ubicación oficial que defina el repositorio).

## Servicios incluidos
- `services/audit-service/docs/domain-map.md`
- `services/commercial-relationship-service/docs/domain-map.md`
- `services/geography-service/docs/domain-map.md`
- `services/inventory-service/docs/domain-map.md`
- `services/operational-context-service/docs/domain-map.md`
- `services/party-identity-service/docs/domain-map.md`
- `services/payment-reference-service/docs/domain-map.md`
- `services/product-catalog-service/docs/domain-map.md`
- `services/purchase-service/docs/domain-map.md`
- `services/sales-service/docs/domain-map.md`
- `services/workflow-service/docs/domain-map.md`

## Nota
El modelo actual también documenta un `Finance Service`, pero no se incluyó porque no aparece entre las carpetas proporcionadas y corresponde a un alcance posterior al MVP actual.

## Registro de servicios (D8)

### product-catalog-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Catálogo global compartido de productos (16 entidades; ver su `domain-map.md`) |
| Ruta | `services/product-catalog-service/` |
| Puerto | `8003` (entorno del servicio), `8103` (entorno integrado `infrastructure/`); interno `8000` |
| Base de datos | PostgreSQL propia `product_catalog` (servicio: `55437`, pruebas: `55438`, integrado: `5444`) |
| Depende de | Keycloak (clase B); Party Identity Service (clase C, `GET organization-identities/{id}`) |
| Es consumido por | Commercial Relationship Service (`batch-lookup`, `first-use`) |
| Referencias externas | `manufacturer_organization_id` → Party Identity Service |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Party Identity; los consumidores usan `client_credentials` |
| Spec | `specs/002-product-catalog-service/` |

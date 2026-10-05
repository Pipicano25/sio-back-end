# Payment Reference Service — Domain Map

## Responsabilidad
Administrar catálogos globales relacionados con condiciones y medios de pago.

## Entidades propietarias
- `GlobalPaymentConditionType` — ciclo de vida `ACTIVE`/`INACTIVE` con acciones explícitas,
  `version` y sin borrado físico (feature 008)
- `GlobalPaymentMethod`

## Contratos entrantes
- **Consulta de `GlobalPaymentConditionType` por UUID** (Provider, feature 008):
  `specs/008-payment-reference-condition-type-contract/contracts/payment-condition-type-provider.md`.
  Distingue activo, inactivo, inexistente, acceso denegado y no disponible; el consumidor usa su
  propio tiempo de espera finito.
- `GlobalPaymentMethod`: sin contrato documentado todavía (GAP-PR-29).

## Consumidores principales
- Commercial Relationship Service — previsto en su Fase B (`SupplierPaymentCondition`), sobre el
  contrato de `GlobalPaymentConditionType`
- Purchase Service
- Sales Service
- futuros procesos financieros

## Eventos
Ninguno.

## Ubicación
`services/payment-reference-service/docs/domain-map.md`

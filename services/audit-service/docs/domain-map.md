# Audit Service — Domain Map

## Responsabilidad
Conservar la trazabilidad auditable de operaciones relevantes realizadas en SIO.

## Entidades propietarias
- `AuditEvent`

## Referencias externas
- `company_id` → Operational Context Service
- `user_id` / identidad del actor → contexto de seguridad correspondiente
- Referencias a documentos y operaciones se almacenan como `REF`, sin FK entre servicios.

## Ubicación
`services/audit-service/docs/domain-map.md`

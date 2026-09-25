# Workflow Service — Domain Map

## Responsabilidad
Gestionar alertas y flujos de autorización que no pertenecen al núcleo transaccional de otro servicio.

## Entidades propietarias
- `Alert`
- `ApprovalRequest`

## Uso
- `Alert`: avisos operativos que requieran seguimiento.
- `ApprovalRequest`: autorizaciones explícitas para reglas que lo requieran.

`ApprovalRequest` puede permanecer sin uso en el MVP mientras no existan procesos de aprobación activos.

## Ubicación
`services/workflow-service/docs/domain-map.md`

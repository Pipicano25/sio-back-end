"""Librería compartida de auditoría de SIO (feature 011).

Módulos:

- `sio_audit.redaction`: política única de claves sensibles (FR-017a).
- `sio_audit.event`: contrato del evento, validación y forma canónica (R-04, R-08).
- `sio_audit.outbox`: tabla `audit_outbox` y registro en la transacción del emisor (R-11).
- `sio_audit.worker`: proceso `audit-outbox-worker` (`python -m sio_audit.worker`).

No contiene lógica de dominio de ningún microservicio (Principio I).
"""

__version__ = "0.1.0"

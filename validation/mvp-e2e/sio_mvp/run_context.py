"""Identificador de corrida y valores de correlación deterministas (research R-04)."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid

# Espacio de nombres propio de la suite para los UUID v5 de la corrida.
SUITE_NAMESPACE = uuid.UUID("6f1d8a2e-0b17-5c3e-9a41-017a5e2e0017")
RUN_ID_PATTERN = re.compile(r"[0-9A-F]{8}")
MAX_IDEMPOTENCY_KEY = 150


def new_run_id() -> str:
    return secrets.token_hex(4).upper()


class RunContext:
    def __init__(self, run_id: str) -> None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("RUN_ID debe tener 8 caracteres hexadecimales en mayúscula")
        self.run_id = run_id
        self.run_uuid = uuid.uuid5(SUITE_NAMESPACE, run_id)

    def correlation_id(self, step: str) -> str:
        """`X-Correlation-Id`: determinista dentro de la corrida y distinto por paso."""
        return str(uuid.uuid5(self.run_uuid, step))

    def idempotency_key(self, step: str, attempt: int = 1) -> str:
        """`Idempotency-Key` `mvp-{RUN_ID}-{paso}-{n}`, acotada a 150 caracteres."""
        key = f"mvp-{self.run_id}-{step}-{attempt}"
        if len(key) <= MAX_IDEMPOTENCY_KEY:
            return key
        digest = hashlib.sha256(step.encode("utf-8")).hexdigest()[:16]
        return f"mvp-{self.run_id}-{digest}-{attempt}"

    def traceparent(self) -> str:
        """Cabecera W3C con un trace-id nuevo (se registra en el diario)."""
        trace_id = secrets.token_hex(16)
        span_id = secrets.token_hex(8)
        if trace_id == "0" * 32 or span_id == "0" * 16:  # valores inválidos en W3C
            return self.traceparent()
        return f"00-{trace_id}-{span_id}-01"

    def label(self, name: str) -> str:
        return f"{name} (dato ficticio) {self.run_id}"

    def code(self, prefix: str) -> str:
        return f"{prefix}-{self.run_id}"

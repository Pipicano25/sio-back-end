"""Diario de pasos (`steps.jsonl`) y auditoría esperada (`audit-expected.json`).

Todo lo que se escribe pasa antes por `redact`: cabeceras `Authorization`, contraseñas, secretos,
tokens, los campos protegidos de `data-model.md` §4 y cualquier valor protegido registrado en la
corrida (identificaciones, correos, teléfonos…) o sensible de `infrastructure/.env` (RC-05). Los
mensajes de aserción usan `safe_text`, con el mismo filtro, porque llegan también a los JUnit.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

REDACTED = "***"

# Claves que siempre se ocultan, en cualquier nivel (comparación sin mayúsculas).
SECRET_KEYS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}
SECRET_KEY_PARTS = ("password", "secret", "access_token", "refresh_token", "id_token")

# data-model.md §4: datos personales (DS-06), de contacto de empresa y sucursal (DS-09) y, en Sales,
# costo y margen.
PROTECTED_FIELDS = {
    "identification_number",
    "birth_date",
    "email",
    "phone",
    "phone_number",
    "mobile_phone",
    "address",
    "address_line",
    "postal_code",
    "latitude",
    "longitude",
    "reference_email",
    "unit_cost_snapshot",
    "cost_total",
    "gross_margin",
    "gross_margin_percent",
    "gross_margin_amount",
    "gross_margin_percentage",
    "cost_known",
}

BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")
MIN_PROTECTED_LENGTH = 3


@dataclass(frozen=True)
class ExpectedAudit:
    step_id: str
    service: str
    action: str
    entity_type: str
    entity_id: str
    scope: str  # COMPANY | PLATFORM
    company_id: str | None
    actor: str  # usuario de prueba o identidad técnica (p. ej. service-account-…)
    correlation_id: str | None = None
    result: str = "SUCCESS"  # FAILURE: fallo con operación registrada (R-13 de la 014 y la 015)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in SECRET_KEYS or any(part in lowered for part in SECRET_KEY_PARTS)


class Journal:
    def __init__(self, directory: Path, sensitive_values: Iterable[str] = ()) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.steps_path = self.directory / "steps.jsonl"
        self._values: set[str] = set()
        for value in sensitive_values:
            self.protect(value)
        self._created: list[tuple[str, str, str]] = []
        self.expected_audits: list[ExpectedAudit] = []
        self._lock = threading.Lock()

    # --- filtro -----------------------------------------------------------------------------
    def protect(self, value: Any) -> None:
        """Registra un valor protegido generado en la corrida (nunca se escribe)."""
        if value is None:
            return
        text = str(value).strip()
        if len(text) >= MIN_PROTECTED_LENGTH:
            self._values.add(text)

    @property
    def protected_values(self) -> set[str]:
        return set(self._values)

    def _redact_text(self, text: str) -> str:
        text = BEARER.sub(f"Bearer {REDACTED}", text)
        text = JWT.sub(REDACTED, text)
        for value in sorted(self._values, key=len, reverse=True):
            if value in text:
                text = text.replace(value, REDACTED)
        return text

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                name = str(key)
                if _is_secret_key(name) or name.lower() in PROTECTED_FIELDS:
                    result[key] = REDACTED
                else:
                    result[key] = self.redact(item)
            return result
        if isinstance(value, (list, tuple)):
            return [self.redact(item) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        if value is not None and not isinstance(value, (bool, int, float)):
            return self._redact_text(str(value))
        if isinstance(value, (int, float)) and not isinstance(value, bool) and str(value) in self._values:
            return REDACTED
        return value

    def safe_text(self, value: Any) -> str:
        if isinstance(value, str):
            return self._redact_text(value)
        return json.dumps(self.redact(value), ensure_ascii=False, default=str)

    # --- escritura ----------------------------------------------------------------------------
    def _append(self, entry: dict) -> None:
        line = json.dumps(self.redact(entry), ensure_ascii=False, default=str)
        with self._lock, self.steps_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def record(self, entry: dict) -> None:
        self._append(entry)

    def verify(self, step_id: str, name: str, *, expected: Any, obtained: Any) -> bool:
        ok = expected == obtained
        # Los valores de verificación (p. ej. costos para el supervisor) no se filtran por nombre de
        # campo, solo por valor protegido o secreto.
        payload = {
            "name": name,
            "expected": self._redact_text(str(expected)) if expected is not None else None,
            "obtained": self._redact_text(str(obtained)) if obtained is not None else None,
            "ok": ok,
        }
        line = json.dumps({"step_id": step_id, "verification": payload}, ensure_ascii=False)
        with self._lock, self.steps_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return ok

    # --- ids y auditoría esperada --------------------------------------------------------------
    def created(self, step_id: str, kind: str, entity_id: str) -> None:
        self._created.append((step_id, kind, str(entity_id)))

    def ids(self, kind: str) -> list[str]:
        return [entity_id for _, item_kind, entity_id in self._created if item_kind == kind]

    def created_entities(self) -> list[tuple[str, str, str]]:
        return list(self._created)

    def expect_audit(self, expected: ExpectedAudit) -> None:
        self.expected_audits.append(expected)

    def write_expected_audit(self) -> Path:
        path = self.directory / "audit-expected.json"
        path.write_text(
            json.dumps([asdict(item) for item in self.expected_audits], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

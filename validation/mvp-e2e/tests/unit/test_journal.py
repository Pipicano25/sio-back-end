"""T008 — Diario de pasos con filtro de secretos y datos protegidos (sio_mvp.journal)."""

import json

import pytest

from sio_mvp.journal import REDACTED, ExpectedAudit, Journal

pytestmark = pytest.mark.unit

JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2lnbmF0dXJh"


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_record_filters_authorization_secrets_and_tokens(tmp_path):
    journal = Journal(tmp_path, sensitive_values={"Sio-Clave-1"})
    journal.record(
        {
            "step_id": "C-01",
            "request_headers": {"Authorization": f"Bearer {JWT}", "Idempotency-Key": "mvp-X-1"},
            "request_body": {"password": "Sio-Clave-1", "client_secret": "x", "name": "Empresa"},
            "response_body": {"access_token": JWT, "note": "clave Sio-Clave-1 usada"},
        }
    )
    text = (tmp_path / "steps.jsonl").read_text(encoding="utf-8")
    assert "Sio-Clave-1" not in text
    assert JWT not in text
    (line,) = read_lines(tmp_path / "steps.jsonl")
    assert line["request_headers"]["Authorization"] == REDACTED
    assert line["request_headers"]["Idempotency-Key"] == "mvp-X-1"
    assert line["request_body"]["password"] == REDACTED
    assert line["request_body"]["client_secret"] == REDACTED
    assert line["request_body"]["name"] == "Empresa"
    assert line["response_body"]["access_token"] == REDACTED


def test_protected_fields_of_data_model_section_4_are_filtered(tmp_path):
    journal = Journal(tmp_path)
    body = {
        "identification_number": "1023456789",
        "birth_date": "1990-01-01",
        "contact": {"email": "a@b.test", "phone": "3001234567", "address": "Calle 1", "postal_code": "110111"},
        "branch": {"latitude": 4.6, "longitude": -74.0, "reference_email": "r@b.test"},
        "lines": [{"unit_cost_snapshot": "1000", "cost_total": "12000", "gross_margin": "4000"}],
        "gross_margin_percent": "25.00",
        "cost_known": True,
        "status": "ACTIVE",
    }
    redacted = journal.redact(body)
    assert redacted["identification_number"] == REDACTED
    assert redacted["birth_date"] == REDACTED
    assert set(redacted["contact"].values()) == {REDACTED}
    assert set(redacted["branch"].values()) == {REDACTED}
    assert set(redacted["lines"][0].values()) == {REDACTED}
    assert redacted["gross_margin_percent"] == REDACTED
    assert redacted["cost_known"] == REDACTED
    assert redacted["status"] == "ACTIVE"
    assert body["identification_number"] == "1023456789", "redact no modifica el original"


def test_registered_protected_values_are_filtered_anywhere(tmp_path):
    journal = Journal(tmp_path)
    journal.protect("1023456789")
    journal.protect("persona@ficticio.test")
    redacted = journal.redact({"detail": "La identificación 1023456789 ya existe", "items": ["persona@ficticio.test"]})
    assert "1023456789" not in json.dumps(redacted)
    assert "persona@ficticio.test" not in json.dumps(redacted)


def test_safe_text_for_assertion_messages_is_filtered(tmp_path):
    journal = Journal(tmp_path, sensitive_values={"Sio-Clave-1"})
    journal.protect("1023456789")
    message = journal.safe_text(
        {"Authorization": f"Bearer {JWT}", "identification_number": "1023456789", "detail": "Sio-Clave-1 en texto"}
    )
    assert JWT not in message and "Sio-Clave-1" not in message and "1023456789" not in message
    assert journal.safe_text(f"respuesta con Bearer {JWT} y token suelto {JWT}").count(JWT) == 0


def test_short_or_empty_values_are_not_registered_as_protected(tmp_path):
    journal = Journal(tmp_path, sensitive_values={"", "  "})
    journal.protect("")
    journal.protect(None)
    assert journal.redact({"status": "ACTIVE"}) == {"status": "ACTIVE"}


def test_created_ids_and_expected_audit_are_registered(tmp_path):
    journal = Journal(tmp_path)
    journal.created("C-03", "company", "c-1")
    journal.created("C-03", "company", "c-2")
    journal.expect_audit(
        ExpectedAudit(
            step_id="C-03",
            service="operational-context",
            action="CREATE_COMPANY",
            entity_type="company",
            entity_id="c-1",
            scope="COMPANY",
            company_id="c-1",
            actor="admin.test",
        )
    )
    assert journal.ids("company") == ["c-1", "c-2"]
    journal.write_expected_audit()
    (expected,) = json.loads((tmp_path / "audit-expected.json").read_text(encoding="utf-8"))
    assert expected["action"] == "CREATE_COMPANY"
    assert expected["scope"] == "COMPANY"
    assert expected["entity_id"] == "c-1"


def test_verification_values_are_recorded_and_filtered(tmp_path):
    journal = Journal(tmp_path)
    journal.protect("1023456789")
    journal.verify("V-06", "costo V2", expected="21600.00", obtained="21600.00")
    journal.verify("C-09", "identificación", expected="1023456789", obtained="1023456789")
    lines = read_lines(tmp_path / "steps.jsonl")
    assert lines[0]["verification"] == {"name": "costo V2", "expected": "21600.00", "obtained": "21600.00", "ok": True}
    assert "1023456789" not in json.dumps(lines[1])

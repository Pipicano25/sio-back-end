"""T007 — Identificador de corrida y correlación (sio_mvp.run_context)."""

import re
import uuid

import pytest

from sio_mvp.run_context import RunContext, new_run_id

pytestmark = pytest.mark.unit


def test_run_id_is_eight_uppercase_hex():
    for _ in range(50):
        assert re.fullmatch(r"[0-9A-F]{8}", new_run_id())


def test_run_uuid_is_stable_uuid5_for_the_same_run_id():
    first = RunContext("A1B2C3D4")
    second = RunContext("A1B2C3D4")
    assert first.run_uuid == second.run_uuid
    assert first.run_uuid.version == 5
    assert RunContext("00000001").run_uuid != first.run_uuid


def test_run_context_rejects_invalid_run_id():
    with pytest.raises(ValueError):
        RunContext("a1b2c3d4")
    with pytest.raises(ValueError):
        RunContext("XYZ")


def test_correlation_id_is_deterministic_per_step_and_distinct_between_steps():
    context = RunContext("A1B2C3D4")
    assert context.correlation_id("P-02-P1") == RunContext("A1B2C3D4").correlation_id("P-02-P1")
    assert context.correlation_id("P-02-P1") != context.correlation_id("P-02-P2")
    assert uuid.UUID(context.correlation_id("P-02-P1")).version == 5
    assert RunContext("00000001").correlation_id("P-02-P1") != context.correlation_id("P-02-P1")


def test_idempotency_key_format_and_length():
    context = RunContext("A1B2C3D4")
    assert context.idempotency_key("P-02-P1") == "mvp-A1B2C3D4-P-02-P1-1"
    assert context.idempotency_key("P-02-P1", 2) == "mvp-A1B2C3D4-P-02-P1-2"
    long_key = context.idempotency_key("X" * 400, 7)
    assert len(long_key) <= 150
    assert long_key.startswith("mvp-A1B2C3D4-")
    assert long_key != context.idempotency_key("X" * 401, 7)


def test_traceparent_is_valid_w3c_and_new_each_time():
    context = RunContext("A1B2C3D4")
    first, second = context.traceparent(), context.traceparent()
    pattern = r"00-([0-9a-f]{32})-([0-9a-f]{16})-01"
    match = re.fullmatch(pattern, first)
    assert match
    assert match.group(1) != "0" * 32 and match.group(2) != "0" * 16
    assert re.fullmatch(pattern, second)
    assert first != second


def test_label_and_code_include_run_id():
    context = RunContext("A1B2C3D4")
    assert context.label("Empresa A") == "Empresa A (dato ficticio) A1B2C3D4"
    assert context.code("PROD-A") == "PROD-A-A1B2C3D4"

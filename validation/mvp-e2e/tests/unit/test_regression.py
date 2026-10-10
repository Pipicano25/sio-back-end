"""T054 — Comparación de la regresión con la línea base por identificador (sio_mvp.regression)."""

import json

import pytest

from sio_mvp import regression
from sio_mvp.regression import KNOWN_GEOGRAPHY_FAILURES, SuiteResult, compare

pytestmark = pytest.mark.unit


def baseline(results):
    return {"taken_at": "2026-10-08T00:00:00Z", "git_head": "abc", "known_failures": {"geography": list(KNOWN_GEOGRAPHY_FAILURES)}, "results": results}


def suite(passed=10, failed=0, errors=0, skipped=0, failures=(), exit_code=0):
    return {"passed": passed, "failed": failed, "errors": errors, "skipped": skipped, "total": passed + failed + errors + skipped, "failures": list(failures), "exit_code": exit_code}


def result(target, name, passed=10, failed=0, errors=0, skipped=0, failures=(), exit_code=0):
    return SuiteResult(target, name, passed, failed, errors, skipped, passed + failed + errors + skipped, list(failures), 1.0, exit_code)


def test_same_known_failures_are_not_a_regression():
    base = baseline({"geography": {"full": suite(107, 6, failures=KNOWN_GEOGRAPHY_FAILURES, exit_code=1)}})
    comparison = compare(base, [result("geography", "full", 107, 6, failures=KNOWN_GEOGRAPHY_FAILURES, exit_code=1)])
    assert comparison.ok
    item = comparison.items[0]
    assert item["new_failures"] == [] and item["known_failures"] == sorted(KNOWN_GEOGRAPHY_FAILURES)


def test_new_failure_is_a_regression():
    base = baseline({"sales": {"full": suite(486)}})
    comparison = compare(base, [result("sales", "full", 485, 1, failures=["tests.unit.test_x::test_y"], exit_code=1)])
    assert not comparison.ok
    assert comparison.items[0]["new_failures"] == ["tests.unit.test_x::test_y"]


def test_failure_of_known_service_with_other_id_is_a_regression():
    base = baseline({"geography": {"full": suite(107, 6, failures=KNOWN_GEOGRAPHY_FAILURES, exit_code=1)}})
    failures = list(KNOWN_GEOGRAPHY_FAILURES) + ["tests.unit.test_other::test_new"]
    comparison = compare(base, [result("geography", "full", 106, 7, failures=failures, exit_code=1)])
    assert not comparison.ok
    assert comparison.items[0]["new_failures"] == ["tests.unit.test_other::test_new"]


def test_fewer_tests_than_baseline_is_an_alert():
    base = baseline({"audit": {"full": suite(209)}})
    comparison = compare(base, [result("audit", "full", 200)])
    assert comparison.ok
    assert comparison.items[0]["alerts"]
    assert comparison.alerts


def test_fixed_failure_is_reported():
    base = baseline({"audit": {"full": suite(208, 1, failures=["tests.api.test_a::test_b"], exit_code=1)}})
    comparison = compare(base, [result("audit", "full", 209)])
    assert comparison.ok
    assert comparison.items[0]["fixed"] == ["tests.api.test_a::test_b"]


def test_missing_suite_or_abnormal_exit_is_not_ok():
    base = baseline({"sales": {"full": suite(486), "integration": suite(20)}})
    comparison = compare(base, [result("sales", "full", 486)])
    assert not comparison.ok
    assert any("integration" in alert for alert in comparison.alerts)
    crashed = compare(base, [result("sales", "full", 0, exit_code=None), result("sales", "integration", 20)])
    assert not crashed.ok


def test_baseline_known_failures_must_match_geography():
    base = baseline({"geography": {"full": suite(107, 6, failures=KNOWN_GEOGRAPHY_FAILURES, exit_code=1)}})
    assert regression.unexpected_baseline_failures(base) == {}
    base["results"]["sales"] = {"full": suite(485, 1, failures=["tests.x::y"], exit_code=1)}
    assert regression.unexpected_baseline_failures(base) == {"sales/full": ["tests.x::y"]}


def test_write_regression_json(tmp_path):
    base = baseline({"sales": {"full": suite(486)}})
    comparison = compare(base, [result("sales", "full", 486)])
    path = comparison.write(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["items"][0]["target"] == "sales"
    assert data["items"][0]["before"]["passed"] == 486
    assert data["items"][0]["after"]["passed"] == 486

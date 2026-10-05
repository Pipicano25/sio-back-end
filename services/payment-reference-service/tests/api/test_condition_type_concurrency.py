"""Concurrencia optimista real (RC-03; FR-015; SC-004).

Cada solicitud usa su propia sesión de base (dependencia por solicitud), de modo que dos solicitudes
simultáneas leen la misma versión y la carrera la resuelve el `UPDATE … WHERE version`.
"""

from __future__ import annotations

import threading

from tests.conftest import CONDITION_TYPES

VERSION_CONFLICT = "PAYMENT_REFERENCE.VERSION_CONFLICT"
PAIRS = 20


def _race(calls):
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def run(index, call):
        barrier.wait()
        results[index] = call()

    threads = [threading.Thread(target=run, args=(i, call)) for i, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def _outcome(responses):
    statuses = sorted(response.status_code for response in responses)
    conflicts = [r for r in responses if r.status_code == 409]
    return statuses, [r.json().get("code") for r in conflicts]


def test_twenty_pairs_of_simultaneous_deactivations(admin):
    for index in range(PAIRS):
        created = admin.post(CONDITION_TYPES, json={"code": f"RACE_{index}", "name": f"Carrera {index}"})
        assert created.status_code == 201, created.text
        item = created.json()
        url = f"{CONDITION_TYPES}/{item['id']}/deactivate"

        responses = _race([lambda: admin.post(url, json={"version": 1})] * 2)

        statuses, codes = _outcome(responses)
        assert statuses == [200, 409], (index, [r.text for r in responses])
        assert codes == [VERSION_CONFLICT]
        current = admin.get(f"{CONDITION_TYPES}/{item['id']}").json()
        assert (current["status"], current["version"]) == ("INACTIVE", 2)


def test_put_and_deactivate_on_same_version(admin, condition_type):
    item_id = condition_type["id"]
    put = lambda: admin.put(  # noqa: E731
        f"{CONDITION_TYPES}/{item_id}", json={"version": 1, "code": "CREDIT", "name": "Crédito comercial"}
    )
    deactivate = lambda: admin.post(f"{CONDITION_TYPES}/{item_id}/deactivate", json={"version": 1})  # noqa: E731

    responses = _race([put, deactivate])

    statuses, codes = _outcome(responses)
    assert statuses == [200, 409], [r.text for r in responses]
    assert codes == [VERSION_CONFLICT]
    assert admin.get(f"{CONDITION_TYPES}/{item_id}").json()["version"] == 2


def test_race_after_version_check_is_resolved_by_update_where_version(admin, condition_type, monkeypatch):
    """Ambas solicitudes pasan la comprobación previa con `version = 1`; la escritura se retrasa para que
    las dos lleguen al `UPDATE … WHERE version = 1`: la segunda no actualiza filas (`StaleDataError`) y
    recibe `409 PAYMENT_REFERENCE.VERSION_CONFLICT`.
    """
    import time

    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from sqlalchemy.orm.exc import StaleDataError

    from payment_reference_service.infrastructure import (
        global_payment_condition_types_repository as repository_module,
    )

    stale = []
    original = repository_module.SqlAlchemyGlobalPaymentConditionTypeRepository.update

    def tracked(self, entity, *, expected_version):
        try:
            return original(self, entity, expected_version=expected_version)
        except Exception as exc:
            stale.append(isinstance(exc.__cause__, StaleDataError))
            raise

    def delay(session, flush_context, instances):
        time.sleep(0.4)

    monkeypatch.setattr(repository_module.SqlAlchemyGlobalPaymentConditionTypeRepository, "update", tracked)
    event.listen(Session, "before_flush", delay)
    try:
        url = f"{CONDITION_TYPES}/{condition_type['id']}/deactivate"
        responses = _race([lambda: admin.post(url, json={"version": 1})] * 2)
    finally:
        event.remove(Session, "before_flush", delay)

    statuses, codes = _outcome(responses)
    assert statuses == [200, 409]
    assert codes == [VERSION_CONFLICT]
    assert stale == [True]
    current = admin.get(f"{CONDITION_TYPES}/{condition_type['id']}").json()
    assert (current["status"], current["version"]) == ("INACTIVE", 2)

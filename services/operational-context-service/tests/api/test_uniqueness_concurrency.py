"""Unicidad y versión bajo concurrencia (RC-02, RC-06, R-09).

Solicitudes simultáneas en hilos independientes (cada una con su propia
sesión): exactamente una tiene éxito y la otra recibe `409`, nunca `500`.
"""

import threading

from tests.conftest import branch_payload, company_payload, update_body


def _parallel(call, times=2):
    barrier = threading.Barrier(times)
    results = [None] * times

    def worker(index):
        barrier.wait()
        results[index] = call()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(times)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return sorted(response.status_code for response in results)


def test_same_organization_in_parallel(api, fake_organizations):
    organization_id = fake_organizations.add()

    statuses = _parallel(lambda: api.post("/api/v1/companies", json=company_payload(organization_id)))

    assert statuses == [201, 409]


def test_same_branch_code_in_parallel(api, create_company):
    company = create_company()

    statuses = _parallel(
        lambda: api.post(f"/api/v1/companies/{company['id']}/branches", json=branch_payload(code="PAR-1"))
    )

    assert statuses == [201, 409]


def test_two_puts_with_same_version(api, create_company):
    company = create_company()
    bodies = iter([update_body(company, phone="1"), update_body(company, phone="2")])
    lock = threading.Lock()

    def put():
        with lock:
            body = next(bodies)
        return api.put(f"/api/v1/companies/{company['id']}", json=body)

    statuses = _parallel(put)

    assert statuses == [200, 409]
    assert api.get(f"/api/v1/companies/{company['id']}").json()["version"] == 2

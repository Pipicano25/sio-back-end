"""Asignaciones concurrentes de una presentación en una lista (T018; CP-47, CP-T10, SC-005; RC-021-1).

50 políticas de la misma lista intentan a la vez incorporar la misma presentación: la exclusión GiST de la base deja
exactamente una asignación y las demás reciben `409 PRESENTATION_ALREADY_IN_POLICY`.
"""

from __future__ import annotations

from sqlalchemy import text

from tests.api.concurrency import race
from tests.api.helpers import adopt, adopt_presentation, create_price_list

ATTEMPTS = 50


def test_cp47_concurrent_assignments_leave_a_single_policy(app, user_token, as_user, company, fake_catalog, test_engine):
    supervisor = as_user("supervisor.test")
    product = adopt(supervisor, company, fake_catalog)
    presentation = adopt_presentation(supervisor, company, fake_catalog, product)["id"]
    public = create_price_list(supervisor, company)
    policies = []
    for index in range(ATTEMPTS):
        response = supervisor.post(
            f"/api/v1/companies/{company}/price-lists/{public['id']}/pricing-policies",
            json={"name": f"Política {index}", "markup_percentage": "10", "company_product_presentation_ids": []},
        )
        assert response.status_code == 201, response.text
        policies.append(response.json())

    results = race(
        app,
        user_token("supervisor.test"),
        [
            ("POST", f"/api/v1/pricing-policies/{policy['id']}/presentations",
             {"version": policy["version"], "company_product_presentation_ids": [presentation]})
            for policy in policies
        ],
    )

    statuses = sorted(response.status_code for response in results)
    assert statuses == [200] + [409] * (ATTEMPTS - 1), [r.text for r in results if r.status_code not in (200, 409)]
    assert all(
        response.json()["code"] == "COMMERCIAL_RELATIONSHIP.PRESENTATION_ALREADY_IN_POLICY"
        for response in results
        if response.status_code == 409
    )
    with test_engine.connect() as connection:
        open_assignments = connection.execute(
            text(
                "SELECT count(*) FROM price_list_pricing_policy_presentations "
                "WHERE company_product_presentation_id = :p AND valid_to IS NULL"
            ),
            {"p": presentation},
        ).scalar_one()
    assert open_assignments == 1

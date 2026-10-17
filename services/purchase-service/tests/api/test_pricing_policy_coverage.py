"""Cobertura de políticas de ganancia obligatoria al confirmar (spec 021, FR-021-35, FR-021-36; T097).

CP-69 (todo cubierto), CP-70 (una o varias sin política), CP-76 (CR indisponible), CP-77 (reintento tras configurar),
CP-78 (rechazo sin efectos: sin número, operación, contador, outbox ni inventario; la clave sigue libre) y CP-79 (la
recepción no vuelve a validar). En los dobles, `fakes.cr.uncovered` son las presentaciones sin política aplicable.
Productos ficticios: "Colgate" = unidad del arroz, "Clarityne" = caja de 12 del arroz, "Dolex" = unidad del aceite.
"""

from __future__ import annotations

from dataclasses import replace

from purchase_service.application.exceptions import COMMERCIAL_RELATIONSHIP, DependencyUnavailableError
from tests.conftest import base, count_rows, line, new_key
from tests.fakes import unit_presentation_of

CODE = "PURCHASE.PRICING_POLICY_NOT_CONFIGURED"


def _three_lines(world) -> list[dict]:
    return [
        line(world.product, "10", "1000"),  # Colgate
        line(world.product, "10", "12000", company_product_presentation_id=world.presentation),  # Clarityne
        line(world.product_2, "10", "800"),  # Dolex
    ]


def _effects(test_engine, purchase_id) -> dict:
    return {
        "operations": count_rows(test_engine, "purchase_operations", "purchase_id = :p", p=purchase_id),
        "counters": count_rows(test_engine, "purchase_sequence_counters"),
        "outbox": count_rows(test_engine, "purchase_price_update_outbox", "purchase_id = :p", p=purchase_id),
        "series": count_rows(test_engine, "purchase_presentation_cost_series"),
    }


def test_cp69_all_presentations_covered_confirms(make_sequence, make_draft, confirm, world, fakes) -> None:
    make_sequence()
    draft = make_draft(*_three_lines(world))
    assert all(detail["warnings"] == [] for detail in draft["lines"])
    response = confirm(draft)
    assert response.status_code == 200, response.text
    [call] = [argument for name, argument in fakes.cr.availability.calls if name == "pricing_coverage"][-1:]
    company, currency, ids = call
    assert company == world.company and currency == "COP"
    assert set(ids) == {unit_presentation_of(world.product), world.presentation, unit_presentation_of(world.product_2)}


def test_cp70_cp78_cp77_missing_policy_blocks_without_effects_and_retry_confirms(
    make_sequence, make_draft, confirm, world, fakes, buyer, test_engine
) -> None:
    """Ejemplo aprobado: Colgate 30 %, Clarityne 25 %, Dolex sin política → `409` solo con Dolex; luego se configura."""
    make_sequence()
    dolex = unit_presentation_of(world.product_2)
    fakes.cr.uncovered = {dolex}
    draft = make_draft(*_three_lines(world))
    before = _effects(test_engine, draft["id"])
    entries_before = fakes.inventory.entry_calls
    key = new_key()

    response = confirm(draft, key)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == CODE
    assert [(error["line_number"], error["company_product_presentation_id"], error["code"]) for error in body["errors"]] == [
        (3, str(dolex), "PRICING_POLICY_NOT_CONFIGURED")
    ]
    assert body["errors"][0]["field"] == "lines[2].company_product_presentation_id"
    current = buyer.get(f"{base(world)}/purchases/{draft['id']}").json()
    assert current["status"] == "DRAFT" and current["number"] is None and current["version"] == draft["version"]
    assert _effects(test_engine, draft["id"]) == before  # sin operación, contador, outbox ni serie
    assert fakes.inventory.entry_calls == entries_before  # sin inventario

    fakes.cr.uncovered = set()  # se configura la política de Dolex en Commercial Relationship
    retried = confirm(draft, key)  # la misma clave: el rechazo no la consumió
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "CONFIRMED" and retried.json()["number"] is not None


def test_cp70_several_missing_policies_are_all_reported(make_sequence, make_draft, confirm, world, fakes) -> None:
    make_sequence()
    fakes.cr.uncovered = {unit_presentation_of(world.product), unit_presentation_of(world.product_2)}
    draft = make_draft(*_three_lines(world))
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == CODE
    assert [error["line_number"] for error in response.json()["errors"]] == [1, 3]


def test_tax_is_checked_before_coverage(make_sequence, make_draft, confirm, world, fakes) -> None:
    """Orden de rechazos (FR-021-35): referencias → repetidas → impuesto → cobertura → usuario → secuencia."""
    make_sequence()
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], purchase_tax_percentage=None)
    fakes.cr.uncovered = {unit_presentation_of(world.product_2)}
    draft = make_draft(*_three_lines(world))
    assert confirm(draft).json()["code"] == "PURCHASE.PURCHASE_TAX_NOT_CONFIGURED"


def test_coverage_is_checked_before_the_sequence(make_draft, confirm, world, fakes) -> None:
    fakes.cr.uncovered = {unit_presentation_of(world.product_2)}
    draft = make_draft(*_three_lines(world))  # sin secuencia configurada
    assert confirm(draft).json()["code"] == CODE


def test_cp76_commercial_relationship_unavailable_is_503_without_effects(
    make_sequence, make_draft, confirm, world, fakes, buyer, test_engine
) -> None:
    make_sequence()
    draft = make_draft(*_three_lines(world))
    before = _effects(test_engine, draft["id"])

    def down(*_args, **_kwargs):
        raise DependencyUnavailableError(COMMERCIAL_RELATIONSHIP, operation="pricing_policy_coverage", cause="prueba")

    fakes.cr.lookup_pricing_coverage = down
    response = confirm(draft)
    assert response.status_code == 503, response.text
    assert response.json()["dependency"] == "commercial-relationship"
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["status"] == "DRAFT"
    assert _effects(test_engine, draft["id"]) == before


def test_draft_lines_warn_without_blocking(make_draft, world, fakes, buyer) -> None:
    """FR-021-36: el borrador se crea y se edita; la línea sin política muestra la advertencia."""
    dolex = unit_presentation_of(world.product_2)
    fakes.cr.uncovered = {dolex}
    draft = make_draft(line(world.product, "1", "1000"))
    assert draft["lines"][0]["warnings"] == []

    added = buyer.post(f"{base(world)}/purchases/{draft['id']}/details",
                       json={**line(world.product_2, "1", "800"), "version": draft["version"]})
    assert added.status_code == 201, added.text
    warnings = {detail["company_product_presentation_id"]: detail["warnings"] for detail in added.json()["lines"]}
    assert warnings == {str(unit_presentation_of(world.product)): [], str(dolex): ["PRICING_POLICY_NOT_CONFIGURED"]}

    fakes.cr.uncovered = set()  # se configura la política; al editar la línea la advertencia desaparece
    dolex_line = next(detail for detail in added.json()["lines"] if detail["company_product_presentation_id"] == str(dolex))
    edited = buyer.put(f"{base(world)}/purchases/{draft['id']}/details/{dolex_line['id']}",
                       json={**line(world.product_2, "2", "800"), "version": added.json()["version"]})
    assert edited.status_code == 200, edited.text
    assert all(detail["warnings"] == [] for detail in edited.json()["lines"])


def test_draft_warning_together_with_the_tax_warning(make_draft, world, fakes) -> None:
    fakes.cr.products[world.product_2] = replace(fakes.cr.products[world.product_2], purchase_tax_percentage=None)
    fakes.cr.uncovered = {unit_presentation_of(world.product_2)}
    draft = make_draft(line(world.product_2, "1", "800"))
    assert draft["lines"][0]["warnings"] == ["PURCHASE_TAX_NOT_CONFIGURED", "PRICING_POLICY_NOT_CONFIGURED"]


def test_cp79_receipt_does_not_revalidate_coverage(make_sequence, make_draft, confirm, receive, world, fakes, test_engine) -> None:
    """RC-021-14: si la política se retira después de confirmar, la recepción no se bloquea."""
    make_sequence()
    draft = make_draft(*_three_lines(world))
    confirmed = confirm(draft)
    assert confirmed.status_code == 200, confirmed.text
    fakes.cr.uncovered = {unit_presentation_of(world.product_2)}  # se retiró la política de Dolex
    calls_before = [name for name, _ in fakes.cr.availability.calls].count("pricing_coverage")
    received = receive(confirmed.json())
    assert received.status_code == 200, received.text
    assert received.json()["receipt_status"] == "RECEIVED"
    assert [name for name, _ in fakes.cr.availability.calls].count("pricing_coverage") == calls_before
    # la solicitud de precio sale igual para las tres líneas; CR decidirá con la captura de received_at
    assert count_rows(test_engine, "purchase_price_update_outbox", "purchase_id = :p", p=draft["id"]) == 3

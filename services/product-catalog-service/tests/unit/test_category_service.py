"""Detección de ciclos jerárquicos (RC-02, FR-021, FR-063)."""

from uuid import uuid4

from product_catalog_service.domain.hierarchy import would_create_cycle


def _tree():
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    parents = {a: None, b: a, c: b, d: None}
    return a, b, c, d, parents.get


def test_self_reference_is_cycle() -> None:
    a, _, _, _, parent_of = _tree()
    assert would_create_cycle(a, a, parent_of)


def test_indirect_cycle_detected() -> None:
    a, _, c, _, parent_of = _tree()
    # A -> B -> C; mover A bajo C crea A -> B -> C -> A.
    assert would_create_cycle(a, c, parent_of)


def test_moving_to_unrelated_branch_is_allowed() -> None:
    _, _, c, d, parent_of = _tree()
    assert not would_create_cycle(c, d, parent_of)


def test_moving_to_root_is_allowed() -> None:
    _, _, c, _, parent_of = _tree()
    assert not would_create_cycle(c, None, parent_of)


def test_corrupted_infinite_chain_counts_as_cycle() -> None:
    x, y = uuid4(), uuid4()
    loop = {x: y, y: x}
    assert would_create_cycle(uuid4(), x, loop.get)

"""Firma del cursor (T088; FR-022-145, FR-022-146, CP-116, CP-117, CP-121, CP-126)."""

from __future__ import annotations

import base64
import json
from uuid import uuid4

import pytest

from product_inventory_query_service.application.exceptions import InvalidCursorError
from product_inventory_query_service.domain.cursor import CursorCodec, Expected

SECRET = "cursor-secret-for-tests-only-0123456789abcdef"
OLD = "previous-cursor-secret-0123456789abcdefghij"
EXPECTED = Expected("product-overviews", str(uuid4()), "huella", "display_name:asc", 20, "R-B")
POSITION = {"k": ["Crema dental"], "id": str(uuid4())}


def codec(secret=SECRET, previous=None, now=1_000_000.0) -> CursorCodec:
    return CursorCodec(secret, previous, ttl_seconds=900, clock=lambda: now)


def _content(cursor: str) -> dict:
    part = cursor.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def test_round_trip() -> None:
    cursor = codec().issue(EXPECTED, kind="PAGE", position=POSITION)
    payload = codec().decode(cursor)
    assert (payload.k, payload.pos, payload.route, payload.ps) == ("PAGE", POSITION, "R-B", 20)
    assert payload.exp - payload.iat == 900
    assert cursor.startswith("v1.") and len(cursor) <= 2048


def test_any_altered_character_is_invalid() -> None:
    cursor = codec().issue(EXPECTED, kind="SCAN", position=POSITION)
    for index in range(3, len(cursor)):
        if cursor[index] == ".":
            continue
        altered = cursor[:index] + ("A" if cursor[index] != "A" else "B") + cursor[index + 1:]
        with pytest.raises(InvalidCursorError):
            codec().decode(altered)


def test_unknown_secret_is_invalid_and_rotation_accepts_previous() -> None:
    old_cursor = codec(secret=OLD).issue(EXPECTED, kind="PAGE", position=POSITION)
    with pytest.raises(InvalidCursorError):
        codec().decode(old_cursor)
    rotating = codec(previous=OLD)
    assert rotating.decode(old_cursor).pos == POSITION
    new_cursor = rotating.issue(EXPECTED, kind="PAGE", position=POSITION)
    assert codec().decode(new_cursor).pos == POSITION  # se firma con el actual


@pytest.mark.parametrize(
    "value",
    ["", "v1", "v1.a", "v2.YQ.YQ", "v1.!!.??", "v1.a.b.c", "x" * 2049, "v1." + "A" * 3000 + ".B"],
)
def test_malformed_cursors_are_invalid(value) -> None:
    with pytest.raises(InvalidCursorError):
        codec().decode(value)


def test_signed_but_wrong_content_is_invalid() -> None:
    import hashlib
    import hmac

    def forge(data) -> str:
        content = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
        signature = hmac.new(SECRET.encode(), f"v1.{content}".encode(), hashlib.sha256).digest()
        return f"v1.{content}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    valid = _content(codec().issue(EXPECTED, kind="PAGE", position=POSITION))
    for broken in ({**valid, "v": 2}, {**valid, "k": "OTRO"}, {k: v for k, v in valid.items() if k != "fh"},
                   {**valid, "extra": 1}, {**valid, "pos": "texto"}, [1, 2]):
        with pytest.raises(InvalidCursorError):
            codec().decode(forge(broken))


def test_content_has_no_secrets_tokens_or_id_lists() -> None:
    content = _content(codec().issue(EXPECTED, kind="PAGE", position=POSITION))
    assert set(content) == {"v", "ep", "cid", "fh", "sort", "ps", "route", "k", "pos", "iat", "exp"}
    text = json.dumps(content)
    for forbidden in ("Bearer", "token", "password", "secret", "perm:", "sub", "ids"):
        assert forbidden not in text
    assert not any(isinstance(value, list) and len(value) > 1 for value in content["pos"].values())

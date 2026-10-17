"""Referencia firmada de imagen (spec 022, FR-022-91, FR-022-97; T026, CP-24, CP-30)."""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from product_catalog_service.domain.image_ref import MIN_SECRET_BYTES, sign_ref, verify_ref

SECRET = "image-ref-secret-for-tests-0123456789abcdef"
OTHER = "another-image-ref-secret-0123456789abcdef!"
SHA = hashlib.sha256(b"contenido").hexdigest()


def test_round_trip_returns_asset_and_sha_prefix() -> None:
    asset_id = uuid4()
    ref = sign_ref(asset_id, SHA, SECRET)
    assert verify_ref(ref, [SECRET]) == (asset_id, SHA[:16])


def test_reference_is_deterministic_per_asset_and_content() -> None:
    asset_id = uuid4()
    assert sign_ref(asset_id, SHA, SECRET) == sign_ref(asset_id, SHA, SECRET)
    assert sign_ref(asset_id, SHA, SECRET) != sign_ref(uuid4(), SHA, SECRET)
    other_sha = hashlib.sha256(b"otro").hexdigest()
    assert sign_ref(asset_id, SHA, SECRET) != sign_ref(asset_id, other_sha, SECRET)


def test_signature_has_at_least_128_bits() -> None:
    ref = sign_ref(uuid4(), SHA, SECRET)
    _, signature = ref.split(".")
    assert len(signature) >= 22  # 16 bytes en base64url sin relleno


def test_any_altered_character_is_rejected() -> None:
    ref = sign_ref(uuid4(), SHA, SECRET)
    for index in range(len(ref)):
        if ref[index] == ".":
            continue
        replacement = "A" if ref[index] != "A" else "B"
        altered = ref[:index] + replacement + ref[index + 1:]
        assert verify_ref(altered, [SECRET]) is None, index


def test_previous_secret_is_accepted_during_rotation_and_unknown_is_not() -> None:
    asset_id = uuid4()
    old = sign_ref(asset_id, SHA, OTHER)
    assert verify_ref(old, [SECRET]) is None
    assert verify_ref(old, [SECRET, OTHER]) == (asset_id, SHA[:16])


@pytest.mark.parametrize(
    "value",
    ["", ".", "abc", "a.b.c", "!!!.???", "A" * 10 + "." + "B" * 22, "A" * 600, None],
)
def test_malformed_references_are_rejected(value) -> None:
    assert verify_ref(value, [SECRET]) is None


def test_short_or_missing_secret_is_rejected() -> None:
    with pytest.raises(ValueError):
        sign_ref(uuid4(), SHA, "corto")
    assert verify_ref(sign_ref(uuid4(), SHA, SECRET), []) is None
    assert MIN_SECRET_BYTES == 32


def test_invalid_sha_is_rejected_when_signing() -> None:
    with pytest.raises(ValueError):
        sign_ref(uuid4(), "no-es-un-sha", SECRET)

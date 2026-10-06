"""Política única de redacción (FR-017, FR-017a; RC-04; R-07)."""

from __future__ import annotations

import copy

import pytest

from sio_audit.redaction import REDACTED_VALUE, SENSITIVE_KEYS, is_sensitive_key, redact

SPELLINGS = {
    "password": ["password", "Password", "PASSWORD"],
    "passwd": ["passwd"],
    "secret": ["secret", "Secret"],
    "clientsecret": ["client_secret", "client-secret", "clientSecret", "CLIENT_SECRET"],
    "token": ["token", "Token"],
    "accesstoken": ["access_token", "accessToken", "access-token"],
    "refreshtoken": ["refresh_token", "refreshToken"],
    "idtoken": ["id_token", "idToken"],
    "authorization": ["authorization", "Authorization"],
    "apikey": ["api_key", "apiKey", "api-key", "API_KEY"],
    "credential": ["credential"],
    "credentials": ["credentials", "Credentials"],
    "privatekey": ["private_key", "privateKey"],
}


def test_policy_covers_every_documented_key() -> None:
    assert set(SPELLINGS) == set(SENSITIVE_KEYS)


@pytest.mark.parametrize(
    "key",
    [spelling for spellings in SPELLINGS.values() for spelling in spellings],
)
def test_each_spelling_is_redacted(key: str) -> None:
    result = redact(None, {key: "valor-secreto", "name": "visible"})

    assert result.new_values == {key: REDACTED_VALUE, "name": "visible"}
    assert result.paths == (f"new_values.{key}",)


@pytest.mark.parametrize(
    "key",
    ["token_count", "password_policy_id", "tokens", "secretary", "authorization_code", "api"],
)
def test_similar_names_are_not_redacted(key: str) -> None:
    assert not is_sensitive_key(key)
    result = redact({key: "valor"}, None)
    assert result.previous_values == {key: "valor"}
    assert result.paths == ()


def test_whole_value_is_replaced_for_objects_and_lists() -> None:
    result = redact(
        None,
        {"credentials": {"user": "a", "api_key": "b"}, "token": ["x", "y"]},
    )

    assert result.new_values == {"credentials": REDACTED_VALUE, "token": REDACTED_VALUE}
    assert result.paths == ("new_values.credentials", "new_values.token")


def test_lists_of_objects_and_nested_paths() -> None:
    result = redact(
        {"contacts": [{"name": "a", "api_key": "k1"}, {"name": "b"}, {"x": {"password": "p"}}]},
        {"config": {"auth": {"client_secret": "s"}}},
    )

    assert result.previous_values == {
        "contacts": [{"name": "a", "api_key": REDACTED_VALUE}, {"name": "b"}, {"x": {"password": REDACTED_VALUE}}]
    }
    assert result.new_values == {"config": {"auth": {"client_secret": REDACTED_VALUE}}}
    assert result.paths == (
        "new_values.config.auth.client_secret",
        "previous_values.contacts[0].api_key",
        "previous_values.contacts[2].x.password",
    )


def test_redaction_reaches_ten_levels() -> None:
    nested: dict = {"password": "p"}
    for _ in range(9):
        nested = {"n": nested}

    result = redact(None, nested)

    assert result.paths == ("new_values" + ".n" * 9 + ".password",)


def test_input_is_not_mutated() -> None:
    original = {"password": "p", "items": [{"token": "t"}]}
    snapshot = copy.deepcopy(original)

    redact(original, original)

    assert original == snapshot


def test_paths_are_merged_sorted_and_deduplicated() -> None:
    result = redact(None, {"password": "p"}, existing_paths=["new_values.password", "new_values.a"])

    assert result.paths == ("new_values.a", "new_values.password")


def test_already_redacted_values_stay_stable() -> None:
    first = redact(None, {"password": "p"})
    second = redact(None, first.new_values, first.paths)

    assert second.new_values == first.new_values
    assert second.paths == first.paths


def test_none_values_are_kept() -> None:
    result = redact(None, None)

    assert result.previous_values is None
    assert result.new_values is None
    assert result.paths == ()

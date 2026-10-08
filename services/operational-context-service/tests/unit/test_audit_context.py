"""Autor y solicitud de los eventos de auditoría (feature 016; research R-04; T020)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

from operational_context_service import audit_context
from operational_context_service.observability import _current_trace_id


def _request(claims):
    return SimpleNamespace(state=SimpleNamespace(sio_claims=claims) if claims else SimpleNamespace())


def test_authenticated_request_binds_subject_and_username() -> None:
    claims = SimpleNamespace(subject="9f0c2f1e-1111-4222-8333-944455556666", preferred_username="u" * 200)

    async def scenario():
        await audit_context.bind_audit_actor(_request(claims))
        return audit_context.current_actor()

    actor = asyncio.run(scenario())

    assert actor.subject == claims.subject
    assert actor.username == "u" * audit_context.USERNAME_MAX_LENGTH


def test_without_token_there_is_no_actor() -> None:
    async def scenario():
        await audit_context.bind_audit_actor(_request(None))
        return audit_context.current_actor()

    assert asyncio.run(scenario()) is None


def test_request_id_is_the_trace_id_as_uuid() -> None:
    token = _current_trace_id.set("0123456789abcdef0123456789abcdef")
    try:
        assert audit_context.current_request_id() == UUID("0123456789abcdef0123456789abcdef")
    finally:
        _current_trace_id.reset(token)


def test_invalid_or_missing_trace_id_gives_no_request_id() -> None:
    token = _current_trace_id.set("no-es-un-uuid")
    try:
        assert audit_context.current_request_id() is None
    finally:
        _current_trace_id.reset(token)
    assert audit_context.current_request_id() is None

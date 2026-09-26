"""Dobles en memoria de los puertos de aplicación, solo para pruebas unitarias."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
    NotFoundError,
    VersionConflictError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.organization_identity import OrganizationIdentity
from party_identity_service.domain.person_identity import PersonIdentity


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryRuleRepository:
    """Reglas activas por (tipo de parte, país, sigla)."""

    def __init__(self, rules: list[IdentificationRule] | None = None) -> None:
        self.rules = list(rules or [])

    def list_active_rules_by_sigla(self, *, party_kind, country_id, sigla) -> list[IdentificationRule]:
        return [
            rule
            for rule in self.rules
            if rule.party_kind == party_kind
            and rule.country_id == country_id
            and rule.sigla == sigla
        ]


class _InMemoryIdentityRepository:
    identity_keys: tuple[str, str, str]
    entity_class: type

    def __init__(self) -> None:
        self.items: dict[UUID, Any] = {}
        self.writes = 0

    def get_by_id(self, entity_id: UUID):
        return self.items.get(entity_id)

    def list_all(self, *, page, page_size, status="ACTIVE", **filters) -> PageResult:
        items = [item for item in self.items.values() if item.status == status]
        return PageResult(items=items, page=page, page_size=page_size, total_records=len(items))

    def create(self, *, actor_id: str, **values):
        self._check_duplicate(values, exclude=None)
        now = _now()
        entity = self.entity_class(
            id=uuid4(),
            status="ACTIVE",
            version=1,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.items[entity.id] = entity
        self.writes += 1
        return entity

    def update(self, entity_id: UUID, *, expected_version: int, values: dict, actor_id: str):
        current = self.items.get(entity_id)
        if current is None:
            raise NotFoundError
        if current.version != expected_version:
            raise VersionConflictError
        merged = {**{key: getattr(current, key) for key in self.identity_keys}, **values}
        self._check_duplicate(merged, exclude=entity_id)
        updated = replace(
            current,
            **values,
            version=current.version + 1,
            updated_by=actor_id,
            updated_at=_now(),
        )
        self.items[entity_id] = updated
        self.writes += 1
        return updated

    def set_status(self, entity_id: UUID, *, expected_version: int, status: str, actor_id: str):
        return self.update(entity_id, expected_version=expected_version, values={"status": status}, actor_id=actor_id)

    def _check_duplicate(self, values: dict, exclude: UUID | None) -> None:
        key = tuple(values[name] for name in self.identity_keys)
        for item in self.items.values():
            if item.id != exclude and tuple(getattr(item, name) for name in self.identity_keys) == key:
                raise DuplicateIdentificationError


class InMemoryPersonRepository(_InMemoryIdentityRepository):
    identity_keys = ("identification_country_id", "identification_type", "identification_number")
    entity_class = PersonIdentity


class InMemoryOrganizationRepository(_InMemoryIdentityRepository):
    identity_keys = ("country_id", "identification_type", "identification_number")
    entity_class = OrganizationIdentity

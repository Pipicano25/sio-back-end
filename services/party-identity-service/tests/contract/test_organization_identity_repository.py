"""Pruebas de persistencia para identidades de organizaciones."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    OrganizationIdentityConflictError,
    OrganizationIdentityVersionConflictError,
)
from party_identity_service.infrastructure.models import (
    OrganizationIdentityModel,
)
from party_identity_service.infrastructure.organization_identity_repository import (
    SQLAlchemyOrganizationIdentityRepository,
)


COUNTRY_ID = UUID("cf160c2d-b6de-4ef5-9257-a0a8539058d9")
ACTOR_ID = "00000000-0000-0000-0000-000000000001"


def test_create_persists_organization_without_verification_digit(
    db_session: Session,
) -> None:
    """Comprueba persistencia y ausencia de DV separado."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        db_session,
    )

    organization = repository.create(
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="900123456-7",
        legal_name="SIO Demo S.A.S.",
        trade_name="SIO Demo",
        organization_type="SAS",
        registration_status="ACTIVE",
        website="https://example.com",
        actor_id=ACTOR_ID,
    )

    stored = db_session.get(
        OrganizationIdentityModel,
        organization.id,
    )

    assert stored is not None
    assert not hasattr(
        stored,
        "verification_digit",
    )

    assert stored.country_id == COUNTRY_ID
    assert stored.identification_type == "NIT"
    assert stored.identification_number == "900123456-7"
    assert stored.legal_name == "SIO Demo S.A.S."
    assert stored.version == 1
    assert str(stored.created_by) == ACTOR_ID
    assert str(stored.updated_by) == ACTOR_ID


def test_create_rejects_duplicate_organization_identification(
    db_session: Session,
) -> None:
    """Comprueba unicidad por país, tipo y número."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        db_session,
    )

    repository.create(
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="900123456-7",
        legal_name="SIO Demo S.A.S.",
        trade_name=None,
        organization_type=None,
        registration_status=None,
        website=None,
        actor_id=ACTOR_ID,
    )

    with pytest.raises(
        OrganizationIdentityConflictError,
    ):
        repository.create(
            country_id=COUNTRY_ID,
            identification_type="NIT",
            identification_number="900123456-7",
            legal_name="SIO Demo Duplicada S.A.S.",
            trade_name=None,
            organization_type=None,
            registration_status=None,
            website=None,
            actor_id=ACTOR_ID,
        )


def test_update_changes_organization_and_increments_version(
    db_session: Session,
) -> None:
    """Comprueba actualización, auditoría y versión."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        db_session,
    )

    created = repository.create(
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="900123456-7",
        legal_name="SIO Demo S.A.S.",
        trade_name="SIO Demo",
        organization_type="SAS",
        registration_status="ACTIVE",
        website="https://example.com",
        actor_id=ACTOR_ID,
    )

    updated = repository.update(
        created.id,
        expected_version=1,
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="800123456-1",
        legal_name="SIO Demo Colombia S.A.S.",
        trade_name="SIO Demo Colombia",
        organization_type="SAS",
        registration_status="ACTIVE",
        website="https://example.co",
        actor_id=ACTOR_ID,
    )

    assert updated is not None
    assert updated.id == created.id
    assert updated.identification_number == "800123456-1"
    assert updated.legal_name == "SIO Demo Colombia S.A.S."
    assert updated.version == 2


def test_update_rejects_stale_version(
    db_session: Session,
) -> None:
    """Comprueba conflicto de concurrencia en actualización."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        db_session,
    )

    created = repository.create(
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="900123456-7",
        legal_name="SIO Demo S.A.S.",
        trade_name=None,
        organization_type=None,
        registration_status=None,
        website=None,
        actor_id=ACTOR_ID,
    )

    with pytest.raises(
        OrganizationIdentityVersionConflictError,
    ):
        repository.update(
            created.id,
            expected_version=2,
            country_id=COUNTRY_ID,
            identification_type="NIT",
            identification_number="900123456-7",
            legal_name="SIO Demo S.A.S.",
            trade_name=None,
            organization_type=None,
            registration_status=None,
            website=None,
            actor_id=ACTOR_ID,
        )


def test_update_returns_none_when_organization_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba actualización de organización inexistente."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        db_session,
    )

    result = repository.update(
        uuid4(),
        expected_version=1,
        country_id=COUNTRY_ID,
        identification_type="NIT",
        identification_number="900123456-7",
        legal_name="SIO Demo S.A.S.",
        trade_name=None,
        organization_type=None,
        registration_status=None,
        website=None,
        actor_id=ACTOR_ID,
    )

    assert result is None

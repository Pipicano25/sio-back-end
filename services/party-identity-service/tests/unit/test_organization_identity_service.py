"""Pruebas de validación para identidades de organizaciones."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from party_identity_service.application.exceptions import (
    InvalidIdentificationNumberError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)
from party_identity_service.domain.organization_identity import (
    OrganizationIdentity,
)


COUNTRY_ID = UUID("cf160c2d-b6de-4ef5-9257-a0a8539058d9")
ACTOR_ID = "00000000-0000-0000-0000-000000000001"


class FakeCountryValidator:
    """Validador de país que siempre encuentra el país."""

    def exists(
        self,
        country_id: UUID,
    ) -> bool:
        """Retorna existencia del país."""
        return country_id == COUNTRY_ID


class FakeIdentificationTypeRuleRepository:
    """Repositorio de reglas activo para organizaciones colombianas."""

    def __init__(self) -> None:
        """Inicializa una regla NIT activa."""
        self.rule = IdentificationRule(
            party_kind="ORGANIZATION",
            country_id=COUNTRY_ID,
            identification_type="TAX_ID",
            sigla="NIT",
            pattern="^[A-Z0-9]{4,11}-[0-9]$",
            description="NIT con guion y digito de verificacion.",
        )

    def list_active_rules_by_sigla(
        self,
        *,
        party_kind: str,
        country_id: UUID,
        sigla: str,
    ) -> list[IdentificationRule]:
        """Retorna reglas activas por sigla."""
        if (
            party_kind == "ORGANIZATION"
            and country_id == COUNTRY_ID
            and sigla == "NIT"
        ):
            return [
                self.rule,
            ]

        return []

    def has_active_rules(
        self,
        *,
        party_kind: str,
        country_id: UUID,
    ) -> bool:
        """Indica si hay reglas activas para el país."""
        return party_kind == "ORGANIZATION" and country_id == COUNTRY_ID


class FakeOrganizationIdentityRepository:
    """Repositorio falso para verificar llamadas de persistencia."""

    def __init__(self) -> None:
        """Inicializa contadores de llamadas."""
        self.created_payload = None
        self.updated_payload = None

    def list_all(self, **kwargs):
        """No usado en estas pruebas."""
        raise NotImplementedError

    def get_by_id(self, organization_identity_id: UUID):
        """No usado en estas pruebas."""
        raise NotImplementedError

    def create(self, **kwargs) -> OrganizationIdentity:
        """Captura payload de creación."""
        self.created_payload = kwargs
        return self._build_identity(
            id=uuid4(),
            **kwargs,
        )

    def update(
        self,
        organization_identity_id: UUID,
        **kwargs,
    ) -> OrganizationIdentity:
        """Captura payload de actualización."""
        self.updated_payload = {
            "organization_identity_id": organization_identity_id,
            **kwargs,
        }
        return self._build_identity(
            id=organization_identity_id,
            **kwargs,
        )

    @staticmethod
    def _build_identity(
        *,
        id: UUID,
        country_id: UUID,
        identification_type: str,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
        expected_version: int | None = None,
    ) -> OrganizationIdentity:
        """Construye una entidad de dominio."""
        now = datetime.now(
            timezone.utc,
        )
        actor_uuid = UUID(
            actor_id,
        )
        return OrganizationIdentity(
            id=id,
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            legal_name=legal_name,
            trade_name=trade_name,
            organization_type=organization_type,
            registration_status=registration_status,
            website=website,
            version=expected_version or 1,
            created_by=actor_uuid,
            updated_by=actor_uuid,
            created_at=now,
            updated_at=now,
        )


@pytest.fixture
def repository() -> FakeOrganizationIdentityRepository:
    """Repositorio falso compartido."""
    return FakeOrganizationIdentityRepository()


@pytest.fixture
def service(
    repository: FakeOrganizationIdentityRepository,
) -> OrganizationIdentityService:
    """Servicio con dependencias falsas."""
    return OrganizationIdentityService(
        repository=repository,
        identification_rule_repository=FakeIdentificationTypeRuleRepository(),
        country_validator=FakeCountryValidator(),
    )


def base_payload() -> dict:
    """Payload válido de organización."""
    return {
        "country_id": COUNTRY_ID,
        "identification_type": "NIT",
        "identification_number": "900123456-7",
        "legal_name": "SIO Demo S.A.S.",
        "trade_name": "SIO Demo",
        "organization_type": "SAS",
        "registration_status": "ACTIVE",
        "website": "https://example.com",
        "actor_id": ACTOR_ID,
    }


def test_create_rejects_identification_number_that_does_not_match_rule(
    service: OrganizationIdentityService,
    repository: FakeOrganizationIdentityRepository,
) -> None:
    """Crear organización rechaza número inválido para su tipo."""
    payload = {
        **base_payload(),
        "identification_number": "900123456",
    }

    with pytest.raises(InvalidIdentificationNumberError):
        service.create(
            **payload,
        )

    assert repository.created_payload is None


def test_update_rejects_identification_number_that_does_not_match_rule(
    service: OrganizationIdentityService,
    repository: FakeOrganizationIdentityRepository,
) -> None:
    """Actualizar organización rechaza número inválido para su tipo."""
    payload = {
        **base_payload(),
        "identification_number": "900123456",
    }

    with pytest.raises(InvalidIdentificationNumberError):
        service.update(
            uuid4(),
            expected_version=1,
            **payload,
        )

    assert repository.updated_payload is None


def test_create_accepts_identification_number_that_matches_rule(
    service: OrganizationIdentityService,
    repository: FakeOrganizationIdentityRepository,
) -> None:
    """Crear organización acepta número válido para su tipo."""
    result = service.create(
        **base_payload(),
    )

    assert result.identification_number == "900123456-7"
    assert repository.created_payload is not None

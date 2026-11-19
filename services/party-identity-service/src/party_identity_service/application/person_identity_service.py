"""Casos de uso para identidades globales de personas."""

import logging
from datetime import date
from uuid import UUID

from party_identity_service.application.partial_update import UNSET
from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    InvalidStatusTransitionError,
    NotFoundError,
    VersionConflictError,
)
from party_identity_service.application.identification_rules import (
    match_identification_number,
    normalize_code,
    normalize_identification_number,
    validate_age,
    validate_birth_date,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryDirectory,
    IdentificationTypeRuleRepository,
    PersonIdentityRepository,
)
from party_identity_service.domain.masking import mask_identification_number
from party_identity_service.domain.person_identity import (
    IdentityStatus,
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)

logger = logging.getLogger("party_identity_service")

PARTY_KIND = "PERSON"
IDENTIFICATION_FIELDS = (
    "identification_country_id",
    "identification_type",
    "identification_number",
)


class PersonIdentityService:
    """Orquesta casos de uso de identidades de personas."""

    def __init__(
        self,
        repository: PersonIdentityRepository,
        identification_rule_repository: IdentificationTypeRuleRepository,
        country_directory: CountryDirectory,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Puerto de persistencia de identidades de persona.
            identification_rule_repository: Puerto de reglas de identificación.
            country_directory: Puerto hacia Geography Service.
        """
        self.repository = repository
        self.identification_rule_repository = identification_rule_repository
        self.country_directory = country_directory

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        identification_country_id: UUID | None = None,
        identification_type: PersonIdentificationType | None = None,
        verification_status: PersonVerificationStatus | None = None,
        status: IdentityStatus = "ACTIVE",
    ) -> PageResult[PersonIdentity]:
        """Obtiene identidades de persona; por defecto solo `ACTIVE` (DS-02)."""
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            identification_country_id=identification_country_id,
            identification_type=(
                normalize_code(identification_type)
                if identification_type
                else None
            ),
            verification_status=verification_status,
            status=status,
        )

    def get_by_id(
        self,
        person_identity_id: UUID,
    ) -> PersonIdentity:
        """Obtiene una identidad de persona en cualquier estado.

        Raises:
            NotFoundError: Si no existe.
        """
        person_identity = self.repository.get_by_id(
            person_identity_id,
        )

        if person_identity is None:
            raise NotFoundError("La persona solicitada no existe.")

        return person_identity

    def create(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        first_name: str,
        middle_name: str | None,
        last_name: str,
        second_last_name: str | None,
        birth_date: date | None,
        verification_status: PersonVerificationStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Crea una identidad global de persona."""
        identification_type = normalize_code(identification_type)
        identification_number = normalize_identification_number(
            identification_number,
        )
        validate_birth_date(birth_date)
        self._validate_country(identification_country_id)
        self._validate_identification(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            birth_date=birth_date,
        )

        person_identity = self.repository.create(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            second_last_name=second_last_name,
            birth_date=birth_date,
            verification_status=verification_status,
            actor_id=actor_id,
        )
        logger.info(
            "Persona creada id=%s identificacion=%s %s",
            person_identity.id,
            identification_type,
            mask_identification_number(identification_number),
        )

        return person_identity

    def update(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int | None,
        identification_country_id: UUID = UNSET,
        identification_type: PersonIdentificationType = UNSET,
        identification_number: str = UNSET,
        first_name: str = UNSET,
        middle_name: str | None = UNSET,
        last_name: str = UNSET,
        second_last_name: str | None = UNSET,
        birth_date: date | None = UNSET,
        verification_status: PersonVerificationStatus = UNSET,
        actor_id: str,
    ) -> PersonIdentity:
        """Modifica una persona (FR-025, FR-026, FR-029).

        Orden: existencia → versión esperada → sin cambios (no escribe) →
        revalidación solo de lo que cambió → escritura.
        """
        current = self.get_by_id(person_identity_id)

        if expected_version is not None and current.version != expected_version:
            raise VersionConflictError
        # D28: un campo no enviado conserva su valor.
        identification_country_id = current.identification_country_id if identification_country_id is UNSET else identification_country_id
        identification_type = current.identification_type if identification_type is UNSET else identification_type
        identification_number = current.identification_number if identification_number is UNSET else identification_number
        first_name = current.first_name if first_name is UNSET else first_name
        middle_name = current.middle_name if middle_name is UNSET else middle_name
        last_name = current.last_name if last_name is UNSET else last_name
        second_last_name = current.second_last_name if second_last_name is UNSET else second_last_name
        birth_date = current.birth_date if birth_date is UNSET else birth_date
        verification_status = current.verification_status if verification_status is UNSET else verification_status

        requested = {
            "identification_country_id": identification_country_id,
            "identification_type": normalize_code(identification_type),
            "identification_number": normalize_identification_number(
                identification_number,
            ),
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "second_last_name": second_last_name,
            "birth_date": birth_date,
            "verification_status": verification_status,
        }
        changes = {
            field: value
            for field, value in requested.items()
            if getattr(current, field) != value
        }

        if not changes:
            return current

        if "birth_date" in changes:
            validate_birth_date(birth_date)

        identification_changed = any(
            field in changes
            for field in IDENTIFICATION_FIELDS
        )

        if identification_changed:
            self._validate_country(requested["identification_country_id"])

        if identification_changed or "birth_date" in changes:
            # Si solo cambió la fecha, la edad se recalcula localmente con la
            # regla aplicable actual, sin consultar Geography (DS-06).
            self._validate_identification(
                identification_country_id=requested["identification_country_id"],
                identification_type=requested["identification_type"],
                identification_number=requested["identification_number"],
                birth_date=birth_date,
                revalidate_number=identification_changed,
            )

        return self.repository.update(
            person_identity_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def deactivate(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> PersonIdentity:
        """Inactiva una persona sin eliminarla (DS-11)."""
        return self._change_status(
            person_identity_id,
            expected_version=expected_version,
            target="INACTIVE",
            actor_id=actor_id,
        )

    def reactivate(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> PersonIdentity:
        """Reactiva una persona inactiva (DS-11)."""
        return self._change_status(
            person_identity_id,
            expected_version=expected_version,
            target="ACTIVE",
            actor_id=actor_id,
        )

    def _change_status(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int | None,
        target: IdentityStatus,
        actor_id: str,
    ) -> PersonIdentity:
        current = self.get_by_id(person_identity_id)

        if expected_version is not None and current.version != expected_version:
            raise VersionConflictError

        if current.status == target:
            raise InvalidStatusTransitionError(
                f"La persona ya se encuentra en estado {target}."
            )

        return self.repository.set_status(
            person_identity_id,
            expected_version=expected_version,
            status=target,
            actor_id=actor_id,
        )

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        """Valida que el país exista en Geography Service."""
        if not self.country_directory.exists(country_id):
            raise CountryNotFoundError

    def _validate_identification(
        self,
        *,
        identification_country_id: UUID,
        identification_type: str,
        identification_number: str,
        birth_date: date | None,
        revalidate_number: bool = True,
    ) -> None:
        """Valida el número y la edad contra las reglas activas de la sigla.

        Con `revalidate_number=False` (solo cambió `birth_date`) el número
        vigente no se vuelve a exigir: la edad se valida con las reglas que el
        número cumple actualmente.
        """
        rules = self.identification_rule_repository.list_active_rules_by_sigla(
            party_kind=PARTY_KIND,
            country_id=identification_country_id,
            sigla=identification_type,
        )

        if revalidate_number:
            matching = match_identification_number(
                rules,
                identification_number,
                sigla=identification_type,
            )
        else:
            matching = [
                rule
                for rule in rules
                if rule.validate(identification_number)
            ]

        validate_age(
            matching,
            birth_date,
        )

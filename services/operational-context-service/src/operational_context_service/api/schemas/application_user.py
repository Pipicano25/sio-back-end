"""Esquemas HTTP de usuarios operativos (`contracts/rest-api.md` de la feature 005, §1).

La cuenta de Keycloak se indica por `keycloak_user_id` (`sub`) **o** por
`username` (exactamente uno); solo se guarda el `sub` (DS-03). La persona
(`person_identity_id`) es obligatoria (DS-16). No se reciben ni devuelven
nombres ni identificación de la persona: pertenecen a Party Identity.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from operational_context_service.api.schemas.common import OptionalEmail, StrictModel, Version
from operational_context_service.application.exceptions import ImmutableFieldError
from operational_context_service.domain.status import EntityStatus


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: Any) -> Any:
    value = _strip(value)
    return value or None if isinstance(value, str) else value


KeycloakSub = Annotated[
    Annotated[str, Field(min_length=1, max_length=255)] | None,
    BeforeValidator(_blank_to_none),
]
Username = Annotated[
    Annotated[str, Field(min_length=1, max_length=255)] | None,
    BeforeValidator(_blank_to_none),
]
DisplayName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=160)]


class ApplicationUserCreate(StrictModel):
    """Alta de usuario operativo en la empresa de la ruta."""

    keycloak_user_id: KeycloakSub = None
    username: Username = None
    person_identity_id: UUID
    display_name: DisplayName
    reference_email: OptionalEmail = None

    @model_validator(mode="after")
    def _exactly_one_account_reference(self) -> "ApplicationUserCreate":
        if (self.keycloak_user_id is None) == (self.username is None):
            raise ValueError(
                "Indique exactamente uno de keycloak_user_id o username para identificar la cuenta."
            )
        return self


IMMUTABLE_FIELDS = ("keycloak_user_id", "person_identity_id", "company_id")


class ApplicationUserUpdate(StrictModel):
    """`PUT` de usuario operativo: solo datos de referencia propios de SIO (FR-013)."""

    display_name: DisplayName
    reference_email: OptionalEmail = None
    version: Version

    @model_validator(mode="before")
    @classmethod
    def _reject_immutable_fields(cls, data: Any) -> Any:
        # `ImmutableFieldError` no es `ValueError`: Pydantic no la envuelve y la
        # traduce `api/errors.py` a `422 IMMUTABLE_FIELD` (no VALIDATION_ERROR).
        if isinstance(data, dict):
            for field in IMMUTABLE_FIELDS:
                if field in data:
                    raise ImmutableFieldError(
                        "El usuario operativo no permite cambiar su cuenta, su persona ni su empresa.",
                        field=field,
                    )
        return data


class ApplicationUserResponse(BaseModel):
    """Representación de un usuario operativo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    company_status: EntityStatus
    keycloak_user_id: str
    person_identity_id: UUID
    display_name: str
    reference_email: str | None
    status: EntityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

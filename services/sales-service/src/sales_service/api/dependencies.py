"""Dependencias FastAPI: sesión, servicios, puertos inyectados y alcance (R-02).

Las fábricas de puertos viven en `app.state` (adaptadores HTTP reales; dobles solo en
pruebas, por DI). Cada solicitud usa una sesión; los servicios confirman o revierten.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request

from sales_service.api.identity import HumanIdentity, require_human_user
from sales_service.application.branch_access import require_membership
from sales_service.application.cancellation_service import CancellationService
from sales_service.application.confirmation_service import ConfirmationService
from sales_service.application.exceptions import ValidationFailedError, field_error
from sales_service.application.availability import AvailabilityService
from sales_service.application.operation_engine import OperationEngine
from sales_service.application.ports import AccessDirectory, Directories, InventoryGateway
from sales_service.application.sale_service import Actor, SaleService
from sales_service.application.query_service import QueryService
from sales_service.application.reference_validation import ReferenceResolver
from sales_service.application.sequence_service import SequenceService
from sales_service.infrastructure.database import Database
from sales_service.infrastructure.repository import SaleRepository
from sales_service.infrastructure.sequence_repository import SequenceRepository

DirectoriesFactory = Callable[[], Directories]
InventoryFactory = Callable[[], InventoryGateway]
AccessFactory = Callable[[Request], AccessDirectory]

_PRINTABLE = re.compile(r"^[\x21-\x7e]{1,150}$")
IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_DESCRIPTION = (
    "Clave de idempotencia de la operación (de 1 a 150 caracteres ASCII imprimibles, sin espacios). "
    "Repetir la misma clave devuelve el mismo resultado sin duplicar efectos; una operación nueva usa otra clave."
)


class Services:
    """Servicios de aplicación de una solicitud, sobre la misma sesión."""

    def __init__(self, request: Request, session) -> None:
        state = request.app.state
        database: Database = state.database
        clock: Callable[[], datetime] = state.clock
        self.repository = SaleRepository(session, lock_timeout_ms=database.lock_timeout_ms)
        self.sequences = SequenceRepository(session)
        self._request = request
        self._clock = clock
        self._directories: Directories | None = None
        self._inventory: InventoryGateway | None = None

    @property
    def directories(self) -> Directories:
        if self._directories is None:
            self._directories = self._request.app.state.directories_factory()
        return self._directories

    @property
    def inventory(self) -> InventoryGateway:
        if self._inventory is None:
            self._inventory = self._request.app.state.inventory_factory()
        return self._inventory

    def resolver(self) -> ReferenceResolver:
        settings = self._request.app.state.settings
        return ReferenceResolver(self.directories, concurrency=settings.lookup_concurrency, clock=self._clock)

    def engine(self) -> OperationEngine:
        return OperationEngine(self.repository, self.sequences, self.inventory, clock=self._clock)

    def sales(self) -> SaleService:
        return SaleService(self.repository, self.resolver(), clock=self._clock)

    def confirmations(self) -> ConfirmationService:
        return ConfirmationService(
            self.repository, self.sequences, self.resolver(), self.engine(), self.inventory, clock=self._clock
        )

    def cancellations(self) -> CancellationService:
        return CancellationService(self.repository, self.confirmations(), self.engine(), clock=self._clock)

    def availability(self) -> AvailabilityService:
        return AvailabilityService(self.repository, self.inventory)

    def sequence_service(self) -> SequenceService:
        return SequenceService(
            self.repository, self.sequences, self.directories.operational_context, clock=self._clock
        )

    def queries(self) -> QueryService:
        return QueryService(self.repository)


def get_services(request: Request) -> Iterator[Services]:
    database: Database = request.app.state.database
    with database.session_factory() as session:
        yield Services(request, session)


def access_directory(request: Request) -> AccessDirectory:
    factory: AccessFactory = request.app.state.access_factory
    return factory(request)


def get_actor(request: Request, identity: Annotated[HumanIdentity, Depends(require_human_user)]) -> Actor:
    """Usuario humano (RC-05) con su acceso operativo propio."""
    return Actor(subject=identity.subject, access=access_directory(request))


def company_reader(company_id: UUID, actor: Annotated[Actor, Depends(get_actor)]) -> UUID:
    """Lecturas: membresía `ACTIVE` en la empresa (no se exige asignación a la sucursal, DS-09)."""
    require_membership(actor.access, company_id)
    return company_id


def idempotency_key(
    # Declarada con `Header` para que OpenAPI y Swagger la muestren. El valor por omisión `None` mantiene la
    # validación propia (`IDEMPOTENCY_KEY_REQUIRED`, `INVALID_FORMAT`); `openapi.py` la marca obligatoria.
    value: Annotated[
        str | None, Header(alias=IDEMPOTENCY_HEADER, description=IDEMPOTENCY_DESCRIPTION, examples=["venta-0001"])
    ] = None,
) -> str:
    if value is None or not value.strip():
        raise ValidationFailedError(
            [field_error("Idempotency-Key", "IDEMPOTENCY_KEY_REQUIRED", "La cabecera Idempotency-Key es obligatoria.")]
        )
    value = value.strip()
    if not _PRINTABLE.match(value):
        raise ValidationFailedError(
            [
                field_error(
                    "Idempotency-Key",
                    "INVALID_FORMAT",
                    "Idempotency-Key admite de 1 a 150 caracteres ASCII imprimibles sin espacios.",
                )
            ]
        )
    return value


def correlation_id(request: Request) -> UUID | None:
    value = request.headers.get("x-correlation-id")
    if value is None or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError:
        raise ValidationFailedError(
            [field_error("X-Correlation-Id", "INVALID_FORMAT", "X-Correlation-Id debe ser un UUID.")]
        ) from None


ServicesDep = Annotated[Services, Depends(get_services)]
ActorDep = Annotated[Actor, Depends(get_actor)]
CompanyReader = Annotated[UUID, Depends(company_reader)]
IdempotencyKey = Annotated[str, Depends(idempotency_key)]
CorrelationId = Annotated[UUID | None, Depends(correlation_id)]

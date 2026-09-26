"""Dobles de los puertos de Party Identity y Geography (solo pruebas, R-12).

Reproducen exactamente los resultados del contrato: registro `ACTIVE` o
`INACTIVE`, `None` (404) y `DependencyUnavailableError` (proveedor caído o
`401`/`403`). Registran cada llamada y, cuando se les da una sesión, si había
una transacción abierta en ese momento (R-09).
"""

from __future__ import annotations

import threading
from typing import Any
from uuid import UUID, uuid4

from operational_context_service.application.exceptions import (
    GEOGRAPHY_UNAVAILABLE,
    PARTY_IDENTITY_UNAVAILABLE,
    DependencyUnavailableError,
)
from operational_context_service.application.ports import CityRef, DivisionRef, ExternalRef


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.in_transaction_at_call: list[bool] = []
        self.watched_sessions: list[Any] = []
        self.mode = "ok"
        self.hold: threading.Event | None = None
        self.called: threading.Event = threading.Event()

    def _record(self, name: str, value: Any) -> None:
        self.calls.append((name, value))
        self.in_transaction_at_call.append(
            any(session.in_transaction() for session in self.watched_sessions)
        )
        self.called.set()

        if self.hold is not None:
            self.hold.wait(timeout=10)

    def count(self, name: str | None = None) -> int:
        return sum(1 for call, _ in self.calls if name is None or call == name)

    def reset(self) -> None:
        self.calls.clear()
        self.in_transaction_at_call.clear()


class FakeOrganizationDirectory(_Recorder):
    """Doble de `OrganizationDirectory`."""

    def __init__(self) -> None:
        super().__init__()
        self.organizations: dict[UUID, str] = {}

    def add(self, status: str = "ACTIVE") -> UUID:
        organization_id = uuid4()
        self.organizations[organization_id] = status
        return organization_id

    def get_organization(self, organization_identity_id: UUID) -> ExternalRef | None:
        self._record("get_organization", organization_identity_id)

        if self.mode == "unavailable":
            raise DependencyUnavailableError(
                provider="party-identity",
                cause=PARTY_IDENTITY_UNAVAILABLE,
                operation="get_organization",
            )

        status = self.organizations.get(organization_identity_id)

        return None if status is None else ExternalRef(id=organization_identity_id, status=status)


class FakeGeographyDirectory(_Recorder):
    """Doble de `GeographyDirectory` con un país, divisiones y ciudades configurables."""

    def __init__(self) -> None:
        super().__init__()
        self.countries: dict[UUID, str] = {}
        self.divisions: dict[UUID, tuple[str, UUID]] = {}
        self.cities: dict[UUID, tuple[str, UUID, UUID | None]] = {}

    def add_country(self, status: str = "ACTIVE", country_id: UUID | None = None) -> UUID:
        country_id = country_id or uuid4()
        self.countries[country_id] = status
        return country_id

    def add_division(
        self,
        country_id: UUID,
        status: str = "ACTIVE",
        division_id: UUID | None = None,
    ) -> UUID:
        division_id = division_id or uuid4()
        self.divisions[division_id] = (status, country_id)
        return division_id

    def add_city(
        self,
        country_id: UUID,
        division_id: UUID | None,
        status: str = "ACTIVE",
        city_id: UUID | None = None,
    ) -> UUID:
        city_id = city_id or uuid4()
        self.cities[city_id] = (status, country_id, division_id)
        return city_id

    def _check(self, operation: str) -> None:
        if self.mode == "unavailable":
            raise DependencyUnavailableError(
                provider="geography",
                cause=GEOGRAPHY_UNAVAILABLE,
                operation=operation,
            )

    def get_country(self, country_id: UUID) -> ExternalRef | None:
        self._record("get_country", country_id)
        self._check("get_country")
        status = self.countries.get(country_id)
        return None if status is None else ExternalRef(id=country_id, status=status)

    def get_administrative_division(self, division_id: UUID) -> DivisionRef | None:
        self._record("get_administrative_division", division_id)
        self._check("get_administrative_division")
        record = self.divisions.get(division_id)
        if record is None:
            return None
        status, country_id = record
        return DivisionRef(id=division_id, status=status, country_id=country_id)

    def get_city(self, city_id: UUID) -> CityRef | None:
        self._record("get_city", city_id)
        self._check("get_city")
        record = self.cities.get(city_id)
        if record is None:
            return None
        status, country_id, division_id = record
        return CityRef(
            id=city_id,
            status=status,
            country_id=country_id,
            administrative_division_id=division_id,
        )


class GeographyFixture:
    """Datos geográficos ficticios coherentes para las pruebas.

    Colombia → Antioquia → Medellín; Colombia → Cundinamarca → Bogotá;
    Perú → Lima (división) → Lima (ciudad); y una ciudad sin división.
    """

    def __init__(self, geography: FakeGeographyDirectory) -> None:
        self.colombia = geography.add_country()
        self.peru = geography.add_country()
        self.antioquia = geography.add_division(self.colombia)
        self.cundinamarca = geography.add_division(self.colombia)
        self.lima_division = geography.add_division(self.peru)
        self.medellin = geography.add_city(self.colombia, self.antioquia)
        self.bogota = geography.add_city(self.colombia, self.cundinamarca)
        self.lima = geography.add_city(self.peru, self.lima_division)
        self.city_without_division = geography.add_city(self.colombia, None)
        self.inactive_country = geography.add_country("INACTIVE")
        self.inactive_division = geography.add_division(self.colombia, "INACTIVE")
        self.inactive_city = geography.add_city(self.colombia, self.antioquia, "INACTIVE")

    def medellin_location(self) -> dict[str, str]:
        return {
            "country_id": str(self.colombia),
            "administrative_division_id": str(self.antioquia),
            "city_id": str(self.medellin),
        }

    def bogota_location(self) -> dict[str, str]:
        return {
            "country_id": str(self.colombia),
            "administrative_division_id": str(self.cundinamarca),
            "city_id": str(self.bogota),
        }

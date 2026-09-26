"""Unicidad bajo concurrencia (RC-02): dos altas simultáneas, solo una persiste."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from sqlalchemy import text

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
)
from party_identity_service.infrastructure.person_identity_repository import (
    SQLAlchemyPersonIdentityRepository,
)
from tests.conftest import COLOMBIA_ID


def test_simultaneous_creates_with_same_identification(session_factory, test_engine) -> None:
    barrier = Barrier(2)

    def create(first_name: str) -> str:
        with session_factory() as session:
            repository = SQLAlchemyPersonIdentityRepository(session)
            barrier.wait()
            try:
                repository.create(
                    identification_country_id=COLOMBIA_ID,
                    identification_type="CC",
                    identification_number="1000000001",
                    first_name=first_name,
                    middle_name=None,
                    last_name="PRUEBA",
                    second_last_name=None,
                    birth_date=date(1990, 1, 1),
                    verification_status="UNVERIFIED",
                    actor_id="user-admin",
                )
                return "created"
            except DuplicateIdentificationError:
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(create, ["ANA", "LUIS"]))

    with test_engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM person_identities")).scalar_one()

    assert results == ["created", "duplicate"]
    assert count == 1

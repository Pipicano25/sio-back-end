"""Pruebas de salud (Principio V, R-19)."""

from sqlalchemy.exc import OperationalError


def test_live_is_minimal_and_public(anonymous) -> None:
    response = anonymous.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_with_database_available(anonymous) -> None:
    response = anonymous.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_without_database_is_503_without_internal_details(app, anonymous, monkeypatch) -> None:
    def fail() -> None:
        raise OperationalError("SELECT 1", {}, Exception("conexión rechazada en 10.0.0.1"))

    monkeypatch.setattr(app.state.database, "check_connection", fail)
    response = anonymous.get("/health/ready")

    assert response.status_code == 503
    assert "10.0.0.1" not in response.text
    assert "SELECT" not in response.text


def test_health_does_not_depend_on_geography(anonymous, fake_countries) -> None:
    fake_countries.mode = "unavailable"

    assert anonymous.get("/health/live").status_code == 200
    assert anonymous.get("/health/ready").status_code == 200
    assert fake_countries.calls == []

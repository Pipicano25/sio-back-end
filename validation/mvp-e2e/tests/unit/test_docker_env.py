"""T009 — Control de contenedores con restauración garantizada (sio_mvp.docker_env)."""

import json

import pytest

from sio_mvp.docker_env import ContainerState, DockerEnv, RestoreError

pytestmark = pytest.mark.unit


class FakeDocker:
    """Simula la CLI de Docker: estados por contenedor y registro de comandos."""

    def __init__(self, states, *, health_after_start="healthy", fail_start=()):
        self.states = {name: dict(state) for name, state in states.items()}
        self.calls = []
        self.health_after_start = health_after_start
        self.fail_start = set(fail_start)

    def __call__(self, args):
        self.calls.append(list(args))
        command, *rest = args
        if command == "inspect":
            name = rest[-1]
            state = self.states[name]
            payload = [
                {
                    "Name": f"/{name}",
                    "State": {
                        "Status": state["status"],
                        "Running": state["status"] == "running",
                        "StartedAt": state.get("started_at", "2026-10-09T00:00:00Z"),
                        **({"Health": {"Status": state["health"]}} if state.get("health") else {}),
                    },
                }
            ]
            return 0, json.dumps(payload)
        if command == "stop":
            self.states[rest[-1]].update(status="exited", health="unhealthy" if self.states[rest[-1]].get("health") else None)
            return 0, rest[-1]
        if command == "start":
            name = rest[-1]
            if name in self.fail_start:
                return 1, "error"
            state = self.states[name]
            state.update(status="running", started_at="2026-10-09T01:00:00Z")
            if state.get("health"):
                state["health"] = self.health_after_start
            return 0, name
        raise AssertionError(f"comando no permitido: {args}")


def make_env(fake, **kwargs):
    clock = {"now": 0.0}

    def sleep(seconds):
        clock["now"] += seconds

    return DockerEnv(runner=fake, sleep=sleep, clock=lambda: clock["now"], **kwargs), clock


def test_inspect_returns_status_health_and_started_at():
    fake = FakeDocker({"sio-sales-service": {"status": "running", "health": "healthy", "started_at": "T0"}})
    env, _ = make_env(fake)
    assert env.inspect("sio-sales-service") == ContainerState("sio-sales-service", "running", "healthy", "T0")


def test_stopped_restarts_in_finally_even_if_body_fails():
    fake = FakeDocker({"sio-inventory-service": {"status": "running", "health": "healthy"}})
    env, _ = make_env(fake)
    with pytest.raises(RuntimeError):
        with env.stopped("sio-inventory-service"):
            assert env.inspect("sio-inventory-service").status == "exited"
            raise RuntimeError("fallo del caso")
    assert fake.states["sio-inventory-service"]["status"] == "running"
    assert ["start", "sio-inventory-service"] in fake.calls


def test_stopped_waits_for_extra_health_check():
    fake = FakeDocker({"sio-audit-service": {"status": "running", "health": "healthy"}})
    env, _ = make_env(fake)
    checks = []

    def ready():
        checks.append(1)
        return len(checks) >= 3

    with env.stopped("sio-audit-service", health=ready):
        pass
    assert len(checks) == 3


def test_health_wait_is_limited_to_180_seconds():
    fake = FakeDocker({"sio-sales-db": {"status": "running", "health": "healthy"}}, health_after_start="starting")
    env, clock = make_env(fake)
    with pytest.raises(RestoreError):
        with env.stopped("sio-sales-db"):
            pass
    assert 180.0 <= clock["now"] <= 185.0


def test_container_without_healthcheck_only_needs_running():
    fake = FakeDocker({"sio-sales-reconciler": {"status": "running", "health": None}})
    env, _ = make_env(fake)
    with env.stopped("sio-sales-reconciler"):
        pass
    assert fake.states["sio-sales-reconciler"]["status"] == "running"


def test_restore_all_starts_only_containers_that_were_healthy_at_start():
    fake = FakeDocker(
        {
            "sio-a": {"status": "running", "health": "healthy"},
            "sio-b": {"status": "running", "health": "healthy"},
            "sio-c": {"status": "exited", "health": None},
            "sio-d": {"status": "running", "health": "unhealthy"},
        }
    )
    env, _ = make_env(fake)
    snapshot = env.snapshot(["sio-a", "sio-b", "sio-c", "sio-d"])
    fake.states["sio-a"].update(status="exited")
    fake.states["sio-d"].update(status="exited")
    report = env.restore_all(snapshot)
    assert report.restored == ["sio-a"]
    assert report.failed == []
    assert report.ok
    assert ["start", "sio-c"] not in fake.calls
    assert ["start", "sio-d"] not in fake.calls
    assert ["start", "sio-b"] not in fake.calls


def test_restore_all_reports_failures():
    fake = FakeDocker({"sio-a": {"status": "running", "health": "healthy"}}, fail_start={"sio-a"})
    env, _ = make_env(fake)
    snapshot = env.snapshot(["sio-a"])
    fake.states["sio-a"].update(status="exited")
    report = env.restore_all(snapshot)
    assert report.failed == ["sio-a"]
    assert not report.ok


def test_never_invokes_destructive_commands():
    fake = FakeDocker({"sio-a": {"status": "running", "health": "healthy"}})
    env, _ = make_env(fake)
    snapshot = env.snapshot(["sio-a"])
    with env.stopped("sio-a"):
        pass
    env.restore_all(snapshot)
    for call in fake.calls:
        assert call[0] in {"inspect", "stop", "start"}
        assert not {"rm", "down", "volume", "kill", "prune"} & set(call)
    with pytest.raises(ValueError):
        env.run(["rm", "sio-a"])
    with pytest.raises(ValueError):
        env.run(["volume", "rm", "x"])


def test_select_only_allows_single_select_statements():
    fake = FakeDocker({})
    env, _ = make_env(fake)
    for sql in ("UPDATE audit_outbox SET status='SENT'", "DELETE FROM x", "SELECT 1; DELETE FROM x", "  insert into x values (1)"):
        with pytest.raises(ValueError):
            env.select("sio-sales-db", "u", "d", sql)
    with pytest.raises(ValueError):
        env.run(["exec", "sio-sales-db", "sh", "-c", "rm -rf /"])

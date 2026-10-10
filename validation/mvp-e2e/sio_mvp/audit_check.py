"""Verificación de la auditoría del recorrido (research R-10; FR-012, FR-013, SC-003).

Por cada entidad del diario consulta su historial en Audit (`entity-history` de empresa o de
plataforma), espera la entrega de los workers (sondeo cada 2 s, acotado) y compara con la auditoría
esperada: cada acción exactamente una vez, actor y alcance correctos y orden por `occurred_at`. En
compras y ventas además localiza la acción por `correlation_id`. Después busca en esos eventos los
valores protegidos de la corrida y los campos de costo y margen en los eventos de Sales.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from .journal import ExpectedAudit

POLL_SECONDS = 2.0
COST_FIELDS = {
    "unit_cost_snapshot",
    "cost_total",
    "cost_known",
    "gross_margin_amount",
    "gross_margin_percentage",
    "gross_margin",
    "gross_margin_percent",
    "has_unknown_cost",
}
MARKERS = {"<registrado>", "<modificado>", "<eliminado>"}


class AuditSource(Protocol):
    def entity_history(self, scope: str, company_id: str | None, entity_type: str, entity_id: str) -> list[dict]: ...

    def by_correlation_id(self, company_id: str, correlation_id: str) -> list[dict]: ...


@dataclass(frozen=True)
class Absence:
    scope: str
    company_id: str | None
    entity_type: str
    entity_id: str
    action: str


@dataclass
class EntityResult:
    scope: str
    company_id: str | None
    entity_type: str
    entity_id: str
    expected: list[str]
    received: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    wrong_actor: list[str] = field(default_factory=list)
    wrong_scope: list[str] = field(default_factory=list)
    wrong_result: list[str] = field(default_factory=list)
    out_of_order: bool = False
    protected: list[str] = field(default_factory=list)
    cost_fields: list[str] = field(default_factory=list)
    unexpected_present: list[str] = field(default_factory=list)
    correlation_missing: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.duplicates
            or self.wrong_actor
            or self.wrong_scope
            or self.wrong_result
            or self.out_of_order
            or self.protected
            or self.cost_fields
            or self.unexpected_present
            or self.correlation_missing
        )


@dataclass
class AuditCheckResult:
    entities: list[EntityResult]
    waited_seconds: float

    @property
    def summary(self) -> dict[str, int]:
        return {
            "expected": sum(len(item.expected) for item in self.entities),
            "received": sum(len(item.received) for item in self.entities),
            "missing": sum(len(item.missing) for item in self.entities),
            "duplicates": sum(len(item.duplicates) for item in self.entities),
            "wrong_actor": sum(len(item.wrong_actor) for item in self.entities),
            "wrong_scope": sum(len(item.wrong_scope) for item in self.entities),
            "wrong_result": sum(len(item.wrong_result) for item in self.entities),
            "out_of_order": sum(1 for item in self.entities if item.out_of_order),
            "protected": sum(len(item.protected) for item in self.entities),
            "cost_fields": sum(len(item.cost_fields) for item in self.entities),
            "unexpected_present": sum(len(item.unexpected_present) for item in self.entities),
            "correlation_missing": sum(len(item.correlation_missing) for item in self.entities),
        }

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.entities)

    def write(self, directory: Path) -> Path:
        path = Path(directory) / "audit-check.json"
        data = {
            "status": "OK" if self.ok else "NO OK",
            "summary": self.summary,
            "waited_seconds": round(self.waited_seconds, 1),
            "entities": [item.__dict__ for item in self.entities],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")
    else:
        yield path, value


def _keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


class AuditChecker:
    def __init__(
        self,
        source: AuditSource,
        *,
        subjects: Mapping[str, str],
        protected_values: set[str],
        application_users: Mapping[str, str] | None = None,
        wait_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.source = source
        self.subjects = subjects
        # Purchase y Sales identifican al autor con el usuario operativo de la empresa
        # (`application_user_id`) y no envían `keycloak_user_id` (Specs 014/015, R-13).
        self.application_users = dict(application_users or {})
        self.protected_values = {value for value in protected_values if value and value not in MARKERS}
        self.wait_seconds = wait_seconds
        self.sleep = sleep
        self.clock = clock

    def _group(self, expected: list[ExpectedAudit]) -> dict[tuple, list[ExpectedAudit]]:
        groups: dict[tuple, list[ExpectedAudit]] = {}
        for item in expected:
            key = (item.scope, item.company_id if item.scope == "COMPANY" else None, item.entity_type, item.entity_id)
            groups.setdefault(key, []).append(item)
        return groups

    def _histories(self, keys: Iterable[tuple]) -> dict[tuple, list[dict]]:
        return {key: self.source.entity_history(*key) for key in keys}

    def check(self, expected: list[ExpectedAudit], absences: list[Absence] | None = None) -> AuditCheckResult:
        absences = absences or []
        groups = self._group(expected)
        absence_keys = {(item.scope, item.company_id if item.scope == "COMPANY" else None, item.entity_type, item.entity_id) for item in absences}
        keys = list(groups) + [key for key in absence_keys if key not in groups]
        started = self.clock()
        while True:
            histories = self._histories(keys)
            complete = all(
                not (Counter(item.action for item in items) - Counter(event["action"] for event in histories[key]))
                for key, items in groups.items()
            )
            if complete or self.clock() - started >= self.wait_seconds:
                break
            self.sleep(POLL_SECONDS)
        waited = self.clock() - started
        results = []
        for key in keys:
            items = groups.get(key, [])
            results.append(self._compare(key, items, histories[key], [item for item in absences if (item.scope, item.company_id if item.scope == "COMPANY" else None, item.entity_type, item.entity_id) == key]))
        return AuditCheckResult(results, waited)

    def _actor_matches(self, actor: str, event: dict) -> bool:
        wanted_sub = self.subjects.get(actor)
        if wanted_sub and event.get("keycloak_user_id") == wanted_sub:
            return True
        wanted_application_user = self.application_users.get(actor)
        if wanted_application_user and event.get("keycloak_user_id") in (None, wanted_sub):
            return event.get("application_user_id") == wanted_application_user
        return wanted_sub is None and wanted_application_user is None

    def _compare(self, key: tuple, items: list[ExpectedAudit], events: list[dict], absences: list[Absence]) -> EntityResult:
        scope, company_id, entity_type, entity_id = key
        expected_actions = [item.action for item in items]
        result = EntityResult(scope, company_id, entity_type, entity_id, expected_actions, steps=sorted({item.step_id for item in items}))
        result.received = [event["action"] for event in events]
        wanted, got = Counter(expected_actions), Counter(result.received)
        for action, count in wanted.items():
            if got[action] < count:
                result.missing += [action] * (count - got[action])
            elif got[action] > count:
                result.duplicates += [action] * (got[action] - count)
        # Actor y alcance de cada evento esperado.
        by_action: dict[str, list[ExpectedAudit]] = {}
        for item in items:
            by_action.setdefault(item.action, []).append(item)
        for event in events:
            candidates = by_action.get(event["action"])
            if not candidates:
                continue
            if not self._actor_matches(candidates[0].actor, event):
                result.wrong_actor.append(event["action"])
            if event.get("result", "SUCCESS") != candidates[0].result:
                result.wrong_result.append(event["action"])
            event_company = event.get("company_id")
            if scope == "PLATFORM" and event_company is not None:
                result.wrong_scope.append(event["action"])
            if scope == "COMPANY" and event_company != company_id:
                result.wrong_scope.append(event["action"])
        # Orden: las acciones esperadas aparecen en el orden del recorrido y por occurred_at.
        ordered = sorted(events, key=lambda event: (event.get("occurred_at") or "", event.get("id") or ""))
        sequence = [event["action"] for event in ordered if event["action"] in wanted]
        expected_sequence = [action for action in expected_actions if action in got]
        if [event["action"] for event in events] != [event["action"] for event in ordered] or _dedupe(sequence) != _dedupe(expected_sequence):
            result.out_of_order = True
        # Valores protegidos y campos de costo y margen.
        for event in events:
            for section in ("previous_values", "new_values", "reason"):
                for path, value in _walk(event.get(section)):
                    if isinstance(value, (str, int, float)) and str(value) in self.protected_values:
                        result.protected.append(f"{event['action']}:{section}.{path}")
            if event.get("source_service") == "sales-service" or entity_type in ("Sale", "SaleDetail"):
                for section in ("previous_values", "new_values"):
                    found = sorted(set(_keys(event.get(section))) & COST_FIELDS)
                    result.cost_fields += [f"{event['action']}:{section}.{name}" for name in found]
        for absence in absences:
            if absence.action in got:
                result.unexpected_present.append(absence.action)
        # Localización por correlation_id (compras y ventas).
        for item in items:
            if item.correlation_id and item.company_id:
                correlated = [event for event in self.source.by_correlation_id(item.company_id, item.correlation_id) if event.get("action") == item.action and event.get("entity_id") == item.entity_id]
                if len(correlated) != 1:
                    result.correlation_missing.append(item.action)
        return result


def _dedupe(sequence: list[str]) -> list[str]:
    result: list[str] = []
    for action in sequence:
        if not result or result[-1] != action:
            result.append(action)
    return result


class HttpAuditSource:
    """Fuente real: Audit por API con un usuario con lectura de eventos de empresa y de plataforma."""

    def __init__(self, client, step_prefix: str = "U-01") -> None:
        self.client = client
        self.step_prefix = step_prefix

    def _pages(self, path: str, params: dict, step_id: str, template: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            response = self.client.get("audit", path, step_id=step_id, params={**params, "page": page, "page_size": 100}, path_template=template)
            if response.status != 200:
                raise AssertionError(f"Audit respondió {response.status} en {template}")
            body = response.body
            items += body.get("items", [])
            if page >= body.get("total_pages", 1):
                return items
            page += 1

    def entity_history(self, scope, company_id, entity_type, entity_id):
        if scope == "PLATFORM":
            return self._pages(
                f"/platform-entity-history/{entity_type}/{entity_id}", {}, f"{self.step_prefix}.plataforma",
                "/platform-entity-history/{tipo_entidad}/{id_entidad}",
            )
        return self._pages(
            f"/companies/{company_id}/entity-history/{entity_type}/{entity_id}", {}, f"{self.step_prefix}.empresa",
            "/companies/{empresa_a}/entity-history/{tipo_entidad}/{id_entidad}",
        )

    def by_correlation_id(self, company_id, correlation_id):
        return self._pages(
            f"/companies/{company_id}/audit-events", {"correlation_id": correlation_id}, f"{self.step_prefix}.correlacion",
            "/companies/{empresa_a}/audit-events",
        )

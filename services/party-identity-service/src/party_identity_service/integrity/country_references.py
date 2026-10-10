"""Validador: `country_id` de las reglas de identificación ⊆ países de Geography (G-017-01).

Party Identity y Geography tienen bases independientes y no hay FK entre ellas: la integridad se
comprueba con el contrato público de Geography (`GET /global-countries/{id}`), una vez por país
distinto. Se revisan todas las reglas, activas e históricas. Resultado esperado: 0 referencias
huérfanas.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from party_identity_service.application.ports import CountryDirectory
from party_identity_service.infrastructure.models import IdentificationTypeRuleModel


@dataclass(slots=True)
class CountryReferenceReport:
    """Resultado de la validación.

    Attributes:
        checked_rules: Reglas revisadas.
        rules_by_country: Reglas por país referenciado.
        orphans: Reglas cuyo país no existe en Geography, por país.
    """

    checked_rules: int = 0
    rules_by_country: dict[UUID, int] = field(default_factory=dict)
    orphans: dict[UUID, list[UUID]] = field(default_factory=dict)

    @property
    def orphan_count(self) -> int:
        """Reglas que apuntan a un país inexistente."""
        return sum(len(rule_ids) for rule_ids in self.orphans.values())


def check_rule_country_references(
    rules: Iterable[tuple[UUID, UUID]],
    country_directory: CountryDirectory,
) -> CountryReferenceReport:
    """Comprueba que el país de cada regla exista en Geography.

    Args:
        rules: Pares `(id de la regla, country_id)`.
        country_directory: Puerto de Geography.

    Raises:
        DependencyUnavailableError: Si Geography no permite validar (no se emite un resultado
            parcial).
    """
    by_country: dict[UUID, list[UUID]] = defaultdict(list)

    for rule_id, country_id in rules:
        by_country[country_id].append(rule_id)

    report = CountryReferenceReport(
        checked_rules=sum(len(rule_ids) for rule_ids in by_country.values()),
        rules_by_country={country_id: len(rule_ids) for country_id, rule_ids in by_country.items()},
    )

    for country_id in sorted(by_country, key=str):
        if not country_directory.exists(country_id):
            report.orphans[country_id] = sorted(by_country[country_id], key=str)

    return report


def rule_country_pairs(session: Session) -> list[tuple[UUID, UUID]]:
    """Pares `(id, country_id)` de todas las reglas de la base del servicio."""
    return [
        (rule_id, country_id)
        for rule_id, country_id in session.execute(
            select(IdentificationTypeRuleModel.id, IdentificationTypeRuleModel.country_id)
        ).all()
    ]

"""Carga idempotente del catálogo CIIU Rev. 5 A.C. desde el snapshot (FR-055–FR-058, DS-10, R-10).

- Verifica el SHA-256 del CSV contra `SOURCE.md` **antes** de escribir.
- Valida en memoria niveles, códigos únicos, padres existentes y ausencia de ciclos.
- Inserta padres antes que hijos; llave funcional `classification_system` + `code`; conserva los
  UUID existentes y solo actualiza `name` o el padre si difieren.
- Una sola transacción (sin cargas parciales) y sin red: no usa Geography, Operational Context ni
  Keycloak.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from party_identity_service.domain.business_sector import CIIU_CLASSIFICATION_SYSTEM
from party_identity_service.infrastructure.business_sector_repository import (
    SectorSeedRow,
    SQLAlchemyBusinessSectorRepository,
)
from party_identity_service.seed.constants import SEED_ACTOR

SNAPSHOT_DIR = Path(__file__).resolve().parent / "data" / "ciiu_rev5_ac"
CSV_NAME = "ciiu_rev5_ac.csv"
LEVELS = ("SECTION", "DIVISION", "GROUP", "CLASS")
COLUMNS = ["level", "code", "name", "parent_code"]
_CSV_CHECKSUM = re.compile(r"SHA-256 del CSV[^\n]*?`([0-9a-f]{64})`")


class SnapshotError(ValueError):
    """El snapshot no es válido; la carga no escribe nada."""


@dataclass(slots=True)
class BusinessSectorSeedStats:
    """Resultado de `load-business-sectors`."""

    classification_system: str
    checksum: str
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    by_level: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _Row:
    level: str
    code: str
    name: str
    parent_code: str | None


def expected_checksum(source_md: Path) -> str:
    """SHA-256 del CSV declarado en `SOURCE.md`."""
    match = _CSV_CHECKSUM.search(source_md.read_text(encoding="utf-8"))
    if match is None:
        raise SnapshotError(f"{source_md} no declara el SHA-256 del CSV.")
    return match.group(1)


def read_snapshot(snapshot_dir: Path, csv_name: str = CSV_NAME) -> tuple[list[_Row], str]:
    """Lee y valida el snapshot; devuelve filas en orden padres → hijos y su SHA-256.

    Raises:
        SnapshotError: Checksum distinto, columnas, niveles o códigos inválidos, padre ausente o ciclo.
    """
    content = (snapshot_dir / csv_name).read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    expected = expected_checksum(snapshot_dir / "SOURCE.md")
    if checksum != expected:
        raise SnapshotError(
            f"El SHA-256 de {csv_name} ({checksum}) no coincide con SOURCE.md ({expected})."
        )

    reader = csv.DictReader(io.StringIO(content.decode("utf-8"), newline=""))
    if reader.fieldnames != COLUMNS:
        raise SnapshotError(f"Columnas esperadas {COLUMNS}, encontradas {reader.fieldnames}.")

    rows: dict[str, _Row] = {}
    for number, raw in enumerate(reader, start=2):
        level, code, name = raw["level"].strip(), raw["code"].strip().upper(), raw["name"].strip()
        if level not in LEVELS:
            raise SnapshotError(f"Línea {number}: nivel desconocido {level!r}.")
        if not code or not name:
            raise SnapshotError(f"Línea {number}: código y nombre son obligatorios.")
        if code in rows:
            raise SnapshotError(f"Línea {number}: código duplicado {code!r}.")
        rows[code] = _Row(level, code, name, raw["parent_code"].strip().upper() or None)

    return _parents_first(rows), checksum


def _parents_first(rows: dict[str, _Row]) -> list[_Row]:
    """Orden topológico (padres antes que hijos) validando padres y ciclos."""
    ordered: list[_Row] = []
    placed: set[str] = set()

    for code in rows:
        chain: list[str] = []
        current: str | None = code
        while current is not None and current not in placed:
            if current in chain:
                raise SnapshotError(f"Ciclo en la jerarquía: {' → '.join([*chain, current])}.")
            if current not in rows:
                raise SnapshotError(f"El padre {current!r} de {chain[-1]!r} no existe en el snapshot.")
            chain.append(current)
            current = rows[current].parent_code
        for item in reversed(chain):
            ordered.append(rows[item])
            placed.add(item)

    return ordered


def load_business_sectors(
    session: Session,
    *,
    snapshot_dir: Path = SNAPSHOT_DIR,
    csv_name: str = CSV_NAME,
    classification_system: str = CIIU_CLASSIFICATION_SYSTEM,
) -> BusinessSectorSeedStats:
    """Carga el catálogo de forma idempotente; ante cualquier error no escribe nada."""
    rows, checksum = read_snapshot(snapshot_dir, csv_name)
    result = SQLAlchemyBusinessSectorRepository(session).upsert_catalog(
        classification_system=classification_system,
        rows=[SectorSeedRow(row.code, row.name, row.parent_code) for row in rows],
        actor_id=SEED_ACTOR,
    )
    counts = Counter(row.level for row in rows)

    return BusinessSectorSeedStats(
        classification_system=classification_system,
        checksum=checksum,
        created=result.created,
        updated=result.updated,
        unchanged=result.unchanged,
        by_level={level: counts[level] for level in LEVELS},
    )

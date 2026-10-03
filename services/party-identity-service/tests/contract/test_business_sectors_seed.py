"""`seed load-business-sectors`: catálogo CIIU Rev. 5 A.C. (T065; RC-11, RC-16, SC-007, FR-055–FR-058)."""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import socket
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from party_identity_service.infrastructure.models import GlobalBusinessSectorModel as Sector
from party_identity_service.seed.business_sectors_loader import (
    CSV_NAME,
    SNAPSHOT_DIR,
    SnapshotError,
    load_business_sectors,
)
from party_identity_service.seed.constants import SEED_ACTOR

EXTRACT_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ciiu_extract"
EXTRACT_CSV = "ciiu_extract.csv"
EXTRACT_COUNTS = {"SECTION": 1, "DIVISION": 3, "GROUP": 14, "CLASS": 37}


def _load_extract(session, snapshot_dir: Path = EXTRACT_DIR):
    return load_business_sectors(session, snapshot_dir=snapshot_dir, csv_name=EXTRACT_CSV)


def _sectors(session) -> dict[str, Sector]:
    return {sector.code: sector for sector in session.scalars(select(Sector)).all()}


def _count(session) -> int:
    return session.scalar(select(func.count()).select_from(Sector))


def _write_snapshot(directory: Path, rows: list[dict[str, str]]) -> Path:
    """Snapshot de prueba con su SOURCE.md coherente (checksum correcto)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / EXTRACT_CSV
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["level", "code", "name", "parent_code"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    (directory / "SOURCE.md").write_text(f"- **SHA-256 del CSV (`{EXTRACT_CSV}`)**: `{checksum}`\n", encoding="utf-8")
    return directory


def _row(level: str, code: str, parent: str = "") -> dict[str, str]:
    return {"level": level, "code": code, "name": f"Sector {code}", "parent_code": parent}


def test_extract_loads_levels_with_correct_parents(db_session) -> None:
    stats = _load_extract(db_session)

    assert stats.by_level == EXTRACT_COUNTS
    assert stats.created == sum(EXTRACT_COUNTS.values()) == _count(db_session)
    sectors = _sectors(db_session)
    by_id = {sector.id: sector.code for sector in sectors.values()}
    assert sectors["A"].parent_sector_id is None
    assert by_id[sectors["01"].parent_sector_id] == "A"
    assert by_id[sectors["011"].parent_sector_id] == "01"
    assert by_id[sectors["0111"].parent_sector_id] == "011"
    for code, sector in sectors.items():
        if len(code) == 3:
            assert by_id[sector.parent_sector_id] == code[:2]
        elif len(code) == 4:
            assert by_id[sector.parent_sector_id] == code[:3]


def test_classification_system_actor_and_status(db_session) -> None:
    _load_extract(db_session)

    sectors = _sectors(db_session).values()
    assert {sector.classification_system for sector in sectors} == {"CIIU_REV5_AC"}
    assert {sector.created_by for sector in sectors} == {SEED_ACTOR}
    assert {sector.updated_by for sector in sectors} == {SEED_ACTOR}
    assert {sector.status for sector in sectors} == {"ACTIVE"}


def test_second_run_creates_nothing_and_keeps_uuids(db_session) -> None:
    _load_extract(db_session)
    before = {code: sector.id for code, sector in _sectors(db_session).items()}

    stats = _load_extract(db_session)

    assert (stats.created, stats.updated, stats.unchanged) == (0, 0, len(before))
    assert {code: sector.id for code, sector in _sectors(db_session).items()} == before


def test_changed_name_is_updated_keeping_uuid(db_session, tmp_path) -> None:
    _load_extract(db_session)
    original = _sectors(db_session)["0111"]
    original_id, original_version = original.id, original.version
    rows = list(csv.DictReader((EXTRACT_DIR / EXTRACT_CSV).open(encoding="utf-8", newline="")))
    for row in rows:
        if row["code"] == "0111":
            row["name"] = "Nombre corregido por el DANE"

    stats = _load_extract(db_session, _write_snapshot(tmp_path, rows))

    db_session.expire_all()
    updated = _sectors(db_session)["0111"]
    assert stats.updated == 1 and stats.created == 0
    assert (updated.id, updated.name) == (original_id, "Nombre corregido por el DANE")
    assert updated.version == original_version + 1


def test_checksum_mismatch_writes_nothing(db_session, tmp_path) -> None:
    shutil.copytree(EXTRACT_DIR, tmp_path / "snapshot")
    tampered = tmp_path / "snapshot" / EXTRACT_CSV
    tampered.write_bytes(tampered.read_bytes().replace(b"Cultivo de arroz", b"Cultivo de arroz alterado"))

    with pytest.raises(SnapshotError, match="SHA-256"):
        _load_extract(db_session, tmp_path / "snapshot")

    assert _count(db_session) == 0


def test_missing_checksum_in_source_fails(db_session, tmp_path) -> None:
    shutil.copytree(EXTRACT_DIR, tmp_path / "snapshot")
    (tmp_path / "snapshot" / "SOURCE.md").write_text("# Sin checksum\n", encoding="utf-8")

    with pytest.raises(SnapshotError, match="no declara"):
        _load_extract(db_session, tmp_path / "snapshot")


@pytest.mark.parametrize(
    "rows, message",
    [
        ([_row("SECTION", "A"), _row("DIVISION", "01", "A"), _row("CLASS", "0111", "011")], "no existe"),
        ([_row("SECTION", "A"), _row("GROUP", "011", "012"), _row("GROUP", "012", "011")], "Ciclo"),
        ([_row("SECTION", "A"), _row("SECTION", "A")], "duplicado"),
        ([_row("SECTION", "A"), _row("SUBCLASS", "01111", "A")], "nivel desconocido"),
    ],
)
def test_invalid_snapshot_fails_without_partial_load(db_session, tmp_path, rows, message) -> None:
    with pytest.raises(SnapshotError, match=message):
        _load_extract(db_session, _write_snapshot(tmp_path, rows))

    assert _count(db_session) == 0


def test_children_listed_before_parents_are_loaded_in_order(db_session, tmp_path) -> None:
    rows = [_row("CLASS", "0111", "011"), _row("GROUP", "011", "01"), _row("DIVISION", "01", "A"), _row("SECTION", "A")]

    stats = _load_extract(db_session, _write_snapshot(tmp_path, rows))

    assert stats.created == 4


def test_database_error_rolls_back_everything(db_session, tmp_path) -> None:
    rows = [_row("SECTION", "A"), {"level": "DIVISION", "code": "01", "name": "x" * 256, "parent_code": "A"}]

    with pytest.raises(Exception):
        _load_extract(db_session, _write_snapshot(tmp_path, rows))

    db_session.rollback()
    assert _count(db_session) == 0


def test_runs_without_network(db_session, monkeypatch) -> None:
    def no_network(*args, **kwargs):
        raise AssertionError("El seed de sectores no debe usar la red.")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(httpx.Client, "send", no_network)

    stats = _load_extract(db_session)

    assert stats.created == sum(EXTRACT_COUNTS.values())


def test_full_snapshot_matches_source_counts(db_session) -> None:
    source = (SNAPSHOT_DIR / "SOURCE.md").read_text(encoding="utf-8")
    declared = {level: int(count) for level, count in re.findall(r"^\| (SECTION|DIVISION|GROUP|CLASS) \| (\d+) \|$", source, re.M)}

    stats = load_business_sectors(db_session)

    assert stats.by_level == declared == {"SECTION": 22, "DIVISION": 87, "GROUP": 266, "CLASS": 544}
    assert stats.created == _count(db_session) == 919
    assert max(len(sector.name) for sector in _sectors(db_session).values()) == 222
    assert (SNAPSHOT_DIR / CSV_NAME).read_bytes().count(b"\r\n") == 0

    second = load_business_sectors(db_session)
    assert (second.created, second.updated, second.unchanged) == (0, 0, 919)

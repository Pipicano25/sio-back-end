"""Validación de los CSV estándar de una empresa (Silver o Gold) contra templates/schemas.

Uso:
    tools/data-migration/.venv/bin/python tools/data-migration/ia-tools/validate_csv.py tools/data-migration/DAO --layer gold --sio

1. Frictionless (Table Schema): encabezados, tipos, obligatorios, valores permitidos, patrones, longitudes,
   mínimos/máximos, únicos, clave primaria y claves foráneas entre los 26 CSV.
2. Lo que Table Schema no aplica, declarado en cada esquema y nada más:
   `uniqueKeys` (Frictionless 5 los acepta pero no los verifica) y `sio.rules`
   (positive, one_true, unique_where, check_where, same_parent, exactly_one_of, catalog, catalog_or_file, file_hash, gold_requires).
3. Gold: todas las filas VALIDADO e idénticas a su fila de Silver (misma referencia).
Con --sio, los códigos de catálogos globales se comparan con SIO mediante ia-tools/sio_query.py (solo GET).

En Silver, los problemas de filas PENDIENTE o CONFLICTO se cuentan como pendientes esperados; los de filas VALIDADO
son errores. En Gold todo problema es error. No modifica ningún archivo.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from frictionless import Package, Resource, Schema

TOOL_DIR = Path(__file__).resolve().parents[1]
SCHEMAS = TOOL_DIR / "templates" / "schemas"


def load_schemas() -> dict[str, dict]:
    return {p.name.removesuffix(".schema.json"): json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCHEMAS.glob("*.schema.json"))}


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


class Report:
    def __init__(self, layer: str) -> None:
        self.layer = layer
        self.errors: list[dict] = []
        self.pending: Counter = Counter()

    def add(self, table: str, row: dict | None, check: str, message: str) -> None:
        status = (row or {}).get("migration_status")
        if self.layer == "silver" and row is not None and status != "VALIDADO":
            self.pending[(table, check)] += 1
            return
        if len(self.errors) < 5000:
            ref = next(iter(row.values())) if row else None
            self.errors.append({"archivo": table, "ref": ref, "control": check, "detalle": message[:300]})


def frictionless_checks(layer_dir: Path, schemas: dict, rows: dict, report: Report) -> None:
    resources = []
    for name, descriptor in schemas.items():
        clean = {k: v for k, v in descriptor.items() if k not in ("sio", "uniqueKeys")}
        resources.append(Resource(path=f"{name}.csv", name=name, schema=Schema.from_descriptor(clean)))
    result = Package(resources=resources, basepath=str(layer_dir)).validate()
    for task in result.tasks:
        for error in task.errors:
            number = getattr(error, "row_number", None)
            row = rows[task.name][number - 2] if number and 0 <= number - 2 < len(rows[task.name]) else None
            report.add(task.name, row, f"frictionless:{error.type}", error.note or error.message)


def _true(value: str) -> bool:
    return value == "true"


def schema_rules(company_dir: Path, layer: str, schemas: dict, rows: dict, report: Report, catalogs) -> None:
    for name, descriptor in schemas.items():
        data = rows[name]
        for key in descriptor.get("uniqueKeys", []):
            seen: dict[tuple, int] = {}
            for row in data:
                values = tuple(row.get(f, "") for f in key)
                if any(v == "" for v in values):
                    continue  # como en SQL: un nulo no participa en la unicidad
                if values in seen:
                    report.add(name, row, "uniqueKeys", f"{key} repetido {values}")
                seen[values] = seen.get(values, 0) + 1
        for rule in descriptor.get("sio", {}).get("rules", []):
            kind, field = rule["type"], rule.get("field")
            if kind == "positive":
                for row in data:
                    if row.get(field) not in ("", None) and float(row[field]) <= 0:
                        report.add(name, row, kind, f"{field} debe ser > 0")
            elif kind == "one_true":
                groups: dict[tuple, list] = defaultdict(list)
                for row in data:
                    groups[tuple(row[f] for f in rule["per"])].append(row)
                limit = rule.get("max", 10**9)
                for group in groups.values():
                    marked = [r for r in group if _true(r.get(field, ""))]
                    validated = [r for r in marked if r.get("migration_status") == "VALIDADO"]
                    if len(marked) <= limit:
                        continue
                    # Error solo si la infracción ocurre entre filas VALIDADO (lo que pasaría a Gold); si la causan
                    # filas pendientes de un producto validado, se cuenta como pendiente en esas filas.
                    for r in (marked if len(validated) > limit else [r for r in marked if r not in validated]):
                        report.add(name, r, kind, f"más de {limit} {field}=true por {rule['per']}")
                if rule.get("min") and rule.get("scope"):
                    parent_pk = schemas[rule["scope"]]["primaryKey"][0]
                    for parent in rows[rule["scope"]]:
                        group = groups.get((parent[parent_pk],), [])
                        if parent.get("migration_status") == "VALIDADO":
                            group = [r for r in group if r.get("migration_status") == "VALIDADO"]
                        if sum(_true(r.get(field, "")) for r in group) < rule["min"]:
                            report.add(rule["scope"], parent, f"{name}:{kind}", f"sin {field}=true en {name}")
            elif kind == "unique_where":
                seen = set()
                for row in data:
                    if any(row.get(k) not in v for k, v in rule["where"].items()):
                        continue
                    values = tuple(row.get(f, "") for f in rule["fields"])
                    if any(v == "" for v in values):
                        continue
                    if values in seen:
                        report.add(name, row, kind, f"{rule['fields']} repetido {values} ({rule.get('note', '')})")
                    seen.add(values)
            elif kind == "same_parent":
                target = schemas[rule["file"]]["primaryKey"][0]
                parents = {r[target]: r[rule["parent"]] for r in rows[rule["file"]]}
                for row in data:
                    if row.get(field) and parents.get(row[field]) not in (None, row[rule["parent"]]):
                        report.add(name, row, kind, f"{field} pertenece a otro {rule['parent']}")
            elif kind == "check_where":
                # Equivalente a un CHECK condicional de la base de datos (p. ej. ck_global_product_identifiers_ium_format).
                patterns = {f: re.compile(p) for f, p in rule.get("pattern", {}).items()}
                for row in data:
                    if any(row.get(k) not in v for k, v in rule["where"].items()):
                        continue
                    missing = [f for f in rule.get("required", []) if not row.get(f)]
                    invalid = [f for f, p in patterns.items() if not p.fullmatch(row.get(f, ""))]
                    if missing or invalid:
                        report.add(name, row, kind, f"{rule.get('note', '')}: falta {missing} / formato inválido {invalid}")
            elif kind == "exactly_one_of":
                for row in data:
                    if sum(row.get(f, "") != "" for f in rule["fields"]) != 1:
                        report.add(name, row, kind, f"debe tener exactamente un valor en {rule['fields']}")
            elif kind in ("catalog", "catalog_or_file") and catalogs is not None:
                allowed = catalogs(rule["service"], rule["path"])
                if kind == "catalog_or_file":
                    allowed = allowed | {r[rule["file_field"]] for r in rows[rule["file"]]}
                for row in data:
                    if row.get(field) and row[field] not in allowed:
                        report.add(name, row, kind, f"{field}={row[field]} no existe en SIO ({rule['path']})" +
                                   (f" ni en {rule['file']}.csv" if kind == "catalog_or_file" else ""))
            elif kind == "file_hash":
                for row in data:
                    path = company_dir / row.get(field, "")
                    if not row.get(field) or not path.is_file():
                        report.add(name, row, kind, f"falta el archivo {row.get(field)}")
                    elif hashlib.sha256(path.read_bytes()).hexdigest() != path.stem:
                        report.add(name, row, kind, f"el SHA-256 de {row[field]} no coincide con su nombre")
            elif kind == "gold_requires" and layer == "gold":
                for row in data:
                    if row.get(field) not in rule["values"]:
                        report.add(name, row, kind, f"{field}={row.get(field)} no admitido en Gold")


def gold_checks(company_dir: Path, schemas: dict, rows: dict, report: Report) -> None:
    for name, descriptor in schemas.items():
        pk = descriptor["primaryKey"][0]
        _, silver_rows = read_rows(company_dir / "silver" / f"{name}.csv")
        silver = {r[pk]: r for r in silver_rows}
        for row in rows[name]:
            if row["migration_status"] != "VALIDADO":
                report.add(name, row, "gold:estado", "fila no VALIDADO en Gold")
            if silver.get(row[pk]) != row:
                report.add(name, row, "gold:igual_a_silver", "la fila no existe en Silver o difiere de ella")


def sio_catalogs():
    spec = importlib.util.spec_from_file_location("sio_query", Path(__file__).with_name("sio_query.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client, cache = module.SioQuery("consulta"), {}

    def codes(service: str, path: str) -> set[str]:
        if (service, path) not in cache:
            status, body = client.get(service, path, {}, all_pages=True)
            if status != 200:
                raise SystemExit(f"No se pudo leer el catálogo {service} {path}: HTTP {status}")
            cache[(service, path)] = {item.get("code") for item in body.get("items", []) if item.get("code")}
        return cache[(service, path)]

    return codes


def validate(company_dir: Path, layer: str, use_sio: bool) -> dict:
    schemas = load_schemas()
    layer_dir = company_dir / layer
    report = Report(layer)
    rows: dict[str, list[dict]] = {}
    for name, descriptor in schemas.items():
        path = layer_dir / f"{name}.csv"
        if not path.is_file():
            report.add(name, None, "archivo", f"falta {path.name}")
            rows[name] = []
            continue
        header, rows[name] = read_rows(path)
        expected = [f["name"] for f in descriptor["fields"]]
        if header != expected:
            report.add(name, None, "encabezado", f"columnas {header} ≠ esquema {expected}")
    frictionless_checks(layer_dir, schemas, rows, report)
    schema_rules(company_dir, layer, schemas, rows, report, sio_catalogs() if use_sio else None)
    if layer == "gold":
        gold_checks(company_dir, schemas, rows, report)
    return {
        "empresa": company_dir.name, "capa": layer, "catalogos_sio_verificados": use_sio,
        "filas": {name: len(data) for name, data in rows.items()},
        "estados": {name: dict(Counter(r.get("migration_status") for r in data)) for name, data in rows.items() if data},
        "errores": len(report.errors), "errores_por_control": dict(Counter((e["archivo"], e["control"]) for e in report.errors).most_common()),
        "pendientes_esperados": {f"{t} · {c}": n for (t, c), n in report.pending.most_common()},
        "detalle_errores": report.errors[:200],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida los CSV estándar de una empresa (Frictionless + reglas declaradas en los esquemas).")
    parser.add_argument("company_dir", type=Path)
    parser.add_argument("--layer", choices=("silver", "gold"), required=True)
    parser.add_argument("--sio", action="store_true", help="Verificar códigos de catálogos globales contra SIO (solo GET)")
    args = parser.parse_args(argv)
    result = validate(args.company_dir.resolve(), args.layer, args.sio)
    result["errores_por_control"] = {f"{t} · {c}": n for (t, c), n in result["errores_por_control"].items()}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errores"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

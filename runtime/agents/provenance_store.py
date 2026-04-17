#!/usr/bin/env python3
"""
runtime/agents/provenance_store.py

Small helpers for Part 1 provenance records:
- safe source_id and path helpers
- load/list records
- atomic JSON writes
- shallow patch/update helpers
- completeness and schema validation
"""

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part1_provenance.schema.json"
DEFAULT_PROVENANCE_DIR = PROJECT_ROOT / "raw-library" / "provenance"

DOWNLOAD_REQUIRED_FIELDS = (
    "source_id",
    "query_id",
    "db",
    "title",
    "authors",
    "journal",
    "year",
    "doi_or_cnki_id",
    "url",
    "abstract",
    "keywords",
    "download_status",
    "downloaded_at",
)


class ProvenanceSchemaError(ValueError):
    """Raised when a provenance record does not match the schema."""


class ProvenanceSchemaUnavailableError(RuntimeError):
    """Raised when jsonschema is not installed but schema validation is requested."""


def ensure_source_id(source_id: str) -> str:
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a non-empty string")

    clean = source_id.strip()
    if clean in {".", ".."} or "/" in clean or "\\" in clean:
        raise ValueError(f"source_id must not contain path separators: {source_id!r}")
    return clean


def source_id_from_record(record: dict[str, Any]) -> str:
    return ensure_source_id(record.get("source_id"))


def provenance_path(provenance_dir: Path | str, source_id: str) -> Path:
    return Path(provenance_dir) / f"{ensure_source_id(source_id)}.json"


def paper_path(project_root: Path | str, source_id: str) -> Path:
    return Path(project_root) / "raw-library" / "papers" / f"{ensure_source_id(source_id)}.pdf"


def normalized_path(project_root: Path | str, source_id: str) -> Path:
    return Path(project_root) / "raw-library" / "normalized" / f"{ensure_source_id(source_id)}.txt"


def load_json(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def load_record(provenance_dir: Path | str, source_id: str) -> dict[str, Any]:
    return load_json(provenance_path(provenance_dir, source_id))


def list_records(provenance_dir: Path | str) -> list[dict[str, Any]]:
    directory = Path(provenance_dir)
    if not directory.exists():
        return []
    return [load_json(path) for path in sorted(directory.glob("*.json"))]


def atomic_write_json(path: Path | str, data: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            json.dump(data, tmp, ensure_ascii=False, indent=2, sort_keys=True)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, target)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

    return target


def write_record(
    provenance_dir: Path | str,
    record: dict[str, Any],
    *,
    validate: bool = True,
) -> Path:
    source_id = source_id_from_record(record)
    next_record = dict(record)
    if validate:
        validate_against_schema(next_record)
    return atomic_write_json(provenance_path(provenance_dir, source_id), next_record)


def patch_record(
    provenance_dir: Path | str,
    source_id: str,
    changes: dict[str, Any],
    *,
    validate: bool = True,
) -> dict[str, Any]:
    current = load_record(provenance_dir, source_id)
    if "source_id" in changes and changes["source_id"] != current.get("source_id"):
        raise ValueError("patch_record cannot change source_id")

    next_record = {**current, **changes}
    if validate:
        validate_against_schema(next_record)
    atomic_write_json(provenance_path(provenance_dir, source_id), next_record)
    return next_record


def update_record(
    provenance_dir: Path | str,
    source_id: str,
    updater: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    validate: bool = True,
) -> dict[str, Any]:
    current = load_record(provenance_dir, source_id)
    next_record = updater(dict(current))
    if not isinstance(next_record, dict):
        raise ValueError("update_record updater must return a dict")
    if next_record.get("source_id") != current.get("source_id"):
        raise ValueError("update_record cannot change source_id")
    if validate:
        validate_against_schema(next_record)
    atomic_write_json(provenance_path(provenance_dir, source_id), next_record)
    return next_record


def field_complete(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def provenance_complete(record: dict[str, Any]) -> bool:
    return all(field_complete(record.get(field)) for field in DOWNLOAD_REQUIRED_FIELDS)


def load_schema(schema_path: Path | str = SCHEMA_PATH) -> dict[str, Any]:
    return load_json(schema_path)


def validate_against_schema(record: dict[str, Any]) -> bool:
    try:
        import jsonschema
    except ImportError as exc:
        raise ProvenanceSchemaUnavailableError(
            "jsonschema is required to validate provenance records. "
            "Install jsonschema or call write_record(..., validate=False)."
        ) from exc

    schema = load_schema()
    try:
        jsonschema.Draft7Validator(schema).validate(record)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path)
        prefix = f"{location}: " if location else ""
        raise ProvenanceSchemaError(f"{prefix}{exc.message}") from exc
    return True

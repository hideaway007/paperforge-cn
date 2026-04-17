#!/usr/bin/env python3
"""
Archive manually captured web Markdown into the Part 1 raw library.

This script is for sources that are not PDFs but still need provenance and
local, auditable storage before they can enter downstream checks.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_source_id(source_id: str) -> str:
    cleaned = str(source_id or "").strip()
    if not cleaned:
        raise ValueError("source_id cannot be empty")
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"source_id must not contain path separators: {source_id!r}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", cleaned):
        raise ValueError(f"source_id has unsupported characters: {source_id!r}")
    return cleaned


def project_relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def archive_markdown_source(
    *,
    project_root: Path | str = PROJECT_ROOT,
    source_id: str,
    url: str,
    markdown_source_path: Path | str,
    metadata: dict[str, Any],
    archive_method: str = "manual_markdown_import",
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    clean_source_id = ensure_source_id(source_id)
    source_path = Path(markdown_source_path).resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"Markdown source not found: {source_path}")

    text = source_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Markdown source is empty: {source_path}")

    archive_dir = root / "raw-library" / "web-archives"
    provenance_dir = root / "raw-library" / "provenance"
    archive_dir.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)

    archive_path = archive_dir / f"{clean_source_id}.md"
    archive_path.write_text(text.rstrip() + "\n", encoding="utf-8")

    record = {
        "source_id": clean_source_id,
        "query_id": metadata.get("query_id") or "manual_web_archive",
        "db": metadata.get("db") or "web",
        "title": metadata.get("title") or clean_source_id,
        "authors": metadata.get("authors") or ["unknown"],
        "journal": metadata.get("journal") or "web",
        "year": int(metadata.get("year") or datetime.now(timezone.utc).year),
        "doi_or_cnki_id": metadata.get("doi_or_cnki_id") or url,
        "url": url or metadata.get("url") or "",
        "abstract": metadata.get("abstract") or text[:500].strip(),
        "keywords": metadata.get("keywords") or ["web archive"],
        "download_status": "success",
        "downloaded_at": now_iso(),
        "local_path": project_relative(root, archive_path),
        "local_artifact_type": "markdown",
        "archive_method": archive_method,
    }

    provenance_path = provenance_dir / f"{clean_source_id}.json"
    provenance_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "archive_path": archive_path,
        "provenance_path": provenance_path,
        "record": record,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive a Markdown web source into raw-library.")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--markdown-source-path", required=True)
    parser.add_argument("--metadata-json", help="Optional JSON object with title/authors/journal/year/keywords.")
    parser.add_argument("--archive-method", default="manual_markdown_import")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    metadata: dict[str, Any] = {}
    if args.metadata_json:
        parsed = json.loads(args.metadata_json)
        if not isinstance(parsed, dict):
            raise ValueError("--metadata-json must be a JSON object")
        metadata = parsed

    result = archive_markdown_source(
        project_root=Path(args.project_root),
        source_id=args.source_id,
        url=args.url,
        markdown_source_path=Path(args.markdown_source_path),
        metadata=metadata,
        archive_method=args.archive_method,
    )
    print(f"Archived: {result['archive_path']}")
    print(f"Provenance: {result['provenance_path']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Export a user-facing table of Part 1 downloaded papers.

The table is a convenience artifact for the user. It is generated from
download provenance first, then enriched by canonical raw-library metadata when
available. It does not replace raw-library/metadata.json as the research source
of truth.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

OUTPUT_CSV = "outputs/part1/downloaded_papers_table.csv"
OUTPUT_MD = "outputs/part1/downloaded_papers_table.md"

TABLE_FIELDS = [
    "source_id",
    "title",
    "authors",
    "year",
    "journal",
    "doi_or_cnki_id",
    "source_name",
    "query_id",
    "download_status",
    "library_status",
    "relevance_tier",
    "relevance_score",
    "authenticity_status",
    "keywords",
    "abstract",
    "local_path",
    "provenance_path",
    "url",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(item) for item in value if item is not None)
    return str(value)


def normalize_cell(value: Any) -> str:
    return as_text(value).replace("\r", " ").replace("\n", " ").strip()


def load_provenance_records(project_root: Path) -> dict[str, dict[str, Any]]:
    provenance_dir = project_root / "raw-library" / "provenance"
    if not provenance_dir.exists():
        return {}

    records: dict[str, dict[str, Any]] = {}
    for path in sorted(provenance_dir.glob("*.json")):
        data = load_json(path)
        if not data:
            continue
        source_id = data.get("source_id") or path.stem
        data.setdefault("source_id", source_id)
        data.setdefault("provenance_path", path.relative_to(project_root).as_posix())
        records[str(source_id)] = data
    return records


def load_metadata_sources(project_root: Path) -> dict[str, dict[str, Any]]:
    metadata = load_json(project_root / "raw-library" / "metadata.json")
    if not metadata:
        return {}
    sources = metadata.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("raw-library/metadata.json sources must be an array")
    return {
        str(source.get("source_id")): source
        for source in sources
        if isinstance(source, dict) and source.get("source_id")
    }


def build_rows(
    provenance_records: dict[str, dict[str, Any]],
    metadata_sources: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    source_ids = sorted(set(provenance_records) | set(metadata_sources))
    rows: list[dict[str, str]] = []

    for source_id in source_ids:
        provenance = provenance_records.get(source_id, {})
        metadata = metadata_sources.get(source_id, {})
        merged = {**provenance, **metadata}

        download_status = normalize_cell(
            provenance.get("download_status")
            or metadata.get("download_status")
            or ("success" if metadata else "")
        )
        if provenance and download_status and download_status != "success":
            continue

        local_path = (
            metadata.get("local_path")
            or provenance.get("local_path")
            or f"raw-library/papers/{source_id}.pdf"
        )
        provenance_path = (
            metadata.get("provenance_path")
            or provenance.get("provenance_path")
            or f"raw-library/provenance/{source_id}.json"
        )

        row = {
            "source_id": source_id,
            "title": normalize_cell(merged.get("title")),
            "authors": normalize_cell(merged.get("authors")),
            "year": normalize_cell(merged.get("year")),
            "journal": normalize_cell(merged.get("journal")),
            "doi_or_cnki_id": normalize_cell(
                merged.get("doi_or_cnki_id")
                or merged.get("cnki_or_source_id")
                or merged.get("doi")
            ),
            "source_name": normalize_cell(merged.get("source_name") or merged.get("db")),
            "query_id": normalize_cell(merged.get("query_id")),
            "download_status": download_status,
            "library_status": "accepted" if source_id in metadata_sources else "downloaded_not_registered",
            "relevance_tier": normalize_cell(merged.get("relevance_tier")),
            "relevance_score": normalize_cell(merged.get("relevance_score")),
            "authenticity_status": normalize_cell(merged.get("authenticity_status")),
            "keywords": normalize_cell(merged.get("keywords")),
            "abstract": normalize_cell(merged.get("abstract")),
            "local_path": normalize_cell(local_path),
            "provenance_path": normalize_cell(provenance_path),
            "url": normalize_cell(merged.get("url")),
        }
        rows.append(row)

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TABLE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def markdown_cell(value: str, max_len: int = 120) -> str:
    text = value.replace("|", " / ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "..."


def write_markdown(path: Path, rows: list[dict[str, str]], generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Part 1 Downloaded Papers Table",
        "",
        f"generated_at: {generated_at}",
        f"total_rows: {len(rows)}",
        "",
        "| source_id | title | authors | year | journal | relevance | status | abstract | local_path |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row["source_id"]),
                    markdown_cell(row["title"]),
                    markdown_cell(row["authors"]),
                    markdown_cell(row["year"]),
                    markdown_cell(row["journal"]),
                    markdown_cell(f"{row['relevance_tier']} {row['relevance_score']}".strip()),
                    markdown_cell(row["library_status"]),
                    markdown_cell(row["abstract"]),
                    markdown_cell(row["local_path"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_downloaded_papers_table(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    provenance_records = load_provenance_records(project_root)
    metadata_sources = load_metadata_sources(project_root)
    rows = build_rows(provenance_records, metadata_sources)

    if not rows:
        raise RuntimeError(
            "没有可导出的 Part 1 下载论文记录：缺少 raw-library/provenance/*.json 或 raw-library/metadata.json sources"
        )

    generated_at = now_iso()
    output_csv = project_root / OUTPUT_CSV
    output_md = project_root / OUTPUT_MD
    write_csv(output_csv, rows)
    write_markdown(output_md, rows, generated_at)

    return {
        "generated_at": generated_at,
        "row_count": len(rows),
        "output_csv": output_csv,
        "output_md": output_md,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Part 1 downloaded papers table")
    parser.add_argument("--project-root", metavar="PATH", help="项目根目录")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT
    result = export_downloaded_papers_table(project_root=project_root)

    print("Part 1 downloaded papers table 已导出")
    print(f"  行数: {result['row_count']}")
    print(f"  项目内 CSV: {result['output_csv'].relative_to(project_root)}")
    print(f"  项目内 Markdown: {result['output_md'].relative_to(project_root)}")


if __name__ == "__main__":
    main()

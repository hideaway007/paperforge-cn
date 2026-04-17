#!/usr/bin/env python3
"""
Codex CLI adapter for RTM argumentagent requests.

Reads the JSON request produced by runtime/llm_agent_bridge.py, asks Codex to
act as the configured argumentagent, and prints a JSON object accepted by the
bridge: artifacts.candidate_trees. The runtime generator remains responsible
for trace, density, schema validation, and candidate file writes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


CODEX_BIN_ENV = "RTM_CODEX_BIN"
CODEX_MODEL_ENV = "RTM_ARGUMENTAGENT_MODEL"
DEFAULT_CODEX_BIN = "codex"
DEFAULT_MODEL = "gpt-5.4"


def load_request() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise RuntimeError("argumentagent adapter input must be JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("argumentagent adapter input must be a JSON object")
    return payload


def load_argumentagent_instructions() -> str:
    config_path = Path.home() / ".codex" / "agents" / "argumentagent.toml"
    if not config_path.exists():
        return ""
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    instructions = data.get("developer_instructions")
    return instructions if isinstance(instructions, str) else ""


def compact_request_for_prompt(request: dict[str, Any]) -> str:
    return json.dumps(request, ensure_ascii=False, indent=2)


def build_prompt(request: dict[str, Any]) -> str:
    developer_instructions = load_argumentagent_instructions()
    return (
        "You are the argumentagent for a Chinese research-to-manuscript workflow.\n"
        "Follow the project AGENTS.md, the referenced Part 3 skills, and the request hard_constraints.\n"
        "Return exactly one JSON object. Do not write files. Do not include markdown fences.\n\n"
        "Developer instructions for argumentagent:\n"
        f"{developer_instructions or '(no external argumentagent developer instructions found)'}\n\n"
        "Runtime request JSON:\n"
        f"{compact_request_for_prompt(request)}\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "artifacts": {\n'
        '    "candidate_trees": [\n'
        "      {\n"
        '        "candidate_id": "candidate_theory_first",\n'
        '        "strategy": "theory_first",\n'
        '        "root": {\n'
        '          "node_id": "thesis_theory_first",\n'
        '          "claim": "Chinese thesis claim",\n'
        '          "node_type": "thesis",\n'
        '          "support_source_ids": ["source ids from seed items"],\n'
        '          "wiki_page_ids": ["wiki page ids from seed items"],\n'
        '          "seed_item_ids": ["item ids from argument_seed_map.json"],\n'
        '          "warrant": "reasoning warrant",\n'
        '          "evidence_summary": "conservative evidence summary",\n'
        '          "assumptions": [],\n'
        '          "limitations": [],\n'
        '          "confidence": 0.7,\n'
        '          "risk_flags": ["innovation_type:concept_reframe"],\n'
        '          "children": []\n'
        "        }\n"
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Generate exactly three candidates with strategies theory_first, problem_solution, and case_application. "
        "Use the existing deterministic argument_seed_map only; include dense sub_arguments, counterargument, rebuttal, "
        "and source/wiki/seed trace on every node."
    )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.S)
    candidates.extend(fenced)
    match = re.search(r"\{.*\}", stripped, flags=re.S)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise RuntimeError("Codex argumentagent did not return a JSON object")


def run_codex(prompt: str, project_root: str) -> str:
    codex_bin = os.environ.get(CODEX_BIN_ENV, DEFAULT_CODEX_BIN)
    model = os.environ.get(CODEX_MODEL_ENV, DEFAULT_MODEL)
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json", delete=False) as tmp:
        output_path = Path(tmp.name)
    try:
        cmd = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--cd",
            project_root,
            "--sandbox",
            "read-only",
            "--model",
            model,
            "--output-last-message",
            str(output_path),
            prompt,
        ]
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            raise RuntimeError(
                "codex argumentagent command failed"
                + (f": {stderr}" if stderr else "")
                + (f"\nstdout: {stdout}" if stdout else "")
            )
        return output_path.read_text(encoding="utf-8")
    finally:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass


def validate_output(payload: dict[str, Any]) -> dict[str, Any]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise RuntimeError("Codex argumentagent output must include artifacts")
    candidate_trees = artifacts.get("candidate_trees")
    if not isinstance(candidate_trees, list) or len(candidate_trees) != 3:
        raise RuntimeError("Codex argumentagent output must include exactly three artifacts.candidate_trees")
    return payload


def main() -> None:
    request = load_request()
    project_root = str(request.get("project_root") or Path.cwd())
    prompt = build_prompt(request)
    raw_output = run_codex(prompt, project_root)
    payload = validate_output(extract_json_object(raw_output))
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"argumentagent_codex_cli.py failed: {exc}", file=sys.stderr)
        sys.exit(1)

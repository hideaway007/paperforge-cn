#!/usr/bin/env python3
"""
Codex CLI adapter for RTM writeagent requests.

Reads the JSON request produced by runtime/llm_writer_bridge.py, asks Codex to
act as the configured writeagent, and prints a JSON object accepted by the
bridge: text/body/manuscript plus optional abstract, keywords, conclusion.
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
CODEX_MODEL_ENV = "RTM_WRITEAGENT_MODEL"
DEFAULT_CODEX_BIN = "codex"
DEFAULT_MODEL = "gpt-5.4"


def load_request() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise RuntimeError("writeagent adapter input must be JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("writeagent adapter input must be a JSON object")
    return payload


def load_writeagent_instructions() -> str:
    config_path = Path.home() / ".codex" / "agents" / "writeagent.toml"
    if not config_path.exists():
        return ""
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    instructions = data.get("developer_instructions")
    return instructions if isinstance(instructions, str) else ""


def compact_request_for_prompt(request: dict[str, Any]) -> str:
    return json.dumps(request, ensure_ascii=False, indent=2)


def build_prompt(request: dict[str, Any]) -> str:
    developer_instructions = load_writeagent_instructions()
    return (
        "You are the writeagent for a Chinese research-to-manuscript workflow.\n"
        "Follow the project AGENTS.md and the request hard_constraints.\n"
        "Return exactly one JSON object. Do not write files. Do not include markdown fences.\n\n"
        "Developer instructions for writeagent:\n"
        f"{developer_instructions or '(no external writeagent developer instructions found)'}\n\n"
        "Runtime request JSON:\n"
        f"{compact_request_for_prompt(request)}\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "body": "continuous Chinese academic manuscript text",\n'
        '  "abstract": "optional abstract",\n'
        '  "keywords": ["optional", "keywords"],\n'
        '  "conclusion": "optional conclusion"\n'
        "}\n"
        "The body must read like thesis prose, not a workflow report. Avoid over-visible evidence-chain language."
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
    raise RuntimeError("Codex writeagent did not return a JSON object")


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
                "codex writeagent command failed"
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
    text = payload.get("body") or payload.get("text") or payload.get("manuscript")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Codex writeagent output must include non-empty body/text/manuscript")
    keywords = payload.get("keywords", [])
    if keywords is not None and not isinstance(keywords, list):
        payload["keywords"] = []
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
        print(f"writeagent_codex_cli.py failed: {exc}", file=sys.stderr)
        sys.exit(1)

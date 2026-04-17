#!/usr/bin/env python3
"""
scripts/new_workspace.py

从当前项目复制 harness 骨架，在项目内创建全新干净工作区。
不携带任何研究产物（raw-library、research-wiki、outputs、process-memory）。

默认在项目根目录下的 workspaces/ 子目录中创建，自动编号格式为 workspaces/ws_NNN/，
每次使用现有最大编号 + 1。

用法：
  python3 scripts/new_workspace.py                 # 空项目自动命名 → workspaces/ws_001/
  python3 scripts/new_workspace.py --name my_test  # → workspaces/my_test/
  python3 scripts/new_workspace.py /absolute/path  # 指定绝对路径
  python3 scripts/new_workspace.py --intake outputs/part1/intake.json --confirm-intake

完成后自动运行 python3 cli.py init 初始化 state。
"""

import sys
import shutil
import argparse
import subprocess
import json
import hashlib
import importlib.util
from pathlib import Path
import re
from datetime import datetime, timezone

# ── 哪些属于 harness（复制代码，不复制数据）──────────────────────────────────

# 整个目录复制（目录内所有内容都是 harness）
HARNESS_DIRS = [
    "docs",
    "manifests",
    "schemas",
    "scripts",
    "skills",
    "writing-policy",
]

# 单个文件复制
HARNESS_FILES = [
    "cli.py",
    "requirements.txt",
    "AGENTS.md",
    "pytest.ini",
]

# runtime/ 只复制代码文件，不复制 state.json / __pycache__
RUNTIME_FILES = [
    "runtime/llm_agent_bridge.py",
    "runtime/llm_writer_bridge.py",
    "runtime/pipeline.py",
    "runtime/source_quota.py",
    "runtime/writing_contract.py",
]

WRITING_POLICY_SOURCE_INDEX = {
    "schema_version": "1.0.0",
    "artifact_type": "writing_policy_source_index",
    "status": "empty_pending_human_input",
    "purpose": (
        "Part 4 audit entry for writing policy inputs. "
        "It indexes writing rules, style guides, reference cases, and rubrics only."
    ),
    "separation_rule": (
        "Research evidence remains in raw-library/ and research-wiki/. "
        "Do not register research evidence in writing-policy/."
    ),
    "rules": [],
    "style_guides": [],
    "reference_cases": [],
    "rubrics": [],
    "audit_notes": [
        "No tutor rules, style guides, reference cases, or rubrics are registered yet.",
        "Do not infer or fabricate writing policy items from research evidence.",
    ],
}

# ── 创建空目录骨架（.gitkeep 占位）──────────────────────────────────────────

EMPTY_DIRS = [
    "raw-library/papers",
    "raw-library/web-archives",
    "raw-library/normalized",
    "raw-library/provenance",
    "research-wiki/pages",
    "writing-policy/rules",
    "writing-policy/style_guides",
    "writing-policy/reference_cases",
    "writing-policy/rubrics",
    "outputs/part1",
    "outputs/part2",
    "outputs/part3/candidate_argument_trees",
    "outputs/part4",
    "outputs/part4/chapters",
    "outputs/part5/chapter_briefs",
    "outputs/part5/case_analysis_templates",
    "process-memory",
    "runtime",        # pipeline.py 会被复制进来
    "runtime/agents", # agent scripts 会被复制进来
]


def auto_name(project_root: Path) -> Path:
    """在 project_root/workspaces/ 下按最大现有编号递增创建 ws_NNN，不回填缺号。"""
    ws_dir = project_root / "workspaces"
    ws_dir.mkdir(exist_ok=True)
    max_number = 0
    for child in ws_dir.iterdir():
        match = re.fullmatch(r"ws_(\d{3})", child.name)
        if match:
            max_number = max(max_number, int(match.group(1)))

    next_number = max_number + 1
    if next_number > 999:
        raise RuntimeError("workspaces 编号已用尽")
    return ws_dir / f"ws_{next_number:03d}"


def validate_workspace_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", cleaned):
        raise ValueError("--name 只能包含英文字母、数字、下划线和连字符；路径请使用显式 target 参数")
    return cleaned


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} 必须是 JSON object")
    return data


def copy_harness(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=False)

    # 整目录
    for d in HARNESS_DIRS:
        s = src / d
        if s.exists():
            shutil.copytree(s, dst / d, dirs_exist_ok=False)
            print(f"  copied  {d}/")
        else:
            print(f"  skip    {d}/  (not found in source)")

    # 单文件
    for f in HARNESS_FILES:
        s = src / f
        if s.exists():
            shutil.copy2(s, dst / f)
            print(f"  copied  {f}")
        else:
            print(f"  skip    {f}  (not found in source)")

    # runtime 代码文件
    (dst / "runtime").mkdir(exist_ok=True)
    for f in RUNTIME_FILES:
        s = src / f
        if s.exists():
            shutil.copy2(s, dst / f)
            print(f"  copied  {f}")
        else:
            print(f"  skip    {f}  (not found in source)")

    agent_src = src / "runtime" / "agents"
    agent_dst = dst / "runtime" / "agents"
    if agent_src.exists():
        shutil.copytree(
            agent_src,
            agent_dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
        print("  copied  runtime/agents/")
    else:
        print("  skip    runtime/agents/  (not found in source)")

    # 空目录骨架
    for d in EMPTY_DIRS:
        p = dst / d
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()
    print(f"  created empty skeleton dirs")

    write_writing_policy_source_index(dst)


def init_workspace_state(dst: Path) -> None:
    result = subprocess.run(
        ["python3", "cli.py", "init"],
        cwd=dst,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"workspace init 失败: {result.stderr.strip()}")


def copy_intake_to_workspace(intake_path: Path, dst: Path) -> Path:
    target = dst / "outputs" / "part1" / "intake.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(intake_path, target)
    return target


def confirm_intake_gate_in_workspace(dst: Path, notes: str) -> None:
    pipeline_path = dst / "runtime" / "pipeline.py"
    spec = importlib.util.spec_from_file_location("workspace_pipeline", pipeline_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROJECT_ROOT = dst
    module.STATE_FILE = dst / "runtime" / "state.json"
    module.PROCESS_MEMORY_DIR = dst / "process-memory"
    module.start_stage("part1")
    module.confirm_human_gate("intake_confirmed", notes)


def write_workspace_manifest(
    src: Path,
    dst: Path,
    intake_path: Path,
    intake: dict,
    intake_sha256: str,
    confirmed_gate: bool,
) -> Path:
    manifest_path = dst / "workspace_manifest.json"
    manifest = {
        "schema_version": "1.0.0",
        "workspace_id": dst.name,
        "created_at": now_iso(),
        "source_project_root": str(src),
        "workspace_path": str(dst),
        "intake_id": intake.get("intake_id", "unknown"),
        "intake_sha256": intake_sha256,
        "source_intake_path": str(intake_path),
        "workspace_intake_path": "outputs/part1/intake.json",
        "confirmed_gate": "intake_confirmed" if confirmed_gate else None,
        "isolation_rule": "harness_only_plus_confirmed_intake",
        "copied_research_artifacts": False,
        "run_instruction": (
            "python3 cli.py confirm-gate intake_confirmed auto-runs runtime/agents/part1_runner.py "
            "inside this workspace unless --no-auto-run-part1 is used. For manual resume, cd this "
            "workspace, then run python3 runtime/agents/part1_runner.py"
        ),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return manifest_path


def workspace_registry_path(src: Path) -> Path:
    return src / "outputs" / "part1" / "workspace_manifest.json"


def load_workspace_registry(src: Path) -> dict:
    path = workspace_registry_path(src)
    if not path.exists():
        return {
            "schema_version": "1.0.0",
            "artifact_type": "part1_workspace_registry",
            "workspaces": [],
        }
    return load_json(path)


def write_workspace_registry(src: Path, registry: dict) -> Path:
    path = workspace_registry_path(src)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def find_existing_workspace_for_intake(src: Path, intake_sha256: str) -> dict | None:
    registry = load_workspace_registry(src)
    for entry in registry.get("workspaces", []):
        if entry.get("intake_sha256") != intake_sha256:
            continue
        workspace_path = Path(entry.get("workspace_path", ""))
        if workspace_path.exists():
            return entry
    return None


def register_workspace(src: Path, workspace_manifest: dict) -> Path:
    registry = load_workspace_registry(src)
    workspaces = [
        entry
        for entry in registry.get("workspaces", [])
        if entry.get("intake_sha256") != workspace_manifest["intake_sha256"]
    ]
    entry = {
        "workspace_id": workspace_manifest["workspace_id"],
        "workspace_path": workspace_manifest["workspace_path"],
        "intake_id": workspace_manifest["intake_id"],
        "intake_sha256": workspace_manifest["intake_sha256"],
        "created_at": workspace_manifest["created_at"],
    }
    workspaces.append(entry)
    registry["workspaces"] = workspaces
    registry["latest_workspace"] = entry
    return write_workspace_registry(src, registry)


def create_workspace_for_intake(
    src: Path,
    dst: Path,
    intake_path: Path,
    confirm_intake: bool = False,
    notes: str = "",
) -> dict:
    src = src.resolve()
    dst = dst.resolve()
    intake_path = intake_path.resolve()
    if not intake_path.exists():
        raise FileNotFoundError(f"intake.json 不存在: {intake_path}")
    if dst.exists():
        raise FileExistsError(f"目标 workspace 已存在: {dst}")

    intake = load_json(intake_path)
    intake_sha256 = sha256_file(intake_path)
    copy_harness(src, dst)
    copy_intake_to_workspace(intake_path, dst)
    init_workspace_state(dst)

    if confirm_intake:
        confirm_intake_gate_in_workspace(
            dst,
            notes or "Workspace initialized from confirmed Part 1 intake",
        )

    manifest_path = write_workspace_manifest(
        src=src,
        dst=dst,
        intake_path=intake_path,
        intake=intake,
        intake_sha256=intake_sha256,
        confirmed_gate=confirm_intake,
    )
    workspace_manifest = load_json(manifest_path)
    registry_path = register_workspace(src, workspace_manifest)
    return {
        "created": True,
        "workspace_path": dst,
        "manifest_path": manifest_path,
        "registry_path": registry_path,
        "intake_sha256": intake_sha256,
    }


def ensure_workspace_for_intake(
    src: Path,
    intake_path: Path,
    target: Path | None = None,
    name: str | None = None,
    confirm_intake: bool = False,
    notes: str = "",
    force_new: bool = False,
) -> dict:
    src = src.resolve()
    intake_path = intake_path.resolve()
    intake_sha256 = sha256_file(intake_path)

    if not force_new and target is None and name is None:
        existing = find_existing_workspace_for_intake(src, intake_sha256)
        if existing:
            return {
                "created": False,
                "workspace_path": Path(existing["workspace_path"]),
                "registry_path": workspace_registry_path(src),
                "intake_sha256": intake_sha256,
            }

    if target is not None:
        dst = target.resolve()
    elif name:
        dst = src / "workspaces" / validate_workspace_name(name)
    else:
        dst = auto_name(src)

    return create_workspace_for_intake(
        src=src,
        dst=dst,
        intake_path=intake_path,
        confirm_intake=confirm_intake,
        notes=notes,
    )


def write_writing_policy_source_index(project_root: Path) -> None:
    """Create or preserve the Part 4 writing-policy audit entry."""
    path = project_root / "writing-policy" / "source_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = load_json(path)
        except (json.JSONDecodeError, RuntimeError):
            existing = {}
        has_baseline_policy = bool(existing.get("rules")) and bool(existing.get("style_guides"))
        if has_baseline_policy:
            print("  preserved writing-policy/source_index.json")
            return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(WRITING_POLICY_SOURCE_INDEX, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("  created writing-policy/source_index.json")


def main():
    parser = argparse.ArgumentParser(description="Create a clean harness workspace")
    parser.add_argument("target", nargs="?", help="目标路径（可选，默认自动命名）")
    parser.add_argument("--name", help="在同级目录创建指定名称的工作区")
    parser.add_argument("--intake", help="将已确认 intake.json 复制到新 workspace")
    parser.add_argument("--confirm-intake", action="store_true",
                        help="在新 workspace 内自动确认 intake_confirmed gate")
    parser.add_argument("--notes", default="", help="workspace 内确认 intake 的备注")
    parser.add_argument("--force-new", action="store_true",
                        help="即使同一 intake 已创建 workspace，也强制新建")
    args = parser.parse_args()

    src = Path(__file__).parent.parent.resolve()

    if args.target:
        dst = Path(args.target).resolve()
    elif args.name:
        dst = src / "workspaces" / validate_workspace_name(args.name)
    else:
        dst = auto_name(src)

    if args.intake:
        intake_path = (src / args.intake).resolve() if not Path(args.intake).is_absolute() else Path(args.intake).resolve()
        result = ensure_workspace_for_intake(
            src=src,
            intake_path=intake_path,
            target=dst if args.target else None,
            name=args.name,
            confirm_intake=args.confirm_intake,
            notes=args.notes,
            force_new=args.force_new,
        )
        if result["created"]:
            print(f"\n✓ intake workspace 已创建: {result['workspace_path']}")
        else:
            print(f"\n✓ intake workspace 已存在: {result['workspace_path']}")
        print(f"  registry: {result['registry_path']}")
        print(f"  cd {result['workspace_path']}")
        print("  python3 runtime/agents/part1_runner.py\n")
        return

    print(f"\n新建工作区: {dst}")
    print(f"源 harness:  {src}\n")

    if dst.exists():
        print(f"错误: 目标目录已存在: {dst}", file=sys.stderr)
        sys.exit(1)

    copy_harness(src, dst)

    # 初始化 state
    print("\n初始化 state...")
    try:
        init_workspace_state(dst)
        print("  Project initialized.")
    except RuntimeError as e:
        print(f"  警告: {e}")

    print(f"\n✓ 工作区就绪: {dst}")
    print(f"  cd {dst}")
    print(f"  python3 cli.py status\n")


if __name__ == "__main__":
    main()

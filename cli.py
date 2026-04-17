#!/usr/bin/env python3
# macOS: use `python3 cli.py <command>`
"""
Research-to-Manuscript Pipeline CLI

Commands:
  init                        初始化项目 state
  status                      查看当前 pipeline 状态
  start   <stage>             标记阶段为 in_progress
  advance <stage>             校验 gate 并推进阶段
  validate <stage>            仅校验 gate，不推进
  confirm-gate <gate_id>      记录人工节点确认
  doctor                      运行诊断
  audit                       查看 process memory 日志
  part1-intake                生成 Part 1 intake 表单请求
  confirm-gate intake_confirmed 后自动创建隔离 workspace 并启动 Part 1 runner
  part1-export-table          导出 Part 1 已下载论文清单到 outputs/part1
  part1-archive-web           导入 Obsidian/Web Clipper 生成的网页 Markdown 并写 provenance
  part2-generate              生成 Part 2 Research Wiki 草稿（不自动推进 Part 2）
  part2-health                检查 Part 2 wiki / writing-policy 是否可进入 Part 3
  part3-seed-map              生成 Part 3 argument seed map
  part3-generate              调用 LLM argumentagent 生成 3 份候选 argument tree
  part3-compare               生成候选 comparison
  part3-refine                基于 seed map 和 comparison 生成 refined candidates
  part3-review                查看候选比较与人工选择入口
  part3-select                记录人工选择并锁定 canonical argument_tree
  part4-generate              生成 Part 4 paper outline
  part4-check                 检查 Part 4 outline / rationale / alignment gate
  part4-confirm               兼容旧流程的 deprecated no-op
  part5-authorize             兼容旧流程的 deprecated no-op
  part5-prep                  生成 Part 5 写作输入包
  part5-confirm-prep          兼容旧流程的 deprecated no-op
  part5-draft                 生成 manuscript_v1
  part5-review                生成结构化 review、用户报告与 citation precheck
  part5-confirm-review        兼容旧流程的 deprecated no-op
  part5-revise                生成 manuscript_v2 / revision_log / Part 6 readiness
  part5-check                 检查 Part 5 completion gate
  part5-accept                兼容旧流程的 deprecated no-op
  part6-precheck              只读检查 Part 6 entry/package gate
  part6-authorize             记录 Part 6 finalization 人工授权
  part6-finalize              运行 Part 6 finalizer step，不自动确认人工 gate
  part6-check                 检查 Part 6 package gate
  part6-confirm-final         记录 Part 6 最终人工决策

Usage:
  python cli.py init
  python cli.py status
  python cli.py start part1
  python cli.py part1-intake
  python cli.py confirm-gate intake_confirmed --notes "主题已确认：..."
  python cli.py confirm-gate intake_confirmed --notes "只确认" --no-auto-run-part1
  python cli.py part1-export-table
  python cli.py part1-archive-web --source-id crossref_2026_001 --url "https://doi.org/..." --from-obsidian page.md
  python cli.py advance part1
  python cli.py part2-generate --dry-run
  python cli.py part2-generate --force
  python cli.py part4-generate --dry-run
  python cli.py part4-generate --force
  python cli.py part5-prep
  python cli.py part5-draft
  python cli.py part5-review
  python cli.py part5-revise
  python cli.py part6-precheck
  python cli.py part6-authorize --notes "授权进入 Part 6 finalization"
  python cli.py part6-finalize --step all
  python cli.py part6-check
  python cli.py part6-confirm-final --notes "最终状态：内部评阅"
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

# Ensure runtime/ is on the import path
sys.path.insert(0, str(Path(__file__).parent / "runtime"))

from pipeline import (
    init_state,
    get_status,
    validate_gate,
    advance_stage,
    start_stage,
    confirm_human_gate,
    run_doctor,
    get_next_action,
    STAGE_ORDER,
    PROCESS_MEMORY_DIR,
)


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_init(args):
    try:
        init_state()
        print("Project initialized.")
        print("  State file: runtime/state.json")
        print("  Next: run `python cli.py status` to see pipeline state.")
    except RuntimeError as e:
        _err(e)


def cmd_status(args):
    try:
        status = get_status()
    except FileNotFoundError as e:
        _err(e)

    _section("Research-to-Manuscript Pipeline Status")
    print(f"  Initialized : {status['initialized_at'] or '—'}")
    print(f"  Current     : {status['current_stage'] or 'none'}")

    STATUS_ICON = {
        "not_started": "○",
        "in_progress":  "◉",
        "completed":    "✓",
        "failed":       "✗",
    }

    for stage_id in STAGE_ORDER:
        s = status["stages"][stage_id]
        icon      = STATUS_ICON.get(s["status"], "?")
        gate_icon = "✓" if s["gate_passed"] else "○"
        print(f"\n  {icon} {stage_id.upper():<8}  gate: {gate_icon}")

        for art in s["artifacts"]:
            if art["exists"]:
                schema_note = (
                    "  [schema ✓]" if art["schema_valid"] is True
                    else "  [schema ✗]" if art["schema_valid"] is False
                    else ""
                )
                print(f"      ✓ {art['path']}{schema_note}")
            else:
                print(f"      ✗ {art['path']}  (missing)")

        for gate_id in s["pending_human_gates"]:
            print(f"      ⚠ 人工节点待确认: {gate_id}")

    if status["last_failure"]:
        f = status["last_failure"]
        print(f"\n  Last failure [{f['stage_id']}] @ {f['failed_at']}")
        for issue in f.get("issues", []):
            print(f"    - {issue}")

    next_action = status.get("next_action") or {}
    if next_action:
        print("\n  Next action")
        print(f"    Stage  : {next_action.get('stage_id')}")
        print(f"    Command: {next_action.get('command')}")
        print(f"    Why    : {next_action.get('reason')}")
    print()


def cmd_start(args):
    stage_id = args.stage
    try:
        if stage_id == "part1":
            _run_agent_script("part1_intake.py", "--force")
        start_stage(stage_id)
        print(f"Stage {stage_id} → in_progress")
    except Exception as e:
        _err(e)


def cmd_validate(args):
    stage_id = args.stage
    print(f"Validating gate: {stage_id} ...")
    passed, issues = validate_gate(stage_id)
    if passed:
        print(f"  ✓ Gate passed — {stage_id} artifacts and gates are valid.")
    else:
        print(f"  ✗ Gate FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def cmd_advance(args):
    stage_id = args.stage
    print(f"Advancing stage: {stage_id} ...")
    success, issues = advance_stage(stage_id)

    if success:
        if stage_id == "part1":
            _run_agent_script("part1_library_table_exporter.py")
        print(f"  ✓ {stage_id} 推进成功。")
        idx = STAGE_ORDER.index(stage_id)
        if idx + 1 < len(STAGE_ORDER):
            next_stage = STAGE_ORDER[idx + 1]
            print(f"  Next: `python cli.py start {next_stage}`")
    else:
        print(f"  ✗ 无法推进 — {len(issues)} 个 gate 问题：")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def cmd_confirm_gate(args):
    gate_id = args.gate_id
    notes   = args.notes or ""
    try:
        confirm_human_gate(gate_id, notes)
        print(f"  ✓ 人工节点已确认: {gate_id}")
        if notes:
            print(f"  Notes: {notes}")
        print(f"  已写入 process-memory/")
        if gate_id == "intake_confirmed":
            workspace_path = _bootstrap_part1_workspace_after_intake(notes)
            print(f"  ✓ 已创建/复用隔离 workspace: {workspace_path}")
            if getattr(args, "no_auto_run_part1", False):
                print(f"  下一步: cd {workspace_path} && python3 runtime/agents/part1_runner.py")
            else:
                print("  → 在隔离 workspace 中启动 Part 1 runner")
                _run_workspace_part1_runner(workspace_path)
    except (ValueError, RuntimeError) as e:
        _err(e)


def cmd_doctor(args):
    _section("Diagnostics")
    issues = run_doctor()
    if not issues:
        print("  ✓ 未发现问题。")
    else:
        print(f"  {len(issues)} 个问题：")
        for issue in issues:
            print(f"    - {issue}")
    next_action = get_next_action()
    print("\n  Next action")
    print(f"    Stage  : {next_action.get('stage_id')}")
    print(f"    Command: {next_action.get('command')}")
    print(f"    Why    : {next_action.get('reason')}")


def cmd_audit(args):
    _section("Process Memory Log")
    if not PROCESS_MEMORY_DIR.exists():
        print("  process-memory/ 目录不存在。")
        return

    files = sorted(PROCESS_MEMORY_DIR.glob("*.json"))
    if not files:
        print("  暂无记录。")
        return

    limit = args.limit or 20
    shown = files[-limit:]
    print(f"  显示最近 {len(shown)} / {len(files)} 条记录\n")

    for fp in shown:
        try:
            with open(fp, encoding="utf-8") as f:
                rec = json.load(f)
            ts    = rec.pop("timestamp", "?")
            event = rec.pop("event", fp.stem)
            print(f"  [{ts}] {event}")
            for k, v in rec.items():
                if isinstance(v, list):
                    for item in v:
                        print(f"      {k}: {item}")
                else:
                    print(f"      {k}: {v}")
        except Exception:
            print(f"  [unreadable] {fp.name}")


def cmd_part1_intake(args):
    script_args = []
    if args.force:
        script_args.append("--force")
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part1_intake.py", *script_args)


def cmd_part1_export_table(args):
    script_args = []
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part1_library_table_exporter.py", *script_args)


def cmd_part1_archive_web(args):
    script_args = ["--source-id", args.source_id, "--url", args.url]
    if args.from_obsidian:
        script_args.extend(["--from-obsidian", args.from_obsidian])
    if args.watch_obsidian_dir:
        script_args.extend(["--watch-obsidian-dir", args.watch_obsidian_dir])
    if args.open_in_chrome:
        script_args.append("--open-in-chrome")
    if args.fetch_html:
        script_args.append("--fetch-html")
    if args.timeout:
        script_args.extend(["--timeout", str(args.timeout)])
    for flag, value in [
        ("--project-root", args.project_root),
        ("--query-id", args.query_id),
        ("--db", args.db),
        ("--title", args.title),
        ("--authors", args.authors),
        ("--journal", args.journal),
        ("--year", str(args.year) if args.year else None),
        ("--doi-or-source-id", args.doi_or_source_id),
        ("--abstract", args.abstract),
        ("--keywords", args.keywords),
    ]:
        if value:
            script_args.extend([flag, value])
    _run_agent_script("web_markdown_archiver.py", *script_args)


def cmd_part3_generate(args):
    script_args = []
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    if args.allow_wiki_fallback:
        script_args.append("--allow-wiki-fallback")
    if args.allow_deterministic_fallback:
        script_args.append("--allow-deterministic-fallback")
    _run_agent_script("part3_candidate_generator.py", *script_args)


def cmd_part3_seed_map(args):
    script_args = []
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part3_argument_seed_map_generator.py", *script_args)


def cmd_part3_compare(args):
    script_args = []
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part3_comparison_generator.py", *script_args)
    project_root = Path(args.project_root).resolve() if args.project_root else Path(__file__).parent
    table_path = project_root / "outputs" / "part3" / "candidate_selection_table.md"
    if table_path.exists():
        print(f"  ✓ 候选表: {table_path.relative_to(project_root)}")


def cmd_part3_refine(args):
    script_args = []
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    if args.force:
        script_args.append("--force")
    if args.allow_after_selection:
        script_args.append("--allow-after-selection")
    _run_agent_script("part3_argument_refiner.py", *script_args)


def cmd_part3_review(args):
    project_root = Path(args.project_root).resolve() if args.project_root else Path(__file__).parent
    comparison_path = project_root / "outputs" / "part3" / "candidate_comparison.json"
    table_path = project_root / "outputs" / "part3" / "candidate_selection_table.md"
    if not comparison_path.exists():
        _err("缺少 outputs/part3/candidate_comparison.json；先运行 `python3 cli.py part3-compare`")
    try:
        with open(comparison_path, encoding="utf-8") as f:
            comparison = json.load(f)
    except json.JSONDecodeError as e:
        _err(f"candidate_comparison.json 无法解析: {e}")

    _section("Part 3 Candidate Review")
    try:
        from agents.part3_comparison_generator import render_selection_table
    except Exception as e:
        _err(f"无法加载 Part 3 selection table renderer: {e}")

    table_text = render_selection_table(comparison)
    table_path.write_text(table_text, encoding="utf-8")
    print(table_text)
    recommendation = comparison.get("recommendation", {})
    recommended_id = recommendation.get("recommended_candidate_id", "unknown")
    print(f"Selection table written: {table_path.relative_to(project_root)}")
    print(f'Next: python3 cli.py part3-select --candidate-id {recommended_id} --notes "选择理由"')


def cmd_part2_generate(args):
    script_args = []
    if args.dry_run:
        script_args.append("--dry-run")
    if args.force:
        script_args.append("--force")
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part2_wiki_generator.py", *script_args, check_exists=False)


def cmd_part3_select(args):
    script_args = ["--candidate-id", args.candidate_id, "--notes", args.notes]
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    if args.force:
        script_args.append("--force")
    if args.candidate_source:
        script_args.extend(["--candidate-source", args.candidate_source])
    _run_agent_script("part3_selection_locker.py", *script_args)
    print("  ✓ runtime/state.json 已记录 human gate: argument_tree_selected")


def cmd_part2_health(args):
    print("Checking Part 2 wiki health + writing-policy layer ...")
    passed, issues = validate_gate("part2")
    if passed:
        status = get_status()
        part2 = status["stages"]["part2"]
        if part2["status"] == "completed" and part2["gate_passed"] is True:
            next_action = status.get("next_action", {})
            print("  ✓ Part 2 已完成且 gate 仍然通过。")
            if next_action:
                print(f"  Next: `{next_action.get('command')}`")
        else:
            print("  ✓ Part 2 gate passed — 可以进入 Part 3 candidate generation。")
            print("  Next: `python3 cli.py advance part2`")
    else:
        print(f"  ✗ Part 2 gate FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def cmd_part4_generate(args):
    script_args = []
    if args.dry_run:
        script_args.append("--dry-run")
    if args.force:
        script_args.append("--force")
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part4_outline_generator.py", *script_args)


def cmd_part4_check(args):
    print("Checking Part 4 outline + rationale + alignment gate ...")
    passed, issues = validate_gate("part4")
    if passed:
        print("  ✓ Part 4 gate passed — outline artifacts/alignment 合格，可进入 Part 5。")
    else:
        print(f"  ✗ Part 4 gate FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def cmd_part4_confirm(args):
    notes = args.notes.strip()
    if not notes:
        _err("part4-confirm requires non-empty --notes")
    try:
        confirm_human_gate("outline_confirmed", notes)
        print("  ⚠ part4-confirm 已废弃：outline_confirmed 不再阻断流程。")
        print(f"  Notes: {notes}")
        print("  已作为 deprecated no-op 写入 process-memory/")
    except Exception as e:
        _err(e)


def _part5_notes(args, command_name: str) -> str:
    notes = (args.notes or "").strip()
    if not notes:
        _err(f"{command_name} requires non-empty --notes")
    return notes


def cmd_part5_authorize(args):
    notes = _part5_notes(args, "part5-authorize")
    try:
        confirm_human_gate("writing_phase_authorized", notes)
        print("  ⚠ part5-authorize 已废弃：writing_phase_authorized 不再阻断流程。")
        print(f"  Notes: {notes}")
        print("  已作为 deprecated no-op 写入 process-memory/")
    except Exception as e:
        _err(e)


def cmd_part5_confirm_prep(args):
    notes = _part5_notes(args, "part5-confirm-prep")
    try:
        confirm_human_gate("part5_prep_confirmed", notes)
        print("  ⚠ part5-confirm-prep 已废弃：part5_prep_confirmed 不再阻断流程。")
        print(f"  Notes: {notes}")
        print("  已作为 deprecated no-op 写入 process-memory/")
    except Exception as e:
        _err(e)


def cmd_part5_confirm_review(args):
    notes = _part5_notes(args, "part5-confirm-review")
    try:
        confirm_human_gate("part5_review_completed", notes)
        print("  ⚠ part5-confirm-review 已废弃：part5_review_completed 不再阻断流程。")
        print(f"  Notes: {notes}")
        print("  已作为 deprecated no-op 写入 process-memory/")
    except Exception as e:
        _err(e)


def cmd_part5_accept(args):
    notes = _part5_notes(args, "part5-accept")
    try:
        confirm_human_gate("manuscript_v2_accepted", notes)
        print("  ⚠ part5-accept 已废弃：manuscript_v2_accepted 不再阻断流程。")
        print(f"  Notes: {notes}")
        print("  已作为 deprecated no-op 写入 process-memory/")
    except Exception as e:
        _err(e)


def _run_part5_step(args, step: str) -> None:
    script_args = ["--step", step]
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part5_mvp_generator.py", *script_args)


def cmd_part5_prep(args):
    _run_part5_step(args, "prep")


def cmd_part5_draft(args):
    _run_part5_step(args, "draft")


def cmd_part5_review(args):
    _run_part5_step(args, "review")


def cmd_part5_revise(args):
    _run_part5_step(args, "revise")


def cmd_part5_check(args):
    print("Checking Part 5 draft + review + revision gate ...")
    passed, issues = validate_gate("part5")
    if passed:
        print("  ✓ Part 5 gate passed — manuscript_v2 / review / revision artifacts 合格；Part 6 仍不自动推进。")
    else:
        print(f"  ✗ Part 5 gate FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def _part6_notes(args, command_name: str) -> str:
    notes = (args.notes or "").strip()
    if not notes:
        _err(f"{command_name} requires non-empty --notes")
    return notes


def cmd_part6_precheck(args):
    print("Checking Part 6 entry/package gate ...")
    passed, issues = validate_gate("part6")
    if passed:
        print("  ✓ Part 6 entry/package gate passed.")
    else:
        print(f"  ✗ Part 6 entry/package gate not passed ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        print("  No Part 6 artifacts were generated.")


def cmd_part6_authorize(args):
    notes = _part6_notes(args, "part6-authorize")
    try:
        confirm_human_gate("part6_finalization_authorized", notes)
        print("  ✓ Part 6 finalization authorized.")
        print(f"  Notes: {notes}")
        print("  已写入 process-memory/")
    except Exception as e:
        _err(e)


def cmd_part6_finalize(args):
    script_args = ["--step", args.step]
    if args.project_root:
        script_args.extend(["--project-root", args.project_root])
    _run_agent_script("part6_mvp_finalizer.py", *script_args)


def cmd_part6_check(args):
    print("Checking Part 6 package gate ...")
    passed, issues = validate_gate("part6")
    if passed:
        print("  ✓ Part6 package gate passed.")
    else:
        print(f"  ✗ Part 6 package gate FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"    - {issue}")
        sys.exit(1)


def cmd_part6_confirm_final(args):
    notes = _part6_notes(args, "part6-confirm-final")
    try:
        confirm_human_gate("part6_final_decision_confirmed", notes)
        print("  ✓ Part 6 final decision recorded.")
        print(f"  Notes: {notes}")
        print("  已写入 process-memory/；未执行 submission。")
    except Exception as e:
        _err(e)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _err(msg) -> None:
    print(f"\nError: {msg}", file=sys.stderr)
    sys.exit(1)


def _run_agent_script(script_name: str, *script_args: str, check_exists: bool = True) -> None:
    script_path = Path(__file__).parent / "runtime" / "agents" / script_name
    if check_exists and not script_path.exists():
        _err(f"Agent script not found: {script_path}")
    result = subprocess.run([sys.executable, str(script_path), *script_args])
    if result.returncode != 0:
        sys.exit(result.returncode)


def _run_project_script(script_name: str, *script_args: str) -> None:
    script_path = Path(__file__).parent / "scripts" / script_name
    if not script_path.exists():
        _err(f"Project script not found: {script_path}")
    result = subprocess.run([sys.executable, str(script_path), *script_args])
    if result.returncode != 0:
        sys.exit(result.returncode)


def _run_workspace_part1_runner(workspace_path: Path) -> None:
    workspace_path = Path(workspace_path).resolve()
    runner_path = workspace_path / "runtime" / "agents" / "part1_runner.py"
    if not runner_path.exists():
        _err(f"Workspace Part 1 runner not found: {runner_path}")
    result = subprocess.run([sys.executable, str(runner_path)], cwd=workspace_path)
    if result.returncode != 0:
        sys.exit(result.returncode)


def _bootstrap_part1_workspace_after_intake(notes: str) -> Path:
    _run_project_script(
        "new_workspace.py",
        "--intake",
        "outputs/part1/intake.json",
        "--confirm-intake",
        "--notes",
        notes,
    )
    manifest_path = Path(__file__).parent / "outputs" / "part1" / "workspace_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            workspace_path = (manifest.get("latest_workspace") or {}).get("workspace_path")
            if workspace_path:
                return Path(workspace_path)
        except (OSError, json.JSONDecodeError) as e:
            _err(f"workspace registry 无法解析: {manifest_path}: {e}")
    return Path(__file__).parent / "workspaces"


# ── Argument parser ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="Research-to-Manuscript Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init",   help="初始化项目 state")
    sub.add_parser("status", help="查看 pipeline 状态")
    sub.add_parser("doctor", help="运行诊断")

    p_audit = sub.add_parser("audit", help="查看 process memory 日志")
    p_audit.add_argument("--limit", type=int, default=20, metavar="N",
                         help="显示最近 N 条记录（默认 20）")

    p_start = sub.add_parser("start", help="标记阶段为 in_progress")
    p_start.add_argument("stage", choices=STAGE_ORDER)

    p_validate = sub.add_parser("validate", help="校验 stage gate（不推进）")
    p_validate.add_argument("stage", choices=STAGE_ORDER)

    p_advance = sub.add_parser("advance", help="校验 gate 并推进阶段")
    p_advance.add_argument("stage", choices=STAGE_ORDER)

    p_confirm = sub.add_parser("confirm-gate", help="记录人工节点确认")
    p_confirm.add_argument("gate_id",
                           help="Gate ID，如 intake_confirmed、argument_tree_selected")
    p_confirm.add_argument("--notes", metavar="TEXT",
                           help="确认备注（建议记录决策依据）")
    p_confirm.add_argument(
        "--no-auto-run-part1",
        action="store_true",
        help="确认 intake 后只创建/复用隔离 workspace，不自动启动 Part 1 runner",
    )

    p_part1_intake = sub.add_parser("part1-intake", help="生成 Part 1 intake 表单请求")
    p_part1_intake.add_argument("--force", action="store_true",
                                help="覆盖 outputs/part1/intake_template.json")
    p_part1_intake.add_argument("--project-root", metavar="PATH",
                                help="透传给 Part 1 intake agent 的项目根目录")

    p_part1_export_table = sub.add_parser(
        "part1-export-table",
        help="导出 Part 1 已下载论文清单到 outputs/part1",
    )
    p_part1_export_table.add_argument("--project-root", metavar="PATH",
                                      help="透传给 Part 1 exporter 的项目根目录")

    p_part1_archive_web = sub.add_parser(
        "part1-archive-web",
        help="导入 Obsidian/Web Clipper 生成的网页 Markdown 并写 Part 1 provenance",
    )
    p_part1_archive_web.add_argument("--source-id", required=True)
    p_part1_archive_web.add_argument("--url", required=True)
    p_part1_archive_web.add_argument("--from-obsidian", metavar="PATH")
    p_part1_archive_web.add_argument("--watch-obsidian-dir", metavar="PATH")
    p_part1_archive_web.add_argument("--open-in-chrome", action="store_true")
    p_part1_archive_web.add_argument("--fetch-html", action="store_true")
    p_part1_archive_web.add_argument("--timeout", type=int, default=180)
    p_part1_archive_web.add_argument("--project-root", metavar="PATH")
    p_part1_archive_web.add_argument("--query-id", default="web_archive_manual")
    p_part1_archive_web.add_argument("--db", default="web")
    p_part1_archive_web.add_argument("--title")
    p_part1_archive_web.add_argument("--authors")
    p_part1_archive_web.add_argument("--journal")
    p_part1_archive_web.add_argument("--year", type=int)
    p_part1_archive_web.add_argument("--doi-or-source-id")
    p_part1_archive_web.add_argument("--abstract")
    p_part1_archive_web.add_argument("--keywords")

    p_part3_generate = sub.add_parser("part3-generate", help="生成 3 份候选 argument tree")
    p_part3_generate.add_argument("--project-root", metavar="PATH",
                                  help="透传给 Part 3 generator 的项目根目录")
    p_part3_generate.add_argument("--allow-wiki-fallback", action="store_true",
                                  help="仅配合 --allow-deterministic-fallback 做离线 wiki fallback；正式 Part 3 不使用")
    p_part3_generate.add_argument("--allow-deterministic-fallback", action="store_true",
                                  help="显式允许离线 deterministic fallback；正式 Part 3 论点应由 LLM argumentagent 生成")

    p_part3_seed_map = sub.add_parser("part3-seed-map", help="生成 Part 3 argument seed map")
    p_part3_seed_map.add_argument("--project-root", metavar="PATH",
                                  help="透传给 Part 3 seed map agent 的项目根目录")

    p_part3_compare = sub.add_parser("part3-compare", help="生成 Part 3 候选 comparison")
    p_part3_compare.add_argument("--project-root", metavar="PATH",
                                 help="透传给 Part 3 comparison agent 的项目根目录")

    p_part3_refine = sub.add_parser(
        "part3-refine",
        help="基于 seed map 和 comparison 生成 refined candidates（不写 canonical）",
    )
    p_part3_refine.add_argument("--project-root", metavar="PATH",
                                help="透传给 Part 3 refiner 的项目根目录")
    p_part3_refine.add_argument("--force", action="store_true",
                                help="只覆盖 refined candidates，不覆盖原始候选或 canonical")
    p_part3_refine.add_argument("--allow-after-selection", action="store_true",
                                help="允许 human selection 后重新生成 refined candidates；仍不写 canonical")

    p_part3_review = sub.add_parser("part3-review", help="查看 Part 3 候选比较与人工选择入口")
    p_part3_review.add_argument("--project-root", metavar="PATH",
                                help="读取指定项目根目录的 candidate_comparison.json")

    p_part2_generate = sub.add_parser(
        "part2-generate",
        help="生成 Part 2 Research Wiki 草稿（不自动推进 Part 2）",
    )
    p_part2_generate.add_argument("--dry-run", action="store_true",
                                  help="透传给 Part 2 agent：打印计划但不写文件")
    p_part2_generate.add_argument("--force", action="store_true",
                                  help="透传给 Part 2 agent：允许覆盖已生成 wiki 草稿")
    p_part2_generate.add_argument("--project-root", metavar="PATH",
                                  help="透传给 Part 2 agent 的项目根目录")

    sub.add_parser("part2-health", help="检查 Part 2 wiki / writing-policy 是否可进入 Part 3")

    p_part3_select = sub.add_parser(
        "part3-select",
        help="记录人工选择并锁定 canonical argument_tree",
    )
    p_part3_select.add_argument("--candidate-id", required=True,
                                help="候选 ID，如 candidate_theory_first")
    p_part3_select.add_argument("--notes", required=True,
                                help="人工选择理由，不能为空")
    p_part3_select.add_argument("--project-root", metavar="PATH",
                                help="透传给 Part 3 selection locker 的项目根目录")
    p_part3_select.add_argument("--force", action="store_true",
                                help="覆盖既有 Part 3 canonical lock（仅在用户明确要求重锁定时使用）")
    p_part3_select.add_argument("--candidate-source", choices=["original", "refined"],
                                default="original",
                                help="选择原始候选或 refined candidate")

    p_part4_generate = sub.add_parser(
        "part4-generate",
        help="生成 Part 4 paper outline",
    )
    p_part4_generate.add_argument("--dry-run", action="store_true",
                                  help="透传给 Part 4 agent：打印产物但不写文件")
    p_part4_generate.add_argument("--force", action="store_true",
                                  help="透传给 Part 4 agent：允许覆盖既有 outline")
    p_part4_generate.add_argument("--project-root", metavar="PATH",
                                  help="透传给 Part 4 agent 的项目根目录")

    sub.add_parser("part4-check", help="检查 Part 4 outline / rationale / alignment gate")

    p_part4_confirm = sub.add_parser(
        "part4-confirm",
        help="兼容旧流程的 deprecated no-op",
    )
    p_part4_confirm.add_argument("--notes", required=True, metavar="TEXT",
                                 help="人工确认备注，不能为空")

    p_part5_authorize = sub.add_parser(
        "part5-authorize",
        help="兼容旧流程的 deprecated no-op",
    )
    p_part5_authorize.add_argument("--notes", required=True, metavar="TEXT",
                                   help="人工授权备注，不能为空")

    p_part5_prep = sub.add_parser(
        "part5-prep",
        help="生成 Part 5 写作输入包",
    )
    p_part5_prep.add_argument("--project-root", metavar="PATH",
                              help="透传给 Part 5 agent 的项目根目录")

    p_part5_confirm_prep = sub.add_parser(
        "part5-confirm-prep",
        help="兼容旧流程的 deprecated no-op",
    )
    p_part5_confirm_prep.add_argument("--notes", required=True, metavar="TEXT",
                                      help="人工确认备注，不能为空")

    p_part5_draft = sub.add_parser(
        "part5-draft",
        help="基于写作输入包生成 manuscript_v1",
    )
    p_part5_draft.add_argument("--project-root", metavar="PATH",
                               help="透传给 Part 5 agent 的项目根目录")

    p_part5_review = sub.add_parser(
        "part5-review",
        help="对 manuscript_v1 生成结构化 review 与 citation precheck",
    )
    p_part5_review.add_argument("--project-root", metavar="PATH",
                                help="透传给 Part 5 agent 的项目根目录")

    p_part5_confirm_review = sub.add_parser(
        "part5-confirm-review",
        help="兼容旧流程的 deprecated no-op",
    )
    p_part5_confirm_review.add_argument("--notes", required=True, metavar="TEXT",
                                        help="人工确认备注，不能为空")

    p_part5_revise = sub.add_parser(
        "part5-revise",
        help="基于 review 生成 manuscript_v2、revision_log 与 Part 6 readiness",
    )
    p_part5_revise.add_argument("--project-root", metavar="PATH",
                                help="透传给 Part 5 agent 的项目根目录")

    sub.add_parser("part5-check", help="检查 Part 5 draft / review / revision gate")

    p_part5_accept = sub.add_parser(
        "part5-accept",
        help="兼容旧流程的 deprecated no-op",
    )
    p_part5_accept.add_argument("--notes", required=True, metavar="TEXT",
                                help="人工接受备注，不能为空")

    sub.add_parser(
        "part6-precheck",
        help="只读检查 Part 6 entry/package gate，不生成 Part 6 artifacts",
    )

    p_part6_authorize = sub.add_parser(
        "part6-authorize",
        help="记录 Part 6 finalization 人工授权",
    )
    p_part6_authorize.add_argument("--notes", required=True, metavar="TEXT",
                                   help="人工授权备注，不能为空")

    p_part6_finalize = sub.add_parser(
        "part6-finalize",
        help="运行 Part 6 finalizer step，不自动确认人工 gate",
    )
    p_part6_finalize.add_argument(
        "--step",
        choices=[
            "precheck",
            "finalize",
            "audit-claim",
            "audit-citation",
            "package-draft",
            "decide",
            "package-final",
            "all",
        ],
        default="all",
        help="Part 6 finalizer step（默认 all）",
    )
    p_part6_finalize.add_argument("--project-root", metavar="PATH",
                                  help="透传给 Part 6 finalizer 的项目根目录")

    sub.add_parser("part6-check", help="检查 Part 6 package gate")

    p_part6_confirm_final = sub.add_parser(
        "part6-confirm-final",
        help="记录 Part 6 最终人工决策，不执行 submission",
    )
    p_part6_confirm_final.add_argument("--notes", required=True, metavar="TEXT",
                                       help="最终人工决策备注，不能为空")

    args = parser.parse_args()
    {
        "init":         cmd_init,
        "status":       cmd_status,
        "start":        cmd_start,
        "validate":     cmd_validate,
        "advance":      cmd_advance,
        "confirm-gate": cmd_confirm_gate,
        "doctor":       cmd_doctor,
        "audit":        cmd_audit,
        "part1-intake": cmd_part1_intake,
        "part1-export-table": cmd_part1_export_table,
        "part1-archive-web": cmd_part1_archive_web,
        "part2-generate": cmd_part2_generate,
        "part2-health": cmd_part2_health,
        "part3-seed-map": cmd_part3_seed_map,
        "part3-generate": cmd_part3_generate,
        "part3-compare":  cmd_part3_compare,
        "part3-refine":   cmd_part3_refine,
        "part3-review":   cmd_part3_review,
        "part3-select":   cmd_part3_select,
        "part4-generate": cmd_part4_generate,
        "part4-check":    cmd_part4_check,
        "part4-confirm":  cmd_part4_confirm,
        "part5-authorize": cmd_part5_authorize,
        "part5-prep": cmd_part5_prep,
        "part5-confirm-prep": cmd_part5_confirm_prep,
        "part5-draft": cmd_part5_draft,
        "part5-review": cmd_part5_review,
        "part5-confirm-review": cmd_part5_confirm_review,
        "part5-revise": cmd_part5_revise,
        "part5-check": cmd_part5_check,
        "part5-accept": cmd_part5_accept,
        "part6-precheck": cmd_part6_precheck,
        "part6-authorize": cmd_part6_authorize,
        "part6-finalize": cmd_part6_finalize,
        "part6-check": cmd_part6_check,
        "part6-confirm-final": cmd_part6_confirm_final,
    }[args.command](args)


if __name__ == "__main__":
    main()

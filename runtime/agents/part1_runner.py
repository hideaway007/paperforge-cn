#!/usr/bin/env python3
"""
runtime/agents/part1_runner.py

Part 1 流程串联脚本 — 按顺序执行以下步骤：

  Step 0: 前置检查（intake_confirmed gate 已过）
  Step 1: search_planner       → outputs/part1/search_plan.json
  Step 2: retrieval_router     → outputs/part1/cnki_task.txt
  Step 3: cnki_cdp_downloader → outputs/part1/download_manifest.json
  Step 4: relevance_scorer     → outputs/part1/relevance_scores.json
  Step 5: authenticity_verifier → outputs/part1/authenticity_report.json
  Step 6: library_registrar    → raw-library/metadata.json
  Step 7: gate 校验            → 标记 part1 complete

用法：
  python3 runtime/agents/part1_runner.py             # 从第一个未完成步骤续跑
  python3 runtime/agents/part1_runner.py --step 1    # 只执行指定步骤
  python3 runtime/agents/part1_runner.py --step 3 --manual-download # Step 3 只提示人工下载
  python3 runtime/agents/part1_runner.py --from-step 2  # 从指定步骤开始往后跑
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
AGENTS_DIR = Path(__file__).parent

# ── 步骤定义 ───────────────────────────────────────────────────────────────────

STEPS = {
    0: {
        "name":        "前置检查",
        "description": "确认 intake_confirmed gate 已完成",
        "output":      None,   # 不产生文件，检查 state.json
    },
    1: {
        "name":        "search_planner",
        "description": "生成检索计划",
        "output":      "outputs/part1/search_plan.json",
    },
    2: {
        "name":        "retrieval_router",
        "description": "生成 CNKI 下载任务文件",
        "output":      "outputs/part1/cnki_task.txt",
    },
    3: {
        "name":        "cnki_cdp_downloader",
        "description": "执行 CNKI 下载并生成 download_manifest.json",
        "output":      "outputs/part1/download_manifest.json",
    },
    4: {
        "name":        "relevance_scorer",
        "description": "评分相关性，筛选有效文献",
        "output":      "outputs/part1/relevance_scores.json",
    },
    5: {
        "name":        "authenticity_verifier",
        "description": "真实性校验，产出校验报告",
        "output":      "outputs/part1/authenticity_report.json",
    },
    6: {
        "name":        "library_registrar",
        "description": "注册通过校验的来源到 raw-library",
        "output":      "raw-library/metadata.json",
    },
    7: {
        "name":        "gate 校验",
        "description": "验证 canonical artifacts，标记 part1 完成",
        "output":      None,   # 不产生文件，修改 state.json
    },
}


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def print_step_header(step_num: int) -> None:
    info = STEPS[step_num]
    print(f"\n{'━' * 60}")
    print(f"Step {step_num}: {info['name']}  —  {info['description']}")
    print(f"{'━' * 60}")


def print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def print_err(msg: str) -> None:
    print(f"  [ERR] {msg}", file=sys.stderr)


def print_warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def output_exists(step_num: int) -> bool:
    """判断某步骤的输出文件是否已存在（Step 0 / 7 另行判断）"""
    rel = STEPS[step_num].get("output")
    if rel is None:
        return False
    return (PROJECT_ROOT / rel).exists()


def load_state() -> dict:
    state_path = PROJECT_ROOT / "runtime" / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(
            f"state.json 不存在: {state_path}\n请先运行 `python cli.py init` 初始化项目。"
        )
    with open(state_path, encoding="utf-8") as f:
        return json.load(f)


def run_script(script_name: str, *args: str) -> bool:
    """运行 agents 目录下的 Python 脚本，返回是否成功（exit code 0）。"""
    cmd = [sys.executable, str(AGENTS_DIR / script_name), *args]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def run_node_script(script_name: str, *args: str, env: dict[str, str] | None = None) -> bool:
    """运行 agents 目录下的 Node 脚本，返回是否成功（exit code 0）。"""
    cmd = ["node", str(AGENTS_DIR / script_name), *args]
    next_env = os.environ.copy()
    if env:
        next_env.update(env)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=next_env)
    return result.returncode == 0


def load_local_agent_module(script_name: str, module_name: str):
    import importlib.util

    script_path = AGENTS_DIR / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_part1_intake_request() -> dict:
    module = load_local_agent_module("part1_intake.py", "part1_intake")
    return module.ensure_intake_request(project_root=PROJECT_ROOT)


def validate_part1_intake_file() -> list[str]:
    module = load_local_agent_module("part1_intake.py", "part1_intake")
    return module.validate_intake_file(project_root=PROJECT_ROOT)


def export_part1_downloaded_papers_table() -> bool:
    try:
        module = load_local_agent_module(
            "part1_library_table_exporter.py",
            "part1_library_table_exporter",
        )
        result = module.export_downloaded_papers_table(project_root=PROJECT_ROOT)
    except Exception as e:
        print_err(f"Part 1 论文清单导出失败: {e}")
        return False

    print_ok(f"论文清单 CSV: {result['output_csv'].relative_to(PROJECT_ROOT)}")
    print_ok(f"论文清单 Markdown: {result['output_md'].relative_to(PROJECT_ROOT)}")
    return True


def validate_part1_completion_gate() -> tuple[bool, list[str]]:
    module = load_local_agent_module("../pipeline.py", "pipeline_for_part1_runner")
    module.PROJECT_ROOT = PROJECT_ROOT
    module.STATE_FILE = PROJECT_ROOT / "runtime" / "state.json"
    module.PROCESS_MEMORY_DIR = PROJECT_ROOT / "process-memory"
    return module.validate_gate("part1")


def intake_confirmed() -> bool:
    try:
        state = load_state()
    except Exception:
        return False
    return "intake_confirmed" in state["stages"]["part1"].get("human_gates_completed", [])


def preflight_for_step(step_num: int) -> bool:
    """Block executable Part 1 steps until the human intake gate exists."""
    if step_num == 0:
        return True
    if intake_confirmed():
        intake_issues = validate_part1_intake_file()
        if not intake_issues:
            return True
        ensure_part1_intake_request()
        print_err(
            "intake_confirmed gate 已记录，但 `outputs/part1/intake.json` 不可用于执行 Part 1：\n"
            + "\n".join(f"  - {issue}" for issue in intake_issues)
        )
        return False
    ensure_part1_intake_request()
    print_err(
        "intake_confirmed gate 尚未完成，不能执行 Part 1 检索计划、下载或后处理步骤。\n"
        "  已生成 `outputs/part1/intake_request.md` 和 `outputs/part1/intake_template.json`。\n"
        "  请先填写 `outputs/part1/intake.json`，再运行 "
        "`python cli.py confirm-gate intake_confirmed --notes \"...\"`。"
    )
    return False


def first_pending_step() -> int:
    """返回第一个尚未完成的步骤编号（Step 0 从 state 判断，其余从文件判断）。"""
    # Step 0: intake_confirmed
    try:
        state = load_state()
        completed_gates = state["stages"]["part1"].get("human_gates_completed", [])
        if "intake_confirmed" not in completed_gates:
            return 0
    except Exception:
        return 0

    # Step 7: gate_passed
    if state["stages"]["part1"].get("gate_passed", False):
        intake_issues = validate_part1_intake_file()
        if intake_issues:
            return 0
        passed, _issues = validate_part1_completion_gate()
        if passed:
            return 8  # 全部完成，超出范围
        return 7

    # Steps 1–6: 检查输出文件
    for step_num in range(1, 7):
        if not output_exists(step_num):
            return step_num

    # Steps 1–6 都有输出文件，但 gate 未过 → 跑 Step 7
    return 7


# ── 各步骤执行逻辑 ────────────────────────────────────────────────────────────

def run_step0() -> bool:
    """Step 0: 前置检查"""
    print_step_header(0)
    try:
        state = load_state()
    except FileNotFoundError as e:
        print_err(str(e))
        return False

    completed = state["stages"]["part1"].get("human_gates_completed", [])
    if "intake_confirmed" not in completed:
        info = ensure_part1_intake_request()
        print_err(
            "intake_confirmed gate 尚未完成。\n"
            f"  intake 表单说明: {info['request_path'].relative_to(PROJECT_ROOT)}\n"
            f"  intake JSON 模板: {info['template_path'].relative_to(PROJECT_ROOT)}\n"
            "  请先填写 `outputs/part1/intake.json`，再运行 "
            "`python cli.py confirm-gate intake_confirmed --notes \"主题与 intake 参数已确认\"`。"
        )
        return False

    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    intake_issues = validate_part1_intake_file()
    if intake_issues:
        info = ensure_part1_intake_request()
        print_err(
            f"intake.json 不可用: {intake_path}\n"
            + "\n".join(f"  - {issue}" for issue in intake_issues)
            + "\n"
            f"  已生成 intake 表单说明: {info['request_path'].relative_to(PROJECT_ROOT)}\n"
            f"  已生成 intake JSON 模板: {info['template_path'].relative_to(PROJECT_ROOT)}"
        )
        return False

    print_ok("intake_confirmed gate 已通过")
    print_ok(f"intake.json 存在: {intake_path.relative_to(PROJECT_ROOT)}")
    return True


def run_step1() -> bool:
    """Step 1: search_planner"""
    print_step_header(1)
    ok = run_script("search_planner.py")
    if ok:
        out = PROJECT_ROOT / "outputs" / "part1" / "search_plan.json"
        print_ok(f"输出: {out.relative_to(PROJECT_ROOT)}")
    else:
        print_err("search_planner.py 执行失败")
    return ok


def run_step2() -> bool:
    """Step 2: retrieval_router"""
    print_step_header(2)
    ok = run_script(
        "retrieval_router.py",
        "--write-task", "outputs/part1/cnki_task.txt"
    )
    if ok:
        task_path = PROJECT_ROOT / "outputs" / "part1" / "cnki_task.txt"
        supplementary_path = PROJECT_ROOT / "outputs" / "part1" / "supplementary_sources_task.md"
        print_ok(f"CNKI 任务文件: {task_path.relative_to(PROJECT_ROOT)}")
        if supplementary_path.exists():
            print_ok(f"非 CNKI/英文期刊任务文件: {supplementary_path.relative_to(PROJECT_ROOT)}")
        print()
        print("  >>> 下一步：Step 3 将自动启动 CNKI CDP 下载器：")
        print("      node runtime/agents/cnki_cdp_downloader.mjs")
        print()
        print("  下载器应写出 outputs/part1/download_manifest.json；补充来源按 supplementary_sources_task.md 导入 provenance。")
    else:
        print_err("retrieval_router.py 执行失败")
    return ok


def validate_download_manifest(manifest: dict) -> list[str]:
    """Validate that a manifest represents a real, usable CNKI download run."""
    issues: list[str] = []
    if manifest.get("task_type") != "cnki_search_download":
        issues.append("task_type 不是 cnki_search_download")
    if manifest.get("dry_run") is True:
        issues.append("download_manifest.json 是 dry_run 产物，不能推进")

    run_status = manifest.get("run_status")
    if run_status in ("fatal", "failed"):
        fatal = manifest.get("fatal_error", "unknown fatal error")
        issues.append(f"CNKI 下载器失败: {fatal}")
    elif run_status not in (None, "success", "completed", "partial"):
        issues.append(f"未知 run_status: {run_status}")

    if int(manifest.get("total_downloaded") or 0) <= 0:
        issues.append("total_downloaded 必须大于 0")
    if not isinstance(manifest.get("failed_downloads", []), list):
        issues.append("failed_downloads 必须是数组")
    return issues


def load_download_manifest(manifest_path: Path) -> tuple[dict | None, list[str]]:
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError:
        return None, [f"download_manifest.json 不存在: {manifest_path}"]
    except json.JSONDecodeError as e:
        return None, [f"download_manifest.json 无法解析: {e}"]
    return manifest, validate_download_manifest(manifest)


def run_step3(
    manual_download: bool = False,
    skip_wait: bool = False,
    cnki_max_downloads: int | None = None,
) -> bool:
    """Step 3: 执行或校验 CNKI 下载 manifest"""
    print_step_header(3)
    manifest_path = PROJECT_ROOT / "outputs" / "part1" / "download_manifest.json"

    if manifest_path.exists():
        manifest, issues = load_download_manifest(manifest_path)
        if issues:
            print_err("download_manifest.json 不可用于推进 Part 1：")
            for issue in issues:
                print_err(f"  - {issue}")
            return False
        total_dl = manifest.get("total_downloaded", "?")
        total_found = manifest.get("total_found", "?")
        failed = len(manifest.get("failed_downloads", []))
        print_ok(f"download_manifest.json 已存在: {manifest_path.relative_to(PROJECT_ROOT)}")
        print_ok(f"检索到: {total_found} 篇 | 下载成功: {total_dl} 篇 | 失败: {failed} 篇")
        return export_part1_downloaded_papers_table()

    if skip_wait:
        print_warn("--skip-cnki-wait 已设置，但缺少有效 download_manifest.json；不能推进。")
        return False

    task_path = PROJECT_ROOT / "outputs" / "part1" / "cnki_task.txt"
    if not task_path.exists():
        print_err(f"CNKI 任务文件不存在: {task_path.relative_to(PROJECT_ROOT)}")
        print_err("请先运行 Step 2 生成 cnki_task.txt。")
        return False

    if manual_download:
        print()
        print("  [人工下载模式] download_manifest.json 尚不存在。")
        print(f"  任务文件: {task_path}")
        print("  完成下载后重新运行：python3 runtime/agents/part1_runner.py")
        return False

    print()
    print("  启动 CNKI CDP 下载器...")
    env = {}
    if cnki_max_downloads is not None:
        env["PART1_CNKI_MAX_DOWNLOADS"] = str(cnki_max_downloads)
        print(f"  下载上限: {cnki_max_downloads} 篇")
    ok = run_node_script("cnki_cdp_downloader.mjs", env=env)
    if not ok:
        print_err("cnki_cdp_downloader.mjs 执行失败")
        if manifest_path.exists():
            manifest, issues = load_download_manifest(manifest_path)
            if issues:
                for issue in issues:
                    print_err(f"  - {issue}")
        return False

    manifest, issues = load_download_manifest(manifest_path)
    if issues:
        print_err("CNKI 下载器运行结束，但 manifest 不可用于推进：")
        for issue in issues:
            print_err(f"  - {issue}")
        return False
    print_ok(f"输出: {manifest_path.relative_to(PROJECT_ROOT)}")
    return export_part1_downloaded_papers_table()


def run_step4() -> bool:
    """Step 4: relevance_scorer"""
    print_step_header(4)
    scorer_path = AGENTS_DIR / "relevance_scorer.py"
    if not scorer_path.exists():
        print_warn(
            "relevance_scorer.py 尚不存在。\n"
            "  请先创建 runtime/agents/relevance_scorer.py，\n"
            "  该脚本应读取 download_manifest.json 并写出 outputs/part1/relevance_scores.json。"
        )
        return False

    ok = run_script("relevance_scorer.py")
    if ok:
        out = PROJECT_ROOT / "outputs" / "part1" / "relevance_scores.json"
        print_ok(f"输出: {out.relative_to(PROJECT_ROOT)}")
    else:
        print_err("relevance_scorer.py 执行失败")
    return ok


def run_step5() -> bool:
    """Step 5: authenticity_verifier"""
    print_step_header(5)
    ok = run_script("authenticity_verifier.py")
    if ok:
        out = PROJECT_ROOT / "outputs" / "part1" / "authenticity_report.json"
        print_ok(f"输出: {out.relative_to(PROJECT_ROOT)}")
    else:
        print_err("authenticity_verifier.py 执行失败")
    return ok


def run_step6() -> bool:
    """Step 6: library_registrar"""
    print_step_header(6)
    ok = run_script("library_registrar.py")
    if ok:
        out = PROJECT_ROOT / "raw-library" / "metadata.json"
        print_ok(f"输出: {out.relative_to(PROJECT_ROOT)}")
        return export_part1_downloaded_papers_table()
    else:
        print_err("library_registrar.py 执行失败")
    return ok


def run_step7() -> bool:
    """Step 7: gate 校验，标记 part1 complete"""
    print_step_header(7)

    # 动态导入 pipeline，避免顶层依赖
    import importlib.util
    pipeline_path = PROJECT_ROOT / "runtime" / "pipeline.py"
    spec = importlib.util.spec_from_file_location("pipeline", pipeline_path)
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)

    if not export_part1_downloaded_papers_table():
        return False

    passed, issues = pipeline.validate_gate("part1")
    if not passed:
        print_err("Gate 校验未通过，part1 无法标记为 complete：")
        for issue in issues:
            print_err(f"  - {issue}")
        return False

    ok, issues = pipeline.advance_stage("part1")
    if ok:
        print_ok("part1 gate 通过，已标记为 completed")
        print_ok("state.json 已更新")
    else:
        print_err("advance_stage 失败：")
        for issue in issues:
            print_err(f"  - {issue}")
    return ok


# ── Runner ─────────────────────────────────────────────────────────────────────

STEP_RUNNERS = {
    0: run_step0,
    1: run_step1,
    2: run_step2,
    3: run_step3,
    4: run_step4,
    5: run_step5,
    6: run_step6,
    7: run_step7,
}


def run_single_step(
    step_num: int,
    skip_cnki_wait: bool = False,
    manual_download: bool = False,
    cnki_max_downloads: int | None = None,
) -> bool:
    if not preflight_for_step(step_num):
        return False
    if step_num == 3:
        return run_step3(
            manual_download=manual_download,
            skip_wait=skip_cnki_wait,
            cnki_max_downloads=cnki_max_downloads,
        )
    runner = STEP_RUNNERS.get(step_num)
    if runner is None:
        print_err(f"未知步骤: {step_num}（有效范围 0–7）")
        return False
    return runner()


def run_from_step(
    start: int,
    skip_cnki_wait: bool = False,
    manual_download: bool = False,
    cnki_max_downloads: int | None = None,
) -> None:
    """从 start 步骤开始顺序执行到 Step 7。"""
    for step_num in range(start, 8):
        ok = run_single_step(
            step_num,
            skip_cnki_wait=skip_cnki_wait,
            manual_download=manual_download,
            cnki_max_downloads=cnki_max_downloads,
        )
        if not ok:
            print(f"\n流程在 Step {step_num}（{STEPS[step_num]['name']}）停止。")
            print("修复问题后重新运行本脚本即可从断点续跑。")
            sys.exit(1)

    print(f"\n{'━' * 60}")
    print("Part 1 全部步骤完成。")
    print(f"{'━' * 60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Part 1 流程串联脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 part1_runner.py                    # 续跑（从第一个未完成步骤）
  python3 part1_runner.py --step 1           # 只运行 Step 1
  python3 part1_runner.py --from-step 4      # 从 Step 4 开始往后跑
  python3 part1_runner.py --cnki-max-downloads 28 # 限制本次 CNKI 下载数量
  python3 part1_runner.py --step 3 --manual-download # 只提示人工下载，不自动启动下载器
  python3 part1_runner.py --list             # 列出所有步骤及当前状态
""",
    )
    parser.add_argument("--step", type=int, metavar="N",
                        help="只执行指定步骤 (0–7)")
    parser.add_argument("--from-step", type=int, metavar="N",
                        help="从指定步骤开始往后顺序执行")
    parser.add_argument("--skip-cnki-wait", action="store_true",
                        help="兼容旧参数；缺少有效 manifest 时不会继续推进")
    parser.add_argument("--manual-download", action="store_true",
                        help="Step 3 不自动启动下载器，只提示人工下载任务")
    parser.add_argument("--cnki-max-downloads", type=int, metavar="N",
                        help="限制 Step 3 本次 CNKI 成功下载数量")
    parser.add_argument("--list", action="store_true",
                        help="列出所有步骤及当前状态")
    args = parser.parse_args()

    if args.list:
        _print_status()
        return

    if args.step is not None and args.from_step is not None:
        print_err("--step 和 --from-step 不能同时使用")
        sys.exit(1)

    if args.step is not None:
        if args.step < 0 or args.step > 7:
            print_err("步骤编号必须在 0–7 之间")
            sys.exit(1)
        ok = run_single_step(
            args.step,
            skip_cnki_wait=args.skip_cnki_wait,
            manual_download=args.manual_download,
            cnki_max_downloads=args.cnki_max_downloads,
        )
        sys.exit(0 if ok else 1)

    if args.from_step is not None:
        if args.from_step < 0 or args.from_step > 7:
            print_err("步骤编号必须在 0–7 之间")
            sys.exit(1)
        run_from_step(
            args.from_step,
            skip_cnki_wait=args.skip_cnki_wait,
            manual_download=args.manual_download,
            cnki_max_downloads=args.cnki_max_downloads,
        )
        return

    # 默认：续跑模式
    pending = first_pending_step()
    if pending >= 8:
        print("Part 1 已全部完成（gate_passed = true）。无需重跑。")
        return

    print(f"续跑模式：从 Step {pending}（{STEPS[pending]['name']}）开始")
    run_from_step(
        pending,
        skip_cnki_wait=args.skip_cnki_wait,
        manual_download=args.manual_download,
        cnki_max_downloads=args.cnki_max_downloads,
    )


def _print_status() -> None:
    """打印各步骤当前状态。"""
    print(f"\n{'━' * 60}")
    print("Part 1 步骤状态")
    print(f"{'━' * 60}")

    # Step 0: gate 状态
    try:
        state = load_state()
        gates = state["stages"]["part1"].get("human_gates_completed", [])
        s0 = "完成" if "intake_confirmed" in gates else "待完成"
        gate_passed = state["stages"]["part1"].get("gate_passed", False)
    except Exception:
        s0 = "无法读取 state.json"
        gate_passed = False

    print(f"  Step 0  前置检查              {s0}")

    for n in range(1, 7):
        exists = output_exists(n)
        out = STEPS[n].get("output", "")
        status = "完成" if exists else "待完成"
        print(f"  Step {n}  {STEPS[n]['name']:<24} {status}  ({out})")

    s7 = "完成" if gate_passed else "待完成"
    print(f"  Step 7  gate 校验              {s7}")
    print()

    pending = first_pending_step()
    if pending >= 8:
        print("  全部完成。")
    else:
        print(f"  下一步: Step {pending} ({STEPS[pending]['name']})")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Part 1 intake request generator.

This script creates a user-facing intake request before any Part 1 retrieval
work starts. It does not confirm the human gate and does not overwrite a filled
outputs/part1/intake.json.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

INTAKE_TEMPLATE_NAME = "intake_template.json"
INTAKE_REQUEST_NAME = "intake_request.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_intake_template() -> dict[str, Any]:
    today = datetime.now(timezone.utc)
    return {
        "intake_id": f"intake_{today.strftime('%Y%m%d')}_topic",
        "research_topic": "",
        "research_question": "",
        "core_research_questions": [],
        "discipline_fields": [],
        "keywords_required": [],
        "keywords_suggested": [],
        "time_range": {
            "start_year": 2015,
            "end_year": today.year,
        },
        "source_preference": {
            "databases": ["cnki", "wanfang", "vip"],
            "document_types": ["期刊论文", "硕士论文", "博士论文"],
            "priority": "CNKI first",
        },
        "scope_notes": "",
        "exclusion_rules": [
            "与本次研究对象、研究问题或应用场景无直接关系的文献不得进入 tier_A",
            "仅命中单一泛化背景词且缺少当前 intake 双锚点的材料只能作为弱相关或补充材料",
        ],
        "confirmation_notes": "",
    }


def _has_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and any(_has_non_empty_text(item) for item in value)


def intake_validation_issues(intake: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not _has_non_empty_text(intake.get("intake_id")):
        issues.append("intake_id 不能为空")
    if not _has_non_empty_text(intake.get("research_topic")):
        issues.append("research_topic 不能为空")
    if not _has_non_empty_text(intake.get("research_question")):
        issues.append("research_question 不能为空")
    if not _has_non_empty_list(intake.get("keywords_required")):
        issues.append("keywords_required 必须至少包含一个检索锚点")
    if not isinstance(intake.get("time_range"), dict):
        issues.append("time_range 必须是 object")
    if not isinstance(intake.get("source_preference"), dict):
        issues.append("source_preference 必须是 object")
    if not _has_non_empty_text(intake.get("scope_notes")):
        issues.append("scope_notes 不能为空")
    return issues


def validate_intake_file(project_root: Path = PROJECT_ROOT) -> list[str]:
    intake_path = project_root / "outputs" / "part1" / "intake.json"
    if not intake_path.exists():
        return [f"outputs/part1/intake.json 不存在: {intake_path}"]
    try:
        with open(intake_path, encoding="utf-8") as f:
            intake = json.load(f)
    except json.JSONDecodeError as e:
        return [f"outputs/part1/intake.json 无法解析: {e}"]
    if not isinstance(intake, dict):
        return ["outputs/part1/intake.json 必须是 JSON object"]
    return intake_validation_issues(intake)


def render_intake_request(template_path: Path, intake_path: Path, created_at: str) -> str:
    return f"""# Part 1 Intake Request

created_at: {created_at}

Part 1 的第一步是确认研究主题与结构化 intake。检索、下载、相关性评分和资料库注册都必须在 `intake_confirmed` 之后执行。

## 你需要填写

请以 `{template_path.name}` 为参考，填写或替换：

`{intake_path.as_posix()}`

必填信息：

| 字段 | 用途 |
|---|---|
| `intake_id` | 本次 Part 1 任务的唯一 ID |
| `research_topic` | 论文研究主题 |
| `research_question` | 本次检索要服务的核心问题 |
| `keywords_required` | 必须优先覆盖的检索锚点 |
| `keywords_suggested` | 代表案例、方法词、补充词 |
| `time_range` | 文献年份范围 |
| `source_preference.document_types` | 期刊、硕博论文等类型偏好 |
| `scope_notes` | 边界说明：纳入什么，不纳入什么 |

## 下一步

1. 填写 `outputs/part1/intake.json`
2. 确认 intake：`python3 cli.py confirm-gate intake_confirmed --notes "主题与 intake 参数已确认"`

确认后系统会创建或复用隔离 workspace，并自动在该 workspace 中运行 Part 1 runner。
如果只想创建 workspace 不立即运行，可加 `--no-auto-run-part1`。

注意：不要直接确认空白 intake。确认前请至少填写 `research_question` 和 `scope_notes`。
"""


def ensure_intake_request(project_root: Path = PROJECT_ROOT, force: bool = False) -> dict[str, Any]:
    part1_dir = project_root / "outputs" / "part1"
    part1_dir.mkdir(parents=True, exist_ok=True)

    intake_path = part1_dir / "intake.json"
    template_path = part1_dir / INTAKE_TEMPLATE_NAME
    request_path = part1_dir / INTAKE_REQUEST_NAME
    created_at = now_iso()

    if force or not template_path.exists():
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(default_intake_template(), f, ensure_ascii=False, indent=2)

    request_text = render_intake_request(
        template_path=template_path.relative_to(project_root),
        intake_path=intake_path.relative_to(project_root),
        created_at=created_at,
    )
    request_path.write_text(request_text, encoding="utf-8")

    return {
        "created_at": created_at,
        "intake_exists": intake_path.exists(),
        "intake_path": intake_path,
        "template_path": template_path,
        "request_path": request_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Part 1 intake request")
    parser.add_argument("--project-root", metavar="PATH", help="项目根目录")
    parser.add_argument("--force", action="store_true", help="覆盖 intake_template.json")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT
    result = ensure_intake_request(project_root=project_root, force=args.force)

    print("Part 1 intake request 已生成")
    print(f"  表单说明: {result['request_path'].relative_to(project_root)}")
    print(f"  JSON 模板: {result['template_path'].relative_to(project_root)}")
    if result["intake_exists"]:
        print(f"  已存在 intake: {result['intake_path'].relative_to(project_root)}")
        print('  下一步: python3 cli.py confirm-gate intake_confirmed --notes "主题与 intake 参数已确认"')
    else:
        print(f"  请填写: {result['intake_path'].relative_to(project_root)}")


if __name__ == "__main__":
    main()

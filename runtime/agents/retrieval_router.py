#!/usr/bin/env python3
"""
runtime/agents/retrieval_router.py

读取 search_plan.json，将 CNKI 任务格式化为 cnki_cdp_downloader.mjs 可执行的下载任务。
万方/维普目前输出为待处理任务列表（需人工或后续 agent 处理）。

用法：
  python3 runtime/agents/retrieval_router.py             # 打印 Codex 任务消息
  python3 runtime/agents/retrieval_router.py --db cnki   # 只处理 CNKI
  python3 runtime/agents/retrieval_router.py --write-task outputs/part1/cnki_task.txt
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def load_search_plan() -> dict:
    plan_path = PROJECT_ROOT / "outputs" / "part1" / "search_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"search_plan.json 不存在: {plan_path}")
    with open(plan_path) as f:
        return json.load(f)


def format_cnki_task(plan: dict) -> str:
    """将 CNKI 查询组格式化为 CDP 下载任务消息"""
    cnki_db = next((db for db in plan["databases"] if db["db_id"] == "cnki"), None)
    if not cnki_db:
        return "错误：search_plan.json 中没有 CNKI 数据库配置"

    query_lines = []
    for group in cnki_db["query_groups"]:
        for q in group["queries"]:
            terms_str = " OR ".join(f'"{t}"' for t in q["terms"])
            filters = q.get("filters", {})
            query_lines.append(
                f"  - query_id: {q['query_id']}\n"
                f"    terms: {terms_str}\n"
                f"    field: {q['field']}\n"
                f"    year: {filters.get('year_from', '?')}-{filters.get('year_to', '?')}\n"
                f"    doc_type: {', '.join(filters.get('doc_type', []))}\n"
                f"    expected: {q.get('expected_results', '?')} 篇\n"
                f"    purpose: {group['purpose']}"
            )

    task = f"""[CNKI_DOWNLOAD_TASK]
生成时间: {datetime.now(timezone.utc).isoformat()}
项目目录: {PROJECT_ROOT}

任务: 使用 CDP 在 CNKI 执行以下检索并下载 PDF

━━ 检索查询 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(query_lines)}

━━ 下载规范 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PDF 目录:       {PROJECT_ROOT}/raw-library/papers/
Provenance 目录: {PROJECT_ROOT}/raw-library/provenance/
Manifest 输出:   {PROJECT_ROOT}/outputs/part1/download_manifest.json
文件命名:        cnki_{{year}}_{{seq:03d}}.pdf  (例: cnki_2023_001.pdf)

━━ Provenance 格式（每篇一个 JSON 文件）━━━━━━━━━
{{
  "source_id": "cnki_{{year}}_{{seq:03d}}",
  "query_id": "<对应 query_id>",
  "db": "cnki",
  "title": "<论文标题>",
  "authors": ["<作者>"],
  "journal": "<期刊名>",
  "year": <年份>,
  "doi_or_cnki_id": "<CNKI 文章编号>",
  "url": "<详情页 URL>",
  "abstract": "<摘要>",
  "keywords": ["<关键词>"],
  "download_status": "success",
  "downloaded_at": "<ISO 时间>"
}}

━━ Manifest 格式 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "manifest_id": "download_manifest_{{timestamp}}",
  "created_at": "<ISO 时间>",
  "task_type": "cnki_search_download",
  "queries_executed": [<query_id 列表>],
  "total_found": <检索到总数>,
  "total_downloaded": <成功下载数>,
  "failed_downloads": [{{"source_id": "...", "reason": "..."}}],
  "output_dir": "raw-library/papers/",
  "provenance_dir": "raw-library/provenance/"
}}

━━ 注意 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 在 CNKI 详情页用真实点击下载，不要直接 URL 复制（会报「来源应用不正确」）
- 未登录时先访问 https://www.cnki.net，使用你有权使用的机构账号或合规访问账号登录
- 每次下载后等待 2-3 秒
- 失败文献记录到 manifest failed_downloads，不要中断整体任务
- 最大下载数: {cnki_db.get('max_results_total', 300)} 篇
"""
    return task


def format_supplementary_sources_task(plan: dict) -> str:
    """Format non-CNKI retrieval instructions, including English journal and Markdown archive handoff."""
    quota = plan.get("source_quota_policy", {})
    non_cnki = [db for db in plan["databases"] if db["db_id"] != "cnki"]
    sections = []
    for db in non_cnki:
        query_lines = []
        for group in db.get("query_groups", []):
            for q in group.get("queries", []):
                terms = " OR ".join(f'"{term}"' for term in q.get("terms", []))
                filters = q.get("filters", {})
                query_lines.append(
                    f"- query_id: {q.get('query_id')}\n"
                    f"  db: {db['db_id']}\n"
                    f"  target_results: {db.get('target_results', db.get('max_results_total'))}\n"
                    f"  terms: {terms}\n"
                    f"  field: {q.get('field')}\n"
                    f"  year: {filters.get('year_from', '?')}-{filters.get('year_to', '?')}\n"
                    f"  document_type: {filters.get('document_type', filters.get('doc_type', 'journal/article'))}\n"
                    f"  purpose: {group.get('purpose')}"
                )
        sections.append(f"## {db['db_name']} ({db['db_id']})\n\n" + "\n".join(query_lines))

    return f"""# Part 1 Supplementary Retrieval Task

生成时间: {datetime.now(timezone.utc).isoformat()}
项目目录: {PROJECT_ROOT}

## Final Accepted Source Quota

- 总量: {quota.get('target_total', 40)} 篇
- CNKI: {quota.get('cnki_min_count', 24)}-{quota.get('cnki_max_count', 28)} 篇
- 英文期刊: 至少 {quota.get('english_journal_min_count', 5)} 篇
- 其余: 万方、维普或其他用户明确允许且可验真的补充来源

## Non-CNKI Queries

{chr(10).join(sections)}

## Markdown Web Archive Handoff

当来源只有网页详情页或开放网页全文时，优先使用本地 Google Chrome 的 Obsidian/Web Clipper 插件生成 Markdown，然后用仓库脚本导入：

```bash
python3 runtime/agents/web_markdown_archiver.py \\
  --source-id crossref_2026_001 \\
  --url "https://doi.org/..." \\
  --from-obsidian "/path/to/obsidian/export/page.md" \\
  --db crossref \\
  --query-id crossref_q1_1 \\
  --title "Paper title" \\
  --authors "Author A; Author B" \\
  --journal "Journal name" \\
  --year 2026 \\
  --doi-or-source-id "10.xxxx/example" \\
  --abstract "Abstract text" \\
  --keywords "architecture; design education"
```

如果想让脚本打开 Chrome 并等待插件输出：

```bash
python3 runtime/agents/web_markdown_archiver.py \\
  --source-id crossref_2026_001 \\
  --url "https://doi.org/..." \\
  --watch-obsidian-dir "/path/to/obsidian/export" \\
  --open-in-chrome \\
  --db crossref \\
  --query-id crossref_q1_1
```

注意：Chrome 插件没有稳定公开 CLI/API，脚本不会伪造插件行为；插件生成 Markdown 后，仓库脚本负责复制到 `raw-library/web-archives/` 并写 `raw-library/provenance/`。
"""


def main():
    parser = argparse.ArgumentParser(description="Route retrieval tasks to appropriate executors")
    parser.add_argument("--db", choices=["cnki", "wanfang", "vip", "all"], default="all")
    parser.add_argument("--write-task", help="将任务消息写入指定文件路径")
    parser.add_argument(
        "--write-supplementary-task",
        default="outputs/part1/supplementary_sources_task.md",
        help="将非 CNKI 检索与网页 Markdown 归档任务写入指定文件路径",
    )
    args = parser.parse_args()

    try:
        plan = load_search_plan()
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    if args.db in ("cnki", "all"):
        task_msg = format_cnki_task(plan)
        if args.write_task:
            out_path = PROJECT_ROOT / args.write_task if not Path(args.write_task).is_absolute() else Path(args.write_task)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(task_msg)
            print(f"✓ CNKI 任务已写入: {out_path}")
            print(f"  供下载器读取: node runtime/agents/cnki_cdp_downloader.mjs")
        else:
            print(task_msg)

    if args.db == "all" and args.write_supplementary_task:
        out_path = (
            PROJECT_ROOT / args.write_supplementary_task
            if not Path(args.write_supplementary_task).is_absolute()
            else Path(args.write_supplementary_task)
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(format_supplementary_sources_task(plan), encoding="utf-8")
        print(f"✓ 非 CNKI 检索任务已写入: {out_path}")

    if args.db in ("wanfang", "vip", "all"):
        non_cnki = [db for db in plan["databases"] if db["db_id"] != "cnki"]
        if non_cnki and args.db != "cnki":
            print(f"\n{'━'*50}")
            print(f"万方/维普检索（暂需人工处理）：")
            for db in non_cnki:
                if args.db == "all" or args.db == db["db_id"]:
                    total_queries = sum(len(g["queries"]) for g in db["query_groups"])
                    print(f"  {db['db_name']}: {total_queries} 个查询，预计 {db['max_results_total']} 篇上限")


if __name__ == "__main__":
    main()

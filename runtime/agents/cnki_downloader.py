#!/usr/bin/env python3
"""
runtime/agents/cnki_downloader.py

基于 Playwright + CDP 的 CNKI 文献检索与下载器。
读取 outputs/part1/search_plan.json 中的 CNKI 查询配置，
执行高级检索、收集结果元数据、真实点击下载 PDF，
为每篇文献生成 provenance JSON，并汇总生成 download_manifest.json。

特性：
- 可见浏览器模式（默认），规避 CNKI 反爬；支持 --headless 调试
- 断点续传：跳过 raw-library/provenance/ 中已存在的 source_id
- 限速：检索 2-3s，下载 3-5s，随机抖动
- 容错：单篇失败记录到 manifest.failed_downloads，不中断
- 跨查询递增的全局序号：cnki_{year}_{seq:03d}

用法：
  python3 runtime/agents/cnki_downloader.py
  python3 runtime/agents/cnki_downloader.py --query-id cnki_q1_1
  python3 runtime/agents/cnki_downloader.py --dry-run
  python3 runtime/agents/cnki_downloader.py --headless
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

SEARCH_PLAN_PATH = PROJECT_ROOT / "outputs" / "part1" / "search_plan.json"
MANIFEST_PATH = PROJECT_ROOT / "outputs" / "part1" / "download_manifest.json"
PAPERS_DIR = PROJECT_ROOT / "raw-library" / "papers"
PROVENANCE_DIR = PROJECT_ROOT / "raw-library" / "provenance"

CNKI_HOME = "https://www.cnki.net"
CNKI_ADVANCED = "https://kns.cnki.net/kns8s/AdvSearch"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ResultRecord:
    """检索结果列表中单条条目（未下载前的元数据）。"""
    query_id: str
    title: str
    authors: list[str]
    journal: str
    year: int
    cnki_id: str
    url: str
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class DownloadOutcome:
    source_id: str
    query_id: str
    success: bool
    reason: str = ""
    record: Optional[ResultRecord] = None


# ---------------------------------------------------------------------------
# IO 辅助
# ---------------------------------------------------------------------------

def load_search_plan() -> dict:
    if not SEARCH_PLAN_PATH.exists():
        raise FileNotFoundError(f"search_plan.json 不存在: {SEARCH_PLAN_PATH}")
    with open(SEARCH_PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)


def already_downloaded_ids() -> set[str]:
    """扫描 provenance/ 目录，返回已下载的 source_id 集合（用于断点续传）。"""
    if not PROVENANCE_DIR.exists():
        return set()
    return {p.stem for p in PROVENANCE_DIR.glob("cnki_*.json")}


def existing_title_keys() -> set[str]:
    """扫描已有 provenance 中的 title + year，用于跨运行去重。"""
    keys: set[str] = set()
    if not PROVENANCE_DIR.exists():
        return keys
    for p in PROVENANCE_DIR.glob("cnki_*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            keys.add(_title_key(d.get("title", ""), d.get("year", 0)))
        except Exception:
            continue
    return keys


def _title_key(title: str, year: int | str) -> str:
    return f"{re.sub(r'\\s+', '', title or '').lower()}::{year}"


def next_seq_for_year(year: int, used: dict[int, int]) -> int:
    """对同一年份跨查询递增序号。"""
    used[year] = used.get(year, 0) + 1
    return used[year]


def init_year_counter_from_disk() -> dict[int, int]:
    """从 provenance/ 已有文件推断每年的最大 seq，作为续传起点。"""
    counter: dict[int, int] = {}
    pattern = re.compile(r"^cnki_(\d{4})_(\d{3})$")
    for p in PROVENANCE_DIR.glob("cnki_*.json"):
        m = pattern.match(p.stem)
        if not m:
            continue
        year = int(m.group(1))
        seq = int(m.group(2))
        counter[year] = max(counter.get(year, 0), seq)
    return counter


def sleep_jitter(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


# ---------------------------------------------------------------------------
# Playwright CNKI 交互
# ---------------------------------------------------------------------------

class CNKIBrowser:
    """封装 CNKI 页面操作。需要在 Python 运行时已安装 playwright 浏览器。"""

    def __init__(self, headless: bool = False, download_dir: Optional[Path] = None):
        self.headless = headless
        self.download_dir = download_dir or (PAPERS_DIR / "_tmp")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self._browser = None
        self._context = None
        self.page = None

    def __enter__(self) -> "CNKIBrowser":
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            accept_downloads=True,
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ------------------------------------------------------------------
    # 登录 / 首页
    # ------------------------------------------------------------------

    def goto_home(self) -> None:
        self.page.goto(CNKI_HOME, wait_until="domcontentloaded", timeout=60_000)
        sleep_jitter(1.5, 3.0)

    def ensure_logged_in(self) -> None:
        """非 headless 模式下，提示用户手动登录（如需要）。"""
        if self.headless:
            return
        # CNKI 大部分检索不强制登录，但下载需要。等待用户确认。
        print("[提示] 若需要下载 PDF，请在打开的浏览器中完成登录（机构账号）。", flush=True)
        print("       登录完成或确认无需登录后按回车继续...", flush=True)
        try:
            input()
        except EOFError:
            pass

    # ------------------------------------------------------------------
    # 高级检索
    # ------------------------------------------------------------------

    def run_advanced_search(
        self,
        terms: list[str],
        field: str,
        year_from: int,
        year_to: int,
        doc_types: list[str],
    ) -> None:
        """在 CNKI 高级检索页面执行一次检索。

        由于 CNKI DOM 会随版本变化，这里采用宽松的选择器策略，找不到时抛异常。
        """
        page = self.page
        page.goto(CNKI_ADVANCED, wait_until="domcontentloaded", timeout=60_000)
        sleep_jitter(2.0, 3.5)

        # 1) 选择检索字段（主题/篇名/关键词/摘要）
        try:
            # 点击第一个字段下拉
            field_dropdown = page.locator("div.sort-default").first
            if field_dropdown.count() > 0:
                field_dropdown.click()
                sleep_jitter(0.3, 0.8)
                page.get_by_text(field, exact=True).first.click()
                sleep_jitter(0.3, 0.8)
        except Exception:
            # 字段选择失败不致命，默认是「主题」
            pass

        # 2) 输入检索词：CNKI 支持在单框内用 OR 连接
        #    使用 "词1"+"词2" 或直接 OR，这里用中文高级检索语法：  词1 OR 词2
        joined = " OR ".join(terms)
        try:
            input_box = page.locator("input.input-box").first
            if input_box.count() == 0:
                input_box = page.locator("input[placeholder*='检索']").first
            input_box.click()
            input_box.fill(joined)
        except Exception as e:
            raise RuntimeError(f"找不到检索输入框: {e}")

        # 3) 年份范围
        try:
            year_from_box = page.locator("input[placeholder*='起始年']").first
            year_to_box = page.locator("input[placeholder*='结束年']").first
            if year_from_box.count() > 0:
                year_from_box.fill(str(year_from))
            if year_to_box.count() > 0:
                year_to_box.fill(str(year_to))
        except Exception:
            pass

        # 4) 文献类型：期刊论文
        #    CNKI 左侧通常有勾选框，文献默认是「学术期刊」；这里不强制点击，
        #    检索后在结果页的「来源类别」过滤里再做一次。

        # 5) 点击检索按钮
        try:
            btn = page.get_by_role("button", name=re.compile("检索|搜索"))
            btn.first.click()
        except Exception:
            page.keyboard.press("Enter")

        # 等待结果加载
        try:
            page.wait_for_selector("table.result-table-list, div.result-table-list", timeout=30_000)
        except Exception:
            # 也许无结果，也许 DOM 不同。让调用方检查
            pass

        # 过滤「学术期刊」（如果页面提供 tab）
        if doc_types and any("期刊" in t for t in doc_types):
            try:
                tab = page.get_by_text(re.compile("学术期刊|期刊"), exact=False).first
                if tab and tab.count() > 0:
                    tab.click()
                    sleep_jitter(1.5, 2.5)
            except Exception:
                pass

        sleep_jitter(2.0, 3.0)

    # ------------------------------------------------------------------
    # 结果解析
    # ------------------------------------------------------------------

    def collect_results(self, query_id: str, limit: int) -> list[ResultRecord]:
        """从当前结果页抓取列表（只抓第一页的前 limit 条；需要翻页时外部循环）。"""
        page = self.page
        records: list[ResultRecord] = []
        rows = page.locator("table.result-table-list tbody tr")
        count = rows.count()
        if count == 0:
            return records

        for i in range(min(count, limit)):
            row = rows.nth(i)
            try:
                title_link = row.locator("a.fz14").first
                title = (title_link.inner_text() or "").strip()
                href = title_link.get_attribute("href") or ""
                url = href if href.startswith("http") else f"https://kns.cnki.net{href}"

                author_cell = row.locator("td.author").first
                authors_raw = author_cell.inner_text() if author_cell.count() > 0 else ""
                authors = [a.strip() for a in re.split(r"[;,、；]", authors_raw) if a.strip()]

                journal_cell = row.locator("td.source").first
                journal = (journal_cell.inner_text() or "").strip() if journal_cell.count() > 0 else ""

                date_cell = row.locator("td.date").first
                year = 0
                if date_cell.count() > 0:
                    m = re.search(r"(\d{4})", date_cell.inner_text() or "")
                    if m:
                        year = int(m.group(1))

                # cnki_id 从 href 的 dbcode/filename 参数中提取
                cnki_id = ""
                m = re.search(r"FileName=([^&]+)", url)
                if m:
                    cnki_id = m.group(1)

                records.append(ResultRecord(
                    query_id=query_id,
                    title=title,
                    authors=authors,
                    journal=journal,
                    year=year,
                    cnki_id=cnki_id,
                    url=url,
                ))
            except Exception:
                continue
        return records

    def try_next_page(self) -> bool:
        """尝试翻到下一页结果；成功返回 True。"""
        page = self.page
        try:
            nxt = page.locator("a#PageNext, a.next").first
            if nxt.count() > 0 and nxt.is_enabled():
                nxt.click()
                page.wait_for_selector("table.result-table-list tbody tr", timeout=15_000)
                sleep_jitter(2.0, 3.0)
                return True
        except Exception:
            return False
        return False

    # ------------------------------------------------------------------
    # 详情页 + 下载
    # ------------------------------------------------------------------

    def open_detail_and_download(self, record: ResultRecord, target_pdf: Path) -> tuple[bool, str, dict]:
        """进入详情页，抓取摘要/关键词，然后触发真实点击下载 PDF。

        返回 (success, reason, extra_meta)。
        extra_meta 可能包含 abstract / keywords。
        """
        page = self.page
        extra: dict = {"abstract": "", "keywords": []}

        try:
            page.goto(record.url, wait_until="domcontentloaded", timeout=45_000)
            sleep_jitter(2.0, 3.5)
        except Exception as e:
            return False, f"打开详情页失败: {e}", extra

        # 抓摘要
        try:
            abs_node = page.locator("span#ChDivSummary, div.abstract-text").first
            if abs_node.count() > 0:
                extra["abstract"] = (abs_node.inner_text() or "").strip()
        except Exception:
            pass

        # 抓关键词
        try:
            kws = page.locator("p.keywords a, div.keywords a")
            if kws.count() > 0:
                extra["keywords"] = [
                    (kws.nth(i).inner_text() or "").strip().rstrip(";；,，")
                    for i in range(kws.count())
                    if (kws.nth(i).inner_text() or "").strip()
                ]
        except Exception:
            pass

        # 点击 PDF 下载
        pdf_link = None
        for sel in [
            "a#pdfDown",
            "a.btn-dlpdf",
            "a:has-text('PDF下载')",
            "li.btn-dlpdf a",
        ]:
            try:
                candidate = page.locator(sel).first
                if candidate.count() > 0:
                    pdf_link = candidate
                    break
            except Exception:
                continue

        if pdf_link is None:
            return False, "未找到 PDF 下载入口", extra

        try:
            with page.expect_download(timeout=60_000) as dl_info:
                pdf_link.click()
            download = dl_info.value
            # 保存到目标路径
            download.save_as(str(target_pdf))
            sleep_jitter(3.0, 5.0)
            if not target_pdf.exists() or target_pdf.stat().st_size == 0:
                return False, "下载文件为空", extra
            return True, "", extra
        except Exception as e:
            return False, f"下载失败: {e}", extra


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def write_provenance(source_id: str, query_id: str, record: ResultRecord,
                     abstract: str, keywords: list[str], status: str) -> None:
    data = {
        "source_id": source_id,
        "query_id": query_id,
        "db": "cnki",
        "title": record.title,
        "authors": record.authors,
        "journal": record.journal,
        "year": record.year,
        "doi_or_cnki_id": record.cnki_id,
        "url": record.url,
        "abstract": abstract,
        "keywords": keywords,
        "download_status": status,
        "downloaded_at": iso_now(),
    }
    out = PROVENANCE_DIR / f"{source_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_queries(
    plan: dict,
    only_query_id: Optional[str],
    dry_run: bool,
    headless: bool,
) -> dict:
    cnki_db = next((db for db in plan["databases"] if db["db_id"] == "cnki"), None)
    if not cnki_db:
        raise RuntimeError("search_plan.json 中没有 CNKI 数据库配置")

    max_total = int(cnki_db.get("max_results_total", 300))
    queries: list[dict] = []
    for group in cnki_db["query_groups"]:
        for q in group["queries"]:
            if only_query_id and q["query_id"] != only_query_id:
                continue
            queries.append(q)

    if not queries:
        raise RuntimeError("没有匹配的 query 可执行")

    ensure_dirs()
    done_ids = already_downloaded_ids()
    seen_titles = existing_title_keys()
    year_counter = init_year_counter_from_disk()

    queries_executed: list[str] = []
    total_found = 0
    total_downloaded = 0
    failed: list[dict] = []

    # dry-run 不启动浏览器
    if dry_run:
        print(f"[dry-run] 将执行 {len(queries)} 个查询，上限 {max_total} 篇；不启动浏览器。")
        for q in queries:
            print(f"  - {q['query_id']}: {q['terms']} ({q['field']})")
        return {
            "manifest_id": f"download_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": iso_now(),
            "task_type": "cnki_search_download",
            "queries_executed": [q["query_id"] for q in queries],
            "total_found": 0,
            "total_downloaded": 0,
            "failed_downloads": [],
            "output_dir": "raw-library/papers/",
            "provenance_dir": "raw-library/provenance/",
            "dry_run": True,
        }

    with CNKIBrowser(headless=headless) as browser:
        browser.goto_home()
        browser.ensure_logged_in()

        for q in queries:
            if total_downloaded >= max_total:
                break
            queries_executed.append(q["query_id"])
            filters = q.get("filters", {})
            year_from = int(filters.get("year_from", 2005))
            year_to = int(filters.get("year_to", 2025))
            doc_types = filters.get("doc_type", ["期刊论文"])

            print(f"\n=== 执行查询 {q['query_id']} ===")
            try:
                browser.run_advanced_search(
                    terms=q["terms"],
                    field=q.get("field", "主题"),
                    year_from=year_from,
                    year_to=year_to,
                    doc_types=doc_types,
                )
            except Exception as e:
                print(f"  ! 检索失败: {e}")
                failed.append({"source_id": f"{q['query_id']}:search", "reason": str(e)})
                sleep_jitter(2.0, 3.0)
                continue

            sleep_jitter(2.0, 3.0)

            # 为该 query 抓取足够的结果（跨多页），直到达到预期或页末
            per_query_quota = min(
                int(q.get("expected_results") or 50),
                max_total - total_downloaded,
            )
            if per_query_quota <= 0:
                break

            collected: list[ResultRecord] = []
            page_no = 0
            while len(collected) < per_query_quota * 2 and page_no < 5:
                page_no += 1
                got = browser.collect_results(q["query_id"], limit=per_query_quota * 2)
                collected.extend(got)
                if len(collected) >= per_query_quota * 2:
                    break
                if not browser.try_next_page():
                    break

            # 去重（按 title+year）
            deduped: list[ResultRecord] = []
            local_seen = set()
            for r in collected:
                key = _title_key(r.title, r.year)
                if not r.title or key in seen_titles or key in local_seen:
                    continue
                local_seen.add(key)
                deduped.append(r)

            total_found += len(deduped)
            print(f"  找到 {len(deduped)} 条新候选（去重后）")

            # 逐篇下载
            for r in deduped:
                if total_downloaded >= max_total:
                    break
                year = r.year if r.year else datetime.now().year
                seq = next_seq_for_year(year, year_counter)
                source_id = f"cnki_{year}_{seq:03d}"
                if source_id in done_ids:
                    # 序号碰撞（理论上不会），递进
                    while source_id in done_ids:
                        seq = next_seq_for_year(year, year_counter)
                        source_id = f"cnki_{year}_{seq:03d}"

                target_pdf = PAPERS_DIR / f"{source_id}.pdf"
                print(f"  -> {source_id} {r.title[:40]}")

                try:
                    ok, reason, extra = browser.open_detail_and_download(r, target_pdf)
                except Exception as e:
                    ok, reason, extra = False, f"异常: {e}", {"abstract": "", "keywords": []}

                if ok:
                    write_provenance(
                        source_id, q["query_id"], r,
                        abstract=extra.get("abstract", ""),
                        keywords=extra.get("keywords", []),
                        status="success",
                    )
                    done_ids.add(source_id)
                    seen_titles.add(_title_key(r.title, r.year))
                    total_downloaded += 1
                else:
                    print(f"     失败: {reason}")
                    failed.append({"source_id": source_id, "reason": reason})
                    # 失败不写 provenance（避免污染 raw-library）
                    # 回退序号，让下一篇复用该编号
                    year_counter[year] = max(year_counter.get(year, 1) - 1, 0)

                sleep_jitter(3.0, 5.0)

            sleep_jitter(2.0, 3.0)

    manifest = {
        "manifest_id": f"download_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": iso_now(),
        "task_type": "cnki_search_download",
        "queries_executed": queries_executed,
        "total_found": total_found,
        "total_downloaded": total_downloaded,
        "failed_downloads": failed,
        "output_dir": "raw-library/papers/",
        "provenance_dir": "raw-library/provenance/",
    }
    return manifest


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="CNKI 检索与下载器（Playwright）")
    parser.add_argument("--query-id", help="只运行指定 query_id")
    parser.add_argument("--dry-run", action="store_true", help="只列出检索计划，不启动浏览器")
    parser.add_argument("--headless", action="store_true", help="headless 模式（仅调试用）")
    args = parser.parse_args()

    try:
        plan = load_search_plan()
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    try:
        manifest = process_queries(
            plan=plan,
            only_query_id=args.query_id,
            dry_run=args.dry_run,
            headless=args.headless,
        )
    except Exception as e:
        print(f"执行失败: {e}", file=sys.stderr)
        return 2

    write_manifest(manifest)
    print(f"\n✓ manifest 写入: {MANIFEST_PATH}")
    print(f"  找到 {manifest['total_found']} 篇 / 下载 {manifest['total_downloaded']} 篇 / 失败 {len(manifest['failed_downloads'])} 篇")
    return 0


if __name__ == "__main__":
    sys.exit(main())

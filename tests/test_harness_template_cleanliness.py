from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_agents_do_not_embed_previous_research_topic_terms():
    """Workspace harness code must stay intake-driven, not carry a prior thesis topic."""
    banned_terms = [
        "地域建筑符号",
        "设计教育",
        "旧题目样本词",
        "地域建筑",
        "地域建筑美学",
        "课程转化",
        "教学实践",
        "设计创作",
    ]
    runtime_files = sorted((PROJECT_ROOT / "runtime" / "agents").glob("*.py"))

    violations = []
    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        for term in banned_terms:
            if term in text:
                violations.append(f"{path.relative_to(PROJECT_ROOT)} contains {term}")

    assert violations == []

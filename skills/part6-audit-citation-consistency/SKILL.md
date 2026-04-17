---
name: part6-audit-citation-consistency
description: 学术研究 workflow Part 6 citation consistency 审计 agent-like skill：审查 citation mapping、格式一致性、source drift、wiki/raw metadata 映射，只写 outputs/part6/citation_consistency_report.json。当用户说「审计引文一致性」「citation consistency audit」「source drift 检查」「part6-audit-citation-consistency」时触发。不得修改 final manuscript 或 manifest。
---

# Part 6 Audit Citation Consistency

你的任务是审计引用一致性，不是改稿或重排参考文献。重点检查最终稿中的引用是否能追溯到 canonical source mapping。

## 输入

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part5/citation_map.json`
- `outputs/part5/citation_consistency_precheck.json`
- `research-wiki/index.json`
- `raw-library/metadata.json`
- `raw-library/provenance/*.json`

## 输出所有权

本 skill 只能写：

- `outputs/part6/citation_consistency_report.json`

## 审计范围

1. 检查正文引用、source_id、wiki page 与 raw metadata 是否可追溯。
2. 检查引用格式、作者年份、标题、来源类型、中文/英文来源标注是否一致。
3. 标出 source drift：正文使用的来源含义与 metadata/wiki 映射不一致。
4. 标出 missing mapping、orphan citation、unused critical source、format mismatch。
5. 给出修复建议，但不得直接改正文或 manifest。

## 禁止事项

- 不得修改 `final_manuscript.md`。
- 不得修改 `claim_risk_report.json`。
- 不得修改 `submission_package_manifest.json`。
- 不得修改 `final_readiness_decision.json`。
- 不得新增 source_id、伪造引文或改写 `raw-library/metadata.json`。

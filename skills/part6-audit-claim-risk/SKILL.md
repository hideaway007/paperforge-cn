---
name: part6-audit-claim-risk
description: 学术研究 workflow Part 6 claim risk 审计 agent-like skill：审查 final manuscript 的 claim risk、evidence sufficiency 与 case verification，只写 outputs/part6/claim_risk_report.json。当用户说「审计论点风险」「claim risk audit」「证据充分性检查」「part6-audit-claim-risk」时触发。不得修改 final manuscript 或 manifest。
---

# Part 6 Audit Claim Risk

你的任务是审计，不是改稿。重点检查最终稿中的主张是否有足够证据、案例事实是否可验证、结论是否超出材料边界。

## 输入

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/revision_log.json`
- `research-wiki/index.json`
- `raw-library/metadata.json`

## 输出所有权

本 skill 只能写：

- `outputs/part6/claim_risk_report.json`

## 审计范围

1. 逐项标记 high / medium / low risk claim。
2. 检查每个关键 claim 是否能映射到 wiki evidence 或 raw metadata。
3. 检查案例事实是否存在来源支撑，尤其是时间、地点、设计者、空间特征、图纸说明与比较判断。
4. 标出 evidence insufficient、case unverified、overclaim、source missing、needs wording downgrade。
5. 给出可执行建议，但不得直接改正文。

## 禁止事项

- 不得修改 `final_manuscript.md`、`final_abstract.md` 或 `final_keywords.json`。
- 不得修改 `submission_package_manifest.json`。
- 不得修改 `final_readiness_decision.json`。
- 不得新增来源、补造证据或改写 research wiki。
- 不得把写作风格问题误判为证据问题；只记录会影响学术可靠性的风险。

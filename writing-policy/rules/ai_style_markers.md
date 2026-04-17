---
rule_id: ai_style_markers
rule_type: expression
title: AI 腔与机械化表达识别规则
source: distilled_external_writing_practice
priority: medium
applies_to: [manuscript_draft, final_manuscript, academic_polish]
may_be_used_as_research_evidence: false
---

# AI 腔与机械化表达识别规则

## 规则定位

本规则只用于识别中文学术写作中的机械化表达风险。它不是研究证据，不得用于补充事实、案例、引文或结论。

## 需要压降的表达

- 机械递进：连续使用“首先、其次、再次、最后”组织复杂论证，但段落之间没有真实推进。
- 空泛价值判断：“具有重要意义”“提供了新的思路”“值得进一步探讨”反复出现，却没有说明意义对象和适用范围。
- 宣传式拔高：“极大推动”“全面提升”“开创性地证明”等，除非已有证据直接支撑。
- 泛化主体：“大量研究表明”“学界普遍认为”“实践证明”，但没有对应来源或 citation map。
- 抽象名词堆叠：用“机制、路径、体系、范式、价值”等连续堆叠替代具体分析。
- 过度均质段落：每段都采用完全相同的开头、连接词和收束句，使文本显得模板化。
- 伪客观语气：用“显然”“必然”“毫无疑问”等词遮蔽论证缺口。

## 推荐处理

- 能具体化的，补回对象、范围、条件或章节上下文。
- 证据不足的，降级为“提示”“表明”“在一定程度上反映”。
- 只是机械连接的，优先用语义顺序衔接，而不是继续增加连接词。
- 需要证据的，不在写作层补造；保留 risk note 或转入 evidence debt。

## 禁止处理

- 不得为了“去 AI 味”删除必要的 citation warning、evidence gap 或 risk note。
- 不得为了自然流畅而改变 claim 强度。
- 不得把作者稳定风格误判为 AI 腔；若存在 `author_style_profile.md`，先按作者风格画像判断。

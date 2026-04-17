---
name: author-style-profile-build
description: 学术写作 workflow 的匿名作者风格画像构建 skill：从已提供的作者语料中蒸馏学术写作机制，生成 writing-policy/style_guides 下的 author style profile 与 negative patterns。当用户要求「蒸馏作者文风」「提炼作者写作风格」「建立作者风格画像」「author-style-profile-build」时触发。该 skill 不直接改正文，不模仿具体人名，不把风格当作 research evidence。
---

# Author Style Profile Build

你的任务是从用户提供的作者语料中提炼可复用的学术写作机制，并把它沉淀为 writing-policy 层的风格约束。不要把这项工作理解为“模仿语气”，而是识别作者如何进入问题、组织段落、托住判断、控制证据强度和避免误写。

## 输出所有权

本 skill 只能写或更新：

- `writing-policy/style_guides/author_style_profile.md`
- `writing-policy/style_guides/author_style_negative_patterns.md`
- `process-memory/{YYYYMMDD}_author_style_profile_build.json`

不得直接写：

- `outputs/part5/manuscript_v1.md`
- `outputs/part5/manuscript_v2.md`
- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `research-wiki/`
- `raw-library/`

## 输入要求

必须有真实语料，且语料应可追溯到用户提供的文本、PDF 抽取文本或已确认的参考片段。没有语料时停止，不得空拟作者风格。

可读取：

- 用户提供的作者语料文本
- `writing-policy/rules/`
- `writing-policy/style_guides/`
- 需要时读取既有 `author_style_profile.md` 与 `author_style_negative_patterns.md`

只允许把语料作为 writing-policy 约束来源，不得把它作为论文 research evidence。

## 蒸馏维度

至少提炼以下六类机制：

1. 问题进入方式：如何开头、如何收束研究对象与问题意识。
2. 段落职责：每类段落承担什么功能，段落之间如何转接。
3. 证据承托：证据如何支撑判断，何时只做参照，何时可形成结论。
4. 判断强度：哪些表达需要限定、降级或保留余地。
5. 术语与句式：稳定术语、常见连接方式、标题层级习惯。
6. 负例模式：通顺但不符合该作者学术机制的写法。

## 执行流程

1. 检查语料是否存在、非空、可识别标题与段落。
2. 先提取段落职责和论证链，不先改句子。
3. 按“可复用机制”写入 `author_style_profile.md`。
4. 按“容易误写的模式”写入 `author_style_negative_patterns.md`。
5. 将本轮语料来源、更新时间、更新项和不采纳项记录到 `process-memory/{YYYYMMDD}_author_style_profile_build.json`。
6. 如果只有单篇语料，只能标记为 provisional；跨两篇以上重复出现后，才可提升为 stable rule。

## 文件内容要求

`author_style_profile.md` 应包含：

- 适用范围
- 写作机制摘要
- 问题进入方式
- 段落职责模式
- 证据与判断强度规则
- 术语和衔接习惯
- 可被 Part 5 / Part 6 调用的写作约束

`author_style_negative_patterns.md` 应包含：

- 不应出现的开头方式
- 不应出现的段落组织
- 不应出现的证据处理
- 不应出现的过强判断
- 不应出现的套话、散文化、宣传化表达

process-memory JSON 应包含：

- `event_type`: `author_style_profile_build`
- `source_refs`
- `profile_path`
- `negative_patterns_path`
- `rules_added`
- `rules_marked_provisional`
- `rules_rejected`
- `does_not_modify_manuscript`: `true`
- `does_not_create_research_evidence`: `true`

## 与 Part 5 / Part 6 的关系

- Part 5 draft/revise 可以读取该 profile 作为 writing-policy 约束。
- Part 6 finalize 可以读取该 profile 做保守表达收束。
- 该 skill 不拥有任何 manuscript artifact。
- 正文 owner 仍然是 `part5-draft-manuscript`、`part5-revise-manuscript` 或 `part6-finalize-manuscript`。

## 禁止事项

- 不得在文件名、正文或规则中写入具体作者人名；统一使用“匿名作者风格画像”或“author style profile”。
- 不得把作者风格当作 research evidence。
- 不得为了贴近风格新增事实、claim、source_id、citation、案例或图纸信息。
- 不得覆盖 canonical manuscript。
- 不得绕过 Part 5 / Part 6 artifact owner。
- 不得删除 evidence debt、risk note 或 citation warning。
- 不得将单篇语料中的偶然句式直接提升为稳定规则。

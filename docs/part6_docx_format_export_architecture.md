# Part 6 DOCX Format Export Architecture

> Current status: implemented contract for the Part 6 `.docx` format export extension. It is based on the user-provided South China University of Technology graduate course paper template. The cover page is explicitly out of scope. This document does not modify the existing Part 6 human gates or canonical audit artifacts.

## 1. Decision

Part 6 adds a final format export subflow:

**Final Manuscript Markdown -> SCUT-formatted DOCX -> Desktop user copy**

The export is a formatting and packaging step, not a rewriting step. It must not add claims, sources, case facts, references, sections, or conclusions. If the final manuscript has content problems, the exporter reports them; it does not hide them behind Word formatting.

## 2. Runtime Surface

Implemented entry points:

```bash
python3 cli.py part6-export-docx
python3 cli.py part6-finalize --step export-docx
python3 cli.py part6-finalize --step all
```

Implemented script:

- `runtime/agents/part6_docx_exporter.py`

The `all` flow runs:

```text
precheck
-> finalize
-> audit-claim
-> audit-citation
-> package-draft
-> export-docx
-> decide
-> package-final
```

## 3. Inputs

The exporter reads:

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `writing-policy/rules/scut_course_paper_format.md`

It must not read from `research-wiki/` as a way to add new content. Any research evidence was already resolved upstream.

## 4. Outputs

The exporter writes:

- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `~/Desktop/{论文题目}.docx`

The desktop file is a convenience copy, not the canonical artifact. The project artifact remains the stable path used by validation and package manifest checks.

## 5. Desktop Naming Rules

The desktop filename must be the paper title:

- Preserve Chinese characters and normal title punctuation.
- Trim leading and trailing whitespace.
- Replace filesystem-unsafe characters such as `/` and control characters.
- Use `.docx` extension.
- Do not use generic names such as `final_manuscript.docx` or `part6_final_manuscript.docx` for the desktop copy.

If `~/Desktop/{paper_title}.docx` already exists, the exporter keeps the final file at that exact name and moves the old conflicting file to a timestamped backup name before writing the new copy.

## 6. Template-Derived Format Contract

The template contributes only formatting rules. The extracted body requirements are captured in:

- `writing-policy/rules/scut_course_paper_format.md`

Core rules:

- A4 paper.
- Margins: top 2.5 cm, bottom 2.5 cm, left 3.0 cm, right 2.5 cm.
- Chinese font: Songti / 宋体简体.
- Title: 18 pt, bold, centered.
- Author: 14 pt, bold, centered.
- Abstract / keyword labels: 12 pt, bold.
- Abstract / keyword content: 12 pt.
- Body headings: 12 pt, bold.
- Body paragraphs: 12 pt.
- References heading: 12 pt, bold.
- Reference entries: 10.5 pt.
- Line spacing: double.

Cover page requirements are ignored:

- No student-number table.
- No college / teacher / semester form.
- No teacher comments or grade block.
- No template instruction text.
- No blue prompt text.

## 7. Validation

`outputs/part6/docx_format_report.json` records:

- `status`: `pass | pass_with_warnings | blocked`
- source manuscript ref
- project docx ref
- desktop docx ref
- paper title
- style checks
- content checks
- warnings / errors

Part 6 gate requires:

- project docx exists
- format report exists
- format report status is `pass` or `pass_with_warnings`
- `cover_excluded=true`
- desktop docx path exists
- package manifest includes both docx artifacts

## 8. Boundaries

- The exporter does not revise the manuscript.
- The exporter does not add sources.
- The exporter does not change citation maps.
- The exporter does not confirm Part 6 human gates.
- The exporter does not submit, upload, or email the paper.

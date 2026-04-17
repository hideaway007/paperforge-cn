# LLM Agent Architecture

> This document defines Codex LLM agent roles for the research-to-manuscript workflow. It does not replace deterministic runtime scripts. Runtime scripts still own file generation, schema validation, gate checks, state writes, and canonical locks unless a project skill explicitly says otherwise.

## 1. Layering

The workflow now has two different meanings of "agent":

| Layer | Example | Responsibility |
|---|---|---|
| Codex LLM agent role | `researchagent`, `writeagent`, `claimauditor` | Judgment, critique, synthesis, drafting proposals, risk analysis |
| Deterministic runtime script | `runtime/agents/part5_mvp_generator.py` | Reproducible file writes, schema validation, state/gate interaction, canonical artifact ownership |

This split matters because LLM agents are useful for academic judgment, but state transitions must remain deterministic.

## 2. Active LLM Roles

| Agent role | Main parts | Judgment owned by LLM | Deterministic owner |
|---|---|---|---|
| `researchagent` | Part 1-2 | Search strategy quality, relevance rationale, research gaps, source triage | Part 1 scripts, authenticity verifier, raw-library registrar, Part 2 gate |
| `wikisynthesisagent` | Part 2 | Concept/topic/method synthesis, contradictions, evidence aggregation quality | Part 2 wiki generator, source mapping, `research-wiki/index.json` validation |
| `argumentagent` | Part 3 | Candidate argument route design, comparison, stress test, refinement | Part 3 seed map, density/trace/schema validation, candidate file writes, human selection, canonical lock |
| `outlineagent` | Part 4 | Argument-to-section structure, chapter responsibility, transition logic, alignment risks | Part 4 outline generator and validation |
| `writeagent` / `writeragent` | Part 5-6 | Chinese academic drafting, conservative revision, author-style and academic-register constraints | Part 5/6 runtime scripts, review integrator, canonical manuscript writes unless a skill owns the artifact |
| `claimauditor` | Part 5-6 | Overclaim, evidence sufficiency, missing warrant, case-verification risk | Part 5 integrator, Part 6 finalizer/report writers |
| `citationauditor` | Part 5-6 | Citation support, source drift, orphan citation, missing mapping, format risk | Part 5 citation precheck, Part 6 citation report writer |

## 3. Runtime Bridges

`writeagent` is now connected to the runtime writing path through `runtime/llm_writer_bridge.py`.

The bridge is intentionally opt-in:

- If `RTM_WRITEAGENT_COMMAND` is configured, Part 5 `draft` sends a JSON request to that command before writing `outputs/part5/manuscript_v1.md`.
- If `RTM_WRITEAGENT_COMMAND` is configured, Part 6 `finalize` sends a JSON request to that command before writing `outputs/part6/writer_body.md` and assembling `outputs/part6/final_manuscript.md`.
- If `RTM_WRITEAGENT_COMMAND` is not configured, Part 5/6 writing now fails by default. The deterministic writer escape hatch is only available when `RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK=1` is set explicitly.
- Write paths write provenance:
  - `outputs/part5/writer_provenance.json`
  - `outputs/part6/writer_provenance.json`

The command receives JSON on stdin and must return JSON on stdout. Accepted text fields are `text`, `body`, or `manuscript`; Part 6 may also return `abstract`, `keywords`, and `conclusion`.

Other LLM roles use the generic `runtime/llm_agent_bridge.py`:

- `researchagent`: `RTM_RESEARCHAGENT_COMMAND`; Part 1 writes a search-plan review sidecar and provenance, while search plan generation, CNKI priority, and source policy remain deterministic.
- `wikisynthesisagent`: `RTM_WIKISYNTHESISAGENT_COMMAND`; Part 2 writes a wiki synthesis review sidecar and provenance, while `research-wiki/index.json`, source mapping, update log, and health checks remain deterministic.
- `argumentagent`: `RTM_ARGUMENTAGENT_COMMAND`; Part 3 candidate arguments and candidate trees must be LLM-designed. Runtime scripts package the request, validate argument density/source trace/schema, write candidate files, and keep seed map generation plus canonical lock deterministic. If this command is not configured, formal Part 3 generation fails; `--allow-deterministic-fallback` is only an offline debug escape hatch.
  - Local Codex adapter: `RTM_ARGUMENTAGENT_COMMAND="python3 runtime/agents/argumentagent_codex_cli.py"`.
- `outlineagent`: `RTM_OUTLINEAGENT_COMMAND`; Part 4 writes an `outlineagent_review.json` sidecar and provenance, but does not let the LLM rewrite canonical outline artifacts.
- `claimauditor`: `RTM_CLAIMAUDITOR_COMMAND`; Part 5/6 writes claim-audit sidecars and provenance, without modifying manuscripts or canonical reports.
- `citationauditor`: `RTM_CITATIONAUDITOR_COMMAND`; Part 5/6 writes citation-audit sidecars and provenance, without modifying citation maps, manuscripts, or readiness decisions.

Generic LLM commands receive JSON on stdin and must return a JSON object with at least one of `text`, `body`, `report`, `proposal`, `artifacts`, or `payload`.

This design keeps offline smoke runs possible through explicit escape hatches while requiring real LLM agents for judgment-heavy formal steps such as Part 3 argument generation.

## 4. Global Boundaries

All LLM agents must follow these boundaries:

- do not confirm human gates
- do not write `runtime/state.json`
- do not mark a stage complete
- do not write or lock canonical artifacts except through the runtime writer bridge or an active project skill that explicitly owns that output
- do not add source IDs, citations, case facts, figure facts, data, or research conclusions without traceability
- do not treat `writing-policy/`, author style samples, rubrics, or external prompt libraries as research evidence
- report evidence gaps instead of smoothing them away
- treat `part6_finalization_authorized` and `part6_final_decision_confirmed` as human-only gates
- never convert `formal_submission_ready` into an automatic submission action

## 5. Why These Agents Exist

The added LLM layer is for the parts where the project needs judgment:

1. Is this source actually relevant to the research question?
2. What does the literature collectively imply, and where does it conflict?
3. Which argument route is strongest?
4. Which chapter structure best carries the argument?
5. Does the manuscript sound academic without becoming vague or overclaimed?
6. Which claims are under-supported?
7. Which citations merely exist versus actually support the sentence?

The deterministic layer remains responsible for everything that must be reproducible.

# Part 3 ArgumentAgent Architecture

> This document extends Part 3 without changing the immutable truth-source docs. It defines how LLM `argumentagent` owns candidate argument generation while deterministic scripts keep evidence, validation, file writes, and gate boundaries intact.

## 1. Design Judgment

Argument tree quality must not depend on deterministic scripts to invent the argument. Scripts are good at repeatability, schema compliance, source tracing, density checks, and canonical locking, but weak at thesis formulation, warrant design, counterargument handling, and route-level judgment.

Part 3 therefore uses a layered model:

```text
deterministic seed map
  -> LLM candidate argument design
  -> LLM stress test and comparison
  -> LLM refined candidate proposal
  -> deterministic schema and traceability validation
  -> human selection
  -> deterministic canonical lock
```

## 2. Role Split

| Layer | Owner | Responsibility |
|---|---|---|
| Evidence anchors | deterministic script | Extract seed map from `research-wiki/` and `raw-library/metadata.json` |
| Candidate design | `argumentagent` | Build genuinely different argument routes from the seed map |
| Quality attack | `argumentagent` | Find logical jumps, missing warrants, overclaims, weak counterarguments and case overextension |
| Candidate refinement | `argumentagent` | Produce refined candidate proposals without overwriting originals |
| Density, schema and traceability | deterministic script | Validate required fields, argument density, source IDs, wiki page IDs and file layout |
| Canonical selection | user + deterministic script | Lock `outputs/part3/argument_tree.json` only after explicit human selection |

## 3. ArgumentAgent Scope

`argumentagent` may read:

- `outputs/part3/argument_seed_map.json`

`argumentagent` may work on:

- `outputs/part3/candidate_argument_trees/*.json`
- `outputs/part3/candidate_comparison.json`
- `outputs/part3/argument_quality_report.json`
- `outputs/part3/refined_candidate_argument_trees/*.json`

`argumentagent` must use these project skills:

- `part3-argument-generate`
- `part3-argument-compare`
- `part3-argument-stress-test`
- `part3-argument-refine`
- `part3-human-selection`

## 4. Hard Boundaries

`argumentagent` must not:

- write or overwrite `outputs/part3/argument_tree.json`
- generate, rewrite, or own `outputs/part3/argument_seed_map.json`
- auto-confirm `argument_tree_selected`
- write `human_selection_feedback.json` without explicit user selection
- advance to Part 4
- add source IDs, citations, case facts, figure facts, data, or conclusions not traceable to research evidence
- use `writing-policy/`, author style material, rubrics, or external prompt libraries as research evidence

## 5. Correct Operating Sequence

1. Run deterministic seed extraction through `python3 cli.py part3-seed-map`.
2. Use `argumentagent` with `part3-argument-generate` and `part3-argument-divergent-generate` to design three dense, genuinely different candidate routes from the seed map.
   - Local Codex adapter: `RTM_ARGUMENTAGENT_COMMAND="python3 runtime/agents/argumentagent_codex_cli.py"`.
3. Use `argumentagent` with `part3-argument-stress-test` to attack the candidates.
4. Use `argumentagent` with `part3-argument-compare` to compare candidate tradeoffs.
5. Use `argumentagent` with `part3-argument-refine` when quality report exposes fixable route-level issues.
6. Ask the user for explicit candidate selection.
7. Lock canonical `argument_tree.json` through `python3 cli.py part3-select ...`.

## 6. Why This Is Better

The LLM handles the part that needs judgment: thesis shape, route difference, warrants, counterarguments, limitations, innovation hypotheses, and explanation strength. The scripts handle the part that must be deterministic: file ownership, argument density checks, schema, source traceability, state, and human gate enforcement.

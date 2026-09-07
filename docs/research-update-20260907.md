# September 7 research update

The completed Luna/high studies retain small positive paired differences, with confidence intervals including zero. A new campaign has begun after a paper-alignment review; **its results are pending**. None of these observations establishes a statistically supported broad reproduction of the original gains.

## Completed held-out observations

| Study | N pairs | No skill | Frozen skill | Difference | Wins / losses | Exact McNemar p | Paired 95% CI |
|---|---:|---:|---:|---:|---:|---:|---|
| OfficeQA V1, paper document tools | 172 | 98 (57.0%) | 104 (60.5%) | +3.49 pp | 19 / 13 | 0.3771 | [-2.91, +9.88] pp |
| Spreadsheet, scoped-Python extension | 278 | 221 (79.5%) | 227 (81.7%) | +2.16 pp | 16 / 10 | 0.3269 | [-1.44, +5.76] pp |

Both decisions are `inconclusive`. The original OfficeQA two-endpoint corrected p is 0.7542; the expanded four-domain correction for Spreadsheet gives 1.0. Do not mix these with historical compromised OfficeQA runs. Earlier Sol V1-to-V2 and raw LiveMath observations remain in the immutable [September 6 snapshot](research-update-20260906.md).

These results came from the originating isolated research harness. They were not rerun by the portable CLI. OfficeQA development included Python while its test used glob/grep/read. Spreadsheet withheld target-region metadata and required concrete values rather than formula recalculation. Those conditions are material limitations, not details to omit from comparisons.

## Effort × fixed Luna skill: exploratory validation screen

All 144 observations are fresh: 24 tasks × medium/high/max × no-skill/skill, with a fixed skill and balanced within-task ordering.

| Effort | No skill /24 | Skill /24 | Skill difference | Mean seconds, no skill → skill |
|---|---:|---:|---:|---|
| medium | 15 | 17 | +2 tasks | 59.8 → 62.3 |
| high | 16 | 18 | +2 tasks | 88.6 → 109.0 |
| max | 20 | 19 | -1 task | 151.8 → 171.1 |

The primary max-versus-medium skill interaction is -12.5 pp, with a paired interval [-41.67, +12.5] pp. This screen does not establish that more reasoning increases skill benefit, nor that max-effort skills are harmful. These validation tasks helped select the skill; they are not fresh held-out confirmation. The maximum-effort condition here changes execution effort, not the effort that generated the frozen skill.

## What the failure analysis found

- Regression offsets 13 of 19 OfficeQA wins and 10 of 16 Spreadsheet wins. A higher retained validation score never implied per-task or test-time non-regression.
- Six of 16 Spreadsheet wins involve baseline formulas without usable caches versus concrete skill-arm values. That includes output/harness adaptation, not only better reasoning.
- Some losses concern target coverage, output location, duplicate handling, or blank/sentinel conventions. Whole-task exact scoring also turns a one-cell miss into a failed task.
- The initial Maintainer samples in the examined six evolution rounds each contained 12 failures and no successes. The original Appendix C reserves up to five failures and three successes. The roles could read other training material, so this is not a claim that successful outcomes were entirely inaccessible.
- The old inline trace summary only recognized shell events, omitting current MCP/Code Mode activity from its default view.
- The paper's Spreadsheet prompt supplies `answer_position` and `instruction_type`; the earlier local extension did not. This made scope inference an extra task.

These are observed implementation/setting differences and failure patterns. Their individual causal effect sizes have **not** been established through ablation. Correcting them does not guarantee larger gains.

## New campaign: alignment before new evolution

Two fresh Luna/high runs start from empty Wikis and skill sets. OfficeQA uses glob/grep/read for train, val and test; Spreadsheet uses isolated bash with Python/openpyxl and a verified workspace-local LibreOffice runtime. Both Spreadsheet arms receive legal target-region/task-type metadata and input previews. Formula caches can be produced; the former concrete-only constraint is removed.

The new learning path uses the paper's incremental Wiki JSON contract, five-failure/three-success sampling, visible tool arguments/results, and create/patch/no_action skill proposals. Skill proposals require actual reads of four distinct traces and include applicability, non-applicability and action instructions. Rejected proposals and full diffs remain in the Wiki history.

| Domain | Train / val / test | Workers | Initial protocol SHA256 |
|---|---|---:|---|
| OfficeQA | 50 / 24 / 172 | 2 | `300744bb991ecd0dbfaabb43eeb15af270e76771b6d7e9f8310dd939e363269d` |
| Spreadsheet | 80 / 40 / 278 | 4 | `112709e5f7b62c5a1f673bee7cc9a91fb94a3a511158e088bb57ef2899e90815` |

The originating implementation/protocol commit is `ec42f777785a2e65504eec229061cbb0f911da69`, recorded before new model calls. Startup found two empty MCP discovery responses that the initial strict audit misclassified. A disclosed transport amendment verifies that discovery responses are empty; resource reads/nonempty data remain forbidden. Completed native outputs were reused without re-querying the model.

Remaining extensions include production Luna/high, the Codex native base system, developer-level role injection, existing local splits, prior researcher exposure, OfficeQA full-corpus retrieval without oracle initial pages, and one complete evolutionary run rather than the paper's three. The Maintainer's `finish` transport adds contract feedback without new computational tools or external evidence.

## What this public package contains

- The portable adapter now reserves success examples and summarizes visible MCP/Code Mode events.
- `wikiskill.paper_alignment` contains separately importable paper JSON/patch contracts and balanced-evidence helpers. Install `.[paper]` for the YAML validation dependency.
- Paper prompt transcriptions are in `resources/paper_alignment/prompts`, attributed to the original authors. These building blocks are available for review and integration.
- **The portable CLI still uses its legacy single-skill proposal transport. It is not the full isolated paper-aligned runtime used for the new campaign.** No live research result is attributed to the default portable backend.

## Recompute the published observations

```bash
python scripts/check_research_update_20260907.py
```

The exported files contain task IDs, scores, hashes, aggregate workload and generic skills. Questions, gold answers, workbooks and complete model traces are excluded. Old snapshots remain unchanged. The checker validates hashes and recomputes paired outcomes, exact tests, intervals and the effort interaction.

Method source: [WikiSkill paper](https://huggingface.co/papers/2608.27454), especially §4.2.2, Appendix C and the appendix agent prompts.

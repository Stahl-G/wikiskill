# Paper-to-code conformance

This page maps each part of the WikiSkill method ([arXiv:2608.27454](https://arxiv.org/html/2608.27454v1)) to this repository and records what is implemented, what deviates and what has not been attempted. It describes code and experiment coverage; it does not change or remeasure any recorded result.

Status labels: **Implemented** — present and covered by offline tests; **Deviation** — present with a documented difference; **Not implemented** / **Not run** — absent from code or from the experiment record.

## Algorithm 1

| Paper step | Repository | Status |
|---|---|---|
| Start from empty skills `S0 = ∅` and an empty Wiki | `engine.initialize` writes an empty `skills/S0.md` and copies a domain Wiki template (index, log, skill-impact, prompts) | Implemented; the template is scaffolding, not prior pattern content |
| Baseline `R_best` from validation with no skill | `engine.evolve` records a `baseline` event before iteration 1 | Implemented |
| Early stop when `R_best = 1.0` | `engine.state` sets `early_stop_validation_ceiling` | Implemented |
| Train rollouts with the current skill | `engine.batch(... 'train' ...)` with the incumbent skill text | Implemented |
| Sample traces for the Maintainer | `paper_alignment.evidence.sample`: up to 5 failing and 3 passing TRAIN traces, seeded | Implemented in the paper adapter; legacy domain Maintainers use their own recorded selection |
| Wiki maintenance `W'k = M_WM(W_k-1, T_sample)` | `wiki_maintainer.py`; `PaperAgents.maintainer_factory` with the appendix prompt | Implemented |
| Proposal `Pk = M_P(W'k, S_k-1, T_train)` | `skill_proposer.py`; `PaperAgents.proposer_factory` | Implemented |
| Validate candidate on val | `engine.batch(... 'val' ...)` with the candidate | Implemented |
| Accept only if `R_val > R_best`; otherwise keep `S_k-1` | `eq4_accepted` (strict; ties rejected) and the `gate` event | Implemented |
| Wiki is never rolled back; every proposal recorded | Wiki is not restored on reject; `skill-impact.md` is regenerated from gate events with diff, score and verdict for accepted and rejected proposals | Implemented |

## Three layers and visibility

| Paper rule | Repository | Status |
|---|---|---|
| Raw traces are immutable | Rollout archives are write-once per iteration; completed tasks are reused on resume, not overwritten | Implemented |
| Inference agent has no Wiki access | Rollouts receive only skill text; the paper handoff records `executor_visibility.wiki = false`; isolated runtimes audit tool reads | Implemented |
| Learning roles see TRAIN only | `PaperAgents._rows` and `evidence.sample` reject non-train records; engine rejects train/val UID overlap | Implemented |
| Proposer reads Wiki and traces on demand (ReAct, `read_file`) | Paper adapter requires at least four distinct, actually successful trace reads before a create/patch | Implemented; the four-read minimum is this repository's check, not a paper number |
| Skills as `SKILL.md` + `PURPOSE.md` with frontmatter | `paper_alignment.contracts.validate_skill` requires frontmatter, applicability sections and purpose sections | Implemented in the paper adapter |
| Multiple skills in a skill set | Paper adapter keeps a named skill map; the legacy engine path stores one concatenated skill text | Deviation |
| No explicit skill length limit | Legacy/product proposer caps: 200 skill lines and 150 changed diff lines (earlier source runs used 80/60) | Deviation, disclosed in [reproduction](reproduction.md) |

## Evaluation protocol

| Paper protocol | Repository | Status |
|---|---|---|
| Disjoint train / val / test | Train/val are enforced by the engine. The 278-task Spreadsheet study evaluated a frozen skill on a fixed split in the source harness | Partially implemented; there is no packaged frozen-skill test command yet |
| Three independent evolutions, test averaged | One evolution per domain/model; the September 8 study repeats inference with one frozen skill | Not run |
| Paired bootstrap significance (1,000 resamples) | Task-cluster bootstrap with 10,000 resamples in `scripts/check_repeatability_20260908.py` | Implemented for recorded results; different resample count and clustering |
| Benchmarks: LiveMath, SealQA, Spreadsheet, OfficeQA, ALFWorld | Adapters for all five; OfficeQA uses staged-document and retrieval settings rather than the paper's oracle-page protocol | Implemented with deviations, see [limitations](limitations.md) |
| Models: Qwen-3.5/3.6, Gemma-4, Gemini-3.5-Flash | Codex-hosted production models | Different model set; paper numbers are not directly comparable |

## Experiments

| Paper experiment | Repository evidence | Status |
|---|---|---|
| WikiSkill vs no skill | Spreadsheet frozen skill: 73.74% → 85.49% over three runs (task-cluster CI excludes zero). SealQA and OfficeQA inconclusive; Math exploratory | Partially reproduced (one domain) |
| Persistent-Wiki ablation (no Wiki, Wiki visible to executor) | Adapters can express it through `maintainer_factory`; no study recorded | Not run |
| Baselines: Trace2Skill, EvoSkill, SkillOpt | None | Not implemented |
| Cross-model skill transfer | Six-cell OfficeQA pilot, mixed or unchanged | Pilot only |
| Skill evolution vs model scaling | None | Not run |

## What this means for users

The loop, visibility rules, gate and audit trail follow the paper and are tested offline. The strongest evidence that the method helps in practice is the repeated Spreadsheet result; it measures one selected skill, not the success rate of fresh evolutions or the Wiki's separate contribution. For your own workload, the relevant test is a frozen evolved skill against no skill on tasks the loop never saw — see the [product guide](product-guide.md).

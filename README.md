# WikiSkill

**A self-evolving skill framework for evaluable agent tasks.**

> **Research results (2026-09-07):** The corrected Spreadsheet fixed-split rerun improved from **213/278 to 237/278 (+8.63 pp)** with one frozen Luna/high skill. SealQA remains inconclusive; repeated mathematics validation is exploratory. Prior test exposure, scoring limits, and protocol amendments are disclosed in the [final record](docs/research-final-20260907.md).

Based on **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)** by Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, and Tu Vu (2026). This repository is an independent implementation of their method.

[Hugging Face Paper](https://huggingface.co/papers/2608.27454) · [arXiv](https://arxiv.org/abs/2608.27454)

WikiSkill turns execution experience into persistent knowledge and reusable procedural skills. An agent runs tasks, a Wiki Maintainer consolidates experience, a Skill Proposer suggests an update, and a deterministic validation gate decides whether to retain it. Rejected skills are rolled back; the Wiki keeps the lessons.

This independent research implementation starts with the Codex runtime and five task domains: document reasoning, spreadsheet manipulation, mathematics, web retrieval, and embodied interaction. The framework can be adapted to other tasks with reliable scoring, repeatable execution, and separate training, selection, and held-out evaluation data.

[中文](README_zh-CN.md) · [Results](docs/results.md) · [Reproduction](docs/reproduction.md) · [Datasets](docs/datasets.md) · [Paper](https://arxiv.org/abs/2608.27454)

## Latest research observations

The corrected Spreadsheet `feedback-v3` study shows a positive paired difference for **one frozen skill with Luna/high execution**. Both arms were freshly executed on the same 278-task split. Researchers had already seen earlier test results, so this is a **fixed-split rerun**, not a completely unseen confirmatory test. It does not establish an independent causal contribution from the Wiki or a guarantee that future evolutions will improve.

| Completed observation | No skill → frozen skill | Difference | Wins / losses | Statistical evidence |
|---|---:|---:|---:|---|
| Spreadsheet, corrected `feedback-v3`, 278 pairs | 213/278 → 237/278 | **+8.63 pp** | 31 / 7 | Exact p=0.000116; four-domain Bonferroni p=0.000465; paired 95% CI [+4.68, +12.95] pp |
| SealQA, original frozen skill, 85 pairs | 41/85 → 44/85 | **+3.53 pp** | 10 / 7 | Exact p=0.6291; four-domain corrected p=1; paired 95% CI [−5.88, +12.94] pp |

Spreadsheet's candidate was selected on validation (**28/40 → 32/40**). Its test scorer checks target-cell cached values; it does not verify whole-workbook formatting, dynamic formula behavior, or content outside the target region. Mean recorded attempt time rose from **94.11 to 121.05 seconds (+28.64%)** and cumulative tool calls from **1,287 to 1,766**. Four transport failures were each retried once and retained; these workload figures omit the full overhead of failed attempts.

SealQA used the original frozen skill, **not** the later candidate that reached 7/10 on validation. One skill-arm timeout was scored zero under a user-authorized amendment made after the run. A separate `view_image` call treated an HTTPS URL as a local path and returned `ENOENT` without data; an evidence-limited audit amendment recovered the original completion without resampling. Both amendments remain part of the result's interpretation.

Repeated mathematics validation used **18 task IDs × 4 arms × 2 repetitions = 144 fresh calls**, all executed by Luna/high with zero tool calls. Against no skill, the old Luna skill averaged **+13.89 pp**, the new Luna skill **+11.11 pp**, and the Astra-authored skill **0.00 pp**. The independent task-cluster count is 18, not 36. These reused validation tasks and unadjusted exploratory intervals do not support a held-out generalization claim. Astra authored one skill for Luna; this does not measure Astra execution or establish proposer superiority.

**Runtime boundary:** these observations are imported from the originating research harness. The published portable adapter includes balanced sampling, modern tool summaries, paper-contract helpers and prompt transcriptions. Its default CLI retains the legacy proposal transport and is **not the complete isolated research harness** used for these results.

[Final methods, results and limitations](docs/research-final-20260907.md) · [Score-only evidence and manifest](src/wikiskill/resources/research/final-20260907) · [Frozen Spreadsheet skill](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) · [Paper prompt resources](src/wikiskill/resources/paper_alignment)

The linked skill is an experimental artifact for inspection; publishing it does not automatically install or enable it.

```bash
# Offline recomputation and integrity checks; no model calls
python scripts/check_research_final_20260907.py
```

<details>
<summary>Earlier September 7 observations — separate frozen skills and protocols</summary>

The earlier Luna/high OfficeQA and Spreadsheet studies were both inconclusive:

| Earlier study | No skill → frozen skill | Difference | Wins / losses | Evidence |
|---|---:|---:|---:|---|
| OfficeQA V1, paper document tools | 98/172 → 104/172 | +3.49 pp | 19 / 13 | p=0.377; 95% CI [−2.91, +9.88] pp |
| Spreadsheet, scoped-Python extension | 221/278 → 227/278 | +2.16 pp | 16 / 10 | p=0.327; 95% CI [−1.44, +5.76] pp |

These observations are retained under their original conditions; the corrected Spreadsheet rerun above uses a different frozen skill and protocol. Its larger difference cannot identify the causal effect of any individual repair.

A 24-task, six-condition effort screen found no established monotonic increase in skill benefit: medium **15→17**, high **16→18**, max **20→19**. This is exploratory validation. Earlier Sol V1→V2 and raw LiveMath results remain in the [September 6 record](docs/research-update-20260906.md); the LiveMath no-tools violation remains disclosed.

The alignment review found that the former Maintainer sample could contain only failures, its inline summary missed modern tool events, and Spreadsheet target-region metadata was omitted. The corrected research path restores success/failure evidence, paper incremental-edit and applicability contracts, legal Spreadsheet inputs, and identical domain tools across train/val/test. OfficeQA uses glob/grep/read; Spreadsheet uses isolated bash with formula recalculation available. Individual repair effects have not been measured by ablation.

[Earlier checkpoint and alignment details](docs/research-update-20260907.md) · [Earlier score-only artifacts](src/wikiskill/resources/research/update-20260907)

The paper-alignment Wiki contract accepts harmless filename variants: missing `.md` suffixes are normalized, and underscores, hyphens and Unicode names are supported. Index paths follow the stored name. Path traversal and ambiguous overwrites remain errors; historical frozen snapshots are unchanged.

</details>

<details>
<summary>Historical September 5 validation snapshot — compromised retrieval observations retained for traceability</summary>

### Archived validation snapshot

Snapshot: **2026-09-05 09:05 UTC**. The originating experiments recorded **12 accepted updates across 9 domain–model configurations**. In office workloads:

| Task setting | Model | No skill | Retained validation score | Change |
|---|---|---:|---:|---:|
| OfficeQA, full-corpus retrieval | Sol | 18/24 · 75.0% | **23/24 · 95.8%** | **+20.8 pp** |
| OfficeQA, full-corpus retrieval | GPT-5.5 | 19/24 · 79.2% | **21/24 · 87.5%** | **+8.3 pp** |
| SpreadsheetBench | GPT-5.5 | 30/40 · 75.0% | **33/40 · 82.5%** | **+7.5 pp** |
| SpreadsheetBench | Sol | 33/40 · 82.5% | **34/40 · 85.0%** | **+2.5 pp** |

These are adaptively selected, single-run **validation outcomes**, not statistically confirmed held-out gains. Those statuses describe the archived September 5 snapshot, not the current runs. Current studies are reported separately. The full results table includes unchanged, unfinished, and unrun configurations. A nondecreasing retained score follows from the gate and does not prove that every task or future run improves.

The included snapshot was produced by the originating experiment harness, from which this package was extracted. The portable driver adds attempt preservation and resume bookkeeping; it has been checked offline, not used to rerun the published model matrix. See [reproduction and differences](docs/reproduction.md).


See [generalization study status](docs/generalization-status.md) for subsequent studies and validity checks.


</details>

## How it works

![WikiSkill evolution loop](assets/wikiskill-evolution.svg)

- **Raw experience:** each inference attempt gets its own directory and result or failure record.
- **Wiki:** train-derived patterns persist across accepted and rejected updates.
- **Skills:** the current skill is injected verbatim into the task prompt.
- **Gate:** retain a candidate only when its complete validation score is strictly greater than the incumbent's recorded score. Ties reject; `no_action` completes an iteration without a candidate evaluation.
- **Resume:** completed inference results are reused; infrastructure failures are preserved and surfaced. A workspace lock prevents duplicate writers.

## Quick start

Python **3.11+** on macOS or Linux. The ALFWorld environment has separate dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Offline: no model calls or API keys
wikiskill demo runs/demo
wikiskill status runs/demo
wikiskill results
python -m pytest -q
```

The demo uses synthetic deterministic outcomes to exercise ACCEPT, REJECT, and `no_action`. Its score is a software check, not an empirical model result.

The source distribution is named `wikiskill-research`; the Python package and CLI are `wikiskill`. Install from this checkout. Do not use an unrelated PyPI package as a substitute for this source release.

## Run a real experiment

An opt-in macOS `wikiskill spreadsheet-study` entry point is available for a bounded, isolated single-round Spreadsheet development study. It freezes caller-supplied data and keeps the legacy CLI unchanged. See [setup and scope](docs/isolated-spreadsheet-study.md). This new path is not the source of the historical published scores.


Install and authenticate the Codex CLI separately, then obtain the dataset under its upstream access terms. `doctor` checks executable availability; it does not validate credentials or model access.

```bash
wikiskill doctor

wikiskill init runs/officeqa-sol \
  --domain officeqa-retrieval \
  --model gpt-5.6-sol \
  --optimizer-model gpt-5.6-sol \
  --csv data/officeqa/officeqa_full.csv \
  --corpus data/officeqa/corpus \
  --iterations 4 --workers 4

# This command starts model calls. Re-running it resumes the same experiment.
wikiskill evolve runs/officeqa-sol
```

Use `--domain officeqa` for pre-staged source documents. Other adapters use `--data` and an optional `--split-dir`; see [dataset configuration](docs/datasets.md). Models are explicit configuration values: availability depends on the caller's account and runtime.

## Extending the framework

The common driver consumes task IDs, a split loader, a rollout function, and a numerical scorer. A new domain supplies those pieces plus Maintainer/Proposer prompts. The scorer should reflect the intended capability, not reward a formatting shortcut or an artifact of task construction. The current CLI exposes the bundled domains; adding another domain is a Python adapter extension, not automatic compatibility with every scored task.

The packaged backend is Codex. Its default portable execution path is not the hardened isolated research backend; do not treat it as a confirmatory isolation guarantee. The package now includes strict JSONL readers and an AST-aware audit utility, while the full versioned research drivers remain separate. Separate OpenClaw/ArXivMath experiments are part of the ongoing research program, not a shipped backend or a result in the bundled snapshot.

## Research status

| Area | Status |
|---|---|
| Train → Wiki → proposal → validation gate | Implemented; observed in live source experiments |
| Five domain adapters | Included; optional data/environment dependencies |
| Portable install and offline demo | Covered by tests and wheel smoke checks |
| Cross-model transfer | Exploratory study; no broad positive-transfer claim |
| Evaluation beyond skill selection | Completed paired observations and a corrected fixed-split rerun; prior exposure and protocol limits are explicit |
| Three independent evolutions per local cell | Not measured by the included snapshot |
| Wiki's independent causal contribution | Not established without matched ablation |

LiveMathematicianBench contains a known fixed meta-option artifact. Historical scores are retained with that limitation; new runs default to a revised split, whose provenance is included. ALFWorld's sampled validation split reached a ceiling for the two production arms. Neither observation justifies silently changing old results. See [limitations](docs/limitations.md).

## Cite the original paper

If you use the WikiSkill method, please cite the original authors:

```bibtex
@misc{tang2026wikiskill,
  title = {WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution},
  author = {Liyan Tang and Cyrus Rashtchian and Chun-Sung Ferng and Andrew Tomkins and Da-Cheng Juan and Tu Vu},
  year = {2026},
  eprint = {2608.27454},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  url = {https://arxiv.org/abs/2608.27454}
}
```

## License and attribution

Framework code is MIT, with retained attribution to the BriefLoop contributors. The vendored OfficeQA scorer is Apache-2.0, © Databricks; its license and notice are included under `third_party/officeqa/`. Dataset licenses and access conditions remain upstream. This is an independent implementation of [WikiSkill](https://arxiv.org/abs/2608.27454), not an author-official repository. See [NOTICE](NOTICE.md).

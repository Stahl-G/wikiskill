# WikiSkill

**A self-evolving skill framework for evaluable agent tasks.**

Based on **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)** by Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, and Tu Vu (2026). This repository is an independent implementation of their method.

[Hugging Face Paper](https://huggingface.co/papers/2608.27454) · [arXiv](https://arxiv.org/abs/2608.27454)

WikiSkill turns execution experience into persistent knowledge and reusable procedural skills. An agent runs tasks, a Wiki Maintainer consolidates experience, a Skill Proposer suggests an update, and a deterministic validation gate decides whether to retain it. Rejected skills are rolled back; the Wiki keeps the lessons.

This independent research implementation starts with the Codex runtime and five task domains: document reasoning, spreadsheet manipulation, mathematics, web retrieval, and embodied interaction. The framework can be adapted to other tasks with reliable scoring, repeatable execution, and separate training, selection, and held-out evaluation data.

[中文](README_zh-CN.md) · [Results](docs/results.md) · [Reproduction](docs/reproduction.md) · [Datasets](docs/datasets.md) · [Paper](https://arxiv.org/abs/2608.27454)

## Measured validation gains

Snapshot: **2026-09-05 09:05 UTC**. The originating experiments recorded **12 accepted updates across 9 domain–model configurations**. In office workloads:

| Task setting | Model | No skill | Retained validation score | Change |
|---|---|---:|---:|---:|
| OfficeQA, full-corpus retrieval | Sol | 18/24 · 75.0% | **23/24 · 95.8%** | **+20.8 pp** |
| OfficeQA, full-corpus retrieval | GPT-5.5 | 19/24 · 79.2% | **21/24 · 87.5%** | **+8.3 pp** |
| SpreadsheetBench | GPT-5.5 | 30/40 · 75.0% | **33/40 · 82.5%** | **+7.5 pp** |
| SpreadsheetBench | Sol | 33/40 · 82.5% | **34/40 · 85.0%** | **+2.5 pp** |

These are adaptively selected, single-run **validation outcomes**, not statistically confirmed held-out gains. Some evolution runs are still active. Generalization and transfer studies are ongoing; held-out results are pending. The full results table includes unchanged, unfinished, and unrun configurations. A nondecreasing retained score follows from the gate and does not prove that every task or future run improves.

The included snapshot was produced by the originating experiment harness, from which this package was extracted. The portable driver adds attempt preservation and resume bookkeeping; it has been checked offline, not used to rerun the published model matrix. See [reproduction and differences](docs/reproduction.md).


See [generalization study status](docs/generalization-status.md) for the running lean test scope and outstanding validity checks.

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

The packaged backend is Codex. Separate OpenClaw/ArXivMath experiments are part of the ongoing research program, not a shipped backend or a result in the bundled snapshot.

## Research status

| Area | Status |
|---|---|
| Train → Wiki → proposal → validation gate | Implemented; observed in live source experiments |
| Five domain adapters | Included; optional data/environment dependencies |
| Portable install and offline demo | Covered by tests and wheel smoke checks |
| Cross-model transfer | Exploratory study; no broad positive-transfer claim |
| Independent held-out generalization | In progress / results pending |
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

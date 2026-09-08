# WikiSkill

**Turn agent experience into reusable skills.**

Give an agent practice tasks and a way to check its work. WikiSkill collects what went right and wrong, organizes the lessons in a persistent Wiki, and turns them into skills the agent can use on its next task.

Built from the ideas in **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**, this independent implementation brings the method to Codex agents and practical document, spreadsheet, and reasoning tasks.

[中文](README_zh-CN.md) · [Quick start](#quick-start) · [Results](docs/research-repeatability-20260908.md) · [Original paper](https://arxiv.org/abs/2608.27454)

## The idea behind the paper

An agent already produces useful experience every time it works: a search that found the right document, a formula that failed, a repair that solved the problem. The paper asks how to turn that experience into knowledge that keeps helping across tasks.

WikiSkill separates three things:

| Layer | What it keeps |
|---|---|
| **Raw experience** | Task inputs, actions, outputs, and feedback |
| **Wiki** | Reusable patterns, explanations, successful approaches, and counterexamples |
| **Skills** | Concrete instructions that an agent follows while working |

A **Wiki Maintainer** consolidates experience. A **Skill Proposer** turns relevant patterns into a candidate skill. The agent tries it on validation tasks; the system keeps it only if its score improves. If the candidate is rejected, the Wiki retains what was learned.

This improves the agent's working instructions without training new model weights.

![The WikiSkill learning loop](assets/wikiskill-evolution.svg)

## A real example: from a failed workbook to a useful skill

In our Spreadsheet experiment, an agent wrote formulas and checked a recalculated temporary copy—but delivered the original file, whose formula results were still missing.

The Maintainer recorded this in the Wiki:

> “Formula recalculation is useful only if the recalculated file replaces the file handed to the evaluator or user.”

The evolved skill turned that lesson into explicit actions:

> “Never deliver the pre-recalculation workbook while inspecting only a temporary copy.”
>
> “Reopen that exact final output twice: once with formulas visible (`data_only=False`) and once with cached results (`data_only=True`).”

These are verbatim excerpts from actual generated artifacts. [Read the Wiki page](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md) · [Read the complete skill](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md)

The resulting skill also covers formula compatibility, text versus numeric output, and when recalculation is unnecessary. It is a practical procedure an agent can follow, inspect, and reuse.

## What we built

- **A working learning loop:** run tasks, build a Wiki, propose a skill, evaluate it, and keep or reject the update.
- **Codex integration:** use explicitly configured models for execution and skill development.
- **Five task adapters:** document QA, spreadsheet editing, mathematics, web research, and ALFWorld interaction.
- **An isolated Spreadsheet path:** a standalone macOS study with Python/openpyxl, LibreOffice recalculation, scoped tools, and separate learning/evaluation inputs.
- **Inspectable artifacts:** read the generated Wiki and skills, track accepted/rejected proposals, and resume completed work without repeating it.
- **Recomputable research results:** public per-task scores, artifact hashes, and offline analysis scripts.

The isolated package path has completed a real end-to-end check from a separate wheel installation: **8 training tasks, 4 validation tasks, one Maintainer, one Proposer, and candidate validation**. Its candidate tied the baseline, so the gate correctly retained the incumbent. [Setup and recorded check](docs/isolated-spreadsheet-study.md)

## Where you can use it

WikiSkill is useful when you have recurring tasks, meaningful feedback, and a way to compare old and new behavior.

| Scenario | What a skill can help the agent learn | Available here |
|---|---|---|
| **Spreadsheet automation** | Edit formulas, recalculate results, check the file that will actually be delivered | Adapter, isolated study, and an evolved example skill |
| **Document analysis** | Locate evidence, read tables, compare reporting periods, and answer from source material | Staged and full-corpus OfficeQA adapters |
| **Web research** | Improve search and evidence-gathering procedures | SealQA adapter |
| **Reasoning tasks** | Reuse problem-solving procedures and avoid recurring mistakes | Mathematics adapter |
| **Your own scored workflow** | Learn procedures specific to your inputs, tools, and feedback | Extend a Python adapter with a task loader, rollout, and binary scorer |

For recurring reports or multi-agent workflows such as BriefLoop, the next step is to learn evidence gathering, analysis, and writing procedures from completed work and human corrections. That integration is a [planned application](docs/research-next-steps.md), not a bundled backend.

## Results: the same skill helped across three runs

We froze the Spreadsheet skill above and compared **Luna/high with and without it** on the same 278 tasks, three times.

| Run | No skill | Frozen skill | Gain |
|---|---:|---:|---:|
| 1 | 76.62% | 85.25% | **+8.63 pp** |
| 2 | 71.94% | 84.17% | **+12.23 pp** |
| 3 | 72.66% | 87.05% | **+14.39 pp** |
| **Three-run average** | **73.74%** | **85.49%** | **+11.75 pp** |

The two follow-up runs—the primary repeatability comparison—averaged **+13.31 percentage points**, with a task-cluster bootstrap 95% interval of **[+9.35, +17.45] pp**. This measures one frozen skill on a reused task set; the score checks the requested cell values. The experiments ran in the originating research harness. [Methods, costs, other domains, and full evidence](docs/research-repeatability-20260908.md)

## Quick start

Python **3.11+**. The offline demo works on macOS and Linux.

```bash
git clone https://github.com/Stahl-G/wikiskill.git
cd wikiskill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .

# Try the learning loop with synthetic tasks. No model access needed.
wikiskill demo runs/demo
wikiskill status runs/demo
```

Open `runs/demo/wiki/` to see the accumulated lessons and `runs/demo/skills/` to inspect skill versions. The demo exercises an accepted update, a rejected update, and a round with no proposal.

### Run a small real Spreadsheet study

On macOS, provide an authenticated Codex CLI, SpreadsheetBench data, and a headless-compatible LibreOffice app. This entry uses **Luna/high** and one bounded learning round.

```bash
python -m pip install '.[spreadsheet,paper]'

wikiskill spreadsheet-study prepare runs/spreadsheet \
  --data /path/to/spreadsheet-data \
  --split-dir /path/to/splits \
  --libreoffice-app /path/to/LibreOffice.app

# Starts real model calls: up to 16 task calls and 2 learning calls.
wikiskill spreadsheet-study run runs/spreadsheet
wikiskill spreadsheet-study status runs/spreadsheet
```

[Dependency checks and study setup](docs/isolated-spreadsheet-study.md) · [Other adapters and data preparation](docs/datasets.md) · [General evolution CLI](docs/reproduction.md)

## Explore the project

| I want to… | Start here |
|---|---|
| Understand the method | [Original paper](https://huggingface.co/papers/2608.27454) |
| Inspect what the agents learned | [Wiki example](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md) and [evolved skill](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) |
| Check the numbers | `python scripts/check_repeatability_20260908.py` |
| Read all experiments, including mixed results | [Latest report](docs/research-repeatability-20260908.md) and [result history](docs/results.md) |
| Run or extend a task adapter | [Reproduction guide](docs/reproduction.md) and [datasets](docs/datasets.md) |
| See what comes next | [Research and practical milestones](docs/research-next-steps.md) |

## Citation

If you use the method, please credit the original paper:

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

## License

Framework code is MIT. Third-party scorers and prompt resources retain their own attribution and notices. This is an independent implementation of the paper. See [LICENSE](LICENSE), [NOTICE](NOTICE.md), and [third-party notices](third_party/).

# WikiSkill

**Turn agent experience into reusable skills.**

Give an agent practice tasks and a way to check its work. WikiSkill collects what went right and wrong, organizes the lessons in a persistent Wiki, and turns them into skills the agent can use on its next task.

Built from the ideas in **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**, this independent implementation lets your existing agent enter an improvement loop using its own model and normal tools.

[中文](README_zh-CN.md) · [Install the skill](#quick-start) · [Product guide](docs/product-guide.md) · [Results](docs/research-repeatability-20260908.md) · [Original paper](https://arxiv.org/abs/2608.27454)

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

![The WikiSkill learning loop](assets/wikiskill-evolution-en.svg)

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
- **Use your own agent and model:** a host-agent request protocol, with no product-level model pin or mandatory sandbox.
- **Your own tasks and scores:** arbitrary JSON/file inputs, finite numeric metrics, maximize/minimize, and user-selected sample sizes and rounds.
- **Keep learning across batches:** carry a retained skill, Wiki and feedback into new tasks with `start --from`.
- **Human feedback straight into the Wiki:** preserve the original note, then connect it to learned patterns.
- **An installable entry skill:** ask your agent to start, resume, inspect or export an improvement loop.
- **Five task adapters:** document QA, spreadsheet editing, mathematics, web research, and ALFWorld interaction.
- **An optional isolated research path:** a standalone macOS study with Python/openpyxl, LibreOffice recalculation, scoped tools, and separate learning/evaluation inputs.
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
| **Your own scored workflow** | Learn procedures specific to your inputs, tools, and feedback | Product task JSON, your agent, and an external scorer or declared human/rubric rating |

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

## Native subagents in v0.1.1

The main agent coordinates. Separate subagents execute each task, maintain the Wiki, and propose a skill. Candidate validation uses fresh task contexts. The CLI prepares role-specific handoffs and records results; your host creates the agents using its native tools.

```bash
# Run in the project where you want to use WikiSkill:
wikiskill agents install --runtime codex --project .
# For Claude Code instead:
wikiskill agents install --runtime claude-code --project .
```

This installs the coordinating skill and three native role definitions. Then ask your agent to use WikiSkill for one round; it handles dispatch, waiting and submission. Existing differing files are preserved. [Host workflow](skills/wikiskill/references/native-subagents.md) · [Validation scope](docs/native-subagents-0.1.1.md).

Codex native fresh-context delegation has a live workflow check. Claude Code definitions are provided and syntax-checked; Claude live inference has not been verified here. Fresh child contexts still inherit host policies and may receive project instructions or memory. They are not filesystem sandboxes.

## Quick start

Python **3.11+** for the controller. Product mode uses your agent's normal environment on macOS, Linux or Windows.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install git+https://github.com/Stahl-G/wikiskill.git
npx skills add Stahl-G/wikiskill --skill wikiskill
```

On Windows PowerShell, replace the activation line with `.venv\Scripts\Activate.ps1`. You can reuse an existing project environment instead.

Then ask your agent:

> Use WikiSkill to improve this skill from my task examples and feedback. Use the project's tests to evaluate it, and start with one round.

The [entry skill](skills/wikiskill/SKILL.md) guides the agent through setup, task execution, Wiki maintenance, proposals and validation. You choose the model, tools and budget. It does not silently launch a fixed provider or alter your host permissions.

A separate agent has completed the workbook example through the installed product entry, including Wiki maintenance and candidate validation. [Observed outcome and setup fix](docs/product-first-use-validation.md).

### See progress and use the result

Your agent prepares the task file from your examples and agreed checks. You can inspect setup and progress at any point:

```bash
wikiskill preflight runs/my-task
wikiskill status runs/my-task --human
wikiskill report runs/my-task
```

The report shows decisions, task-level improvements and regressions, actual skill changes, and learned Wiki patterns. After completion, `wikiskill install runs/my-task ./my-skills/task-name` installs a retained skill. An authorized `--replace` keeps a backup and returns a restore command. Required tools and supporting files still need to be available. [Installation and recovery](docs/product-guide.md#install-and-recover-a-local-skill).

Run `wikiskill doctor` to check the distribution and installation path: this project is **Stahl-G/wikiskill**, distributed as **wikiskill-research**.

### Use the CLI or connect another agent

```bash
# Create a workflow using your own task examples.
wikiskill start runs/my-task --tasks tasks.json --rounds 2

# Return the next task or learning request for your agent.
wikiskill next runs/my-task

# Add feedback directly, or inspect progress.
wikiskill feedback runs/my-task --text "Check the exact file you will deliver."
wikiskill status runs/my-task

# After the loop finishes, export the retained skill.
wikiskill export runs/my-task ./improved-skill
```

External scorer commands are inspected and authorized once per unchanged local configuration. [Scorer trust](docs/product-guide.md#review-an-external-scorer-once).

Provide an external scorer with `--scorer '["python", "score.py"]'`, or record a human/rubric-based score. The controller returns work requests; the host agent executes them and records the actual outputs. [Task format, scoring, and complete workflow](docs/product-guide.md) · [Small text example](examples/text-cleanup/) · [Workbook delivery example](examples/workbook-delivery/)

### Try an offline demo

```bash
wikiskill demo runs/demo
wikiskill status runs/demo
```

The synthetic demo needs no model access and exercises acceptance, rejection and no_action. Open `runs/demo/wiki/` and `runs/demo/skills/` to inspect the artifacts.

The existing benchmark adapters and the isolated macOS Spreadsheet study remain available as separate research tools. [Research study setup](docs/isolated-spreadsheet-study.md) · [Datasets](docs/datasets.md) · [Legacy evolution CLI](docs/reproduction.md)

## Explore the project

| I want to… | Start here |
|---|---|
| Understand the method | [Original paper](https://huggingface.co/papers/2608.27454) |
| Inspect what the agents learned | [Wiki example](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md) and [evolved skill](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) |
| Check the numbers | `python scripts/check_repeatability_20260908.py` |
| Read all experiments, including mixed results | [Latest report](docs/research-repeatability-20260908.md) and [result history](docs/results.md) |
| Improve my own task | [Product guide](docs/product-guide.md) and [entry skill](skills/wikiskill/SKILL.md) |
| Run the research adapters | [Reproduction guide](docs/reproduction.md) and [datasets](docs/datasets.md) |
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

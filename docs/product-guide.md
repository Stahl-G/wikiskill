# Improve a skill with your own agent

WikiSkill's product workflow is driven by the agent you already use. It can be a terminal assistant, an IDE agent, or another tool-using agent that can run commands and write files. The controller does not choose its model, start a provider session, or impose an OS sandbox. Your host's normal permissions still apply.

## Install the package and entry skill

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install git+https://github.com/Stahl-G/wikiskill.git
npx skills add Stahl-G/wikiskill --skill wikiskill
```

On Windows PowerShell, replace the activation line with `.venv\Scripts\Activate.ps1`. You can reuse an existing project environment instead.

Use an existing project environment if you already have one. A venv isolates Python dependencies; it does not sandbox the agent or restrict normal file/tool access. Installing from Git runs package build code, so use a source you trust.

Alternatively clone the repository, run `python -m pip install .`, and copy `skills/wikiskill/` into the skill directory used by your agent. The skill has no dependency on another personal skill or a research checkout.

Ask your agent:

> Use WikiSkill to improve this recurring task using these examples and my feedback. Start with one round and evaluate with the project's tests.

The skill helps identify inputs and the evaluation method, creates a workspace, follows work requests, and explains the result. It asks only for missing decisions that materially affect the task or budget.

## The workflow

1. Run the current skill on validation tasks to establish a baseline.
2. Execute training tasks and retain outputs, scores, feedback and optional visible traces.
3. Consolidate reusable lessons in the Wiki, including direct human feedback.
4. Propose a revised skill, or return no_action.
5. Evaluate a candidate using the same validation task set and scoring criterion.
6. Retain it only when improvement exceeds the configured threshold; keep the Wiki even when the skill is rejected.

Each round follows these steps. The caller chooses the number of rounds and the amount of task data. There is no Luna/high requirement, macOS requirement, 8/4 sample cap, binary-score requirement or provider-specific execution API in this product path.

## Task files and evaluation

Use JSON with `train` and `validation` lists. Each item has an `id`, an `instruction`, optional arbitrary JSON `input`, optional `files`, and optional `reference` for evaluation. File paths resolve relative to the task JSON. See the [small text-cleanup example](../examples/text-cleanup/tasks.json).

```bash
wikiskill start runs/my-workflow \
  --tasks examples/text-cleanup/tasks.json \
  --rounds 2 \
  --scorer '["python", "examples/text-cleanup/score.py"]'
```

Add `--skill path/to/current/SKILL.md` to start from an existing skill. Use `--direction minimize` for loss or error metrics. `--min-improvement 0.05` requires an improvement strictly greater than 0.05. Scores can be any finite numbers; larger task sets and more rounds are user choices rather than hardcoded experiment settings.

An external scorer receives task/output JSON on stdin and returns `{ "score": 0.8, "feedback": "...", "success": false }` on stdout. For non-text output it reads the saved file path. Human or rubric-based scores can instead be passed through `record --score` with their basis in `--feedback`. A broken scorer is a recorded failure, not a score of zero.

## Review an external scorer once

```bash
wikiskill scorer inspect runs/my-workflow
wikiskill scorer trust runs/my-workflow --fingerprint <fingerprint-from-inspect>
```

The inspection shows exactly which command will run, its executable, working directory, timeout and directly named file hashes. Local authorization is stored separately from the workflow, so an imported workspace cannot authorize its own command. An unchanged trusted scorer does not ask again for every task. Changes to that binding require a fresh inspection. Indirect imports and remote dependencies still belong to the program's normal trust scope. Authorization permits execution; it does not certify the grading logic. If that logic changes, establish a consistent new comparison rather than silently mix old and new scores.

If you supplied and approved the scorer yourself at creation, `start ... --trust-scorer` is the explicit shortcut. Do not apply it blindly to another person's configuration. If authorization is missing, task dispatch pauses with `needs_scorer_trust`; approving it continues the same workflow without spending a model call.

## Following work requests

```bash
wikiskill next runs/my-workflow
wikiskill next runs/my-workflow --count 4
```

The returned requests tell the current agent which task and skill to use, or where to read the Maintainer/Proposer context. `--count` supports host-managed parallel task execution; it does not start threads or models itself.

Record an actual task output:

```bash
wikiskill record runs/my-workflow --request req-... --output result.txt --trace work-log.txt
```

Submit Wiki patterns, then a candidate skill:

```bash
wikiskill learn runs/my-workflow --request req-... --file patterns.json
wikiskill propose runs/my-workflow --request req-... --skill candidate/SKILL.md --note "What changed"
```

The agent normally handles these details after loading the [entry skill](../skills/wikiskill/SKILL.md). The [command reference](../skills/wikiskill/references/workflow.md) contains exact formats.

## Human feedback goes straight to the Wiki

```bash
wikiskill feedback runs/my-workflow --text "Validate the file you will actually deliver."
```

The original note is saved immediately and appears in the Wiki index. No LAJ score or model approval is required. The Maintainer can connect it to task outcomes, add counterexamples and revise derived patterns; it cannot overwrite the original feedback through the learning API. A note entering the Wiki does not automatically turn a factual assertion into evidence or promote an untested skill.

You may also start a workspace without tasks, collect feedback, and attach a task set with `wikiskill tasks ... --file tasks.json` before execution.

## Keep learning from new tasks

```bash
wikiskill start runs/next-batch --from runs/my-workflow --tasks new-tasks.json --scorer '["python", "score.py"]'
```

This starts with the retained skill, accumulated Wiki and original feedback from the earlier workspace. It establishes a new baseline on the new tasks instead of reusing old scores. The earlier journal stays unchanged; each batch has its own current evaluation settings.

## Results, retry and export

```bash
wikiskill status runs/my-workflow
wikiskill export runs/my-workflow ./improved-skill
```

The export contains the retained SKILL.md and provenance. Original and rejected candidates remain in the workspace. An empty or rejected-only run without an initial skill has nothing to export as a retained skill; its Wiki and candidate records are still available.

An execution failure can be recorded with `record --error`. Resolve its cause, run `retry --request`, then call `next` again. The prior failure remains recorded. If evaluation failed after a usable output was produced, the next request points to that saved output so the agent can retry scoring without unnecessarily rerunning the task. Re-recording the same completed output does not invoke the scorer again.

Keep workspaces in your own project and out of public commits when they contain private inputs or feedback.

## Python integration

```python
from wikiskill import product

product.start("runs/job", tasks="tasks.json", rounds=2)
work = product.next_work("runs/job", count=4)
# Your own agent/executor handles work["requests"].
# product.record(), product.learn() and product.propose() advance the loop.
```

The JSON request protocol is the integration surface. A provider does not need a dedicated plugin to participate, but an executor must actually handle tasks and record outcomes. This package is not a background model service.

## Product use and research records

`start` / `next` and the entry skill are the normal host-agent product path. Existing `evolve`, `demo` and `spreadsheet-study` remain compatible for their documented uses. In particular, `spreadsheet-study` retains its original isolated macOS/Luna research conditions.

Product workspaces preserve useful records, but they inherit normal host access and are not presented as isolated benchmark evidence. The published benchmark results retain their original runtime and protocol descriptions.

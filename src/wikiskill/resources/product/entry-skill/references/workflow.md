# Operating the product workflow

Codex and Claude Code users should use [native delegation](native-subagents.md), including `start --agent-runtime`, `dispatch`, `bind-agent` and `collect`. The direct `next/record/learn/propose` sequence below documents the compatibility API; it is not permission to perform native-workflow roles in the coordinator context.

The product commands below use the calling agent's model and normal tools. They do not start a Codex subprocess, require a particular provider, or create an OS sandbox. `evolve` and `spreadsheet-study` are separate research/legacy paths.

## Create a workspace

```bash
wikiskill capabilities
wikiskill start .wikiskill/my-task --tasks tasks.json --rounds 1
```

Add `--skill path/to/current/SKILL.md` to improve an existing skill. Use `--direction minimize` for error/cost metrics; maximize is the default. `--min-improvement 0.01` requires more than that improvement. Samples and rounds have no experiment-only upper bound.

Tasks are supplied as JSON:

```json
{
  "train": [
    {"id": "train-1", "instruction": "Describe the requested job", "input": {"text": "example"}, "files": [], "reference": "optional scorer reference"}
  ],
  "validation": [
    {"id": "val-1", "instruction": "Describe another instance of the job", "input": {"text": "another example"}, "files": [], "reference": "optional scorer reference"}
  ]
}
```

IDs must be unique; `files` resolve relative to the task JSON. `input` can contain arbitrary JSON. Execution requests omit the reserved `reference`, `expected`, `gold` and `score` fields. These are routing conventions, not filesystem access isolation.

You can initialize without tasks to collect feedback, then attach them before execution:

```bash
wikiskill start .wikiskill/my-task
wikiskill feedback .wikiskill/my-task --text "Check the actual delivered file, not a temporary copy."
wikiskill tasks .wikiskill/my-task --file tasks.json
```

The task set is fixed once attached so baseline and candidate are checked against the same tasks. For new tasks, carry the retained skill, Wiki and feedback into a new workspace:

```bash
wikiskill start .wikiskill/next-batch --from .wikiskill/my-task --tasks new-tasks.json --scorer '["python", "score.py"]'
```

This carries knowledge, not previous scores or task-completion caches. Configure the current batch's scorer, metric and budget explicitly.

## Scoring

Use `--scorer '["python", "score.py"]' --project /path/to/project` at start for an external evaluator. It runs in that project with the normal environment. The command gets JSON on stdin:

```json
{"task": {"id": "...", "reference": "..."}, "output": {"path": "/absolute/saved/output", "text": "UTF-8 text, or null for binary files"}, "phase": "baseline", "round": 1}
```

It must print a JSON object such as:

```json
{"score": 0.8, "feedback": "Two requested details were missing.", "success": false}
```

`score` is any finite number. `feedback` and `success` are optional. Nonzero exits, invalid JSON and invalid scores become recorded failures, not task scores. For workbook/PDF outputs, the evaluator reads `output.path`.

Without a configured evaluator, provide `--score` and describe the actual human/checker/judge basis in `--feedback`. Explicit rubric-based model evaluation is possible, but do not substitute a guessed score for an agreed evaluation method. Prefer a fresh judge context where available; no fixed judge model is required.

## Authorize the scorer once

```bash
wikiskill scorer inspect .wikiskill/my-task
# Review command, executable, working directory and direct-file hashes.
wikiskill scorer trust .wikiskill/my-task --fingerprint <fingerprint-from-inspect>
```

Trust is kept in the current user's local WikiSkill trust store, outside the workflow folder. Copying a workspace does not carry that authorization to another path or user environment. Commands, working directory, executable or directly named files changing invalidates the fingerprint. This fingerprints direct files, not all imported modules or remote dependencies.

When the user explicitly supplied/approved the checker while starting the workflow, `start ... --trust-scorer` records that existing authorization without another dialogue. Do not use the shortcut for an unreviewed imported configuration.

`next` returns `needs_scorer_trust` before issuing task work, and `record` refuses an untrusted scorer without executing it. After approval, continue the same request; no task retry is needed solely for trust approval.

## Execute the next request

```bash
wikiskill next .wikiskill/my-task
# Optional: request several task jobs for parallel execution.
wikiskill next .wikiskill/my-task --count 4
```

Each request has a stable `id`, `kind`, `phase`, `round` and task or context. Relative file paths, including `skill.file`, `context_file`, output/trace artifacts and feedback files, resolve against the workspace root. Read the indicated skill before task execution.

### Task

Execute `request.task.instruction` using its `input`/`files`, save the actual output, then:

```bash
wikiskill record .wikiskill/my-task --request req-... --output output.txt --trace work-log.txt --model chosen-model --runtime chosen-agent
```

Use optional `--effort` to record a known reasoning setting. Omit trace/model/effort/runtime if unknown or unavailable; do not fabricate provenance. With manual evaluation, also pass `--score 0.8 --feedback "..."`. Existing TRAIN outputs and logs can be recorded when they match the declared tasks and conditions; do not call them fresh executions.

### Maintainer

Read `context_file`. It contains Wiki patterns, verbatim human observations, training output/trace locations and feedback. Produce:

```json
{"patterns":[{"name":"Deliver the checked file","content":"Verify the exact final output after the last transformation.","sources":["req-training-example","feedback-example"]}]}
```

Use actual source IDs from that context. Pattern names are topic labels, not constrained filenames. Updates merge into the persistent Wiki; previous versions remain in the journal.

```bash
wikiskill learn .wikiskill/my-task --request req-... --file patterns.json
```

### Proposer

Read the current Wiki and relevant training evidence. Write a complete candidate SKILL.md with standard `name` and `description` frontmatter and useful procedural instructions. Then:

```bash
wikiskill propose .wikiskill/my-task --request req-... --skill candidate/SKILL.md --note "What changed and why"
# Or, when no useful change is justified:
wikiskill propose .wikiskill/my-task --request req-... --no-action --note "Why no change is proposed"
```

The controller issues candidate validation jobs and applies the strict improvement gate. Rejected skills stay in history; the Wiki retains its updates. Call `next` again until complete or a real problem requires attention.

## Failure, status and export

```bash
wikiskill record .wikiskill/my-task --request req-... --error "Tool or execution failure"
wikiskill status .wikiskill/my-task
# After resolving the actual cause:
wikiskill retry .wikiskill/my-task --request req-...
wikiskill next .wikiskill/my-task
```

A retry receives a new request ID and preserves the old failure. If `previous_output` exists, attempt to evaluate that saved output before rerunning the model. A repeated record of the same completed request does not rerun the evaluator.

```bash
wikiskill export .wikiskill/my-task ./improved-skill
```

If there was no initial skill and every candidate was rejected or no_action, there is no retained skill to export. Explain that result and link the Wiki and candidate history; do not present the rejected candidate as retained.

Export writes the retained `SKILL.md` plus provenance. It does not overwrite an occupied directory or automatically install a global skill. When installation/replacement is authorized, use the install/restore commands below for the chosen directory. Keep user run folders and feedback out of public Git commits.

## Readiness and user-facing results

Run `wikiskill preflight WORKSPACE` before task execution. It is read-only and does not execute a scorer; exit 2 identifies missing setup. Optional task `group` records a source family for split review. Use `wikiskill doctor` to identify the installed distribution and module.

Use `wikiskill status WORKSPACE --human` for progress and `wikiskill report WORKSPACE` at completion. The report contains recorded gate decisions, candidate/incumbent task comparisons, skill diffs and source-bound Wiki patterns. `--format json` returns structured data. No-action has no candidate score; partial baselines remain unmeasured. Save the report to the user's local workspace if useful, and explain applicability/tools from the actual skill rather than inventing them.

After explicitly selecting an installation directory, `wikiskill install WORKSPACE DESTINATION` installs the retained SKILL.md. Add `--replace` only for an intended replacement. The command returns a backup ID and `wikiskill restore DESTINATION --backup ID` undo command; later user edits are protected. Existing support files are not changed, and tool dependencies are not installed automatically.

A checker changed after successful scores requires a new comparison workspace, even after local authorization. A checker repaired before any successful score can rescore saved output through the normal retry path.

If the host cannot write the default `~/.wikiskill/scorer-trust` directory, set `WIKISKILL_TRUST_DIR` to a writable operator-owned directory **outside the workflow**. Use that same environment setting for subsequent commands. Resume the existing workspace with `scorer inspect` / `scorer trust`; a setup permission error does not require starting over. Do not point this setting at an imported workspace's own approval files.

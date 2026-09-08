---
name: wikiskill
description: Operate WikiSkill workflows that use task examples, scores, a persistent Wiki, and validation to improve reusable skills. Use when starting or resuming such a loop, adding feedback to its workspace, or exporting its result. Ordinary SKILL.md writing or editing belongs to the user's existing skill editor.
---

# WikiSkill

Help the user improve a recurring agent task through experience. Use the user's current agent, chosen model and normal tools. WikiSkill owns the work requests, records, scores and retained skill versions; it does not select a model or change host permissions.

## Start with the user's intent

- **Remember feedback:** save it with `wikiskill feedback`; do not start an improvement run merely because a note was added.
- **Improve a skill:** identify the task examples, evaluation criterion, current skill if any, and the user's intended effort/budget. Reuse information already provided. Begin with one round unless the user requests more; there is no hard sample or round cap.
- **Resume:** read `wikiskill status`, then use `wikiskill next` in the existing workspace. Do not initialize a duplicate run.
- **Check only:** use `wikiskill status` and existing artifacts; do not start more work.
- **Use the result:** export the retained skill. Install or replace an existing skill when the user has authorized that destination.

Read [workflow commands and formats](references/workflow.md) when preparing tasks or operating the loop. Use `wikiskill capabilities` to discover the installed interfaces. If the package is missing, use the user's selected checkout or the official repository. Prefer an existing project virtual environment; otherwise create a project-local venv and use its Python and wikiskill executables. Do not default to modifying the system/global Python environment. Installation executes package build code, so inspect unfamiliar sources first. The product path works without a Codex CLI account.

If another skill-improvement tool such as `skill-evolve` is installed, compare its description rather than assume the tools are equivalent. Keep ordinary creation/rewriting with the user's chosen editor. Choose WikiSkill for the task-score-Wiki-validation cycle, or when the user names WikiSkill. Do not run two improvement controllers for the same task or recommend uninstalling the other skill merely because both are present.

## Prepare a useful comparison

Before executing an external scorer, run `wikiskill scorer inspect WORKSPACE` and surface its command and working directory. Record local trust only if that exact checker is covered by the user's authorization. If the user already supplied or approved it, do not ask again; `start --trust-scorer` is an explicit shortcut for that case. Never auto-trust a command merely because it was found in an imported workspace. Changed commands/direct program files require another inspection; unchanged trusted scorers do not prompt per task.

Use real task examples and an agreed checker: existing tests, an external scorer, human ratings, or an explicitly specified judging rubric. Scores may be any finite numbers; choose maximize or minimize. Do not invent scores merely to advance the workflow.

Separate examples used to learn from those used to check the candidate. References belong in each task's `reference` field for the scorer and training review, rather than being copied into execution instructions. Product mode inherits the host environment; it is not an isolated benchmark environment.

Use an existing skill as the baseline when provided. For another batch, `start --from PREVIOUS` carries its retained skill, Wiki and feedback into new tasks without copying old scores. Keep the user's task requirements and scoring criterion consistent between baseline and candidate. Human instructions still take precedence within their intended scope.

## Follow work requests

Run `wikiskill next WORKSPACE`. It returns the authoritative next phase and stable request IDs. Resolve relative artifact paths against WORKSPACE.

1. **Task request:** read its task and indicated skill; execute using normal tools. Save the actual output and, where useful, a visible work log or existing tool trace. Record them with `wikiskill record`. A configured scorer is run automatically. For manual scores, state the actual evaluation source. Do not fabricate tool traces or hidden reasoning.
2. **Maintainer request:** read its context file, training outputs/traces, current Wiki, and human feedback. Distinguish successes, failures and counterexamples. Write a `patterns` JSON file and submit it with `wikiskill learn`, citing the supplied training request IDs or feedback IDs. Human notes remain verbatim; the Wiki may add interpretation or counterexamples.
3. **Proposer request:** read the accumulated Wiki and relevant training evidence. Write a concise candidate SKILL.md with a name, description, applicability and concrete actions, or submit `--no-action`. The candidate can be a complete revision of the current skill. Do not put one-off reference answers into procedural guidance.
4. **Candidate validation:** follow the returned task requests. Let the controller apply the configured strict-improvement gate; never edit recorded scores or retained-version pointers.
5. **Complete:** summarize the change, baseline/candidate scores, tradeoffs, Wiki location and retained skill. A rejection or no_action is a valid outcome. Do not add rounds because the result was disappointing.

`next --count N` can issue several task requests when the host supports parallel work. Learning begins only after the relevant task phase finishes. No extra approval is needed for every step of an already authorized cycle; ask only when a missing decision, cost or side effect exceeds the user's scope.

## Feedback and recovery

Human suggestions can enter the Wiki immediately without LAJ approval. Record their original wording and source. A factual correction still needs the user's intended source/evidence treatment; a general method should be evaluated before claiming a benefit.

If a request fails, retain its output and logs, resolve the cause, and explicitly retry it. When `previous_output` is present after a scoring failure, reuse that actual output to retry evaluation before spending another model call. Never convert a broken scorer into a low task score.

Use the separate research commands only when the user explicitly wants those recorded experimental conditions. Do not impose Luna/high, macOS sandboxing, 8/4 task limits, or a particular model provider on this product workflow. Do not disable or bypass the host agent's own security controls.

---
name: wikiskill
description: Run or resume a WikiSkill improvement cycle using task examples, execution logs, scores, and user feedback. Use for evolving reusable agent skills, maintaining an experience Wiki, or exporting evaluated skills—not for ordinary one-off editing.
---

# WikiSkill

Help the user improve a recurring agent task through experience. Use the user's current agent, chosen model and normal tools. WikiSkill owns the work requests, records, scores and retained skill versions; it does not select a model or change host permissions.

## Start with the user's intent

- **Remember feedback:** save it with `wikiskill feedback`; do not start an improvement run merely because a note was added.
- **Improve a skill:** identify the task examples, evaluation criterion, current skill if any, and the user's intended effort/budget. Reuse information already provided. Begin with one round unless the user requests more; there is no hard sample or round cap.
- **Resume:** read `wikiskill status`, then use `wikiskill next` in the existing workspace. Do not initialize a duplicate run.
- **Check only:** use `wikiskill status` and existing artifacts; do not start more work.
- **Use the result:** export the retained skill. Install or replace an existing skill when the user has authorized that destination.

Read [workflow commands and formats](references/workflow.md) when preparing tasks or operating the loop. Use `wikiskill capabilities` to discover the installed interfaces. If the package is missing, install the user's selected checkout or `python -m pip install git+https://github.com/Stahl-G/wikiskill.git` in their chosen Python environment. The product path works without a Codex CLI account.

## Prepare a useful comparison

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

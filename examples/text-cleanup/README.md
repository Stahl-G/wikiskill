# A small user-workflow example

This example checks text labels: trim outside whitespace, collapse internal whitespace and lowercase the result. `tasks.json` has two learning examples and two validation examples; `score.py` is an external deterministic evaluator.

From the repository root:

```bash
wikiskill start runs/labels --tasks examples/text-cleanup/tasks.json --scorer '["python", "examples/text-cleanup/score.py"]'
```

Inspect and authorize the example scorer with `wikiskill scorer inspect runs/labels` and `wikiskill scorer trust runs/labels --fingerprint <shown-fingerprint>`.

Then ask your tool-using agent to load `skills/wikiskill/SKILL.md` and continue `runs/labels`, or inspect `wikiskill next runs/labels` yourself. The current agent executes tasks and authors the Wiki and candidate; the Python controller does not generate those outputs.

The example is deliberately small and may tie if the agent already normalizes every label correctly. That tests correct behavior of the loop, not a claim of model improvement.

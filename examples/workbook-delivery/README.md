# Learn from workbook delivery tasks

This small product example uses four synthetic order sheets: two learning cases and two validation cases. Complete the amount formulas, recalculate, and deliver the actual checked file. It is a usability example, not a benchmark or a promise of improvement. A capable agent may already solve every case without a skill.

## Give this to your agent

> Use WikiSkill to improve workbook delivery using this example's tasks and score.py. Start from no skill and run one round. Use my normal tools. The supplied checker is approved. Keep the source files unchanged, save outputs in a new local workspace, and finish with the result report and any retained skill. Do not add rounds to get a better result.

Install the WikiSkill entry skill as described in the repository README. The agent prepares/operates the workflow; you do not need to type each controller command.

## Requirements

- Python 3.11+, WikiSkill, and `openpyxl` for the checker (`python -m pip install openpyxl` in your project environment).
- A spreadsheet editor/calculation engine available to your agent. LibreOffice, Excel, or an existing workbook tool that saves calculated values can work. Merely setting a workbook to recalculate when opened is insufficient for these tasks.
- No particular inference model, provider, OS sandbox or account is required by this example.

The included input XLSX files are ready to use. They have no dependency on the authoring tool that generated them.

For direct CLI users, from the checkout root:

```bash
wikiskill start runs/workbook-delivery --tasks examples/workbook-delivery/tasks.json --rounds 1 --scorer '["python", "examples/workbook-delivery/score.py"]'
wikiskill scorer inspect runs/workbook-delivery
# Authorize the checker fingerprint if this checker is covered by your approval.
wikiskill scorer trust runs/workbook-delivery --fingerprint FINGERPRINT
wikiskill preflight runs/workbook-delivery
wikiskill next runs/workbook-delivery
```

## What is scored

Three equally weighted checks produce a score from 0 to 1:

1. Live multiplication/PRODUCT formulas for amounts and SUM/addition for the total, as specified by the tasks. The checker deliberately supports this narrow formula vocabulary, not every equivalent Excel expression.
2. Correct cached numeric values in the exact submitted workbook, derived independently from the input values.
3. Unrelated cell values and number formats preserved.

The checker reads outputs; it does not recalculate them for the agent. Missing caches lose the saved-values component. A malformed output workbook scores zero; a missing dependency or source file is a scorer failure. This does not measure every formatting feature, prove general formula behavior, or enforce a benchmark isolation boundary. There is no external dataset or answer key.

The input files and checker should stay fixed for a run. Do not replace them after seeing the candidate's results. Baseline and candidate should use the same tools and task requirements. The generated Wiki, proposal and report belong to your local run; do not treat this example as an independent estimate of the research paper's effect.

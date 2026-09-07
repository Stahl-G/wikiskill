# Opt-in isolated Spreadsheet study

This entry point ports the Spreadsheet task/learning path into the installed package. It is a **single-round train/validation development study**, not an additional benchmark result. The default `wikiskill evolve` path and historical result snapshots remain unchanged.

The initial scope is macOS, the Codex CLI, and explicit Luna/high role calls. Install the package with its workbook and paper-contract dependencies:

```bash
python -m pip install '.[spreadsheet,paper]'
```

Supply your own authenticated Codex CLI, legally obtained SpreadsheetBench data and train/val split JSON files, and an installed headless-compatible LibreOffice application bundle. The package does not download the dataset or bundle LibreOffice. Paths below are placeholders.

```bash
# Local checks only; no model inference
wikiskill spreadsheet-study preflight --libreoffice-app /path/to/LibreOffice.app

# Freeze a small study. Selection is deterministic, not based on scores.
wikiskill spreadsheet-study prepare /path/to/study \
  --data /path/to/spreadsheet-data \
  --split-dir /path/to/splits \
  --libreoffice-app /path/to/LibreOffice.app \
  --train-limit 8 --val-limit 4 --workers 2

# Starts real model calls; requires available model access.
wikiskill spreadsheet-study run /path/to/study
wikiskill spreadsheet-study status /path/to/study
wikiskill spreadsheet-study verify /path/to/study
```

The bounded study runs a no-skill validation baseline and fresh training tasks, then one Maintainer and one Proposer from an empty Wiki. Sampling separates up to five failures and three successes; a missing category is disclosed, not fabricated or obtained through repeated sampling. If the Proposer submits a valid candidate, that candidate is evaluated on the same validation tasks and retained only on strict improvement. `no_action`, ties and decreases are valid outcomes. There is no automatic K=4 continuation or test launch.

Both inference conditions receive the legal instruction type, answer region/sheet and input preview. The original cell-region cached-value scorer remains outside inference. Only the task input workbook enters the inference payload. Training references enter optimizer payloads only. Native role isolation, disabled personal instructions/memory, explicit permitted tools and per-call boundary probes are part of this backend; `workspace-write` alone is not treated as read isolation.

The selected runtime supports isolated bash with Python/openpyxl and workspace-local LibreOffice recalculation. The skill's entire text is injected for candidate validation; automatic skill retrieval is not tested. Target-value scoring does not establish whole-workbook formatting or dynamic formula fidelity.

Completed native calls and score records are retained and checked on resume. A completed native call may be recovered through deterministic postprocessing without resampling. Failed/incomplete calls remain inspectable and are not automatically re-queried. Diagnose a failure before a new revision or retry policy; do not remove its artifacts to force another sample.

For the initial 8-train/4-validation defaults, the maximum is 16 task calls plus two role calls. This is an installation/runtime acceptance check. It does not measure held-out skill benefit, compare optimization methods, or reproduce the published 278-task result. Run status and terminal outcomes are recorded in the caller-owned study directory; no private runtime logs or dataset material should be committed to the repository.

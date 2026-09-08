# Product first-use validation

This is the local implementation and acceptance record for the product usability update following v0.1.0. It does not announce a new release or remeasure the historical research experiments.

## Implemented user path

The entry skill prepares task JSON from examples and agreed acceptance criteria, inspects readiness, follows the host-agent loop and produces a journal-derived report. New interfaces are `preflight`, `status --human`, `report`, `install` and `restore`. `doctor` identifies the project/distribution and actual installation path. JSON work requests remain available for integrations.

Reports show completed gates, per-task changes against the incumbent of each round, skill diffs, source-bound Wiki patterns and what can be exported. Partial baselines are marked incomplete. Local replacement backs up SKILL.md, preserves support files and refuses to restore over subsequent user edits.

The rule review found and corrected missing-score-to-zero conversion in the research mean. Shared finite-score/strict-improvement functions now serve research and product while their journals and protocols remain separate. New product task sets bind input file contents; a changed external checker after successful scoring requires a new comparison. Old frozen records are not migrated or reinterpreted.

## Independent agent acceptance

A separate agent received only the copied entry skill, workbook example, installed CLI, tool availability and a realistic request to run one round. It did not inspect implementation source or tests. It executed two baseline tasks, two training tasks, Wiki maintenance, a candidate proposal and two candidate validations.

All six scored 1.0. The gate rejected the tie, retained no skill from the empty initial state, and preserved two Wiki patterns and the candidate. No candidate was installed or exported as retained. [Per-task scores and hashes](../examples/workbook-delivery/acceptance.json).

The agent used its ordinary spreadsheet guidance and tools for both conditions: Artifact Tool import/edit/recalculate/export, with read-only openpyxl checks of the exact exported files. It freshly executed candidate workbooks rather than reusing baseline answers. These are small synthetic cases on one host; ordinary host instructions and context remained available. Exact model/effort identity was not available and was omitted. This proves workflow execution, not an improvement in capability.

There was **one configuration intervention**. The sandbox could not write the default local scorer trust directory. The agent was given the supported `WIKISKILL_TRUST_DIR` override and resumed the existing workspace. The documentation and permission error were subsequently updated to expose that recovery path. A targeted check verifies failed setup leaves a resumable workspace and that a writable external trust directory permits continuation. The six workbook tasks were not rerun to claim an unaided result.

After the hint, no further user decision or implementation-source access was required. A separate read-only recomputation of all six saved outputs matched the recorded scores. Input workbooks, task definitions and checker matched the checkout byte-for-byte.

## Natural-language setup check

A small follow-up asked the same evaluator to prepare a different title-cleanup task from natural-language examples, with human scoring and an explicit instruction not to start execution. It used the updated entry skill and final installed CLI, produced two training/two validation tasks and the requested scoring/scope note, initialized and preflighted a new workspace, and stopped. The journal showed zero task results, no pending requests, no gates and an unmeasured baseline. No user-authored JSON or additional configuration hint was needed. This is a setup-only check, not another evolution run or an independent second evaluator.

## Software and installation evidence

Focused checks cover reports for acceptance/rejection/no_action, per-round incumbent selection, partial baselines, minimize metrics, readiness without task/scorer side effects, input changes, checker changes, local install/restore and preservation of user edits. The workbook checker is tested against known complete outputs, absent caches, absent formulas, changed inputs and malformed output files; those ZIP mutations are software fixtures, not claims of real recalculation.

A non-editable wheel was installed outside the source tree with ordinary dependencies supplied by the local environment. Its demo exercised acceptance, rejection and no-action, and its bundled result verification passed. A final wheel's product modules were compared byte-for-byte with source; it read and reported the completed agent workspace successfully. The agent run preceded the later input-binding and diagnostic refinements; those additions have targeted software coverage rather than a claimed second agent run.

Source archives include all four example XLSX files. Package execution does not depend on the local artifact-authoring library. Existing CI now includes the new product view/installation tests in its Linux/Windows/macOS matrix; only local checks have run for this unpushed update.

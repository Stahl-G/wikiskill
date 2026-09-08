# Product workflow validation

The product controller is independent of the older research runners. Its commands emit work requests for a calling agent and record actual task outputs, evaluation results, Wiki submissions and candidate skills.

## Independent entry-skill forward test

An independent tool-using agent received the entry SKILL.md, the text-cleanup task examples and the external scorer. It operated the workflow without reading implementation source or being told which gate verdict to produce.

It completed two baseline tasks, two training tasks, Wiki maintenance, a candidate skill and two candidate validation tasks. It also recorded a direct user-feedback note before the loop. Both baseline and candidate scored 1.0, so the controller rejected the tied candidate. The Wiki retained two generated patterns and the original feedback. No retained skill was exported because the initial skill was empty and the candidate did not improve the baseline.

This verifies one real agent-driven use of the entry instructions. It is not benchmark evidence of an improvement. No additional model API was launched by the controller; the calling agent performed the work using its normal tools. The agent reported that normal operation required no implementation-source inspection. Its discovered export edge-case documentation gap was corrected.

## Deterministic checks

Focused product tests cover continuous scores and minimize/maximize, acceptance/rejection/no_action, Wiki and feedback retention, source-bound pattern updates, retry without losing a saved output, duplicate-record behavior, changed-output detection, concurrent-writer exclusion, configurable task/round sizes, and carrying knowledge into new task batches without carrying old scores.

The normal project CI also exercises the product commands on Linux, Windows and macOS. These software checks and the agent-driven example complement each other; neither makes the normal host environment an isolated research runtime.

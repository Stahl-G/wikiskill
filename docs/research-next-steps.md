# Next research and practical milestones

Status: proposed work, not launched or measured. These directions follow the [September 7 final results](research-final-20260907.md).

## 1. Make the observed path reproducible from this repository

First integrate the corrected Spreadsheet input contract, permitted recalculation tools, balanced learning evidence and isolated inference boundary into a versioned portable backend. Keep legacy snapshots unchanged. A clean install should run a small real train → Wiki → proposal → validation gate cycle, resume it, and evaluate/export a frozen skill. The published score-only recomputation checks are already useful, but are not this model-backed installation proof.

Prioritize separate interfaces for importing existing train traces, evaluating frozen skills, and exporting a skill bundle with its required tools and applicability. Keep test evaluation separate from the evolution engine. Domain preflight should check datasets, scoring dependencies and boundary enforcement before starting model calls. These are proposed interfaces; they are not current CLI commands.

## 2. Separate repeatability, transfer and causal attribution

| Question | Proposed comparison | Interpretation boundary |
|---|---|---|
| Does the same skill remain useful on another run? | Freeze the current skill and repeat fresh paired S0/SK inference under the same conditions, fixed repeat count decided before execution | Repeated inference measures this artifact; it does not measure the probability of evolving a useful skill |
| Does it help on genuinely new workbooks? | New independently authored tasks, with no-skill, a pre-fixed generic recalculation/checking baseline, and the frozen evolved skill | Extra conditions diagnose whether a short engineering recipe explains most of the gain; never retroactively modify the completed benchmark |
| Is persistent Wiki accumulation itself useful? | Full WikiSkill versus a paper-aligned no-Wiki ablation, matched task/validation access and declared optimizer budgets, from independent empty starts | Repeat evolution, not just inference; publish all starts and their costs rather than selecting the best seed |
| Does the skill transfer to another model/runtime? | Within each recipient, fresh matched S0/SK with the source skill unchanged | Keep model, effort and runtime differences separate; do not infer transfer from an unmatched score table |

The paper's persistent-Wiki ablation and cross-model experiments motivate the last two questions ([original paper, sections 4.2.2 and 5.1](https://arxiv.org/html/2608.27454v1)). The current corrected Spreadsheet result tests a selected skill against no skill; it has not isolated the Wiki's causal contribution.

## 3. Pilot a narrow workbook-delivery capability

A useful first application is formula editing followed by recalculation and verification of the exact delivered workbook. Start with offline shadow evaluation on copied workbooks. Evaluate target values, required formulas, changed inputs/new rows, out-of-region cells, formats, time and correction effort. Keep the original benchmark score as a separate metric; business acceptance must not silently replace it.

Test both forced skill injection and normal skill selection before claiming end-to-end deployment benefit. A safe artifact can still be loaded for the wrong task, ignored, or require unavailable tools. Publish the measured artifact and requirements; do not automatically install it into every agent or promote every validation winner into production.

## Defer broad expansion

Additional domains, a full model-by-effort grid, another large K=4 sweep, and a general-purpose self-editing production loop should wait for the small reproducible package path and an external task pilot. The completed uncertain or negative observations remain part of the research record. OpenClaw experiments remain a separate runtime study until an explicitly matched comparison exists.

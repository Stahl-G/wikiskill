# Generalization study status

Updated 2026-09-05. An independent lean held-out campaign has started in the originating experimental environment. It is separate from the portable train/val CLI in this repository.

The revised study compares S0 and a frozen skill once on each task, with five selected nonempty-skill cells: staged OfficeQA/GPT-5.5, LiveMath-v2/GPT-5.5, SealQA/Sol, Spreadsheet/Sol and Spreadsheet/GPT-5.5. Planned work is 1,874 task episodes. The estimand concerns these retained skills; it is not the original all-model, all-domain average.

**Full-corpus OfficeQA retrieval is not included in this campaign.** In particular, this run will not independently validate the headline retrieval Sol gain of +20.8 validation percentage points. Retrieval needs its own held-out design.

A launch audit found unresolved protocol/code/split binding metadata in the source campaign, while the skill-file hashes themselves matched. The running state is evidence of execution, not a completed validity review. Results remain pending and unvalidated; subsequent corrections or protocol revisions must preserve their actual timing and any affected run history.

No test scores or model answers were inspected for this status update. The repository's validation snapshot remains unchanged. See [reproduction](reproduction.md) for differences between historical source experiments and this portable package.

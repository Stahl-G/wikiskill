# Generalization study status

## Integrity update: 2026-09-05

The subsequent OfficeQA v1-to-v2 Sol transfer run completed 90 pairs. Its journal
can be recomputed (S0 59/90; frozen skill 52/90), but postflight inspection found
successful reads of answer-bearing CSV files, other-arm answers and personal
memory. These numbers are contaminated execution observations, not an estimate
of a clean skill effect. They establish neither improvement nor deterioration.

The historical v1 retrieval line also has confirmed cross-run validation access:
in Sol iteration 2, UID0240 read prior outcome records containing scores and
predictions. Therefore the previously highlighted +20.8pp validation gain cannot
support an uncontaminated reproduction claim. Historical files and values are
retained, not silently corrected. Other cells have not thereby been certified
clean or proven contaminated; their validity needs their own evidence.

A corrective local replication now starts from an empty Wiki and empty skill,
using Sol/medium, v1 train 50 / val 24, up to four iterations, followed by a frozen
paired test on the same 90 v2 questions when a nonempty skill is retained. The
runtime uses scoped document tools, isolated role payloads, disabled personal
memory and a native calculation sandbox. Training reference answers are available
only to the optimizer. Existing parsed-text inputs are retained, so this is not
an official multimodal leaderboard configuration. Prior researcher exposure and
the change in runtime/tool interface are explicitly disclosed.

The isolated driver is currently in the originating experimental environment;
it has not yet replaced the portable backend shipped here. Do not use the current
unrestricted backend as a confirmatory isolation guarantee. No new efficacy claim
will be made before the corrective run and its validity review finish.

## Earlier campaign note (historical)

Updated 2026-09-05. An independent lean held-out campaign has started in the originating experimental environment. It is separate from the portable train/val CLI in this repository.

The revised study compares S0 and a frozen skill once on each task, with five selected nonempty-skill cells: staged OfficeQA/GPT-5.5, LiveMath-v2/GPT-5.5, SealQA/Sol, Spreadsheet/Sol and Spreadsheet/GPT-5.5. Planned work is 1,874 task episodes. The estimand concerns these retained skills; it is not the original all-model, all-domain average.

**Full-corpus OfficeQA retrieval is not included in this campaign.** In particular, this run will not independently validate the headline retrieval Sol gain of +20.8 validation percentage points. Retrieval needs its own held-out design.

A launch audit found unresolved protocol/code/split binding metadata in the source campaign, while the skill-file hashes themselves matched. The running state is evidence of execution, not a completed validity review. Results remain pending and unvalidated; subsequent corrections or protocol revisions must preserve their actual timing and any affected run history.

No test scores or model answers were inspected for this status update. The repository's validation snapshot remains unchanged. See [reproduction](reproduction.md) for differences between historical source experiments and this portable package.

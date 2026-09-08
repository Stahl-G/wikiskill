# September 8: the frozen Spreadsheet skill across three runs

The same Luna/high Spreadsheet skill improved accuracy in three full executions of a fixed 278-task split. This follow-up asks whether the first observed benefit repeats, using the same skill, recipient model, effort, permitted tools, input metadata and target-cell scorer.

## Results

| Run | No skill | Frozen skill | Difference | Wins / losses |
|---|---:|---:|---:|---:|
| 1 | 213/278 (76.62%) | 237/278 (85.25%) | +8.63 pp | 31 / 7 |
| 2 | 200/278 (71.94%) | 234/278 (84.17%) | +12.23 pp | 43 / 9 |
| 3 | 202/278 (72.66%) | 242/278 (87.05%) | +14.39 pp | 44 / 4 |

The **primary follow-up comparison** uses only the two newly planned repetitions: mean accuracy **72.30% → 85.61%**, a **+13.31 pp** difference with task-cluster bootstrap 95% CI **[+9.35, +17.45] pp**. The supplementary three-run average is **73.74% → 85.49%**, **+11.75 pp**, CI **[+8.27, +15.35] pp**.

Both intervals use 10,000 resamples and seed `2026090804`. Each resampled unit is a task UID, keeping its observations from the included repetitions together. There are **278 task clusters**, not 834 independent tasks. Three runs do not fully characterize variation across dates, service versions or independent skill evolutions.

The no-skill result changed correctness at least once for **58 of the 278 tasks** across three runs. The skill's aggregate accuracy remained between 84.17% and 87.05%. This supports repeated usefulness of this frozen artifact in the recorded setting, rather than a claim that the agent learned further during testing.

## Design and execution record

- The follow-up was planned after the first positive result was observed. It is an exploratory fixed-split replication, not an untouched confirmatory study. Earlier researcher exposure remains disclosed.
- The first run's skill, data, code and results were bound before the additional work. The frozen skill SHA256 is `7876c7ecb4b2aad0e55d7623335bd3781512247a1723815c2deec0036e1cc0bf`.
- Runs 2 and 3 each contain 278 fresh S0/skill pairs: **1,112 new task attempts** in total. No previous answer was used as a cached new inference.
- Four task pairs ran concurrently; each pair's two arms ran sequentially. Run 3 reversed the arm order for every UID from run 2, with a separately shuffled task order. Run 2 completed before run 3 began.
- No new Wiki/Proposer calls, skill selection or model changes occurred during this follow-up. Both positive and negative task changes remain in the output.
- A predeclared 1,800-second task timeout counted as zero, with the incomplete attempt preserved. It occurred once in run 3's skill arm. There were **zero transport retries** in the follow-up.
- Execution had a 12-hour new-pair dispatch window, at most 32 bounded transport retries and an 8 GiB free-disk pause threshold. All planned pairs completed.
- Host sleep interrupted part of run 3. Original timestamps remain intact. A process-bound idle-sleep assertion was added without restarting the experiment; raw elapsed time should not be interpreted entirely as active computation cost.

The source harness imports and scores workbooks using the recorded permitted tools. Its outcome is exact matching of requested target-cell cached values. It does not assess all formatting, off-target changes or formula behavior under future edits. The runtime/source differences and first-run transport history remain in the [September 7 report](research-final-20260907.md).

This experiment establishes neither the persistent Wiki's independent causal contribution nor the success rate of fresh evolutions. Those require matched optimizer ablations and repeated evolution starts. It also does not replace evaluation on new workbook tasks.

## Public evidence

[Score-only records and manifest](../src/wikiskill/resources/research/repeatability-20260908) include three complete paired tables, the frozen UID order for exact bootstrap reproduction, aggregate statistics and provenance hashes. The original Wiki page is included as a concrete learning example; the associated [skill](../src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) remains byte-identical.

```bash
python scripts/check_repeatability_20260908.py
```

This independently recomputes the paired scores, both cluster intervals and baseline flips from the public records. It makes no model calls. Recalculation of exported results is different from executing a new model experiment.

Local source verification checked all 1,112 result rows and **15,565 registered artifact hashes** without mismatch; the primary cluster analysis was also recomputed. Raw workbooks, task questions, answers, trajectories, account information and local paths are not included in the public export.

## Installed package: a separate real workflow check

The new opt-in `spreadsheet-study` path also completed a small real loop from a non-editable wheel installed outside the source checkout:

- 4 fresh baseline calls and 8 training calls;
- one Maintainer and one Proposer, with four actual training traces read by the Proposer;
- 4 candidate validation calls;
- a **3/4 → 3/4** tie, correctly rejected;
- final artifact verification and completed-run resume with **zero additional model calls**.

This establishes one real integration run, not an efficacy estimate or a rerun of the 278-task study. It used source commit `e6f0759`; a later cancellation-cleanup fix has separate offline tests and was not hot-installed into that run. See [the installed study guide](isolated-spreadsheet-study.md).

## Other domains remain part of the record

The original SealQA test finished **41/85 → 44/85**, statistically inconclusive. OfficeQA V1's earlier **98/172 → 104/172** result is also inconclusive. Mathematics' four-arm, two-repeat study is exploratory validation, with one old and one new skill showing positive average differences and the Astra-authored artifact showing no average difference. See [complete results and amendments](research-final-20260907.md); the positive Spreadsheet follow-up does not replace them.
